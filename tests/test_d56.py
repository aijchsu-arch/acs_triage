"""D-56（Clinical Owner 2026-11-15）：R7 有胸部症狀一律至少 T2；R9 抽取呼叫逾時延長、重試、失敗計入錯誤數。"""
import random
import socket
import urllib.error

import pytest

from acs_triage.loaders import load_clinical_rules, question_by_id, slot_defs
from acs_triage.pathway import router
from acs_triage.pathway.router import tier9_fallback
from acs_triage.rules import RulesEngine, SlotState, tiers
from sim.cases import all_cases
from sim.patient import ScriptedPatient
from sim.runner import run_case

E = RulesEngine()
QB = question_by_id()
FLOOR = load_clinical_rules()["chest_symptom_floor"]

STABLE = dict(cad_history=True, onset_new=False, pattern_unchanged_duration_months=24, rest_symptom=False, threshold_decreased=False,
              dyspnea_acute=False, presyncope=False, syncope=False, ongoing_now=False, diaphoresis=False, ntg_use_increased=False,
              episode_frequency_increased=False, dyspnea_grade="none", orthopnea_pnd=False, cant_finish_sentence=False,
              antiplatelet_interrupted=False)
MECH = dict(symptom_character="pain", reproducible_mechanical=True, exertion_relation="rest_only", ongoing_now=False,
            diaphoresis=False, presyncope=False, onset_new=True, last_episode_timing="today", rest_symptom=False,
            threshold_decreased=False, ntg_use_increased=False, episode_frequency_increased=False)


def _d(*base, **slots):
    merged = {}
    for b in base:
        merged.update(b)
    return E.decide(SlotState({**merged, **slots}))


# ---------------------------------------------------------------- R7：資料
def test_r7_floor_config_is_data():
    assert load_clinical_rules()["rules_version"] == "0.11.0"
    assert FLOOR["rule_id"] == "T2-CHEST-FLOOR" and FLOOR["min_tier"] == 2 and FLOOR["exempt_rules"] == ["T3-MECHANICAL"]
    assert set(FLOOR["characters"]) == {"pressure", "tightness", "jaw_shoulder_heaviness", "pain", "vague", "epigastric"}
    assert FLOOR["unknown_with_chest_mention"] is True and FLOOR["exempt_d44_exception_a"] is True
    assert set(FLOOR["characters"]) <= set(slot_defs()["symptom_character"]["choices"])     # enum 名稱以程式定義為準
    assert "T2-CHEST-FLOOR" in {r["id"] for r in load_clinical_rules()["tier_rules"]["T2"]}


# ---------------------------------------------------------------- R7：哪些算胸部症狀
@pytest.mark.parametrize("character", ["pressure", "tightness", "jaw_shoulder_heaviness", "pain", "epigastric"])
def test_r7_stable_with_chest_character_raised_to_t2(character):
    d = _d(STABLE, symptom_character=character)
    assert (d.provisional_tier, d.tier, d.gate_passed) == (2, 2, True)
    assert d.evidence[:2] == ["T3-STABLE", "T2-CHEST-FLOOR"]


@pytest.mark.parametrize("slots", [dict(symptom_character="none"), dict(symptom_character="other"), dict(),
                                   dict(symptom_character="none", chest_discomfort_mentioned=True)])
def test_r7_not_chest_symptom_stays_t3(slots):
    d = _d(STABLE, slots)
    assert d.provisional_tier == 3 and "T2-CHEST-FLOOR" not in d.evidence


def test_r7_unknown_character_with_chest_mention_counts():
    """性質未知＋提過胸口 → 比照 vague 走 T3-STABLE（D-54 #15），但不是 D-44 例外 A（裁定限 vague）→ 提高到 T2；
    裁定 4：性質未知不能定案 → gate 缺 symptom_character。"""
    d = _d(STABLE, chest_discomfort_mentioned=True)
    assert d.provisional_tier == 2 and d.evidence[:2] == ["T3-STABLE", "T2-CHEST-FLOOR"]
    assert d.tier == 9 and "symptom_character" in d.missing


# ---------------------------------------------------------------- 裁定 1（2026-11-16）：D-44 例外 A 不受下限影響
def test_ruling1_d44_exception_a_stays_t3():
    d = _d(STABLE, symptom_character="vague")
    assert (d.provisional_tier, d.tier, d.gate_passed) == (3, 3, True) and d.evidence == ["T3-STABLE"]
    assert tiers.d44_exception_a(SlotState({**STABLE, "symptom_character": "vague"}))
    assert _d(STABLE, symptom_character="vague", onset_new=None).provisional_tier == 3          # onset_new 未知：例外 A 仍成立
    assert _d(STABLE, symptom_character="vague", onset_new=True).provisional_tier == 9          # 例外 A 的 onset_new 防護（矛盾 → T9）
    d = _d(STABLE, symptom_character="vague", pending_abnormal_test=True)
    assert d.provisional_tier == 1 and d.evidence == ["T3-STABLE", "T1-PENDING-TEST"]          # 待追蹤檢查下限照舊


def test_ruling1_other_vague_t3_paths_are_raised():
    """vague 走到 T3 的其他路徑只有 D-44 例外 B（新發＋勞累型 → 一般規則）：T3-POST-PCI-MILDER、（矛盾的）T3-STABLE → 照樣提高到 T2。"""
    b = dict(symptom_character="vague", onset_new=True, exertion_relation="exertion_only", symptom_vs_pre_pci="milder",
             rest_symptom=False, threshold_decreased=False, pci_history=True)
    d = _d(b)
    assert d.provisional_tier == 2 and d.evidence[:2] == ["T3-POST-PCI-MILDER", "T2-CHEST-FLOOR"]
    assert not tiers.d44_exception_a(SlotState(b))
    d = _d(STABLE, symptom_character="vague", onset_new=True, exertion_relation="exertion_only", last_episode_timing="over_24h",
           recurrence=True)
    assert d.provisional_tier == 2 and "T3-STABLE" in d.evidence and "T2-CHEST-FLOOR" in d.evidence


