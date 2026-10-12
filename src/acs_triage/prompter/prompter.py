"""Prompter（§3.5）：從固定問題庫選「下一題」給客服逐字唸。

選題規則（Phase 0）：
1. redflag 題優先，且只問與主訴相關者（胸部症狀 → 胸部紅旗題；呼吸困難 → 呼吸紅旗題）。
2. 其次是 sufficiency gate 列出的 missing slot 對應題。
3. 再其次是 decisive 題（相關者）。
4. 最後 refine 題。
已知 slot 的題跳過。每次只回傳一題。
"""
from __future__ import annotations

from ..loaders import questions
from ..rules.state import SlotState
from ..schemas import Question

# 題目相關性：哪些 slot 的題目只在特定情境下才問
_CHEST_ONLY = {"ongoing_now", "presyncope", "diaphoresis", "episode_duration_min", "last_episode_timing",
               "recurrence", "onset_new", "onset_weeks_ago", "threshold_decreased", "threshold_decrease_timescale",
               "rest_symptom", "rest_symptom_first_time", "exertion_relation", "ntg_use_increased",
               "reproducible_mechanical", "cough_related", "postprandial_relieved", "symptom_vs_pre_pci",
               "nausea", "antiplatelet_interrupted"}
_CHEST_OR_DYSPNEA = {"pattern_unchanged_duration_months"}
_DYSPNEA_ONLY = {"cant_finish_sentence", "dyspnea_acute", "orthopnea_pnd", "edema"}
_ALWAYS_REDFLAG = {"dyspnea_grade"}  # 呼吸分級：有呼吸主訴或未排除時都要問一次
_CONDITIONAL = {
    "rest_symptom_first_time": lambda s: s.is_true("rest_symptom"),
    "threshold_decrease_timescale": lambda s: s.is_true("threshold_decreased"),
    "onset_weeks_ago": lambda s: s.is_true("onset_new"),
    "recurrence": lambda s: s.get("last_episode_timing") in ("over_24h", "yesterday_within_24h"),
    "syncope": lambda s: s.is_true("presyncope") or s.is_true("postural_dizziness"),
    "patient_reachable": lambda s: s.is_true("third_party_call"),
    "symptom_vs_pre_pci": lambda s: s.is_true("pci_history") and s.chest_symptom_present(),
    "recent_pci_months": lambda s: s.is_true("pci_history"),
    "antiplatelet_interrupted": lambda s: s.is_true("pci_history") or s.is_true("cad_history"),
    "new_medication_recent": lambda s: s.is_true("postural_dizziness"),
    "pattern_unchanged_duration_months": lambda s: s.get("onset_new") is not True,
}


def _relevant(q: Question, s: SlotState) -> bool:
    slot = q.slot_id
    chest = s.chest_symptom_present()
    if slot in _CONDITIONAL and not _CONDITIONAL[slot](s):
        return False
    if slot in _CHEST_ONLY and not chest:
        return False
    if slot in _CHEST_OR_DYSPNEA and not (chest or s.dyspnea_present()):
        return False
    if slot in _DYSPNEA_ONLY and not s.dyspnea_present():
        return False
    # dyspnea_grade：所有人都問一次（RF-02 篩檢；無症狀諮詢的 gate 也需要明確否認）
    return True


class Prompter:
    def __init__(self) -> None:
        self._qs = questions()
        self._by_priority = {p: [q for q in self._qs if q.priority == p] for p in ("redflag", "decisive", "refine")}

    def next_question(self, state: SlotState, missing: list[str] | None = None,
                      asked: set[str] | None = None) -> Question | None:
        asked = asked or set()
        missing = missing or []

        def candidates(qs: list[Question]) -> list[Question]:
            return [q for q in qs if q.id not in asked and not state.known(q.slot_id) and _relevant(q, state)]

        # 1. 紅旗題
        rf = candidates(self._by_priority["redflag"])
        if rf:
            return rf[0]
        # 2. gate 缺的 slot
        for slot in missing:
            for q in self._qs:
                if q.slot_id == slot and q.id not in asked and not state.known(slot):
                    return q
        # 3. decisive
        dec = candidates(self._by_priority["decisive"])
        if dec:
            return dec[0]
        # 4. refine
        ref = candidates(self._by_priority["refine"])
        return ref[0] if ref else None
