"""對話 runner：開場白 → 逐題問答 → 紅旗逐句檢查 → sufficiency → 最終 tier。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acs_triage.audit import AuditLog
from acs_triage.extract import extract
from acs_triage.loaders import load_clinical_rules
from acs_triage.pathway import route
from acs_triage.prompter import Prompter
from acs_triage.prompter.confirm import confirm_prompt, resolve_confirm, should_confirm
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
    # D-50 複誦確認（confirm_prompt_zh 為 None = 沒有複誦）；answer 是確認後採用的值
    confirm_prompt_zh: str | None = None
    pre_confirm_answer: Any = None
    confirm_utterance_zh: str | None = None
    confirm_answer: Any = None
    confirm_downgrade_blocked: bool = False    # 確認值較不嚴重 → 保留原值


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
    n_confirms: int = 0                        # D-50：複誦確認次數（不算進 n_questions）
    n_confirm_changed: int = 0                 # 確認後值改變的次數
    n_confirm_downgrade_blocked: int = 0       # 確認值較不嚴重、因此保留原值的次數（複誦不得降級）
    pending_test_asked: bool = False           # rules 0.8.0：有症狀暫判 T2–T4、定案前加問了待追蹤檢查
    pending_test_skipped_at_cap: bool = False  # 該加問但已達題數上限 → 沒問，照原結果定案
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
             max_questions: int | None = None, stt_min_conf: float | None = None,
             confirm_back: bool | None = None) -> RunResult:
    th = load_clinical_rules()["thresholds"]
    max_q = max_questions if max_questions is not None else th["max_questions"]
    min_conf = stt_min_conf if stt_min_conf is not None else th["stt_min_confidence"]
    crit_conf = th.get("stt_min_confidence_critical", min_conf)          # D-43：關鍵題門檻
    crit_qs = set(th.get("stt_critical_questions", []))
    confirm_on = confirm_back if confirm_back is not None else th.get("stt_confirm_back", False)   # D-50
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
            q = None
            if d.provisional_tier != 9 and d.gate_passed:
                # rules 0.8.0：有症狀暫判 T2–T4 → 定案前加問待追蹤檢查一次（算題數；已達上限就不問、照原結果定案）
                q = prompter.pending_test_question(state, d, asked)
                if q is not None and res.n_questions >= max_q:
                    res.pending_test_skipped_at_cap = True
                    q = None
                if q is None:
                    res.stop_reason = "gate_passed"
                    break
                res.pending_test_asked = True
            if q is None and d.provisional_tier == 0 and d.missing and all(
                    any(qb0[x].slot_id == slot for x in asked) for slot in d.missing):
                # D-45：T0 不會被 gate 降級；缺的題都問過（病人答不知道）→ 直接定案，不再拖到題數上限
                res.stop_reason = "gate_passed_t0_asked"
                break
            if q is None and res.n_questions >= max_q:
                res.stop_reason = "max_questions"
                break
            q = q or prompter.next_question(state, missing=d.missing, asked=asked)
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
            audit.emit(call_id, "stt_segment", {"speaker": "patient", "text": reply.utterance_zh,
                                                "confidence": reply.stt_confidence})
            turn = Turn(q.id, q.slot_id, reply.value, reply.utterance_zh, reply.stt_confidence, repeated)
            if confirm_on and should_confirm(engine, state, q, reply.value, reply.utterance_zh):
                # D-50 複誦確認（不算題數）；寫入後即 Hard stop 者不複誦，不得因確認延誤送醫；確認後取較嚴重者
                prompt = confirm_prompt(q, reply.value)
                c = patient.confirm(q, prompt)
                heard = c.value if c.stt_confidence >= thr else None    # 確認回答信心偏低 → 視為未確認
                turn.answer, turn.confirm_downgrade_blocked = resolve_confirm(q, reply.value, heard)
                turn.pre_confirm_answer, turn.confirm_prompt_zh = reply.value, prompt
                turn.confirm_utterance_zh, turn.confirm_answer = c.utterance_zh, c.value
                res.n_confirms += 1
                res.n_confirm_changed += int(turn.answer != reply.value)
                res.n_confirm_downgrade_blocked += int(turn.confirm_downgrade_blocked)
                audit.emit(call_id, "confirm_back", {"question_id": q.id, "slot_id": q.slot_id, "pre_value": reply.value,
                                                     "prompt_zh": prompt, "reply_text": c.utterance_zh,
                                                     "reply_value": c.value, "reply_confidence": c.stt_confidence,
                                                     "value": turn.answer, "downgrade_blocked": turn.confirm_downgrade_blocked})
            state.set(q.slot_id, turn.answer, asked_by=q.id, source=f"turn{res.n_questions}")
            res.turns.append(turn)
            audit.emit(call_id, "slot_update", {"slot": q.slot_id, "value": turn.answer, "question_id": q.id})
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
