"""D-42：單一答案翻轉敏感度的回歸門檻。嚴重降級（Hard stop／T0 → T1–T4）不得比基線多。"""
import pytest

from sim.robustness import flip_sensitivity
from sim.run_eval import run_all


@pytest.fixture(scope="module")
def sens():
    results, _ = run_all("clean", seed=0)
    return flip_sensitivity(results)


SEVERE_BASELINE = 8          # 2026-10-18 基線：8 次，全部來自 Q-CHARACTER-01（rules 0.5.1）


def test_severe_downgrades_not_worse_than_baseline(sens):
    assert len(sens["severe"]) <= SEVERE_BASELINE, sens["severe"]


def test_severe_downgrades_only_from_known_question(sens):
    # 若出現新的單點故障題目，必須被看見並記入 DECISIONS，而不是默默通過
    assert {e["question_id"] for e in sens["severe"]} <= {"Q-CHARACTER-01"}, sens["severe"]


def test_every_redflag_yes_is_single_point_of_failure(sens):
    # 規則的性質：紅旗題答「有」被聽成「沒有」一定降級；此測試記錄這個事實，供 M4 設計確認機制
    for q, c in sens["redflag_yes_to_no"].items():
        assert c["downgraded"] == c["turns"], (q, c)
