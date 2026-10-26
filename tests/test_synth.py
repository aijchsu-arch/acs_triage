"""實驗 1（合成病人驗證集）：生成、標註、三層評估、報告與裁定表的離線測試（假 client，不打 API、不需金鑰）。"""
import json
import sys
import zipfile
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from acs_triage.loaders import slot_defs
from sim import run_llm_eval, synth_annotate as sa, synth_eval as se, synth_gen as sg
from sim.llm_patient import render_sheet
from sim.patient import ScriptedPatient
from sim.run_llm_eval import run_llm, transcripts_json
from sim.runner import run_case

from test_llm_patient import FakeClient

CASES = [
    {"id": "SYN-T01", "category": "acs_today", "persona_style": "general", "name_zh": "持續壓迫",
     "opening_zh": "我今天坐著看電視，胸口突然像被壓住，已經十分鐘了。",
     "slots": {"ongoing_now": True, "symptom_character": "pressure", "onset_new": True, "last_episode_timing": "ongoing",
               "diaphoresis": False, "presyncope": False, "syncope": False, "dyspnea_grade": "none"}},
    {"id": "SYN-T02", "category": "admin_followup", "persona_style": "minimizer", "name_zh": "問門診",
     "opening_zh": "歹勢喔，我只是想問下禮拜三有沒有門診，人都好好的。",
     "slots": {"consult_topic": "appointment_admin", "symptom_character": "none", "dyspnea_grade": "none",
               "presyncope": False, "syncope": False, "palpitations": False, "postural_dizziness": False,
               "pending_abnormal_test": False, "ongoing_now": False}},
    {"id": "SYN-T03", "category": "atypical", "persona_style": "unclear", "name_zh": "說不清楚",
     "opening_zh": "就是怪怪的，我也講不出來，好幾天了。",
     "slots": {"symptom_character": "vague", "diaphoresis": False, "presyncope": False, "syncope": False}},
]


def _write_synth(tmp_path, cases=CASES):
    meta = {"synth_version": "test", "cost": {"est_cost_usd": 0.0},
            "generated_by": {"model": "fake", "model_versions": ["fake"], "reasoning_effort": "low", "prompt_version": "t"},
            "similarity": sg.similarity_stats([{**c, "_sim": {"regen": 0, "still_similar": False}} for c in cases], ["無關的句子"])}
    p = tmp_path / "synth.yaml"
    sg.save(p, [{**c, "_sim": {"regen": 0, "still_similar": False}} for c in cases], meta)
    return p


# ---------------------------------------------------------------- 生成
def test_slot_schema_is_strict_and_follows_slot_defs():
    s = sg.slot_schema()
    assert s["additionalProperties"] is False and sorted(s["required"]) == sorted(s["properties"])
    assert set(s["properties"]) == set(slot_defs()) - {"consult_screen_positive"}
    for sid, prop in s["properties"].items():
        t = slot_defs()[sid]["type"]
        if t == "choice":
            assert prop["anyOf"][0]["enum"] == slot_defs()[sid]["choices"] and prop["anyOf"][1] == {"type": "null"}
        else:
            assert prop["type"] == [{"yes_no": "boolean", "duration": "number"}[t], "null"]
    b = sg.batch_schema()
    item = b["properties"]["cases"]["items"]
    assert item["additionalProperties"] is False and item["properties"]["slots"] == s


def test_validate_slots():
    assert sg.validate_slots({"ongoing_now": True, "episode_duration_min": 5, "symptom_character": "pressure", "edema": None}) == []
    errs = sg.validate_slots({"ongoing_now": "yes", "episode_duration_min": True, "symptom_character": "burning",
                              "consult_screen_positive": True, "nope": 1})
    assert len(errs) == 5


