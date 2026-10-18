"""D-44：DV-5 不接受「說不上來」；症狀未定性（vague）→ T9 及其兩個例外；紅旗與非性質 T0 觸發不受影響。"""
from acs_triage.rules import RulesEngine, SlotState

E = RulesEngine()
POSTPRANDIAL = {"symptom_character": "epigastric", "postprandial_relieved": True, "ongoing_now": False, "diaphoresis": False,
                "cad_history": True, "last_episode_timing": "today"}


def _d(**slots):
    return E.decide(SlotState(slots))


def test_dv5_requires_explicit_rest_only():
    assert "T3-POSTPRANDIAL" in _d(**POSTPRANDIAL, exertion_relation="rest_only").evidence
    for v in ("unclear", "both", "exertion_only"):
        assert "T3-POSTPRANDIAL" not in _d(**POSTPRANDIAL, exertion_relation=v).evidence, v
    d = _d(**POSTPRANDIAL)                                   # 尚未問到：暫時適用，但定案前必問
    assert "T3-POSTPRANDIAL" in d.evidence and d.tier == 9 and "exertion_relation" in d.missing


def test_vague_goes_to_t9():
    d = _d(symptom_character="vague", onset_new=True, last_episode_timing="today", cad_history=True)
    assert d.provisional_tier == 9 and d.evidence == ["T9-VAGUE-CHARACTER"]


def test_vague_exception_b_new_and_exertional_is_ischemic_like():
    d = _d(symptom_character="vague", onset_new=True, exertion_relation="exertion_only", last_episode_timing="today")
    assert d.provisional_tier == 0 and "T0-NEW-TODAY" in d.evidence


def test_vague_exception_a_stable_pattern_t3_unless_new():
    stable = dict(symptom_character="vague", cad_history=True, pattern_unchanged_duration_months=24, rest_symptom=False,
                  threshold_decreased=False, dyspnea_acute=False, presyncope=False, syncope=False)
    assert _d(**stable, onset_new=False).provisional_tier == 3
    assert _d(**stable, onset_new=True).provisional_tier == 9            # 矛盾組合不走 A


def test_vague_non_character_t0_triggers_still_t0():
    for extra in ({"threshold_decreased": True, "threshold_decrease_timescale": "days"}, {"dyspnea_acute": True},
                  {"ntg_use_increased": True}, {"orthopnea_pnd": True}, {"rest_symptom": True}):
        d = _d(symptom_character="vague", **extra)
        assert d.provisional_tier == 0 and "T9-VAGUE-CHARACTER" not in d.evidence, extra


def test_vague_red_flags_unchanged():
    assert _d(symptom_character="vague", ongoing_now=True).hard_stop
    assert _d(symptom_character="vague", presyncope=True).hard_stop
    assert _d(symptom_character="vague", diaphoresis=True).hard_stop


def test_vague_third_party_unreachable_precedes():
    d = _d(symptom_character="vague", third_party_call=True, patient_reachable=False)
    assert d.provisional_tier == 9 and d.evidence == ["T9-THIRD-PARTY-UNREACHABLE"]
