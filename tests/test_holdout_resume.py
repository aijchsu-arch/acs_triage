"""保留集補跑（sim.holdout_resume，D-58 基礎設施失敗例外）：全部用假 client 與 tmp 目錄，不打 API（Anthropic／OpenAI／LM Studio）。
假保留集用開發集的 case（不讀保留集內容）；凍結檢查比對的是真的凍結檔 sha256。"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import sim.closed_loop as cl
import sim.holdout_resume as hr
import sim.llm_extract_v2 as v2
from acs_triage.extract import extract
from acs_triage.loaders import REPO_ROOT, question_by_id
from sim.cases import all_cases
from sim.llm_extract_v2 import LLMExtractorV2
from sim.llm_patient import build_system
from sim.patient import ScriptedPatient

QB = question_by_id()
CASES = [c for c in all_cases() if c.truth_tier is not None][:8]
ERRORED = [CASES[2].id, CASES[3].id, CASES[6].id]
# 假 truth：多數同情境 truth；CASES[2]（補跑的）標成 Hard stop → miss＋under，CASES[4]（原本成功的）標成 T1 → over；CASES[7] 無 truth
TRUTH = {c.id: ((0 if c.truth_hard_stop else c.truth_tier), c.truth_hard_stop) for c in CASES[:7]} | {CASES[2].id: (0, True), CASES[4].id: (1, False)}


def ident(s):
    return s


class BadRequestError(Exception):
    status_code = 400

    def __init__(self):
        super().__init__("You have reached your specified API usage limits. You will regain access on 2026-12-01.")


class FakeOpus:
    """假病人 LLM：依 system 認 case、依最近一個題目原文認題，回 ScriptedPatient 的值（話＝JSON 值，給 EchoExtractor 解回）。
    max_tokens=1 是探測；probe_ok=False 時探測丟用量上限錯誤；fail_case 的 case 一律丟 BadRequestError。"""

    def __init__(self, cases, probe_ok=True, fail_case=None):
        self.by_sys = {build_system(c): c for c in cases}
        self.by_text = {q.script_zh.strip(): q for q in QB.values()}
        self.probe_ok, self.fail_case = probe_ok, fail_case
        self.n = self.probes = self.fails = 0
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        if kw.get("max_tokens") == 1:
            self.probes += 1
            if not self.probe_ok:
                raise BadRequestError()
            return SimpleNamespace(stop_reason="max_tokens", content=[])
        case = self.by_sys[kw["system"]]
        if case.id == self.fail_case:
            self.fails += 1
            raise BadRequestError()
        self.n += 1
        q = next(self.by_text[m["content"]] for m in reversed(kw["messages"])
                 if m["role"] == "user" and m["content"] in self.by_text)
        v = ScriptedPatient(case).answer(q).value
        dk = v is None or v == "unknown"
        txt = json.dumps({"utterance_zh": json.dumps(v, ensure_ascii=False), "dont_know": dk, "answer": False if dk else v},
                         ensure_ascii=False)
        return SimpleNamespace(stop_reason="end_turn", model="fake-opus", content=[SimpleNamespace(type="text", text=txt)],
                               usage=SimpleNamespace(input_tokens=10, output_tokens=20, cache_creation_input_tokens=0,
                                                     cache_read_input_tokens=100))


class EchoExtractor:
    """假抽取器（LLMExtractorV2 介面的子集）：病人的話是 JSON 值 → 直接解回；開場白用關鍵字抽取。"""
    key = staticmethod(LLMExtractorV2.key)

    def __init__(self):
        self.cache, self.spent, self.n_tw_changed = {}, 0.0, 0

    def load(self, path, meta, reparse=False):
        return []

    def save(self, path, meta, history):
        path.write_text(json.dumps({"meta": meta, "n": len(self.cache)}), encoding="utf-8")

    def record(self, text, q, confirm_prompt=None):
        k = self.key(text, q, confirm_prompt)
        if k not in self.cache:
            slots = extract(text) if q is None else {q.slot_id: json.loads(text)}
            self.cache[k] = {"ok": True, "slots": slots, "diag": {}, "latency_s": 0.01, "cost": 0.0}
        return self.cache[k]

    def __call__(self, text, q=None, confirm_prompt=None):
        out = dict(self.record(text, q, confirm_prompt)["slots"])
        if q is not None:
            out.setdefault(q.slot_id, None)
        return out


def _minimal(schema):
    """schema 合法的最小輸出（null／最後一個 enum 值／空字串／0／空陣列）。"""
    t = schema.get("type")
    if isinstance(t, list) and "null" in t:
        return None
    if "enum" in schema:
        return schema["enum"][-1]
    return {"object": lambda: {k: _minimal(v) for k, v in schema["properties"].items()}, "array": list,
            "string": str, "number": int, "boolean": bool}[t]()


class FakeGPT:
    """假 gpt 抽取 client（OpenAIStructured.ask 介面）：回 schema 合法的最小輸出，每次 1000 input tokens；
    fail_text 出現在 user 提示時丟 OpenAI HTTP 400（同 adapter 的 RuntimeError 格式；4xx 不重試）。"""

    def __init__(self, fail_text=None):
        self.fail_text, self.n, self.fails = fail_text, 0, 0

    def ask(self, system, user, schema, name):
        if self.fail_text and self.fail_text in user:
            self.fails += 1
            raise RuntimeError("OpenAI HTTP 400 code=insufficient_quota type=invalid_request_error")
        self.n += 1
        return _minimal(schema), {"input_tokens": 1000, "output_tokens": 0}, "fake-gpt"


def _label(tier, hs):
    return {"tier": f"T{tier}", "hard_stop": hs, "rf_ids": [], "confidence": "high", "rationale_zh": "假"}


def _run_full(arm):
    """同一組假 client、沒有中斷的完整一次（對照組）。"""
    return cl.run_arm(CASES, arm=arm, cache=cl.PatientCache(), client=FakeOpus(CASES), extractor=cl.UsedKeys(EchoExtractor()),
                      tw=ident, budget=None, workers=1)


def _write_original(d, arm):
    outs = _run_full(arm)
    ok = [o for o in outs if o["case"].id not in ERRORED]
    recs = [{"case_id": o["case"].id, "error": "BadRequestError", "extract_failures": [], "wall_s": 0.1,
             "patient": {"live": 1, "cached": 0, "sources": {"live": 1}, "cost": 0.007, "deviations": []}}
            if o["case"].id in ERRORED else cl.case_record(o) for o in outs]
    rep = {"meta": {"set": "holdout", "arm": arm, "limit": None, "file_sha256": cl.file_hashes()},
           "patient_usage": {"live_calls": 1}, "extractor_usage": {"cost_total_usd": 0.0}, "cases": recs,
           "metrics": cl.holdout_metrics(cl.holdout_rows(ok), CASES),
           "mention_conflicts": [c for o in ok for c in o["result"].mention_conflicts],
           "mention_confirms": [c for o in ok for c in o["result"].mention_confirms], "reasks": cl.all_reasks(ok), "extract_failures": []}
    (d / f"closed_holdout_{arm}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def env(tmp_path, monkeypatch):
    for k in ("ACS_PATIENT_LLM_KEY", "ACS_OPENAI_API_KEY", "ACS_JEV_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    orig, ref, truth = tmp_path / "orig", tmp_path / "ref.json", tmp_path / "truth.json"
    (orig / "cache_holdout").mkdir(parents=True)
    # truth：CASES[0] 最終裁定、CASES[1..6] 一致標註、CASES[7] 兩位標註不一致（無 truth）
    labels = [{"opus": _label(*TRUTH[c.id]), "gpt": _label(*TRUTH[c.id])} for c in CASES[1:7]] + [{"opus": _label(3, False), "gpt": _label(1, False)}]
    ref.write_text(json.dumps({"cases": [{"case_id": c.id, "labels": lb} for c, lb in zip(CASES[1:], labels)]}), encoding="utf-8")
    truth.write_text(json.dumps({"_meta": {}, CASES[0].id: _label(*TRUTH[CASES[0].id])}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(cl, "FREEZE_PATH", tmp_path / "freeze.json")
    monkeypatch.setattr(cl, "HOLDOUT_REGISTRY", tmp_path / "runs.json")
    monkeypatch.setattr(cl, "HOLDOUT_REFERENCE", ref)
    monkeypatch.setattr(cl, "HOLDOUT_TRUTH", truth)
    monkeypatch.setattr(cl, "check_structured_version", lambda path, set_name="dev": calls.append((path, set_name)))
    monkeypatch.setattr(cl, "load_set", lambda name: (CASES, []))
    monkeypatch.setattr(cl, "check_lmstudio", lambda *a: None)
    monkeypatch.setattr(v2, "load_to_tw", lambda: ident)
    monkeypatch.setattr(v2, "make_extractor", lambda name, budget=None, to_traditional=None: EchoExtractor())
    monkeypatch.setattr(hr, "ORIG_DIR", orig)
    fake = FakeOpus(CASES)
    monkeypatch.setattr(cl, "make_client", lambda: fake)
    cl.freeze_main([])                                           # 真的凍結檔 sha256 → tmp 凍結紀錄
    for arm in ("gpt", "gemma"):
        _write_original(orig, arm)
        (orig / "cache_holdout" / f"extract_cache_holdout_{arm}.json").write_text('{"meta": {}, "records": []}', encoding="utf-8")
    cl.PatientCache().save(orig / "cache_holdout" / "patient_cache_holdout.json")
    runs = [{"arm": a, "started_at": "2026-11-25T23:26:31", "output": f"<scratch>/run1125/hold_out/closed_holdout_{a}.json"}
            for a in ("structured", "gpt", "gemma")]
    cl.HOLDOUT_REGISTRY.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    monkeypatch.setenv("ACS_PATIENT_LLM_KEY", "dummy-not-used")
    monkeypatch.setenv("ACS_OPENAI_API_KEY", "dummy-not-used")
    return SimpleNamespace(tmp=tmp_path, orig=orig, fake=fake, calls=calls, scratch=tmp_path / "scratch")


def _args(env, arm="gpt", extra=()):
    return ["--arm", arm, "--scratch", str(env.scratch), "--workers", "2", *extra]     # 預算用預設值


def _load(env, name):
    return json.loads((env.orig / name).read_text(encoding="utf-8"))


def _runs():
    return json.loads(cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8"))


def _no_outputs(env):
    return not list(env.orig.glob("*_resume.json")) and not list(env.orig.glob("*_combined.json"))


# ---------------------------------------------------------------- 凍結
@pytest.mark.parametrize("item", ["sim/closed_loop.py", "data/clinical_rules.yaml", "data/extractor_prompts_v2.yaml", "rendered_sha256"])
def test_refuses_on_freeze_hash_mismatch(env, item):
    rec = json.loads(cl.FREEZE_PATH.read_text(encoding="utf-8"))
    bad = {**rec, item: "x"} if item == "rendered_sha256" else {**rec, "files": {**rec["files"], item: "0" * 64}}
    cl.FREEZE_PATH.write_text(json.dumps(bad), encoding="utf-8")
    before = cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8")
    with pytest.raises(SystemExit, match="改動"):
        hr.run_main(_args(env))
    assert cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8") == before and env.fake.n == env.fake.probes == 0
    assert _no_outputs(env) and not env.scratch.exists()


def test_refuses_without_freeze_record(env):
    cl.FREEZE_PATH.unlink()
    with pytest.raises(SystemExit, match="凍結"):
        hr.run_main(_args(env))
    assert _no_outputs(env)


# ---------------------------------------------------------------- 只補 error 的 case
def test_resumes_exactly_the_errored_ids(env):
    orig_sha = _sha(env.orig / "closed_holdout_gpt.json")
    cache_sha = {p.name: _sha(p) for p in (env.orig / "cache_holdout").iterdir()}
    hr.run_main(_args(env))
    orig, res, comb = (_load(env, f"closed_holdout_gpt{s}.json") for s in ("", "_resume", "_combined"))
    assert res["meta"]["case_ids"] == ERRORED == [r["case_id"] for r in res["cases"]] == res["meta"]["attempted"]
    assert res["meta"]["errored_again"] == res["meta"]["not_attempted"] == [] and all(r["final"] for r in res["cases"])
    entry = _runs()[-1]
    assert (entry["arm"], entry["kind"], entry["case_ids"], entry["reason"]) == ("gpt", hr.KIND, ERRORED, hr.REASON)
    assert entry["freeze_sha256"] == json.loads(cl.FREEZE_PATH.read_text(encoding="utf-8"))["files"]
    assert entry["started_at"] and entry["finished_at"] and entry["errored_again"] == []
    assert [r["case_id"] for r in comb["cases"]] == [r["case_id"] for r in orig["cases"]]
    assert [r for r in comb["cases"] if r["case_id"] not in ERRORED] == [r for r in orig["cases"] if not r["error"]]
    assert comb["meta"]["case_sources"]["resumed"] == ERRORED and comb["meta"]["errors"] == []
    assert env.calls == [(cl.HOLDOUT_STRUCTURED, "holdout")] and env.fake.probes == 1 and env.fake.n > 0
    assert _sha(env.orig / "closed_holdout_gpt.json") == orig_sha                       # 原輸出不覆寫
    assert {p.name: _sha(p) for p in (env.orig / "cache_holdout").iterdir()} == cache_sha   # 已 commit 的快取不動
    assert (env.scratch / "cache_holdout" / "patient_cache_holdout.json").exists()
    assert (res["meta"]["opus_budget"], res["meta"]["gpt_budget"]) == (5.0, 6.0)              # 預設預算
    assert entry["cache_sha256_after"] == hr.cache_hashes(env.scratch / "cache_holdout")


def test_refuses_when_original_has_no_errors(env):
    p = env.orig / "closed_holdout_gpt.json"
    rep = json.loads(p.read_text(encoding="utf-8"))
    rep["cases"] = [r for r in rep["cases"] if not r["error"]]
    p.write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit, match="沒有 error"):
        hr.run_main(_args(env))
    assert all("kind" not in r for r in _runs()) and _no_outputs(env)


# ---------------------------------------------------------------- 只補跑一次；原本的保留集 run 照樣拒跑
def test_resume_runs_once_per_arm(env):
    hr.run_main(_args(env))
    n = env.fake.n
    with pytest.raises(SystemExit, match="只補跑一次"):
        hr.run_main(_args(env))
    with pytest.raises(SystemExit, match="只補跑一次"):                                 # 換 --out 也拒跑（已登記）
        hr.run_main(_args(env, extra=["--out", str(env.tmp / "other")]))
    cl.HOLDOUT_REGISTRY.write_text(json.dumps([r for r in _runs() if r.get("kind") != hr.KIND]), encoding="utf-8")
    with pytest.raises(SystemExit, match="只補跑一次"):                                 # 沒登記、但已有 resume 輸出 → 拒跑
        hr.run_main(_args(env))
    cl.HOLDOUT_REGISTRY.write_text(json.dumps(_runs() + [{"arm": "gemma", "kind": hr.KIND}]), encoding="utf-8")
    with pytest.raises(SystemExit, match="只補跑一次"):                                 # 已登記、沒有輸出 → 拒跑
        hr.run_main(_args(env, arm="gemma"))
    assert env.fake.n == n


def test_original_closed_loop_run_still_refuses_after_resume(env):
    before = _runs()
    hr.run_main(_args(env))
    after = _runs()
    assert after[:len(before)] == before and len(after) == len(before) + 1 and after[-1]["arm"] == "gpt"   # 只附加一筆
    for out in (env.orig, env.tmp / "fresh_out"):
        with pytest.raises(SystemExit, match="只跑一次"):
            cl.run_main(["--set", "holdout", "--arm", "gpt", "--cache-dir", str(env.tmp / "c2"), "--out", str(out)])
    cl.HOLDOUT_REGISTRY.write_text(json.dumps([r for r in after if not (r["arm"] == "gpt" and "kind" not in r)]), encoding="utf-8")
    with pytest.raises(SystemExit, match="只跑一次"):                                   # 補跑紀錄本身也擋得住原本的 run
        cl.run_main(["--set", "holdout", "--arm", "gpt", "--cache-dir", str(env.tmp / "c2"), "--out", str(env.tmp / "fresh_out")])


# ---------------------------------------------------------------- 合併指標
def test_combined_metrics_equal_manual_recomputation(env):
    hr.run_main(_args(env))
    comb = _load(env, "closed_holdout_gpt_combined.json")
    full = _run_full("gpt")                                      # 同一組假 client、沒有中斷的完整一次
    assert comb["metrics"] == hr._j(cl.holdout_metrics(cl.holdout_rows(full), CASES))
    recs = {r["case_id"]: r for r in comb["cases"]}
    assert {i: (r["final"]["tier"], r["final"]["hs"]) for i, r in recs.items()} == \
        {o["case"].id: (o["result"].final.tier, o["result"].final.hard_stop) for o in full}
    truth = TRUTH
    assert all(r["final"]["tier"] != 9 for r in recs.values())  # 假資料沒有 T9：急迫度＝Hard stop -1、其餘 tier

    def sys_out(i):                                              # premature：truth 為 Hard stop、系統 Hard stop 只靠抽錯的值 → 計 miss
        f = recs[i]["final"]
        return (f["tier"], f["hs"] and not (truth[i][1] and recs[i]["hs_supported"] is False))

    def urg(tier, hs):
        return -1 if hs else tier
    t = comb["metrics"]["truth"]
    hs_ids = [i for i in truth if truth[i][1]]
    under = [i for i in truth if urg(*sys_out(i)) > urg(*truth[i])]
    over = [i for i in truth if urg(*sys_out(i)) < urg(*truth[i])]
    assert t["coverage"] == {"adjudicated": 1, "consensus": 6, "none": 1} and t["n"] == 7
    assert t["exact"]["x"] == sum(sys_out(i) == truth[i] for i in truth) == 5
    assert t["hs_sensitivity"]["n"] == len(hs_ids) and t["hs_miss"] == [i for i in hs_ids if not sys_out(i)[1]] == [CASES[2].id]
    assert (t["under"]["x"], t["under_cases"], t["over"]["x"], t["over_cases"]) == (len(under), under, len(over), over)
    assert under == [CASES[2].id] and over == [CASES[4].id] and t["premature"] == [] and t["t9"]["x"] == 0
    assert comb["meta"]["n_with_result"] == len(CASES)


def test_record_rows_reproduce_original_metrics_or_refuse(env):
    p = env.orig / "closed_holdout_gpt.json"
    rep = json.loads(p.read_text(encoding="utf-8"))
    rep["metrics"]["truth"]["exact"]["x"] += 1                    # 原輸出指標與逐例紀錄對不上 → 合併不可信，登記前就停
    p.write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SystemExit, match="重算的指標"):
        hr.run_main(_args(env))
    assert all("kind" not in r for r in _runs()) and env.fake.probes == 0


# ---------------------------------------------------------------- 前置檢查失敗不登記
def test_probe_failure_aborts_without_registering(env):
    before = cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8")
    env.fake.probe_ok = False
    with pytest.raises(SystemExit, match="探測失敗：BadRequestError HTTP 400；用量上限仍未解除"):
        hr.run_main(_args(env))
    assert cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8") == before and env.fake.probes == 1 and env.fake.n == 0
    assert _no_outputs(env)
    with pytest.raises(SystemExit, match="探測失敗"):
        hr.probe_main(["--arm", "gpt"])
    env.fake.probe_ok = True
    hr.run_main(_args(env))                                      # 上限解除後可再試（沒被當成已補跑）
    assert _runs()[-1]["kind"] == hr.KIND


def test_missing_key_exits_2_without_registering(env, monkeypatch, capsys):
    before = cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8")
    monkeypatch.delenv("ACS_OPENAI_API_KEY")
    with pytest.raises(SystemExit) as e:
        hr.run_main(_args(env))
    out = capsys.readouterr().out
    assert e.value.code == 2 and "ACS_OPENAI_API_KEY: MISSING" in out and "ACS_PATIENT_LLM_KEY: OK" in out
    assert "dummy-not-used" not in out and cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8") == before and env.fake.probes == 0


# ---------------------------------------------------------------- 又出錯：記錄、停止、不迴圈
def test_error_again_is_recorded_and_stops_the_arm(env):
    env.fake.fail_case = ERRORED[1]
    with pytest.raises(SystemExit) as e:
        hr.run_main(_args(env, extra=["--workers", "1"]))
    assert e.value.code == 3 and env.fake.fails == 1                                       # 不重試、不迴圈
    res, comb, orig = (_load(env, f"closed_holdout_gpt{s}.json") for s in ("_resume", "_combined", ""))
    m = res["meta"]
    assert (m["attempted"], m["errored_again"], m["not_attempted"]) == (ERRORED[:2], [ERRORED[1]], [ERRORED[2]])
    entry = _runs()[-1]
    assert entry["errored_again"] == [ERRORED[1]] and entry["not_attempted"] == [ERRORED[2]]
    recs = {r["case_id"]: r for r in comb["cases"]}
    assert recs[ERRORED[1]]["error"] == "BadRequestError" and "final" in recs[ERRORED[0]]
    assert recs[ERRORED[2]] == next(r for r in orig["cases"] if r["case_id"] == ERRORED[2])      # 沒補到 → 保留原 error 紀錄
    assert comb["meta"]["errors"] == ERRORED[1:] and comb["meta"]["n_with_result"] == len(CASES) - 2


# ---------------------------------------------------------------- gpt 之後跑 Gemma：共用病人快取；路徑改寫
def test_gemma_after_gpt_reuses_shared_patient_cache(env):
    hr.run_main(_args(env))
    n = env.fake.n
    hr.run_main(_args(env, arm="gemma"))
    res = _load(env, "closed_holdout_gemma_resume.json")
    assert env.fake.n == n and res["patient_usage"]["live_calls"] == 0 and res["patient_usage"]["sources"]["live_reused"] > 0
    assert res["meta"]["case_ids"] == ERRORED and res["meta"]["cache_copied"] == [] and res["meta"]["workers"] == 2
    assert (res["meta"]["opus_budget"], res["meta"]["gpt_budget"]) == (15.0, None)


def test_refuses_unverified_cache_content(env):
    before = cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8")
    c = env.scratch / "cache_holdout"
    c.mkdir(parents=True)
    (c / "patient_cache_holdout.json").write_text('{"meta": {}, "store": {}}', encoding="utf-8")   # 不是已 commit 的內容
    with pytest.raises(SystemExit, match="未驗證"):
        hr.run_main(_args(env))
    assert cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8") == before and env.fake.probes == 0 and _no_outputs(env)
    (c / "patient_cache_holdout.json").write_bytes((env.orig / "cache_holdout" / "patient_cache_holdout.json").read_bytes())
    hr.run_main(_args(env))                                      # 與已 commit 的 sha256 相同 → 可用，只補缺的檔
    assert _load(env, "closed_holdout_gpt_resume.json")["meta"]["cache_copied"] == ["extract_cache_holdout_gemma.json",
                                                                                     "extract_cache_holdout_gpt.json"]


def test_gemma_refuses_cache_changed_after_gpt_resume(env):
    hr.run_main(_args(env))
    p = env.scratch / "cache_holdout" / "patient_cache_holdout.json"
    p.write_text(p.read_text(encoding="utf-8") + " ", encoding="utf-8")   # gpt 補跑之後被動過 → 不等於登記的 sha256
    with pytest.raises(SystemExit, match="未驗證"):
        hr.run_main(_args(env, arm="gemma"))
    assert not any(r.get("arm") == "gemma" and r.get("kind") == hr.KIND for r in _runs())


def test_written_paths_are_sanitized(env):
    hr.run_main(_args(env))
    for p in (env.orig / "closed_holdout_gpt_resume.json", env.orig / "closed_holdout_gpt_combined.json", cl.HOLDOUT_REGISTRY):
        txt = p.read_text(encoding="utf-8")
        assert str(env.scratch) not in txt and str(env.scratch.resolve()) not in txt
    assert _load(env, "closed_holdout_gpt_resume.json")["meta"]["cache_dir"] == "<scratch>/cache_holdout"
    assert _runs()[-1]["cache_dir"] == "<scratch>/cache_holdout"
    assert hr.sanitize({"a": [f"{REPO_ROOT}/reports/x", f"{Path.home()}/y", f"{env.scratch}/z"]}, env.scratch) == \
        {"a": ["<repo>/reports/x", "<home>/y", "<scratch>/z"]}


# ---------------------------------------------------------------- 抽取端失敗也是基礎設施失敗（真的 LLMExtractorV2＋假 gpt client）
def _real_extractor(env, monkeypatch, gpt, spent):
    """已 commit 的 gpt 抽取快取：同 meta、已累計 spent（一筆失敗紀錄帶費用，同 11-25 的累計方式）。"""
    rec = {"q": None, "confirm_prompt": None, "text": "11-25 累計", "sent": "11-25 累計", "ok": False, "error": "x", "cost": spent}
    (env.orig / "cache_holdout" / "extract_cache_holdout_gpt.json").write_text(
        json.dumps({"meta": v2.meta_for("gpt"), "records": [rec]}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(v2, "make_extractor", lambda name, budget=None, to_traditional=None: LLMExtractorV2(
        gpt, name="fake-gpt", price=(10.0, 1.0, 10.0), budget_usd=budget, to_traditional=to_traditional, sleep=lambda s: None))


def _assert_extract_failure_stops(env, e, reason):
    assert e.value.code == 3
    res, comb = (_load(env, f"closed_holdout_gpt{s}.json") for s in ("_resume", "_combined"))
    m = res["meta"]
    assert (m["attempted"], m["errored_again"], m["not_attempted"]) == (ERRORED[:1], ERRORED[:1], ERRORED[1:])
    assert reason in m["errored_again_reasons"][ERRORED[0]] and res["cases"][0]["error"] is None and res["cases"][0]["extract_failures"]
    entry = _runs()[-1]
    assert (entry["errored_again"], entry["not_attempted"]) == (ERRORED[:1], ERRORED[1:])
    assert reason in entry["errored_again_reasons"][ERRORED[0]] and entry["finished_at"]
    assert comb["meta"]["errors"] == ERRORED and comb["meta"]["n_with_result"] == len(CASES) - 3
    assert comb["meta"]["case_sources"]["resumed"] == [] and comb["metrics"]["truth"]["n"] == 7 - 3
    assert ERRORED[0] not in comb["metrics"]["truth"]["under_cases"] + comb["metrics"]["truth"]["hs_miss"]


def test_gpt_budget_exhaustion_counts_as_infra_failure(env, monkeypatch):
    gpt = FakeGPT()
    _real_extractor(env, monkeypatch, gpt, spent=3.18)
    with pytest.raises(SystemExit) as e:                         # 每次 US$0.01：兩次後 3.20 用完 → budget_exceeded
        hr.run_main(_args(env, extra=["--workers", "1", "--gpt-budget", "3.20"]))
    _assert_extract_failure_stops(env, e, "budget_exceeded")
    assert gpt.n in (2, 3)                                       # 3.18＋0.01＋0.01 的浮點累加可能略小於 3.20，多放行一次


def test_extractor_400_counts_as_infra_failure(env, monkeypatch):
    gpt = FakeGPT(fail_text=next(c for c in CASES if c.id == ERRORED[0]).opening_zh)
    _real_extractor(env, monkeypatch, gpt, spent=3.18)
    with pytest.raises(SystemExit) as e:
        hr.run_main(_args(env, extra=["--workers", "1"]))
    _assert_extract_failure_stops(env, e, "HTTP 400")
    assert gpt.fails == 1                                        # 4xx 不重試、不迴圈
