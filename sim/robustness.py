"""穩健度：單一答案翻轉敏感度（D-42）。

python -m sim.robustness [--out reports/]

對 Scripted clean 每個 case 的每一輪，把病人答案換成另一個合法值（只換一題、其他照舊），重跑規則引擎，
統計有多少「單一答案錯誤」（STT 聽反、病人答錯）會讓結果變得較不急。不打 API。
嚴重降級 = 原本 Hard stop／T0 變成 T1–T4（急症被當成門診）。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from acs_triage.loaders import REPO_ROOT, question_by_id
from acs_triage.pathway.router import tier9_fallback
from acs_triage.rules import RulesEngine, SlotState

from .decisive import answer_values
from .run_eval import _fmt_pct, run_all
from .runner import RunResult


def _urgency(d, state: SlotState) -> int:
    return -1 if d.hard_stop else (tier9_fallback(state)[0] if d.tier == 9 else d.tier)


def _label(d) -> str:
    return "HS" if d.hard_stop else f"T{d.tier}"


def flip_sensitivity(results: list[RunResult]) -> dict[str, Any]:
    engine, qb = RulesEngine(), question_by_id()
    total = under = 0
    transitions: Counter = Counter()
    by_q: dict[str, Counter] = defaultdict(Counter)
    severe: list[dict[str, Any]] = []
    rf_yes_no: dict[str, list[int]] = defaultdict(lambda: [0, 0])   # 紅旗題答「有」被聽成「沒有」→ [降級數, 輪數]
    for r in results:
        if r.truth_tier is None:
            continue
        st0 = SlotState(r.final_slots)
        d0 = engine.decide(st0)
        u0 = _urgency(d0, st0)
        for t in r.turns:
            q = qb[t.question_id]
            for alt in answer_values(q):
                if alt == t.answer:
                    continue
                s = dict(r.final_slots)
                s[q.slot_id] = alt
                st = SlotState(s)
                d = engine.decide(st)
                total += 1
                by_q[q.id]["total"] += 1
                if _urgency(d, st) > u0:
                    under += 1
                    by_q[q.id]["under"] += 1
                    transitions[f"{_label(d0)}→{_label(d)}"] += 1
                    if _label(d0) in ("HS", "T0") and d.tier in (1, 2, 3, 4):
                        severe.append({"case_id": r.case_id, "question_id": q.id, "answer": t.answer, "flipped_to": alt,
                                       "transition": f"{_label(d0)}→{_label(d)}"})
            if q.priority == "redflag" and t.answer is True:
                rf_yes_no[q.id][1] += 1
                s = dict(r.final_slots)
                s[q.slot_id] = False
                st = SlotState(s)
                if _urgency(engine.decide(st), st) > u0:
                    rf_yes_no[q.id][0] += 1
    return {"total_flips": total, "under": under,
            "transitions": dict(transitions.most_common()),
            "severe": severe,
            "by_question": {qid: {"under": c["under"], "total": c["total"], "priority": qb[qid].priority}
                            for qid, c in sorted(by_q.items(), key=lambda kv: -kv[1]["under"])},
            "redflag_yes_to_no": {qid: {"downgraded": v[0], "turns": v[1]} for qid, v in rf_yes_no.items()}}


def render(s: dict[str, Any]) -> str:
    L = [f"# 穩健度：單一答案翻轉敏感度 — {date.today().isoformat()}", "",
         "- 對 Scripted clean 每個 case 的每一輪，把答案換成另一個合法值（只換一題），重跑規則引擎；模擬 STT 聽反或病人答錯一題。",
         f"- 翻轉總數 {s['total_flips']}；變得較不急 {s['under']}（{_fmt_pct(s['under'] / s['total_flips']) if s['total_flips'] else '—'}）；"
         f"**嚴重降級（Hard stop／T0 → T1–T4）{len(s['severe'])}**", "",
         "## 降級轉移（原 → 翻轉後）", "", "| 轉移 | 次數 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in s["transitions"].items()]
    L += ["", "- T9 = 轉護理師（護理師不可得時依 C6 D 預設等級）；HS→T0 仍叫去急診，但少了「留在線上直到撥 119」。", "",
          f"## 嚴重降級明細（{len(s['severe'])}）", ""]
    L += [f"- {e['case_id']}：{e['question_id']} {e['answer']} → {e['flipped_to']}（{e['transition']}）" for e in s["severe"]] or ["（無）"]
    L += ["", "## 最容易因一個答案翻錯而降級的題目", "", "| 題目 | 優先級 | 降級／翻轉 |", "|---|---|---|"]
    L += [f"| {q} | {c['priority']} | {c['under']}/{c['total']} |" for q, c in list(s["by_question"].items())[:12]]
    L += ["", "## 紅旗題「有」被聽成「沒有」", "", "| 題目 | 降級／答有的輪數 |", "|---|---|"]
    L += [f"| {q} | {c['downgraded']}/{c['turns']} |" for q, c in s["redflag_yes_to_no"].items()]
    L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    results, _ = run_all("clean", seed=0)
    s = flip_sensitivity(results)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"robustness_{date.today().isoformat()}"
    if (outdir / f"{stem}.md").exists():          # 同日重跑：加 _r2、_r3…，不覆蓋舊報告
        stem = next(f"{stem}_r{i}" for i in range(2, 1000) if not (outdir / f"{stem}_r{i}.md").exists())
    (outdir / f"{stem}.md").write_text(render(s), encoding="utf-8")
    (outdir / f"{stem}.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"total_flips": s["total_flips"], "under": s["under"], "severe": len(s["severe"]),
                      "severe_questions": sorted({e["question_id"] for e in s["severe"]})}, ensure_ascii=False))
    print(f"→ {outdir / (stem + '.md')}")


if __name__ == "__main__":
    main()
