from acs_triage.extract import extract
from acs_triage.rules import RulesEngine, SlotState


def decide_text(engine: RulesEngine, text: str):
    return engine.decide(SlotState(extract(text)))


def decide_slots(engine: RulesEngine, slots: dict):
    return engine.decide(SlotState(slots))