def test_similarity():
    a = "我有冠心症，剛剛吃太飽胸口脹脹的，打嗝之後就好了，現在完全沒事，想確認要不要去急診。"
    assert sg.overlap(a, a) == 1.0
    assert sg.overlap("齁，那個…" + a + "啦", a) >= sg.SIM_THRESHOLD          # 加贅詞的照抄抓得到
    assert sg.overlap("昨天搬家具之後右邊肋骨壓下去會痛。", a) < sg.SIM_THRESHOLD
    ex = sg.existing_openings()
    assert len(ex) == 40 and all(sg.most_similar(o, ex)[0] == 1.0 for o in ex[:3])


def test_plan_matches_coverage_matrix():
    plan = sg.build_plan(sg.prompts())
    from collections import Counter
    assert len(plan) == 150 and len({p["id"] for p in plan}) == 150
    assert Counter(p["category"] for p in plan) == {k: v["n"] for k, v in sg.prompts()["categories"].items()}
    assert all(p["persona_style"] == "family_proxy" for p in plan if p["category"] == "family_proxy")
    assert set(p["persona_style"] for p in plan) == set(sg.prompts()["personas"])


class FakeOpenAI:
    """依 user prompt 的題數回傳 cases；第一次把第一例的開場白抄成既有開場白，觸發重生。"""

    def __init__(self, existing):
        self.existing = existing
        self.calls = []

    def ask(self, system, user, schema, name):
        assert schema == sg.batch_schema() and name == "synthetic_patients"
        self.calls.append(user)
        n = sum(1 for line in user.splitlines() if "persona_style=" in line)
        copy = len(self.calls) == 1
        cases = [{"name_zh": f"情境{i}", "opening_zh": (self.existing[0] if copy and i == 0 else f"第{len(self.calls)}批第{i}例，昨天爬山後膝蓋酸"),
                  "slots": {k: None for k in sg.generated_slot_ids()} | {"ongoing_now": False}} for i in range(n)]
        return {"cases": cases}, {"input_tokens": 100, "input_tokens_details": {"cached_tokens": 0}, "output_tokens": 10}, "fake-gpt"


def test_generator_regenerates_too_similar_openings():
    cfg = sg.prompts()
    ex = sg.existing_openings()
    fake = FakeOpenAI(ex)
    gen = sg.Generator(fake, cfg, ex)
    plan = [p for p in sg.build_plan(cfg) if p["category"] == "family_proxy"]
    out = sg.generate(plan, gen, workers=1)
    assert [c["id"] for c in out] == [p["id"] for p in plan]
    first = out[0]
    assert first["_sim"]["regen"] == 1 and first["_sim"]["first_overlap_existing"] == 1.0 and not first["_sim"]["still_similar"]
    assert "（重寫）" in fake.calls[1] and ex[0] in fake.calls[1]
    assert all(c["slots"] == {"ongoing_now": False} for c in out)       # null 不存
    assert "ongoing_now" in gen.system and ex[0] in gen.system and "RF-01" not in gen.system   # 生成器不看規則
    assert gen.cost() > 0 and gen.model_versions == {"fake-gpt"}


def test_save_and_load_roundtrip(tmp_path):
    p = _write_synth(tmp_path)
    text = p.read_text(encoding="utf-8")
    assert "LLM 生成" in text and "不是 Clinical Owner truth" in text and "不得" in text
    cases = sg.load_synth_cases(p)
    assert [c.id for c in cases] == ["SYN-T01", "SYN-T02", "SYN-T03"]
    c2 = cases[1]
    assert c2.truth_tier is None and c2.persona == "normal" and c2.module == "admin_followup"
    assert c2.slots["consult_screen_positive"] is False            # _complete 推得
    bad = dict(CASES[0], slots={"ongoing_now": "yes"})
    with pytest.raises(ValueError):
        sg.synth_case(bad)


# ---------------------------------------------------------------- 標註
def test_rules_excerpt_is_sections_1_to_3_only():
    ex = sa.rules_excerpt()
    assert ex.startswith("## 1. 分流等級") and "RF-06" in ex and "### 3.1" in ex
    assert "## 4." not in ex and "ND-01" not in ex and "T0-NEW-TODAY" not in ex and "### 5.1" not in ex


