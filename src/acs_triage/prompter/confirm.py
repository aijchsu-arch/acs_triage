"""紅旗題與關鍵題的有條件複誦確認（confirm-back；D-50，rules_version 0.8.0，docs/CLINICAL_RULES.md §5.10）。

範圍：`priority: redflag` 的題，加上 `thresholds.stt_critical_questions`。信心偏低時先走 Confidence Gate
（請病人再說一次，D-43），再說一次之後的回答才套這裡的觸發條件。對話流程在呼叫端（sim/runner.py）；這裡放要不要複誦
（should_confirm，含寫入即 Hard stop 不複誦）、確認後取值與文字組合。詞表在 data/extraction_patterns.yaml 的
leading_yes_no，嚴重度順序在 data/clinical_rules.yaml 的 confirm_back_severity，複誦文字與值的中文在 data/scripts_zh.yaml
（DRAFT，待 Q-10）。複誦不得成為降級路徑：值已是最嚴重一級不複誦；確認後取較嚴重者（Clinical Owner 2026-10-22）。
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from ..loaders import load_clinical_rules, load_extraction_patterns, load_scripts
from ..rules import RulesEngine, SlotState
from ..schemas import Question


@lru_cache(maxsize=None)
def _lexicon() -> tuple[tuple[str, ...], tuple[str, ...], list[str], re.Pattern[str]]:
    lx = load_extraction_patterns()["leading_yes_no"]
    pos = tuple(sorted(lx["affirmative"], key=len, reverse=True))
    neg = tuple(sorted(lx["negative"], key=len, reverse=True))
    masks = sorted(lx["non_negation_phrases"], key=len, reverse=True)
    return pos, neg, masks, re.compile(rf"^[\W_{lx['filler_chars']}]+")


def leading_yes_no(text: str) -> bool | None:
    """回答句首是否為明確的肯定詞（True）或否定詞（False）；都不是 → None（不明確）。

    去掉句首標點與語助詞，並先遮罩「不舒服、不知道、不確定」等含「不／沒」但非否定的片語，
    再看開頭：否定詞（沒有、沒、不會、不是、不、沒什麼、還沒）→ False；肯定詞（有、會、是、還在、對）→ True。
    只看句首，其後的否定詞不翻轉它（「有，不過沒有冒汗」→ True）。

    **輸入必須是繁體。** 詞表是繁體；Whisper 輸出多為簡體，進抽取器與本判斷前一定要先轉繁
    （D-49：OpenCC s2twp，並先在「是」「只」之間切開，避開 OpenCC 詞組「是只→是隻」）。
    簡體漏網時，含簡體字的詞（没有、没、对、会、还在、还没）比不到詞表 → 判為不明確 → 觸發確認，屬安全方向；
    但以「不」開頭的簡體非否定片語（不确定、不适、不规则、不过…）遮罩不到，會被當成否定詞「不」，
    所以轉繁是必要前置，不能靠本函式兜底。
    """
    pos, neg, masks, lead_re = _lexicon()
    s = lead_re.sub("", text)
    for m in masks:
        s = s.replace(m, "□" * len(m))
    if s.startswith(neg):
        return False
    if s.startswith(pos):
        return True
    return None


def in_scope(q: Question) -> bool:
    """紅旗題與 stt_critical_questions（同 Confidence Gate 用 0.9 門檻的題目）。"""
    return q.priority == "redflag" or q.id in load_clinical_rules()["thresholds"].get("stt_critical_questions", [])


@lru_cache(maxsize=None)
def _severity_table() -> dict[str, dict[Any, int]]:
    """confirm_back_severity → {slot 或 "yes_no": {值: 級數}}，0 = 最嚴重，同一層同級。"""
    return {key: {v: rank for rank, level in enumerate(levels) for v in level}
            for key, levels in load_clinical_rules()["confirm_back_severity"].items()}


def severity(q: Question, value: Any) -> int:
    """值的嚴重度級數（0 = 最嚴重）。是非題共用 yes_no 順序（有 > 沒有），選擇題依 slot。"""
    return _severity_table()["yes_no" if q.answer_type == "yes_no" else q.slot_id][value]


def needs_confirm(q: Question, value: Any, utterance_zh: str) -> bool:
    """回答本身是否可疑、要複誦（只看值與句子；範圍與 Hard stop 例外由 should_confirm 處理）。

    值已是該題最嚴重一級（是非題「有」、典型症狀、坐著也喘）→ 不複誦：複誦只可能把它改得較不嚴重。
    是非題：值不明（None），或值為「沒有」而句首不是明確的否定詞（不明確或句首是肯定詞）→ 複誦。
    選擇題：值不明或不是最嚴重一級 → 複誦。
    """
    if value is not None and severity(q, value) == 0:
        return False
    if q.answer_type != "yes_no":
        return True
    return value is None or leading_yes_no(utterance_zh) is not False


def _trial(state: SlotState, q: Question, value: Any) -> SlotState:
    st = state.copy()
    st.set(q.slot_id, value, asked_by=q.id, source="confirm_trial")
    return st


def confirm_prompt(q: Question, value: Any) -> str:
    """複誦文字：只用 data/scripts_zh.yaml 的模板＋題目原文＋值的中文組合（DRAFT，待 Q-10）。"""
    scripts = load_scripts()
    question = q.script_zh.strip()
    if value is None:
        sid = "S-CONFIRM-BACK-ASK-YESNO" if q.answer_type == "yes_no" else "S-CONFIRM-BACK-ASK"
        return scripts["scripts"][sid]["text"].format(question=question)
    labels = scripts["confirm_value_labels_zh"]
    answer = labels["yes_no"][value] if q.answer_type == "yes_no" else labels[q.slot_id][value]
    return scripts["scripts"]["S-CONFIRM-BACK"]["text"].format(question=question, answer=answer)


def should_confirm(engine: RulesEngine, state: SlotState, q: Question, value: Any, utterance_zh: str) -> bool:
    """呼叫端用的總判斷：範圍內、回答可疑（needs_confirm），且寫入後不是 Hard stop（不得因確認延誤送醫）。"""
    return (in_scope(q) and needs_confirm(q, value, utterance_zh)
            and not engine.decide(_trial(state, q, value)).hard_stop)


def resolve_confirm(q: Question, value: Any, confirmed: Any) -> tuple[Any, bool]:
    """確認後取值 → (採用的值, 是否因確認值較不嚴重而保留原值)。

    確認回答不明 → 是非題原為「沒有」改成 None（未經確認的紅旗否認不採信），其他保留原值。
    原值不明 → 採用確認值。兩者都有值 → 取嚴重度較高者（confirm_back_severity）；同級保留原值。
    """
    if confirmed is None:
        return (None if q.answer_type == "yes_no" and value is False else value), False
    if value is None:
        return confirmed, False
    if severity(q, confirmed) < severity(q, value):
        return confirmed, False
    return value, severity(q, confirmed) > severity(q, value)
