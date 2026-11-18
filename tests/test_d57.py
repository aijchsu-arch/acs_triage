"""D-57（Clinical Owner 2026-11-18 採用 A）：關鍵詞路徑命中的可重現胸壁痛同樣只記旗標 reproducible_mechanical_mentioned，
紅旗題後問一次 Q-REPRO-01，只有直接回答寫入（修 D-56 已知限制 (a)；CLINICAL_RULES §5.13-6，同 D-56 裁定 #3）。
情境事實（sim/cases.py，病人知道的事）不變：開場白說的胸壁痛仍是事實，病人被問到時答得出來。"""
import dataclasses

import pytest

from acs_triage.extract import extract
from acs_triage.loaders import question_by_id
from acs_triage.rules import SlotState
from sim.cases import all_cases
from sim.patient import ScriptedPatient
from sim.runner import run_case

FLAG = "reproducible_mechanical_mentioned"
CASES = {c.id: c for c in all_cases()}
REDFLAGS = {q.id for q in question_by_id().values() if q.priority == "redflag"}
EXAMPLES = ["按下去不會痛", "胸口按下去不會痛，深呼吸也不會痛", "搬東西的時候會悶"]       # D-56 已知限制 (a) 的三句
S14_FULL = CASES["S-MID-14"].opening_zh
S14_SHORT = "胸口肌肉按下去會痛，深呼吸也痛"
# D-56 對抗探針（LLM 路徑按壓用語防護的兩輪最終驗收；D-57 前現行關鍵詞樣式把第二輪 25 句非按壓／否定句中的 9 句寫成 true）
PROBE1 = [
    "胸口肌肉按下去會痛，深呼吸也痛", "現在沒在咳就不會痛", "咳嗽的時候胸口會痛", "按下去不會痛", "深呼吸會痛", "轉身會痛",
    "血壓高的時候胸口會痛", "像被石頭壓住", "壓著會痛", "摸到那邊就痛", "按時吃藥還是痛", "按下去不會痛，咳嗽會痛",
    "咳嗽會痛，按下去也痛", "碰到會疼", "按壓胸口會很痛", "一按就痛", "按照醫生說的吃藥，胸口還是痛", "壓力大的時候胸口會痛",
    "胸口壓壓的會痛", "有壓迫感，很痛", "胸口被壓著很痛", "按下去沒有痛", "按下去並不會痛，只是悶", "沒有按也會痛",
    "沒有去按也會痛", "沒有特別按也會痛", "不需要按就會痛", "就算沒有去碰也會痛", "好像有一塊大石頭壓著會痛",
    "被一個很重的東西壓著會痛", "按下去會痛還是不會痛我不確定", "用手按那邊，有一點痛", "按電梯按鈕的時候胸口痛",
    "一碰到爬樓梯就胸口痛", "碰到冷風胸口就會痛", "按摩的時候胸口會痛", "睡覺壓到會痛", "像針刺一樣，按下去也會痛",
    "胸口按下去的時候左邊那一塊會痛",
]
PROBE2 = [
    "按下去的時候沒什麼感覺，但走路會痛", "壓著不會痛但咳嗽會痛", "摸到那邊是腫腫的，不痛", "碰到胸口的衣服會痛",
    "按下去還好走路的時候胸口會痛", "摸起來還好爬樓梯才會痛", "按下去感覺還好但是休息的時候也會痛", "按著扶手爬樓梯胸口會痛",
    "手按著胸口才能減輕疼痛", "我都按著胸口忍痛", "按著胸口會舒服一點痛比較少", "你是說按下去會痛嗎？沒有啦",
    "醫生問我按下去會痛嗎？我說還好。", "按下去應該會痛吧我也說不準", "按下去可能會痛吧", "按下去哪會痛", "按下去並非會痛",
    "之前按下去會痛現在已經好了", "壓著棉被睡覺起來胸口痛", "碰到那邊的冷水會痛", "摸到冰的東西胸口會痛", "按下門鈴的時候胸口痛",
    "按下去痛的是手指", "壓下去心臟會悶悶的痛", "按到胸口那邊就喘就痛",
    "胸口按下去會痛", "按壓那邊會痛", "摸到胸口那裡會痛", "碰到那邊會疼", "按著會痛", "胸口按下去會痛 深呼吸也痛",
    "按下去會痛喔", "那邊按到胸口會痛",
]


def _qs(r):
    return [t.question_id for t in r.turns]


