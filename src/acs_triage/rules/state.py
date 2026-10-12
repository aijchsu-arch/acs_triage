"""Slot state：所有 slot 的目前值（None = 未知）與來源。"""
from __future__ import annotations

from typing import Any, Iterable

from ..loaders import load_clinical_rules, slot_defs
from ..schemas import SlotValue

UNKNOWN_TIMESCALE = {None, "unknown"}


class SlotState:
    def __init__(self, initial: dict[str, Any] | None = None):
        self._defs = slot_defs()
        self._values: dict[str, SlotValue] = {}
        if initial:
            for k, v in initial.items():
                self.set(k, v, source="initial")

    # ---- 基本操作 ----
    def set(self, slot_id: str, value: Any, *, source: str | None = None,
            asked_by: str | None = None, confidence: float = 1.0) -> None:
        if slot_id not in self._defs:
            raise KeyError(f"unknown slot: {slot_id}")
        self._values[slot_id] = SlotValue(slot_id=slot_id, value=value, confidence=confidence,
                                          source_segment_id=source, asked_by_question_id=asked_by)

    def get(self, slot_id: str) -> Any:
        sv = self._values.get(slot_id)
        return None if sv is None else sv.value

    def known(self, slot_id: str) -> bool:
        return self.get(slot_id) is not None

    def update(self, values: dict[str, Any], *, source: str, skip_none: bool = False) -> None:
        for k, v in values.items():
            if v is None and skip_none:
                continue
            self.set(k, v, source=source)

    def as_dict(self) -> dict[str, Any]:
        return {k: sv.value for k, sv in self._values.items()}

    def copy(self) -> "SlotState":
        s = SlotState()
        s._values = {k: v.model_copy() for k, v in self._values.items()}
        return s

    def __getitem__(self, slot_id: str) -> Any:
        return self.get(slot_id)

    # ---- 衍生述詞（供規則使用） ----
    @property
    def rules(self) -> dict[str, Any]:
        return load_clinical_rules()

    def is_true(self, slot_id: str) -> bool:
        return self.get(slot_id) is True

    def not_true(self, slot_id: str) -> bool:
        return self.get(slot_id) is not True

    def is_false(self, slot_id: str) -> bool:
        return self.get(slot_id) is False

    def chest_symptom_present(self) -> bool:
        return self.get("symptom_character") in set(self.rules["chest_symptom_characters"])

    def ischemic(self) -> bool:
        return self.get("symptom_character") in set(self.rules["ischemic_characters"])

    def chest_denied(self) -> bool:
        return self.get("symptom_character") == "none"

    def dyspnea_present(self) -> bool:
        g = self.get("dyspnea_grade")
        return (g is not None and g != "none") or self.is_true("dyspnea_acute") or self.is_true("orthopnea_pnd")

    def dyspnea_denied(self) -> bool:
        return self.get("dyspnea_grade") == "none"

    def no_symptoms(self) -> bool:
        """無任何胸部／呼吸／心悸／暈厥類症狀（未知視為無，provisional 用）。"""
        return (not self.chest_symptom_present() and not self.dyspnea_present()
                and self.not_true("palpitations") and self.not_true("presyncope")
                and self.not_true("syncope") and self.not_true("postural_dizziness")
                and self.not_true("ongoing_now") and self.not_true("ntg_use_increased"))

    def symptoms_denied(self) -> bool:
        """三項否認皆已確認（final gate 用）。"""
        return self.chest_denied() and self.dyspnea_denied() and self.is_false("presyncope")

    def known_all(self, slot_ids: Iterable[str]) -> list[str]:
        """回傳尚未知的 slot。"""
        return [s for s in slot_ids if not self.known(s)]
