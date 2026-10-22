"""rules 0.8.0（Clinical Owner 2026-10-22）：異常檢查待追蹤 → 至少 T1，不論有無症狀（CLINICAL_RULES §5.4、§5.8）。

更急的規則（Hard stop、T0）照常優先；有症狀者先照一般規則判（所屬規則的 sufficiency 題目照常問到），T2–T4 再提高到 T1；
T9 不改（繼續問），護理師不可得時的備援等級至少 T1。
"""
import dataclasses

from acs_triage.pathway.router import tier9_fallback
from acs_triage.rules import RulesEngine, SlotState
from sim.cases import all_cases
from sim.patient import ScriptedPatient
from sim.runner import run_case

E = RulesEngine()


def _decide(**slots):
    st = SlotState(slots)
    return E.decide(st), st


def test_asymptomatic_pending_test_is_t1_as_before():
    case = next(c for c in all_cases() if c.id == "S-MID-09")
    r = run_case(case, patient=ScriptedPatient(case))
    assert (r.final.tier, r.final.evidence) == (1, ["T1-PENDING-TEST"])


def test_symptomatic_t2_to_t4_raised_to_t1_keeping_original_rule():
    cases = {
        "T3-PALPITATIONS": dict(palpitations=True, symptom_character="none", dyspnea_grade="none", presyncope=False, syncope=False),
        "T2-POSTURAL-NEWMED": dict(postural_dizziness=True, new_medication_recent=True, symptom_character="none",
                                   dyspnea_grade="none", presyncope=False),
        "T2-DYSPNEA-DAILY": dict(dyspnea_grade="exertional_daily", dyspnea_acute=False, orthopnea_pnd=False,
                                 cant_finish_sentence=False, symptom_character="none"),
        "T3-STABLE": dict(symptom_character="tightness", onset_new=False, pattern_unchanged_duration_months=12,
                          rest_symptom=False, threshold_decreased=False, dyspnea_acute=False, ongoing_now=False),
    }
    for rule, slots in cases.items():
        d0, _ = _decide(**slots)
        assert rule in d0.evidence and d0.provisional_tier in (2, 3), rule          # 沒有待追蹤檢查：照舊
        d1, _ = _decide(**slots, pending_abnormal_test=True)
        assert d1.provisional_tier == 1 and rule in d1.evidence and "T1-PENDING-TEST" in d1.evidence, rule


def test_vague_stable_exception_also_raised():
    slots = dict(symptom_character="vague", onset_new=False, pattern_unchanged_duration_months=12, rest_symptom=False,
                 threshold_decreased=False, dyspnea_acute=False, ongoing_now=False)
    assert _decide(**slots)[0].provisional_tier == 3
    assert _decide(**slots, pending_abnormal_test=True)[0].provisional_tier == 1


def test_more_urgent_rules_still_win():
    d, _ = _decide(symptom_character="pressure", onset_new=True, last_episode_timing="today", pending_abnormal_test=True)
    assert d.provisional_tier == 0 and "T0-NEW-TODAY" in d.evidence
    d, _ = _decide(symptom_character="pressure", ongoing_now=True, pending_abnormal_test=True)
    assert d.hard_stop
    case = next(c for c in all_cases() if c.id == "S-MID-09#0")                   # 胸口壓迫、今天新發＋待追蹤檢查
    assert run_case(case, patient=ScriptedPatient(case)).final.tier == 0


def test_t9_stays_t9_with_fallback_at_least_t1():
    # 無規則成立（快昏倒、無胸部症狀）：仍判 T9 繼續問，備援 T3 → T1
    d, st = _decide(presyncope=True, symptom_character="none", dyspnea_grade="none", pending_abnormal_test=True)
    assert (d.provisional_tier, d.tier) == (9, 9) and tier9_fallback(st)[0] == 1
    st.set("pending_abnormal_test", False)
    assert tier9_fallback(st)[0] == 3
    # gate 未過而判 T9（心悸、症狀性質未問）：備援 T2 → T1
    d, st = _decide(palpitations=True, pending_abnormal_test=True)
    assert d.tier == 9 and d.provisional_tier == 1 and tier9_fallback(st)[0] == 1
    st.set("pending_abnormal_test", None)
    assert tier9_fallback(st)[0] == 2


def test_s_mid_09_presyncope_full_call_still_asks_syncope():
    """S-MID-09 若答「快昏倒」：照常追問是否真的昏過去（RF-05），問完仍資訊不足 → T9，備援 T1（改前 T3）。
    若把 T1-PENDING-TEST 直接改成不論有無症狀都成立，gate 會在問完快昏倒後就通過、不再追問昏倒（安全退步）。"""
    base = next(c for c in all_cases() if c.id == "S-MID-09")
    case = dataclasses.replace(base, id="S-MID-09+presyncope", slots={**base.slots, "presyncope": True, "syncope": False})
    r = run_case(case, patient=ScriptedPatient(case))
    asked = [t.question_id for t in r.turns]
    assert "Q-SYNCOPE-02" in asked and r.final.tier == 9 and not r.final.hard_stop
    assert tier9_fallback(r.final_state)[0] == 1