# ---------------------------------------------------------------- R7：例外與其他規則
def test_r7_mechanical_alone_stays_t3():
    d = _d(MECH)
    assert (d.provisional_tier, d.tier) == (3, 3) and d.evidence == ["T3-MECHANICAL"]


@pytest.mark.parametrize("extra,other", [(dict(cough_related=True), "T3-COUGH"), (STABLE, "T3-STABLE")])
def test_r7_mechanical_with_other_t3_rule_stays_t3(extra, other):
    """T3-MECHANICAL 與其他 T3 規則同時成立 → 例外照樣適用、維持 T3（規格未涵蓋，理由見 D-56，待 Clinical Owner 確認）。"""
    d = _d(extra, MECH)
    assert d.provisional_tier == 3 and {"T3-MECHANICAL", other} <= set(d.evidence) and "T2-CHEST-FLOOR" not in d.evidence


@pytest.mark.parametrize("slots,rule", [
    (dict(symptom_character="epigastric", postprandial_relieved=True, ongoing_now=False, exertion_relation="rest_only", diaphoresis=False),
     "T3-POSTPRANDIAL"),
    (dict(symptom_character="pain", cough_related=True, exertion_relation="rest_only"), "T3-COUGH"),
    (dict(symptom_character="tightness", symptom_vs_pre_pci="milder", exertion_relation="exertion_only", rest_symptom=False,
          threshold_decreased=False, pci_history=True), "T3-POST-PCI-MILDER"),
    (dict(symptom_character="tightness", cad_history=True, pattern_unchanged_duration_months=12, rest_symptom=True,
          rest_symptom_first_time=False, onset_new=False, ongoing_now=False), "T3-STABLE-REST-RECURRENT"),
])
def test_r7_other_t3_carveouts_raised(slots, rule):
    d = _d(slots)
    assert d.provisional_tier == 2 and d.evidence[:2] == [rule, "T2-CHEST-FLOOR"]


def test_r7_more_urgent_tiers_untouched():
    assert _d(symptom_character="pressure", ongoing_now=True).hard_stop
    d = _d(symptom_character="pressure", onset_new=True, last_episode_timing="today")
    assert d.provisional_tier == 0 and "T2-CHEST-FLOOR" not in d.evidence
    d = _d(symptom_character="tightness", onset_new=True, last_episode_timing="yesterday_within_24h")
    assert d.provisional_tier == 1 and "T2-CHEST-FLOOR" not in d.evidence
    d = _d(symptom_character="tightness", onset_new=True, last_episode_timing="over_24h", recurrence=False, rest_symptom=False)
    assert d.provisional_tier == 2 and d.evidence[0] == "T2-NEW-OVER24H" and "T2-CHEST-FLOOR" not in d.evidence
    d = _d(symptom_character="vague", onset_new=True, last_episode_timing="today")           # T9 不改（繼續問）
    assert d.provisional_tier == 9 and "T2-CHEST-FLOOR" not in d.evidence


def test_r7_pending_test_floor_still_applies_after():
    d = _d(STABLE, symptom_character="tightness", pending_abnormal_test=True)
    assert (d.provisional_tier, d.tier) == (1, 1) and d.evidence == ["T3-STABLE", "T2-CHEST-FLOOR", "T1-PENDING-TEST"]
    d = _d(MECH, pending_abnormal_test=True)
    assert (d.provisional_tier, d.tier) == (1, 1) and d.evidence == ["T3-MECHANICAL", "T1-PENDING-TEST"]


# ---------------------------------------------------------------- 裁定 2（2026-11-16）：抗血小板中斷時 T2 也附 expedite
def test_ruling2_expedite_on_t3_and_all_t2_not_t0_t1():
    from acs_triage.pathway import route
    d = _d(STABLE, symptom_character="tightness", antiplatelet_interrupted=True)           # 下限提高的 T2
    assert d.provisional_tier == 2 and "expedite" in d.pathway_actions
    pw = route(d, SlotState({**STABLE, "symptom_character": "tightness", "antiplatelet_interrupted": True}))
    assert pw.tier == 2 and pw.script_id == "S-T2" and "expedite" in pw.actions
    t2 = dict(dyspnea_grade="exertional_daily", dyspnea_acute=False, orthopnea_pnd=False, cant_finish_sentence=False,
              symptom_character="none", presyncope=False)
    d = _d(t2, antiplatelet_interrupted=True)                                                # 原本就是 T2（不是下限提高）也附
    assert d.provisional_tier == 2 and d.evidence[0] == "T2-DYSPNEA-DAILY" and "expedite" in d.pathway_actions
    assert "expedite" not in _d(t2, antiplatelet_interrupted=False).pathway_actions
    d = _d(MECH, onset_new=False, antiplatelet_interrupted=True)
    assert d.provisional_tier == 3 and "expedite" in d.pathway_actions
    d = _d(STABLE, symptom_character="tightness", antiplatelet_interrupted=True, pending_abnormal_test=True)
    assert d.provisional_tier == 1 and "expedite" not in d.pathway_actions                    # T1 下限不附
    d = _d(symptom_character="tightness", onset_new=True, last_episode_timing="over_24h", antiplatelet_interrupted=True)
    assert d.provisional_tier == 1 and "expedite" not in d.pathway_actions                    # T1-ANTIPLT-SYMPTOMATIC 不附
    d = _d(symptom_character="pressure", onset_new=True, last_episode_timing="today", antiplatelet_interrupted=True)
    assert d.provisional_tier == 0 and "expedite" not in d.pathway_actions


