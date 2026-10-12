"""§3 紅旗（slot 層）。條件定義讀自 data/clinical_rules.yaml 的 red_flags.when。"""
from __future__ import annotations

from ..loaders import load_clinical_rules
from .state import SlotState


def _when_matches(state: SlotState, when: dict) -> bool:
    for key, expected in when.items():
        if key == "chest_symptom_present":
            if state.chest_symptom_present() is not expected:
                return False
        elif key == "any_true":
            if not any(state.is_true(s) for s in expected):
                return False
        else:
            if state.get(key) != expected:
                return False
    return True


def red_flag_hits(state: SlotState) -> list[str]:
    hits: list[str] = []
    for rf in load_clinical_rules()["red_flags"]:
        if _when_matches(state, rf["when"]):
            hits.append(rf["id"])
    return hits
