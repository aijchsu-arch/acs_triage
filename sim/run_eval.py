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


def render_md(mode: str, seed: int, results: list[RunResult], m: Metrics,
              patient_label: str = "ScriptedPatient（確定性腳本；LLM 病人為 M2b）") -> str:
    L: list[str] = []
    L.append(f"# Phase 0 評估報告 — mode={mode} seed={seed}")
    L.append("")
    L.append(f"- 日期：{date.today().isoformat()}　rules_version：{rules_version()}")
    L.append(f"- cases：{m.n_cases}（可評分 {m.n_scored}；`expect.tier: null` 的變體不計分）")
    L.append(f"- 模擬病人：{patient_label}")
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
    L.append(f"| Escalating-question recall（答案可能使分流更急的題目） | {_fmt_pct(m.escalating_recall)}（{m.escalating_hit}/{m.escalating_total}） | ≥ 90% |")
    L.append(f"| Escalating recall（嚴格：由否認推導出的值不算已知，D-42） | {_fmt_pct(m.escalating_recall_strict)}（{m.escalating_total - len(m.escalating_missed_strict)}/{m.escalating_total}） | 記錄 |")
    L.append(f"| Decisive-question recall（答案會改變分流的題目，含只會降級者） | {_fmt_pct(m.decisive_recall)}（{m.decisive_hit}/{m.decisive_total}） | 記錄 |")
    L.append(f"| Abstention precision / recall | {_fmt_pct(m.abstention_precision)} / {_fmt_pct(m.abstention_recall)} | 記錄 |")
    L.append(f"| Questions-to-decision（平均） | {m.mean_questions:.1f} | 記錄 |")
    L.append(f"| Gate effect（低信心重問次數） | {m.repeats} | 記錄 |")
    L.append(f"| Confirm-back（紅旗／關鍵題複誦確認，D-50；不算題數） | 總數 {m.confirms}；平均每通 {m.mean_confirms:.2f}；確認後改值 {m.confirm_changed}；確認值較不嚴重而保留原值 {m.confirm_downgrade_blocked} | 記錄 |")
    L.append(f"| 待追蹤檢查加問（有症狀暫判 T2–T4，rules 0.8.0；算題數） | 加問 {m.pending_test_asked} 通；已達題數上限沒問 {m.pending_test_skipped_at_cap} 通 | 記錄 |")
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
    L.append("- Decisive／Escalating 題目由 `sim/decisive.py` 依每個 case 的完整事實逐題反事實計算（D-27）：")
    L.append("  把該題換成任一可能答案，若 (provisional_tier, hard_stop) 會改變即為 decisive；其中存在答案使結果**更急**者為 escalating。")
    L.append("  Tier 9 依 C6 D 主訴對照表換算急迫度。Escalating 漏問 = 可能 under-triage，是安全指標；只會降級的題漏問只造成 over-triage。")
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

    from collections import Counter as _C
    by_q = _C(q for _, q, _, _ in m.escalating_missed)
    L.append(f"## 漏問的 escalating 題目（{len(m.escalating_missed)}）")
    L.append("")
    L.append("| 題目 | 漏問次數 |")
    L.append("|---|---|")
    for q, n in by_q.most_common():
        L.append(f"| {q} | {n} |")
    L.append("")
    L.append("明細（case, 題目, final tier, 結束原因）：")
    L.append("")
    for it in m.escalating_missed:
        L.append(f"- {it}")
    L.append("")

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
    print(json.dumps({k: v for k, v in m.to_dict().items() if k in ("n_cases", "n_scored", "exact_rate", "escalating_recall", "decisive_recall", "questions_to_decision_mean")}, ensure_ascii=False))
    print("hard_stop:", m.to_dict()["hard_stop"])
    print("under:", m.under_triage)
    print("over:", m.over_triage)
    print("abstain_fp:", m.abstain_fp)
    print("abstain_fn:", m.abstain_fn)
    print("stop:", dict(m.stop_reasons))
    print(f"→ {out / (stem + '.md')}")


if __name__ == "__main__":
    main()
