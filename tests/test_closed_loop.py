"""閉環模擬：runner 的 extractor 選項（預設關閉、行為不變）、病人對話前綴快取、premature 判定。全部用假 client，不打 API。"""
import json
from types import SimpleNamespace

import pytest

from acs_triage.loaders import question_by_id
from acs_triage.rules import SlotState
from sim.cases import all_cases
from sim.closed_loop import CachedLLMPatient, PatientCache, dev_metrics, hs_supported, reconstruct
from sim.patient import ScriptedPatient
from sim.runner import run_case

QB = question_by_id()
CASES = {c.id: c for c in all_cases()}


def _key(r):
    return (r.final.tier, r.final.hard_stop, [t.question_id for t in r.turns], [t.answer for t in r.turns], r.n_confirms)


def test_default_off_is_unchanged():
    for c in list(CASES.values())[:40]:
        assert _key(run_case(c)) == _key(run_case(c, extractor=None, to_traditional=None))


class StructuredEcho:
    """假抽取器：回傳 ScriptedPatient 的結構化值（開場白給固定值）；記錄每次呼叫。"""

    def __init__(self, case, opening=None, override=None):
        self.case, self.opening, self.override, self.calls = case, opening or {}, override or {}, []

    def __call__(self, text, q, confirm_prompt=None):
        self.calls.append((text, q.id if q else None, confirm_prompt))
        if q is None:
            return dict(self.opening)
        if q.id in self.override:
            return {q.slot_id: self.override[q.id]}
        return {q.slot_id: ScriptedPatient(self.case).answer(q).value}


def test_closed_loop_uses_extracted_values_and_keeps_structured_for_comparison():
    c = CASES["S-ACUTE-01"]
    from acs_triage.extract import extract
    ex = StructuredEcho(c, opening=extract(c.opening_zh))
    r = run_case(c, extractor=ex, to_traditional=lambda s: s + "（繁）")
    base = run_case(c)
    assert (r.final.tier, r.final.hard_stop) == (base.final.tier, base.final.hard_stop)
    assert ex.calls[0] == (c.opening_zh + "（繁）", None, None)                      # 開場白也交給抽取器，且先轉繁
    assert all(t.structured_answer == t.answer for t in r.turns if t.confirm_prompt_zh is None)
    assert r.opening_extracted == extract(c.opening_zh)


def test_closed_loop_extracted_value_drives_decision():
    c = next(x for x in CASES.values() if x.truth_hard_stop and x.truth_rf == "RF-06" and x.id == "S-MID-13#0")
    from acs_triage.extract import extract
    ok = run_case(c, extractor=StructuredEcho(c, opening=extract(c.opening_zh)))
    assert ok.final.hard_stop
    # 抽取器把「有冒冷汗」抽成未知 → 紅旗題值未知 → 複誦；複誦回答也抽成未知 → 不是 Hard stop
    ex = StructuredEcho(c, opening=extract(c.opening_zh), override={"Q-DIAPH-01": None})
    r = run_case(c, extractor=ex)
    t = next(t for t in r.turns if t.question_id == "Q-DIAPH-01")
    assert t.structured_answer is True and t.pre_confirm_answer is None and t.confirm_prompt_zh is not None
    assert any(cp == t.confirm_prompt_zh for _, qid, cp in ex.calls if qid == "Q-DIAPH-01")   # 複誦句當 context 傳入
    assert not r.final.hard_stop and t.confirm_structured is True


def test_closed_loop_mentions_written_but_not_over_asked():
    c = CASES["S-ACUTE-01"]
    from acs_triage.extract import extract

    class Mention(StructuredEcho):
        def __call__(self, text, q, confirm_prompt=None):
            out = super().__call__(text, q, confirm_prompt)
            if q is not None and q.id != "Q-ONGOING-01":
                out["nausea"] = True
                out["ongoing_now"] = True          # 已直接問過 → 不得覆蓋
            return out

    r = run_case(c, extractor=Mention(c, opening=extract(c.opening_zh)))
    asked = {t.question_id: t.answer for t in r.turns}
    if "Q-ONGOING-01" in asked and len(r.turns) > 1:
        assert r.final_slots["ongoing_now"] == asked["Q-ONGOING-01"]
    assert r.final_slots.get("nausea") is True and "Q-NAUSEA-01" not in asked


# ---------------------------------------------------------------- 病人快取
class FakeAnthropic:
    def __init__(self, replies):
        self.replies, self.n = list(replies), 0
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.n += 1
        utt, dk, ans = self.replies.pop(0)
        txt = json.dumps({"utterance_zh": utt, "dont_know": dk, "answer": ans}, ensure_ascii=False)
        return SimpleNamespace(stop_reason="end_turn", model="fake-opus", content=[SimpleNamespace(type="text", text=txt)],
                               usage=SimpleNamespace(input_tokens=10, output_tokens=20, cache_creation_input_tokens=100,
                                                     cache_read_input_tokens=1000))


def test_reconstruct():
    assert reconstruct(None, "不知道")["dont_know"] and reconstruct("unknown", "不記得")["dont_know"]
    assert reconstruct(True, "有") == {"utterance_zh": "有", "dont_know": False, "answer": True}


