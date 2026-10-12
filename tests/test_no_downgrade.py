"""ND-01～ND-05 的程式層強制。"""
from acs_triage.rules import RulesEngine, SlotState
from acs_triage.schemas import ECGResult
from helpers import decide_slots, decide_text

BASE_T0 = {"symptom_character": "pressure", "onset_new": True, "last_episode_timing": "today",
           "ongoing_now": False, "presyncope": False, "diaphoresis": False}


def test_nd01_model_cannot_downgrade(engine):
    d = decide_slots(engine, BASE_T0)
    assert d.provisional_tier == 0
    m = RulesEngine.merge_with_model(d, model_tier=3, model_confidence=0.9, model_version="llm-test")
    assert m.provisional_tier == 0 and m.tier == 0 and m.model_downgrade_blocked


def test_nd01_model_may_upgrade(engine):
    d = decide_slots(engine, {"symptom_character": "tightness", "onset_new": True,
                              "last_episode_timing": "yesterday_within_24h", "ongoing_now": False,
                              "rest_symptom": False, "presyncope": False, "diaphoresis": False})
    assert d.provisional_tier == 1
    m = RulesEngine.merge_with_model(d, model_tier=0, model_confidence=0.8, model_version="llm-test")
    assert m.provisional_tier == 0 and not m.model_downgrade_blocked


def test_nd01_model_cannot_turn_tier9_into_low_urgency(engine):
    d = decide_slots(engine, {"symptom_character": "vague", "cad_history": True})
    assert d.provisional_tier == 9
    m = RulesEngine.merge_with_model(d, model_tier=4, model_confidence=0.95, model_version="llm-test")
    assert m.provisional_tier == 9 and m.model_downgrade_blocked


def test_nd01_hard_stop_immune_to_model(engine):
    d = decide_slots(engine, {"symptom_character": "pressure", "presyncope": True})
    assert d.hard_stop
    m = RulesEngine.merge_with_model(d, model_tier=3, model_confidence=1.0, model_version="llm-test")
    assert m.hard_stop and m.tier == 0


def test_nd02_ecg_only_upgrades(engine):
    d = decide_slots(engine, {"symptom_character": "tightness", "pattern_unchanged_duration_months": 24,
                              "rest_symptom": False, "threshold_decreased": False, "dyspnea_acute": False,
                              "ongoing_now": False, "presyncope": False, "diaphoresis": False})
    assert d.tier == 3
    up = RulesEngine.apply_ecg(d, ECGResult(device_id="x", quality_ok=True, ai_findings=["ST elevation"], ecg_tier_suggestion=0))
    assert up.tier == 0 and up.provisional_tier == 0
    normal = RulesEngine.apply_ecg(d, ECGResult(device_id="x", quality_ok=True, ai_findings=[], ecg_tier_suggestion=None))
    assert normal.tier == 3
    bad = RulesEngine.apply_ecg(d, ECGResult(device_id="x", quality_ok=False, ai_findings=["ST elevation"], ecg_tier_suggestion=0))
    assert bad.tier == 3, "訊號不佳必須完全忽略"


def test_nd02_ecg_cannot_downgrade_t0(engine):
    d = decide_slots(engine, BASE_T0)
    e = RulesEngine.apply_ecg(d, ECGResult(device_id="x", quality_ok=True, ai_findings=["normal"], ecg_tier_suggestion=1))
    assert e.provisional_tier == 0


def test_nd03_drug_attribution_does_not_downgrade(engine):
    d = decide_text(engine, "最近吃藥後偶爾覺得胸口不太舒服，想知道是不是藥物造成。")
    assert d.provisional_tier == 9
    d2 = decide_slots(engine, {"symptom_character": "pressure", "onset_new": True, "exertion_relation": "exertion_only",
                               "drug_time_correlation": True})
    assert d2.provisional_tier == 0


def test_nd04_ntg_effective_and_no_literal_pain_do_not_downgrade(engine):
    d = decide_text(engine, "我有冠心症，前天開始走路會胸悶，昨天含了一次舌下片有效，今天還沒發作，休息時沒有。")
    assert d.provisional_tier == 1
    d2 = decide_text(engine, "今天忽然喘得很明顯，和平常差很多，但胸口沒有痛。")
    assert d2.provisional_tier == 0


def test_nd05_cad_pci_alone_do_not_upgrade_but_interruption_matters(engine):
    stable = decide_text(engine, "三年前放過支架，之後一直都是很用力運動才有一點胸悶，半年內完全沒有變嚴重。")
    assert stable.provisional_tier == 3
    asympt = decide_text(engine, "放支架半年，上禮拜因為拔牙停了保栓通三天，還沒有不舒服，想問要不要趕快回去吃。")
    assert asympt.provisional_tier == 3 and "expedite" in asympt.pathway_actions
    sympt = decide_slots(engine, {"symptom_character": "tightness", "onset_new": True, "antiplatelet_interrupted": True,
                                  "symptom_vs_pre_pci": "milder", "exertion_relation": "exertion_only",
                                  "rest_symptom": False, "threshold_decreased": False})
    assert sympt.provisional_tier == 1
