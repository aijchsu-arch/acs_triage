"""D-45：Q-05 兩條新規則的邊界、gate 必問、T0 答不知道即定案。"""
from acs_triage.rules import RulesEngine, SlotState
from sim.cases import all_cases
from sim.patient import ScriptedPatient
from sim.runner import run_case

E = RulesEngine()


def _d(**slots):
    return E.decide(SlotState(slots))


HEAVY = dict(dyspnea_complaint=True, dyspnea_grade="exertional_heavy", dyspnea_acute=False, orthopnea_pnd=False,
             symptom_character="none", cant_finish_sentence=False)


def test_t2_dyspnea_heavy_and_stable_exclusion():
    assert _d(**HEAVY, pattern_unchanged_duration_months=1).provisional_tier == 2
    d = _d(**HEAVY, pattern_unchanged_duration_months=6, presyncope=False, syncope=False)
    assert d.provisional_tier == 3 and "T3-STABLE" in d.evidence            # ≥6 個月穩定 → T3（S-INSUF-04#2）
    assert _d(**{**HEAVY, "dyspnea_acute": True}).provisional_tier == 0       # 今日突發仍 T0
    assert "T2-DYSPNEA-HEAVY" not in _d(**{**HEAVY, "dyspnea_complaint": None}).evidence   # 非主訴喘不進此規則


REC = dict(symptom_character="tightness", cad_history=True, pattern_unchanged_duration_months=12, rest_symptom=True,
           rest_symptom_first_time=False, onset_new=False, ongoing_now=False, threshold_decreased=False,
           ntg_use_increased=False, presyncope=False, syncope=False, diaphoresis=False, dyspnea_grade="none")


def test_t3_stable_rest_recurrent_boundaries():
    assert _d(**REC).provisional_tier == 3
    assert _d(**{**REC, "rest_symptom_first_time": True}).provisional_tier == 0      # 首次 → T0-REST-NEW
    assert _d(**{**REC, "rest_symptom_first_time": None}).provisional_tier == 0      # 未答視同首次
    assert _d(**{**REC, "threshold_decreased": True, "threshold_decrease_timescale": "days"}).provisional_tier == 0
    assert _d(**{**REC, "ntg_use_increased": True}).provisional_tier == 0
    assert _d(**{**REC, "ongoing_now": True}).hard_stop                                # RF-03 不變
    d = _d(**{**REC, "threshold_decreased": None})                                    # 未知可暫時成立，但 gate 要明確否認
    assert d.provisional_tier == 3 and "threshold_decreased" in d.missing


def test_gate_asks_onset_before_t1_threshold_and_weeks_before_pci():
    d = _d(symptom_character="tightness", cad_history=True, threshold_decreased=True, threshold_decrease_timescale="weeks_to_month",
           rest_symptom=False, ongoing_now=False, diaphoresis=False, presyncope=False, ntg_use_increased=False)
    assert d.provisional_tier == 1 and "onset_new" in d.missing
    d = _d(symptom_character="tightness", pci_history=True, recent_pci_months=1, symptom_vs_pre_pci="milder", exertion_relation="exertion_only",
           rest_symptom=False, threshold_decreased=False, onset_new=True, ongoing_now=False, diaphoresis=False, presyncope=False,
           ntg_use_increased=False, last_episode_timing="unknown", antiplatelet_interrupted=False)
    assert d.provisional_tier == 3 and "onset_weeks_ago" in d.missing


def test_t0_settles_once_missing_questions_asked():
    """S-MID-13#3：sheet 無 rest_symptom_first_time（病人答不知道）→ T0 不拖到題數上限。"""
    c = next(x for x in all_cases() if x.id == "S-MID-13#3")
    r = run_case(c, patient=ScriptedPatient(c))
    assert r.final.tier == 0 and r.stop_reason == "gate_passed_t0_asked" and r.n_questions < 11
