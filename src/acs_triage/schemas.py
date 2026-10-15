"""Pydantic v2 資料模型 —— 對應 docs/BLUEPRINT.md §4。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Tier = Literal[0, 1, 2, 3, 4, 9]
Speaker = Literal["patient", "agent", "unknown"]
Priority = Literal["redflag", "decisive", "refine"]
AnswerType = Literal["yes_no", "choice", "duration", "free"]


class TranscriptSegment(BaseModel):
    id: str
    call_id: str
    speaker: Speaker
    text: str
    confidence: float = 1.0
    lang_hint: Literal["zh-TW", "nan-TW", "mixed", "unknown"] = "zh-TW"
    t_start: float = 0.0
    t_end: float = 0.0


class RedFlagHit(BaseModel):
    rf_id: str
    segment_id: str | None = None
    path: Literal["rules", "model", "both"] = "rules"
    model_p: float | None = None


class SlotValue(BaseModel):
    slot_id: str
    value: Any = None
    confidence: float = 1.0
    source_segment_id: str | None = None
    asked_by_question_id: str | None = None


class Question(BaseModel):
    id: str
    slot_id: str
    priority: Priority
    answer_type: AnswerType
    script_zh: str
    why_zh: str
    choices: list[str] | None = None
    ask_when: str = "always"


class TierDecision(BaseModel):
    provisional_tier: Tier
    tier: Tier
    gate_passed: bool
    hard_stop: bool
    rf_hits: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    evidence: list[str] = Field(default_factory=list)   # rule ids / slot ids
    missing: list[str] = Field(default_factory=list)    # slot ids still needed
    source: Literal["rules", "model", "merged"] = "rules"
    model_downgrade_blocked: bool = False
    pathway_actions: list[str] = Field(default_factory=list)
    rules_version: str = ""


class ECGResult(BaseModel):
    device_id: str
    quality_ok: bool
    ai_findings: list[str] = Field(default_factory=list)
    ecg_tier_suggestion: Literal[0, 1] | None = None


class Pathway(BaseModel):
    tier: Tier | Literal["hard_stop"]
    script_id: str
    actions: list[str]
    safety_net_script_id: str | None


class AuditEvent(BaseModel):
    ts: datetime
    call_id: str
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    rules_version: str = ""
    model_version: str | None = None


# ---- 決策模型抽象層（BLUEPRINT §5） ----
class TypedQuestion(BaseModel):
    kind: Literal["yes_no", "choice", "ordinal"]
    prompt: str
    choices: list[str] | None = None
    context: str = ""
    criteria: dict[str, str] | None = None   # M3a：Jev 需要每個選項／是否的說明


class Decision(BaseModel):
    answer: Any
    confidence: float
    model_version: str
    probabilities: dict[str, float] | None = None   # M3a：模型回傳的機率分布（noul 為 {"true": p}）
