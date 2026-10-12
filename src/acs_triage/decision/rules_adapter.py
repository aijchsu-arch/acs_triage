"""把 RulesEngine 包成 DecisionModel：確定性、信心 1.0、永遠作為紅旗保底。"""
from __future__ import annotations

from ..loaders import rules_version
from ..rules import RulesEngine, SlotState
from ..schemas import Decision, TypedQuestion


class RulesDecisionModel:
    def __init__(self) -> None:
        self.engine = RulesEngine()
        self.model_version = f"rules-{rules_version()}"

    def decide(self, q: TypedQuestion) -> Decision:
        # context 為 slot dict 的 repr；Phase 0 只支援 tier 與 hard_stop 兩種問法
        import ast
        state = SlotState(ast.literal_eval(q.context) if q.context else {})
        d = self.engine.decide(state)
        if q.kind == "yes_no":
            return Decision(answer=d.hard_stop, confidence=1.0, model_version=self.model_version)
        return Decision(answer=d.provisional_tier, confidence=1.0, model_version=self.model_version)

    def decide_many(self, qs: list[TypedQuestion]) -> list[Decision]:
        return [self.decide(q) for q in qs]