def test_patient_cache_seed_live_and_reuse():
    c = CASES["S-ACUTE-01"]
    q1, q2 = QB["Q-SYNCOPE-01"], QB["Q-DIAPH-01"]
    cache = PatientCache()                                       # 預設：目前病人模型／effort／prompt_version
    cache.seed([{"case_id": c.id, "turns": [{"q": q1.id, "value": False, "utterance_zh": "沒有耶。"}]}], source="seed:x")
    p = CachedLLMPatient(c, cache=cache, live=False)
    assert p.answer(q1).value is False and p.n_cached == 1
    with pytest.raises(RuntimeError, match="patient_cache_miss"):
        p.answer(q2)
    fake = FakeAnthropic([("有，有冒冷汗。", False, True)])
    p2 = CachedLLMPatient(c, cache=cache, client=fake, live=True)
    p2.answer(q1)
    assert p2.answer(q2).value is True and fake.n == 1 and p2.n_live == 1 and p2.cost > 0
    p3 = CachedLLMPatient(c, cache=cache, client=FakeAnthropic([]), live=True)   # 同一串問句 → 重用，不再呼叫
    assert p3.answer(q1).value is False and p3.answer(q2).value is True and p3.n_live == 0
    assert p3.messages[-1]["role"] == "assistant" and len(p3.messages) == 4
    p4 = CachedLLMPatient(c, cache=cache, client=FakeAnthropic([("不知道。", True, False)]), live=True)
    assert p4.answer(q2).value is None and p4.n_live == 1                          # 不同前綴 → 新呼叫


def test_hs_supported_and_premature_adjustment():
    c = CASES["S-MID-13#0"]                     # truth RF-06（胸口不適＋冒冷汗）
    st = SlotState({"symptom_character": "epigastric", "diaphoresis": True})
    assert hs_supported(c, st)
    bad = SlotState({"symptom_character": "epigastric", "ongoing_now": True})          # 事實是現在沒事
    assert not hs_supported(c, bad)
    from acs_triage.rules import RulesEngine
    d = RulesEngine().decide(bad)
    assert d.hard_stop
    r2 = run_case(c)
    r2.final, r2.final_state = d, bad
    m = dev_metrics([{"case": c, "result": r2, "patient": None, "error": None}])
    assert m["premature"] == [c.id] and m["hs_miss"] == [c.id] and m["false_hs"] == []


def test_seed_extractor_reuses_stage_a_outputs_keyed_by_traditional_text(tmp_path):
    from sim.closed_loop import seed_extractor
    from sim.llm_extract_v2 import LLMExtractorV2, meta_for

    class NoCall:
        def ask(self, *a):
            raise AssertionError("不該呼叫")

    meta = meta_for("gemma")
    raw = {"asked": {"evidence": "沒有", "stance": "no"}, "mentions": [], "unclassified": []}
    rec = {"q": "Q-DIAPH-01", "confirm_prompt": None, "text": "沒有，沒有冒汗。", "sent": "沒有,沒有冒汗。", "ok": True,
           "slots": {"diaphoresis": True}, "diag": {}, "raw": raw, "cost": 0.01, "latency_s": 1.0, "usage": {}, "model": "m"}
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"meta": {**meta, "code_sha256": "old"}, "records": [rec]}), encoding="utf-8")
    ex = LLMExtractorV2(NoCall(), name="m")
    assert seed_extractor(ex, p, meta) == 1
    assert ex("沒有,沒有冒汗。", QB["Q-DIAPH-01"]) == {"diaphoresis": False}        # 以目前程式重算；鍵＝轉繁後的句子
    assert ex.spent == 0.0
    p.write_text(json.dumps({"meta": {**meta, "rendered_sha256": "x"}, "records": [rec]}), encoding="utf-8")
    with pytest.raises(SystemExit):
        seed_extractor(LLMExtractorV2(NoCall(), name="m"), p, meta)


# ---------------------------------------------------------------- 順口值的寫入規則（adversarial，假抽取器）
from acs_triage.rules import RulesEngine  # noqa: E402
from sim.runner import _write_mentions  # noqa: E402
from sim.synth_eval import urgency  # noqa: E402


def test_asked_unknown_then_spontaneous_red_flag_is_written():
    """驗收 B1：Q-DIAPH-01 答不知道、之後別題順口說冒冷汗 → 要寫入並 Hard stop（不得被「問過」擋掉）。"""
    case = CASES["S-STABLE-01"]

    class P:
        def answer(self, q):
            from sim.patient import PatientReply
            return PatientReply(value=None, utterance_zh=f"答{q.id}", stt_confidence=1.0)

        def confirm(self, q, prompt_zh):
            return self.answer(q)

    order = []

    def ex(text, q, confirm_prompt=None):
        if q is None:
            return {"symptom_character": "tightness", "onset_new": False, "pattern_unchanged_duration_months": 24}
        order.append(q.id)
        out = {q.slot_id: None}
        if q.id != "Q-DIAPH-01" and "Q-DIAPH-01" in order and confirm_prompt is None:
            out["diaphoresis"] = True
        return out

    r = run_case(case, patient=P(), extractor=ex)
    assert "Q-DIAPH-01" in [t.question_id for t in r.turns]
    assert r.final.hard_stop and "RF-06" in r.final.rf_hits


def _dev_states():
    eng = RulesEngine()
    for c in list(CASES.values()):
        yield c, SlotState({k: v for k, v in c.slots.items() if v is not None}), eng