# ---------------------------------------------------------------- 裁定 4（2026-11-16）：判 T3 前一律問性質
def test_ruling4_t3_requires_character_known():
    dys = dict(cad_history=True, onset_new=False, pattern_unchanged_duration_months=24, dyspnea_grade="exertional_heavy",
               dyspnea_acute=False, orthopnea_pnd=False, cant_finish_sentence=False, presyncope=False, syncope=False,
               rest_symptom=False, threshold_decreased=False, ongoing_now=False, diaphoresis=False, antiplatelet_interrupted=False,
               ntg_use_increased=False, episode_frequency_increased=False)
    d = _d(dys)
    assert d.provisional_tier == 3 and d.tier == 9 and d.missing == ["symptom_character"]      # 呼吸路徑的 T3-STABLE：HEAD 不問性質
    assert _d(dys, symptom_character="none").tier == 3
    assert _d(dys, symptom_character="vague").tier == 3                                         # vague → 例外 A
    d = _d(dys, symptom_character="tightness")
    assert d.provisional_tier == 2 and "T2-CHEST-FLOOR" in d.evidence
    d = _d(dys, pending_abnormal_test=True)
    assert d.provisional_tier == 1 and "symptom_character" in d.missing                        # 被提高的 T3 規則也要問
    from acs_triage.prompter import Prompter
    st = SlotState(dys)
    q = Prompter().next_question(st, missing=E.decide(st).missing, asked=set())
    assert q.id == "Q-CHARACTER-01"


# ---------------------------------------------------------------- R7：T9 備援
def test_r7_t9_fallback_at_least_t2_with_chest_symptom(monkeypatch):
    for ch in FLOOR["characters"]:
        assert tier9_fallback(SlotState({"symptom_character": ch}))[0] <= 2
    assert tier9_fallback(SlotState({"chest_discomfort_mentioned": True}))[0] <= 2
    # 表中胸部症狀目前已是 T1；把表改得較不急，確認下限本身有作用
    rules = {**load_clinical_rules()}
    rules["tier9_nurse_unavailable_fallback"] = {**rules["tier9_nurse_unavailable_fallback"], "chest_or_equivalent": 3}
    monkeypatch.setattr(router, "load_clinical_rules", lambda: rules)
    assert tier9_fallback(SlotState({"symptom_character": "vague"}))[0] == 2
    assert tier9_fallback(SlotState({"symptom_character": "none", "palpitations": True}))[0] == 2      # 心悸、無胸部症狀：表值照舊
    assert tier9_fallback(SlotState({"symptom_character": "vague", "pending_abnormal_test": True}))[0] == 1


# ---------------------------------------------------------------- R7：只往較急方向、不改問題序列
def _random_state(rng):
    defs = slot_defs()
    slots = {}
    for sid, d in defs.items():
        if rng.random() < 0.55:
            continue
        if d["type"] == "yes_no":
            slots[sid] = rng.choice([True, False])
        elif d["type"] == "choice":
            slots[sid] = rng.choice(d["choices"])
        else:
            slots[sid] = rng.choice([0.0, 0.3, 1.0, 2.0, 4.0, 6.0, 12.0, 24.0])
    return slots


def test_r7_never_less_urgent_than_without_floor():
    """隨機 slot 狀態 6,000 組：下限只會讓暫判 T3／T4 → T2；其餘與沒有下限時完全相同。"""
    rng = random.Random(56)
    raised = 0
    for _ in range(6000):
        st = SlotState(_random_state(rng))
        tier, rules = tiers.provisional_tier(st)
        base, base_rules = tiers._provisional_tier(st)
        if st.is_true("pending_abnormal_test") and base in (2, 3, 4):
            base, base_rules = 1, base_rules + ["T1-PENDING-TEST"]
        if "T2-CHEST-FLOOR" in rules:
            raised += 1
            assert tier in (1, 2) and base in (1, 3, 4) and tiers.chest_floor_applies(st)
            assert not set(rules) & set(FLOOR["exempt_rules"]) and not (base == 3 and tiers.d44_exception_a(st))
        else:
            assert (tier, rules) == (base, base_rules)
        assert tier <= base or base == 9 and tier == 9
    assert raised > 0


def test_r7_question_sequences_unchanged_and_only_listed_cases_change(monkeypatch):
    """Scripted clean 119 例：有下限與沒有下限的問題序列逐例相同；分級改變的 12 例都是 T3 → T2，且全部等於 truth。"""
    on = {c.id: run_case(c, patient=ScriptedPatient(c)) for c in all_cases()}
    monkeypatch.setattr(tiers, "chest_floor_applies", lambda s: False)
    off = {c.id: run_case(c, patient=ScriptedPatient(c)) for c in all_cases()}
    changed = set()
    for cid, a in on.items():
        b = off[cid]
        assert [t.question_id for t in a.turns] == [t.question_id for t in b.turns], cid
        if (a.final.tier, a.final.hard_stop) != (b.final.tier, b.final.hard_stop):
            assert (b.final.tier, a.final.tier) == (3, 2) and "T2-CHEST-FLOOR" in a.final.evidence, cid
            changed.add(cid)
    assert changed == {"S-ACUTE-01#2", "S-ACUTE-05#1", "S-STABLE-01", "S-STABLE-02", "S-STABLE-02#0", "S-STABLE-04",
                       "S-INSUF-02#1", "S-INSUF-05#1", "S-INSUF-08#1", "S-MID-08", "S-MID-13", "S-MID-16"}   # Clinical Owner 2026-11-16 確認
    assert on["S-MID-14"].final.tier == 3 and on["S-MID-14"].final.evidence == ["T3-MECHANICAL"]   # 例外
    assert on["S-INSUF-01#1"].final.tier == 3 and on["S-INSUF-01#1"].final.evidence == ["T3-STABLE"]   # D-44 例外 A（裁定 1）
    assert all(r.final.tier == r.truth_tier and r.final.hard_stop == r.truth_hard_stop for r in on.values())


