"""Prompter（§3.5）：從固定問題庫選「下一題」給客服逐字唸。

選題規則（Phase 0）：
1. redflag 題優先，且只問與主訴相關者（胸部症狀 → 胸部紅旗題；呼吸困難 → 呼吸紅旗題）。
2. 其次是 sufficiency gate 列出的 missing slot 對應題。
3. 再其次是 decisive 題（相關者）。
4. 最後 refine 題。
已知 slot 的題跳過。每次只回傳一題。
"""
from __future__ import annotations

from ..loaders import question_by_id, questions
from ..rules.state import SlotState
from ..schemas import Question, TierDecision

# 題目相關性：哪些 slot 的題目只在特定情境下才問
_CHEST_ONLY = {"ongoing_now", "presyncope", "diaphoresis", "episode_duration_min", "last_episode_timing",
               "recurrence", "onset_new", "onset_weeks_ago", "threshold_decreased", "threshold_decrease_timescale",
               "rest_symptom", "rest_symptom_first_time", "exertion_relation", "ntg_use_increased",
               "episode_frequency_increased",
               "reproducible_mechanical", "cough_related", "postprandial_relieved", "symptom_vs_pre_pci",
               "nausea", "antiplatelet_interrupted"}
_CHEST_OR_DYSPNEA = {"pattern_unchanged_duration_months"}
_DYSPNEA_ONLY = {"cant_finish_sentence", "dyspnea_acute", "orthopnea_pnd", "edema"}
_SCREEN_UNDERLYING = {"palpitations", "postural_dizziness", "pending_abnormal_test"}   # Q-14f
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
    if slot == "consult_screen_positive" and (chest or s.dyspnea_present()):
        return False  # Q-14f：合併篩檢只用於無胸部／呼吸症狀的來電
    # dyspnea_grade：所有人都問一次（RF-02 篩檢；無症狀諮詢的 gate 也需要明確否認）
    return True


