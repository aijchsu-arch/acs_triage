"""端到端：病人口語經抽取器再進規則（D-42）。回答「若 M4 用這個抽取器上線，會漏掉什麼」。

python -m sim.extractor_e2e [--extractor keyword] [--transcripts ...] [--out reports/]

- 重放 M2b Opus 病人逐字稿：開場白與每一句回答都交給抽取器，抽出的 slot 值進規則引擎（而非 D-32 的結構化值）。
- 對話序列固定（照逐字稿），但決策依抽取後的狀態；抽取狀態一觸發 Hard stop 即停（同真實 runner）。
- rf_reveal_turn 以結構化（真實事實）狀態計算，hard_stop_turn 以抽取狀態計算 → latency = 抽取器晚了幾句才抓到。
- 近似：真實 runner 可能因抽取狀態不足而多問到 11 題；本重放不補問，所以 Tier 9（轉護理師）可能偏多、under 偏少。
- 預設把該句抽到的**所有** slot 都寫入（比照上線行為，BLUEPRINT §3.4「病人自發說出的資訊也要填 slot」）；
  `--asked-only` 則只寫被問那題（同 M2 runner 的結構化答案），兩者差異為抽取器改寫其他 slot 的影響。
- 防呆：抽取狀態在真紅旗那句之前就誤觸發 Hard stop 的 case 列為 premature（不算命中）。
- 抽取器可換：extract_fn(句子, 被問的題目)，開場白的題目為 None；keyword = src/acs_triage/extract（不看題目）。不打 API。
  LLM 抽取器與「逐字稿／電話轉寫」兩種文字條件見 `sim/e2e_llm.py`（texts 指定送進抽取器的文字；結構化狀態一律用逐字稿原文）。
"""
from __future__ import annotations

import argparse
import inspect
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Callable

from acs_triage.extract import extract
from acs_triage.loaders import REPO_ROOT, question_by_id
from acs_triage.pathway import route
from acs_triage.rules import RulesEngine, SlotState
from acs_triage.schemas import Question

from .cases import all_cases
from .metrics import compute
from .openai_eval import DEFAULT_TRANSCRIPTS
from .openai_slots import grade
from .run_eval import _fmt_pct, render_md
from .runner import RunResult, Turn

ExtractFn = Callable[[str, "Question | None"], dict[str, Any]]


def keyword(text: str, question: Question | None = None) -> dict[str, Any]:
    """現行關鍵詞抽取器：不看題目。"""
    return extract(text)


EXTRACTORS: dict[str, ExtractFn] = {"keyword": keyword}


