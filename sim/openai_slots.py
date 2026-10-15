"""M3b slot 抽取評估（D-36、D-38）：病人中文口語回答 → 該題 slot 值，OpenAI vs 關鍵詞抽取器。

python -m sim.openai_slots [--limit N] [--workers 8] [--transcripts ...] [--out reports/]

- 每一輪問答一次呼叫；正確答案 = M2b Opus 病人逐字稿該輪的結構化答案（D-34：與 sheet 零矛盾）。
- 對照組：同一句話交給現行關鍵詞抽取器 extract()（不知道題目脈絡）。
- 「不知道」（None）與選擇題的 unknown（不記得）在 runner 中意義不同，分開計數，不算成一般錯誤。
- 產出 reports/m3b_slots_<date>_<model>[_limitN].md／.json。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

from acs_triage.decision.openai_adapter import KEY_ENV, OpenAIStructured, usage_cost
from acs_triage.extract import extract
from acs_triage.loaders import DATA_DIR, REPO_ROOT, _load_yaml, question_by_id, slot_defs
from acs_triage.schemas import Question

from .openai_eval import DEFAULT_TRANSCRIPTS, PRICES
from .patient import _ZH_CHOICE
from .run_eval import _fmt_pct


def slot_schema(q: Question) -> dict[str, Any]:
    if q.answer_type == "yes_no":
        ans: dict[str, Any] = {"type": "boolean"}
    elif q.answer_type == "choice":
        ans = {"type": "string", "enum": list(slot_defs()[q.slot_id]["choices"])}
    elif q.answer_type == "duration":
        ans = {"type": "number"}
    else:
        ans = {"type": "string"}
    return {"type": "object", "properties": {"dont_know": {"type": "boolean"}, "answer": ans},
            "required": ["dont_know", "answer"], "additionalProperties": False}


def choices_text(q: Question) -> str:
    if q.answer_type != "choice":
        return ""
    return "選項：" + "、".join(f"{c}（{_ZH_CHOICE.get(c, c)}）" for c in slot_defs()[q.slot_id]["choices"])


def norm(v: Any) -> Any:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v


SPEECHLESS = {"exertion_relation": "unclear", "symptom_character": "vague"}   # D-40：「說不上來」記為此選項


def grade(truth: Any, pred: Any, slot: str | None = None) -> str:
    if norm(truth) == norm(pred):
        return "correct"
    if truth is None and slot in SPEECHLESS and pred == SPEECHLESS[slot]:
        return "speechless"               # D-40 前的逐字稿把「說不上來」記成不知道；依裁定抽成 unclear／vague

    if {truth, pred} <= {None, "unknown"}:
        return "unknown_equiv"            # 「不知道」與「不記得」互換
    if pred is None or pred == "unknown":
        return "missed"                   # 病人有答，抽取成不知道
    if truth is None or truth == "unknown":
        return "invented"                 # 病人沒答，抽取出值
    return "wrong"


def turns(transcripts: list[dict], case_ids: set[str] | None) -> list[dict]:
    qb = question_by_id()
    out = []
    for t in transcripts:
        if case_ids is not None and t["case_id"] not in case_ids:
            continue
        for i, turn in enumerate(t["turns"], 1):
            q = qb[turn["q"]]
            out.append({"case_id": t["case_id"], "turn": i, "q": q.id, "slot": q.slot_id, "priority": q.priority,
                        "answer_type": q.answer_type, "utterance_zh": turn["utterance_zh"], "truth": turn["value"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--transcripts", default=str(DEFAULT_TRANSCRIPTS))
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    cfg = _load_yaml(DATA_DIR / "openai_prompts.yaml")
    if not os.environ.get(KEY_ENV):
        print(f"{KEY_ENV}: MISSING")
        sys.exit(2)
    print(f"{KEY_ENV}: OK")
    model, effort = cfg["model"], cfg["reasoning_effort"]
    client = OpenAIStructured(model=model, effort=effort)
    transcripts = json.loads(Path(args.transcripts).read_text(encoding="utf-8"))
    ids = {t["case_id"] for t in transcripts[: args.limit]} if args.limit else None
    items = turns(transcripts, ids)
    qb = question_by_id()

    def one(it: dict):
        q = qb[it["q"]]
        user = cfg["slot_user_zh"].format(slot_id=q.slot_id, answer_type=q.answer_type, choices=choices_text(q),
                                          question_zh=q.script_zh.strip(), utterance_zh=it["utterance_zh"])
        try:
            obj, usage, m = client.ask(cfg["slot_system_zh"], user, slot_schema(q), "slot_value")
        except Exception as e:  # noqa: BLE001
            return None, (f"{it['case_id']}#t{it['turn']}", f"{type(e).__name__}: {e}")
        pred = None if obj["dont_know"] else obj["answer"]
        rule = extract(it["utterance_zh"]).get(it["slot"])
        return {**it, "pred": pred, "rule_pred": rule, "grade": grade(it["truth"], pred, it["slot"]),
                "rule_grade": grade(it["truth"], rule, it["slot"]), "usage": usage, "model": m}, None

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        out = list(ex.map(one, items))
    rows = [x for x, _ in out if x]
    errors = [e for _, e in out if e]
    price = PRICES[model]
    cost = sum(usage_cost(r["usage"], *price) for r in rows)
    full_n = len(turns(transcripts, None))
    g, rg = Counter(r["grade"] for r in rows), Counter(r["rule_grade"] for r in rows)
    n = len(rows)
    # 安全：紅旗題中病人答「有」(True) 卻抽成非 True
    rf_pos = [r for r in rows if r["priority"] == "redflag" and r["truth"] is True]
    rf_pos_miss = [r for r in rf_pos if r["pred"] is not True]
    rf_pos_miss_rule = [r for r in rf_pos if r["rule_pred"] is not True]
    by_type: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by_type[r["answer_type"]][r["grade"]] += 1

    L = [f"# M3b slot 抽取：OpenAI vs 關鍵詞抽取器 — {date.today().isoformat()}", "",
         f"- 模型：`{model}` effort={effort}，回應 model：{', '.join(sorted({r['model'] for r in rows}))}；prompts_version {cfg['prompts_version']}",
         f"- 輪數 {n}（錯誤 {len(errors)}）；正確答案 = M2b Opus 病人逐字稿每輪的結構化答案", "",
         "## 總覽", "", "| 結果 | OpenAI | 關鍵詞抽取器 |", "|---|---|---|"]
    for k, label in [("correct", "正確"), ("unknown_equiv", "「不知道」⇄「不記得」互換"),
                     ("speechless", "「說不上來」→ unclear／vague（D-40，非錯誤，逐句列於下）"), ("missed", "漏抽（病人有答，判成不知道）"),
                     ("wrong", "抽錯值"), ("invented", "多抽（病人沒答，卻抽出值）")]:
        L.append(f"| {label} | {g[k]}（{_fmt_pct(g[k] / n) if n else '—'}） | {rg[k]}（{_fmt_pct(rg[k] / n) if n else '—'}） |")
    L += ["", f"- **紅旗題中病人答「有」**：{len(rf_pos)} 輪；OpenAI 未抽成「有」{len(rf_pos_miss)}；關鍵詞抽取器 {len(rf_pos_miss_rule)}", "",
          "## OpenAI 依題型", "", "| 題型 | 正確 | 互換 | 漏抽 | 抽錯 | 多抽 |", "|---|---|---|---|---|---|"]
    for t, c in sorted(by_type.items()):
        L.append(f"| {t} | {c['correct']} | {c['unknown_equiv']} | {c['missed']} | {c['wrong']} | {c['invented']} |")
    L += ["", "## 「說不上來」→ unclear／vague 的輪（D-40；請確認病人原話確為說不上來）", ""]
    for r in rows:
        if r["grade"] == "speechless":
            L.append(f"- {r['case_id']} 第 {r['turn']} 輪 {r['q']}（{r['slot']}）→ {r['pred']}｜{r['utterance_zh']}")
    L += ["", "## OpenAI 非正確的輪（互換、說不上來除外）", ""]
    for r in rows:
        if r["grade"] not in ("correct", "unknown_equiv", "speechless"):
            L.append(f"- {r['case_id']} 第 {r['turn']} 輪 {r['q']}（{r['slot']}）：正確 {r['truth']}／抽出 {r['pred']}（{r['grade']}）｜{r['utterance_zh']}")
    L += ["", "## 費用（依牌價估算，以帳單為準）", "",
          f"- 本次 US${cost:.4f}；每輪平均 US${cost / max(n, 1):.5f}；**全量 {full_n} 輪推估 US${cost / max(n, 1) * full_n:.2f}**", "",
          f"## 執行錯誤（{len(errors)}）", "", "（無）" if not errors else "\n".join(f"- {a}：{b}" for a, b in errors), ""]
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"m3b_slots_{date.today().isoformat()}_{model}{'_limit' + str(args.limit) if args.limit else ''}"
    (outdir / f"{stem}.md").write_text("\n".join(L), encoding="utf-8")
    (outdir / f"{stem}.json").write_text(json.dumps({"rows": rows, "errors": errors}, ensure_ascii=False, indent=2, default=str),
                                         encoding="utf-8")
    print(json.dumps({"turns": n, "errors": len(errors), "openai": dict(g), "rule": dict(rg),
                      "rf_pos": len(rf_pos), "rf_pos_miss": len(rf_pos_miss), "cost_now": round(cost, 4),
                      "est_full": round(cost / max(n, 1) * full_n, 2)}, ensure_ascii=False))
    print(f"→ {outdir / (stem + '.md')}")


if __name__ == "__main__":
    main()
