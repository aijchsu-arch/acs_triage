"""M3b 評估（D-36、D-38）：OpenAI 逐句紅旗＋分級對照（shadow，分流仍由規則決定）。

python -m sim.openai_eval [--limit N] [--workers 8] [--transcripts reports/...transcripts.json] [--out reports/]

- 逐句紅旗：每一步（開場白、每輪問答後）把到目前為止的中文對話交給模型，逐條判斷 RF-01～06；
  正確答案 = 規則引擎依當下 slot 狀態算出的 rf_hits（對話取自 M2b Opus 病人逐字稿）。
- 分級：與 Jev 相同的英文題目（data/jev_questions.yaml）與第二版輸入（D-37）。
- 產出 reports/m3b_openai_<date>_<model>[_limitN].md／.json，含 token 用量、實際費用與全量推估。
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

from acs_triage.decision.jev_adapter import load_config as load_jev_config, slot_state
from acs_triage.decision.merge import merge_tier, urgency_rank
from acs_triage.decision.openai_adapter import KEY_ENV, OpenAIStructured, usage_cost
from acs_triage.extract import extract
from acs_triage.loaders import DATA_DIR, REPO_ROOT, _load_yaml, question_by_id, rules_version
from acs_triage.rules import RulesEngine, SlotState

from .cases import all_cases
from .run_eval import _fmt_pct, run_all

RFS = ["RF-01", "RF-02", "RF-03", "RF-04", "RF-05", "RF-06"]
# USD / 1M tokens：input, cached input, output。來源：OpenAI 官方價目頁（2026-10-15 查證）；以帳單為準。
PRICES = {"gpt-6.1-sol": (2.00, 0.10, 10.00)}
DEFAULT_TRANSCRIPTS = REPO_ROOT / "reports" / "eval_2026-10-16_llm_opus-5-5_medium_transcripts.json"
RF_SCHEMA = {"type": "object", "properties": {rf: {"type": "boolean"} for rf in RFS},
             "required": RFS, "additionalProperties": False}
TIERS = ["T0", "T1", "T2", "T3", "T4", "T9"]
TIER_SCHEMA = {"type": "object", "properties": {"tier": {"type": "string", "enum": TIERS}, "sufficient": {"type": "boolean"}},
               "required": ["tier", "sufficient"], "additionalProperties": False}


def rf_steps(transcripts: list[dict], case_ids: set[str] | None = None) -> list[dict]:
    """每個 case 的每一步：{case_id, step, opening_zh, dialogue_zh, label}（label = 規則引擎 rf_hits）。"""
    cases = {c.id: c for c in all_cases()}
    qb = question_by_id()
    engine = RulesEngine()
    out = []
    for t in transcripts:
        if case_ids is not None and t["case_id"] not in case_ids:
            continue
        case = cases[t["case_id"]]
        state = SlotState(extract(t["opening_zh"]))
        for k in case.reset_slots:
            state.set(k, None, source="reset_for_variant")
        lines: list[str] = []
        out.append({"case_id": case.id, "step": 0, "opening_zh": t["opening_zh"], "dialogue_zh": "",
                    "label": sorted(engine.decide(state).rf_hits)})
        for i, turn in enumerate(t["turns"], 1):
            q = qb[turn["q"]]
            state.set(q.slot_id, turn["value"], asked_by=q.id, source=f"turn{i}")
            lines += [f"客服：{q.script_zh.strip()}", f"病人：{turn['utterance_zh']}"]
            out.append({"case_id": case.id, "step": i, "opening_zh": t["opening_zh"], "dialogue_zh": "\n".join(lines),
                        "label": sorted(engine.decide(state).rf_hits)})
    return out


def tier_prompt(cfg: dict) -> str:
    crit = "\n".join(f"- {k}: {v}" for k, v in cfg["tier"]["criteria"].items())
    return (f"{cfg['tier']['instructions']}\n\n{cfg['principles'].strip()}\n\nTiers:\n{crit}\n\n"
            f"Also answer 'sufficient': {cfg['sufficient']['instructions'].strip()}")


def summarize_rf(rows: list[dict]) -> dict:
    per = {}
    for rf in RFS:
        tp = sum(rf in r["label"] and r["pred"][rf] for r in rows)
        fn = sum(rf in r["label"] and not r["pred"][rf] for r in rows)
        fp = sum(rf not in r["label"] and r["pred"][rf] for r in rows)
        tn = len(rows) - tp - fn - fp
        per[rf] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn}
    any_l = [bool(r["label"]) for r in rows]
    any_p = [any(r["pred"].values()) for r in rows]
    return {"per_rf": per, "steps": len(rows),
            "hs_steps_label": sum(any_l), "hs_missed_by_model": sum(l and not p for l, p in zip(any_l, any_p)),
            "hs_added_by_model": sum(p and not l for l, p in zip(any_l, any_p))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--transcripts", default=str(DEFAULT_TRANSCRIPTS))
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    cfg = _load_yaml(DATA_DIR / "openai_prompts.yaml")
    jev_cfg = load_jev_config()
    if not os.environ.get(KEY_ENV):
        print(f"{KEY_ENV}: MISSING")
        sys.exit(2)
    print(f"{KEY_ENV}: OK")
    model, effort = cfg["model"], cfg["reasoning_effort"]
    client = OpenAIStructured(model=model, effort=effort)

    results, _ = run_all("clean", seed=0)
    if args.limit:
        results = results[: args.limit]
    ids = {r.case_id for r in results}
    transcripts = json.loads(Path(args.transcripts).read_text(encoding="utf-8"))
    steps = rf_steps(transcripts, ids)

    def do_rf(s: dict):
        user = cfg["redflag_user_zh"].format(opening_zh=s["opening_zh"], dialogue=s["dialogue_zh"])
        try:
            pred, usage, m = client.ask(cfg["redflag_system_zh"], user, RF_SCHEMA, "redflags")
            return {**s, "pred": pred, "usage": usage, "model": m}, None
        except Exception as e:  # noqa: BLE001
            return None, (f"{s['case_id']}@{s['step']}", f"{type(e).__name__}: {e}")

    tsys = tier_prompt(jev_cfg)

    def do_tier(r):
        user = json.dumps(slot_state(r.final_slots, jev_cfg["state_preamble"].strip(), "known"), ensure_ascii=False, sort_keys=True)
        try:
            ans, usage, m = client.ask(tsys, user, TIER_SCHEMA, "triage_tier")
        except Exception as e:  # noqa: BLE001
            return None, (r.case_id, f"{type(e).__name__}: {e}")
        mt = int(ans["tier"].removeprefix("T"))
        st = SlotState(r.final_slots)
        rr, mr = urgency_rank(r.final.tier, st), urgency_rank(mt, st)
        row = {"case_id": r.case_id, "truth": r.truth_tier, "rules": r.final.tier, "rules_hs": r.final.hard_stop,
               "model": mt, "model_sufficient": ans["sufficient"], "rules_sufficient": r.final.tier != 9,
               "relation": "agree" if mt == r.final.tier else
                           ("model_less_urgent" if mr > rr else "model_more_urgent" if mr < rr else "same_urgency_diff_tier"),
               "downgrade_blocked": merge_tier(r.final, mt, st).model_downgrade_blocked, "usage": usage, "model_version": m}
        if r.truth_tier is not None:
            tr = urgency_rank(r.truth_tier, st)
            row["model_vs_truth"] = "exact" if mt == r.truth_tier else ("under" if mr > tr else "over" if mr < tr else "same_urgency")
        return row, None

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        rf_out = list(ex.map(do_rf, steps))
        tier_out = list(ex.map(do_tier, results))
    rf_rows = [x for x, _ in rf_out if x]
    tier_rows = [x for x, _ in tier_out if x]
    errors = [e for _, e in rf_out + tier_out if e]

    price = PRICES[model]
    rf_cost = sum(usage_cost(r["usage"], *price) for r in rf_rows)
    tier_cost = sum(usage_cost(r["usage"], *price) for r in tier_rows)
    full_steps = len(rf_steps(transcripts))
    full_turns = full_steps - len(transcripts)
    n_cases_all = len(run_all("clean", seed=0)[0]) if args.limit else len(results)
    est = {"redflag_per_call": rf_cost / max(len(rf_rows), 1), "tier_per_call": tier_cost / max(len(tier_rows), 1)}
    est["redflag_full"] = est["redflag_per_call"] * full_steps
    est["tier_full"] = est["tier_per_call"] * n_cases_all
    est["slot_extraction_full_extrapolated"] = est["redflag_per_call"] * full_turns   # 推估：每輪一次、提示長度相近
    est["total_full"] = est["redflag_full"] + est["tier_full"] + est["slot_extraction_full_extrapolated"]
    rf_sum = summarize_rf(rf_rows)
    rel = Counter(x["relation"] for x in tier_rows)
    vt = Counter(x.get("model_vs_truth") for x in tier_rows if "model_vs_truth" in x)
    versions = sorted({x["model"] for x in rf_rows} | {x["model_version"] for x in tier_rows})

    L = [f"# M3b：OpenAI vs 規則引擎（shadow）— {date.today().isoformat()}", "",
         f"- 模型：要求 `{model}` effort={effort}，回應 model：{', '.join(versions)}；prompts_version {cfg['prompts_version']}；rules {rules_version()}",
         f"- cases：{len(results)}；紅旗步數 {len(rf_rows)}；分級 {len(tier_rows)}；錯誤 {len(errors)}", "",
         "## 逐句紅旗（每步判斷到目前為止的對話；正確答案 = 規則引擎）", "",
         "| RF | TP | FN | FP | TN | 敏感度 | 特異度 |", "|---|---|---|---|---|---|---|"]
    for rf, c in rf_sum["per_rf"].items():
        sens = _fmt_pct(c["tp"] / (c["tp"] + c["fn"])) if c["tp"] + c["fn"] else "—"
        spec = _fmt_pct(c["tn"] / (c["tn"] + c["fp"])) if c["tn"] + c["fp"] else "—"
        L.append(f"| {rf} | {c['tp']} | {c['fn']} | {c['fp']} | {c['tn']} | {sens} | {spec} |")
    L += ["", f"- 規則判紅旗成立的步數 {rf_sum['hs_steps_label']}；模型漏掉 {rf_sum['hs_missed_by_model']}；"
              f"模型多判（規則未成立）{rf_sum['hs_added_by_model']}——若接進決策（規則 OR 模型），多判的會變成額外 Hard stop。", ""]
    disagree = [r for r in rf_rows if set(r["label"]) != {k for k, v in r["pred"].items() if v}]
    L += [f"### 紅旗不一致的步（{len(disagree)}）", ""]
    for r in disagree:
        L.append(f"- {r['case_id']} 第 {r['step']} 步：規則 {r['label'] or '無'}／模型 {[k for k, v in r['pred'].items() if v] or '無'}")
    L += ["", "## 分級（與 Jev 相同題目、第二版輸入）", "", "| 指標 | 值 |", "|---|---|",
          f"| 與規則完全一致 | {rel['agree']}/{len(tier_rows)} |",
          f"| 模型比規則不急（ND-01 會擋） | {rel['model_less_urgent']} |",
          f"| 模型比規則更急 | {rel['model_more_urgent']} |",
          f"| 模型判 T9 | {sum(x['model'] == 9 for x in tier_rows)} |",
          f"| 模型 vs truth exact／under／over | {vt['exact']}／{vt['under']}／{vt['over']} |",
          f"| 「資訊足夠」與規則一致 | {sum(x['model_sufficient'] == x['rules_sufficient'] for x in tier_rows)}/{len(tier_rows)} |", ""]
    for x in tier_rows:
        if x["relation"] != "agree":
            L.append(f"- {x['case_id']}：truth {x['truth']}，規則 {x['rules']}{'Y' if x['rules_hs'] else ''}，模型 {x['model']}（{x['relation']}）")
    L += ["", "## 費用（依牌價估算，以帳單為準；output 含 reasoning tokens）", "",
          f"- 本次實際：紅旗 US${rf_cost:.4f}、分級 US${tier_cost:.4f}，合計 US${rf_cost + tier_cost:.4f}",
          f"- 每次呼叫平均：紅旗 US${est['redflag_per_call']:.5f}、分級 US${est['tier_per_call']:.5f}",
          f"- **全量推估**（{n_cases_all} cases、紅旗 {full_steps} 步）：紅旗 US${est['redflag_full']:.2f} ＋ 分級 US${est['tier_full']:.2f} "
          f"＋ slot 抽取（尚未實作，以紅旗每次費用 × {full_turns} 輪推估）US${est['slot_extraction_full_extrapolated']:.2f} "
          f"＝ **US${est['total_full']:.2f}**", "",
          f"## 執行錯誤（{len(errors)}）", "", "（無）" if not errors else "\n".join(f"- {a}：{b}" for a, b in errors), ""]
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"m3b_openai_{date.today().isoformat()}_{model}{'_limit' + str(args.limit) if args.limit else ''}"
    (outdir / f"{stem}.md").write_text("\n".join(L), encoding="utf-8")
    (outdir / f"{stem}.json").write_text(json.dumps({"rf": rf_rows, "rf_summary": rf_sum, "tier": tier_rows, "estimate": est,
                                                     "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rf_steps": len(rf_rows), "tier": len(tier_rows), "errors": len(errors),
                      "hs_missed": rf_sum["hs_missed_by_model"], "hs_added": rf_sum["hs_added_by_model"],
                      "tier_relation": dict(rel), "cost_now": round(rf_cost + tier_cost, 4),
                      "est_full": round(est["total_full"], 2)}, ensure_ascii=False))
    print(f"→ {outdir / (stem + '.md')}")


if __name__ == "__main__":
    main()
