"""M2b：LLMPatientSimulator 離線測試（假 client，不打 API、不需金鑰）。"""
import json
from pathlib import Path
from types import SimpleNamespace

from acs_triage.loaders import REPO_ROOT, questions
from sim.cases import all_cases
from sim.llm_patient import KEY_ENV, LLMPatientSimulator, answer_schema, build_system
from sim.metrics import compute
from sim.patient import ScriptedPatient
from sim.runner import run_case

_BY_SCRIPT = {q.script_zh.strip(): q for q in questions()}


class FakeClient:
    """依 hidden sheet 照實回答（answer_fn 可換成會出錯的病人）。記錄每次請求供檢查。"""

    def __init__(self, case, answer_fn=None, confirm_fn=None):
        self.oracle = ScriptedPatient(case)
        self.answer_fn = answer_fn
        self.confirm_fn = confirm_fn            # D-50：複誦確認時改用的回答（None = 照原題規則）
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.requests.append({**kw, "messages": list(kw["messages"])})
        content = kw["messages"][-1]["content"]
        # 原題 = 題目原文；D-50 複誦確認 = 內含題目原文的句子（取最長的那題）
        q = _BY_SCRIPT.get(content) or _BY_SCRIPT[max((s for s in _BY_SCRIPT if s in content), key=len)]
        if self.confirm_fn and content not in _BY_SCRIPT:
            v = self.confirm_fn(q)
        else:
            v = self.answer_fn(q) if self.answer_fn else self.oracle.answer(q).value
        schema_ans = kw["output_config"]["format"]["schema"]["properties"]["answer"]
        dont_know = v is None or (v == "unknown" and "unknown" not in schema_ans.get("enum", []))
        if not dont_know and "enum" in schema_ans:
            assert v in schema_ans["enum"], (q.id, v)   # 真的 API 受 schema 限制，假 client 也要
        filler = {"boolean": False, "number": 0, "string": (schema_ans.get("enum") or [""])[0]}[schema_ans["type"]]
        data = {"utterance_zh": "不知道。" if dont_know else f"{v}。", "dont_know": dont_know,
                "answer": filler if dont_know else v}
        usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=0)
        return SimpleNamespace(stop_reason="end_turn", model="fake-model", usage=usage,
                               content=[SimpleNamespace(type="text", text=json.dumps(data, ensure_ascii=False))])


def _run(case, answer_fn=None):
    fc = FakeClient(case, answer_fn)
    p = LLMPatientSimulator(case, client=fc)
    return run_case(case, patient=p), p, fc


def test_faithful_llm_patient_matches_scripted_clean():
    cases = all_cases()
    llm, scripted = [], []
    for c in cases:
        r, p, _ = _run(c)
        assert p.deviations == [], c.id
        llm.append(r)
        scripted.append(run_case(c, patient=ScriptedPatient(c)))
    for a, b in zip(llm, scripted):
        assert (a.final.tier, a.final.hard_stop, [t.question_id for t in a.turns]) == \
               (b.final.tier, b.final.hard_stop, [t.question_id for t in b.turns]), a.case_id
    m = compute(llm)
    assert m.hard_stop_miss == [] and m.under_triage == []


def test_deviations_are_classified():
    case = next(c for c in all_cases() if c.persona == "normal" and not c.is_variant)
    oracle = ScriptedPatient(case)

    def liar(q):
        v = oracle.answer(q).value
        if v is None:
            return True if q.answer_type == "yes_no" else v      # 編造
        if isinstance(v, bool):
            return not v                                          # 矛盾
        return None                                               # 漏答
    _, p, _ = _run(case, liar)
    kinds = {d.kind for d in p.deviations}
    assert p.deviations and kinds <= {"fabricated", "contradicted", "omitted"}


def test_vague_persona_sheet_hides_non_redflag_facts():
    case = next(c for c in all_cases() if c.persona == "vague")
    sheet = build_system(case)
    by_slot = {q.slot_id: q for q in questions()}
    for slot, v in case.slots.items():
        q = by_slot.get(slot)
        if v is not None and q is not None and q.priority != "redflag":
            assert f"- {slot}（" not in sheet


