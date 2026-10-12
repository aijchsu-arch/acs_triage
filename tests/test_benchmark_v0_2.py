"""v0.2 的 18 個情境：只給開場白 → provisional_tier／hard_stop == truth（D-12）。"""
import pytest

from acs_triage import loaders
from helpers import decide_text

SCS = loaders.load_scenarios("v0.2")["scenarios"]


@pytest.mark.parametrize("sc", SCS, ids=[s["id"] for s in SCS])
def test_opening_only_matches_truth(engine, sc):
    d = decide_text(engine, sc["opening_zh"])
    assert d.provisional_tier == sc["truth_tier"], (sc["opening_zh"], d.evidence)
    assert d.hard_stop == sc["truth_hard_stop"], (sc["opening_zh"], d.rf_hits)
    if sc.get("reviewer_rf"):
        assert sc["reviewer_rf"] in d.rf_hits