def test_mentions_never_make_known_values_less_urgent():
    """把每個 case 已知 slot 逐一換成每個可能的順口值：寫入後的急迫度（Hard stop＝-1、T9 依備援）不得比寫入前不急。"""
    from acs_triage.loaders import slot_defs
    worse = []
    for c, st, eng in _dev_states():
        before = eng.decide(st)
        u0 = urgency(before.tier, before.hard_stop, st)
        for slot, v0 in list(st.as_dict().items()):
            d = slot_defs()[slot]
            alts = [True, False] if d["type"] == "yes_no" else (d.get("choices") or [])
            for v in alts:
                if v == v0:
                    continue
                s2 = st.copy()
                _write_mentions(s2, {slot: v}, "__none__", source="adv")
                after = eng.decide(s2)
                if s2.get(slot) != v0 and urgency(after.tier, after.hard_stop, s2) > u0:
                    worse.append((c.id, slot, v0, v))
    assert worse == []


def test_mentions_never_block_red_flag_upgrade():
    rf_slots = [q.slot_id for q in QB.values() if q.priority == "redflag" and q.answer_type == "yes_no"]
    for slot in rf_slots:
        for old in (False, None):
            st = SlotState({"symptom_character": "pressure"})
            st.set(slot, old, asked_by="Q-X", source="turn1")
            _write_mentions(st, {slot: True}, "__none__", source="adv")
            assert st.get(slot) is True
    st = SlotState({"symptom_character": "pressure", "diaphoresis": False})
    _write_mentions(st, {"diaphoresis": True}, "__none__", source="adv")
    assert RulesEngine().decide(st).hard_stop


def test_conflicts_recorded_in_run_result():
    c = CASES["S-ACUTE-01"]
    from acs_triage.extract import extract

    class Conf(StructuredEcho):
        def __call__(self, text, q, confirm_prompt=None):
            out = super().__call__(text, q, confirm_prompt)
            if q is not None and q.id != "Q-ONSET-01":
                out["onset_new"] = False                     # 開場白說第一次；順口說「以前就有」→ conflict
            return out

    r = run_case(c, extractor=Conf(c, opening={**extract(c.opening_zh), "onset_new": True}))
    assert r.final_slots["onset_new"] is True
    assert r.mention_conflicts and all(x["kind"] == "conflict" and x["slot"] == "onset_new" and x["known"] is True and x["mention"] is False
                                       and x["case_id"] == c.id and x["utterance_zh"] for x in r.mention_conflicts)


# ---------------------------------------------------------------- 保留集防護（load_set 換成丟例外：絕不讀到保留集）
def _guard_env(tmp_path, monkeypatch):
    import sim.closed_loop as cl

    def boom(name):
        raise RuntimeError("reached load_set")

    monkeypatch.setattr(cl, "FREEZE_PATH", tmp_path / "freeze.json")
    monkeypatch.setattr(cl, "HOLDOUT_REGISTRY", tmp_path / "runs.json")
    monkeypatch.setattr(cl, "load_set", boom)
    return cl


def _args(tmp_path, arm, out="out", extra=()):
    return ["--set", "holdout", "--arm", arm, "--cache-dir", str(tmp_path / "cache"), "--out", str(tmp_path / out), *extra]


@pytest.mark.parametrize("arm", ["gpt", "gemma", "structured"])
def test_holdout_requires_freeze_for_every_arm(tmp_path, monkeypatch, arm):
    cl = _guard_env(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="凍結"):
        cl.run_main(_args(tmp_path, arm))


