from acs_triage.extract import extract
from acs_triage.pathway import route, script_text, tier9_fallback
from acs_triage.prompter import Prompter
from acs_triage.rules import RulesEngine, SlotState


def test_prompter_asks_redflag_first_for_chest_complaint(engine):
    s = SlotState(extract("最近有時胸口悶一下，但沒有特別記時間。"))
    q = Prompter().next_question(s)
    assert q is not None and q.priority == "redflag" and q.slot_id in ("ongoing_now", "presyncope", "diaphoresis", "episode_duration_min")


def test_prompter_skips_known_slots_and_eventually_exhausts():
    s = SlotState(extract("我有冠心症，快走上坡時偶爾胸悶，這個情況兩年來都一樣，最近沒有任何變化。"))
    p = Prompter()
    asked = set()
    for _ in range(40):
        q = p.next_question(s, asked=asked)
        if q is None:
            break
        asked.add(q.id)
        assert not s.known(q.slot_id)
        s.set(q.slot_id, False if q.answer_type == "yes_no" else (q.choices[0] if q.choices else 0), source="t")
    assert q is None


def test_prompter_dyspnea_grade_asked_for_dyspnea_complaint():
    s = SlotState(extract("最近覺得比較喘，但不知道是不是心臟。"))
    q = Prompter().next_question(s)
    assert q is not None and q.slot_id == "dyspnea_grade"


def test_pathway_hard_stop_and_tiers(engine):
    eng = RulesEngine()
    hs = eng.decide(SlotState({"symptom_character": "pressure", "presyncope": True}))
    p = route(hs, SlotState({}))
    assert p.tier == "hard_stop" and p.script_id == "S-HS" and p.safety_net_script_id is None
    t4 = eng.decide(SlotState({"consult_topic": "medication_handling", "symptom_character": "none",
                               "dyspnea_grade": "none", "presyncope": False, "consult_screen_positive": False}))
    p4 = route(t4, SlotState({}))
    assert p4.tier == 4 and p4.safety_net_script_id == "S-SN-A"
    assert script_text(p4.script_id)


def test_pathway_t3_expedite_script(engine):
    eng = RulesEngine()
    s = SlotState({"antiplatelet_interrupted": True, "symptom_character": "none", "dyspnea_grade": "none",
                   "presyncope": False, "consult_screen_positive": False})
    d = eng.decide(s)
    p = route(d, s)
    assert p.tier == 3 and "expedite" in p.actions and p.script_id == "S-T3-EXPEDITE"


def test_tier9_fallback_table():
    assert tier9_fallback(SlotState({"symptom_character": "vague"})) == (1, [])
    assert tier9_fallback(SlotState({"dyspnea_grade": "exertional_daily"})) == (1, [])
    assert tier9_fallback(SlotState({"palpitations": True})) == (2, [])
    assert tier9_fallback(SlotState({"third_party_call": True, "patient_reachable": False})) == (1, ["family_relay_safety_net"])
    assert tier9_fallback(SlotState({"consult_topic": "medication_handling"})) == (3, [])


def test_tier9_route_nurse_unavailable():
    eng = RulesEngine()
    s = SlotState(extract("我有冠心症，最近胸口有時候怪怪的，想問要不要提早看醫生。"))
    d = eng.decide(s)
    assert d.tier == 9
    p = route(d, s, nurse_available=False)
    assert p.tier == 1 and "tier9_fallback_nurse_unavailable" in p.actions
    p2 = route(d, s, nurse_available=True)
    assert p2.tier == 9 and p2.script_id == "S-T9"
