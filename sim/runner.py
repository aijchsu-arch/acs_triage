"""對話 runner：開場白 → 逐題問答 → 紅旗逐句檢查 → sufficiency → 最終 tier。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acs_triage.audit import AuditLog
from acs_triage.extract import extract
from acs_triage.loaders import load_clinical_rules
from acs_triage.pathway import route, tier9_fallback
from acs_triage.prompter import Prompter
from acs_triage.prompter.confirm import confirm_prompt, in_scope, reask_prompt, resolve_confirm, severity, should_confirm
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
    # 閉環（extractor 選項）：answer 改由抽取器決定；病人模擬回傳的結構化值只留作對照
    structured_answer: Any = None
    extracted: dict[str, Any] | None = None    # 這句抽到的全部 slot（含順口提到的）
    confirm_structured: Any = None


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
    opening_extracted: dict[str, Any] | None = None              # 閉環：開場白抽取結果
    mention_conflicts: list[dict[str, Any]] = field(default_factory=list)   # 閉環：沒採用的順口值（conflict／d50_not_most_severe）
    mention_confirms: list[dict[str, Any]] = field(default_factory=list)    # 閉環：因順口值對已問過的 D-50 題複誦（計入 n_confirms）
    reasks: list[dict[str, Any]] = field(default_factory=list)              # D-54：順口值矛盾再問（不算題數）
    # 通話結束時把再問前的值放回最後狀態重算，因再問而較不急者。只放回值、不重跑對話，路徑分岔造成的差異記不到（例如 S-MID-04#0），要看 reasks 全部明細
    reask_downgrades: list[dict[str, Any]] = field(default_factory=list)

    @property
    def hard_stop_latency(self) -> int | None:
        if self.hard_stop_turn is None or self.rf_reveal_turn is None:
            return None
        return self.hard_stop_turn - self.rf_reveal_turn


def _d50_top_values() -> dict[str, set[Any]]:
    """D-50 範圍（紅旗題＋stt_critical_questions）的 slot → 最嚴重一級的值（是非題「有」；選擇題 confirm_back_severity 第一級）。"""
    from acs_triage.loaders import questions
    from acs_triage.prompter.confirm import in_scope
    table = load_clinical_rules()["confirm_back_severity"]
    return {q.slot_id: ({True} if q.answer_type == "yes_no" else set(table[q.slot_id][0])) for q in questions() if in_scope(q)}


def _severity_rank(slot: str, value: Any) -> int:
    """confirm_back_severity 的級數（0＝最嚴重）；是非題用 yes_no 順序。"""
    table = load_clinical_rules()["confirm_back_severity"]
    levels = table.get(slot) or table["yes_no"]
    return next((i for i, level in enumerate(levels) if value in level), len(levels))


def _hard_stop_after(state: SlotState, slot: str, value: Any) -> bool:
    """寫入這個值會讓規則引擎由「非 Hard stop」變成 Hard stop（升級）。原本已是 Hard stop 不算。"""
    eng = RulesEngine()
    if eng.decide(state).hard_stop:
        return False
    trial = state.copy()
    trial.set(slot, value, source="mention_trial")
    return eng.decide(trial).hard_stop


def _mention_may_override(slot: str, new: Any, old: Any) -> bool:
    """已知值可被順口提到的值覆蓋的兩種臨床順序情況：紅旗是非題的「有」（升級），以及 data/clinical_rules.yaml
    confirm_back_severity 已核定順序中較嚴重的值（symptom_character、dyspnea_grade）。不另訂臨床順序。
    （第三種「寫入後即 Hard stop」需要狀態，在 _write_mentions 判斷。）"""
    from acs_triage.loaders import questions
    if new is True and slot in {q.slot_id for q in questions() if q.priority == "redflag" and q.answer_type == "yes_no"}:
        return True
    table = load_clinical_rules()["confirm_back_severity"]
    if slot not in table:
        return False
    rank = {v: i for i, level in enumerate(table[slot]) for v in level}
    return new in rank and old in rank and rank[new] < rank[old]


def _urgency(state: SlotState) -> int:
    """數字越小越急：Hard stop = -1；T0–T4；Tier 9 依 C6 D 預設等級（同 sim.decisive.urgency，但保留 slot 來源）。"""
    d = RulesEngine().decide(state)
    if d.hard_stop:
        return -1
    return tier9_fallback(state)[0] if d.provisional_tier == 9 else d.provisional_tier


def _write_mentions(state: SlotState, found: dict[str, Any], asked_slot: str, source: str) -> list[dict[str, Any]]:
    """閉環：病人順口提到的其他 slot（BLUEPRINT §3.4）。
    - 未知的 slot（含問過但答不知道的）補上；rest_symptom＝false 例外，不採用（D-55 F2）。D-50 範圍（紅旗題＋stt_critical_questions）的 slot：寫入後由非 Hard stop
      變成 Hard stop、或是最嚴重一級 → 補上；其他較不嚴重的值不直接寫入：該題還沒問過 → kind＝d50_not_most_severe
      （由 run_case 暫存；之後直接問到而答案仍未知時，以暫存值當解讀值複誦一次）；該題問過而目前未知 → kind＝d50_confirm
      （由 run_case 立刻對該題複誦一次）。
    - 已知值只在三種情況被覆蓋：紅旗是非題「有」、confirm_back_severity 較嚴重、寫入後規則引擎由非 Hard stop 變成 Hard stop；
      其他不同一律保留已知值，記為 kind＝conflict（由 run_case 對該題再問一次，D-54）。"""
    top = _d50_top_values()
    notes = []
    for k, v in found.items():
        if k == asked_slot or v is None:
            continue
        old = state.get(k)
        if old is None:
            if k == "rest_symptom" and v is False:
                # D-55 F2（Clinical Owner 2026-11-05）：順口提到的「休息時沒有發作」不採用（比照紅旗順口否認），false 只能來自直接回答
                notes.append({"kind": "rest_denial_not_used", "slot": k, "known": None, "mention": v})
                continue
            if k in top and v not in top[k] and not _hard_stop_after(state, k, v):
                sv = state._values.get(k)
                asked_q = sv.asked_by_question_id if sv is not None else None
                if k == "symptom_character" and v in load_clinical_rules()["chest_symptom_characters"]:
                    state.set("chest_discomfort_mentioned", True, source=source)     # D-54（裁定 #15）：性質先不收，但提過胸部症狀
                notes.append({"kind": "d50_confirm" if asked_q else "d50_not_most_severe", "slot": k, "known": None, "mention": v}
                             | ({"question_id": asked_q} if asked_q else {}))
                continue
            state.set(k, v, source=source)
        elif v == old:
            continue
        elif _mention_may_override(k, v, old) or _hard_stop_after(state, k, v):
            state.set(k, v, source=source)
        else:
            notes.append({"kind": "conflict", "slot": k, "known": old, "mention": v})
    return notes


def _reply_mentions(state: SlotState, found: dict[str, Any], q: Any, utterance_zh: str, res: RunResult, source: str) -> None:
    """D-54（H2）：複誦與再問的回答裡順口提到的其他 slot 也照一般回答寫入（_write_mentions）；只記 conflict，不再遞迴複誦或再問。"""
    for cf in _write_mentions(state, found, q.slot_id, source=source):
        res.mention_conflicts.append({"case_id": res.case_id, "turn": res.n_questions, "question_id": q.id, **cf,
                                      "utterance_zh": utterance_zh, "from_reply": True})


def run_case(case: Case, *, patient: PatientSimulator | None = None, engine: RulesEngine | None = None,
             prompter: Prompter | None = None, audit: AuditLog | None = None,
             max_questions: int | None = None, stt_min_conf: float | None = None,
             confirm_back: bool | None = None, extractor: Any = None,
             to_traditional: Any = None) -> RunResult:
    """extractor（閉環，預設 None = 行為不變）：callable(text, q, confirm_prompt=None) -> {slot: value}，q 為 None = 開場白。
    給定時開場白與病人每句話（含再說一次、複誦回答）都交給它，抽出的值決定 slot、紅旗、gate、下一題與 D-50 複誦；
    病人模擬回傳的結構化值只記在 Turn.structured_answer。to_traditional：送進抽取器與句首判斷前的簡轉繁（D-49）。"""
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

    tw = to_traditional or (lambda s: s)
    # 初始狀態：開場白抽取；變體 override 的 slot 設回未知（資訊只能靠問出來）
    opening_found = None if extractor is None else extractor(tw(case.opening_zh), None)
    state = SlotState(extract(case.opening_zh) if extractor is None
                      else {k: v for k, v in opening_found.items() if v is not None})
    for k in case.reset_slots:
        state.set(k, None, source="reset_for_variant")
    audit.emit(call_id, "stt_segment", {"speaker": "patient", "text": case.opening_zh})
    audit.emit(call_id, "slot_update", {"slots": state.as_dict(), "from": "opening"})

    opening_decision = engine.decide(state)
    res = RunResult(case_id=case.id, scenario_id=case.scenario_id, module=case.module, is_variant=case.is_variant,
                    truth_tier=case.truth_tier, truth_hard_stop=case.truth_hard_stop, truth_rf=case.truth_rf,
                    final=opening_decision, opening_decision=opening_decision,
                    decisive_total=len(case.decisive_questions), opening_extracted=opening_found)
    asked: set[str] = set()
    mention_confirmed: set[str] = set()      # 閉環：已因順口值做過 D-50 複誦的 slot（每個 slot 一次）
    d50_confirmed: set[str] = set()          # 直接問時已做過 D-50 複誦的 slot（矛盾再問不再加問）
    stashed: dict[str, Any] = {}             # 閉環：D-50 slot 在該題還沒問過時被拒收的順口值（留較嚴重者）
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
            if res.n_questions < max_q:
                q = prompter.character_followup_question(state, d, asked)     # D-54（裁定 #15）
            if q is None and d.provisional_tier != 9 and d.gate_passed:
                # rules 0.8.0：有症狀暫判 T2–T4 → 定案前加問待追蹤檢查一次（算題數；已達上限就不問、照原結果定案）
                q = prompter.pending_test_question(state, d, asked)
                if q is not None and res.n_questions >= max_q:
                    res.pending_test_skipped_at_cap = True
                    q = None
                # D-54（裁定 #4、#5）：開場白 vague 的再問只在還有題數時才問，排在待追蹤檢查之後算題數
                recheck = prompter.vague_recheck_question(state, d, asked)
                if recheck is not None and max_q - res.n_questions > (q is not None):
                    q = recheck
                elif q is None:
                    res.stop_reason = "gate_passed"
                    break
                else:
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
            value, utt = reply.value, reply.utterance_zh
            reply_mentions: list[tuple[dict[str, Any], Any, str, str]] = []   # D-54（N1）：再問、順口複誦回覆裡的順口值，直接回答寫入後才寫
            if extractor is not None:
                # 閉環：抽取器讀病人原句（繁體）；順口提到的其他 slot 先寫入，讓複誦的「寫入後即 Hard stop」判斷也看得到
                utt = tw(reply.utterance_zh)
                found = extractor(utt, q)
                value = found.get(q.slot_id)
                for cf in _write_mentions(state, found, q.slot_id, source=f"turn{res.n_questions}_mention"):
                    if cf["kind"] in ("d50_confirm", "d50_not_most_severe"):
                        # 目前已是 Hard stop，或寫入該值（連同同一句被問那題的值）後會變 Hard stop：不複誦、直接寫入並走 Hard stop
                        # （D-50：寫入後即 Hard stop 者不複誦，不得因確認延誤送醫；試寫比照 should_confirm）
                        trial = state.copy()
                        if value is not None:
                            trial.set(q.slot_id, value, asked_by=q.id, source="confirm_trial")
                        trial.set(cf["slot"], cf["mention"], source="confirm_trial")
                        if engine.decide(state).hard_stop or engine.decide(trial).hard_stop:
                            sv = state._values.get(cf["slot"])
                            state.set(cf["slot"], cf["mention"], asked_by=sv.asked_by_question_id if sv is not None else None,
                                      source=f"turn{res.n_questions}_mention_hard_stop")
                            continue
                    if cf["kind"] == "d50_confirm" and confirm_on and cf["slot"] not in mention_confirmed:
                        # 該題問過、目前未知，順口值又不是最嚴重一級：立刻對該題複誦一次，以順口值當解讀值（不算題數、計入複誦）
                        mention_confirmed.add(cf["slot"])
                        q2 = qb0[cf["question_id"]]
                        thr2 = crit_conf if (q2.priority == "redflag" or q2.id in crit_qs) else min_conf
                        prompt2 = confirm_prompt(q2, cf["mention"])
                        c2 = patient.confirm(q2, prompt2)
                        found2 = extractor(tw(c2.utterance_zh), q2, confirm_prompt=prompt2)
                        c2_value = found2.get(q2.slot_id)
                        reply_mentions.append((found2, q2, c2.utterance_zh, f"turn{res.n_questions}_confirm_mention"))   # D-54（H2、N1）
                        heard2 = c2_value if c2.stt_confidence >= thr2 else None
                        value2, blocked2 = resolve_confirm(q2, cf["mention"], heard2)
                        state.set(q2.slot_id, value2, asked_by=q2.id, source=f"turn{res.n_questions}_mention_confirm")
                        res.n_confirms += 1
                        res.n_confirm_changed += int(value2 != cf["mention"])
                        res.n_confirm_downgrade_blocked += int(blocked2)
                        res.mention_confirms.append({"stage": "asked_unknown", "case_id": case.id, "turn": res.n_questions,
                                                     "during_question_id": q.id,
                                                     "question_id": q2.id, "slot": q2.slot_id, "mention": cf["mention"],
                                                     "utterance_zh": reply.utterance_zh, "prompt_zh": prompt2,
                                                     "reply_zh": c2.utterance_zh, "reply_value": c2_value,
                                                     "reply_structured": c2.value, "value": value2})
                        audit.emit(call_id, "confirm_back", {"question_id": q2.id, "slot_id": q2.slot_id, "pre_value": cf["mention"],
                                                             "prompt_zh": prompt2, "reply_text": c2.utterance_zh, "reply_value": c2_value,
                                                             "reply_confidence": c2.stt_confidence, "value": value2,
                                                             "downgrade_blocked": blocked2, "from_mention": True})
                        continue
                    if cf["kind"] == "d50_not_most_severe" and cf["slot"] not in mention_confirmed:
                        # 該題還沒問過：暫存（同一 slot 留較嚴重者），直接問到而答案仍未知時，以它當解讀值複誦一次
                        prev = stashed.get(cf["slot"])
                        if prev is None or _severity_rank(cf["slot"], cf["mention"]) < _severity_rank(cf["slot"], prev):
                            stashed[cf["slot"]] = cf["mention"]
                    if cf["kind"] == "d50_confirm":
                        cf = {**cf, "kind": "d50_not_most_severe"}       # 同一題已因順口值複誦過一次（或複誦關閉）→ 不採用
                    if cf["kind"] == "conflict" and confirm_on and not {cf["slot"]} & (mention_confirmed | d50_confirmed):
                        # D-54（裁定 #16）：矛盾 → 對該題再問一次（不算題數；每個欄位一次；已 Hard stop 或這句寫入後 Hard stop 不問）
                        q2 = next((x for x in qb0.values() if x.slot_id == cf["slot"]), None)
                        trial = state.copy()
                        if value is not None:
                            trial.set(q.slot_id, value, asked_by=q.id, source="confirm_trial")
                        # D-50 範圍內：已是最嚴重一級或與順口值同級 → 再問不可能改值，不問
                        moot = q2 is not None and in_scope(q2) and (severity(q2, cf["known"]) == 0
                                                                    or severity(q2, cf["known"]) == severity(q2, cf["mention"]))
                        if q2 is not None and not moot and not engine.decide(trial).hard_stop:
                            mention_confirmed.add(cf["slot"])
                            cf = {**cf, "reasked": True}
                            thr2 = crit_conf if (q2.priority == "redflag" or q2.id in crit_qs) else min_conf
                            prompt2 = reask_prompt(q2)
                            c2 = patient.confirm(q2, prompt2)
                            found2 = extractor(tw(c2.utterance_zh), q2, confirm_prompt=prompt2)
                            c2_value = found2.get(q2.slot_id)
                            reply_mentions.append((found2, q2, c2.utterance_zh, f"turn{res.n_questions}_reask_mention"))   # D-54（H2、N1）
                            heard2 = c2_value if c2.stt_confidence >= thr2 and c2_value != "unknown" else None    # H1：「不記得」也是不明
                            # D-50 範圍內維持取較嚴重者（既有裁定，再問不覆蓋）；範圍外以再問的答案為準，答案不明保留原值
                            value2 = (resolve_confirm(q2, cf["known"], heard2)[0] if in_scope(q2)
                                      else (cf["known"] if heard2 is None else heard2))
                            state.set(q2.slot_id, value2, asked_by=q2.id, source=f"turn{res.n_questions}_reask")
                            asked.add(q2.id)
                            rec = {"case_id": case.id, "turn": res.n_questions, "during_question_id": q.id, "question_id": q2.id,
                                   "slot": q2.slot_id, "known": cf["known"], "mention": cf["mention"], "utterance_zh": reply.utterance_zh,
                                   "prompt_zh": prompt2, "reply_zh": c2.utterance_zh, "reply_value": c2_value, "value": value2}
                            res.reasks.append(rec)
                            audit.emit(call_id, "mention_reask", rec)
                    res.mention_conflicts.append({"case_id": case.id, "turn": res.n_questions, "question_id": q.id, **cf,
                                                  "utterance_zh": reply.utterance_zh})
            turn = Turn(q.id, q.slot_id, value, reply.utterance_zh, reply.stt_confidence, repeated)
            if extractor is not None:
                turn.structured_answer, turn.extracted = reply.value, found
            stash_basis = None
            if extractor is not None and value is None and confirm_on and q.slot_id in stashed:
                # 閉環：先前順口提到、因該題還沒問過而暫存的較不嚴重值；直接問到仍未知 → 以它當解讀值複誦（取代一般的未知複誦）
                stash_basis = stashed.pop(q.slot_id)
                mention_confirmed.add(q.slot_id)
                if engine.decide(state).hard_stop or _hard_stop_after(state, q.slot_id, stash_basis):
                    # 目前已是 Hard stop，或寫入暫存值後會變 Hard stop：不複誦、直接寫入並走 Hard stop（比照 should_confirm）
                    value, stash_basis = stash_basis, None
                    turn.answer = value
            if confirm_on and (stash_basis is not None or should_confirm(engine, state, q, value, utt)):
                # D-50 複誦確認（不算題數）；寫入後即 Hard stop 者不複誦，不得因確認延誤送醫；確認後取較嚴重者
                basis = value if stash_basis is None else stash_basis
                prompt = confirm_prompt(q, basis)
                c = patient.confirm(q, prompt)
                if extractor is None:
                    c_value = c.value
                else:
                    found_c = extractor(tw(c.utterance_zh), q, confirm_prompt=prompt)
                    c_value = found_c.get(q.slot_id)
                    _reply_mentions(state, found_c, q, c.utterance_zh, res, f"turn{res.n_questions}_confirm_mention")   # D-54（H2）
                heard = c_value if c.stt_confidence >= thr else None    # 確認回答信心偏低 → 視為未確認
                turn.answer, turn.confirm_downgrade_blocked = resolve_confirm(q, basis, heard)
                turn.pre_confirm_answer, turn.confirm_prompt_zh = value, prompt
                turn.confirm_utterance_zh, turn.confirm_answer = c.utterance_zh, c_value
                if extractor is not None:
                    turn.confirm_structured = c.value
                if stash_basis is not None:
                    res.mention_confirms.append({"stage": "stashed_then_asked_unknown", "case_id": case.id, "turn": res.n_questions,
                                                 "during_question_id": q.id, "question_id": q.id, "slot": q.slot_id,
                                                 "mention": stash_basis, "utterance_zh": reply.utterance_zh, "prompt_zh": prompt,
                                                 "reply_zh": c.utterance_zh, "reply_value": c_value, "reply_structured": c.value,
                                                 "value": turn.answer})
                d50_confirmed.add(q.slot_id)
                res.n_confirms += 1
                res.n_confirm_changed += int(turn.answer != basis)
                res.n_confirm_downgrade_blocked += int(turn.confirm_downgrade_blocked)
                audit.emit(call_id, "confirm_back", {"question_id": q.id, "slot_id": q.slot_id, "pre_value": basis,
                                                     "prompt_zh": prompt, "reply_text": c.utterance_zh,
                                                     "reply_value": c_value, "reply_confidence": c.stt_confidence,
                                                     "value": turn.answer, "downgrade_blocked": turn.confirm_downgrade_blocked})
            adopted = turn.answer
            if q.id == "Q-CHARACTER-01":
                # D-54：開場白或順口提到的性質再問一次 → 依 confirm_back_severity 取較嚴重者（答不知道、沒有 → 保留原來的）
                prior = state.get(q.slot_id) if state.known(q.slot_id) else stashed.get(q.slot_id)
                if prior is not None:
                    adopted = resolve_confirm(q, prior, turn.answer)[0]
            state.set(q.slot_id, adopted, asked_by=q.id, source=f"turn{res.n_questions}")
            for found2, q2, utt2, src2 in reply_mentions:
                # D-54（N1）：寫在直接回答之後，紅旗「有」照 _write_mentions 的規則覆蓋同題的「沒有」，其他矛盾只記 conflict
                _reply_mentions(state, found2, q2, utt2, res, src2)
            res.turns.append(turn)
            audit.emit(call_id, "slot_update", {"slot": q.slot_id, "value": adopted, "question_id": q.id})
            d = engine.decide(state)       # 每句都重跑：紅旗逐句檔
            if d.hard_stop:
                res.hard_stop_turn = res.n_questions
                res.rf_reveal_turn = res.n_questions
                res.stop_reason = "hard_stop"
                audit.emit(call_id, "redflag_hit", {"rf": d.rf_hits, "turn": res.n_questions})
                break
    # D-54（裁定 #16）：把再問前的值放回去重算（反事實），最終因再問而較不急才算 reask_downgrade
    for rec in res.reasks:
        trial = state.copy()
        trial.set(rec["slot"], rec["known"], asked_by=rec["question_id"], source="reask_counterfactual")
        if _urgency(state) > _urgency(trial):
            res.reask_downgrades.append(rec)
            audit.emit(call_id, "reask_downgrade", rec)
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
