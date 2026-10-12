"""Phase 0 評估入口：python -m sim.run_eval [--mode clean|vague|low_stt] [--seed N] [--out reports/]

產出 reports/eval_<date>_<mode>.md 與 .json。
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from acs_triage.loaders import REPO_ROOT, rules_version

from .cases import all_cases
from .metrics import Metrics, compute
from .patient import ScriptedPatient
from .runner import RunResult, run_case

MODES = {
    "clean": dict(vague_p=0.0, low_stt_p=0.0),
    "vague": dict(vague_p=0.25, low_stt_p=0.0),
    "low_stt": dict(vague_p=0.0, low_stt_p=0.2),
}


def run_all(mode: str = "clean", seed: int = 0) -> tuple[list[RunResult], Metrics]:
    cases = all_cases()
    results = [run_case(c, patient=ScriptedPatient(c, seed=seed, **MODES[mode])) for c in cases]
    return results, compute(results)


def _fmt_pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def render_md(mode: str, seed: int, results: list[RunResult], m: Metrics) -> str:
    L: list[str] = []
    L.append(f"# Phase 0 評估報告 — mode={mode} seed={seed}")
    L.append("")
    L.append(f"- 日期：{date.today().isoformat()}　rules_version：{rules_version()}")
    L.append(f"- cases：{m.n_cases}（可評分 {m.n_scored}；`expect.tier: null` 的變體不計分）")
    L.append(f"- 模擬病人：ScriptedPatient（確定性腳本；LLM 病人為 M2b）")
    L.append("")
    L.append("## 核心安全指標")
    L.append("")
    L.append("| 指標 | 值 | 目標 |")
    L.append("|---|---|---|")
    L.append(f"| Hard-stop miss rate | {_fmt_pct(m.hard_stop_miss_rate)}（{len(m.hard_stop_miss)}/{m.hard_stop_truth}） | 0% |")
    L.append(f"| Hard-stop latency（最大） | {m.hard_stop_latency_max} 句 | 0 句 |")
    L.append(f"| Hard-stop false alarm | {len(m.hard_stop_false_alarm)} | 記錄 |")
    L.append(f"| Under-triage rate | {_fmt_pct(m.under_triage_rate)}（{len(m.under_triage)}） | 趨近 0 |")
    L.append(f"| Over-triage rate | {_fmt_pct(m.over_triage_rate)}（{len(m.over_triage)}） | 記錄 |")
    L.append(f"| Tier exact accuracy | {_fmt_pct(m.exact_rate)} | 記錄 |")
    L.append(f"| Decisive-question recall（core：redflag+decisive 題） | {_fmt_pct(m.decisive_core_recall)} | ≥ 90% |")
    L.append(f"| Decisive-question recall（all：含 refine 題） | {_fmt_pct(m.decisive_recall)} | 記錄 |")
    L.append(f"| Abstention precision / recall | {_fmt_pct(m.abstention_precision)} / {_fmt_pct(m.abstention_recall)} | 記錄 |")
    L.append(f"| Questions-to-decision（平均） | {m.mean_questions:.1f} | 記錄 |")
    L.append(f"| Gate effect（低信心重問次數） | {m.repeats} | 記錄 |")
    L.append("")
    L.append("## 混淆矩陣（truth → pred）")
    L.append("")
    tiers = [0, 1, 2, 3, 4, 9]
    L.append("| truth \\ pred | " + " | ".join(str(t) for t in tiers) + " |")
    L.append("|---|" + "---|" * len(tiers))
    for t in tiers:
        row = [str(m.confusion.get((t, p), 0)) for p in tiers]
        L.append(f"| **{t}** | " + " | ".join(row) + " |")
    L.append("")
    L.append("## 依模組")
    L.append("")
    L.append("| module | n | exact | under | over | abstain_fp | abstain_fn |")
    L.append("|---|---|---|---|---|---|---|")
    for mod, c in sorted(m.by_module.items()):
        L.append(f"| {mod} | {c['n']} | {c['exact']} | {c['under']} | {c['over']} | {c['abstain_fp']} | {c['abstain_fn']} |")
    L.append("")
    L.append("## 指標說明")
    L.append("")
    L.append("- Under/Over-triage 只計 truth 與 pred 皆在 0–4 的案例；pred 9 另計 abstention FP、truth 9 另計 abstention FN。")
    L.append("- Hard-stop latency = 揭露紅旗事實的那句與觸發 Hard stop 之間相隔的句數；引擎逐句重算，理論上恆為 0。")
    L.append("- Decisive recall 的分母是情境檔的 `decisive_questions`（設計者列的理想問題清單）；引擎只問會改變 disposition 的題，")
    L.append("  所以 refine 題常在定案前被略過，這是設計使然。core 版只計 redflag／decisive 優先級的題。")
    L.append("- 資訊不足組（persona vague）的 base case 以 `max_questions` 結束並維持 Tier 9 是**預期行為**（節制），不是失敗。")
    L.append("")
    L.append("## 結束原因")
    L.append("")
    for k, v in sorted(m.stop_reasons.items()):
        L.append(f"- {k}: {v}")
    L.append("")

    def _list(title: str, items: list) -> None:
        L.append(f"## {title}（{len(items)}）")
        L.append("")
        if not items:
            L.append("（無）")
        for it in items:
            L.append(f"- {it}")
        L.append("")

    _list("Hard-stop miss", m.hard_stop_miss)
    _list("Hard-stop false alarm", m.hard_stop_false_alarm)
    _list("Under-triage（case, truth, pred）", m.under_triage)
    _list("Over-triage（case, truth, pred）", m.over_triage)
    _list("Abstention FP（truth 0–4 但最終 9）", m.abstain_fp)
    _list("Abstention FN（truth 9 但給了 0–4）", m.abstain_fn)
    _list("RF 不一致（case, expected rf, got）", m.rf_mismatch)

    L.append("## 每案摘要")
    L.append("")
    L.append("| case | truth | final | HS | stop | Q | 問到的題 |")
    L.append("|---|---|---|---|---|---|---|")
    for r in results:
        qs = " ".join(t.question_id.replace("Q-", "") for t in r.turns)
        tr = "—" if r.truth_tier is None else f"{r.truth_tier}{'Y' if r.truth_hard_stop else ''}"
        fi = f"{r.final.tier}{'Y' if r.final.hard_stop else ''}"
        mark = "" if (r.truth_tier is None or (r.final.tier == r.truth_tier and r.final.hard_stop == r.truth_hard_stop)) else " ⚠"
        L.append(f"| {r.case_id} | {tr} | {fi}{mark} | {','.join(r.final.rf_hits)} | {r.stop_reason} | {r.n_questions} | {qs} |")
    L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=sorted(MODES), default="clean")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    results, m = run_all(args.mode, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"eval_{date.today().isoformat()}_{args.mode}"
    (out / f"{stem}.md").write_text(render_md(args.mode, args.seed, results, m), encoding="utf-8")
    (out / f"{stem}.json").write_text(json.dumps(m.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in m.to_dict().items() if k in ("n_cases", "n_scored", "exact_rate", "decisive_recall_core", "decisive_recall_all", "questions_to_decision_mean")}, ensure_ascii=False))
    print("hard_stop:", m.to_dict()["hard_stop"])
    print("under:", m.under_triage)
    print("over:", m.over_triage)
    print("abstain_fp:", m.abstain_fp)
    print("abstain_fn:", m.abstain_fn)
    print("stop:", dict(m.stop_reasons))
    print(f"→ {out / (stem + '.md')}")


if __name__ == "__main__":
    main()
