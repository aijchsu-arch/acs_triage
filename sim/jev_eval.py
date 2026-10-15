"""M3a 評估（D-36）：Jev 對每個 case 對話結束時的 slot 狀態判 tier 與「資訊是否足夠」，與規則引擎並列比較（shadow）。

python -m sim.jev_eval [--input known|all] [--limit N] [--workers 4] [--out reports/]

產出 reports/m3a_jev_<date>_<input>[_limitN].md／.json。預設 known（D-37）；all 為 M3a 基線格式。金鑰只讀 ACS_JEV_API_KEY（D-31），缺少時只印 MISSING。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from acs_triage.decision.jev_adapter import KEY_ENV, JevAdapter, load_config, slot_state, triage_questions
from acs_triage.decision.merge import merge_tier, urgency_rank
from acs_triage.loaders import REPO_ROOT, rules_version
from acs_triage.rules import SlotState

from .run_eval import _fmt_pct, run_all
from .runner import RunResult


def judge(r: RunResult, cfg: dict, *, api_key: str | None = None, transport=None, input_mode: str = "all") -> dict:
    ctx = json.dumps(slot_state(r.final_slots, cfg["state_preamble"].strip(), input_mode), ensure_ascii=False, sort_keys=True)
    jev = JevAdapter(api_key=api_key, model=cfg["model"], transport=transport, seed=r.case_id)
    tier_d, suff_d = jev.decide_many(triage_questions(cfg, ctx))
    model_tier = int(str(tier_d.answer).removeprefix("T"))
    state = SlotState(r.final_slots)
    merged = merge_tier(r.final, model_tier, state)
    rr, mr = urgency_rank(r.final.tier, state), urgency_rank(model_tier, state)
    out = {"case_id": r.case_id, "truth": r.truth_tier, "truth_hs": r.truth_hard_stop,
           "rules": r.final.tier, "rules_hs": r.final.hard_stop, "rules_sufficient": r.final.tier != 9,
           "model": model_tier, "model_conf": round(tier_d.confidence, 3),
           "model_probs": {k: round(v, 3) for k, v in (tier_d.probabilities or {}).items()},
           "sufficient_p": round(suff_d.probabilities["true"], 3), "model_sufficient": bool(suff_d.answer),
           "relation": "agree" if mr == rr and model_tier == r.final.tier else
                       ("model_less_urgent" if mr > rr else "model_more_urgent" if mr < rr else "same_urgency_diff_tier"),
           "downgrade_blocked": merged.model_downgrade_blocked, "merged_tier": merged.tier,
           "model_version": tier_d.model_version, "usage": jev.last_usage}
    if r.truth_tier is not None:
        tr = urgency_rank(r.truth_tier, state)
        out["model_vs_truth"] = "exact" if model_tier == r.truth_tier else ("under" if mr > tr else "over" if mr < tr else "same_urgency")
    return out


def render(rows: list[dict], errors: list[tuple[str, str]], cfg: dict, input_mode: str = "all") -> str:
    n = len(rows)
    rel = Counter(x["relation"] for x in rows)
    vt = Counter(x.get("model_vs_truth") for x in rows if "model_vs_truth" in x)
    suff_agree = sum(x["model_sufficient"] == x["rules_sufficient"] for x in rows)
    versions = sorted({x["model_version"] for x in rows})
    L = [f"# M3a：Jev vs 規則引擎（shadow）— {date.today().isoformat()}", "",
         f"- rules_version：{rules_version()}　Jev 要求 `{cfg['model']}`，回應 model_version：{', '.join(versions)}"
         f"　questions_version：{cfg['questions_version']}　輸入格式：`{input_mode}`",
         f"- cases：{n}（失敗 {len(errors)}）；輸入 = Scripted clean 對話結束時的英文 slot 狀態；分流結果仍由規則決定（D-36）", "",
         "## 摘要", "", "| 指標 | 值 |", "|---|---|",
         f"| 與規則完全一致 | {rel['agree']}/{n}（{_fmt_pct(rel['agree'] / n) if n else '—'}） |",
         f"| 模型比規則**不急**（若接進決策會被 ND-01 擋下） | {rel['model_less_urgent']} |",
         f"| 模型比規則**更急**（若接進決策會升級） | {rel['model_more_urgent']} |",
         f"| 急迫度相同但 tier 不同 | {rel['same_urgency_diff_tier']} |",
         f"| 「資訊是否足夠」與規則（tier≠9）一致 | {suff_agree}/{n} |",
         f"| 模型 vs truth：exact／under／over | {vt['exact']}／{vt['under']}／{vt['over']}（可評分 {sum(vt.values())}） |",
         f"| Jev input tokens 合計 | {sum((x['usage'] or {}).get('input_tokens', 0) for x in rows)} |", "",
         "- 急迫度：Hard stop／T0=0、T1–T4=1–4；Tier 9 依 C6 D 主訴對照表換算。",
         "- 「模型比規則不急」的 case 是 ND-01 的實例；「模型比規則更急」的 case 值得 Clinical Owner 檢視是否為規則漏洞。", ""]

    def table(title: str, items: list[dict]) -> None:
        L.extend([f"## {title}（{len(items)}）", ""])
        if not items:
            L.extend(["（無）", ""])
            return
        L.append("| case | truth | 規則 | 模型 | 模型信心 | 足夠 p | 規則足夠 | 機率分布 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for x in items:
            probs = " ".join(f"{k}:{v}" for k, v in sorted(x["model_probs"].items(), key=lambda kv: -kv[1])[:3])
            tr = "—" if x["truth"] is None else f"{x['truth']}{'Y' if x['truth_hs'] else ''}"
            L.append(f"| {x['case_id']} | {tr} | {x['rules']}{'Y' if x['rules_hs'] else ''} | {x['model']} | "
                     f"{x['model_conf']} | {x['sufficient_p']} | {x['rules_sufficient']} | {probs} |")
        L.append("")

    table("模型比規則更急（潛在規則漏洞，請檢視）", [x for x in rows if x["relation"] == "model_more_urgent"])
    table("模型比規則不急（ND-01 會擋）", [x for x in rows if x["relation"] == "model_less_urgent"])
    table("急迫度相同但 tier 不同", [x for x in rows if x["relation"] == "same_urgency_diff_tier"])
    table("「資訊是否足夠」與規則不一致", [x for x in rows if x["model_sufficient"] != x["rules_sufficient"]])
    L.extend([f"## 執行錯誤（{len(errors)}）", "", "（無）" if not errors else "\n".join(f"- {c}：{m}" for c, m in errors), ""])
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", choices=["known", "all"], default="known")   # D-37
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    cfg = load_config()
    if not os.environ.get(KEY_ENV):
        print(f"{KEY_ENV}: MISSING")
        sys.exit(2)
    print(f"{KEY_ENV}: OK")
    results, _ = run_all("clean", seed=0)
    if args.limit:
        results = results[: args.limit]

    def one(r: RunResult):
        try:
            return judge(r, cfg, input_mode=args.input), None
        except Exception as e:  # noqa: BLE001 — 單案失敗記錄後繼續
            return None, (r.case_id, f"{type(e).__name__}: {e}")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        out = list(ex.map(one, results))
    rows = [x for x, _ in out if x]
    errors = [e for _, e in out if e]
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = (f"m3a_jev_{date.today().isoformat()}_{args.input}"
            f"{'_limit' + str(args.limit) if args.limit else ''}")
    if (outdir / f"{stem}.md").exists():          # 同日同設定重跑：加 _r2、_r3…，不覆蓋舊報告
        stem = next(f"{stem}_r{i}" for i in range(2, 1000) if not (outdir / f"{stem}_r{i}.md").exists())
    (outdir / f"{stem}.md").write_text(render(rows, errors, cfg, args.input), encoding="utf-8")
    (outdir / f"{stem}.json").write_text(json.dumps({"rows": rows, "errors": errors}, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    print(json.dumps({"n": len(rows), "errors": len(errors), "relation": dict(Counter(x["relation"] for x in rows))},
                     ensure_ascii=False))
    print(f"→ {outdir / (stem + '.md')}")


if __name__ == "__main__":
    main()