def _stated_vague(s: SlotState) -> bool:
    """性質 vague 只來自開場白或順口提到（不是直接回答，D-40）。"""
    sv = s._values.get("symptom_character")
    return sv is not None and sv.value == "vague" and sv.asked_by_question_id is None


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
            if state.get("symptom_character") in (None, "vague") and state.chest_symptom_present():
                rf.sort(key=lambda q: q.slot_id not in _CHEST_ONLY)    # D-54（裁定 #4、#15）：胸部紅旗題排在呼吸分級之前
            return rf[0]
        # D-54（H3，Clinical Owner 2026-11-03）：胸部症狀（含 vague、提過胸口）合併呼吸症狀 → 呼吸的 T0 因子題先問，不被題數上限擠掉
        if state.dyspnea_present() and state.chest_symptom_present():
            by_id = question_by_id()
            for qid in ("Q-DYSPNEA-ACUTE-01", "Q-ORTHO-01"):
                if qid not in asked and not state.known(by_id[qid].slot_id) and _relevant(by_id[qid], state):
                    return by_id[qid]
            # D-54（順序 D，Clinical Owner 2026-11-03）：性質未知或 vague 時接著問新發；確定不是新發 → 4 個胸部 T0 因子題接著先問
            # （新發今天這條不可能成立，性質題可延後）
            if state.get("symptom_character") in (None, "vague"):
                on = by_id["Q-ONSET-01"]
                if on.id not in asked and not state.known(on.slot_id) and _relevant(on, state):
                    return on
                if state.is_false("onset_new"):
                    for qid in ("Q-REST-01", "Q-NTG-01", "Q-THRESHOLD-01", "Q-FREQ-01"):
                        if qid not in asked and not state.known(by_id[qid].slot_id) and _relevant(by_id[qid], state):
                            return by_id[qid]
        # 2. gate 缺的 slot；Q-14f：無症狀來電的三項篩檢先問合併題，答「有」或「不知道」才逐項追問
        if any(sl in _SCREEN_UNDERLYING for sl in missing) and not state.known("consult_screen_positive"):
            scr = question_by_id()["Q-SCREEN-01"]
            if scr.id not in asked and _relevant(scr, state):
                return scr
        for slot in missing:
            for q in self._qs:
                if q.slot_id == slot and q.id not in asked and not state.known(slot):
                    return q
        # 3. decisive
        dec = candidates(self._by_priority["decisive"])
        # D-54（H3 的連帶處理）：vague 合併呼吸症狀、新發已確定、活動關係未知 → 先問活動題。D-44 例外 B（新發且活動相關視同缺血等價）
        # 由它決定；排在題庫順序會被呼吸題擠到上限之外（S-INSUF-06#0 加上會喘時 T0 → T9）
        if (state.get("symptom_character") == "vague" and state.dyspnea_present() and state.is_true("onset_new")
                and not state.known("exertion_relation") and "Q-EXERTION-01" not in asked):
            return question_by_id()["Q-EXERTION-01"]
        # D-54（裁定 #4、#5）：開場白或順口的 vague 仍問一次性質題：排在時序題之後（gate 必問題與基線問得到的題優先，還有題數才問得到）；
        # 有呼吸症狀時提前，因為呼吸類決定題會用掉題數，排後面就問不到性質（新發今天的壓迫會落 T9）
        by_id = question_by_id()
        if ("Q-CHARACTER-01" not in asked and _stated_vague(state)
                and not (dec and self._qs.index(dec[0]) <= self._qs.index(by_id["Q-TIMING-01"]) and not state.dyspnea_present())):
            return by_id["Q-CHARACTER-01"]
        if dec:
            return dec[0]
        # 4. refine
        ref = candidates(self._by_priority["refine"])
        return ref[0] if ref else None

    def character_followup_question(self, state: SlotState, decision: TierDecision, asked: set[str]) -> Question | None:
        """D-54（裁定 #15）：提過胸口不適但性質未知 → 胸部紅旗題問完後先問 Q-CHARACTER-01。Hard stop／T0 不加問（不得延誤送醫）；
        例外：T0 只靠 T0-NEW-TODAY → 仍要問（性質決定這條成不成立，如上腹餐後 carve-out），問不出來維持 T0。"""
        q = question_by_id()["Q-CHARACTER-01"]
        if state.known(q.slot_id) or not state.chest_symptom_present() or q.id in asked or decision.hard_stop:
            return None
        if decision.provisional_tier == 0 and not set(decision.evidence) <= {"T0-NEW-TODAY", "T9-GATE"}:
            return None
        if any(c.id not in asked and not state.known(c.slot_id) and _relevant(c, state) for c in self._by_priority["redflag"]):
            return None
        return q

    def vague_recheck_question(self, state: SlotState, decision: TierDecision, asked: set[str]) -> Question | None:
        """D-54（裁定 #4、#5）：gate 已通過，性質只來自開場白或順口的 vague → 還有題數就問一次性質題。Hard stop／T0 不加問；題數由呼叫端判斷。"""
        q = question_by_id()["Q-CHARACTER-01"]
        if _stated_vague(state) and q.id not in asked and not decision.hard_stop and decision.provisional_tier != 0:
            return q
        return None

    def pending_test_question(self, state: SlotState, decision: TierDecision, asked: set[str]) -> Question | None:
        """rules 0.8.0（Clinical Owner 2026-10-22）：有症狀、gate 已通過且暫判 T2–T4、「檢查異常待追蹤」仍未知且沒問過 →
        定案前加問一次（答「有」依 tiers.provisional_tier 的下限提高到 T1；答不知道照原結果定案）。
        Hard stop／T0／T1／T9 不加問（不得延誤送醫）；無症狀來電由 Q-14f 合併篩檢問到，不在此列。題數上限由呼叫端判斷。"""
        q = question_by_id()["Q-PENDINGTEST-01"]
        if (not decision.hard_stop and decision.gate_passed and decision.provisional_tier in (2, 3, 4)
                and not state.no_symptoms() and not state.known(q.slot_id) and q.id not in asked):
            return q
        return None