class FakeAnthropic:
    def __init__(self, label):
        self.label = label
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.requests.append(kw)
        if self.label is None:
            raise RuntimeError("stop_reason=refusal")
        usage = SimpleNamespace(input_tokens=100, output_tokens=50, cache_creation_input_tokens=0, cache_read_input_tokens=900)
        return SimpleNamespace(stop_reason="end_turn", model="fake-opus", usage=usage,
                               content=[SimpleNamespace(type="text", text=json.dumps(self.label, ensure_ascii=False))])


class FakeGpt:
    def __init__(self, label, exc=None):
        self.label, self.exc, self.calls = label, exc, []

    def ask(self, system, user, schema, name):
        self.calls.append((system, user, schema, name))
        if self.exc:
            raise self.exc
        return self.label, {"input_tokens": 100, "input_tokens_details": {"cached_tokens": 50}, "output_tokens": 20}, "fake-gpt"


def _lab(tier, hs=False, rf=()):
    return {"tier": tier, "hard_stop": hs, "rf_ids": list(rf), "rationale_zh": "理由", "confidence": "high"}


def test_annotate_is_blind_and_checks_agreement(tmp_path):
    cases = sg.load_synth_cases(_write_synth(tmp_path))
    cfg = sg.prompts()
    opus = FakeAnthropic(_lab("T0", True, ["RF-03"]))
    gpt = FakeGpt(_lab("T0", True, ["RF-03"]))
    rows = sa.annotate(cases[:1], {"opus": sa.OpusAnnotator(opus), "gpt": sa.GptAnnotator(gpt)}, cfg, workers=1)
    assert rows[0]["agree"] and rows[0]["labels"]["opus"]["model_version"] == "fake-opus"
    req = opus.requests[0]
    system = req["system"][0]["text"]
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"} and req["model"] == "claude-opus-5-5"
    assert req["output_config"]["format"]["schema"] == sa.LABEL_SCHEMA and req["output_config"]["effort"] == "medium"
    assert sa.rules_excerpt() in system and "ND-01" not in system
    user = req["messages"][0]["content"]
    assert cases[0].opening_zh in user and render_sheet(cases[0]) in user
    for banned in ("acs_today", "general", "SYN-T01", "Scripted", "provisional"):   # 看不到類別、人物風格、id、系統結果
        assert banned not in user
    assert gpt.calls[0][0] == system and gpt.calls[0][1] == user
    assert rows[0]["labels"]["opus"]["est_cost_usd"] == pytest.approx((100 * 4 + 50 * 20 + 900 * 4 * 0.1) / 1e6)


def test_annotate_disagreement_and_errors_do_not_leak(tmp_path):
    cases = sg.load_synth_cases(_write_synth(tmp_path))
    cfg = sg.prompts()

    class Leaky(Exception):
        status_code = 401

        def __str__(self):
            return "Incorrect API key provided: sk-proj-abcd"

    rows = sa.annotate(cases[:1], {"opus": sa.OpusAnnotator(FakeAnthropic(_lab("T1"))),
                                   "gpt": sa.GptAnnotator(FakeGpt(None, exc=Leaky()))}, cfg, workers=1)
    assert not rows[0]["agree"] and rows[0]["errors"]["gpt"] == "Leaky HTTP 401"
    assert not sa.agree(_lab("T0", True), _lab("T0", False))
    assert sa.agree(_lab("T1", True), _lab("T0", True))          # hard_stop 一律視為 T0
    assert sa.normalized(_lab("T9")) == (9, False)


# ---------------------------------------------------------------- 評估
def test_clopper_pearson_known_values():
    assert se.clopper_pearson(0, 10)[1] == pytest.approx(1 - 0.025 ** 0.1, abs=1e-6)
    assert se.clopper_pearson(10, 10)[0] == pytest.approx(0.025 ** 0.1, abs=1e-6)
    lo, hi = se.clopper_pearson(5, 10)
    assert lo == pytest.approx(0.1871, abs=1e-4) and hi == pytest.approx(0.8129, abs=1e-4)
    assert se.clopper_pearson(0, 0) is None
    assert se.prop(3, 4)["p"] == 0.75