# ---------------------------------------------------------------- 有症狀暫判 T2–T4 → 定案前加問一次（Clinical Owner 2026-10-22）
PENDING_SENTENCE = "另外，上個月做的心臟超音波說有點異常，醫師叫我回診，我還沒掛到號。"   # 對 119 例開場白只多抽出 pending_abnormal_test


def _with_pending_opening(c):
    return dataclasses.replace(c, opening_zh=c.opening_zh + PENDING_SENTENCE,
                               slots={**c.slots, "pending_abnormal_test": True, "consult_screen_positive": True})


def test_extra_question_only_for_symptomatic_t2_to_t4_and_counts_toward_cap():
    from acs_triage.loaders import load_clinical_rules
    max_q = load_clinical_rules()["thresholds"]["max_questions"]
    asked = skipped = 0
    for c in all_cases():
        on = run_case(c, patient=ScriptedPatient(c))
        qs = [t.question_id for t in on.turns]
        if on.pending_test_asked:
            asked += 1
            assert qs[-1] == "Q-PENDINGTEST-01" and qs.count("Q-PENDINGTEST-01") == 1, c.id
            assert on.final.tier in (2, 3, 4) and not on.final.hard_stop and not on.final_state.no_symptoms(), c.id
            assert on.n_questions <= max_q
        if on.pending_test_skipped_at_cap:
            skipped += 1
            assert on.n_questions == max_q and "Q-PENDINGTEST-01" not in qs and on.final.tier in (2, 3, 4), c.id
        if on.final.hard_stop or on.final.tier in (0, 1, 9):
            assert not on.pending_test_asked, c.id                                  # Hard stop／T0／T1／T9 不加問
    assert asked == 20 and skipped == 2


def test_extra_question_yes_raises_to_t1():
    class SaysYes(ScriptedPatient):
        def answer(self, q):
            r = super().answer(q)
            if q.id == "Q-PENDINGTEST-01":
                self._said[q.id] = True
                return dataclasses.replace(r, value=True, utterance_zh="有。")
            return r
    raised = 0
    for c in all_cases():
        base = run_case(c, patient=ScriptedPatient(c))
        if not base.pending_test_asked:
            continue
        r = run_case(c, patient=SaysYes(c))
        assert (r.final.tier, r.final.hard_stop) == (1, False) and "T1-PENDING-TEST" in r.final.evidence, c.id
        assert r.n_questions == base.n_questions                                     # 答「有」之後不再追問
        raised += 1
    assert raised == 20


def test_cap_reached_keeps_original_result_not_t9():
    for cid in ("S-ACUTE-05#1", "S-INSUF-02#1"):
        c = next(x for x in all_cases() if x.id == cid)
        r = run_case(c, patient=ScriptedPatient(c))
        assert r.pending_test_skipped_at_cap and r.final.tier == 3 and r.stop_reason == "gate_passed", cid


def test_all_openings_with_pending_test():
    """假設情境：119 例開場白都補一句待追蹤檢查。Hard stop、T0、T1 不變；T2–T4 → T1；不因下限的必要 slot 撞上限變 T9
    （第四輪 S-MID-02：呼吸分級答不知道，下限曾套用 T1-PENDING-TEST 用來確認「無症狀」的必要 slot → T9）。"""
    lab = lambda r: "HS" if r.final.hard_stop else f"T{r.final.tier}"
    for c in all_cases():
        a, b = run_case(c, patient=ScriptedPatient(c)), run_case(_with_pending_opening(c), patient=ScriptedPatient(_with_pending_opening(c)))
        expect = {"T2": "T1", "T3": "T1", "T4": "T1"}.get(lab(a), lab(a))
        assert lab(b) == expect, (c.id, lab(a), lab(b))


def test_expedite_only_when_t3():
    """抗血小板中斷的提前門診只在 T3 附加；被待追蹤檢查下限提高到 T1 時不附（獨立驗收例：S-STABLE-02#0）。"""
    from acs_triage.pathway import route
    c = next(x for x in all_cases() if x.id == "S-STABLE-02#0")
    a = run_case(c, patient=ScriptedPatient(c))
    assert a.final.tier == 3 and "expedite" in a.final.pathway_actions and route(a.final, a.final_state).script_id == "S-T3-EXPEDITE"
    c2 = _with_pending_opening(c)
    b = run_case(c2, patient=ScriptedPatient(c2))
    assert b.final.tier == 1 and "expedite" not in b.final.pathway_actions
    assert "expedite" not in route(b.final, b.final_state).actions
