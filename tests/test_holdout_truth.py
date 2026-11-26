"""D-52 保留集 truth：48 例最終裁定（AI 代理裁定（Fable 5.2，2026-11-25，Clinical Owner 授權），未經 Clinical Owner 逐例審閱）
＋其餘一致標註。sim.synth_eval 與 sim.closed_loop 保留集路徑加「對 truth」指標，既有對參考標註的指標不變。
保留集內容不讀不印：只比對 case id、分級、來源與彙總數字。"""
import json
import sys

import pytest

import sim.closed_loop as cl
from acs_triage.loaders import REPO_ROOT
from sim import synth_annotate as sa, synth_eval as se, synth_gen as sg
from sim.cases import all_cases
from sim.run_llm_eval import run_llm, transcripts_json

from test_synth import CASES as SYN, _lab, _multi_case_client, _write_synth

FINAL = REPO_ROOT / "reports" / "synth_adjudication_2026-10-26_final.json"
FABLE = REPO_ROOT / "reports" / "synth_adjudication_2026-10-26_fable.json"
REVIEW = REPO_ROOT / "reports" / "synth_adjudication_2026-10-26_fable_review.json"
MARKER = "AI 代理裁定（Fable 5.2，2026-11-25，Clinical Owner 授權），未經 Clinical Owner 逐例審閱"
OVERRIDES = {"SYN-114": ("T0", "low"), "SYN-145": ("T3", "low"), "SYN-066": ("T3", "low"), "SYN-074": ("T3", "low")}


def _j(p):
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 最終裁定檔
def test_final_adjudication_format_and_overrides():
    final, fable, review = _j(FINAL), _j(FABLE), _j(REVIEW)
    assert final["_meta"]["marker"] == MARKER and final["_meta"]["n_cases"] == 48
    labs = {k: v for k, v in final.items() if k != "_meta"}
    assert set(labs) == {k for k in fable if k != "_meta"} and len(labs) == 48
    props = sa.LABEL_SCHEMA["properties"]
    for cid, lab in labs.items():
        assert set(sa.LABEL_SCHEMA["required"]) <= set(lab), cid
        assert lab["tier"] in props["tier"]["enum"] and isinstance(lab["hard_stop"], bool), cid
        assert lab["rf_ids"] == [] and lab["confidence"] in props["confidence"]["enum"], cid          # Fable 沒給紅旗編號 → 未知
        assert isinstance(lab["rationale_zh"], str) and lab["rationale_zh"], cid
        assert lab["adjudicator"] == MARKER and lab["source"] in ("fable", "review_override"), cid
        assert not lab["hard_stop"] or lab["tier"] == "T0", cid
    flagged = {k for k, v in review.items() if k != "_meta" and v["verdict"] in ("DISAGREE-more-urgent", "DEVIATION-UNJUSTIFIED")}
    assert flagged == set(OVERRIDES) == {k for k, v in labs.items() if v["source"] == "review_override"}
    for cid, (tier, conf) in OVERRIDES.items():
        lab = labs[cid]
        assert (lab["tier"], lab["hard_stop"], lab["confidence"]) == (tier, False, conf), cid
        assert lab["review_reason"] == review[cid]["reason"] and lab["review_verdict"] == review[cid]["verdict"], cid
        assert lab["fable_tier"] == f"T{fable[cid]['tier']}" != tier, cid
    for cid in ("SYN-066", "SYN-074"):
        assert "C7 C" in labs[cid]["rationale_zh"]
    for cid, lab in labs.items():
        if cid not in OVERRIDES:                                                                   # 其他列沿用 Fable
            f = fable[cid]
            assert (lab["tier"], lab["hard_stop"], lab["confidence"], lab["rationale_zh"]) == \
                   (f"T{f['tier']}", f["hard_stop"], f["confidence"], f["rationale"]), cid


def test_holdout_truth_covers_every_case():
    """真實保留集：48 例裁定、其餘一致標註，沒有 truth 的 0 例（只看彙總）。"""
    ref = {r["case_id"]: r for r in _j(cl.HOLDOUT_REFERENCE)["cases"]}
    adj = se.load_adjudication(FINAL)
    src = []
    for case in sg.load_synth_cases(cl.HOLDOUT_SCENARIOS):
        labels = ref[case.id]["labels"]
        agree = se.ref_outcome(labels["opus"], case) if sa.agree(labels.get("opus"), labels.get("gpt")) else None
        src.append(se.truth_of(case, adj.get(case.id), agree)[1])
    assert len(src) == 150 and src.count("adjudicated") == 48 and src.count(None) == 0
    assert src.count("consensus") == 102


