"""§5.9 Sufficiency Gate：provisional tier 要定案，哪些 slot 必須已確認（非 None）。

回傳仍缺的 slot 清單；空 → gate 通過。
"""
from __future__ import annotations

from .state import SlotState

CHEST_REDFLAG = ["ongoing_now", "presyncope", "diaphoresis"]
DYSPNEA_REDFLAG = ["dyspnea_grade", "cant_finish_sentence"]
CHEST_CONTEXT = ["rest_symptom", "ongoing_now", "diaphoresis", "presyncope"]
DYSPNEA_CONTEXT = ["dyspnea_grade", "cant_finish_sentence", "orthopnea_pnd", "dyspnea_acute"]

RULE_REQUIREMENTS: dict[str, list[str]] = {
    # T0
    "T0-NEW-TODAY": CHEST_REDFLAG,
    "T0-THRESHOLD-DAYS": CHEST_REDFLAG,
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
    "T3-STABLE": CHEST_CONTEXT + ["threshold_decreased", "dyspnea_acute"],
    "T3-ADMIN": ["consult_topic", "symptom_character", "dyspnea_grade", "presyncope"],
    "T3-ANTIPLT-ASYMPTOMATIC": ["symptom_character", "dyspnea_grade", "presyncope"],
    "T3-PALPITATIONS": ["symptom_character", "presyncope", "syncope", "dyspnea_grade"],
    "T3-POST-PCI-MILDER": CHEST_CONTEXT + ["threshold_decreased"],
    "T3-POSTPRANDIAL": ["ongoing_now", "diaphoresis", "exertion_relation", "presyncope"],
    "T3-MECHANICAL": ["ongoing_now", "diaphoresis", "exertion_relation", "presyncope"],
    "T3-COUGH": ["ongoing_now", "diaphoresis", "exertion_relation", "presyncope"],
    # T4
    "T4-CONSULT": ["consult_topic", "symptom_character", "dyspnea_grade", "presyncope"],
}


def missing_for(state: SlotState, provisional: int, rule_ids: list[str]) -> list[str]:
    if provisional == 9:
        return []  # Tier 9 不需 gate；由 Prompter 決定是否還有可問之題
    required: list[str] = []
    for rid in rule_ids:
        for slot in RULE_REQUIREMENTS.get(rid, []):
            if slot not in required:
                required.append(slot)
    missing = state.known_all(required)
    # 穩定型 T3 另需明確否認（不只是已知）
    if "T3-STABLE" in rule_ids:
        for slot in ("rest_symptom", "threshold_decreased", "dyspnea_acute"):
            if state.get(slot) is not False and slot not in missing:
                missing.append(slot)
    return missing