def _old_keyword_path(case):
    """對照：D-57 前的關鍵詞路徑（開場白命中直接寫 true），回答用結構化事實（同 Scripted）。"""
    def ex(text, q, confirm_prompt=None):
        if q is None:
            x = {k: v for k, v in extract(text).items() if v is not None}
            if x.pop(FLAG, None):
                x["reproducible_mechanical"] = True
            return x
        return {q.slot_id: ScriptedPatient(case).answer(q).value}
    return ex


@pytest.mark.parametrize("text", EXAMPLES + [S14_FULL, S14_SHORT])
def test_keyword_hit_sets_flag_only(text):
    """三句例句與 S-MID-14 開場白：不寫入 reproducible_mechanical，只記旗標；「有症狀」判斷（consult_topic）不變。"""
    x = extract(text)
    assert "reproducible_mechanical" not in x and x[FLAG] is True
    assert x["consult_topic"] == "symptom"


@pytest.mark.parametrize("text", PROBE1 + PROBE2)
def test_probe_sentences_never_write_slot(text):
    """兩輪對抗探針的每一句（非按壓、否定、不確定、手勢、問句複述，以及真的按壓痛）：關鍵詞路徑都不寫入 slot。"""
    assert "reproducible_mechanical" not in extract(text)


@pytest.mark.parametrize("text", [S14_FULL, S14_SHORT])
def test_s_mid_14_opening_alone_not_t3_confirmed_t3(engine, text):
    """S-MID-14 benchmark 重新定義（Clinical Owner 2026-11-18）：只給開場白 ≠ T3；開場白＋Q-REPRO-01 答「會」→ T3（T3-MECHANICAL）。"""
    slots = extract(text)
    assert engine.decide(SlotState(slots)).provisional_tier != 3
    d = engine.decide(SlotState({**slots, "reproducible_mechanical": True}))
    assert (d.provisional_tier, d.hard_stop) == (3, False) and "T3-MECHANICAL" in d.evidence


def test_case_facts_unchanged():
    """情境事實不含旗標；S-MID-14 的事實仍是 reproducible_mechanical＝true（truth 不變，病人答得出 Q-REPRO-01）。"""
    assert all(FLAG not in c.slots for c in CASES.values())
    assert CASES["S-MID-14"].slots["reproducible_mechanical"] is True


def test_scripted_s_mid_14_asks_repro_once_after_redflags_then_t3():
    """Scripted（關鍵詞路徑）S-MID-14：紅旗題問完後第 5 題問 Q-REPRO-01、答「會」→ T3-MECHANICAL；與 D-57 前相同，多 1 題。"""
    c = CASES["S-MID-14"]
    r, old = run_case(c), run_case(c, extractor=_old_keyword_path(c))
    qs = _qs(r)
    assert qs.count("Q-REPRO-01") == 1 and qs.index("Q-REPRO-01") == 4 and set(qs[:4]) <= REDFLAGS
    assert r.final_state._values["reproducible_mechanical"].asked_by_question_id == "Q-REPRO-01"
    assert [x for x in qs if x != "Q-REPRO-01"] == _qs(old) and r.n_questions == old.n_questions + 1
    assert (r.final.tier, r.final.hard_stop, r.final.evidence) == (3, False, ["T3-MECHANICAL"])
    assert (old.final.tier, old.final.evidence) == (3, ["T3-MECHANICAL"])


@pytest.mark.parametrize("fact", [False, None])
@pytest.mark.parametrize("text,old_evidence", [
    ("按下去不會痛", ["T3-MECHANICAL"]),
    ("胸口按下去不會痛，深呼吸也不會痛", ["T3-MECHANICAL"]),
    ("搬東西的時候會悶", ["T0-NEW-TODAY"]),          # 性質是 tightness，D-57 前在這組事實下也沒走 T3-MECHANICAL
])
def test_examples_no_longer_under_triage(text, old_evidence, fact):
    """S-MID-14 的其他事實（今天新發刺痛）＋例句開場白，病人其實沒有可重現胸壁痛（答「不會」或不知道）：
    D-57 前關鍵詞直接寫 true → 前兩句走 T3-MECHANICAL 定案 T3（全資訊 T0，under-triage）；D-57 起問一次 Q-REPRO-01 → T0。"""
    base = CASES["S-MID-14"]
    c = dataclasses.replace(base, id="D57-X", opening_zh=text, slots={**base.slots, "reproducible_mechanical": fact})
    r, old = run_case(c), run_case(c, extractor=_old_keyword_path(c))
    assert old.final.evidence == old_evidence
    assert _qs(r).count("Q-REPRO-01") == 1 and r.final_state.get("reproducible_mechanical") is fact
    assert (r.final.tier, r.final.hard_stop) == (0, False) and "T3-MECHANICAL" not in r.final.evidence