# ---------------------------------------------------------------- truth 規則
def test_truth_of_precedence():
    case = all_cases()[0]
    agree = se.ref_outcome(_lab("T2"), case)
    t, s = se.truth_of(case, _lab("T1"), agree)
    assert (t["tier"], t["hs"], s) == (1, False, "adjudicated")                 # 有裁定 → 裁定優先於一致標註
    t, s = se.truth_of(case, _lab("T3", True), None)
    assert (t["tier"], t["hs"], s) == (0, True, "adjudicated")                  # hard_stop 一律視為 T0
    assert se.truth_of(case, None, agree) == (agree, "consensus")
    assert se.truth_of(case, None, None) == (None, None)


def _rows(tmp_path, adjudication):
    path = _write_synth(tmp_path)
    cases = sg.load_synth_cases(path)
    out = run_llm(cases, client=_multi_case_client(cases), model="claude-opus-5-5", effort="medium", workers=1)
    tr = transcripts_json([r for r, _, _ in out], cases)
    reference = {"_meta": {"est_cost_usd": {"opus": 0.1, "gpt": 0.05}}, "cases": [
        {"case_id": "SYN-T01", "labels": {"opus": _lab("T0", True, ["RF-03"]), "gpt": _lab("T0", True, ["RF-03"])}, "errors": {}},
        {"case_id": "SYN-T02", "labels": {"opus": _lab("T1"), "gpt": _lab("T3")}, "errors": {}},
        {"case_id": "SYN-T03", "labels": {"opus": _lab("T0"), "gpt": _lab("T1")}, "errors": {}}]}
    return path, cases, tr, reference, se.build_rows(sg.load_synth(path)["scenarios"], reference, tr, adjudication)


def test_build_rows_and_summary_vs_truth_keep_reference_metrics(tmp_path):
    adjudication = {"SYN-T02": _lab("T4"), "SYN-T01": _lab("T2")}               # 裁定改寫一致的 T01、不一致的 T02；T03 不一致且沒裁定
    *_, rows = _rows(tmp_path, adjudication)
    by = {r["id"]: r for r in rows}
    assert [by[i]["truth_source"] for i in ("SYN-T01", "SYN-T02", "SYN-T03")] == ["adjudicated", "adjudicated", None]
    assert by["SYN-T01"]["truth"]["tier"] == 2 and not by["SYN-T01"]["truth"]["hs"] and by["SYN-T03"]["truth"] is None
    m = se.summarize(rows)
    assert m["truth_coverage"] == {"adjudicated": 2, "consensus": 0, "none": 1}
    a = m["vs_truth"]["a"]
    assert a["n"] == 2 and a["hs_sensitivity"]["n"] == 0
    a_t01 = by["SYN-T01"]["a"]
    assert ("SYN-T01" in a["over_cases"]) == (a_t01["urg"] < 2) and ("SYN-T01" in a["under_cases"]) == (a_t01["urg"] > 2)
    *_, rows0 = _rows(tmp_path, None)                                         # 沒有裁定 → truth＝一致標註
    m0 = se.summarize(rows0)
    assert m0["truth_coverage"] == {"adjudicated": 0, "consensus": 1, "none": 2}
    assert m0["vs_truth"]["a"]["hs_miss"] == m0["ref_agree"]["a"]["hs_miss"] and m0["vs_truth"]["a"]["n"] == m0["ref_agree"]["a"]["n"] == 1
    for k in ("ref_agree", "ref_cons", "vs_annotator", "agree"):              # 既有指標不受 truth 影響
        assert m[k] == m0[k]
    assert m["vs_truth"]["a"]["hs_miss"] == [] and m0["vs_truth"]["a"]["hs_sensitivity"]["n"] == 1


