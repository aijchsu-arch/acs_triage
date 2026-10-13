"""Q-14 裁定（2026-10-13）a／b／c／e／f／g 的行為測試。"""
from acs_triage.loaders import question_by_id
from acs_triage.prompter import Prompter
from acs_triage.rules import RulesEngine, SlotState
from helpers import decide_slots

JAW_TODAY = {"symptom_character": "jaw_shoulder_heaviness", "onset_new": True, "last_episode_timing": "today",
             "ongoing_now": False, "presyncope": False, "diaphoresis": False}


def test_a_ntg_question_is_decisive():
    assert question_by_id()["Q-NTG-01"].priority == "decisive"


def test_b_chest_t1_t3_needs_t0_triggers_ruled_out(engine):
    s = {"symptom_character": "tightness", "onset_new": True, "last_episode_timing": "yesterday_within_24h",
         "ongoing_now": False, "presyncope": False, "diaphoresis": False, "rest_symptom": False}
    d = decide_slots(engine, s)
    assert d.provisional_tier == 1 and d.tier == 9
    assert set(d.missing) >= {"threshold_decreased", "ntg_use_increased"}
    d2 = decide_slots(engine, {**s, "threshold_decreased": False, "ntg_use_increased": False})
    assert d2.tier == 1


def test_c_third_party_needs_reachability(engine):
    s = {"third_party_call": True, "consult_topic": "medication_handling", "symptom_character": "none",
         "dyspnea_grade": "none", "presyncope": False, "consult_screen_positive": False}
    assert decide_slots(engine, s).tier == 9
    assert decide_slots(engine, {**s, "patient_reachable": True}).tier == 4


def test_e_carveouts_do_not_apply_to_jaw_or_pressure(engine):
    for extra in ({"reproducible_mechanical": True}, {"cough_related": True},
                  {"postprandial_relieved": True, "exertion_relation": "rest_only"}):
        assert decide_slots(engine, {**JAW_TODAY, **extra}).provisional_tier == 0, extra
        assert decide_slots(engine, {**JAW_TODAY, **extra, "symptom_character": "pressure"}).provisional_tier == 0, extra


def test_e_carveouts_still_apply_to_pain_and_epigastric(engine):
    pain = {**JAW_TODAY, "symptom_character": "pain", "exertion_relation": "unclear"}
    assert decide_slots(engine, {**pain, "reproducible_mechanical": True}).provisional_tier == 3
    assert decide_slots(engine, {**pain, "cough_related": True}).provisional_tier == 3
    epi = {**JAW_TODAY, "symptom_character": "epigastric", "postprandial_relieved": True, "exertion_relation": "rest_only"}
    assert decide_slots(engine, epi).provisional_tier == 3


def test_f_consult_screen_question_and_gate():
    s = SlotState({"consult_topic": "education_question", "symptom_character": "none", "dyspnea_grade": "none",
                   "presyncope": False})
    eng = RulesEngine()
    assert eng.decide(s).tier == 9                                     # 篩檢未問，不得定案
    q = Prompter().next_question(s, missing=eng.decide(s).missing)
    assert q is not None and q.id == "Q-SCREEN-01"
    s.set("consult_screen_positive", False)
    assert s.get("palpitations") is False and s.get("pending_abnormal_test") is False
    assert eng.decide(s).tier == 4
    chest = SlotState({"symptom_character": "tightness"})
    assert "Q-SCREEN-01" not in {qq.id for qq in [Prompter().next_question(chest, asked={"Q-ONGOING-01", "Q-SYNCOPE-01", "Q-DIAPH-01", "Q-DYSPNEA-GRADE-01"})] if qq}


def test_g_ongoing_timing_is_hard_stop(engine):
    d = decide_slots(engine, {"symptom_character": "pressure", "onset_new": True, "last_episode_timing": "ongoing"})
    assert d.hard_stop and "RF-03" in d.rf_hits