# ---------------------------------------------------------------- R9：重試、逾時、錯誤數
from sim.llm_extract_v2 import EXTRACT_TIMEOUT_S, LLMExtractorV2, failed_calls, make_extractor, retryable  # noqa: E402

OK_OBJ = {"asked": {"evidence": "有", "stance": "yes"}, "mentions": [], "unclassified": []}
USAGE = {"input_tokens": 100, "output_tokens": 10}


class Flaky:
    """依序丟出 errors 裡的例外，之後回 OK_OBJ。"""

    def __init__(self, errors):
        self.errors, self.calls = list(errors), 0

    def ask(self, system, user, schema, name):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return OK_OBJ, USAGE, "fake"


@pytest.mark.parametrize("exc,expect", [
    (TimeoutError("timed out"), True), (socket.timeout(), True), (urllib.error.URLError("refused"), True),
    (ConnectionResetError(), True), (RuntimeError("OpenAI HTTP 504 code=None type=None"), True),
    (RuntimeError("LM Studio HTTP 503"), True), (urllib.error.HTTPError("u", 502, "bad", {}, None), True),
    (RuntimeError("OpenAI HTTP 400 code=bad type=invalid_request_error"), False), (RuntimeError("LM Studio finish_reason=length"), False),
    (urllib.error.HTTPError("u", 404, "nf", {}, None), False), (ValueError("$: keys mismatch"), False),
])
def test_r9_retryable_classification(exc, expect):
    assert retryable(exc) is expect


def test_r9_timeout_then_504_then_success_same_result_as_no_failure():
    sleeps = []
    c = Flaky([TimeoutError("timed out"), RuntimeError("OpenAI HTTP 504 code=None type=None")])
    ex = LLMExtractorV2(c, name="fake", sleep=sleeps.append)
    clean = LLMExtractorV2(Flaky([]), name="fake", sleep=sleeps.append)
    q = QB["Q-DIAPH-01"]
    assert ex("有。", q) == clean("有。", q) == {"diaphoresis": True}
    rec = ex.record("有。", q)
    assert rec["ok"] and c.calls == 3 and sleeps == [5.0, 10.0]
    assert rec["retry_errors"] == ["TimeoutError", "RuntimeError: OpenAI HTTP 504 code=None type=None"]
    assert "retry_errors" not in clean.record("有。", q)               # 沒重試的成功呼叫：紀錄格式與之前相同
    assert ex("有。", q) == {"diaphoresis": True} and c.calls == 3       # 快取照舊：同一句不再呼叫


def test_r9_gives_up_after_two_retries_and_counts_as_failure():
    sleeps = []
    c = Flaky([RuntimeError("OpenAI HTTP 504 code=None type=None")] * 5)
    ex = LLMExtractorV2(c, name="fake", sleep=sleeps.append)
    assert ex("有。", QB["Q-DIAPH-01"]) == {"diaphoresis": None}          # 照舊當作沒抽到
    rec = ex.record("有。", QB["Q-DIAPH-01"])
    assert not rec["ok"] and c.calls == 3 and sleeps == [5.0, 10.0] and "504" in rec["error"] and len(rec["retry_errors"]) == 2


def test_r9_non_retryable_not_retried():
    c = Flaky([RuntimeError("LM Studio finish_reason=length")])
    ex = LLMExtractorV2(c, name="fake", sleep=lambda s: pytest.fail("不該重試"))
    assert not ex.record("有。", QB["Q-DIAPH-01"])["ok"] and c.calls == 1


def test_r9_openai_adapter_504_status_retried_by_extractor():
    from acs_triage.decision.openai_adapter import OpenAIStructured
    import json as _json
    ok_body = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": _json.dumps(OK_OBJ)}]}],
               "usage": USAGE, "model": "gpt-test"}
    seq = [(504, {}, None), (200, {}, ok_body)]
    calls = []

    def transport(url, headers, body):
        calls.append(url)
        return seq.pop(0)

    ex = LLMExtractorV2(OpenAIStructured(model="m", effort="low", api_key="test-dummy", transport=transport), name="m", sleep=lambda s: None)
    assert ex("有。", QB["Q-DIAPH-01"]) == {"diaphoresis": True} and len(calls) == 2


def test_r9_extractor_clients_use_longer_timeout(monkeypatch):
    from acs_triage.decision.openai_adapter import OpenAIStructured
    assert EXTRACT_TIMEOUT_S == 600
    assert make_extractor("gemma").client.transport.keywords == {"timeout": 600}
    monkeypatch.setenv("ACS_OPENAI_API_KEY", "test-dummy")                 # 假值：只建 client，不連網
    gpt = make_extractor("gpt")
    assert gpt.client.transport.keywords == {"timeout": 600} and gpt.max_retries == 2
    assert OpenAIStructured(model="m", effort="low", api_key="k").transport.keywords == {"timeout": 300}   # 其他用途不變


class OpeningTimesOut:
    """開場白一律逾時；回答句回「不知道」（依 schema 填合法的空答案）。"""

    def ask(self, system, user, schema, name):
        if name == "opening_v2":
            raise TimeoutError()
        asked = {}
        for k, v in schema["properties"]["asked"]["properties"].items():
            asked[k] = {"evidence": "", "stance": "unclear", "status": "dont_know", "agreement": "unclear"}.get(k)
            if asked[k] is None:
                asked[k] = "沒有重新回答" if k == "reply_answer" else (v["enum"][0] if "enum" in v else 0)
        return {"asked": asked, "mentions": [], "unclassified": []}, USAGE, "fake"