def test_holdout_guards(tmp_path, monkeypatch):
    cl = _guard_env(tmp_path, monkeypatch)
    cl.freeze_main([])
    rec = json.loads(cl.FREEZE_PATH.read_text(encoding="utf-8"))
    assert set(rec["files"]) == set(cl.FROZEN_FILES) and {"sim/closed_loop.py", "sim/stt_synth_asr.py"} <= set(rec["files"])
    assert rec["rendered_sha256"] and rec["prompt_file_sha256"] and rec["frozen_at"]
    with pytest.raises(SystemExit, match="只做一次"):
        cl.freeze_main([])
    with pytest.raises(SystemExit, match="--limit"):
        cl.run_main(_args(tmp_path, "gpt", extra=["--limit", "3"]))
    for f in cl.FROZEN_FILES:                                   # 任何一個凍結檔的 sha256 不符 → 拒跑
        bad = {**rec, "files": {**rec["files"], f: "0" * 64}}
        cl.FREEZE_PATH.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(SystemExit, match="改動"):
            cl.run_main(_args(tmp_path, "structured"))
    cl.FREEZE_PATH.write_text(json.dumps({**rec, "rendered_sha256": "x"}), encoding="utf-8")
    with pytest.raises(SystemExit, match="改動"):
        cl.run_main(_args(tmp_path, "gpt"))
    cl.FREEZE_PATH.write_text(json.dumps(rec), encoding="utf-8")
    with pytest.raises(RuntimeError, match="reached load_set"):  # 全部通過 → 先登記、才讀資料
        cl.run_main(_args(tmp_path, "structured"))
    assert [r["arm"] for r in json.loads(cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8"))] == ["structured"]
    with pytest.raises(SystemExit, match="只跑一次"):            # 已登記 → 換 --out 也拒跑
        cl.run_main(_args(tmp_path, "structured", out="other"))
    (tmp_path / "out3").mkdir()
    (tmp_path / "out3" / "closed_holdout_gemma_limit3.json").write_text("{}")
    with pytest.raises(SystemExit, match="只跑一次"):            # --out 已有該 arm 的任何保留集輸出 → 拒跑
        cl.run_main(_args(tmp_path, "gemma", out="out3"))


def test_patient_cache_key_includes_model_effort_prompt_version(tmp_path):
    a = PatientCache("claude-opus-5-5", "medium", "0.3")
    b = PatientCache("claude-opus-5-5", "medium", "0.4")
    assert a.key("S-1", ["q"]) != b.key("S-1", ["q"])
    a.put(a.key("S-1", ["q"]), {"utterance_zh": "有", "dont_know": False, "answer": True})
    p = tmp_path / "c.json"
    a.save(p)
    with pytest.raises(SystemExit):
        b.load(p)
    c = PatientCache("claude-opus-5-5", "medium", "0.3")
    c.load(p)
    assert c.get(c.key("S-1", ["q"]))["answer"] is True


# ---------------------------------------------------------------- 第三輪驗收：Hard stop 升級一律放行、D-50 範圍只收最嚴重一級、前置檢查先於登記
def test_ongoing_timing_mention_escalates_to_hard_stop():
    """驗收 r3 ongoing_timing_test：開場白 today、Q-ONGOING-01 答未知，之後順口只抽到 last_episode_timing＝ongoing → RF-03。"""
    case = CASES["S-ACUTE-01"]

    class P:
        def answer(self, q):
            from sim.patient import PatientReply
            return PatientReply(value=None, utterance_zh="答", stt_confidence=1.0)

        def confirm(self, q, p):
            return self.answer(q)

    def ex(text, q, confirm_prompt=None):
        if q is None:
            return {"symptom_character": "tightness", "onset_new": True, "last_episode_timing": "today"}
        out = {q.slot_id: None}
        if q.id != "Q-ONGOING-01" and confirm_prompt is None:
            out["last_episode_timing"] = "ongoing"
        return out

    r = run_case(case, patient=P(), extractor=ex)
    assert r.final.hard_stop and "RF-03" in r.final.rf_hits and r.final_slots["last_episode_timing"] == "ongoing"


def test_no_blocked_hard_stop_escalation_and_no_new_underestimate():
    """驗收 r3 enum_mentions（開發集 sheet 狀態）：單一順口值直接寫入會 Hard stop 者，經 _write_mentions 也要 Hard stop；
    已知值不得被改得較不急。D-50 範圍的未知 slot 只收最嚴重一級（較不嚴重的不寫，狀態不變）。"""
    from acs_triage.loaders import slot_defs
    eng = RulesEngine()
    blocked, worse = [], []
    for c in CASES.values():
        base = SlotState({k: v for k, v in c.slots.items() if v is not None})
        d0 = eng.decide(base)
        u0 = urgency(d0.tier, d0.hard_stop, base)
        for slot, dfn in slot_defs().items():
            alts = [True, False] if dfn["type"] == "yes_no" else (dfn.get("choices") or [])
            old = base.get(slot)
            for v in alts:
                if v == old:
                    continue
                sm, sd = base.copy(), base.copy()
                _write_mentions(sm, {slot: v}, "__none__", source="adv")
                sd.set(slot, v, source="adv")
                dm = eng.decide(sm)
                if eng.decide(sd).hard_stop and not dm.hard_stop and not d0.hard_stop:
                    blocked.append((c.id, slot, old, v))
                if old is not None and urgency(dm.tier, dm.hard_stop, sm) > u0:
                    worse.append((c.id, slot, old, v))
    assert blocked == [] and worse == []


def test_d50_scope_unknown_slots_take_only_most_severe_mention():
    from sim.runner import _d50_top_values
    top = _d50_top_values()
    assert top["rest_symptom_first_time"] == {True} and top["dyspnea_grade"] == {"rest"}
    assert top["symptom_character"] == {"pressure", "tightness", "jaw_shoulder_heaviness"}
    for slot, low, high in (("rest_symptom_first_time", False, True), ("presyncope", False, True), ("dyspnea_grade", "exertional_daily", "rest"),
                            ("symptom_character", "vague", "pressure")):
        st = SlotState()                                         # 還沒問過 → 不收，之後照常直接問
        notes = _write_mentions(st, {slot: low}, "__none__", source="m")
        assert st.get(slot) is None and notes == [{"kind": "d50_not_most_severe", "slot": slot, "known": None, "mention": low}]
        st.set(slot, None, asked_by="Q-X", source="turn1")       # 問過、答未知 → 交給 run_case 立刻複誦
        notes = _write_mentions(st, {slot: low}, "__none__", source="m")
        assert st.get(slot) is None and notes == [{"kind": "d50_confirm", "slot": slot, "known": None, "mention": low, "question_id": "Q-X"}]
        _write_mentions(st, {slot: high}, "__none__", source="m")
        assert st.get(slot) == high
    st = SlotState()
    _write_mentions(st, {"recurrence": False, "last_episode_timing": "yesterday_within_24h"}, "__none__", source="m")
    assert st.get("recurrence") is False and st.get("last_episode_timing") == "yesterday_within_24h"   # D-50 範圍外照補


def test_rest_first_time_denial_mention_does_not_skip_q_rest_02():
    """驗收 r3 指出的 Q-REST-02 例：順口「以前也有」（rest_symptom_first_time＝False）不得補上未知 → Q-REST-02 照問、照 D-50。"""
    c = CASES["S-STABLE-01#0"]                                   # truth T0：休息時發作、首次
    from acs_triage.extract import extract

    class Mention(StructuredEcho):
        def __call__(self, text, q, confirm_prompt=None):
            out = super().__call__(text, q, confirm_prompt)
            if q is not None and q.id == "Q-REST-01":
                out["rest_symptom_first_time"] = False
            return out

    r = run_case(c, extractor=Mention(c, opening=extract(c.opening_zh)))
    qs = [t.question_id for t in r.turns]
    assert "Q-REST-01" in qs and "Q-REST-02" in qs and r.final.tier == 0
    assert any(x["kind"] == "d50_not_most_severe" and x["slot"] == "rest_symptom_first_time" for x in r.mention_conflicts)


def _frozen(tmp_path, monkeypatch):
    cl = _guard_env(tmp_path, monkeypatch)
    cl.freeze_main([])
    return cl


def test_holdout_precheck_failures_do_not_register(tmp_path, monkeypatch):
    cl = _frozen(tmp_path, monkeypatch)
    import sim.llm_extract_v2 as v2
    monkeypatch.delenv("ACS_PATIENT_LLM_KEY", raising=False)
    for _ in range(2):                                           # 缺金鑰 → exit 2、不登記、可重試（不會被當成已跑過）
        with pytest.raises(SystemExit) as e:
            cl.run_main(_args(tmp_path, "gpt"))
        assert e.value.code == 2 and not cl.HOLDOUT_REGISTRY.exists()
    monkeypatch.setenv("ACS_PATIENT_LLM_KEY", "dummy-not-used")
    monkeypatch.delenv("ACS_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(v2, "load_to_tw", lambda: (lambda s: s))
    with pytest.raises(SystemExit):                              # gpt 抽取金鑰缺少
        cl.run_main(_args(tmp_path, "gpt"))
    assert not cl.HOLDOUT_REGISTRY.exists()

    def no_opencc():
        raise SystemExit("opencc 無法 import")
    monkeypatch.setattr(v2, "load_to_tw", no_opencc)
    with pytest.raises(SystemExit, match="opencc"):
        cl.run_main(_args(tmp_path, "gemma"))
    assert not cl.HOLDOUT_REGISTRY.exists()
    monkeypatch.setattr(v2, "load_to_tw", lambda: (lambda s: s))

    def no_lms(base_url, model):
        raise SystemExit("LM Studio 連不上")
    monkeypatch.setattr(cl, "check_lmstudio", no_lms)
    with pytest.raises(SystemExit, match="LM Studio"):
        cl.run_main(_args(tmp_path, "gemma"))
    assert not cl.HOLDOUT_REGISTRY.exists()
    monkeypatch.setattr(cl, "HOLDOUT_REFERENCE", tmp_path / "no_such_reference.json")
    with pytest.raises(SystemExit, match="輸入檔不存在"):
        cl.run_main(_args(tmp_path, "structured"))
    assert not cl.HOLDOUT_REGISTRY.exists()
    monkeypatch.undo()


def test_check_lmstudio_reports_unreachable_and_not_loaded(monkeypatch):
    import io
    import urllib.request

    import sim.closed_loop as cl

    def fake(url, timeout=5):
        if url.endswith("/v1/models"):
            return io.BytesIO(json.dumps({"data": [{"id": "m"}]}).encode())
        return io.BytesIO(json.dumps({"data": [{"id": "m", "state": "not-loaded"}]}).encode())
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    with pytest.raises(SystemExit, match="未載入"):
        cl.check_lmstudio("http://127.0.0.1:1234/v1", "m")
    with pytest.raises(SystemExit, match="沒有模型"):
        cl.check_lmstudio("http://127.0.0.1:1234/v1", "other")

    def down(url, timeout=5):
        raise OSError("refused")
    monkeypatch.setattr(urllib.request, "urlopen", down)
    with pytest.raises(SystemExit, match="連不上"):
        cl.check_lmstudio("http://127.0.0.1:1234/v1", "m")


# ---------------------------------------------------------------- 第四輪驗收：D-50 slot 未知時的順口值（收 Hard stop 升級；問過的題立刻複誦）
class _UnknownPatient:
    def answer(self, q):
        from sim.patient import PatientReply
        return PatientReply(value=None, utterance_zh="答", stt_confidence=1.0)

    def confirm(self, q, p):
        from sim.patient import PatientReply
        return PatientReply(value=None, utterance_zh="確認", stt_confidence=1.0)


@pytest.mark.parametrize("val", ["epigastric", "pain", "vague"])
@pytest.mark.parametrize("rf", [("diaphoresis", True), ("ongoing_now", True)])
def test_asked_but_unclassified_character_is_not_stuck(val, rf):
    """驗收 r4 stuck_character_test：Q-CHARACTER-01 問過但抽不出（None），之後順口說「上腹悶脹／會痛／說不上來」
    → 立刻對 Q-CHARACTER-01 複誦（以順口值當解讀值；複誦回答也抽不出 → 依 resolve 規則保留順口值）→ 胸部紅旗題照問 → Hard stop。"""
    case = CASES["S-MID-13#0"]
    seen = []

    def ex(text, q, confirm_prompt=None):
        if q is None:
            return {"onset_new": True, "last_episode_timing": "today"}
        seen.append((q.id, confirm_prompt))
        out = {q.slot_id: None}
        if confirm_prompt is None and q.slot_id == rf[0]:
            out[q.slot_id] = rf[1]
        if confirm_prompt is None and any(x == "Q-CHARACTER-01" for x, _ in seen) and q.id != "Q-CHARACTER-01":
            out["symptom_character"] = val
        return out

    r = run_case(case, patient=_UnknownPatient(), extractor=ex)
    assert r.final.hard_stop, (r.final.tier, r.stop_reason, r.final_slots.get("symptom_character"))
    assert r.final_slots["symptom_character"] == val
    assert [m["question_id"] for m in r.mention_confirms] == ["Q-CHARACTER-01"]
    assert any(qid == "Q-CHARACTER-01" and cp and f"『" in cp for qid, cp in seen)      # 複誦句當 context 傳給抽取器


def test_no_blocked_hard_stop_escalation_with_d50_slots_blank():
    """驗收 r4 enum_r4：sheet 狀態再加「每個 D-50 slot 設為未知」的變體，單一順口值直接寫入會 Hard stop 者，經 _write_mentions
    也要 Hard stop（或交由 run_case 複誦：d50_confirm 只在不會 Hard stop 時才出現）。"""
    from acs_triage.loaders import slot_defs
    from sim.runner import _d50_top_values
    eng = RulesEngine()
    states = []
    for c in CASES.values():
        base = {k: v for k, v in c.slots.items() if v is not None}
        states.append(base)
        states += [{k: v for k, v in base.items() if k != s} for s in _d50_top_values() if s in base]
    blocked = []
    for init in states:
        base = SlotState(init)
        if eng.decide(base).hard_stop:
            continue
        for slot, dfn in slot_defs().items():
            alts = [True, False] if dfn["type"] == "yes_no" else (dfn.get("choices") or [])
            for v in alts:
                if v == base.get(slot):
                    continue
                sd = base.copy()
                sd.set(slot, v, source="adv")
                if not eng.decide(sd).hard_stop:
                    continue
                sm = base.copy()
                _write_mentions(sm, {slot: v}, "__none__", source="adv")
                if not eng.decide(sm).hard_stop:
                    blocked.append((slot, base.get(slot), v))
    assert blocked == []


def test_asked_unknown_rest_first_time_denial_mention_triggers_confirm_not_silent_downgrade():
    """驗收 r3／r4：Q-REST-02 問過答未知，之後順口「以前也有」（False）→ 立刻複誦 Q-REST-02（解讀值＝沒有）；
    複誦回答抽不出 → 依 D-50「未經確認的紅旗否認不採信」維持未知，不得靜默變成 False（T0→T3）。"""
    c = CASES["S-STABLE-01#0"]
    from acs_triage.extract import extract
    calls = []

    class Ex(StructuredEcho):
        def __call__(self, text, q, confirm_prompt=None):
            calls.append((q.id if q else None, confirm_prompt))
            if q is not None and q.id == "Q-REST-02":
                return {q.slot_id: None}                       # 問的時候抽不出
            out = super().__call__(text, q, confirm_prompt)
            if q is not None and confirm_prompt is None and any(x == "Q-REST-02" for x, _ in calls[:-1]):
                out["rest_symptom_first_time"] = False         # 之後順口說「以前也有」
            return out

    r = run_case(c, extractor=Ex(c, opening=extract(c.opening_zh)))
    qs = [t.question_id for t in r.turns]
    assert "Q-REST-02" in qs
    after = qs[qs.index("Q-REST-02") + 1:]
    if after:                                                  # Q-REST-02 之後還有題 → 順口值出現 → 必須觸發複誦
        assert [m["question_id"] for m in r.mention_confirms] == ["Q-REST-02"]
        assert r.mention_confirms[0]["mention"] is False and r.mention_confirms[0]["prompt_zh"]
    assert r.final_slots.get("rest_symptom_first_time") is not False
    assert r.final.tier != 3


def test_asked_unknown_rest_first_time_then_denial_mention_forces_confirm():
    """固定題序（假 Prompter）：Q-REST-02 先問、抽不出；下一題順口「以前也有」→ 立刻複誦 Q-REST-02（解讀值＝沒有，計入複誦、不算題數）。
    (a) 複誦回答抽不出 → 依 D-50 維持未知；(b) 複誦回答「對，以前也有」→ 定案 False（經過複誦）。"""
    order = ["Q-REST-02", "Q-ONSET-01", "Q-THRESHOLD-01"]

    class FixedPrompter:
        def next_question(self, state, missing=None, asked=None):
            return next((QB[q] for q in order if q not in (asked or set())), None)

        def pending_test_question(self, state, decision, asked):
            return None

    case = CASES["S-STABLE-01#0"]
    for reply_value, expect in ((None, None), (False, False)):
        prompts = []

        def ex(text, q, confirm_prompt=None):
            if q is None:
                return {"symptom_character": "pressure", "rest_symptom": True}
            if confirm_prompt is not None:                      # 問的當下的 D-50 複誦（請您回答有還是沒有）也抽不出；
                prompts.append((q.id, confirm_prompt))          # 只有順口值觸發的複誦（您的回答是『沒有』，對嗎？）回 reply_value
                return {q.slot_id: reply_value if (q.id == "Q-REST-02" and "您的回答是" in confirm_prompt) else None}
            if q.id == "Q-REST-02":
                return {q.slot_id: None}
            return {q.slot_id: None, "rest_symptom_first_time": False}

        r = run_case(case, patient=_UnknownPatient(), extractor=ex, prompter=FixedPrompter())
        assert [m["question_id"] for m in r.mention_confirms] == ["Q-REST-02"]
        m = r.mention_confirms[0]
        assert m["mention"] is False and "『沒有』" in m["prompt_zh"] and m["value"] is expect
        assert r.final_slots.get("rest_symptom_first_time") is expect
        assert r.n_questions == len([t for t in r.turns]) and r.n_confirms >= 1


# ---------------------------------------------------------------- 最終驗收 r5：d50_injection（暫存被拒收的順口值、不重複複誦、不迴圈）
class _Echo:
    """ScriptedPatient＋回聲抽取器：開場白去掉 drop 欄；注入一句如實但較不嚴重的順口值。mode 1：該題還沒問過時注入；
    mode 2：該題問過但抽不出（含它自己的複誦），下一題注入。"""

    def __init__(self, case, drop, inject, mode):
        self.case, self.drop, self.inject, self.mode, self.done, self.asked_unknown = case, drop, inject, mode, inject is None, False

    def __call__(self, text, q, confirm_prompt=None):
        if q is None:
            return {k: v for k, v in extract(self.case.opening_zh).items() if k != self.drop}
        truth = ScriptedPatient(self.case).answer(q).value
        if q.slot_id == self.drop and self.mode == 2 and not self.done:
            self.asked_unknown = True
            return {q.slot_id: None}
        out = {q.slot_id: truth}
        if confirm_prompt is None and not self.done and q.slot_id != self.drop and (self.mode == 1 or self.asked_unknown):
            out[self.drop] = self.inject
            self.done = True
        return out


from acs_triage.extract import extract  # noqa: E402


def _inject_run(case, slot, v, mode, policy, monkeypatch):
    import sim.runner as R
    if policy == "accept_all":
        monkeypatch.setattr(R, "_d50_top_values", lambda: {})
    try:
        r = run_case(case, extractor=_Echo(case, slot, None if policy == "no_mention" else v, mode))
    finally:
        monkeypatch.undo()
    return r, urgency(r.final.tier, r.final.hard_stop, r.final_state)


@pytest.mark.parametrize("mode", [1, 2])
def test_d50_injection_never_less_urgent_than_no_mention_or_accept_all(mode, monkeypatch):
    from sim.runner import _d50_top_values
    worse_none, worse_accept, n = [], [], 0
    for case in CASES.values():
        for slot, top in _d50_top_values().items():
            v = case.slots.get(slot)
            if v is None or v in top:
                continue
            n += 1
            a, ua = _inject_run(case, slot, v, mode, "dev", monkeypatch)
            _, ub = _inject_run(case, slot, v, mode, "accept_all", monkeypatch)
            _, uc = _inject_run(case, slot, v, mode, "no_mention", monkeypatch)
            if ua > uc:
                worse_none.append((case.id, slot, v))
            if ua > ub:
                worse_accept.append((case.id, slot, v))
            assert a.n_questions <= 11
    assert n > 500 and worse_none == [] and worse_accept == []


def test_stashed_mention_confirmed_when_slot_later_asked_unknown():
    """驗收 r5 的 3 組：vague 型 persona 先順口說「說不上來」（該題還沒問過 → 暫存），之後 Q-CHARACTER-01 直接問仍抽不出
    → 以暫存值複誦（「您的回答是『說不上來』，對嗎？」）→ 定案 vague（T9 備援 T3 → 收下後 T1）。"""
    for cid in ("S-INSUF-01", "S-INSUF-02", "S-INSUF-06"):
        case = CASES[cid]
        r = run_case(case, extractor=_Echo(case, "symptom_character", "vague", 1))
        m = [x for x in r.mention_confirms if x["slot"] == "symptom_character"]
        assert len(m) == 1 and m[0]["stage"] == "stashed_then_asked_unknown" and "『說不上來』" in m[0]["prompt_zh"]
        assert r.final_slots["symptom_character"] == "vague"
        t = next(t for t in r.turns if t.question_id == "Q-CHARACTER-01")
        assert t.pre_confirm_answer is None and t.answer == "vague" and t.confirm_prompt_zh == m[0]["prompt_zh"]
        base = run_case(case, extractor=_Echo(case, "symptom_character", None, 1))
        assert r.n_confirms == base.n_confirms                  # 取代一般的未知複誦，不多一次


def test_mention_confirms_count_in_confirm_changed_and_no_loops():
    """順口值觸發的複誦計入 n_confirm_changed；每通每個 slot 最多一次；題數不超過上限（極端：每句都順口否認全部 D-50 slot）。"""
    from sim.runner import _d50_top_values
    low = {s: (False if s not in ("dyspnea_grade", "symptom_character") else {"dyspnea_grade": "none", "symptom_character": "vague"}[s])
           for s in _d50_top_values()}
    for case in CASES.values():
        def storm(text, q, confirm_prompt=None):
            if q is None:
                return {}
            return {q.slot_id: None, **{s: v for s, v in low.items() if s != q.slot_id}}
        r = run_case(case, extractor=storm)
        slots = [m["slot"] for m in r.mention_confirms]
        assert len(slots) == len(set(slots)) and r.n_questions <= 11
    # n_confirm_changed：Q-CHARACTER-01 問過抽不出 → 順口「會痛」→ 複誦回答「不是，被壓住」→ 採 pressure（≠ 解讀值 pain）
    case = CASES["S-MID-13#0"]
    seen = []

    def ex(text, q, confirm_prompt=None):
        if q is None:
            return {"onset_new": True, "last_episode_timing": "today"}
        seen.append(q.id)
        if confirm_prompt is not None and q.id == "Q-CHARACTER-01" and "『刺痛』" in confirm_prompt:
            return {q.slot_id: "pressure"}
        out = {q.slot_id: None}
        if confirm_prompt is None and "Q-CHARACTER-01" in seen[:-1]:
            out["symptom_character"] = "pain"
        return out

    r = run_case(case, patient=_UnknownPatient(), extractor=ex)
    m = [x for x in r.mention_confirms if x["slot"] == "symptom_character"]
    assert m and m[0]["value"] == "pressure" and r.n_confirm_changed >= 1


# ---------------------------------------------------------------- 驗收 r6：stash_hs_delay（已是或將成 Hard stop 時不得先複誦）
class _CountingPatient(_UnknownPatient):
    def __init__(self):
        self.confirms = []

    def confirm(self, q, p):
        self.confirms.append(q.id)
        return super().confirm(q, p)


def test_stash_not_confirmed_when_same_answer_hard_stops():
    """先暫存 pain（Q-CHARACTER-01 還沒問）；回答 Q-CHARACTER-01 時順口說有昏過去 → 不得先對 Q-CHARACTER-01 複誦，直接 Hard stop。"""
    case = CASES["S-MID-13#0"]

    def ex(text, q, confirm_prompt=None):
        if q is None:
            return {"onset_new": True, "last_episode_timing": "today"}
        out = {q.slot_id: None}
        if confirm_prompt is None and q.id != "Q-CHARACTER-01":
            out["symptom_character"] = "pain"
        if confirm_prompt is None and q.id == "Q-CHARACTER-01":
            out["syncope"] = True
        return out

    p = _CountingPatient()
    r = run_case(case, patient=p, extractor=ex)
    assert r.final.hard_stop and r.turns[-1].question_id == "Q-CHARACTER-01"
    assert "Q-CHARACTER-01" not in p.confirms and r.turns[-1].confirm_prompt_zh is None and r.mention_confirms == []
    assert r.final_slots["symptom_character"] == "pain"                 # 暫存值直接寫入


@pytest.mark.parametrize("order", [("syncope", "symptom_character"), ("symptom_character", "syncope")])
def test_asked_unknown_mention_not_confirmed_when_same_sentence_hard_stops(order):
    """Q-CHARACTER-01 先答未知；之後同一句同時說昏倒與痛（兩種欄位順序）→ 不由順口值觸發複誦，直接寫入並 Hard stop。"""
    case = CASES["S-MID-13#0"]
    seen = []

    def ex(text, q, confirm_prompt=None):
        if q is None:
            return {"onset_new": True, "last_episode_timing": "today"}
        seen.append(q.id)
        out = {q.slot_id: None}
        if confirm_prompt is None and "Q-CHARACTER-01" in seen and q.id != "Q-CHARACTER-01":
            vals = {"syncope": True, "symptom_character": "pain"}
            out.update({k: vals[k] for k in order})
        return out

    p = _CountingPatient()
    r = run_case(case, patient=p, extractor=ex)
    assert r.final.hard_stop and r.mention_confirms == [] and p.confirms.count("Q-CHARACTER-01") == 1   # 只有它自己問的當下那次
    assert r.final_slots["symptom_character"] == "pain"


@pytest.mark.parametrize("partner", ["diaphoresis", "presyncope", "ongoing_now"])
@pytest.mark.parametrize("as_mention", [True, False])
def test_asked_unknown_mention_not_confirmed_when_combined_value_hard_stops(partner, as_mention):
    """Q-CHARACTER-01 答未知；之後同一句說「痛」與冒汗／快暈倒／還在——單看「痛」不會 Hard stop，合起來會。
    不論另一個值是順口提到（排在「痛」之後）還是被問那題的回答，都不得先由順口值複誦 Q-CHARACTER-01。"""
    from acs_triage.prompter import Prompter
    case = CASES["S-MID-13#0"]
    qb = question_by_id()
    target = next(q.id for q in qb.values() if q.slot_id == partner and q.priority == "redflag")

    class Forced(Prompter):
        def next_question(self, state, missing=None, asked=None):
            for qid in ("Q-CHARACTER-01", "Q-PALP-01" if as_mention else target):
                if qid not in asked:
                    return qb[qid]
            return super().next_question(state, missing=missing, asked=asked)

    def ex(text, q, confirm_prompt=None):
        if q is None:
            return {"onset_new": True, "last_episode_timing": "today"}
        out = {q.slot_id: None}
        if confirm_prompt is None and q.id != "Q-CHARACTER-01":
            out.update({"symptom_character": "pain", partner: True})
        return out

    p = _CountingPatient()
    r = run_case(case, patient=p, extractor=ex, prompter=Forced())
    assert r.final.hard_stop and len(r.turns) == 2
    assert r.mention_confirms == [] and p.confirms.count("Q-CHARACTER-01") == 1 and r.turns[-1].confirm_prompt_zh is None
    assert r.final_slots["symptom_character"] == "pain"
