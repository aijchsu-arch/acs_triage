"""§5 Tier 規則引擎（provisional：不經 sufficiency gate）。

每個條件函式回傳 rule_id（命中）或 None。rule_id 對應 data/clinical_rules.yaml 的 tier_rules，供稽核。
評估順序：T0 → §5.8 明確 Tier 9 → T1 → T2 → T3 → T4 → 否則 Tier 9。
未知（None）的處理原則：升級因子未知 → 視為不成立；但「新發且時序未知」→ 視為今天（T0-NEW-TODAY），
以敏感度優先；可降級的 carve-out 全部條件須為已知且成立才適用。
"""
from __future__ import annotations

from ..loaders import load_clinical_rules
from .state import SlotState, UNKNOWN_TIMESCALE


def _th(key: str):
    return load_clinical_rules()["thresholds"][key]


# ---------------------------------------------------------------- 型態述詞（owner 已確認之 carve-out）
def dv2_new_stable_weeks(s: SlotState) -> bool:
    """DV-2：新發勞累性、≥2 週、型態穩定、無休息、無閾值下降。"""
    w = s.get("onset_weeks_ago")
    return (s.is_true("onset_new") and w is not None and w >= _th("new_stable_pattern_min_weeks")
            and s.get("exertion_relation") == "exertion_only"
            and s.not_true("rest_symptom") and s.not_true("threshold_decreased"))


def dv4_post_pci_milder(s: SlotState) -> bool:
    """DV-4：PCI 後輕症較術前輕、純勞累、無休息、無閾值下降。"""
    return (s.get("symptom_vs_pre_pci") == "milder" and s.get("exertion_relation") == "exertion_only"
            and s.not_true("rest_symptom") and s.not_true("threshold_decreased"))


def dv5_postprandial(s: SlotState) -> bool:
    """DV-5：餐後脹氣、打嗝後完全緩解、非活動相關、無冒汗；Q-14e：僅限上腹不適（epigastric）。
    D-44：exertion_relation 明確答「說不上來」（unclear）不豁免——降級豁免須有明確證據；
    尚未問到（None）時暫時適用（provisional），定案前 sufficiency gate 會強制問到。"""
    return (s.get("symptom_character") == "epigastric"
            and s.is_true("postprandial_relieved") and s.is_false("ongoing_now")
            and s.get("exertion_relation") in (None, "rest_only") and s.not_true("diaphoresis"))


def mechanical(s: SlotState) -> bool:
    """可重現胸壁痛；Q-14e：僅限刺痛（pain），壓迫／悶／下顎肩膀沉重不適用。"""
    return (s.get("symptom_character") == "pain" and s.is_true("reproducible_mechanical")
            and s.get("exertion_relation") != "exertion_only")


def cough(s: SlotState) -> bool:
    """咳嗽相關胸痛；Q-14e：僅限刺痛（pain）。"""
    return (s.get("symptom_character") == "pain" and s.is_true("cough_related")
            and s.get("exertion_relation") != "exertion_only")


def _exertional_carveout(s: SlotState) -> bool:
    """勞累型豁免（DV-2 新發穩定 ≥2 週、DV-4 PCI 後較輕）。Q-14d C：明確今天／仍在發作 → 不豁免（T0）。"""
    return dv2_new_stable_weeks(s) or dv4_post_pci_milder(s)


def _nonischemic_carveout(s: SlotState) -> bool:
    """非缺血型豁免（刺痛可重現、刺痛咳嗽、上腹餐後；Q-14e 限縮）。Q-14d C：不論時序都適用。"""
    return dv5_postprandial(s) or mechanical(s) or cough(s)


# ---------------------------------------------------------------- T0
def t0_rules(s: SlotState) -> list[str]:
    hits: list[str] = []
    timing = s.get("last_episode_timing")
    timing_unknown = timing in (None, "unknown")
    if (s.chest_symptom_present() and s.is_true("onset_new") and (timing in ("ongoing", "today") or timing_unknown)
            and not _nonischemic_carveout(s)
            and not (_exertional_carveout(s) and timing_unknown)):
        hits.append("T0-NEW-TODAY")
    if s.is_true("threshold_decreased") and s.get("threshold_decrease_timescale") in (UNKNOWN_TIMESCALE | {"days"}):
        hits.append("T0-THRESHOLD-DAYS")
    if s.is_true("rest_symptom") and s.get("rest_symptom_first_time") is not False:
        hits.append("T0-REST-NEW")
    if s.is_true("dyspnea_acute"):
        hits.append("T0-DYSPNEA-ACUTE")
    if s.is_true("ntg_use_increased"):
        hits.append("T0-NTG-INCREASED")
    if s.is_true("orthopnea_pnd"):
        hits.append("T0-ORTHOPNEA")
    return hits


# ---------------------------------------------------------------- 明確 Tier 9（§5.8 前段）
def t9_explicit(s: SlotState) -> list[str]:
    hits: list[str] = []
    if s.is_true("third_party_call") and s.is_false("patient_reachable"):
        hits.append("T9-THIRD-PARTY-UNREACHABLE")
    return hits


