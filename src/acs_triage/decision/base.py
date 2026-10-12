"""DecisionModel 抽象層（BLUEPRINT §5）。Phase 0 只有 RulesEngine 實作；LLM／Jev adapter 為 M3。"""
from __future__ import annotations

from typing import Protocol

from ..schemas import Decision, TypedQuestion


class DecisionModel(Protocol):
    model_version: str

    def decide(self, q: TypedQuestion) -> Decision: ...

    def decide_many(self, qs: list[TypedQuestion]) -> list[Decision]: ...
