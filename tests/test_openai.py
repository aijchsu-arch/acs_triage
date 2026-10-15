"""M3b：OpenAI adapter（假 transport，不打 API）與逐句紅旗標籤。"""
import json

import pytest

from acs_triage.decision.openai_adapter import ENDPOINT, KEY_ENV, OpenAIStructured, usage_cost
from acs_triage.loaders import REPO_ROOT
from sim.openai_eval import RF_SCHEMA, RFS, rf_steps


def _resp(obj, status="completed"):
    return 200, {}, {"status": status, "model": "gpt-6.1-sol",
                     "output": [{"type": "reasoning"}, {"type": "message", "content": [{"type": "output_text", "text": json.dumps(obj)}]}],
                     "usage": {"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 400}, "output_tokens": 200}}


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, json.loads(body)))
        return self.responses.pop(0)


def test_request_and_parse():
    t = FakeTransport([_resp({rf: False for rf in RFS})])
    c = OpenAIStructured(model="gpt-6.1-sol", effort="medium", api_key="k", transport=t)
    obj, usage, model = c.ask("sys", "user", RF_SCHEMA, "redflags")
    url, headers, body = t.calls[0]
    assert url == ENDPOINT and headers["Authorization"] == "Bearer k"
    assert body["model"] == "gpt-6.1-sol" and body["reasoning"] == {"effort": "medium"} and body["store"] is False
    fmt = body["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True and fmt["schema"]["additionalProperties"] is False
    assert body["input"][0]["role"] == "developer"
    assert obj == {rf: False for rf in RFS} and model == "gpt-6.1-sol"


def test_errors_do_not_leak_message(monkeypatch):
    monkeypatch.setattr("acs_triage.decision.openai_adapter.time.sleep", lambda s: None)
    t = FakeTransport([(401, {}, {"error": {"message": "Incorrect API key provided: sk-proj-****abcd", "code": "invalid_api_key", "type": "x"}})])
    with pytest.raises(RuntimeError) as e:
        OpenAIStructured(model="m", effort="low", api_key="k", transport=t).ask("s", "u", RF_SCHEMA, "n")
    assert "invalid_api_key" in str(e.value) and "sk-proj" not in str(e.value)
    t = FakeTransport([(429, {"retry-after": "0"}, None), _resp({rf: True for rf in RFS})])
    assert OpenAIStructured(model="m", effort="low", api_key="k", transport=t).ask("s", "u", RF_SCHEMA, "n")[0]["RF-01"]
    with pytest.raises(RuntimeError, match="incomplete"):
        OpenAIStructured(model="m", effort="low", api_key="k", transport=FakeTransport([_resp({}, status="incomplete")])).ask("s", "u", RF_SCHEMA, "n")


def test_usage_cost():
    u = {"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 400}, "output_tokens": 200}
    assert usage_cost(u, 2.0, 0.1, 10.0) == pytest.approx((600 * 2 + 400 * 0.1 + 200 * 10) / 1e6)


def test_rf_steps_labels_follow_engine():
    tr = [{"case_id": "S-ACUTE-01#0", "opening_zh": "今天第一次在快走時胸口像被壓住，休息後才比較好。",
           "turns": [{"q": "Q-ONGOING-01", "value": True, "utterance_zh": "現在還在壓。"}]}]
    s = rf_steps(tr)
    assert [x["step"] for x in s] == [0, 1]
    assert s[0]["label"] == [] and s[1]["label"] == ["RF-03"]
    assert "客服：" in s[1]["dialogue_zh"] and "病人：現在還在壓。" in s[1]["dialogue_zh"]


def test_key_policy_and_prompt_matches_rules():
    src = (REPO_ROOT / "src/acs_triage/decision/openai_adapter.py").read_text(encoding="utf-8")
    assert KEY_ENV == "ACS_OPENAI_API_KEY"
    for f in ("src/acs_triage/decision/openai_adapter.py", "sim/openai_eval.py"):
        txt = (REPO_ROOT / f).read_text(encoding="utf-8").replace("ACS_OPENAI_API_KEY", "")
        assert "OPENAI_API_KEY" not in txt and "ANTHROPIC_API_KEY" not in txt
    rules = (REPO_ROOT / "docs/CLINICAL_RULES.md").read_text(encoding="utf-8")
    prompt = (REPO_ROOT / "data/openai_prompts.yaml").read_text(encoding="utf-8")
    for cond in ["胸部壓迫／疼痛／缺血等價症狀 **合併** 瀕厥或暈厥", "**靜止休息時仍有呼吸困難**",
                 "來電當下**症狀仍持續中**的胸部壓迫／疼痛或缺血等價症狀（下顎、左肩、上腹沉重等）",
                 "呼吸困難到**無法完整說完一句話**，或口唇發紺", "真正**意識喪失**（任何心臟相關症狀脈絡下）",
                 "胸部不適／缺血等價症狀 **合併明顯冒汗**（diaphoresis）"]:
        assert cond in rules and cond in prompt   # 紅旗條件逐字取自 CLINICAL_RULES §3


def test_slot_grade_and_schema():
    from acs_triage.loaders import question_by_id
    from sim.openai_slots import grade, slot_schema, turns
    assert grade(True, True) == "correct" and grade(10, 10.0) == "correct"
    assert grade(None, "unknown") == "unknown_equiv" and grade("unknown", None) == "unknown_equiv"
    assert grade(True, None) == "missed" and grade(None, False) == "invented" and grade(True, False) == "wrong"
    qb = question_by_id()
    s = slot_schema(qb["Q-DYSPNEA-GRADE-01"])
    assert s["additionalProperties"] is False and "none" in s["properties"]["answer"]["enum"]
    tr = [{"case_id": "X", "opening_zh": "o", "turns": [{"q": "Q-ONGOING-01", "value": True, "utterance_zh": "還在。"}]}]
    assert turns(tr, None) == [{"case_id": "X", "turn": 1, "q": "Q-ONGOING-01", "slot": "ongoing_now", "priority": "redflag",
                                "answer_type": "yes_no", "utterance_zh": "還在。", "truth": True}]


def test_speechless_grading_d40():
    from sim.openai_slots import grade
    assert grade(None, "unclear", "exertion_relation") == "speechless"
    assert grade(None, "vague", "symptom_character") == "speechless"
    assert grade(None, "unclear", "symptom_character") == "invented"     # 只限各自對應的選項
    assert grade("none", "vague", "symptom_character") == "wrong"         # 明確否認被抽成說不上來仍是錯
