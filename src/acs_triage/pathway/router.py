"""Pathway Router（§3.9 / CLINICAL_RULES §6）：tier → 流程、腳本、動作、safety net。"""
from __future__ import annotations

from ..loaders import load_clinical_rules, load_scripts
from ..rules.state import SlotState
from ..schemas import Pathway, TierDecision


def _complaint_category(s: SlotState) -> str:
    if s.is_true("third_party_call") and s.is_false("patient_reachable"):
        return "third_party_unreachable"
    if s.chest_symptom_present():
        return "chest_or_equivalent"
    if s.dyspnea_present():
        return "dyspnea_rest_excluded"
    if s.is_true("palpitations") or s.is_true("postural_dizziness"):
        return "palpitations_or_dizziness_no_chest"
    return "consult_no_symptoms"


def tier9_fallback(state: SlotState) -> tuple[int, list[str]]:
    """Tier 9 且護理師不可得 → 依主訴對照表（C6 D）。"""
    table = load_clinical_rules()["tier9_nurse_unavailable_fallback"]
    cat = _complaint_category(state)
    entry = table[cat]
    tier, actions = (int(entry["tier"]), [entry["extra_action"]]) if isinstance(entry, dict) else (int(entry), [])
    if state.is_true("pending_abnormal_test"):     # Clinical Owner 2026-10-22（rules 0.8.0）：異常檢查待追蹤 → 至少 T1（含 T9 備援）
        tier = min(tier, 1)
    return tier, actions


def route(decision: TierDecision, state: SlotState, *, nurse_available: bool = True) -> Pathway:
    pw = load_clinical_rules()["pathways"]
    if decision.hard_stop:
        p = pw["hard_stop"]
        return Pathway(tier="hard_stop", script_id=p["script"], actions=list(p["actions"]), safety_net_script_id=None)
    tier = decision.tier
    extra: list[str] = list(decision.pathway_actions)
    if tier == 9 and not nurse_available:
        fb_tier, fb_actions = tier9_fallback(state)
        p = pw[fb_tier]
        return Pathway(tier=fb_tier, script_id=p["script"],
                       actions=["tier9_fallback_nurse_unavailable", *p["actions"], *fb_actions, *extra],
                       safety_net_script_id=p.get("safety_net"))
    p = pw[tier]
    actions = list(p["actions"])
    for a in extra:
        if a in p.get("optional_actions", []) or a not in actions:
            actions.append(a)
    script = p["script"]
    if tier == 3 and "expedite" in actions:
        script = "S-T3-EXPEDITE"
    return Pathway(tier=tier, script_id=script, actions=actions, safety_net_script_id=p.get("safety_net"))


def script_text(script_id: str) -> str:
    return load_scripts()["scripts"][script_id]["text"]
