"""中間帶 20 個情境：只給開場白 → provisional_tier／hard_stop == truth（D-13、D-17）。"""
import pytest

from acs_triage import loaders
from helpers import decide_text

SCS = loaders.load_scenarios("midband")["scenarios"]


@pytest.mark.parametrize("sc", SCS, ids=[s["id"] for s in SCS])
def test_opening_only_matches_truth(engine, sc):
    d = decide_text(engine, sc["opening_zh"])
    assert d.provisional_tier == sc["truth_tier"], (sc["opening_zh"], d.evidence)
    assert d.hard_stop == sc["truth_hard_stop"], (sc["opening_zh"], d.rf_hits)
    if "expedite" in sc.get("pathway_actions", []):
        assert "expedite" in d.pathway_actions


def test_distribution():
    dist = {}
    for sc in SCS:
        dist[sc["truth_tier"]] = dist.get(sc["truth_tier"], 0) + 1
    assert dist == {0: 2, 1: 4, 2: 4, 3: 6, 4: 4}
