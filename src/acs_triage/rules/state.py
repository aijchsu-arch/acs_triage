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
        if self.get(slot_id) != value:
            # 來源值改變（含變體把它設回未知）→ 由它衍生、且之後未被明確回答的值失去依據，一併清除
            prefix = f"derived:{slot_id}="
            for k in [k for k, sv in self._values.items() if (sv.source_segment_id or "").startswith(prefix)]:
                del self._values[k]
        self._values[slot_id] = SlotValue(slot_id=slot_id, value=value, confidence=confidence,
                                          source_segment_id=source, asked_by_question_id=asked_by)
        self._derive(slot_id, value, source)

    def _derive(self, slot_id: str, value: Any, source: str | None) -> None:
        """病人明確陳述帶出的衍生：只填尚未知的 slot。
        否認 → 往「無此症狀」方向推；唯一例外是病人自己說「現在還在發作」（Q-14g）→ ongoing_now=True（升級方向）。"""
        derived: dict[str, Any] = {}
        if slot_id == "dyspnea_grade" and value == "none":
            derived = {"dyspnea_acute": False, "orthopnea_pnd": False, "cant_finish_sentence": False,
                       "dyspnea_complaint": False}
        elif slot_id == "symptom_character" and value == "none":
            derived = {"ongoing_now": False}
        elif slot_id == "consult_screen_positive" and value is False:
            derived = {"palpitations": False, "postural_dizziness": False, "pending_abnormal_test": False}
        elif slot_id == "last_episode_timing" and value == "ongoing":
            derived = {"ongoing_now": True}
        for k, v in derived.items():
            if self.get(k) is None:
                self._values[k] = SlotValue(slot_id=k, value=v, confidence=0.9,
                                            source_segment_id=f"derived:{slot_id}={value}")

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
        return ((g is not None and g != "none") or self.is_true("dyspnea_acute") or self.is_true("orthopnea_pnd")
                or (self.is_true("dyspnea_complaint") and g != "none"))

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