def test_synth_eval_main_writes_truth_metrics(tmp_path, monkeypatch):
    path, cases, tr, reference, _ = _rows(tmp_path, None)
    (tmp_path / "ref.json").write_text(json.dumps(reference, ensure_ascii=False), encoding="utf-8")
    llm = {"model": "claude-opus-5-5", "model_versions": ["fake"], "effort": "medium", "deviations": [], "errors": [],
           "usage": {"est_cost_usd": 0.0}}
    (tmp_path / "llm.json").write_text(json.dumps(llm), encoding="utf-8")
    (tmp_path / "llm_transcripts.json").write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    truth = {"_meta": {"marker": MARKER}, "SYN-T02": _lab("T0", True, ["RF-03"])}
    (tmp_path / "truth.json").write_text(json.dumps(truth, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["synth_eval", "--scenarios", str(path), "--reference", str(tmp_path / "ref.json"),
                                      "--truth", str(tmp_path / "truth.json"), "--llm-json", str(tmp_path / "llm.json"),
                                      "--date", "2026-01-01", "--out", str(tmp_path / "o")])
    se.main()
    rep = _j(tmp_path / "o" / "synth_eval_2026-01-01.json")
    assert rep["metrics"]["truth_coverage"] == {"adjudicated": 1, "consensus": 1, "none": 1}
    assert rep["inputs"]["truth"].endswith("truth.json") and rep["metrics"]["vs_truth"]["a"]["hs_sensitivity"]["n"] == 2
    assert {c["id"]: c["truth_source"] for c in rep["cases"]} == {"SYN-T01": "consensus", "SYN-T02": "adjudicated", "SYN-T03": None}
    md = (tmp_path / "o" / "synth_eval_2026-01-01.md").read_text(encoding="utf-8")
    assert "### 對 truth（D-52：最終裁定 1 例＋其餘一致標註 1 例；無 truth 1 例不計）" in md and MARKER in md
    assert "### 參考一致子集（主分析）" in md and "### 全部 150 例（保守參考＝兩位標註者中較急者）" in md


# ---------------------------------------------------------------- 閉環保留集路徑
def _sys(tier, hs=False, supported=None):
    return {"tier": tier, "hs": hs, "rf": [], "urg": -1 if hs else tier, "t9_fallback": None, "n_q": 3, "stop": "x",
            "hs_supported": supported, "n_confirms": 0, "reasks": 0, "reask_downgrades": 0}


def test_closed_loop_holdout_metrics_vs_truth(tmp_path, monkeypatch):
    a, b, c = all_cases()[:3]
    ref = {"cases": [{"case_id": a.id, "labels": {"opus": _lab("T1"), "gpt": _lab("T1")}},
                     {"case_id": b.id, "labels": {"opus": _lab("T2"), "gpt": _lab("T3")}},
                     {"case_id": c.id, "labels": {"opus": _lab("T2"), "gpt": _lab("T4")}}]}
    (tmp_path / "ref.json").write_text(json.dumps(ref), encoding="utf-8")
    (tmp_path / "truth.json").write_text(json.dumps({"_meta": {}, b.id: _lab("T0", True)}), encoding="utf-8")
    monkeypatch.setattr(cl, "HOLDOUT_REFERENCE", tmp_path / "ref.json")
    monkeypatch.setattr(cl, "HOLDOUT_TRUTH", tmp_path / "truth.json")
    rows = {a.id: _sys(1), b.id: _sys(0, True, supported=False), c.id: _sys(3)}
    m = cl.holdout_metrics(rows, [a, b, c])
    t = m["truth"]
    assert t["coverage"] == {"adjudicated": 1, "consensus": 1, "none": 1} and t["n"] == 2
    assert t["hs_sensitivity"]["n"] == 1 and t["hs_miss"] == [b.id] and t["premature"] == [b.id]   # 只靠抽錯的值 → miss
    assert t["exact"]["x"] == 1 and t["under_cases"] == [b.id] and t["t9"]["x"] == 0
    assert m["ref_agree"]["n"] == 1 and m["ref_cons"]["n"] == 3 and m["ref_agree"]["hs_miss"] == []      # 既有指標照舊


def test_truth_file_is_frozen_but_not_a_transcript_input():
    rel = cl.HOLDOUT_TRUTH.relative_to(REPO_ROOT).as_posix()
    assert rel == "reports/synth_adjudication_2026-10-26_final.json" and cl.HOLDOUT_TRUTH == se.DEFAULT_TRUTH
    assert rel in cl.FROZEN_FILES and rel in cl.NOT_IN_TRANSCRIPT_CHECK      # 凍結後不得改；只影響計分，不使逐字稿過期


def test_holdout_run_refuses_without_truth_file(tmp_path, monkeypatch):
    for name in ("HOLDOUT_SCENARIOS", "HOLDOUT_STRUCTURED", "HOLDOUT_REFERENCE"):
        f = tmp_path / f"{name}.json"
        f.write_text("[]", encoding="utf-8")
        monkeypatch.setattr(cl, name, f)
    monkeypatch.setattr(cl, "HOLDOUT_TRUTH", tmp_path / "no_such_truth.json")
    monkeypatch.setattr(cl, "HOLDOUT_REGISTRY", tmp_path / "runs.json")
    monkeypatch.setattr(cl, "check_holdout_allowed", lambda *a: {})
    with pytest.raises(SystemExit, match="輸入檔不存在"):
        cl.run_main(["--set", "holdout", "--arm", "structured", "--cache-dir", str(tmp_path / "c"), "--out", str(tmp_path / "o")])
    assert not cl.HOLDOUT_REGISTRY.exists()