def test_r9_closed_loop_failures_counted_in_errors():
    from sim.closed_loop import FailureTap, UsedKeys, dev_metrics
    c = next(x for x in all_cases() if x.id == "S-MID-01")
    ex = LLMExtractorV2(OpeningTimesOut(), name="fake", sleep=lambda s: None)                # 開場白三次都逾時
    tap = FailureTap(UsedKeys(ex))
    r = run_case(c, patient=ScriptedPatient(c), extractor=tap)
    assert tap.failures[0] == {"q": None, "confirm": False, "error": "TimeoutError"} and len(tap.failures) == 1
    m = dev_metrics([{"case": c, "result": r, "patient": None, "error": None, "extract_failures": tap.failures}])
    assert m["errors"] == [("S-MID-01", "extract_failed opening: TimeoutError")]


def test_r9_replay_cell_failures_counted():
    ex = LLMExtractorV2(Flaky([TimeoutError()] * 3), name="fake", sleep=lambda s: None)
    tr = [{"case_id": "X", "opening_zh": "胸口悶。", "turns": [{"q": "Q-DIAPH-01", "utterance_zh": "有。"}]}]
    ex("胸口悶。", None)
    ex("有。", QB["Q-DIAPH-01"])
    assert failed_calls(ex, tr, {}) == [("X", None)]


# ---------------------------------------------------------------- R8：以「天」表達的時序（程式防護）
from sim.llm_extract_v2 import days_only_weeks, parse  # noqa: E402
from sim.llm_extract_v2 import mention_slots  # noqa: E402


@pytest.mark.parametrize("text,expect", [
    ("我有冠心症，前天開始走路會胸悶，昨天含了一次舌下片有效，今天還沒發作，休息時沒有。", (True, 0.29)),   # S-MID-19
    ("我爸爸有心臟病，這兩天說胸口不太舒服，但他現在不在我旁邊。", (True, 0.29)),                          # S-INSUF-07
    ("這兩個禮拜變成一個禮拜兩三次", (False, None)), ("上個月放支架", (False, None)), ("過去一年都是走很快", (False, None)),
    ("這幾天腳有點腫", (True, None)), ("最近每天都會悶", (False, None)), ("大概三天前開始", (True, 0.43)),
    ("十二天前", (True, 1.71)),
])
def test_r8_days_only_weeks(text, expect):
    assert days_only_weeks(text) == expect


def _opening(**vals):
    ev = vals.pop("_evidence", [])
    return {"evidence": [{"slot": s, "quote": t} for s, t in ev], **{k: vals.get(k) for k in mention_slots()}, "unclassified": []}


def test_r8_opening_day_onset_converted_week_and_month_kept():
    t = "我有冠心症，前天開始走路會胸悶，昨天含了一次舌下片有效，今天還沒發作，休息時沒有。"
    slots, diag = parse(_opening(onset_weeks_ago=2.0, _evidence=[("onset_weeks_ago", "前天開始")]), t, None)
    assert slots["onset_weeks_ago"] == 0.29 and any(g["guard"] == "onset_days_as_weeks" for g in diag["guards"])
    slots, _ = parse(_opening(onset_weeks_ago=2.0), "我爸爸有心臟病，這兩天說胸口不太舒服，但他現在不在我旁邊。", None)   # 沒列 evidence → 看整句
    assert slots["onset_weeks_ago"] == 0.29
    t3 = "我有冠心症，這兩個禮拜晚上躺下會覺得比較喘要墊高枕頭，白天走路還可以，胸口不會痛。"
    assert parse(_opening(onset_weeks_ago=2.0, _evidence=[("onset_weeks_ago", "這兩個禮拜")]), t3, None)[0]["onset_weeks_ago"] == 2.0
    t8 = "上個月放支架，傷口沒問題，最近走路會有一點悶，比放支架前輕很多，但以前是完全沒有。"
    assert parse(_opening(onset_weeks_ago=4.0), t8, None)[0]["onset_weeks_ago"] == 4.0     # 月：不是防護範圍（D-55 的 4.0 要靠提示）
    assert parse(_opening(onset_weeks_ago=0.29), t, None)[0]["onset_weeks_ago"] == 0.29    # < 1 週不動
    assert parse(_opening(onset_weeks_ago=1.0), "這幾天胸口悶", None)[0]["onset_weeks_ago"] is None     # 說不出天數 → 未知（追問）


def test_r8_answer_asked_and_mention_converted():
    q = QB["Q-ONSET-WEEKS-01"]
    obj = {"asked": {"evidence": "大概前天開始的", "status": "answered", "value": 2}, "mentions": [], "unclassified": []}
    assert parse(obj, "大概前天開始的。", q)[0]["onset_weeks_ago"] == 0.29
    obj = {"asked": {"evidence": "大概一個禮拜前開始的", "status": "answered", "value": 1}, "mentions": [], "unclassified": []}
    assert parse(obj, "大概一個禮拜前開始的。", q)[0]["onset_weeks_ago"] == 1.0                 # 開發集句子：週 → 不動
    obj = {"asked": {"evidence": "沒有", "stance": "no"}, "unclassified": [],
           "mentions": [{"slot": "onset_weeks_ago", "evidence": "這兩天才開始", "value": "2"}]}
    assert parse(obj, "沒有，這兩天才開始的。", QB["Q-DIAPH-01"])[0]["onset_weeks_ago"] == 0.29


@pytest.mark.parametrize("chest", [dict(symptom_character=ch) for ch in FLOOR["characters"]]
                         + [dict(symptom_character=None, chest_discomfort_mentioned=True)])
