"""RulesEngine：把 slot state 轉成 TierDecision（hard stop → provisional → gate → final）。

另提供 ND-01／ND-02 的程式層強制（merge_with_model、apply_ecg）。
"""
from __future__ import annotations

from ..loaders import rules_version
from ..schemas import ECGResult, TierDecision
from . import sufficiency, tiers
from .redflags import red_flag_hits
from .state import SlotState


class RulesEngine:
    def decide(self, state: SlotState) -> TierDecision:
        rf = red_flag_hits(state)
        if rf:
            return TierDecision(provisional_tier=0, tier=0, gate_passed=True, hard_stop=True,
                               rf_hits=rf, evidence=list(rf), missing=[], rules_version=rules_version())
        prov, rule_ids = tiers.provisional_tier(state)
        missing = sufficiency.missing_for(state, prov, rule_ids)
        gate_passed = not missing
        # provisional 0 永不因資訊不足而變成 9（不得降級精神）；gate 只驅動 Prompter 繼續問
        final = prov if (gate_passed or prov == 0) else 9
        evidence = list(rule_ids) + (["T9-GATE"] if not gate_passed else [])
        return TierDecision(provisional_tier=prov, tier=final, gate_passed=gate_passed, hard_stop=False,
                            rf_hits=[], evidence=evidence, missing=missing,
                            pathway_actions=tiers.pathway_actions_for(state, rule_ids),
                            rules_version=rules_version())

    # ------------------------------------------------------------- ND-01
    @staticmethod
    def merge_with_model(rules_decision: TierDecision, model_tier: int, model_confidence: float,
                         model_version: str) -> TierDecision:
        """模型輸出若比規則更不急（數字更大）→ 取規則結果並標記；更急則採模型（升級允許）。
        Hard stop 永遠不受模型影響。Tier 9 視為「未定」：模型不得把規則的 0–4 改成 9，也不得把規則的 9 降成 4。"""
        d = rules_decision.model_copy()
        d.source = "merged"
        if d.hard_stop:
            return d
        r = d.provisional_tier
        if model_tier == 9:
            # 模型棄答：不改變規則結果（規則 9 則維持 9）
            return d
        if r == 9:
            # 規則未定、模型給 0–4：只允許模型升級到 0／1（高急迫度），不允許 2–4（等同降級）
            if model_tier in (0, 1):
                d.provisional_tier = model_tier
                d.tier = model_tier if d.gate_passed else 9
                d.evidence.append(f"MODEL:{model_version}:{model_tier}")
            else:
                d.model_downgrade_blocked = True
            return d
        if model_tier > r:
            d.model_downgrade_blocked = True
            return d
        if model_tier < r:
            d.provisional_tier = model_tier
            d.tier = model_tier if d.gate_passed else 9
            d.evidence.append(f"MODEL:{model_version}:{model_tier}")
        return d

    # ------------------------------------------------------------- ND-02
    @staticmethod
    def apply_ecg(decision: TierDecision, ecg: ECGResult) -> TierDecision:
        """ECG 只能升級：final = min(symptom, ecg)。quality_ok=False 完全忽略。正常 ECG 不改變任何事。"""
        d = decision.model_copy()
        if not ecg.quality_ok or ecg.ecg_tier_suggestion is None:
            return d
        e = ecg.ecg_tier_suggestion
        if d.provisional_tier == 9 or e < d.provisional_tier:
            d.provisional_tier = e
            d.evidence.append(f"ECG:{e}")
        if d.tier == 9 or e < d.tier:
            d.tier = e
            d.gate_passed = True
        return d
