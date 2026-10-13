"""M2 端到端：ScriptedPatient 對話 → final tier 與 truth 比對（BLUEPRINT §6.3、§11 M2 驗收）。"""
import pytest

from sim.cases import all_cases
from sim.run_eval import run_all


@pytest.fixture(scope="module")
def clean():
    return run_all("clean", seed=0)


def test_case_expansion_counts():
    cases = all_cases()
    assert len(cases) == 119
    assert sum(1 for c in cases if not c.is_variant) == 38
    assert sum(1 for c in cases if c.truth_tier is None) == 3


def test_clean_hard_stop_safety(clean):
    _, m = clean
    assert m.hard_stop_truth == 27
    assert m.hard_stop_miss == []
    assert m.hard_stop_false_alarm == []
    assert m.hard_stop_latency_max == 0
    assert m.rf_mismatch == []


# Q-14b 讓胸部症狀定案前須排除三個 T0 觸發因子；PCI＋模糊開場的穩定型需 11 題，
# max_questions=10 時 S-INSUF-02#1 以 Tier 9（轉護理師）結束。是否調為 11 待 Clinical Owner 裁定（Q-15）。
KNOWN_BUDGET_ABSTAIN = [("S-INSUF-02#1", 3)]
ESCALATING_FLOOR = 0.958   # D-28 基線 95.9%（510/532）


def test_clean_no_under_triage_and_exact(clean):
    _, m = clean
    assert m.under_triage == []
    assert m.over_triage == []
    assert m.abstain_fp == KNOWN_BUDGET_ABSTAIN and m.abstain_fn == []
    assert m.exact == m.n_scored - len(KNOWN_BUDGET_ABSTAIN)


def test_clean_insufficient_group_abstains(clean):
    results, _ = clean
    base_insuf = [r for r in results if r.module == "insufficient" and not r.is_variant]
    assert len(base_insuf) == 8
    assert all(r.final.tier == 9 for r in base_insuf)
    assert all(r.stop_reason == "max_questions" for r in base_insuf)


def test_clean_escalating_recall_floor(clean):
    """D-27 基線 86.5%（455/526）→ Q-14 a/b/c/e/f/g 後見 D-28。目標 ≥ 90%；此測試防退步。"""
    _, m = clean
    assert m.escalating_recall >= ESCALATING_FLOOR


def test_vague_mode_never_under_triages_or_misses_hard_stop():
    _, m = run_all("vague", seed=0)
    assert m.hard_stop_miss == [] and m.hard_stop_latency_max == 0
    assert m.under_triage == []
    assert len(m.abstain_fp) > 0          # 不知道 → 轉護理師，是預期行為


def test_low_stt_gate_repeats_without_changing_outcome(clean):
    _, m_clean = clean
    _, m = run_all("low_stt", seed=0)
    assert m.repeats > 0
    assert m.exact_rate == m_clean.exact_rate
    assert m.hard_stop_miss == [] and m.under_triage == []