def _o(tier, hs=False, urg=None, n_q=None):
    return {"tier": tier, "hs": hs, "rf": [], "urg": (-1 if hs else tier) if urg is None else urg, "t9_fallback": None,
            "n_q": n_q, "stop": None}


def test_metrics_under_over_exact_and_ed_burden():
    rows = [
        {"id": "x1", "ref": _o(0, True), "a": _o(0, False)},            # HS miss → under
        {"id": "x2", "ref": _o(2), "a": _o(0)},                          # over、急診負擔
        {"id": "x3", "ref": _o(3), "a": _o(3)},                          # exact
        {"id": "x4", "ref": _o(1), "a": _o(9, urg=1)},                   # T9 備援 T1：同急迫度、不算 under，但不 exact
        {"id": "x5", "ref": None, "a": _o(4)},                           # 無參考 → 不計
        {"id": "x6", "ref": _o(0), "a": _o(9, urg=1)},                   # T9 備援 T1 比參考 T0 不急 → under（經由 T9）
    ]
    m = se.metrics(rows, "a", "ref")
    assert m["n"] == 5 and m["hs_sensitivity"]["x"] == 0 and m["hs_miss"] == ["x1"]
    assert m["under_cases"] == ["x1", "x6"] and m["under_via_t9"]["x"] == 1
    assert m["over_cases"] == ["x2"] and m["exact"]["x"] == 1 and m["t9"]["x"] == 2
    assert m["ed_burden"]["n"] == 3 and m["ed_burden_cases"] == ["x2"]
    assert se.conservative(_o(9, urg=1) | {"tier": 9}, _o(1))["tier"] == 1
    assert se.conservative(_o(0, True), _o(0))["hs"] is True


def _multi_case_client(cases):
    """run_llm 共用一個 client：依 system prompt 裡的開場白找到 case，交給 test_llm_patient.FakeClient 照事實回答。"""
    fakes = {c.opening_zh: FakeClient(c) for c in cases}

    def create(**kw):
        return next(f for o, f in fakes.items() if o in kw["system"])._create(**kw)
    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create)))


