"""模型 tier 與規則 tier 合併（BLUEPRINT §3.7、CLINICAL_RULES §4 ND-01）。

ND-01：模型比規則引擎更不急 → 取規則結果並標記 model_downgrade_blocked。
急迫度：Hard stop／T0 = 0，T1–T4 = 1–4；Tier 9 依 C6 D 主訴對照表換算（護理師不可得時的預設等級）。
M3a 為 shadow 模式（D-36）：此函式只用來計算「若接進決策會如何」，分流結果仍由規則決定。
"""
from __future__ import annotations

from ..pathway.router import tier9_fallback
from ..rules.state import SlotState
from ..schemas import TierDecision


def urgency_rank(tier: int, state: SlotState) -> int:
    return tier9_fallback(state)[0] if tier == 9 else tier


def merge_tier(rules: TierDecision, model_tier: int, state: SlotState) -> TierDecision:
    r = urgency_rank(rules.tier, state)
    m = urgency_rank(model_tier, state)
    if m > r:
        return rules.model_copy(update={"source": "merged", "model_downgrade_blocked": True})
    if m < r and not rules.hard_stop:
        return rules.model_copy(update={"source": "merged", "tier": model_tier})
    return rules.model_copy(update={"source": "merged"})