def test_r8_closer_onset_never_less_urgent_with_chest_symptom(chest):
    """防護只把 onset_weeks_ago 變近：有胸部症狀時，開發集 119 例的事實 × 時序 × PCI 後較輕與否，改成 0.29 週不會比 2／4 週不急
    （DV-2 不成立後最不急的 T3-POST-PCI-MILDER 由 R7 提高到 T2）。已知限制：沒有胸部症狀時 dv2_new_stable_weeks 不要求胸部症狀
    （§5.5 寫的是「新發勞累性缺血等價症狀」，既有程式與文件不一致），否認胸部症狀卻有新發＋勞累型＋≥2 週的矛盾狀態會因變近失去 T2，見 D-56。"""
    from sim.runner import _urgency
    for c in all_cases():
        for timing in ("today", "yesterday_within_24h", "over_24h", "unknown", None):
            for extra in ({}, {"symptom_vs_pre_pci": "milder", "pci_history": True}):
                for far in (2.0, 4.0):
                    base = {**c.slots, **extra, **chest, "onset_new": True, "exertion_relation": "exertion_only",
                            "last_episode_timing": timing, "rest_symptom": False, "threshold_decreased": False}
                    near = _urgency(SlotState({**base, "onset_weeks_ago": 0.29}))
                    assert near <= _urgency(SlotState({**base, "onset_weeks_ago": far})), (c.id, timing, extra, far)


def test_ruling_t9_fallback_t1_keeps_provisional_expedite():
    """Clinical Owner 2026-11-16：護理師不可得、T9 備援為 T1 時保留暫判 T2／T3 的 expedite（「T1 不附」的唯一例外，router 現行行為）；
    待追蹤檢查的 T1 下限仍不附。"""
    from acs_triage.pathway import route
    st = SlotState({"symptom_character": "tightness", "last_episode_timing": "over_24h", "antiplatelet_interrupted": True})
    d = E.decide(st)
    assert (d.provisional_tier, d.tier) == (2, 9) and "expedite" in d.pathway_actions
    pw = route(d, st, nurse_available=False)
    assert pw.tier == 1 and "tier9_fallback_nurse_unavailable" in pw.actions and "expedite" in pw.actions
    st2 = SlotState({"symptom_character": "tightness", "last_episode_timing": "over_24h", "antiplatelet_interrupted": True,
                     "pending_abnormal_test": True})
    d2 = E.decide(st2)
    assert d2.provisional_tier == 1 and "expedite" not in d2.pathway_actions
    pw2 = route(d2, st2, nurse_available=False)
    assert pw2.tier == 1 and "expedite" not in pw2.actions


# ---------------------------------------------------------------- 2026-11-17 裁定 #3：「改成提到就問一次確認」（LLM 抽取器路徑）
# 開場白與順口的 reproducible_mechanical＝true 一律不寫入，改記 reproducible_mechanical_mentioned；紅旗題後問一次 Q-REPRO-01，
# 只有直接回答寫入。關鍵詞路徑不變（已知限制 (a)，另外修）。
from acs_triage.extract import extract  # noqa: E402
from acs_triage.prompter import Prompter  # noqa: E402
from sim.runner import _write_mentions  # noqa: E402

CASES = {c.id: c for c in all_cases()}
FLAG = "reproducible_mechanical_mentioned"
REDFLAGS = {q.id for q in QB.values() if q.priority == "redflag"}
# 最終驗收第二輪探針（probe_palp2.py）的 33 句：非按壓、否定、不確定、手勢、問句複述，以及真的按壓痛——一律不得直接寫入
PROBE2 = [
    "按下去的時候沒什麼感覺，但走路會痛", "壓著不會痛但咳嗽會痛", "摸到那邊是腫腫的，不痛", "碰到胸口的衣服會痛",
    "按下去還好走路的時候胸口會痛", "摸起來還好爬樓梯才會痛", "按下去感覺還好但是休息的時候也會痛", "按著扶手爬樓梯胸口會痛",
    "手按著胸口才能減輕疼痛", "我都按著胸口忍痛", "按著胸口會舒服一點痛比較少", "你是說按下去會痛嗎？沒有啦",
    "醫生問我按下去會痛嗎？我說還好。", "按下去應該會痛吧我也說不準", "按下去可能會痛吧", "按下去哪會痛", "按下去並非會痛",
    "之前按下去會痛現在已經好了", "壓著棉被睡覺起來胸口痛", "碰到那邊的冷水會痛", "摸到冰的東西胸口會痛", "按下門鈴的時候胸口痛",
    "按下去痛的是手指", "壓下去心臟會悶悶的痛", "按到胸口那邊就喘就痛",
    "胸口按下去會痛", "按壓那邊會痛", "摸到胸口那裡會痛", "碰到那邊會疼", "按著會痛", "胸口按下去會痛 深呼吸也痛",
    "按下去會痛喔", "那邊按到胸口會痛",
]


def _asked(q, v):
    if q.answer_type == "yes_no":
        return {"evidence": "", "stance": {True: "yes", False: "no"}.get(v, "unclear")}
    return {"evidence": "沒有" if v == "none" else "這個", "status": "dont_know" if v is None else "answered", "value": v}


class ParseFake:
    """假 LLM 抽取器：模型輸出＝被問那題的病人事實（answers 可覆蓋）＋mentions（題號 → 順口說 reproducible_mechanical＝true 的原句），
    開場白＝opening 欄位值；都經 parse()（與閉環同一條路）。複誦回答直接回事實（不經 parse）。"""

    def __init__(self, case, opening=None, mentions=None, answers=None, opening_quote="胸口肌肉按下去會痛"):
        self.case, self.opening, self.mentions, self.answers = case, opening or {}, mentions or {}, answers or {}
        self.quote = opening_quote

    def __call__(self, text, q, confirm_prompt=None):
        if q is None:
            return parse(_opening(**self.opening, _evidence=[("reproducible_mechanical", self.quote)]), text, None)[0]
        v = self.answers.get(q.id, ScriptedPatient(self.case).answer(q).value)
        if confirm_prompt is not None:
            return {q.slot_id: v}
        said = self.mentions.get(q.id, [])
        obj = {"asked": _asked(q, v), "unclassified": [],
               "mentions": [{"slot": "reproducible_mechanical", "evidence": t, "value": "true"} for t in said]}
        return parse(obj, "，".join(said) or "嗯。", q)[0]


