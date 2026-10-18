"""D-43：紅旗題與 Q-CHARACTER-01 的 STT 信心門檻 0.9，其餘 0.75。"""
from acs_triage.loaders import load_clinical_rules, question_by_id
from sim.cases import all_cases
from sim.patient import PatientReply, ScriptedPatient
from sim.runner import run_case


class MidConfidencePatient(ScriptedPatient):
    """每句回答信心 0.8：介於一般門檻（0.75）與關鍵題門檻（0.9）之間。"""

    def answer(self, q):
        r = super().answer(q)
        return PatientReply(value=r.value, utterance_zh=r.utterance_zh, stt_confidence=0.8)


def test_thresholds_in_rules():
    th = load_clinical_rules()["thresholds"]
    assert th["stt_min_confidence"] == 0.75 and th["stt_min_confidence_critical"] == 0.9
    assert th["stt_critical_questions"] == ["Q-CHARACTER-01"]


def test_critical_questions_reasked_at_0_8_others_not():
    qb = question_by_id()
    seen_critical = seen_other = 0
    for c in all_cases():
        r = run_case(c, patient=MidConfidencePatient(c))
        for t in r.turns:
            critical = qb[t.question_id].priority == "redflag" or t.question_id == "Q-CHARACTER-01"
            assert t.repeated == critical, (c.id, t.question_id, t.repeated)
            seen_critical += critical
            seen_other += not critical
    assert seen_critical > 50 and seen_other > 50        # 兩類都有被覆蓋到


def test_results_unchanged_by_reask():
    """重問只影響流程（多問一次），不改變最終分流：與 clean 基線逐案相同。"""
    for c in all_cases():
        a = run_case(c, patient=MidConfidencePatient(c))
        b = run_case(c, patient=ScriptedPatient(c))
        assert (a.final.tier, a.final.hard_stop, [t.question_id for t in a.turns]) == \
               (b.final.tier, b.final.hard_stop, [t.question_id for t in b.turns]), c.id