def test_three_layers_reports_and_adjudication(tmp_path):
    path = _write_synth(tmp_path)
    cases = sg.load_synth_cases(path)
    out = run_llm(cases, client=_multi_case_client(cases), model="claude-opus-5-5", effort="medium", workers=1)
    assert all(err is None for _, _, err in out)
    tr = transcripts_json([r for r, _, _ in out], cases)
    for c, (r, _, _) in zip(cases, out):
        c_out = se.replay(c, next(t for t in tr if t["case_id"] == c.id))
        b_out = se.layer_b(c)
        s = run_case(c, patient=ScriptedPatient(c))
        assert (c_out["tier"], c_out["hs"], c_out["n_q"]) == (r.final.tier, r.final.hard_stop, r.n_questions)
        assert (b_out["tier"], b_out["hs"]) == (s.final.tier, s.final.hard_stop)
    a = [se.layer_a(c) for c in cases]
    assert a[0]["hs"] and a[0]["urg"] == -1
    reference = {"_meta": {"est_cost_usd": {"opus": 0.1, "gpt": 0.05}}, "cases": [
        {"case_id": "SYN-T01", "labels": {"opus": _lab("T0", True, ["RF-03"]), "gpt": _lab("T0", True, ["RF-03"])}, "errors": {}},
        {"case_id": "SYN-T02", "labels": {"opus": _lab("T1"), "gpt": _lab("T3")}, "errors": {}},
        {"case_id": "SYN-T03", "labels": {"opus": _lab("T0"), "gpt": _lab("T0")}, "errors": {}}]}
    rows = se.build_rows(sg.load_synth(path)["scenarios"], reference, tr)
    assert all(r["a"] and r["b"] and r["c"] and not r["errors"] for r in rows)
    assert rows[0]["ref_agree"]["hs"] and rows[1]["ref_agree"] is None and rows[1]["ref_cons"]["tier"] == 1
    adj = se.adjudication_rows(rows)
    ids = {r["id"] for r in adj}
    assert "SYN-T02" in ids and "SYN-T01" not in ids             # 一致且系統沒有比較不急 → 不列
    t02 = next(r for r in adj if r["id"] == "SYN-T02")
    assert "標註者不一致" in t02["reasons"]
    m = se.summarize(rows)
    assert m["ref_agree"]["a"]["n"] == 2 and m["ref_cons"]["a"]["n"] == 3
    md = se.render_report(rows, m, {"scenarios": "s", "reference": "r", "llm_json": "l", "gen": sg.load_synth(path)}, adj,
                          {"合計": 0.1}, {"model": "fake", "model_versions": [], "errors": []}, "2026-01-01")
    assert md.index("## 限制") < md.index("## 結論摘要") and "Clopper-Pearson" in md
    amd = se.render_adjudication_md(adj, "2026-01-01")
    assert "Clinical Owner 裁定" in amd and CASES[1]["opening_zh"] in amd
    x = tmp_path / "adj.xlsx"
    table = se.adjudication_table(adj)
    se.write_xlsx(x, [("裁定表", table, se.ADJ_WIDTHS), ("說明", [["a", "b"], ["c", "d"]], [10, 10])])
    with zipfile.ZipFile(x) as z:
        names = set(z.namelist())
        assert {"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml",
                "xl/styles.xml"} <= names
        for n in names:
            ElementTree.fromstring(z.read(n))                    # 每個 part 都是合法 XML
        sheet = z.read("xl/worksheets/sheet1.xml").decode()
    assert "Clinical Owner 裁定" in sheet and CASES[1]["opening_zh"] in sheet and table[0] == se.ADJ_COLUMNS
    root = ElementTree.fromstring(sheet)
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    assert root.find("m:dimension", ns).get("ref") == f"A1:Q{len(table)}"
    assert all(len(row.findall("m:c", ns)) == len(se.ADJ_COLUMNS) for row in root.iter(f"{{{ns['m']}}}row"))   # 輸入欄也有空白儲存格
    sem = se.slot_semantics([dict(CASES[1], slots={**CASES[1]["slots"], "rest_symptom": True, "rest_symptom_first_time": True,
                                                    "exertion_relation": "rest_only"})])
    assert sem["rest_symptom_true_no_chest"] == ["SYN-T02"] and sem["exertion_relation_no_chest"] == ["SYN-T02"]
    assert sem["a_t0_only_by_rest_new_no_chest"] == ["SYN-T02"] and sem["rest_symptom_true_postprandial_relieved"] == []
    assert "10. **生成資料的 slot 語意問題**" in se.semantics_limit(sem)


def test_run_llm_eval_scenarios_option(tmp_path, monkeypatch):
    path = _write_synth(tmp_path)
    cases = sg.load_synth_cases(path)
    monkeypatch.setenv(run_llm_eval.KEY_ENV, "fake")
    monkeypatch.setattr(run_llm_eval, "make_client", lambda: _multi_case_client(cases))
    monkeypatch.setattr(sys, "argv", ["run_llm_eval", "--scenarios", str(path), "--out", str(tmp_path / "r"), "--workers", "1"])
    run_llm_eval.main()
    js = [p for p in (tmp_path / "r").glob("*.json") if not p.name.endswith("_transcripts.json")]
    assert len(js) == 1 and "_synth_" in js[0].name
    d = json.loads(js[0].read_text(encoding="utf-8"))
    assert d["errors"] == [] and d["metrics"]["n_cases"] == 3 and d["deviations"] == []
    assert run_llm_eval.SYNTH_NOTE in js[0].with_suffix(".md").read_text(encoding="utf-8")       # 無 truth 的指標標成不適用
    tr = json.loads(js[0].with_name(js[0].stem + "_transcripts.json").read_text(encoding="utf-8"))
    assert [t["case_id"] for t in tr] == ["SYN-T01", "SYN-T02", "SYN-T03"]
