"""D-27：decisive／escalating 題目的反事實定義與情境檔紀錄一致。"""
import pytest
import yaml

from acs_triage.loaders import DATA_DIR
from sim.cases import all_cases
from sim.decisive import classify

BASE = {c.id: c for c in all_cases() if not c.is_variant}


@pytest.mark.parametrize("fname", ["scenarios_v0.2.yaml", "scenarios_midband_v0.1.yaml"])
def test_yaml_matches_computed(fname):
    """規則或問題庫一改，YAML 記錄就要用 `python -m sim.decisive --write` 重算。"""
    d = yaml.safe_load((DATA_DIR / fname).read_text(encoding="utf-8"))
    for sc in d["scenarios"]:
        assert sc["decisive_questions"] == BASE[sc["id"]].decisive_questions, sc["id"]


def test_examples_follow_definition():
    acute = classify(BASE["S-ACUTE-01"].slots)
    assert "Q-REST-01" not in acute                 # 已 T0：休息時症狀不改變結果
    assert acute["Q-ONGOING-01"] == {"up"}          # 仍持續 → Hard stop
    assert "down" in acute["Q-TIMING-01"]           # 昨天 → T1（DV-1）
    stable = classify(BASE["S-STABLE-01"].slots)
    assert stable["Q-REST-01"] == {"up"} and stable["Q-THRESHOLD-01"] == {"up"}
    assert "Q-DURATION-01" not in stable            # Q-07 未裁定，持續時間不影響等級


def test_escalating_subset_of_decisive():
    for c in all_cases():
        assert set(c.escalating_questions) <= set(c.decisive_questions), c.id