# ---------------------------------------------------------------- T1
def t1_rules(s: SlotState) -> list[str]:
    hits: list[str] = []
    if (s.chest_symptom_present() and s.get("onset_new") is not False
            and s.get("last_episode_timing") == "yesterday_within_24h" and s.not_true("ongoing_now")
            and not _nonischemic_carveout(s)):
        hits.append("T1-NEW-YESTERDAY")
    if s.is_true("threshold_decreased") and s.get("threshold_decrease_timescale") == "weeks_to_month":
        hits.append("T1-THRESHOLD-WEEKS")
    if s.is_true("pending_abnormal_test") and s.no_symptoms():
        hits.append("T1-PENDING-TEST")
    if s.chest_symptom_present() and s.is_true("onset_new") and s.is_true("antiplatelet_interrupted"):
        hits.append("T1-ANTIPLT-SYMPTOMATIC")
    return hits


# ---------------------------------------------------------------- T2
def t2_rules(s: SlotState) -> list[str]:
    hits: list[str] = []
    if (s.chest_symptom_present() and s.get("onset_new") is not False
            and s.get("last_episode_timing") == "over_24h" and s.not_true("recurrence")
            and s.not_true("rest_symptom") and not _nonischemic_carveout(s)):
        hits.append("T2-NEW-OVER24H")
    if dv2_new_stable_weeks(s):
        hits.append("T2-NEW-STABLE-WEEKS")
    if (s.get("dyspnea_grade") == "exertional_daily" and s.not_true("dyspnea_acute")
            and s.not_true("orthopnea_pnd") and not s.chest_symptom_present()):
        hits.append("T2-DYSPNEA-DAILY")
    if (s.is_true("postural_dizziness") and s.is_true("new_medication_recent")
            and not s.chest_symptom_present() and s.not_true("presyncope")):
        hits.append("T2-POSTURAL-NEWMED")
    return hits


# ---------------------------------------------------------------- T3
def _no_escalators(s: SlotState) -> bool:
    return (s.not_true("rest_symptom") and s.not_true("threshold_decreased") and s.not_true("dyspnea_acute")
            and s.not_true("presyncope") and s.not_true("syncope") and s.not_true("ntg_use_increased")
            and s.not_true("orthopnea_pnd") and s.not_true("ongoing_now")
            and s.get("dyspnea_grade") != "rest")


def t3_rules(s: SlotState) -> list[str]:
    hits: list[str] = []
    months = s.get("pattern_unchanged_duration_months")
    if months is not None and months >= _th("stable_pattern_min_months") and _no_escalators(s):
        hits.append("T3-STABLE")
    if s.get("consult_topic") == "appointment_admin" and s.no_symptoms():
        hits.append("T3-ADMIN")
    if s.is_true("antiplatelet_interrupted") and s.no_symptoms():
        hits.append("T3-ANTIPLT-ASYMPTOMATIC")
    if (s.is_true("palpitations") and not s.chest_symptom_present()
            and s.not_true("presyncope") and s.not_true("syncope")):
        hits.append("T3-PALPITATIONS")
    if s.chest_symptom_present() and dv4_post_pci_milder(s):
        hits.append("T3-POST-PCI-MILDER")
    if dv5_postprandial(s):
        hits.append("T3-POSTPRANDIAL")
    if mechanical(s):
        hits.append("T3-MECHANICAL")
    if cough(s):
        hits.append("T3-COUGH")
    return hits


# ---------------------------------------------------------------- T4
def t4_rules(s: SlotState) -> list[str]:
    if (s.get("consult_topic") in ("education_question", "medication_handling", "minor_noncardiac")
            and s.no_symptoms()):
        return ["T4-CONSULT"]
    return []


# ---------------------------------------------------------------- provisional
def provisional_tier(s: SlotState) -> tuple[int, list[str]]:
    """回傳 (tier, rule_ids)。不含 hard stop 判斷（由 engine 先做）。"""
    h = t0_rules(s)
    # D-44（§5.8）：症狀未定性（vague）→ Tier 9，兩個例外（Clinical Owner 2026-10-18）：
    #   B. 新發且活動相關 → 視同缺血等價症狀，走一般規則（S-INSUF-06#0 維持 T0）
    #   A. 有明確穩定型態證據（T3-STABLE 成立）→ 可定案 T3（S-INSUF-01#1 維持 T3）
    # 其餘：T0-NEW-TODAY 以缺血等價症狀為前提、vague 不成立；不依賴症狀性質的 T0 觸發因子仍升 T0；紅旗不變。
    vague_ischemic_like = s.is_true("onset_new") and s.get("exertion_relation") == "exertion_only"
    if s.get("symptom_character") == "vague" and not vague_ischemic_like:
        h = [x for x in h if x != "T0-NEW-TODAY"]
        if h:
            return 0, h
        h = t9_explicit(s)
        if h:
            return 9, h
        if "T3-STABLE" in t3_rules(s):
            return 3, ["T3-STABLE"]
        return 9, ["T9-VAGUE-CHARACTER"]
    if h:
        return 0, h
    h = t9_explicit(s)
    if h:
        return 9, h
    for tier, fn in ((1, t1_rules), (2, t2_rules), (3, t3_rules), (4, t4_rules)):
        h = fn(s)
        if h:
            return tier, h
    return 9, ["T9-NO-RULE"]


def pathway_actions_for(s: SlotState, rule_ids: list[str]) -> list[str]:
    acts: list[str] = []
    if "T3-ANTIPLT-ASYMPTOMATIC" in rule_ids:
        acts.append("expedite")
    if "T9-THIRD-PARTY-UNREACHABLE" in rule_ids:
        acts.append("family_relay_safety_net")
    return acts