def test_request_shape():
    case = all_cases()[0]
    _, _, fc = _run(case)
    req = fc.requests[0]
    assert req["system"] == build_system(case)
    assert req["model"] == "claude-opus-5-5" and req["fallbacks"] == "default"   # D-34
    assert req["output_config"]["effort"] == "medium"
    p = LLMPatientSimulator(case, client=FakeClient(case))
    run_case(case, patient=p)
    assert p.usage["calls"] > 0 and p.usage["input_tokens"] == 10 * p.usage["calls"]
    schema = req["output_config"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    # 對話只增不改（append-only）：後一次請求的 messages 以前一次為前綴
    for a, b in zip(fc.requests, fc.requests[1:]):
        assert b["messages"][: len(a["messages"])] == a["messages"]


def test_choice_schema_enum_matches_slot():
    for q in questions():
        s = answer_schema(q)["properties"]["answer"]
        if q.answer_type == "choice":
            assert s["enum"]


def test_key_handling_policy():
    """D-31：只用 ACS_PATIENT_LLM_KEY，程式碼不得提到 ANTHROPIC_API_KEY。"""
    assert KEY_ENV == "ACS_PATIENT_LLM_KEY"
    for f in ("sim/llm_patient.py", "sim/run_llm_eval.py"):
        src = Path(REPO_ROOT / f).read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY" not in src
        assert 'api_key=os.environ[KEY_ENV]' in src or f.endswith("run_llm_eval.py")


def test_confirm_back_is_next_user_turn_with_same_answer_schema():
    """D-50：複誦確認是同一段對話的下一則 user 訊息，內含題目原文；answer 的 schema 與原題相同（填實際值，不是「對／不對」）。
    假 client 的回答句（如「False。」）句首不是「有／沒有」→ 範圍內的是非題都會被複誦；照實回答時結果與偏差都不受影響。"""
    n_confirm = 0
    for case in all_cases()[:30]:
        r, p, fc = _run(case)
        assert p.deviations == [] and r.n_confirm_changed == 0, case.id
        for prev, req in zip(fc.requests, fc.requests[1:]):
            content = req["messages"][-1]["content"]
            if content in _BY_SCRIPT:
                continue
            q = _BY_SCRIPT[prev["messages"][-1]["content"]]
            assert q.script_zh.strip() in content
            assert req["output_config"]["format"]["schema"] == answer_schema(q)
            n_confirm += 1
        assert r.n_confirms == sum(1 for req in fc.requests if req["messages"][-1]["content"] not in _BY_SCRIPT)
    assert n_confirm > 20


def test_confirm_reply_deviation_counted_and_reported():
    """複誦回答也與事實清單比對：被「請您回答『有』還是『沒有』」逼出的答案記為編造（confirm=True），報告另列並標「（複誦）」。"""
    from sim.metrics import compute
    from sim.run_llm_eval import render_compare
    found = None
    for case in all_cases():
        fc = FakeClient(case, confirm_fn=lambda q: True if q.answer_type == "yes_no" else None)
        p = LLMPatientSimulator(case, client=fc)
        r = run_case(case, patient=p)
        if any(d.confirm and d.kind == "fabricated" for d in p.deviations):
            found = (case, r, p)
            break
    assert found
    case, r, p = found
    assert p.deviations and all(d.confirm for d in p.deviations)          # 原題照實回答，偏差只來自複誦
    s = run_case(case, patient=ScriptedPatient(case))
    md = render_compare([r], compute([r]), {case.id: s}, compute([s]), [p], [])
    assert f"其中複誦確認（D-50）的回答 {r.n_confirms} 次：偏差 {len(p.deviations)}" in md
    assert f"| {case.id} | {p.deviations[0].question_id}（複誦） |" in md
    assert f"總回答數：{len(r.turns) + r.n_confirms}；" in md
