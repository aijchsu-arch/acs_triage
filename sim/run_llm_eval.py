"""M2b 評估入口：LLM 扮演病人跑全部 case，與 ScriptedPatient（clean）比對。

python -m sim.run_llm_eval [--model claude-opus-5-5] [--effort low] [--workers 8] [--limit N] [--out reports/]

產出 reports/eval_<date>_llm.md／.json，以及 llm_transcripts_<date>.json（逐題問答，供人工抽查）。
金鑰只讀 ACS_PATIENT_LLM_KEY（D-31）；缺少時只印 MISSING 並結束，不印任何金鑰內容。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import date
from pathlib import Path

from acs_triage.loaders import REPO_ROOT, rules_version

from .cases import Case, all_cases
from .llm_patient import DEFAULT_MODEL, KEY_ENV, LLMPatientSimulator, _prompt_cfg, make_client
from .metrics import Metrics, compute
from .run_eval import _fmt_pct, render_md, run_all
from .runner import RunResult, run_case


def _run_one(case: Case, client, model: str, effort: str) -> tuple[RunResult | None, LLMPatientSimulator, str | None]:
    p = LLMPatientSimulator(case, client=client, model=model, effort=effort)
    try:
        return run_case(case, patient=p), p, None
    except Exception as e:  # noqa: BLE001 — 單案失敗要記錄並在報告列出，不讓整批中斷
        return None, p, f"{type(e).__name__}: {e}"


def run_llm(cases: list[Case], *, client, model: str, effort: str, workers: int):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda c: _run_one(c, client, model, effort), cases))


def _key(r: RunResult) -> str:
    return f"{r.final.tier}{'Y' if r.final.hard_stop else ''}"


# 估算成本用的牌價（USD / 1M tokens：input, output；cache 寫入 1.25×input、讀取 0.1×input）。
# 來源：Claude API 價目（2026-10-06 快取版）；以帳單為準。
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00), "claude-opus-5-5": (4.00, 20.00)}


def usage_summary(patients: list[LLMPatientSimulator], model: str) -> dict:
    u = {k: sum(p.usage[k] for p in patients) for k in patients[0].usage} if patients else {}
    pin, pout = PRICES.get(model, (None, None))
    if pin is not None and u:
        u["est_cost_usd"] = round((u["input_tokens"] * pin + u["output_tokens"] * pout
                                   + u["cache_creation_input_tokens"] * pin * 1.25
                                   + u["cache_read_input_tokens"] * pin * 0.1) / 1e6, 4)
    return u


def render_compare(llm_res: list[RunResult], m_llm: Metrics, scripted: dict[str, RunResult], m_s: Metrics,
                   patients: list[LLMPatientSimulator], errors: list[tuple[str, str]]) -> str:
    devs = [d for p in patients for d in p.deviations]
    n_turns = sum(len(r.turns) for r in llm_res)
    oracle_unknown = sum(1 for r in llm_res for t in r.turns
                         if scripted_turn_unknown(r.case_id, t.question_id, patients))
    by_kind = Counter(d.kind for d in devs)
    dev_cases = {d.case_id for d in devs}
    L: list[str] = []
    L.append("## M2b：LLM 病人 vs ScriptedPatient（clean）")
    L.append("")
    L.append("| 指標 | LLM 病人 | Scripted clean |")
    L.append("|---|---|---|")
    rows = [
        ("Hard-stop miss", f"{len(m_llm.hard_stop_miss)}/{m_llm.hard_stop_truth}", f"{len(m_s.hard_stop_miss)}/{m_s.hard_stop_truth}"),
        ("Hard-stop false alarm", len(m_llm.hard_stop_false_alarm), len(m_s.hard_stop_false_alarm)),
        ("Under-triage", len(m_llm.under_triage), len(m_s.under_triage)),
        ("Over-triage", len(m_llm.over_triage), len(m_s.over_triage)),
        ("Abstention FP / FN", f"{len(m_llm.abstain_fp)} / {len(m_llm.abstain_fn)}", f"{len(m_s.abstain_fp)} / {len(m_s.abstain_fn)}"),
        ("Tier exact", _fmt_pct(m_llm.exact_rate), _fmt_pct(m_s.exact_rate)),
        ("Escalating recall", _fmt_pct(m_llm.escalating_recall), _fmt_pct(m_s.escalating_recall)),
        ("Questions-to-decision", f"{m_llm.mean_questions:.1f}", f"{m_s.mean_questions:.1f}"),
    ]
    for name, a, b in rows:
        L.append(f"| {name} | {a} | {b} |")
    L.append("")
    L.append("## 病人模型偏差（與 hidden sheet 比對，D-30）")
    L.append("")
    L.append(f"- 總回答數：{n_turns}；偏差 {len(devs)}（{_fmt_pct(len(devs) / n_turns) if n_turns else '—'}），分布 {dict(by_kind)}")
    L.append(f"- **編造率**（sheet 無此事實卻給出答案）：{by_kind['fabricated']}/{oracle_unknown}"
             f"（{_fmt_pct(by_kind['fabricated'] / oracle_unknown) if oracle_unknown else '—'}）")
    L.append(f"- 有偏差的 case：{len(dev_cases)}")
    L.append("")
    if devs:
        L.append("| case | 題目 | 類型 | sheet | LLM | 病人原話 |")
        L.append("|---|---|---|---|---|---|")
        for d in devs:
            utt = d.utterance_zh.replace("|", "\\|").replace("\n", " ")
            L.append(f"| {d.case_id} | {d.question_id} | {d.kind} | {d.expected} | {d.got} | {utt} |")
        L.append("")
    L.append("## 最終結果與 Scripted 不同的 case")
    L.append("")
    diff = [(r, scripted[r.case_id]) for r in llm_res if _key(r) != _key(scripted[r.case_id])]
    if not diff:
        L.append("（無）")
    for r, s in diff:
        why = "病人偏差" if r.case_id in dev_cases else "無偏差（需查）"
        L.append(f"- {r.case_id}：truth {r.truth_tier}{'Y' if r.truth_hard_stop else ''}，LLM {_key(r)}，Scripted {_key(s)}（{why}）")
    L.append("")
    u = usage_summary(patients, patients[0].model) if patients else {}
    L.append("## Token 用量與估算成本")
    L.append("")
    for k, v in u.items():
        L.append(f"- {k}：{v}")
    L.append("- 成本為依牌價估算（`PRICES`），以帳單為準；output 含 thinking token。")
    L.append("")
    L.append(f"## 執行錯誤（{len(errors)}）")
    L.append("")
    L.append("（無）" if not errors else "\n".join(f"- {cid}：{msg}" for cid, msg in errors))
    L.append("")
    return "\n".join(L)


def scripted_turn_unknown(case_id: str, qid: str, patients: list[LLMPatientSimulator]) -> bool:
    from acs_triage.loaders import question_by_id
    p = next(p for p in patients if p.case.id == case_id)
    v = p.oracle.answer(question_by_id()[qid]).value
    return v is None or v == "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--effort", default="low")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None, help="只跑前 N 個 case（冒煙測試）")
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    if not os.environ.get(KEY_ENV):
        print(f"{KEY_ENV}: MISSING")
        sys.exit(2)
    print(f"{KEY_ENV}: OK")

    cases = all_cases()[: args.limit] if args.limit else all_cases()
    t0 = time.monotonic()
    out = run_llm(cases, client=make_client(), model=args.model, effort=args.effort, workers=args.workers)
    elapsed = time.monotonic() - t0
    llm_res = [r for r, _, _ in out if r is not None]
    patients = [p for r, p, _ in out if r is not None]
    errors = [(p.case.id, err) for _, p, err in out if err]
    m_llm = compute(llm_res)
    s_res, _ = run_all("clean", seed=0)
    scripted = {r.case_id: r for r in s_res}
    m_s = compute([scripted[r.case_id] for r in llm_res])

    versions = sorted({v for p in patients for v in p.model_versions})
    label = (f"LLMPatientSimulator（{args.model}，effort={args.effort}，回應 model_version={', '.join(versions)}，"
             f"prompt_version={_prompt_cfg()['prompt_version']}）")
    label += f"；成功 {len(llm_res)}／{len(cases)} case（失敗的 case 不計入任何指標，見「執行錯誤」）"
    md = render_md("llm", 0, llm_res, m_llm, patient_label=label)
    md = md.replace("\n## 核心安全指標", "\n" + render_compare(llm_res, m_llm, scripted, m_s, patients, errors)
                    + "\n## 核心安全指標（LLM 病人）", 1)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    tag = "" if (args.model, args.effort) == (DEFAULT_MODEL, "low") else f"_{args.model.removeprefix('claude-')}_{args.effort}"
    stem = f"eval_{date.today().isoformat()}_llm{tag}{'_limit' + str(args.limit) if args.limit else ''}"
    (outdir / f"{stem}.md").write_text(md, encoding="utf-8")
    devs = [asdict(d) for p in patients for d in p.deviations]
    (outdir / f"{stem}.json").write_text(json.dumps(
        {"model": args.model, "model_versions": versions, "effort": args.effort, "rules_version": rules_version(),
         "metrics": m_llm.to_dict(), "scripted_metrics": m_s.to_dict(), "deviations": devs,
         "errors": errors, "usage": usage_summary(patients, args.model),
         "wall_seconds": round(elapsed, 1)}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (outdir / f"{stem}_transcripts.json").write_text(json.dumps(
        [{"case_id": r.case_id, "opening_zh": next(c.opening_zh for c in cases if c.id == r.case_id),
          "final": _key(r), "stop": r.stop_reason,
          "turns": [{"q": t.question_id, "value": t.answer, "utterance_zh": t.utterance_zh} for t in r.turns]}
         for r in llm_res], ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"n": len(llm_res), "errors": len(errors), "hard_stop_miss": m_llm.hard_stop_miss,
                      "under": m_llm.under_triage, "over": m_llm.over_triage, "deviations": len(devs)},
                     ensure_ascii=False))
    print(f"→ {outdir / (stem + '.md')}")


if __name__ == "__main__":
    main()
