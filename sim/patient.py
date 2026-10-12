"""模擬病人（Phase 0：腳本式、確定性、可重現）。

只回答被問到的事（slot 在 case.slots 內 → 回答該值；不在 → 「不知道」）。
persona:
- normal：照 sheet 回答。
- vague：紅旗題照 sheet 回答，決定性／修飾題一律「不知道」（用來測 Tier 9 節制）。
noise（可開關，seeded）：
- vague_p：以機率 p 把已知的非紅旗答案變成「不知道」。
- low_stt_p：以機率 p 把這句 utterance 標為低信心（runner 會先要求重說一次）。
LLM 扮演病人為 M2b（DECISIONS D-21），這裡只定介面。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Protocol

from acs_triage.schemas import Question

from .cases import Case

_ZH_CHOICE = {
    "today": "今天", "yesterday_within_24h": "昨天", "over_24h": "更早以前", "unknown": "不記得",
    "days": "這幾天", "weeks_to_month": "這幾個禮拜慢慢變的",
    "exertional_heavy": "只有很激烈的運動才會", "exertional_daily": "平常走路做家事就會", "rest": "坐著休息也會",
    "none": "沒有",
    "pressure": "像被壓住", "pain": "會痛", "tightness": "悶悶的", "jaw_shoulder_heaviness": "下顎和肩膀沉重",
    "epigastric": "上腹悶脹", "vague": "說不上來，就是怪怪的", "other": "其他",
    "exertion_only": "走路用力的時候才會，停下來就好", "rest_only": "休息的時候", "both": "走路會，休息也會", "unclear": "不太清楚",
    "milder": "比較輕", "same": "差不多", "worse": "比較重",
    "appointment_admin": "想問門診時間", "education_question": "想問回診前要注意什麼", "medication_handling": "想問藥怎麼吃",
    "minor_noncardiac": "一點小問題", "symptom": "身體有不舒服",
}


@dataclass
class PatientReply:
    value: Any            # slot 值；None = 不知道
    utterance_zh: str
    stt_confidence: float


class PatientSimulator(Protocol):
    def answer(self, q: Question) -> PatientReply: ...


class ScriptedPatient:
    def __init__(self, case: Case, *, seed: int = 0, vague_p: float = 0.0, low_stt_p: float = 0.0) -> None:
        self.case = case
        self.rng = random.Random(f"{case.id}:{seed}")
        self.vague_p = vague_p
        self.low_stt_p = low_stt_p

    def _render(self, q: Question, value: Any) -> str:
        if value is None:
            return "不知道，我沒有注意。"
        if q.answer_type == "yes_no":
            return "有。" if value else "沒有。"
        if q.answer_type == "choice":
            return _ZH_CHOICE.get(str(value), str(value)) + "。"
        if q.answer_type == "duration":
            return f"大概{value}。"
        return str(value)

    def answer(self, q: Question) -> PatientReply:
        value = self.case.slots.get(q.slot_id)
        if self.case.persona == "vague" and q.priority != "redflag":
            value = None
        elif value is None and q.answer_type == "choice":
            # 一般病人對選擇題不會「不知道」到底：若該 slot 有 unknown 選項就答 unknown（「不記得」）
            from acs_triage.loaders import slot_defs
            if "unknown" in (slot_defs()[q.slot_id].get("choices") or []):
                value = "unknown"
        elif q.priority != "redflag" and self.vague_p > 0 and self.rng.random() < self.vague_p:
            value = None
        conf = 1.0
        if self.low_stt_p > 0 and self.rng.random() < self.low_stt_p:
            conf = 0.5
        return PatientReply(value=value, utterance_zh=self._render(q, value), stt_confidence=conf)
