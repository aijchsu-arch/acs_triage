"""M3a：Jev adapter（假 transport，不打 API）與 ND-01 合併邏輯（model_downgrade_blocked）。"""
import json
from pathlib import Path

import pytest

from acs_triage.decision.jev_adapter import ENDPOINT, KEY_ENV, JevAdapter, load_config, slot_state, triage_questions
from acs_triage.decision.merge import merge_tier
from acs_triage.loaders import REPO_ROOT, slot_defs
from acs_triage.rules import RulesEngine, SlotState
from acs_triage.schemas import TierDecision


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, json.loads(body)))
        return self.responses.pop(0)


def _ok(choice="T1", noul=0.8):
    return 200, {}, {"model": "jev-1.13.0", "usage": {"input_tokens": 100, "output_tokens": 0},
                     "answers": {"q0": {"type": "choice", "choice": choice, "confidence": 0.7,
                                        "probabilities": {choice: 0.85, "T0": 0.15}},
                                 "q1": {"type": "noul", "noul": noul}}}


def _qs():
    cfg = load_config()
    ctx = json.dumps(slot_state({"cad_history": True}, cfg["state_preamble"]), sort_keys=True)
    return cfg, triage_questions(cfg, ctx)


def test_request_shape_and_parse():
    cfg, qs = _qs()
    t = FakeTransport([_ok()])
    tier, suff = JevAdapter(api_key="test-key", transport=t, seed="S-X").decide_many(qs)
    url, headers, body = t.calls[0]
    assert url == ENDPOINT and headers["Authorization"] == "Bearer test-key"
    assert body["model"] == "jev-1.13.0" == cfg["model"]
    assert body["questions"]["q0"]["type"] == "choice" and set(body["questions"]["q0"]["criteria"]) == set(cfg["tier"]["criteria"])
    assert body["questions"]["q1"]["type"] == "noul" and set(body["questions"]["q1"]["criteria"]) == {"true", "false"}
    findings = body["state"]["findings"]
    assert set(findings) == set(slot_defs()) and findings["cad_history"] is True and findings["ongoing_now"] == "unknown"
    assert tier.answer == "T1" and tier.model_version == "jev-1.13.0" and tier.probabilities["T1"] == 0.85
    assert suff.answer is True and suff.confidence == pytest.approx(0.6) and suff.probabilities == {"true": 0.8}


def test_choice_order_shuffled_per_seed():
    _, qs = _qs()
    orders = set()
    for seed in range(8):
        t = FakeTransport([_ok()])
        JevAdapter(api_key="k", transport=t, seed=seed).decide_many(qs)
        orders.add(tuple(t.calls[0][2]["questions"]["q0"]["criteria"]))
    assert len(orders) > 1


def test_retry_on_429_then_error_on_4xx(monkeypatch):
    monkeypatch.setattr("acs_triage.decision.jev_adapter.time.sleep", lambda s: None)
    _, qs = _qs()
    t = FakeTransport([(429, {"retry-after": "0"}, None), _ok()])
    assert JevAdapter(api_key="k", transport=t).decide_many(qs)[0].answer == "T1"
    assert len(t.calls) == 2
    with pytest.raises(RuntimeError, match="401"):
        JevAdapter(api_key="k", transport=FakeTransport([(401, {}, {"error": "x"})])).decide_many(qs)


def test_draft_config_refused(tmp_path, monkeypatch):
    import acs_triage.decision.jev_adapter as ja
    (tmp_path / "jev_questions.yaml").write_text("status: draft\n", encoding="utf-8")
    monkeypatch.setattr(ja, "DATA_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="核可"):
        ja.load_config()


# ---------------------------------------------------------------- ND-01 合併（model_downgrade_blocked）
def _td(tier, hs=False):
    return TierDecision(provisional_tier=tier, tier=tier, gate_passed=tier != 9, hard_stop=hs)


CHEST = SlotState({"symptom_character": "pressure"})          # Tier 9 → C6 D 胸部不適 → T1


@pytest.mark.parametrize("rules,model,blocked,final", [
    (1, 3, True, 1),      # 模型較不急 → 擋下，維持規則
    (0, 4, True, 0),
    (3, 1, False, 1),     # 模型較急 → 升級（shadow 下只是「若接進決策」）
    (2, 2, False, 2),
    (9, 3, True, 9),      # 規則 9（胸部→T1）vs 模型 T3 → 擋下
    (0, 9, True, 0),      # 模型 9（→T1）比規則 T0 不急 → 擋下
    (3, 9, False, 9),     # 模型 9（→T1）比規則 T3 急 → 升級為 9
])
def test_merge_nd01(rules, model, blocked, final):
    m = merge_tier(_td(rules), model, CHEST)
    assert m.model_downgrade_blocked is blocked and m.tier == final and m.source == "merged"


def test_merge_never_overrides_hard_stop():
    m = merge_tier(_td(0, hs=True), 0, CHEST)
    assert m.hard_stop and m.tier == 0 and not m.model_downgrade_blocked
    m = merge_tier(_td(0, hs=True), 3, CHEST)
    assert m.hard_stop and m.tier == 0 and m.model_downgrade_blocked


def test_merge_with_real_engine_decision():
    s = SlotState({"ongoing_now": True, "symptom_character": "pressure"})   # RF-03
    d = RulesEngine().decide(s)
    assert d.hard_stop
    assert merge_tier(d, 4, s).model_downgrade_blocked


def test_key_policy():
    for f in ("src/acs_triage/decision/jev_adapter.py", "sim/jev_eval.py"):
        src = (REPO_ROOT / f).read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY" not in src and "OPENAI_API_KEY" not in src and "TYPESAFE_API_KEY" not in src
    assert KEY_ENV == "ACS_JEV_API_KEY"


def test_slot_state_known_mode():
    s = slot_state({"cad_history": True, "ongoing_now": None}, "pre", "known")
    assert s["findings"] == {"cad_history": True}
    assert "ongoing_now" in s["not_yet_asked"] and "cad_history" not in s["not_yet_asked"]
    assert set(s["findings"]) | set(s["not_yet_asked"]) == set(slot_defs())
