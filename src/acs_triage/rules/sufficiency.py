"""§5.9 Sufficiency Gate：provisional tier 要定案，哪些 slot 必須已確認（非 None）。

回傳仍缺的 slot 清單；空 → gate 通過。
"""
from __future__ import annotations

from .state import SlotState

CHEST_REDFLAG = ["ongoing_now", "presyncope", "diaphoresis"]
DYSPNEA_REDFLAG = ["dyspnea_grade", "cant_finish_sentence"]
CHEST_CONTEXT = ["rest_symptom", "ongoing_now", "diaphoresis", "presyncope"]
DYSPNEA_CONTEXT = ["dyspnea_grade", "cant_finish_sentence", "orthopnea_pnd", "dyspnea_acute"]
T0_TRIGGERS_CHEST = ["rest_symptom", "threshold_decreased", "ntg_use_increased"]        # Q-14b
CONSULT_SCREEN = ["palpitations", "postural_dizziness", "pending_abnormal_test"]          # Q-14f

RULE_REQUIREMENTS: dict[str, list[str]] = {
    # T0
    # T0 的 gate 不會把 final 降下來（provisional 0 → final 0），只決定 Prompter 還要問什麼：
    # 紅旗題（偵測 hard stop）＋能把等級往下修正的時序題（DV-1／C3 B）。
    "T0-NEW-TODAY": CHEST_REDFLAG + ["last_episode_timing"],
    "T0-THRESHOLD-DAYS": CHEST_REDFLAG + ["threshold_decrease_timescale"],
    "T0-REST-NEW": CHEST_REDFLAG,
    "T0-DYSPNEA-ACUTE": DYSPNEA_REDFLAG,
    "T0-NTG-INCREASED": CHEST_REDFLAG,
    "T0-ORTHOPNEA": DYSPNEA_REDFLAG,
    # T1
    "T1-NEW-YESTERDAY": CHEST_CONTEXT + ["last_episode_timing"],
    "T1-THRESHOLD-WEEKS": CHEST_CONTEXT + ["threshold_decrease_timescale"],
    "T1-PENDING-TEST": ["symptom_character", "dyspnea_grade", "presyncope"],
    "T1-ANTIPLT-SYMPTOMATIC": CHEST_CONTEXT,
    # T2
    "T2-NEW-OVER24H": CHEST_CONTEXT + ["recurrence"],
    "T2-NEW-STABLE-WEEKS": CHEST_CONTEXT + ["onset_weeks_ago", "threshold_decreased"],
    "T2-DYSPNEA-DAILY": DYSPNEA_CONTEXT + ["symptom_character"],
    "T2-POSTURAL-NEWMED": ["symptom_character", "presyncope", "dyspnea_grade", "new_medication_recent"],
    # T3
    "T3-STABLE": [],  # 動態：見 missing_for
    "T3-ADMIN": ["consult_topic", "symptom_character", "dyspnea_grade", "presyncope"] + CONSULT_SCREEN,
    "T3-ANTIPLT-ASYMPTOMATIC": ["symptom_character", "dyspnea_grade", "presyncope"] + CONSULT_SCREEN,
    "T3-PALPITATIONS": ["symptom_character", "presyncope", "syncope", "dyspnea_grade"],
    "T3-POST-PCI-MILDER": CHEST_CONTEXT + ["threshold_decreased"],
    "T3-POSTPRANDIAL": ["ongoing_now", "diaphoresis", "exertion_relation", "presyncope"],
    "T3-MECHANICAL": ["ongoing_now", "diaphoresis", "exertion_relation", "presyncope"],
    "T3-COUGH": ["ongoing_now", "diaphoresis", "exertion_relation", "presyncope"],
    # T4
    "T4-CONSULT": ["consult_topic", "symptom_character", "dyspnea_grade", "presyncope"] + CONSULT_SCREEN,
}


def missing_for(state: SlotState, provisional: int, rule_ids: list[str]) -> list[str]:
    if provisional == 9:
        return []  # Tier 9 不需 gate；由 Prompter 決定是否還有可問之題
    required: list[str] = []
    for rid in rule_ids:
        for slot in RULE_REQUIREMENTS.get(rid, []):
            if slot not in required:
                required.append(slot)
    if "T3-STABLE" in rule_ids:
        if state.chest_symptom_present():
            required += [s for s in CHEST_CONTEXT + ["threshold_decreased", "dyspnea_acute"] if s not in required]
        else:
            required += [s for s in DYSPNEA_CONTEXT + ["presyncope"] if s not in required]
    # Q-14b：胸部症狀要定在 T1–T4 前，三個 T0 觸發因子必須已知
    if provisional in (1, 2, 3, 4) and state.chest_symptom_present():
        required += [s for s in T0_TRIGGERS_CHEST if s not in required]
    # Q-14c：第三方來電必須確認病人本人可及
    if state.is_true("third_party_call") and "patient_reachable" not in required:
        required.append("patient_reachable")
    # ND-05：已知 CAD／PCI 且有胸部症狀、provisional 在 1–3 → 必須確認抗血小板是否中斷（升級因子）
    if provisional in (1, 2, 3) and state.chest_symptom_present() and (state.is_true("pci_history") or state.is_true("cad_history")):
        if "antiplatelet_interrupted" not in required:
            required.append("antiplatelet_interrupted")
    missing = state.known_all(required)
    # 穩定型 T3 另需明確否認（不只是已知）
    if "T3-STABLE" in rule_ids:
        explicit = ["rest_symptom", "threshold_decreased", "dyspnea_acute"] if state.chest_symptom_present() else ["dyspnea_acute", "orthopnea_pnd"]
        for slot in explicit:
            if state.get(slot) is not False and slot not in missing:
                missing.append(slot)
    return missing