def _qs(r):
    return [t.question_id for t in r.turns]


def _kw(cid):
    return {k: v for k, v in extract(CASES[cid].opening_zh).items() if v is not None}


def _true_from_start(cid):
    """對照：一開始就是 true（今天的關鍵詞路徑／裁定前的 LLM 路徑）。"""
    c = CASES[cid]
    return run_case(c, extractor=lambda text, q, confirm_prompt=None: dict(_kw(cid)) if q is None
                    else {q.slot_id: ScriptedPatient(c).answer(q).value})


@pytest.mark.parametrize("cid", ["S-MID-14", "S-MID-14#0"])
def test_repro_opening_flag_asks_once_after_redflags_then_same_as_true(cid):
    """S-MID-14 開場白（模型輸出 true）→ 只記旗標；紅旗題問完後第 5 題問 Q-REPRO-01 → 答「會」→ 之後與「一開始就是 true」相同（＋1 題），
    S-MID-14 為 T3（T3-MECHANICAL），#0（走路會更痛）為 T0。"""
    c = CASES[cid]
    assert _kw(cid)["reproducible_mechanical"] is True and c.slots["reproducible_mechanical"] is True      # 事實有，病人答得出來
    r = run_case(c, extractor=ParseFake(c, opening=_kw(cid)))
    ref = _true_from_start(cid)
    qs = _qs(r)
    assert qs.count("Q-REPRO-01") == 1 and qs.index("Q-REPRO-01") == 4 and set(qs[:4]) <= REDFLAGS
    assert [x for x in qs if x != "Q-REPRO-01"] == _qs(ref) and r.n_questions == ref.n_questions + 1
    assert r.final_state._values["reproducible_mechanical"].asked_by_question_id == "Q-REPRO-01"
    assert (r.final.tier, r.final.hard_stop, r.final.evidence) == (ref.final.tier, ref.final.hard_stop, ref.final.evidence)
    assert r.final.tier == c.truth_tier and ("T3-MECHANICAL" in r.final.evidence) == (cid == "S-MID-14")


@pytest.mark.parametrize("said", [["現在沒在咳就不會痛"], ["咳嗽的時候胸口會痛"], ["按下去不會痛"]])
@pytest.mark.parametrize("reply", [None, False])
def test_repro_mention_flag_s_mid_16_asked_then_t2(said, reply):
    """S-MID-16（11-16 Gemma 閉環的 under-triage）：Q-ONGOING-01 回答裡順口的 true（含「按下去不會痛」）只記旗標 → 紅旗題後問 Q-REPRO-01，
    答不知道或「不會」→ T3-COUGH 由 R7 提高到 T2＝truth；其餘問題序列與 Scripted 相同。"""
    c = CASES["S-MID-16"]
    r = run_case(c, extractor=ParseFake(c, opening=_kw("S-MID-16"), mentions={"Q-ONGOING-01": said}, answers={"Q-REPRO-01": reply}))
    qs = _qs(r)
    assert qs.count("Q-REPRO-01") == 1 and qs.index("Q-REPRO-01") == 4 and set(qs[:4]) <= REDFLAGS
    assert [x for x in qs if x != "Q-REPRO-01"] == _qs(run_case(c))
    assert r.final_state.get("reproducible_mechanical") is reply and r.final_state.get(FLAG) is True
    assert (r.final.tier, r.final.hard_stop) == (2, False) and "T3-MECHANICAL" not in r.final.evidence


def test_repro_keyword_path_unchanged_limitation_a():
    """Clinical Owner 2026-11-17：關鍵詞路徑照舊（已知限制 (a)，M4 前另外修）——仍直接寫 true、不記旗標，Scripted 不問 Q-REPRO-01。"""
    for t in ("按下去不會痛", "胸口按下去不會痛，深呼吸也不會痛", "搬東西的時候會悶", CASES["S-MID-14"].opening_zh):
        x = extract(t)
        assert x["reproducible_mechanical"] is True and FLAG not in x
    assert "Q-REPRO-01" not in _qs(run_case(CASES["S-MID-14"]))


@pytest.mark.parametrize("text", PROBE2)
def test_repro_probe2_sentences_never_write_slot(text):
    """probe_palp2.py 的每一句：模型輸出 true（順口或開場白）都不寫入 reproducible_mechanical，只記旗標。"""
    obj = {"asked": {"evidence": "", "stance": "unclear"}, "unclassified": [],
           "mentions": [{"slot": "reproducible_mechanical", "evidence": text, "value": "true"}]}
    slots, diag = parse(obj, text, QB["Q-ONGOING-01"])
    assert "reproducible_mechanical" not in slots and slots[FLAG] is True
    assert [g["guard"] for g in diag["guards"] if g["slot"] == "reproducible_mechanical"] == ["repro_mention_not_used"]
    slots, _ = parse(_opening(reproducible_mechanical=True, _evidence=[("reproducible_mechanical", text)]), text, None)
    assert "reproducible_mechanical" not in slots and slots[FLAG] is True


