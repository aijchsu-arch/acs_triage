"""對話 runner：開場白 → 逐題問答 → 紅旗逐句檢查 → sufficiency → 最終 tier。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acs_triage.audit import AuditLog
from acs_triage.extract import extract
from acs_triage.loaders import load_clinical_rules
from acs_triage.pathway import route
from acs_triage.prompter import Prompter
from acs_triage.rules import RulesEngine, SlotState
from acs_triage.schemas import TierDecision

from .cases import Case
from .patient import PatientSimulator, ScriptedPatient


@dataclass
class Turn:
    question_id: str
    slot_id: str
    answer: Any
    utterance_zh: str
    stt_confidence: float
    repeated: bool = False


@dataclass
class RunResult:
    case_id: str
    scenario_id: str
    module: str
    is_variant: bool
    truth_tier: int | None
    truth_hard_stop: bool
    truth_rf: str | None
    final: TierDecision
    opening_decision: TierDecision
    turns: list[Turn] = field(default_factory=list)
    n_questions: int = 0
    n_repeats: int = 0
    hard_stop_turn: int | None = None          # 觸發 HS 時已問幾題（0 = 開場白即觸發）
    rf_reveal_turn: int | None = None          # 揭露 RF 事實的那一題（與 hard_stop_turn 相同 → latency 0）
    decisive_asked_or_known: int = 0
    decisive_total: int = 0
    escalating_asked_or_known: int = 0
    escalating_total: int = 0
    escalating_missed: list[str] = field(default_factory=list)
    escalating_missed_strict: list[str] = field(default_factory=list)   # D-42：推導值不算已知
    pathway_script: str = ""
    stop_reason: str = ""
    final_slots: dict[str, Any] = field(default_factory=dict)   # M3a：對話結束時的 slot 狀態
    final_state: Any = None                                      # D-42：含來源的 SlotState 副本（翻轉測試需保留推導語意）

    @property
    def hard_stop_latency(self) -> int | None:
        if self.hard_stop_turn is None or self.rf_reveal_turn is None:
            return None
        return self.hard_stop_turn - self.rf_reveal_turn


def run_case(case: Case, *, patient: PatientSimulator | None = None, engine: RulesEngine | None = None,
             prompter: Prompter | None = None, audit: AuditLog | None = None,
             max_questions: int | None = None, stt_min_conf: float | None = None) -> RunResult:
    th = load_clinical_rules()["thresholds"]
    max_q = max_questions if max_questions is not None else th["max_questions"]
    min_conf = stt_min_conf if stt_min_conf is not None else th["stt_min_confidence"]
    crit_conf = th.get("stt_min_confidence_critical", min_conf)          # D-43：關鍵題門檻
    crit_qs = set(th.get("stt_critical_questions", []))
    engine = engine or RulesEngine()
    prompter = prompter or Prompter()
    patient = patient or ScriptedPatient(case)
    audit = audit or AuditLog()
    call_id = case.id

    # 初始狀態：開場白抽取；變體 override 的 slot 設回未知（資訊只能靠問出來）
    state = SlotState(extract(case.opening_zh))
    for k in case.reset_slots:
        state.set(k, None, source="reset_for_variant")
    audit.emit(call_id, "stt_segment", {"speaker": "patient", "text": case.opening_zh})
    audit.emit(call_id, "slot_update", {"slots": state.as_dict(), "from": "opening"})

    opening_decision = engine.decide(state)
    res = RunResult(case_id=case.id, scenario_id=case.scenario_id, module=case.module, is_variant=case.is_variant,
                    truth_tier=case.truth_tier, truth_hard_stop=case.truth_hard_stop, truth_rf=case.truth_rf,
                    final=opening_decision, opening_decision=opening_decision,
                    decisive_total=len(case.decisive_questions))
    asked: set[str] = set()
    from acs_triage.loaders import question_by_id as _qbi
    qb0 = _qbi()
    d = opening_decision
    if d.hard_stop:
        res.hard_stop_turn = 0
        res.rf_reveal_turn = 0
        res.stop_reason = "hard_stop_opening"
    else:
        while True:
            if d.provisional_tier != 9 and d.gate_passed:
                res.stop_reason = "gate_passed"
                break
            if d.provisional_tier == 0 and d.missing and all(
                    any(qb0[q].slot_id == slot for q in asked) for slot in d.missing):
                # D-45：T0 不會被 gate 降級；缺的題都問過（病人答不知道）→ 直接定案，不再拖到題數上限
                res.stop_reason = "gate_passed_t0_asked"
                break
            if res.n_questions >= max_q:
                res.stop_reason = "max_questions"
                break
            q = prompter.next_question(state, missing=d.missing, asked=asked)
            if q is None:
                res.stop_reason = "no_more_questions"
                break
            audit.emit(call_id, "question_shown", {"question_id": q.id, "slot_id": q.slot_id})
            reply = patient.answer(q)
            repeated = False
            thr = crit_conf if (q.priority == "redflag" or q.id in crit_qs) else min_conf
            if reply.stt_confidence < thr:
                # Confidence Gate：請病人再說一次（不餵下游）；紅旗題與關鍵題用較高門檻（D-43）
                audit.emit(call_id, "gate_uncertain", {"question_id": q.id, "confidence": reply.stt_confidence, "threshold": thr})
                res.n_repeats += 1
                repeated = True
                reply = patient.answer(q)
                reply.stt_confidence = 1.0
            asked.add(q.id)
            res.n_questions += 1
            state.set(q.slot_id, reply.value, asked_by=q.id, source=f"turn{res.n_questions}")
            res.turns.append(Turn(q.id, q.slot_id, reply.value, reply.utterance_zh, reply.stt_confidence, repeated))
            audit.emit(call_id, "stt_segment", {"speaker": "patient", "text": reply.utterance_zh,
                                                "confidence": reply.stt_confidence})
            audit.emit(call_id, "slot_update", {"slot": q.slot_id, "value": reply.value, "question_id": q.id})
            d = engine.decide(state)       # 每句都重跑：紅旗逐句檔
            if d.hard_stop:
                res.hard_stop_turn = res.n_questions
                res.rf_reveal_turn = res.n_questions
                res.stop_reason = "hard_stop"
                audit.emit(call_id, "redflag_hit", {"rf": d.rf_hits, "turn": res.n_questions})
                break
    res.final = d
    res.final_slots = state.as_dict()
    res.final_state = state.copy()
    audit.emit(call_id, "tier_decision", d.model_dump())
    pw = route(d, state)
    res.pathway_script = pw.script_id
    audit.emit(call_id, "pathway_shown", pw.model_dump())
    # decisive／escalating recall：被問到或結束時 slot 已知（D-27）
    from acs_triage.loaders import question_by_id
    qb = question_by_id()

    def covered(qid: str) -> bool:
        return qid in asked or state.known(qb[qid].slot_id)

    res.decisive_asked_or_known = sum(1 for qid in case.decisive_questions if covered(qid))
    res.escalating_total = len(case.escalating_questions)
    res.escalating_missed = [qid for qid in case.escalating_questions if not covered(qid)]
    res.escalating_asked_or_known = res.escalating_total - len(res.escalating_missed)
    res.escalating_missed_strict = [qid for qid in case.escalating_questions
                                    if not (qid in asked or (state.known(qb[qid].slot_id) and not state.is_derived(qb[qid].slot_id)))]
    return res
