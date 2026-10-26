"""實驗 2：完整流程重放（口語 → 文字 → 抽取器 → 規則），3 抽取器 × 2 文字條件（D-42 延伸；M4 抽取模型，D-47）。

python -m sim.e2e_llm [--extractors keyword,gpt,gemma] [--conditions ref,phone] [--limit N] [--workers 8]
                      [--budget 12] [--cache-dir DIR] [--out reports/]

- 逐字稿：D-49 合成語音的來源 `reports/eval_2026-10-20_llm_opus-5-5_medium_transcripts.json`（Opus 病人；
  `reports/stt_utterances_2026-10-22.json` 是由它建的）。
- 文字條件：ref = 逐字稿原文；phone = 同一句經合成電話語音＋本機 Whisper 的轉寫 `hyp_tw`（已轉繁體，D-49），
  取自 `reports/stt_whisper_2026-10-22.json` 的 rows（condition = phone；與 A 段原始結果 JSON 的 hyp_tw 相同）。
  對不到轉寫的句子改用原文並計數。
- 抽取器：keyword（現行）；gpt = gpt-6.1-sol（Responses API strict json_schema、store false、effort 依 openai_prompts.yaml）；
  gemma = 本機 LM Studio（OpenAI 相容端點、json_schema；輸出再驗證，不合法 = 抽取失敗）。提示見 `sim/llm_extract.py`。
- 重放用 `sim.extractor_e2e.replay`（不補問）；「結構化答案」= 同一份逐字稿、同一版規則、每輪寫入逐字稿的結構化值。
- 呼叫紀錄存 --cache-dir（可續跑、不重複付費）；--limit 只跑前 N 個 case（估算費用用）。只用合成資料（D-10）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any, Callable

from acs_triage.decision.openai_adapter import KEY_ENV, OpenAIStructured
from acs_triage.extract import extract
from acs_triage.loaders import REPO_ROOT, question_by_id, rules_version
from acs_triage.prompter.confirm import needs_confirm
from acs_triage.rules import RulesEngine, SlotState
from acs_triage.schemas import Question

from .cases import all_cases
from .extractor_e2e import ExtractFn, keyword, replay
from .llm_extract import LLMExtractor, LMStudioStructured, load_prompts
from .metrics import compute
from .openai_eval import PRICES
from .openai_slots import grade
from .run_eval import _fmt_pct

DEFAULT_TRANSCRIPTS = REPO_ROOT / "reports" / "eval_2026-10-20_llm_opus-5-5_medium_transcripts.json"
DEFAULT_STT = REPO_ROOT / "reports" / "stt_whisper_2026-10-22.json"
STT_CONDITION = "phone"
OK_GRADES = ("correct", "unknown_equiv", "speechless")
PRIORITIES = ["redflag", "decisive", "refine"]
COND_LABEL = {"ref": "逐字稿原文", "phone": "電話語音＋Whisper（hyp_tw）"}

Key = tuple[str, int]                      # (case_id, 第幾句)；0 = 開場白


# ---------------------------------------------------------------- 文字與句子
def utterances(t: dict) -> list[tuple[int, str, str | None]]:
    """[(第幾句, 原文, 題目 id)]；開場白題目為 None。"""
    return [(0, t["opening_zh"], None)] + [(i, x["utterance_zh"], x["q"]) for i, x in enumerate(t["turns"], 1)]


def phone_texts(transcripts: list[dict], stt_rows: list[dict]) -> tuple[dict[Key, str], list[Key]]:
    """依原文對到 STT rows（condition = phone）的 hyp_tw；回傳 (texts, 對不到的句子)。"""
    hyp = {r["ref"]: r["hyp_tw"] for r in stt_rows if r["condition"] == STT_CONDITION}
    texts: dict[Key, str] = {}
    unmatched: list[Key] = []
    for t in transcripts:
        for i, s, _ in utterances(t):
            if s in hyp:
                texts[(t["case_id"], i)] = hyp[s]
            else:
                unmatched.append((t["case_id"], i))
    return texts, unmatched


def items(transcripts: list[dict], texts: dict[Key, str]) -> list[tuple[str, Question | None]]:
    qb = question_by_id()
    return [(texts.get((t["case_id"], i), s), qb[qid] if qid else None) for t in transcripts for i, s, qid in utterances(t)]


def structured_fn(transcripts: list[dict]) -> ExtractFn:
    """結構化答案：開場白 = 關鍵詞抽取逐字稿（同 M2 runner 的起始狀態）；每輪 = 逐字稿記下的結構化值。"""
    table: dict[tuple[str, str], Any] = {}
    for t in transcripts:
        for x in t["turns"]:
            k = (x["q"], x["utterance_zh"])
            if k in table and table[k] != x["value"]:
                raise ValueError(f"同一題同一句有兩種結構化值：{k}")
            table[k] = x["value"]

    def fn(text: str, q: Question | None = None) -> dict[str, Any]:
        return extract(text) if q is None else {q.slot_id: table[(q.id, text)]}
    return fn


# ---------------------------------------------------------------- 指標
def full_rows(transcripts: list[dict], fn: ExtractFn, texts: dict[Key, str]) -> list[dict]:
    """每一輪（不因 Hard stop 截斷）被問那題的抽取結果，分母固定，可跨格比較。"""
    qb = question_by_id()
    rows = []
    for t in transcripts:
        for i, x in enumerate(t["turns"], 1):
            q = qb[x["q"]]
            text = texts.get((t["case_id"], i), x["utterance_zh"])
            pred = fn(text, q).get(q.slot_id)
            rows.append({"case_id": t["case_id"], "turn": i, "q": q.id, "slot": q.slot_id, "priority": q.priority,
                         "truth": x["value"], "pred": pred, "grade": grade(x["value"], pred, q.slot_id),
                         "text": text, "ref": x["utterance_zh"]})
    return rows


def opening_diffs(transcripts: list[dict], fn: ExtractFn, texts: dict[Key, str]) -> dict[str, Any]:
    """開場白抽取 vs 結構化事實（關鍵詞抽取逐字稿；cases.py 的情境事實即由此起算），依不同開場白計。"""
    seen: dict[str, dict[str, Any]] = {}
    for t in transcripts:
        text = texts.get((t["case_id"], 0), t["opening_zh"])
        if t["opening_zh"] in seen:
            continue
        truth, pred = extract(t["opening_zh"]), fn(text, None)
        seen[t["opening_zh"]] = {"case_id": t["case_id"], "text": text,
                                 "missing": sorted(k for k in truth if truth[k] is not None and pred.get(k) is None),
                                 "extra": sorted(k for k in pred if pred[k] is not None and truth.get(k) is None),
                                 "different": sorted(k for k in truth if truth[k] is not None and pred.get(k) is not None
                                                     and grade(truth[k], pred[k]) != "correct")}
    diffs = [v for v in seen.values() if v["missing"] or v["extra"] or v["different"]]
    return {"n_openings": len(seen), "n_differ": len(diffs),
            "slot_counts": {k: dict(Counter(s for d in diffs for s in d[k])) for k in ("missing", "extra", "different")},
            "diffs": diffs}


def priority_table(rows: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        out[r["priority"]][r["grade"]] += 1
        out[r["priority"]]["n"] += 1
        out["all"][r["grade"]] += 1
        out["all"]["n"] += 1
    return {k: dict(v) for k, v in out.items()}


def rf_yes_missed(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["priority"] == "redflag" and r["truth"] is True and r["pred"] is not True]


def confirm_estimate(rows: list[dict]) -> dict[str, Any]:
    """D-50 估算：紅旗題抽錯（非 OK_GRADES）的輪，needs_confirm(題目, 抽到的值, 送進抽取器的文字) 是否會觸發複誦。
    只看句子與值（不含「寫入後即 Hard stop 不複誦」的狀態判斷）；只估算，不改重放。"""
    qb = question_by_id()
    wrong = [r for r in rows if r["priority"] == "redflag" and r["grade"] not in OK_GRADES]
    out = []
    for r in wrong:
        out.append({**{k: r[k] for k in ("case_id", "turn", "q", "truth", "pred", "grade", "text")},
                    "triggered": needs_confirm(qb[r["q"]], r["pred"], r["text"])})
    yes = [r for r in out if r["truth"] is True]
    uniq = {(r["q"], r["text"]): r["triggered"] for r in out}
    uniq_yes = {(r["q"], r["text"]): r["triggered"] for r in yes}
    return {"wrong_turns": len(out), "triggered_turns": sum(r["triggered"] for r in out),
            "wrong_sentences": len(uniq), "triggered_sentences": sum(uniq.values()),
            "yes_missed_turns": len(yes), "yes_missed_triggered_turns": sum(r["triggered"] for r in yes),
            "yes_missed_sentences": len(uniq_yes), "yes_missed_triggered_sentences": sum(uniq_yes.values()),
            "rows": out}


def pctl(xs: list[float], p: float) -> float | None:
    """最近秩百分位（p ∈ (0, 100]）。"""
    if not xs:
        return None
    s = sorted(xs)
    return s[max(0, min(len(s) - 1, math.ceil(len(s) * p / 100) - 1))]


def latency_stats(recs: list[dict]) -> dict[str, Any]:
    def st(xs: list[float]) -> dict[str, Any]:
        return {"n": len(xs), "median_s": median(xs) if xs else None, "p95_s": pctl(xs, 95), "max_s": max(xs, default=None)}
    ok = [r for r in recs if r["latency_s"] is not None and r["ok"]]
    return {"all": st([r["latency_s"] for r in ok]), "opening": st([r["latency_s"] for r in ok if r["q"] is None]),
            "turn": st([r["latency_s"] for r in ok if r["q"] is not None])}


def abstain_diag(transcripts: list[dict], results: list, fn: ExtractFn, texts: dict[Key, str]) -> list[dict]:
    """該判 0–4 卻判 9 的 case：gate 缺哪些 slot；dropped = 結構化開場白已知、但這個抽取器的開場白沒抽到的
    （真實 runner 會補問，重放不補問 → 這類 9 部分是重放近似造成）。"""
    cases = {c.id: c for c in all_cases()}
    by_id = {t["case_id"]: t for t in transcripts}
    out = []
    for r in results:
        if r.truth_tier is None or r.truth_tier == 9 or r.final.tier != 9:
            continue
        t = by_id[r.case_id]
        truth_open = {k: v for k, v in extract(t["opening_zh"]).items() if v is not None and k not in cases[r.case_id].reset_slots}
        ext_open = fn(texts.get((r.case_id, 0), t["opening_zh"]), None)
        out.append({"case_id": r.case_id, "truth": r.truth_tier, "missing": list(r.final.missing),
                    "dropped": [k for k in r.final.missing if k in truth_open and ext_open.get(k) is None]})
    return out


def hs_trigger_diag(transcripts: list[dict], results: list, fn: ExtractFn, texts: dict[Key, str]) -> list[dict]:
    """假 Hard stop 與 premature：照重放的寫入方式逐句重算，找出第一次觸發 Hard stop 的那句與寫入的值
    （開場白觸發 → 列出與結構化開場白不同的欄位；回答觸發 → 被問那題的正確值與抽到的值）。"""
    cases = {c.id: c for c in all_cases()}
    by_id = {t["case_id"]: t for t in transcripts}
    qb = question_by_id()
    engine = RulesEngine()
    out = []
    for r in results:
        kind = "premature" if r.stop_reason == "premature_hard_stop" else (
            "false_alarm" if r.final.hard_stop and not r.truth_hard_stop else None)
        if kind is None:
            continue
        t = by_id[r.case_id]
        found = fn(texts.get((r.case_id, 0), t["opening_zh"]), None)
        ext = SlotState(found)
        for k in cases[r.case_id].reset_slots:
            ext.set(k, None, source="reset_for_variant")
        d = engine.decide(ext)
        row: dict[str, Any] = {"case_id": r.case_id, "kind": kind, "truth_tier": r.truth_tier}
        if d.hard_stop:
            truth = extract(t["opening_zh"])
            row.update(turn=0, rf=d.rf_hits, text=texts.get((r.case_id, 0), t["opening_zh"]),
                       wrote={k: v for k, v in found.items() if k not in cases[r.case_id].reset_slots and truth.get(k) != v},
                       truth={k: truth.get(k) for k in found if k not in cases[r.case_id].reset_slots and truth.get(k) != found[k]})
        else:
            for i, x in enumerate(t["turns"], 1):
                q = qb[x["q"]]
                text = texts.get((r.case_id, i), x["utterance_zh"])
                got = fn(text, q)
                ext.update(got, source=f"turn{i}", skip_none=True)
                d = engine.decide(ext)
                if d.hard_stop:
                    row.update(turn=i, rf=d.rf_hits, text=text, q=q.id, wrote=got, truth={q.slot_id: x["value"]})
                    break
        out.append(row)
    return out


def run_cell(transcripts: list[dict], fn: ExtractFn, texts: dict[Key, str], *, asked_only: bool = False) -> dict[str, Any]:
    results, slot_rows, premature = replay(transcripts, fn, asked_only=asked_only, texts=texts)
    m = compute(results)
    rows = full_rows(transcripts, fn, texts)
    return {"metrics": m.to_dict(), "_m": m, "premature": premature,
            "replay_slot_grades": dict(Counter(r["grade"] for r in slot_rows)), "replay_turns": len(slot_rows),
            "slot_by_priority": priority_table(rows), "rf_yes_missed": rf_yes_missed(rows),
            "opening": opening_diffs(transcripts, fn, texts), "abstain_diag": abstain_diag(transcripts, results, fn, texts),
            "hs_trigger": hs_trigger_diag(transcripts, results, fn, texts),
            "finals": {r.case_id: {"truth": r.truth_tier, "truth_hs": r.truth_hard_stop, "tier": r.final.tier,
                                   "hs": r.final.hard_stop, "stop": r.stop_reason} for r in results},
            "rows": rows}


# ---------------------------------------------------------------- 抽取器與快取
def _cache_path(cache_dir: Path, name: str) -> Path:
    return cache_dir / f"e2e_llm_cache_{name}.json"


def load_cache(ex: LLMExtractor, path: Path, meta: dict[str, Any]) -> list[dict]:
    """成功的呼叫放回快取；失敗的不沿用（重跑時再試），但留在檔案裡、費用照計。回傳失敗紀錄。"""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("meta") != meta:
        raise SystemExit(f"{path}：快取設定與本次不同（{data.get('meta')} vs {meta}），請換 --cache-dir")
    for r in data["records"]:
        if r["ok"]:
            ex.cache[(r["q"], r["text"])] = r
    ex.spent = sum(r["cost"] for r in data["records"])
    return [r for r in data["records"] if not r["ok"]]


def save_cache(ex: LLMExtractor, path: Path, meta: dict[str, Any], history: list[dict]) -> None:
    recs = history + list(ex.cache.values())
    path.write_text(json.dumps({"meta": meta, "records": recs}, ensure_ascii=False, indent=1), encoding="utf-8")


def prompt_sha() -> str:
    """提示全文（含欄位清單）的雜湊：提示改了，舊快取就不能沿用。"""
    from .llm_extract import opening_fields_zh
    cfg = load_prompts()
    blob = "\n".join([cfg["slot_system_zh"], cfg["slot_user_zh"], cfg["opening_system_zh"], cfg["opening_user_zh"], opening_fields_zh()])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def make_llm(name: str, args: argparse.Namespace) -> tuple[LLMExtractor, dict[str, Any], int]:
    cfg = load_prompts()
    versions = {"slot_prompts": cfg["slot_prompts_version"], "opening_prompts": cfg["opening_prompts_version"],
                "prompt_sha": prompt_sha()}
    if name == "gpt":
        if not os.environ.get(KEY_ENV):
            print(f"{KEY_ENV}: MISSING")
            sys.exit(2)
        client = OpenAIStructured(model=cfg["model"], effort=cfg["reasoning_effort"], api_key=os.environ[KEY_ENV])
        meta = {"extractor": cfg["model"], "effort": cfg["reasoning_effort"], **versions}
        return LLMExtractor(client, name=cfg["model"], price=PRICES[cfg["model"]], budget_usd=args.budget), meta, args.workers
    client = LMStudioStructured(model=cfg["local_model"], base_url=cfg["local_base_url"],
                                temperature=cfg["local_temperature"], max_tokens=cfg["local_max_tokens"])
    meta = {"extractor": cfg["local_model"], "temperature": cfg["local_temperature"], **versions}
    return LLMExtractor(client, name=cfg["local_model"]), meta, 1        # 本機一次一句：延遲才有意義


def prefetch(ex: LLMExtractor, todo: list[tuple[str, Question | None]], workers: int, path: Path,
             meta: dict[str, Any], history: list[dict], chunk: int = 100) -> None:
    for a in range(0, len(todo), chunk):
        ex.prefetch(todo[a:a + chunk], workers=workers)
        save_cache(ex, path, meta, history)
        done = len(ex.cache)
        print(f"  {ex.name}: {done} 筆完成，累計估算 US${ex.spent:.4f}", flush=True)


# ---------------------------------------------------------------- 報告
def _hs(m) -> str:
    return f"{len(m.hard_stop_miss)}/{m.hard_stop_truth}"


def render(rep: dict[str, Any]) -> str:
    cells, meta = rep["cells"], rep["meta"]
    L = [f"# 實驗 2：完整流程重放（口語 → 文字 → 抽取器 → 規則）— {meta['date']}", "",
         "> **限制（先讀）**", ">",
         "> 1. **重放不補問**：對話序列照逐字稿固定，抽取狀態不足時真實 runner 會再問（最多 11 題），重放不會 → "
         "Tier 9（轉護理師）可能偏多、under 可能偏少；抽取狀態一觸發 Hard stop 即停，其後各輪不再重放。",
         "> 2. **合成語音**：phone 條件是 macOS `say` 合成標準國語、模擬電話線路後給本機 Whisper 轉寫（D-49），"
         "沒有台語、高齡口音、喘氣停頓與環境噪音，是 **樂觀上限**，不能代表真實來電。",
         "> 3. **Opus 病人逐字稿**：病人回答由 LLM（Opus）依情境事實生成，句子比真實病人完整、少答非所問；"
         "正確答案＝情境事實（單一裁定者），本實驗是一致性檢查，不是準確度。",
         "> 4. **雲端模型不可用於真實資料**：gpt-6.1-sol 只作「抽取能力上限」參考，真實病人資料不得送外部 API（D-10）；"
         "院內可部署的候選是本機模型。全部資料為合成資料。", "",
         "## 0. 設定", "",
         f"- rules_version {meta['rules_version']}；逐字稿 `{meta['transcripts']}`（{meta['n_cases']} cases、{meta['n_utterances']} 句：開場白 "
         f"{meta['n_cases']}＋回答 {meta['n_utterances'] - meta['n_cases']}；不同句子 {meta['n_unique_texts']}）。"
         + ("" if not meta["limit"] else f"**只跑前 {meta['limit']} 個 case（估算用）。**"),
         f"- phone 文字：`{meta['stt_source']}` rows（condition = {STT_CONDITION}，`hyp_tw` 已轉繁體）；"
         f"對不到轉寫的句子 {meta['phone_unmatched']} 句（改用原文）；轉寫與原文逐字相同 {meta['phone_identical']} 句。",
         f"- 抽取提示：有題目的輪原封沿用 `data/openai_prompts.yaml` slot 提示 {meta['slot_prompts_version']}（D-40 起的版本；D-39 用 0.1，規則 3b「說不上來」為 D-40 新增）；"
         f"開場白為新增 `data/extractor_prompts.yaml` {meta['opening_prompts_version']}（一次輸出全部欄位，沒提到填 null；"
         f"排除 consult_screen_positive）。兩個 LLM 用同一份提示與 schema。",
         f"- gpt：`{meta['gpt_model']}` effort {meta['gpt_effort']}，Responses API strict json_schema、store false，{meta['gpt_workers']} 路並行。"
         f"gemma：`{meta['local_model']}`（LM Studio，`/v1/chat/completions` response_format json_schema strict，"
         f"temperature {meta['local_temperature']}），一次一句。兩者輸出都再以 schema 驗證，不合法＝抽取失敗（該句不寫入）。",
         "- 同一（題目, 句子）只呼叫一次（快取）；寫入方式＝該句抽到的所有 slot（§3.4）。LLM 有題目的輪只回被問那題，"
         "開場白可回多欄。結構化答案＝同一份逐字稿、同一版規則、每輪寫入結構化值（同 M2 runner；只寫被問那題）。",
         "- Hard-stop miss 含 premature（抽取狀態在真紅旗那句之前就觸發 Hard stop，不算命中）。", "",
         "## 1. 6 格結果（對照：結構化答案）", "",
         "| 抽取器 | 文字 | Hard-stop miss（含 premature） | premature | 假 Hard stop | latency 最大 | under | over | exact | abstention FP（TP） | 抽取失敗 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    order = [k for k in ["structured", "keyword/ref", "keyword/phone", "gpt/ref", "gpt/phone", "gemma/ref", "gemma/phone"] if k in cells]
    for k in order:
        c, m = cells[k], cells[k]["_m"]
        ext, cond = (k, "—") if k == "structured" else k.split("/")
        L.append(f"| {rep['labels'].get(ext, ext)} | {COND_LABEL.get(cond, cond)} | **{_hs(m)}** | {len(c['premature'])} | "
                 f"{len(m.hard_stop_false_alarm)} | {m.hard_stop_latency_max} | {len(m.under_triage)} | {len(m.over_triage)} | "
                 f"{_fmt_pct(m.exact_rate)} | {len(m.abstain_fp)}（{m.abstain_tp}） | {c.get('failures', 0)} |")
    L += ["", "under／over 不含 Tier 9（9 另計 abstention）；exact 分母為可評分 case。", "",
          "### phone 比 ref 掉多少（phone − ref）", "",
          "| 抽取器 | Hard-stop miss | 假 Hard stop | under | over | exact | abstention FP | 被問 slot 正確 | 紅旗「有」漏抽 |", "|---|---|---|---|---|---|---|---|---|"]
    for ext in ["keyword", "gpt", "gemma"]:
        if f"{ext}/ref" not in cells or f"{ext}/phone" not in cells:
            continue
        a, b = cells[f"{ext}/ref"], cells[f"{ext}/phone"]
        ma, mb = a["_m"], b["_m"]
        ca, cb = a["slot_by_priority"]["all"].get("correct", 0), b["slot_by_priority"]["all"].get("correct", 0)
        L.append(f"| {rep['labels'][ext]} | {len(mb.hard_stop_miss) - len(ma.hard_stop_miss):+d} | "
                 f"{len(mb.hard_stop_false_alarm) - len(ma.hard_stop_false_alarm):+d} | {len(mb.under_triage) - len(ma.under_triage):+d} | "
                 f"{len(mb.over_triage) - len(ma.over_triage):+d} | {100 * (mb.exact_rate - ma.exact_rate):+.1f} pt | "
                 f"{len(mb.abstain_fp) - len(ma.abstain_fp):+d} | {cb - ca:+d} | {len(b['rf_yes_missed']) - len(a['rf_yes_missed']):+d} |")
    L += ["", "### Hard-stop miss 明細", ""]
    for k in order:
        m = cells[k]["_m"]
        L.append(f"- {k}：{', '.join(m.hard_stop_miss) or '（無）'}" + (f"；premature {cells[k]['premature']}" if cells[k]["premature"] else "")
                 + (f"；假 Hard stop {', '.join(m.hard_stop_false_alarm)}" if m.hard_stop_false_alarm else ""))
    L += ["", "### 假 Hard stop 與 premature 的觸發點（第一次觸發的那句與寫入的值；「正確」＝結構化值）", ""]
    for k in order:
        hs = cells[k]["hs_trigger"]
        if not hs:
            continue
        L.append(f"- **{k}**（{len(hs)}）")
        for h in hs:
            where = "開場白" if h.get("turn") == 0 else f"第 {h.get('turn')} 句 {h.get('q', '')}"
            L.append(f"  - {h['case_id']}（{'premature' if h['kind'] == 'premature' else '假警報'}，truth T{h['truth_tier']}）{where} "
                     f"{'／'.join(h.get('rf', []))}：寫入 {h.get('wrote')}，正確 {h.get('truth')}「{h.get('text', '')}」")
    L += ["", "### ref → phone 結果改變的 case", ""]
    for ext in ["keyword", "gpt", "gemma"]:
        if f"{ext}/ref" not in cells or f"{ext}/phone" not in cells:
            continue
        fa, fb = cells[f"{ext}/ref"]["finals"], cells[f"{ext}/phone"]["finals"]
        ch = [f"{cid}（truth {fa[cid]['truth']}{'＋HS' if fa[cid]['truth_hs'] else ''}：{_fin(fa[cid])} → {_fin(fb[cid])}）"
              for cid in fa if (fa[cid]["tier"], fa[cid]["hs"]) != (fb[cid]["tier"], fb[cid]["hs"])]
        L.append(f"- {rep['labels'][ext]}（{len(ch)}）：" + ("；".join(ch) or "（無）"))
    L += ["", "## 2. 被問那題的抽取（每一輪都算，不因 Hard stop 截斷；正確答案＝逐字稿結構化值）", "",
          "| 抽取器 | 文字 | 全部 正確 | 紅旗題 | 關鍵題（decisive） | 補充題（refine） | 漏抽 | 抽錯 | 多抽 | 互換／說不上來 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k in order:
        if k == "structured":
            continue
        ext, cond = k.split("/")
        p = cells[k]["slot_by_priority"]

        def acc(g: dict[str, int]) -> str:
            return f"{g.get('correct', 0)}/{g.get('n', 0)}（{_fmt_pct(g.get('correct', 0) / g['n']) if g.get('n') else '—'}）"
        a = p["all"]
        L.append(f"| {rep['labels'][ext]} | {COND_LABEL[cond]} | {acc(a)} | " + " | ".join(acc(p.get(x, {})) for x in PRIORITIES)
                 + f" | {a.get('missed', 0)} | {a.get('wrong', 0)} | {a.get('invented', 0)} | {a.get('unknown_equiv', 0) + a.get('speechless', 0)} |")
    L += ["", "### 紅旗題病人答「有」卻沒抽成「有」", ""]
    for k in order:
        if k == "structured":
            continue
        miss = cells[k]["rf_yes_missed"]
        n_yes = sum(1 for r in cells[k]["rows"] if r["priority"] == "redflag" and r["truth"] is True)
        L.append(f"- **{k}**：{len(miss)}/{n_yes}" + ("" if not miss else "：" + "；".join(
            f"{r['case_id']}#t{r['turn']} {r['q']}→{r['pred']}「{r['text']}」" for r in miss)))
    L += ["", "### 開場白抽取 vs 結構化事實（依不同開場白計）", ""]
    for k in order:
        if k == "structured":
            continue
        o = cells[k]["opening"]
        sc = o["slot_counts"]
        L.append(f"- {k}：{o['n_differ']}/{o['n_openings']} 句有差異；漏 {sum(sc['missing'].values())}（{_top(sc['missing'])}）、"
                 f"多 {sum(sc['extra'].values())}（{_top(sc['extra'])}）、值不同 {sum(sc['different'].values())}（{_top(sc['different'])}）")
    L += ["", "（開場白的結構化事實＝關鍵詞抽取逐字稿，因此 keyword/ref 必為 0；LLM 的「多」不一定是錯，可能是關鍵詞漏掉的真資訊。）", "",
          "### Abstention FP（該判 0–4 卻判 9）：gate 缺的 slot", "",
          "＊＝結構化開場白已知、這個抽取器的開場白沒抽到（真實 runner 會補問這題，重放不補問 → 這類 9 部分來自重放近似）。", ""]
    for k in order:
        ad = cells[k]["abstain_diag"]
        n_drop = sum(1 for a in ad if a["dropped"])
        L.append(f"- {k}（{len(ad)}，含＊ {n_drop}）：" + ("；".join(
            f"{a['case_id']}（T{a['truth']}）" + "、".join(x + ("＊" if x in a["dropped"] else "") for x in a["missing"]) for a in ad) or "（無）"))
    L += ["",
          "## 3. 延遲與失敗", "",
          "| 抽取器 | 呼叫數 | 失敗 | 全部 中位數／p95（秒） | 開場白 中位數／p95 | 回答 中位數／p95 | 並行 |", "|---|---|---|---|---|---|---|"]
    for ext, s in rep["llm"].items():
        lat = s["latency"]
        L.append(f"| {rep['labels'][ext]} | {s['n_calls']} | {s['n_failed']}（先前失敗後重試 {s['prior_failed_attempts']}） | {_sec(lat['all'])} | {_sec(lat['opening'])} | "
                 f"{_sec(lat['turn'])} | {s['workers']} |")
    for ext, s in rep["llm"].items():
        if s["errors"] or s["prior_failed_errors"]:
            L.append(f"- {rep['labels'][ext]} 最終失敗類型：{s['errors'] or '（無）'}；先前失敗（已重試）：{s['prior_failed_errors'] or '（無）'}")
    L += ["", "gpt 的延遲是 8 路並行下量到的單次呼叫牆鐘時間（含網路與重試）；gemma 為本機一次一句。", "",
          "## 4. 費用（gpt-6.1-sol；依 `sim/openai_eval.py` PRICES 估算，以帳單為準）", ""]
    if "gpt" in rep["llm"]:
        g = rep["llm"]["gpt"]
        L.append(f"- 本報告用到的呼叫合計 US${g['cost_used']:.4f}（{g['n_calls']} 次，平均 US${g['cost_used'] / max(g['n_calls'], 1):.5f}）；"
                 f"快取檔累計實際花費（含估算用試跑、失敗呼叫）US${g['cost_total']:.4f}；上限 US${meta['budget']:.2f}。")
    else:
        L.append("- 本次未跑 gpt。")
    L += ["", "## 5. 若有 D-50 複誦確認：phone 條件紅旗題抽錯的句子會不會觸發複誦（估算）", "",
          "對 phone 條件每一輪紅旗題抽錯（漏抽、抽錯、多抽）的句子，以 `confirm.needs_confirm(題目, 抽到的值, hyp_tw)` 判斷是否觸發複誦"
          "（句首判定 `leading_yes_no`）。只估算觸發，不模擬複誦回答，也不含「寫入後即 Hard stop 不複誦」；重放邏輯不變。範圍只含紅旗題，未含 D-50 範圍內的關鍵題（`stt_critical_questions`：Q-CHARACTER-01、Q-REST-02）。"
          "值為「有」（最嚴重一級）的多抽依設計不複誦（安全方向）。", "",
          "| 抽取器 | 抽錯 輪（句） | 會觸發複誦 輪（句） | 其中答「有」被漏抽 輪（句） | 「有」被漏抽且會觸發 輪（句） |", "|---|---|---|---|---|"]
    for ext, ce in rep["confirm_estimate"].items():
        L.append(f"| {rep['labels'][ext]} | {ce['wrong_turns']}（{ce['wrong_sentences']}） | {ce['triggered_turns']}（{ce['triggered_sentences']}） | "
                 f"{ce['yes_missed_turns']}（{ce['yes_missed_sentences']}） | {ce['yes_missed_triggered_turns']}（{ce['yes_missed_triggered_sentences']}） |")
    for ext, ce in rep["confirm_estimate"].items():
        nt = [r for r in ce["rows"] if not r["triggered"]]
        if nt:
            L.append(f"- {rep['labels'][ext]} 不會觸發的：" + "；".join(
                f"{r['case_id']}#t{r['turn']} {r['q']} 正確 {r['truth']}／抽出 {r['pred']}「{r['text']}」" for r in nt))
    L += ["", "## 6. 重現", "", "```",
          "# 費用估算（前 3 個 case）",
          "zsh -ic 'cd ~/Documents/GitHub/acs_triage && uv run python -m sim.e2e_llm --limit 3 --extractors keyword,gpt --cache-dir <scratch> --out <scratch>'",
          "# 全量（LM Studio 需先 lms load gemma-4-26b-a4b-it-mlx）",
          "zsh -ic 'cd ~/Documents/GitHub/acs_triage && uv run python -m sim.e2e_llm --cache-dir <scratch>'", "```",
          "關鍵詞抽取器的既有重放：`python -m sim.extractor_e2e --extractor keyword [--asked-only]`（extract_fn 介面擴充後輸出不變）。", ""]
    return "\n".join(L)


def _fin(f: dict) -> str:
    return "HS" if f["hs"] else f"T{f['tier']}"


def _top(c: dict[str, int], n: int = 4) -> str:
    return "、".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:n]) or "—"


def _sec(s: dict) -> str:
    return "—" if not s["n"] else f"{s['median_s']:.2f}／{s['p95_s']:.2f}"


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractors", default="keyword,gpt,gemma")
    ap.add_argument("--conditions", default="ref,phone")
    ap.add_argument("--transcripts", default=str(DEFAULT_TRANSCRIPTS))
    ap.add_argument("--stt", default=str(DEFAULT_STT))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--budget", type=float, default=12.0, help="gpt 累計估算費用上限（USD），到了就不再呼叫")
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args(argv)
    exts = [e for e in args.extractors.split(",") if e]
    conds = [c for c in args.conditions.split(",") if c]
    transcripts = json.loads(Path(args.transcripts).read_text(encoding="utf-8"))
    if args.limit:
        transcripts = transcripts[: args.limit]
    stt_rows = json.loads(Path(args.stt).read_text(encoding="utf-8"))["rows"]
    ptexts, unmatched = phone_texts(transcripts, stt_rows)
    texts = {"ref": {}, "phone": ptexts}
    all_utts = [(t["case_id"], i, s) for t in transcripts for i, s, _ in utterances(t)]
    cfg = load_prompts()
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    labels = {"keyword": "keyword", "gpt": cfg["model"], "gemma": cfg["local_model"], "structured": "結構化答案"}

    cells: dict[str, Any] = {"structured": run_cell(transcripts, structured_fn(transcripts), {}, asked_only=True)}
    llm: dict[str, Any] = {}
    fns: dict[str, ExtractFn] = {"keyword": keyword}
    for e in exts:
        if e == "keyword":
            continue
        ex, meta, workers = make_llm(e, args)
        path = _cache_path(cache_dir, e)
        history = load_cache(ex, path, meta)
        todo = [it for c in conds for it in items(transcripts, texts[c])]
        print(f"{labels[e]}：{len(dict.fromkeys(ex.key(t, q) for t, q in todo))} 個不同（題目, 句子）", flush=True)
        prefetch(ex, todo, workers, path, meta, history)
        used = {ex.key(t, q) for t, q in todo}
        recs = [ex.cache[k] for k in used]
        fails = [r for r in recs if not r["ok"]]
        llm[e] = {"n_calls": len(recs), "n_failed": len(fails), "errors": dict(Counter(r["error"] for r in fails)),
                  "latency": latency_stats(recs), "workers": workers, "models": sorted({r["model"] for r in recs if r["model"]}),
                  "cost_used": sum(r["cost"] for r in recs), "cost_total": ex.spent, "cache": str(path),
                  "prior_failed_attempts": len(history),
                  "prior_failed_errors": dict(Counter(r["error"] for r in history))}
        fns[e] = ex
    for e in exts:
        for c in conds:
            cell = run_cell(transcripts, fns[e], texts[c])
            if e != "keyword":
                ex = fns[e]
                cell["failures"] = sum(1 for t, q in items(transcripts, texts[c]) if not ex.cache[ex.key(t, q)]["ok"])
            cells[f"{e}/{c}"] = cell
    confirm = {e: confirm_estimate(cells[f"{e}/phone"]["rows"]) for e in exts if f"{e}/phone" in cells}
    rep = {"meta": {"date": date.today().isoformat(), "rules_version": rules_version(), "transcripts": Path(args.transcripts).name,
                    "stt_source": Path(args.stt).name, "limit": args.limit, "n_cases": len(transcripts), "n_utterances": len(all_utts),
                    "n_unique_texts": len({s for _, _, s in all_utts}),
                    "phone_unmatched": len(unmatched), "phone_unmatched_keys": unmatched,
                    "phone_identical": sum(1 for cid, i, s in all_utts if ptexts.get((cid, i)) == s),
                    "slot_prompts_version": cfg["slot_prompts_version"], "opening_prompts_version": cfg["opening_prompts_version"],
                    "gpt_model": cfg["model"], "gpt_effort": cfg["reasoning_effort"], "gpt_workers": args.workers,
                    "local_model": cfg["local_model"], "local_temperature": cfg["local_temperature"], "budget": args.budget},
           "labels": labels, "cells": cells, "llm": llm, "confirm_estimate": confirm}
    md = render(rep)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"e2e_llm_extractors_{date.today().isoformat()}{'_limit' + str(args.limit) if args.limit else ''}"
    if (outdir / f"{stem}.md").exists():          # 同日重跑：加 _r2、_r3…，不覆蓋舊報告
        stem = next(f"{stem}_r{i}" for i in range(2, 1000) if not (outdir / f"{stem}_r{i}.md").exists())
    (outdir / f"{stem}.md").write_text(md, encoding="utf-8")
    js = {**rep, "cells": {k: {kk: vv for kk, vv in v.items() if kk != "_m"} for k, v in cells.items()}}
    (outdir / f"{stem}.json").write_text(json.dumps(js, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    summary = {k: {"hs_miss": len(v["_m"].hard_stop_miss), "false_hs": len(v["_m"].hard_stop_false_alarm),
                   "under": len(v["_m"].under_triage), "over": len(v["_m"].over_triage), "exact": round(v["_m"].exact_rate, 3),
                   "abstain_fp": len(v["_m"].abstain_fp), "rf_yes_missed": len(v["rf_yes_missed"])} for k, v in cells.items()}
    print(json.dumps({"cells": summary, "cost": {e: round(s["cost_total"], 4) for e, s in llm.items()}}, ensure_ascii=False))
    print(f"→ {outdir / (stem + '.md')}")


if __name__ == "__main__":
    main()