def replay(transcripts: list[dict], extract_fn: ExtractFn, *, asked_only: bool = False,
           texts: dict[tuple[str, int], str] | None = None) -> tuple[list[RunResult], list[dict], list[str]]:
    """texts：{(case_id, 第幾句): 送進抽取器的文字}（0 = 開場白），未列者用逐字稿原文。
    舊的單參數 extract_fn(句子)（例如直接傳 extract）仍可用：不給題目。"""
    texts = texts or {}
    if len(inspect.signature(extract_fn).parameters) < 2:
        one_arg = extract_fn
        extract_fn = lambda text, q: one_arg(text)          # noqa: E731
    cases = {c.id: c for c in all_cases()}
    qb = question_by_id()
    engine = RulesEngine()
    results: list[RunResult] = []
    slot_rows: list[dict] = []
    premature: list[str] = []
    for t in transcripts:
        case = cases[t["case_id"]]
        ext = SlotState(extract_fn(texts.get((case.id, 0), t["opening_zh"]), None))   # 抽取狀態（決策用）
        truth = SlotState(extract(t["opening_zh"]))         # 結構化狀態（只用來標記真實紅旗揭露的那句）
        for k in case.reset_slots:
            ext.set(k, None, source="reset_for_variant")
            truth.set(k, None, source="reset_for_variant")
        d = engine.decide(ext)
        dt = engine.decide(truth)
        res = RunResult(case_id=case.id, scenario_id=case.scenario_id, module=case.module, is_variant=case.is_variant,
                        truth_tier=case.truth_tier, truth_hard_stop=case.truth_hard_stop, truth_rf=case.truth_rf,
                        final=d, opening_decision=d, decisive_total=len(case.decisive_questions))
        if dt.hard_stop:
            res.rf_reveal_turn = 0
        asked: set[str] = set()
        if d.hard_stop:
            res.hard_stop_turn = 0
            res.stop_reason = "hard_stop_opening"
        else:
            for i, turn in enumerate(t["turns"], 1):
                q = qb[turn["q"]]
                asked.add(q.id)
                res.n_questions += 1
                truth.set(q.slot_id, turn["value"], asked_by=q.id, source=f"turn{i}")
                dt = engine.decide(truth)
                if dt.hard_stop and res.rf_reveal_turn is None:
                    res.rf_reveal_turn = i
                found = extract_fn(texts.get((case.id, i), turn["utterance_zh"]), q)
                got = found.get(q.slot_id)
                if asked_only:
                    if got is not None:
                        ext.set(q.slot_id, got, asked_by=q.id, source=f"turn{i}")
                else:
                    ext.update(found, source=f"turn{i}", skip_none=True)
                slot_rows.append({"case_id": case.id, "turn": i, "q": q.id, "slot": q.slot_id, "priority": q.priority,
                                  "truth": turn["value"], "pred": got, "grade": grade(turn["value"], got, q.slot_id),
                                  "utterance_zh": turn["utterance_zh"]})
                res.turns.append(Turn(q.id, q.slot_id, got, turn["utterance_zh"], 1.0))
                d = engine.decide(ext)
                if d.hard_stop:
                    res.hard_stop_turn = i
                    res.stop_reason = "hard_stop"
                    break
            else:
                res.stop_reason = "replay_end"
        if res.truth_hard_stop and d.hard_stop and (res.rf_reveal_turn is None or (res.hard_stop_turn or 0) < res.rf_reveal_turn):
            premature.append(case.id)          # 真紅旗揭露前就誤觸發：不能算命中
            d = d.model_copy(update={"hard_stop": False, "rf_hits": []})
            res.hard_stop_turn = None
            res.stop_reason = "premature_hard_stop"
        res.final = d
        res.final_slots = ext.as_dict()
        res.final_state = ext.copy()
        res.pathway_script = route(d, ext).script_id

        def covered(qid: str) -> bool:
            return qid in asked or ext.known(qb[qid].slot_id)

        res.decisive_asked_or_known = sum(1 for qid in case.decisive_questions if covered(qid))
        res.escalating_total = len(case.escalating_questions)
        res.escalating_missed = [qid for qid in case.escalating_questions if not covered(qid)]
        res.escalating_asked_or_known = res.escalating_total - len(res.escalating_missed)
        res.escalating_missed_strict = [qid for qid in case.escalating_questions
                                        if not (qid in asked or (ext.known(qb[qid].slot_id) and not ext.is_derived(qb[qid].slot_id)))]
        results.append(res)
    return results, slot_rows, premature


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractor", choices=sorted(EXTRACTORS), default="keyword")
    ap.add_argument("--transcripts", default=str(DEFAULT_TRANSCRIPTS))
    ap.add_argument("--asked-only", action="store_true", help="只寫被問那題的 slot（同 M2 runner）")
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    transcripts = json.loads(Path(args.transcripts).read_text(encoding="utf-8"))
    results, slot_rows, premature = replay(transcripts, EXTRACTORS[args.extractor], asked_only=args.asked_only)
    m = compute(results)
    g = Counter(r["grade"] for r in slot_rows)
    rf_pos = [r for r in slot_rows if r["priority"] == "redflag" and r["truth"] is True]
    rf_pos_miss = [r for r in rf_pos if r["pred"] is not True]
    lat = [(r.case_id, r.hard_stop_latency) for r in results if r.truth_hard_stop and r.final.hard_stop and (r.hard_stop_latency or 0) > 0]
    L = ["## 端到端（口語經抽取器）vs 結構化答案", "",
         f"- 抽取器：`{args.extractor}`；逐字稿：`{Path(args.transcripts).name}`（Opus 病人，結構化答案下 Hard-stop miss 0、under 0）",
         f"- 寫入方式：{'只寫被問那題（--asked-only）' if args.asked_only else '該句抽到的所有 slot 都寫入（比照上線，§3.4）'}；"
         f"對話序列照逐字稿重放、不補問；抽取狀態一觸發 Hard stop 即停（被截掉的後續輪不計入抽取統計）。",
         f"- 真紅旗揭露前就誤觸發 Hard stop（不算命中）：{premature or '（無）'}", "",
         "| 指標 | 口語經抽取器 | 結構化答案（參考） |", "|---|---|---|",
         f"| Hard-stop miss | {len(m.hard_stop_miss)}/{m.hard_stop_truth} | 0/{m.hard_stop_truth} |",
         f"| Hard-stop latency（最大） | {m.hard_stop_latency_max} 句 | 0 句 |",
         f"| Under-triage | {len(m.under_triage)} | 0 |",
         f"| Over-triage | {len(m.over_triage)} | 0 |",
         f"| Abstention FP（該判 0–4 卻判 9 → 轉護理師） | {len(m.abstain_fp)} | 0 |",
         f"| Tier exact | {_fmt_pct(m.exact_rate)} | 100% |", "",
         f"- 被問到那題的抽取結果（{len(slot_rows)} 輪）：正確 {g['correct']}、互換 {g['unknown_equiv']}、說不上來 {g['speechless']}、"
         f"漏抽 {g['missed']}、抽錯 {g['wrong']}、多抽 {g['invented']}",
         f"- 紅旗題病人答「有」{len(rf_pos)} 輪，抽取器未抽成「有」{len(rf_pos_miss)}：" +
         ("（無）" if not rf_pos_miss else "、".join(f"{r['case_id']} {r['q']}「{r['utterance_zh']}」" for r in rf_pos_miss)),
         f"- Hard stop 晚抓到（latency > 0）：{lat or '（無）'}", ""]
    md = render_md(f"e2e_{args.extractor}", 0, results, m, patient_label=f"Opus 逐字稿重放，口語經 `{args.extractor}` 抽取器（D-42）")
    md = md.replace("\n## 核心安全指標", "\n" + "\n".join(L) + "\n## 核心安全指標（口語經抽取器）", 1)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"e2e_{date.today().isoformat()}_{args.extractor}{'_askedonly' if args.asked_only else ''}"
    if (outdir / f"{stem}.md").exists():          # 同日重跑：加 _r2、_r3…，不覆蓋舊報告
        stem = next(f"{stem}_r{i}" for i in range(2, 1000) if not (outdir / f"{stem}_r{i}.md").exists())
    (outdir / f"{stem}.md").write_text(md, encoding="utf-8")
    (outdir / f"{stem}.json").write_text(json.dumps({"extractor": args.extractor, "metrics": m.to_dict(), "slot_grades": dict(g),
                                                     "rf_pos_missed": rf_pos_miss, "latency": lat, "premature": premature,
                                                     "asked_only": args.asked_only, "slot_rows": slot_rows},
                                                    ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"hs_miss": m.hard_stop_miss, "latency_max": m.hard_stop_latency_max, "under": m.under_triage,
                      "over": len(m.over_triage), "abstain_fp": len(m.abstain_fp), "exact": round(m.exact_rate, 3),
                      "slot_grades": dict(g), "rf_pos_missed": len(rf_pos_miss)}, ensure_ascii=False))
    print(f"→ {outdir / (stem + '.md')}")


if __name__ == "__main__":
    main()
