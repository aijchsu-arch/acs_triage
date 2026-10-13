"""決定性問題（decisive question）的可重算定義。

定義（依 Reviewer Prompt v0.2：「只列會真正改變 disposition 的問題」）：
  在某個 case 的完整事實（hidden sheet）下，題目 q 是決定性的，若且唯若
  (1) 依 Prompter 的相關性規則，q 在「其他事實皆已知、只有 q 未知」時會被視為相關；且
  (2) 把 q 的 slot 換成任一可能答案，(provisional_tier, hard_stop) 不全相同。
也就是：答案會改變分流結果的題目。不改變結果的題目（例如已判 T0 後再問休息時症狀）不算。

方向（D-27）：
  escalating   = 存在某個答案，使結果比「真實答案」更急 —— 漏問會造成 under-triage（安全指標）。
  de-escalating = 只存在使結果較不急的答案 —— 漏問只會 over-triage（保守），不列入安全指標。
  急迫度排序：Hard stop > T0 > T1 > T2 > T3 > T4；Tier 9 依 C6 D 主訴對照表換算成護理師不可得時的預設等級。
限制：單一 slot 擾動不檢查與開場白的邏輯一致性（例如「今天第一次」卻答「三週前開始」），
  因此 de-escalating 清單可能含不可能的組合；escalating 清單用於安全指標。

用法：
  python -m sim.decisive            # 列出 YAML 與計算結果的差異
  python -m sim.decisive --write    # 以計算結果改寫兩份情境檔的 decisive_questions
"""
from __future__ import annotations

import argparse
import re
from typing import Any

from acs_triage.loaders import DATA_DIR, questions, slot_defs
from acs_triage.pathway import tier9_fallback
from acs_triage.prompter.prompter import _relevant  # 與 Prompter 共用同一套相關性規則
from acs_triage.rules import RulesEngine, SlotState
from acs_triage.schemas import Question

# duration 型 slot 的代表答案（涵蓋規則門檻兩側）
DURATION_VALUES: dict[str, list[Any]] = {
    "pattern_unchanged_duration_months": [1, 6, 24],   # 門檻 6 個月（§5.6）
    "onset_weeks_ago": [1, 3],                          # 門檻 2 週（DV-2）
    "episode_duration_min": [5, 25],                    # Q-07 未裁定，目前不影響等級
    "recent_pci_months": [1, 36],
}

_ENGINE = RulesEngine()


def answer_values(q: Question) -> list[Any]:
    if q.answer_type == "yes_no":
        return [True, False]
    if q.answer_type == "choice":
        return list(slot_defs()[q.slot_id]["choices"])
    if q.answer_type == "duration":
        return DURATION_VALUES[q.slot_id]
    raise ValueError(f"unsupported answer_type: {q.answer_type}")


def _outcome(slots: dict[str, Any]) -> tuple[int, bool]:
    d = _ENGINE.decide(SlotState(slots))
    return d.provisional_tier, d.hard_stop


def urgency(slots: dict[str, Any]) -> int:
    """數字越小越急：Hard stop = -1；T0–T4 = 0–4；Tier 9 → C6 D 預設等級。"""
    s = SlotState(slots)
    d = _ENGINE.decide(s)
    if d.hard_stop:
        return -1
    return tier9_fallback(s)[0] if d.provisional_tier == 9 else d.provisional_tier


def classify(slots: dict[str, Any]) -> dict[str, set[str]]:
    """回傳 {question_id: {"up", "down"} 的子集}；只含決定性題目。"""
    out: dict[str, set[str]] = {}
    for q in questions():
        base = {k: v for k, v in slots.items() if k != q.slot_id}
        if not _relevant(q, SlotState(base)):
            continue
        outcomes = {_outcome({**base, q.slot_id: v}) for v in answer_values(q)}
        if len(outcomes) <= 1:
            continue
        truth = urgency({**base, q.slot_id: slots.get(q.slot_id)})
        alts = [urgency({**base, q.slot_id: v}) for v in answer_values(q)]
        dirs = ({"up"} if any(u < truth for u in alts) else set()) | ({"down"} if any(u > truth for u in alts) else set())
        out[q.id] = dirs
    return out


def decisive_for(slots: dict[str, Any]) -> list[str]:
    return list(classify(slots))


def escalating_for(slots: dict[str, Any]) -> list[str]:
    return [qid for qid, dirs in classify(slots).items() if "up" in dirs]


# ---------------------------------------------------------------- CLI
_FILES = {"v0.2": DATA_DIR / "scenarios_v0.2.yaml", "midband": DATA_DIR / "scenarios_midband_v0.1.yaml"}


def _computed_by_scenario() -> dict[str, list[str]]:
    from .cases import all_cases
    return {c.id: c.decisive_questions for c in all_cases() if not c.is_variant}


def _rewrite(path, computed: dict[str, list[str]]) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for sid, qids in computed.items():
        m = re.search(rf"^  - id: {re.escape(sid)}\n", text, flags=re.M)
        if not m:
            continue
        start = m.end()
        nxt = re.search(r"^  - id: ", text[start:], flags=re.M)
        end = start + nxt.start() if nxt else len(text)
        block = text[start:end]
        new_block, k = re.subn(r"^    decisive_questions: \[.*\]$",
                               f"    decisive_questions: [{', '.join(qids)}]", block, count=1, flags=re.M)
        assert k == 1, sid
        text = text[:start] + new_block + text[end:]
        n += 1
    path.write_text(text, encoding="utf-8")
    return n


def main() -> None:
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    computed = _computed_by_scenario()
    for name, path in _FILES.items():
        listed = {sc["id"]: sc.get("decisive_questions", []) for sc in yaml.safe_load(path.read_text(encoding="utf-8"))["scenarios"]}
        for sid, old in listed.items():
            new = computed[sid]
            rm = [q for q in old if q not in new]
            add = [q for q in new if q not in old]
            flag = "" if not (rm or add) else "  ←"
            print(f"{sid:<12} 舊 {len(old)} → 新 {len(new)}  刪 {rm}  增 {add}{flag}")
        if args.write:
            print(f"rewrote {_rewrite(path, {k: v for k, v in computed.items() if k in listed})} scenarios in {path.name}")


if __name__ == "__main__":
    main()
