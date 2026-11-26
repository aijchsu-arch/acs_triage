"""保留集補跑（D-58 基礎設施失敗例外；Clinical Owner 2026-11-26 裁定）：只補跑 11-25 一次性保留集閉環中，因 Anthropic API
用量上限（BadRequestError）而沒有結果的 case。規則、提示、程式維持凍結（本檔不在 FROZEN_FILES；sim/closed_loop.py 一字不改）。

python -m sim.holdout_resume probe [--arm gpt|gemma]     # 凍結檢查＋金鑰 OK/MISSING＋1 token Anthropic 探測（不登記、不跑 case）
python -m sim.holdout_resume run --arm gpt|gemma [--opus-budget X] [--gpt-budget Y] [--scratch DIR] [--cache-dir DIR]
                                 [--out DIR] [--workers 8]
  預設（＝建議）預算：gpt arm --opus-budget 5 --gpt-budget 6（gpt 為抽取快取累計、含 11-25 已花的 US$3.18）；gemma arm --opus-budget 15。

- 前置檢查同保留集閉環：凍結紀錄存在、全部 FROZEN_FILES 與提示全文 sha256 相符（直接呼叫 check_holdout_allowed）、逐字稿版本
  檢查（check_structured_version）、輸入檔存在、金鑰（只印 OK／MISSING）、Gemma 時 LM Studio；另加 1 token Anthropic 探測，
  確認用量上限已解除。全部通過才登記；任何一項失敗都不留下登記。
- case：已 commit 的原輸出（ORIG_DIR/closed_holdout_<arm>.json）中 error 有值者，且只有這些；沒有就拒跑。
- 每個 arm 只補跑一次：resume／combined 輸出已存在，或登記檔已有該 arm 的 infra_failure_resume 紀錄 → 拒跑。登記是在同一個
  登記檔附加一筆（arm 欄照填），原本的 `sim.closed_loop run --set holdout --arm <arm>` 照樣因「已登記」拒跑。
- 執行路徑與參數同 `sim.closed_loop run --set holdout --arm <arm>`：同一個 run_arm／CachedLLMPatient／FailureTap／UsedKeys、
  病人快取以 HOLDOUT_STRUCTURED 為種子、同一份 truth 與 holdout_metrics、workers（Gemma ≤4）。--cache-dir 預設
  <scratch>/cache_holdout：空的（或不存在）→ 複製已 commit 的 cache_holdout（已 commit 的快取不動）；已有內容 → 每個檔的 sha256
  必須等於已 commit 的版本，或等於登記檔裡先前補跑紀錄的 cache_sha256_after（gpt 補跑後留下的），否則拒跑（不沿用未驗證的內容）。
  gpt 與 Gemma 補跑用同一個 --cache-dir，Gemma 可沿用 gpt 補跑新取得的病人回答。
- 基礎設施失敗＝case 的 error 有值，或有 extract_failures（抽取重試後仍失敗，含 gpt 抽取預算用完 budget_exceeded、OpenAI 4xx）。
  以 workers 個 case 為一批呼叫 run_arm；某批有這種 case → 記為 errored_again、停止該 arm（不重試、不迴圈），其餘記為
  not_attempted，結束碼 3。這些 case 不計入合併指標（n_with_result、truth.n），列在合併輸出的 errors。
- 輸出（新檔、以獨占模式建立，不覆寫原輸出）：closed_holdout_<arm>_resume.json（補跑的 case）與 closed_holdout_<arm>_combined.json
  （原本成功的 case 紀錄＋補跑結果；指標以 holdout_metrics 重算）。原本成功的 case 沒有 RunResult 物件，以逐例紀錄重建列；
  前置檢查先確認這樣重算的原輸出指標與原輸出逐項相同，不同就拒跑。寫出的絕對路徑改寫為 <scratch>／<repo>／<home>。
- 金鑰只讀環境變數（ACS_PATIENT_LLM_KEY、ACS_OPENAI_API_KEY），不印出；錯誤只記類型與狀態碼。只用合成資料（D-10）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from acs_triage.loaders import REPO_ROOT, rules_version
from acs_triage.rules import SlotState

from . import closed_loop as cl
from .llm_patient import DEFAULT_EFFORT, DEFAULT_MODEL, KEY_ENV, _prompt_cfg

ORIG_DIR = REPO_ROOT / "reports" / "extractor_v2_2026-11-25_inputs"     # 已 commit 的原輸出與快取（cache_holdout/）
KIND = "infra_failure_resume"
REASON = "Anthropic API usage limit BadRequestError; Clinical Owner 2026-11-26 approved resuming errored cases only"
DEFAULT_BUDGETS = {"gpt": {"opus": 5.0, "gpt": 6.0}, "gemma": {"opus": 15.0, "gpt": None}}   # USD；gpt 為抽取快取累計


def _j(x: Any) -> Any:
    return json.loads(json.dumps(x, ensure_ascii=False, default=str))


def sanitize(obj: Any, scratch: Path) -> Any:
    """字串中的絕對路徑 → <scratch>／<repo>／<home>（長的先換：repo 在 home 底下）。"""
    pairs: dict[str, str] = {}
    for p, tag in ((scratch, "<scratch>"), (REPO_ROOT, "<repo>"), (Path.home(), "<home>")):
        for s in (str(p.absolute()), str(p.resolve())):
            pairs.setdefault(s, tag)
    subs = sorted(pairs.items(), key=lambda kv: -len(kv[0]))

    def fix(x: Any) -> Any:
        if isinstance(x, str):
            for old, new in subs:
                x = x.replace(old, new)
            return x
        if isinstance(x, dict):
            return {k: fix(v) for k, v in x.items()}
        if isinstance(x, list):
            return [fix(v) for v in x]
        return x
    return fix(_j(obj))


# ---------------------------------------------------------------- 檢查
def check_frozen() -> dict[str, Any]:
    """保留集閉環的同一個檢查（check_holdout_allowed）：凍結紀錄、全部凍結檔與提示全文 sha256。只取它的凍結部分：arm 給一個
    不會被登記的名字、out_dir 給空目錄，它的「每個 arm 只跑一次」就不適用（補跑自己的只跑一次見 check_resume_once）。"""
    with tempfile.TemporaryDirectory() as d:
        return cl.check_holdout_allowed("_resume_freeze_check", None, Path(d))


def registry() -> list[dict[str, Any]]:
    return json.loads(cl.HOLDOUT_REGISTRY.read_text(encoding="utf-8")) if cl.HOLDOUT_REGISTRY.exists() else []


def _write_registry(runs: list[dict[str, Any]]) -> None:
    cl.HOLDOUT_REGISTRY.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")   # 同 register_holdout_run


def output_paths(arm: str, out_dir: Path) -> tuple[Path, Path]:
    return out_dir / f"closed_holdout_{arm}_resume.json", out_dir / f"closed_holdout_{arm}_combined.json"


def check_resume_once(arm: str, out_dir: Path) -> None:
    existing = [p.name for d in {out_dir.resolve(), ORIG_DIR.resolve()} for p in output_paths(arm, d) if p.exists()]
    if any(r.get("arm") == arm and r.get("kind") == KIND for r in registry()) or existing:
        raise SystemExit(f"保留集 {arm} arm 已經補跑過（{cl.HOLDOUT_REGISTRY.name} 已有 {KIND} 紀錄或已有輸出 {existing}）：每個 arm 只補跑一次")


def load_original(arm: str, freeze: dict[str, Any]) -> dict[str, Any]:
    """已 commit 的原輸出；必須是凍結版、完整（非 --limit）的保留集該 arm 輸出。"""
    path = ORIG_DIR / f"closed_holdout_{arm}.json"
    if not path.exists():
        raise SystemExit(f"原輸出不存在：{path.name}")
    rep = json.loads(path.read_text(encoding="utf-8"))
    m = rep["meta"]
    if (m.get("set"), m.get("arm"), m.get("limit")) != ("holdout", arm, None) or m.get("file_sha256") != freeze["files"]:
        raise SystemExit(f"{path.name} 不是凍結版保留集 {arm} arm 的完整輸出")
    return rep


def errored_ids(rep: dict[str, Any]) -> list[str]:
    return [r["case_id"] for r in rep["cases"] if r["error"]]


def failure(rec: dict[str, Any]) -> str | None:
    """補跑的基礎設施失敗：error 有值，或抽取重試後仍失敗（extract_failures：gpt 抽取預算用完 budget_exceeded、OpenAI 4xx…）。
    回傳原因（只含類型／狀態碼），沒失敗 → None。case_record 與 run_arm 的輸出都適用。"""
    if rec.get("error"):
        return rec["error"]
    f = rec.get("extract_failures") or []
    return f"extract_failed x{len(f)}: {f[0]['error']}" if f else None


def record_row(rec: dict[str, Any]) -> dict[str, Any]:
    """case_record → holdout_rows 的一列（同 synth_eval._outcome：urg、t9_fallback 由結束時的 slot 值重算）。"""
    from .synth_eval import tier9_fallback, urgency
    f, st = rec["final"], SlotState(rec["final_slots"])
    return {"tier": f["tier"], "hs": f["hs"], "rf": list(f["rf"]), "urg": urgency(f["tier"], f["hs"], st),
            "t9_fallback": tier9_fallback(st)[0] if f["tier"] == 9 else None, "n_q": rec["n_q"], "stop": rec["stop"],
            "hs_supported": rec["hs_supported"], "n_confirms": rec["n_confirms"],
            "reasks": len(rec["reasks"]), "reask_downgrades": len(rec["reask_downgrades"])}


def check_original_metrics(rep: dict[str, Any], cases: list[Any]) -> None:
    """以逐例紀錄重建的列重算原輸出的指標，必須與原輸出逐項相同；不同 → 合併指標不可信，登記前就停。"""
    rows = {r["case_id"]: record_row(r) for r in rep["cases"] if not r["error"]}
    if _j(cl.holdout_metrics(rows, cases)) != rep["metrics"]:
        raise SystemExit("以原輸出逐例紀錄重算的指標與原輸出不同：合併指標不可信，不補跑")


def check_keys(arm: str | None) -> None:
    """只印 OK／MISSING，不印值；缺任何一個 → exit 2（不登記）。arm=None（probe）時兩把都查。"""
    from acs_triage.decision.openai_adapter import KEY_ENV as OPENAI_KEY_ENV
    missing = False
    for k in [KEY_ENV] + ([OPENAI_KEY_ENV] if arm in (None, "gpt") else []):
        ok = bool(os.environ.get(k))
        print(f"{k}: {'OK' if ok else 'MISSING'}")
        missing = missing or not ok
    if missing:
        sys.exit(2)


def probe(client: Any) -> None:
    """1 token Anthropic 探測（病人模型），確認用量上限已解除。任何失敗都中止（呼叫端在登記前呼叫）；只記類型與狀態碼。"""
    try:
        client.beta.messages.create(model=DEFAULT_MODEL, max_tokens=1, messages=[{"role": "user", "content": "ping"}])
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "status_code", None)
        hint = "；用量上限仍未解除" if "usage limit" in str(e).lower() else ""
        raise SystemExit(f"Anthropic 探測失敗：{type(e).__name__}{f' HTTP {code}' if code else ''}{hint}（不登記、不補跑）")
    print("Anthropic probe: OK")


def cache_hashes(d: Path) -> dict[str, str]:
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(d.iterdir()) if f.is_file() and not f.name.startswith(".")}


def prepare_cache(cache_dir: Path) -> list[str]:
    """--cache-dir：空的（或不存在）→ 複製已 commit 的 cache_holdout。已有內容 → 每個檔的 sha256 必須等於已 commit 的版本，或等於
    登記檔中先前補跑紀錄的 cache_sha256_after（gpt 補跑更新過的病人快取留給 Gemma 沿用），否則拒跑：不沿用未驗證的內容。"""
    src = ORIG_DIR / "cache_holdout"
    if cache_dir.resolve() == src.resolve():
        raise SystemExit("--cache-dir 不得是已 commit 的 cache_holdout（只能用複本）")
    committed = cache_hashes(src)
    have = cache_hashes(cache_dir) if cache_dir.exists() else {}
    known = [committed] + [r.get("cache_sha256_after") or {} for r in registry() if r.get("kind") == KIND]
    bad = [n for n, h in have.items() if not any(k.get(n) == h for k in known)]
    if bad:
        raise SystemExit(f"--cache-dir 已有未驗證的內容（sha256 不等於已 commit 的快取，也不等於先前補跑紀錄）：{bad}；換一個空的 --scratch")
    cache_dir.mkdir(parents=True, exist_ok=True)
    copied = [n for n in committed if n not in have]
    for n in copied:
        shutil.copy2(src / n, cache_dir / n)
    return copied


def update_entry(arm: str, info: dict[str, Any], scratch: Path) -> None:
    runs = registry()
    next(r for r in runs if r.get("arm") == arm and r.get("kind") == KIND).update(sanitize(info, scratch))
    _write_registry(runs)


# ---------------------------------------------------------------- CLI：run
def run_main(argv: list[str]) -> None:
    from . import llm_extract_v2 as v2
    ap = argparse.ArgumentParser(prog="sim.holdout_resume run")
    ap.add_argument("--arm", choices=["gpt", "gemma"], required=True)
    ap.add_argument("--opus-budget", type=float, default=None,
                    help="Opus 病人新呼叫的估算費用上限（USD，本次補跑；同 sim.closed_loop）；預設 gpt arm 5、gemma arm 15")
    ap.add_argument("--gpt-budget", type=float, default=None,
                    help="gpt 抽取累計估算費用上限（USD，快取檔累計、含 11-25 已花的 US$3.18；同 sim.closed_loop）；預設 6（只用於 gpt arm）")
    ap.add_argument("--scratch", default=str(Path(tempfile.gettempdir()) / "acs_holdout_resume"),
                    help="scratch 目錄（輸出中的路徑改寫為 <scratch>）")
    ap.add_argument("--cache-dir", default=None, help="預設 <scratch>/cache_holdout（已 commit 快取的複本）")
    ap.add_argument("--out", default=None, help="預設與原輸出同目錄（檔名不同、不覆寫）")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(argv)
    arm, scratch = args.arm, Path(args.scratch)
    cache_dir = Path(args.cache_dir) if args.cache_dir else scratch / "cache_holdout"
    out_dir = Path(args.out) if args.out else ORIG_DIR
    if args.opus_budget is None:
        args.opus_budget = DEFAULT_BUDGETS[arm]["opus"]
    if arm == "gpt" and args.gpt_budget is None:
        args.gpt_budget = DEFAULT_BUDGETS[arm]["gpt"]
    # ---- 前置檢查（全部在登記之前；任何一項失敗都不留下登記，可修好後重試）
    freeze = check_frozen()
    check_resume_once(arm, out_dir)
    orig = load_original(arm, freeze)
    ids = errored_ids(orig)
    if not ids:
        raise SystemExit(f"closed_holdout_{arm}.json 沒有 error 的 case：不需要補跑")
    missing = [f.name for f in (cl.HOLDOUT_SCENARIOS, cl.HOLDOUT_STRUCTURED, cl.HOLDOUT_REFERENCE, cl.HOLDOUT_TRUTH) if not f.exists()]
    if missing:
        raise SystemExit(f"輸入檔不存在：{missing}")
    cl.check_structured_version(cl.HOLDOUT_STRUCTURED, "holdout")
    cases, structured = cl.load_set("holdout")
    by_id = {c.id: c for c in cases}
    if [i for i in ids if i not in by_id]:
        raise SystemExit("原輸出 error 的 case id 不在保留集裡")
    check_original_metrics(orig, cases)
    check_keys(arm)
    copied = prepare_cache(cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = cl.PatientCache(DEFAULT_MODEL, DEFAULT_EFFORT, _prompt_cfg()["prompt_version"])
    cpath = cache_dir / "patient_cache_holdout.json"
    cache.load(cpath)
    client = cl.make_client()
    tw = v2.load_to_tw()
    extractor = v2.make_extractor(arm, budget=args.gpt_budget, to_traditional=tw)
    if arm == "gemma":
        cfg = v2.load_prompts()
        cl.check_lmstudio(cfg["local_base_url"], cfg["local_model"])
    ex_meta = v2.meta_for(arm)
    epath = cache_dir / f"extract_cache_holdout_{arm}.json"
    history = extractor.load(epath, ex_meta, reparse=True)
    if arm == "gpt" and extractor.spent >= args.gpt_budget:
        raise SystemExit(f"--gpt-budget {args.gpt_budget} 不大於抽取快取已累計的 US${extractor.spent:.4f}：新抽取會全部 budget_exceeded")
    probe(client)
    started = datetime.now().isoformat(timespec="seconds")
    runs = registry()
    runs.append(sanitize({"arm": arm, "kind": KIND, "case_ids": ids, "started_at": started, "freeze_sha256": freeze["files"],
                          "reason": REASON, "original_output": str(ORIG_DIR / f"closed_holdout_{arm}.json"),
                          "out": str(out_dir), "cache_dir": str(cache_dir)}, scratch))
    _write_registry(runs)
    # ---- 補跑（同 sim.closed_loop run_main 的執行段；只換成 errored 的 case、分批以便出錯即停）
    todo = [by_id[i] for i in ids]
    n_seed = cache.seed(structured, source="seed:" + cl.HOLDOUT_STRUCTURED.name)
    budget = cl.Budget(args.opus_budget)
    tracker = cl.UsedKeys(extractor)
    keys_before, spent_before = set(extractor.cache), extractor.spent
    workers = args.workers if arm != "gemma" else min(args.workers, 4)
    outs: list[dict[str, Any]] = []
    t0 = time.monotonic()
    try:
        for i in range(0, len(todo), workers):
            outs += cl.run_arm(todo[i:i + workers], arm=arm, cache=cache, client=client, extractor=tracker, tw=tw,
                               budget=budget, workers=workers)
            if any(failure(o) for o in outs):
                break                                            # 又失敗（error 或抽取失敗）→ 停止該 arm（不重試、不迴圈）
    finally:
        cache.save(cpath)
        extractor.save(epath, ex_meta, history)
        update_entry(arm, {"cache_sha256_after": cache_hashes(cache_dir)}, scratch)   # 之後同一 --cache-dir 的補跑據此驗證
    finished = datetime.now().isoformat(timespec="seconds")
    recs = [cl.case_record(o) for o in outs]
    reasons = {r["case_id"]: failure(r) for r in recs if failure(r)}
    again = list(reasons)
    attempted = [r["case_id"] for r in recs]
    not_attempted = [i for i in ids if i not in set(attempted)]
    status = {"case_ids": ids, "attempted": attempted, "errored_again": again, "errored_again_reasons": reasons,
              "not_attempted": not_attempted}
    ok_outs = [o for o in outs if not failure(o)]
    resume_path, combined_path = output_paths(arm, out_dir)
    meta = {"set": "holdout", "arm": arm, "kind": KIND, "reason": REASON, "resume_of": f"closed_holdout_{arm}.json",
            "started_at": started, "finished_at": finished, "wall_s": round(time.monotonic() - t0, 1), "rules_version": rules_version(),
            "patient": {"model": DEFAULT_MODEL, "effort": DEFAULT_EFFORT, "prompt_version": _prompt_cfg()["prompt_version"]},
            "extractor": ex_meta, "prompts_version": v2.load_prompts()["prompts_version"], "file_sha256": cl.file_hashes(),
            "freeze": freeze, "n_seed_entries": n_seed, "structured_source": cl.HOLDOUT_STRUCTURED.name, "workers": workers,
            "opus_budget": args.opus_budget, "gpt_budget": args.gpt_budget, "cache_dir": str(cache_dir), "cache_copied": copied, **status}
    resume: dict[str, Any] = {
        "meta": meta,
        "patient_usage": {"live_calls": sum(o["patient"].n_live for o in outs), "cached_calls": sum(o["patient"].n_cached for o in outs),
                          "sources": dict(sum((o["patient"].sources for o in outs), Counter())), "opus_cost_usd": round(budget.spent, 4)},
        "extractor_usage": cl._ex_usage(extractor, tracker.used, keys_before, spent_before),
        "cases": recs, "metrics": cl.holdout_metrics(cl.holdout_rows(ok_outs), cases), "extraction": cl.extraction_stats(recs),
        "mention_conflicts": [c for o in outs if o["result"] is not None for c in o["result"].mention_conflicts],
        "mention_confirms": [c for o in outs if o["result"] is not None for c in o["result"].mention_confirms],
        "reasks": cl.all_reasks(outs),
        "extract_failures": [{"case_id": o["case"].id, **f} for o in outs for f in o.get("extract_failures", [])]}
    # ---- 合併：原本成功的紀錄＋補跑紀錄（沒補到的保留原 error 紀錄）；失敗的不計入指標；指標以同一套 holdout_metrics 重算
    new, resumed_rows = {r["case_id"]: r for r in recs}, cl.holdout_rows(ok_outs)
    merged = [new.get(r["case_id"], r) if r["error"] else r for r in orig["cases"]]
    rows = {r["case_id"]: resumed_rows[r["case_id"]] if r["case_id"] in resumed_rows else record_row(r)
            for r in merged if not failure(r)}                   # 保留原 case 順序（指標裡的 case 清單同完整一次跑的順序）
    combined = {
        "meta": {"set": "holdout", "arm": arm, "kind": f"combined_after_{KIND}", "original": f"closed_holdout_{arm}.json",
                 "resume": resume_path.name, "reason": REASON, "rules_version": rules_version(), "file_sha256": cl.file_hashes(),
                 "freeze": freeze, "original_meta": orig["meta"], "resume_meta": meta,
                 "case_sources": {"original": [r["case_id"] for r in orig["cases"] if not r["error"]],
                                  "resumed": [i for i in attempted if i not in again], **status},
                 "n_with_result": len(rows), "errors": [r["case_id"] for r in merged if failure(r)]},
        "patient_usage": {"original": orig["patient_usage"], "resume": resume["patient_usage"]},
        "extractor_usage": {"original": orig["extractor_usage"], "resume": resume["extractor_usage"]},
        "cases": merged, "metrics": cl.holdout_metrics(rows, cases), "extraction": cl.extraction_stats(merged),
        **{k: orig[k] + resume[k] for k in ("mention_conflicts", "mention_confirms", "reasks", "extract_failures")}}
    for path, rep in ((resume_path, resume), (combined_path, combined)):
        with path.open("x", encoding="utf-8") as fh:            # 獨占建立：已存在就失敗，絕不覆寫
            fh.write(json.dumps(sanitize(rep, scratch), ensure_ascii=False, indent=1))
    update_entry(arm, {"finished_at": finished, "output": str(resume_path), "combined": str(combined_path), "errored_again": again,
                       "errored_again_reasons": reasons, "not_attempted": not_attempted}, scratch)
    t = combined["metrics"]["truth"]
    print(json.dumps({"resume": {k: v for k, v in status.items() if k != "case_ids"}, "n_case_ids": len(ids),
                      "patient": resume["patient_usage"], "extractor_cost_this_run": resume["extractor_usage"]["cost_this_run_usd"],
                      "extract_failures": [f["case_id"] for f in resume["extract_failures"]]}, ensure_ascii=False))
    print(json.dumps({"combined_truth_coverage": t["coverage"], **{k: t.get(k) for k in ("hs_sensitivity", "hs_miss", "premature", "under",
                                                                                         "over", "exact", "t9")}},
                     ensure_ascii=False, default=str))
    print(f"→ {sanitize(str(resume_path), scratch)}\n→ {sanitize(str(combined_path), scratch)}")
    if again:
        print(f"補跑中又失敗、已停止 {arm} arm（不重試）：errored_again={reasons}，not_attempted={len(not_attempted)} 例")
        sys.exit(3)


def probe_main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(prog="sim.holdout_resume probe")
    ap.add_argument("--arm", choices=["gpt", "gemma"], default=None, help="只查該 arm 需要的金鑰；gemma 另查 LM Studio")
    args = ap.parse_args(argv)
    freeze = check_frozen()
    print(f"freeze: {len(freeze['files'])}/{len(cl.FROZEN_FILES)} files + prompt sha256 match")
    check_keys(args.arm)
    if args.arm == "gemma":
        from .llm_extract_v2 import load_prompts
        cfg = load_prompts()
        cl.check_lmstudio(cfg["local_base_url"], cfg["local_model"])
        print("LM Studio: OK")
    probe(cl.make_client())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        run_main(sys.argv[2:])
    elif cmd == "probe":
        probe_main(sys.argv[2:])
    else:
        print(__doc__)
