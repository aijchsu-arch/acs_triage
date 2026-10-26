"""實驗 2（e2e LLM 抽取器）：extract_fn 介面、LLM 抽取器、LM Studio client、文字條件、指標。全部用假 client，不打 API。"""
import json

import pytest

from acs_triage.extract import extract
from acs_triage.loaders import question_by_id, slot_defs
from sim.e2e_llm import confirm_estimate, pctl, phone_texts, structured_fn, utterances
from sim.extractor_e2e import EXTRACTORS, keyword, replay
from sim.llm_extract import (LLMExtractor, LMStudioStructured, build_request, load_prompts, opening_schema,
                             opening_slots, to_slots, validate)
from sim.openai_slots import slot_schema

QB = question_by_id()
OPENING = "今天第一次在快走時胸口像被壓住，休息後才比較好。"
T = {"case_id": "S-ACUTE-01", "opening_zh": OPENING, "turns": [
    {"q": "Q-SYNCOPE-01", "value": False, "utterance_zh": "沒有耶，不會想昏倒，眼前也沒有發黑。"},
    {"q": "Q-DIAPH-01", "value": True, "utterance_zh": "有，那時候有冒冷汗。"}]}


class FakeClient:
    """依 schema 名稱回固定答案；可指定例外或不合法輸出。"""

    def __init__(self, turn=None, opening=None, exc=None):
        self.turn, self.opening, self.exc = turn, opening, exc
        self.calls = []

    def ask(self, system, user, schema, name):
        self.calls.append((system, user, schema, name))
        if self.exc:
            raise self.exc
        obj = self.opening if name == "opening_slots" else self.turn
        return obj, {"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 0}, "output_tokens": 100}, "fake-model"


def _opening_obj(**vals):
    return {k: vals.get(k) for k in opening_slots()}


# ---------------------------------------------------------------- extract_fn 介面
def test_keyword_ignores_question():
    q = QB["Q-DIAPH-01"]
    assert keyword("有，那時候有冒冷汗。", q) == extract("有，那時候有冒冷汗。") == keyword("有，那時候有冒冷汗。", None)
    assert EXTRACTORS["keyword"] is keyword


def test_replay_passes_question_and_texts():
    seen = []

    def spy(text, q):
        seen.append((text, q.id if q else None))
        return keyword(text, q)

    replay([T], spy, texts={("S-ACUTE-01", 1): "轉寫一", ("S-ACUTE-01", 2): "轉寫二"})
    assert seen[0] == (OPENING, None)                       # 開場白沒有題目
    assert seen[1:] == [("轉寫一", "Q-SYNCOPE-01"), ("轉寫二", "Q-DIAPH-01")]


def test_replay_truth_uses_ref_text_not_condition_text():
    # 抽取器只看到 texts 的文字；結構化（真實事實）狀態仍用逐字稿 → 紅旗揭露的那句不受影響
    res, rows, _ = replay([T], lambda text, q: {}, texts={("S-ACUTE-01", 0): "聽不清楚"})
    assert rows[1]["truth"] is True and rows[1]["pred"] is None and rows[1]["grade"] == "missed"
    assert res[0].rf_reveal_turn == 2 and res[0].final.hard_stop is False


def test_structured_fn_writes_transcript_values():
    fn = structured_fn([T])
    assert fn(OPENING, None) == extract(OPENING)
    assert fn("有，那時候有冒冷汗。", QB["Q-DIAPH-01"]) == {"diaphoresis": True}
    res, rows, _ = replay([T], fn, asked_only=True)
    assert all(r["grade"] == "correct" for r in rows) and res[0].final.hard_stop and res[0].hard_stop_turn == 2


def test_structured_fn_rejects_conflicting_values():
    bad = {**T, "case_id": "S-ACUTE-01#0", "turns": [{**T["turns"][1], "value": False}]}
    with pytest.raises(ValueError):
        structured_fn([T, bad])


# ---------------------------------------------------------------- 文字條件
def test_phone_texts_maps_by_text_and_counts_unmatched():
    rows = [{"condition": "phone", "ref": OPENING, "hyp_tw": "今天第一次在快走時胸口像被壓住"},
            {"condition": "clean", "ref": T["turns"][0]["utterance_zh"], "hyp_tw": "不該用 clean"},
            {"condition": "phone", "ref": T["turns"][1]["utterance_zh"], "hyp_tw": "那時候有冒冷汗"}]
    texts, unmatched = phone_texts([T], rows)
    assert texts == {("S-ACUTE-01", 0): "今天第一次在快走時胸口像被壓住", ("S-ACUTE-01", 2): "那時候有冒冷汗"}
    assert unmatched == [("S-ACUTE-01", 1)]
    assert [u[0] for u in utterances(T)] == [0, 1, 2]


# ---------------------------------------------------------------- 提示與 schema
def test_turn_request_reuses_slot_prompt_verbatim():
    q = QB["Q-DIAPH-01"]
    system, user, schema, name = build_request("有，那時候有冒冷汗。", q)
    cfg = load_prompts()
    assert system == cfg["slot_system_zh"] and cfg["slot_prompts_version"] == "0.3"
    assert schema == slot_schema(q) and name == "slot_value"
    assert "客服：" + q.script_zh.strip() in user and "病人：有，那時候有冒冷汗。" in user


def test_opening_schema_is_strict_and_nullable():
    s = opening_schema()
    assert s["additionalProperties"] is False and s["required"] == list(s["properties"])
    assert "consult_screen_positive" not in s["properties"]
    assert set(s["properties"]) == set(slot_defs()) - {"consult_screen_positive"}
    assert s["properties"]["diaphoresis"]["type"] == ["boolean", "null"]
    assert s["properties"]["symptom_character"]["enum"][-1] is None
    system, user, _, name = build_request(OPENING, None)
    assert name == "opening_slots" and OPENING in user and "- diaphoresis（yes_no）：" in system
    assert "ongoing（現在還在不舒服）" in system


def test_validate():
    q = QB["Q-DYSPNEA-GRADE-01"]
    validate({"dont_know": False, "answer": "rest"}, slot_schema(q))
    for bad in [{"dont_know": False, "answer": "sometimes"}, {"dont_know": "no", "answer": "rest"},
                {"dont_know": False}, {"dont_know": False, "answer": "rest", "x": 1}, ["rest"]]:
        with pytest.raises(ValueError):
            validate(bad, slot_schema(q))
    with pytest.raises(ValueError):                         # bool 不是 number
        validate({"dont_know": False, "answer": True}, slot_schema(QB["Q-DURATION-01"]))
    validate(_opening_obj(diaphoresis=True, episode_duration_min=20), opening_schema())


def test_to_slots():
    q = QB["Q-DIAPH-01"]
    assert to_slots({"dont_know": False, "answer": False}, q) == {"diaphoresis": False}
    assert to_slots({"dont_know": True, "answer": True}, q) == {}
    assert to_slots(_opening_obj(symptom_character="pressure", ongoing_now=None), None) == {"symptom_character": "pressure"}


# ---------------------------------------------------------------- LLM 抽取器
def test_llm_extractor_turn_opening_cache_and_cost():
    c = FakeClient(turn={"dont_know": False, "answer": True}, opening=_opening_obj(onset_new=True, symptom_character="pressure"))
    ex = LLMExtractor(c, name="fake", price=(2.0, 0.1, 10.0))
    q = QB["Q-DIAPH-01"]
    assert ex("有，那時候有冒冷汗。", q) == {"diaphoresis": True}
    assert ex("有，那時候有冒冷汗。", q) == {"diaphoresis": True}       # 第二次走快取
    assert ex(OPENING, None) == {"onset_new": True, "symptom_character": "pressure"}
    assert len(c.calls) == 2
    rec = ex.cache[("Q-DIAPH-01", "有，那時候有冒冷汗。")]
    assert rec["ok"] and rec["latency_s"] is not None and rec["model"] == "fake-model"
    assert ex.spent == pytest.approx(2 * (1000 * 2.0 + 100 * 10.0) / 1e6)


@pytest.mark.parametrize("client", [FakeClient(turn={"dont_know": False, "answer": "maybe"}),     # schema 不合法
                                    FakeClient(exc=RuntimeError("LM Studio HTTP 500")),
                                    FakeClient(exc=TimeoutError("secret-ish detail"))])
def test_llm_extractor_failure_writes_nothing(client):
    ex = LLMExtractor(client, name="fake")
    assert ex("有。", QB["Q-DIAPH-01"]) == {}
    rec = ex.cache[("Q-DIAPH-01", "有。")]
    assert rec["ok"] is False and rec["error"]
    assert "secret-ish" not in rec["error"]                 # 非 adapter 例外只記類型


def test_llm_extractor_budget_stops_calls():
    c = FakeClient(turn={"dont_know": False, "answer": True})
    ex = LLMExtractor(c, name="fake", price=(2.0, 0.1, 10.0), budget_usd=0.001)
    q = QB["Q-DIAPH-01"]
    ex.prefetch([("有。", q), ("有啊。", q), ("有喔。", q)], workers=1)
    assert len(c.calls) == 1
    assert [ex.cache[("Q-DIAPH-01", t)]["error"] for t in ("有啊。", "有喔。")] == ["budget_exceeded"] * 2


# ---------------------------------------------------------------- LM Studio client
class FakeTransport:
    def __init__(self, status, payload):
        self.status, self.payload, self.calls = status, payload, []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, json.loads(body)))
        return self.status, {}, self.payload


