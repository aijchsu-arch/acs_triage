"""中間帶 20 個情境：只給開場白 → provisional_tier／hard_stop == truth（D-13、D-17）。"""
import pytest

from acs_triage import loaders
from acs_triage.extract import extract
from acs_triage.rules import SlotState
from helpers import decide_text

SCS = loaders.load_scenarios("midband")["scenarios"]
# D-57（Clinical Owner 2026-11-18 採用 A）：關鍵詞命中的可重現胸壁痛只記旗標，要 Q-REPRO-01 直接答「會」才寫入。
# S-MID-14 重新定義：只給開場白 ≠ T3；開場白＋Q-REPRO-01 答「會」→ truth（T3）。
REPRO_CONFIRMED = {"S-MID-14"}


@pytest.mark.parametrize("sc", SCS, ids=[s["id"] for s in SCS])
def test_opening_only_matches_truth(engine, sc):
    if sc["id"] in REPRO_CONFIRMED:
        slots = extract(sc["opening_zh"])
        assert slots.get("reproducible_mechanical_mentioned") is True and "reproducible_mechanical" not in slots
        assert engine.decide(SlotState(slots)).provisional_tier != 3, sc["opening_zh"]      # 只給開場白 ≠ T3
        d = engine.decide(SlotState({**slots, "reproducible_mechanical": True}))         # Q-REPRO-01 答「會」
    else:
        d = decide_text(engine, sc["opening_zh"])
    assert d.provisional_tier == sc["truth_tier"], (sc["opening_zh"], d.evidence)
    assert d.hard_stop == sc["truth_hard_stop"], (sc["opening_zh"], d.rf_hits)
    if "expedite" in sc.get("pathway_actions", []):
        assert "expedite" in d.pathway_actions


def test_distribution():
    dist = {}
    for sc in SCS:
        dist[sc["truth_tier"]] = dist.get(sc["truth_tier"], 0) + 1
    assert dist == {0: 2, 1: 4, 2: 7, 3: 3, 4: 4}                 # D-56 R7：S-MID-08、S-MID-13、S-MID-16 truth 3 → 2（Clinical Owner 2026-11-16）