def test_repro_direct_answer_used():
    """直接回答 Q-REPRO-01 照寫（含模型把答案寫在 mentions），不記旗標；閉環中被問那題由 run_case 直接寫入。"""
    q = QB["Q-REPRO-01"]
    slots, diag = parse({"asked": {"evidence": "會，按下去會痛", "stance": "yes"}, "mentions": [], "unclassified": []}, "會，按下去會痛。", q)
    assert slots == {"reproducible_mechanical": True} and diag["guards"] == []
    obj = {"asked": {"evidence": "", "stance": "unclear"}, "unclassified": [],
           "mentions": [{"slot": "reproducible_mechanical", "evidence": "轉身會痛", "value": "true"}]}
    slots, diag = parse(obj, "轉身會痛。", q)
    assert slots == {"reproducible_mechanical": True} and [g["guard"] for g in diag["guards"]] == ["asked_value_from_mentions"]
    st = SlotState({})
    assert _write_mentions(st, {"reproducible_mechanical": True}, "reproducible_mechanical", source="m") == []
    assert st.get("reproducible_mechanical") is None


def test_repro_asked_at_most_once():
    """答不知道、之後每題又順口說一次：Q-REPRO-01 只問一次（該欄仍未知）。Prompter 本身：問過就不再給。"""
    c = CASES["S-MID-14"]
    later = {q: ["胸口按下去會痛"] for q in ("Q-EXERTION-01", "Q-REST-01", "Q-THRESHOLD-01", "Q-NTG-01", "Q-FREQ-01", "Q-ONSET-01")}
    r = run_case(c, extractor=ParseFake(c, opening=_kw("S-MID-14"), mentions=later, answers={"Q-REPRO-01": None}))
    assert _qs(r).count("Q-REPRO-01") == 1 and r.final_state.get("reproducible_mechanical") is None
    st = SlotState({FLAG: True, "symptom_character": "pain", "ongoing_now": False, "presyncope": False, "diaphoresis": False,
                    "dyspnea_grade": "none"})
    d, p = E.decide(st), Prompter()
    assert p.repro_confirm_question(st, d, set()) == QB["Q-REPRO-01"]
    assert p.repro_confirm_question(st, d, {"Q-REPRO-01"}) is None


def test_repro_question_counts_toward_cap():
    """Q-REPRO-01 計入題數上限：上限 4（紅旗題剛好問完）→ 不問、到上限；上限 5 → 第 5 題就是它。"""
    c = CASES["S-MID-14"]
    r4 = run_case(c, extractor=ParseFake(c, opening=_kw("S-MID-14")), max_questions=4)
    assert r4.n_questions == len(r4.turns) == 4 and "Q-REPRO-01" not in _qs(r4) and r4.stop_reason == "max_questions"
    r5 = run_case(c, extractor=ParseFake(c, opening=_kw("S-MID-14")), max_questions=5)
    assert r5.n_questions == len(r5.turns) == 5 and _qs(r5)[4] == "Q-REPRO-01" and r5.stop_reason == "max_questions"


def test_repro_not_asked_at_hard_stop_or_other_t0():
    """Hard stop 不問（S-MID-14#1 冒汗）；T0 已由 T0-NEW-TODAY 以外的規則成立 → 不問；只靠 T0-NEW-TODAY → 定案前要問。"""
    c = CASES["S-MID-14#1"]
    r = run_case(c, extractor=ParseFake(c, opening=_kw("S-MID-14#1")))
    assert r.final.hard_stop and "Q-REPRO-01" not in _qs(r)
    p = Prompter()
    base = {FLAG: True, "symptom_character": "pain", "ongoing_now": False, "presyncope": False, "diaphoresis": False,
            "dyspnea_grade": "none", "onset_new": True, "last_episode_timing": "today"}
    st = SlotState(base)
    d = E.decide(st)
    assert d.provisional_tier == 0 and set(d.evidence) <= {"T0-NEW-TODAY", "T9-GATE"}
    assert p.repro_confirm_question(st, d, set()) == QB["Q-REPRO-01"]
    st2 = SlotState({**base, "rest_symptom": True})
    d2 = E.decide(st2)
    assert d2.provisional_tier == 0 and "T0-REST-NEW" in d2.evidence and p.repro_confirm_question(st2, d2, set()) is None
    st3 = SlotState({**base, "reproducible_mechanical": True})
    assert E.decide(st3).provisional_tier == 3                      # 答「會」之後與一開始就是 true 相同（T3-MECHANICAL）


def test_repro_mention_false_still_used():
    """false（較急的方向）照舊採用：開場白、回答句順口、_write_mentions 都寫入，不記旗標。"""
    st = SlotState({})
    assert _write_mentions(st, {"reproducible_mechanical": False}, "ongoing_now", source="m") == []
    assert st.get("reproducible_mechanical") is False
    obj = {"asked": {"evidence": "", "stance": "unclear"}, "unclassified": [],
           "mentions": [{"slot": "reproducible_mechanical", "evidence": "按胸口不會痛", "value": "false"}]}
    slots, diag = parse(obj, "沒有，按胸口不會痛。", QB["Q-ONGOING-01"])
    assert slots["reproducible_mechanical"] is False and FLAG not in slots and diag["guards"] == []
    slots, _ = parse(_opening(reproducible_mechanical=False, _evidence=[("reproducible_mechanical", "深呼吸不會痛")]),
                     "胸口悶悶的，深呼吸不會痛。", None)
    assert slots["reproducible_mechanical"] is False and FLAG not in slots


def test_repro_flag_slot_not_sent_to_model_and_not_a_rule_input():
    """旗標不進送給模型的欄位清單與 schema；寫入旗標不改變規則結果。"""
    from sim.llm_extract_v2 import fields_zh
    assert FLAG not in mention_slots() and FLAG not in fields_zh() and slot_defs()[FLAG]["type"] == "yes_no"
    st = SlotState({"symptom_character": "pain", "cough_related": True, "exertion_relation": "rest_only"})
    st2 = st.copy()
    st2.set(FLAG, True, source="m")
    assert E.decide(st).evidence == E.decide(st2).evidence
