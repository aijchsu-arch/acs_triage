"""每個 boundary_variant：extract(opening) ∪ hidden_slots ∪ override → provisional／hard_stop／rf == expect。
expect.tier: null 的變體跳過並列印。"""
import pytest

from acs_triage import loaders
from acs_triage.extract import extract
from helpers import decide_slots

CASES = []
for sc in loaders.all_scenarios():
    for i, var in enumerate(sc.get("boundary_variants", [])):
        CASES.append(pytest.param(sc, var, id=f"{sc['id']}#{i}"))


@pytest.mark.parametrize("sc,var", CASES)
def test_variant(engine, sc, var):
    exp = var["expect"]
    if exp.get("tier") is None:
        pytest.skip(f"{sc['id']} 變體目標 tier 未定：{var.get('note')}")
    slots = extract(var.get("opening_zh", sc["opening_zh"]))   # D-35：變體可帶專用開場白
    for k, v in sc.get("hidden_slots", {}).items():
        if v is not None:
            slots[k] = v
    slots.update(var["override"])  # override 的 null 強制設回 None
    d = decide_slots(engine, slots)
    assert d.provisional_tier == exp["tier"], (var, d.evidence, d.rf_hits)
    assert d.hard_stop == exp.get("hard_stop", False), (var, d.rf_hits)
    if exp.get("rf"):
        assert exp["rf"] in d.rf_hits, (var, d.rf_hits)


def test_variant_count():
    assert len(CASES) == 81   # D-35：刪除 S-MID-03#1、新增 S-MID-13#3