def _chat(content, finish="stop"):
    return {"model": "gemma-4-26b-a4b-it-mlx", "choices": [{"message": {"content": content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 70, "completion_tokens": 12}}


def test_lmstudio_request_and_parse():
    t = FakeTransport(200, _chat('{"dont_know": false, "answer": true}'))
    c = LMStudioStructured(model="gemma-4-26b-a4b-it-mlx", base_url="http://127.0.0.1:1234/v1/", transport=t)
    obj, usage, model = c.ask("sys", "user", slot_schema(QB["Q-DIAPH-01"]), "slot_value")
    url, headers, body = t.calls[0]
    assert url == "http://127.0.0.1:1234/v1/chat/completions" and "Authorization" not in headers
    assert body["temperature"] == 0.0 and body["messages"][0] == {"role": "system", "content": "sys"}
    rf = body["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True and rf["json_schema"]["name"] == "slot_value"
    assert obj == {"dont_know": False, "answer": True} and model == "gemma-4-26b-a4b-it-mlx" and usage["completion_tokens"] == 12


@pytest.mark.parametrize("status,payload", [(400, None), (200, _chat("不是 JSON")), (200, _chat('{"dont_know"', finish="length"))])
def test_lmstudio_errors_become_extraction_failures(status, payload):
    c = LMStudioStructured(model="m", base_url="http://127.0.0.1:1234/v1", transport=FakeTransport(status, payload))
    ex = LLMExtractor(c, name="m")
    assert ex("有。", QB["Q-DIAPH-01"]) == {}
    assert ex.cache[("Q-DIAPH-01", "有。")]["ok"] is False


# ---------------------------------------------------------------- 指標
def test_confirm_estimate_uses_leading_yes_no_on_text():
    rows = [  # 紅旗題答「有」被抽成沒有：句首不是否定詞 → 會複誦；句首是否定詞 → 不會
        {"case_id": "a", "turn": 1, "q": "Q-DIAPH-01", "priority": "redflag", "truth": True, "pred": False, "grade": "wrong",
         "text": "那時候有冒冷汗。"},
        {"case_id": "b", "turn": 1, "q": "Q-DIAPH-01", "priority": "redflag", "truth": True, "pred": False, "grade": "wrong",
         "text": "沒有，好像有一點冒汗。"},
        {"case_id": "c", "turn": 1, "q": "Q-DIAPH-01", "priority": "redflag", "truth": True, "pred": True, "grade": "correct",
         "text": "有。"},
        {"case_id": "d", "turn": 1, "q": "Q-NAUSEA-01", "priority": "refine", "truth": True, "pred": None, "grade": "missed",
         "text": "有。"}]
    ce = confirm_estimate(rows)
    assert ce["wrong_turns"] == 2 and ce["triggered_turns"] == 1
    assert ce["yes_missed_turns"] == 2 and ce["yes_missed_triggered_sentences"] == 1


def test_pctl_nearest_rank():
    xs = [float(i) for i in range(1, 21)]
    assert pctl(xs, 95) == 19.0 and pctl(xs, 50) == 10.0 and pctl([], 95) is None


def test_hs_trigger_and_abstain_diagnostics():
    from sim.e2e_llm import abstain_diag, hs_trigger_diag
    neg = {**T, "case_id": "S-ACUTE-01#1", "turns": [{**T["turns"][1], "value": False, "utterance_zh": "沒有冒冷汗。"}]}
    # 假 Hard stop：「沒有冒冷汗」被抽成有 → 第 1 句觸發 RF-06
    fn = lambda text, q: {"diaphoresis": True} if q is not None else extract(text)   # noqa: E731
    res, _, _ = replay([neg], fn)
    diag = hs_trigger_diag([neg], res, fn, {})
    assert res[0].final.hard_stop and not res[0].truth_hard_stop
    assert diag == [{"case_id": "S-ACUTE-01#1", "kind": "false_alarm", "truth_tier": res[0].truth_tier, "turn": 1,
                     "rf": res[0].final.rf_hits, "text": "沒有冒冷汗。", "q": "Q-DIAPH-01",
                     "wrote": {"diaphoresis": True}, "truth": {"diaphoresis": False}}]
    # 開場白什麼都沒抽到 → 若判 9，結構化開場白已知的缺項標成 dropped
    res, _, _ = replay([neg], lambda text, q: {})
    for a in abstain_diag([neg], res, lambda text, q: {}, {}):
        assert set(a["dropped"]) <= set(extract(OPENING)) and set(a["dropped"]) <= set(a["missing"])


def test_replay_still_accepts_single_argument_extract_fn():
    a = replay([T], extract)
    b = replay([T], keyword)
    assert a[1] == b[1] and a[2] == b[2] and [r.final for r in a[0]] == [r.final for r in b[0]]
