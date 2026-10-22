"""STT 評估流程 B 段：建 utterance 清單（build）與計分出報告（score）（D-48）。

python -m sim.stt_eval build  [--transcripts reports/eval_2026-10-20_llm_opus-5-5_medium_transcripts.json]
                              [--out reports/stt_utterances_2026-10-22.json]
python -m sim.stt_eval score  --asr <sim/stt_synth_asr.py 的結果 JSON>
                              [--utterances reports/stt_utterances_2026-10-22.json] [--out-dir reports]

流程 A 段（`sim/stt_synth_asr.py`，在 ASR 環境）：utterance 清單 → 合成電話音質 → Whisper → 原始結果 JSON。
本檔在專案 .venv 執行（有 acs_triage，沒有 mlx-whisper／opencc），不碰音檔與模型。
換模型（Breeze-ASR-25）或換真實錄音時，只要 A 段換 --model／--recordings-dir，本檔照用。

量測三件事：
1. 字錯率（正規化後字元層 Levenshtein；正規化 = NFKC、繁轉簡、去標點空白，由 A 段完成）。
2. 極性翻轉：回答的「否定判定」ref 與 hyp 不同。
3. 信心值能否抓到錯誤（錯誤 = CER > 0.1 或極性翻轉）與 0.9／0.75 門檻的實際效果。
合成語音是樂觀上限，不能代表真實病人（見報告開頭）。純函式與計分邏輯在上半部，有單元測試（tests/test_stt_eval.py）。
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterable, Sequence

from acs_triage.extract import extract
from acs_triage.loaders import REPO_ROOT, load_clinical_rules, question_by_id

DEFAULT_TRANSCRIPTS = REPO_ROOT / "reports" / "eval_2026-10-20_llm_opus-5-5_medium_transcripts.json"
DEFAULT_UTTERANCES = REPO_ROOT / "reports" / "stt_utterances_2026-10-22.json"
DEFAULT_STEM = "stt_whisper_2026-10-22"

LOOP_COMPRESSION_RATIO = 2.4                               # Whisper 預設的壓縮比門檻：高於此視為重複幻覺
CER_ERROR_THRESHOLD = 0.1                                  # 「CER > 0.1」視為轉寫錯誤
THRESHOLDS = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
MARK_THRESHOLDS = (0.75, 0.9)                              # 系統現行門檻（D-43）
FEATURES = ("mean_avg_logprob", "min_word_prob", "mean_word_prob")
MISSING_LOGPROB = -10.0                                    # 完全沒有 segment（空轉寫）時的 avg_logprob 代用值
CONDITION_ORDER = ["clean", "phone", "phone_prompt", "rec", "rec_prompt"]
FLIP_KINDS = ["inversion", "lead_lost", "lead_gained", "inner"]
FLIP_KIND_LABEL = {"inversion": "明確互換", "lead_lost": "句首詞消失", "lead_gained": "句首多出詞", "inner": "句中否定詞增減"}
QTYPE_ORDER = ["redflag", "critical", "other", "opening"]
QTYPE_LABEL = {"redflag": "紅旗題", "critical": "關鍵題", "other": "其他", "opening": "開場白"}
_QTYPE_RANK = {q: i for i, q in enumerate(QTYPE_ORDER)}


# ======================================================================== 字錯率
def strip_punct(s: str) -> str:
    """去掉標點、符號與空白（保留漢字、字母、數字）。"""
    return re.sub(r"[\W_]+", "", s)


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def edit_stats(ref: str, hyp: str) -> tuple[int, int]:
    """回傳 (編輯距離, ref 長度)；ref、hyp 須已正規化。"""
    return levenshtein(ref, hyp), len(ref)


def cer(ref: str, hyp: str) -> float:
    """字元錯誤率 = 編輯距離 / len(ref)。ref 為空：hyp 也空 → 0.0，否則 1.0。"""
    edits, n = edit_stats(ref, hyp)
    if n == 0:
        return 0.0 if edits == 0 else 1.0
    return edits / n


# ======================================================================== 極性（否定判定）
# 以簡體為標準字形；輸入（繁／簡）與詞表都先過同一張對照表，所以兩種字形結果一致。
_T2S = str.maketrans("沒麼會還對確說記適規則動過關係來樣誒", "没么会还对确说记适规则动过关系来样诶")   # 詞表用到的字


def _canon(s: str) -> str:
    return s.translate(_T2S)


NEG_TOKENS = ["沒有", "沒", "不會", "不是", "不", "沒什麼", "還沒"]            # 任務定義的否定詞集合
POS_STARTS = ["有", "會", "是", "還在", "對"]                                   # 肯定回答開頭
# 含「不／沒」但不是在否定症狀的片語（沿用 extraction_patterns.yaml 的 non_negation_phrases，再補不確定語氣與連接詞）
NON_NEGATION = ["不舒服", "不太舒服", "不適", "說不上來", "不知道", "不確定", "不太確定", "不清楚", "不太清楚",
                "記不清楚", "記不太清楚", "不太對", "不一樣", "不規則", "不正常", "不動", "不過", "不管", "不然", "沒關係"]
FILLER_CHARS = "嗯呃喔哦啊欸唔哈哎唉誒"

_NEG_SORTED = sorted({_canon(t) for t in NEG_TOKENS}, key=len, reverse=True)
_NEG_RE = re.compile("|".join(map(re.escape, _NEG_SORTED)))
_POS_SORTED = tuple(sorted({_canon(t) for t in POS_STARTS}, key=len, reverse=True))
_MASKS = sorted({_canon(t) for t in NON_NEGATION}, key=len, reverse=True)


_LEAD_RE = re.compile(rf"^[\W_{FILLER_CHARS}]+")


def _prepare(text: str) -> str:
    """標準字形、去句首標點與語助詞、遮罩非否定片語。"""
    s = _LEAD_RE.sub("", _canon(text))
    for m in _MASKS:
        s = s.replace(m, "□" * len(m))
    return s


def _lead(s: str) -> str | None:
    if _NEG_RE.match(s):
        return "neg"
    return "pos" if s.startswith(_POS_SORTED) else None


def lead_polarity(text: str) -> str | None:
    """答案是否以否定詞（'neg'）或肯定詞（'pos'）開頭；都不是 → None。"""
    return _lead(_prepare(text))


def polarity(text: str) -> str:
    """回答的極性：'neg'（否定）／'pos'（肯定開頭）／'unk'（無法判定）。

    去掉句首標點與語助詞後：以否定詞開頭 → neg；以肯定詞開頭 → pos（其後的否定詞不翻轉它，
    如「有，不過沒有冒汗」）；否則整句出現否定詞 → neg；都沒有 → unk。
    不依賴標點切句：Whisper 輸出有時完全沒有標點（實測），按子句判斷會因此誤報翻轉。
    """
    s = _prepare(text)
    return _lead(s) or ("neg" if _NEG_RE.search(s) else "unk")


def is_negated(text: str) -> bool:
    return polarity(text) == "neg"


def polarity_flip(ref: str, hyp: str) -> bool:
    """ref 與 hyp 的否定判定不同 = 極性翻轉。"""
    return is_negated(ref) != is_negated(hyp)


def flip_kind(lead_ref: str | None, lead_hyp: str | None) -> str:
    """翻轉的性質（輸入為 lead_polarity 的結果）：
    inversion = 明確互換（有↔沒有）；lead_lost = 句首肯定／否定詞消失、剩下的句子恰好含／不含否定詞；
    lead_gained = 句首多出肯定／否定詞（如「這個」被聽成「有個」）；inner = 句首都不是，句中否定詞增減。"""
    if lead_ref and lead_hyp:
        return "inversion"
    if lead_ref:
        return "lead_lost"
    return "lead_gained" if lead_hyp else "inner"


def flip_direction(ref: str, hyp: str) -> str | None:
    """neg_gained：非否定被聽成否定（「有」→「沒有」，紅旗題會降級）；neg_lost：否定被聽成非否定。"""
    r, h = is_negated(ref), is_negated(hyp)
    if r == h:
        return None
    return "neg_gained" if h else "neg_lost"


# ======================================================================== AUC 與門檻
def auc(scores: Sequence[float], labels: Sequence[bool]) -> float | None:
    """Mann–Whitney：隨機一個 label=True 的分數高於隨機一個 label=False 的機率（同分算 0.5）。單一類別 → None。"""
    n_pos = sum(1 for l in labels if l)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1                      # 名次從 1 起算，同分取平均
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    rank_sum = sum(r for r, l in zip(ranks, labels) if l)
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def low_confidence_auc(values: Sequence[float], is_error: Sequence[bool]) -> float | None:
    """信心值越低越可能錯：把信心取負號當分數。> 0.5 表示信心值有鑑別力。"""
    return auc([-v for v in values], is_error)


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def threshold_stats(values: Sequence[float], thresholds: Sequence[float], is_error: Sequence[bool],
                    is_flip: Sequence[bool]) -> dict[str, Any]:
    """thresholds 可以是單一數字（長度 n 的序列則逐句不同）。信心 < 門檻 → 重問。"""
    n = len(values)
    flagged = [v < t for v, t in zip(values, thresholds)]
    n_re = sum(flagged)
    n_err = sum(is_error)
    n_flip = sum(is_flip)
    caught_err = sum(1 for f, e in zip(flagged, is_error) if f and e)
    caught_flip = sum(1 for f, x in zip(flagged, is_flip) if f and x)
    return {"n": n, "n_reask": n_re, "reask_rate": _ratio(n_re, n),
            "n_error": n_err, "n_error_caught": caught_err, "error_caught": _ratio(caught_err, n_err),
            "n_flip": n_flip, "n_flip_caught": caught_flip, "flip_caught": _ratio(caught_flip, n_flip),
            "precision": _ratio(caught_err, n_re)}


def threshold_table(values: Sequence[float], is_error: Sequence[bool], is_flip: Sequence[bool],
                    thresholds: Iterable[float] = THRESHOLDS) -> list[dict[str, Any]]:
    out = []
    for t in thresholds:
        row = threshold_stats(values, [t] * len(values), is_error, is_flip)
        row["threshold"] = t
        out.append(row)
    return out


# ======================================================================== 信心特徵
def confidence_features(segments: list[dict], words: list[list]) -> dict[str, float]:
    """逐字機率只取有內容的字（純標點的 token 不是轉寫內容，其機率不代表聽錯）。"""
    probs = [float(p) for w, p in words if strip_punct(w)]
    lp = [s["avg_logprob"] for s in segments]
    return {"mean_avg_logprob": mean(lp) if lp else MISSING_LOGPROB,
            "min_word_prob": min(probs) if probs else 0.0,
            "mean_word_prob": mean(probs) if probs else 0.0}


# ======================================================================== build：utterance 清單
def critical_question_ids() -> set[str]:
    return set(load_clinical_rules()["thresholds"].get("stt_critical_questions", []))


def qtype_of(is_opening: bool, redflag: bool, critical: bool) -> str:
    if redflag:
        return "redflag"
    if critical:
        return "critical"
    return "opening" if is_opening else "other"


def build_utterances(transcripts: list[dict], qb: dict, critical_ids: set[str]) -> list[dict[str, Any]]:
    """開場白與病人回答，依文字去重（第一次出現的順序編號 u0001…）；每句保留所有來源。

    qtype 取所有來源中最嚴重者：redflag > critical > other > opening。
    """
    by_text: dict[str, dict[str, Any]] = {}

    def add(text: str, src: dict[str, Any]) -> None:
        u = by_text.get(text)
        if u is None:
            u = by_text[text] = {"id": f"u{len(by_text) + 1:04d}", "text": text, "sources": []}
        u["sources"].append(src)

    for t in transcripts:
        add(t["opening_zh"], {"case_id": t["case_id"], "kind": "opening", "turn": 0, "q": None, "slot_id": None,
                              "redflag": False, "critical": False, "value": None})
        for i, turn in enumerate(t["turns"], 1):
            q = qb[turn["q"]]
            add(turn["utterance_zh"], {"case_id": t["case_id"], "kind": "answer", "turn": i, "q": q.id,
                                       "slot_id": q.slot_id, "redflag": q.priority == "redflag",
                                       "critical": q.id in critical_ids, "value": turn["value"]})
    out = list(by_text.values())
    for u in out:
        u["qtype"] = min((qtype_of(s["kind"] == "opening", s["redflag"], s["critical"]) for s in u["sources"]),
                         key=_QTYPE_RANK.__getitem__)
    return out


def cmd_build(args: argparse.Namespace) -> None:
    transcripts = json.loads(Path(args.transcripts).read_text(encoding="utf-8"))
    utts = build_utterances(transcripts, question_by_id(), critical_question_ids())
    out = Path(args.out)
    out.write_text(json.dumps(utts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_src = sum(len(u["sources"]) for u in utts)
    print(f"{len(utts)} 句（{n_src} 個來源；{Counter(u['qtype'] for u in utts)}）-> {out}")


# ======================================================================== score：逐筆列
def make_rows(asr: dict, utterances: list[dict]) -> list[dict[str, Any]]:
    by_id = {u["id"]: u for u in utterances}
    ref_ext: dict[str, dict] = {}
    rows = []
    for r in asr["results"]:
        u = by_id[r["id"]]
        if u["text"] != r["ref"]:
            raise ValueError(f"{r['id']}：utterance 清單與 ASR 結果的 ref 不一致（清單被改過？）")
        ref, hyp, hyp_tw = r["ref"], r["hyp"], r["hyp_tw"]
        hyp_p = hyp_tw                                       # 極性與抽取都看繁體化後的轉寫（STT adapter 應有的輸出）
        edits, ref_len = edit_stats(r["ref_norm"], r["hyp_norm"])
        c = cer(r["ref_norm"], r["hyp_norm"])
        ref_x = ref_ext.setdefault(r["id"], extract(ref))
        hyp_x, hyp_raw_x = extract(hyp_tw), extract(hyp)
        slot_ids = sorted({s["slot_id"] for s in u["sources"] if s["slot_id"]})
        feats = confidence_features(r["segments"], r["words"])
        flip = polarity_flip(ref, hyp_p)
        lead_r, lead_h = lead_polarity(ref), lead_polarity(hyp_p)
        rows.append({
            "id": r["id"], "condition": r["condition"], "voice": r["voice"], "qtype": u["qtype"],
            "q_ids": sorted({s["q"] for s in u["sources"] if s["q"]}), "slot_ids": slot_ids,
            "ref": ref, "hyp": hyp, "hyp_tw": hyp_tw, "ref_norm": r["ref_norm"], "hyp_norm": r["hyp_norm"],
            "edits": edits, "ref_len": ref_len, "cer": c,
            "pol_ref": polarity(ref), "pol_hyp": polarity(hyp_p), "lead_ref": lead_r, "lead_hyp": lead_h,
            "flip": flip, "flip_dir": flip_direction(ref, hyp_p), "flip_kind": flip_kind(lead_r, lead_h) if flip else None,
            "script_converted": hyp_tw != unicodedata.normalize("NFKC", hyp),
            "ref_extract_nonempty": bool(ref_x),
            "ext_diff": hyp_x != ref_x, "ext_diff_raw": hyp_raw_x != ref_x,
            "ext_diff_slots": sorted(k for k in set(ref_x) | set(hyp_x) if ref_x.get(k) != hyp_x.get(k)),
            "ext_asked_diff": any(ref_x.get(s) != hyp_x.get(s) for s in slot_ids),
            "max_compression_ratio": max((x["compression_ratio"] for x in r["segments"]), default=0.0),
            **feats,
            "error": c > CER_ERROR_THRESHOLD or flip,
            "elapsed_s": r["elapsed_s"],
        })
    return rows


# ======================================================================== score：彙總
def _conditions(rows: list[dict]) -> list[str]:
    present = {r["condition"] for r in rows}
    return [c for c in CONDITION_ORDER if c in present] + sorted(present - set(CONDITION_ORDER))


def _groups(rows: list[dict], key: Callable[[dict], str], order: list[str]) -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        g[key(r)].append(r)
    return {k: g[k] for k in order if k in g} | {k: v for k, v in g.items() if k not in order}


def cer_summary(rows: list[dict]) -> dict[str, Any]:
    n = len(rows)
    edits, chars = sum(r["edits"] for r in rows), sum(r["ref_len"] for r in rows)
    capped = sum(min(r["edits"], r["ref_len"]) for r in rows)
    return {"n": n, "ref_chars": chars, "edits": edits, "cer": _ratio(edits, chars),
            "cer_capped": _ratio(capped, chars),
            "n_loops": sum(r["max_compression_ratio"] > LOOP_COMPRESSION_RATIO for r in rows),
            "mean_utt_cer": mean(r["cer"] for r in rows) if n else None,
            "share_cer_gt_threshold": _ratio(sum(r["cer"] > CER_ERROR_THRESHOLD for r in rows), n),
            "share_exact": _ratio(sum(r["edits"] == 0 for r in rows), n)}


def polarity_summary(rows: list[dict]) -> dict[str, Any]:
    n = len(rows)
    flips = [r for r in rows if r["flip"]]
    kinds = Counter(r["flip_kind"] for r in flips)
    lead_ref = [r for r in rows if r["lead_ref"]]
    return {"n": n, "n_ref_neg": sum(r["pol_ref"] == "neg" for r in rows), "n_flip": len(flips),
            "flip_rate": _ratio(len(flips), n),
            "n_neg_gained": sum(r["flip_dir"] == "neg_gained" for r in flips),
            "n_neg_lost": sum(r["flip_dir"] == "neg_lost" for r in flips),
            "flip_kinds": {k: kinds.get(k, 0) for k in FLIP_KINDS},
            "n_lead_ref_pos": sum(r["lead_ref"] == "pos" for r in rows),
            "n_lead_ref_neg": sum(r["lead_ref"] == "neg" for r in rows),
            "n_inversion": sum(1 for r in lead_ref if r["lead_hyp"] and r["lead_hyp"] != r["lead_ref"]),
            "n_lead_lost_pos": sum(1 for r in lead_ref if r["lead_ref"] == "pos" and not r["lead_hyp"]),
            "n_lead_lost_neg": sum(1 for r in lead_ref if r["lead_ref"] == "neg" and not r["lead_hyp"])}


def extractor_summary(rows: list[dict]) -> dict[str, Any]:
    n = len(rows)
    with_slots = [r for r in rows if r["slot_ids"]]
    return {"n": n, "n_ref_nonempty": sum(r["ref_extract_nonempty"] for r in rows),
            "n_diff": sum(r["ext_diff"] for r in rows), "diff_rate": _ratio(sum(r["ext_diff"] for r in rows), n),
            "n_diff_raw": sum(r["ext_diff_raw"] for r in rows),
            "diff_rate_raw": _ratio(sum(r["ext_diff_raw"] for r in rows), n),
            "n_with_asked_slot": len(with_slots), "n_asked_diff": sum(r["ext_asked_diff"] for r in with_slots),
            "asked_diff_rate": _ratio(sum(r["ext_asked_diff"] for r in with_slots), len(with_slots)),
            "script_converted_rate": _ratio(sum(r["script_converted"] for r in rows), n)}


def calibration_for(rows: list[dict]) -> dict[str, Any]:
    errors, flips = [r["error"] for r in rows], [r["flip"] for r in rows]
    gated = [r for r in rows if r["qtype"] in ("redflag", "critical")]
    out: dict[str, Any] = {"n": len(rows), "n_error": sum(errors), "n_flip": sum(flips),
                           "n_gated": len(gated), "n_gated_error": sum(r["error"] for r in gated),
                           "auc_error": {}, "auc_error_gated": {}, "auc_flip": {}, "threshold_table": {}}
    for f in FEATURES:
        vals = [r[f] for r in rows]
        out["auc_error"][f] = low_confidence_auc(vals, errors)
        out["auc_flip"][f] = low_confidence_auc(vals, flips)
        out["auc_error_gated"][f] = low_confidence_auc([r[f] for r in gated], [r["error"] for r in gated])
    for f in ("min_word_prob", "mean_word_prob"):
        out["threshold_table"][f] = threshold_table([r[f] for r in rows], errors, flips)
    return out


def policy_for(rows: list[dict], thr_critical: float, thr_other: float) -> dict[str, Any]:
    """比照系統現行政策：紅旗題與關鍵題用 thr_critical，其他（含開場白）用 thr_other。"""
    out = {}
    for f in ("min_word_prob", "mean_word_prob"):
        thr = [thr_critical if r["qtype"] in ("redflag", "critical") else thr_other for r in rows]
        s = threshold_stats([r[f] for r in rows], thr, [r["error"] for r in rows], [r["flip"] for r in rows])
        sub = {}
        for name, sel in (("gated", lambda r: r["qtype"] in ("redflag", "critical")),
                          ("other", lambda r: r["qtype"] not in ("redflag", "critical"))):
            idx = [i for i, r in enumerate(rows) if sel(r)]
            sub[name] = threshold_stats([rows[i][f] for i in idx], [thr[i] for i in idx],
                                        [rows[i]["error"] for i in idx], [rows[i]["flip"] for i in idx])
        out[f] = {**s, "subgroups": sub}
    return out


def analyze(rows: list[dict], thr_critical: float, thr_other: float) -> dict[str, Any]:
    """只依 rows 計算所有彙總數字（報告 JSON 內含 rows，因此數字可由 JSON 重現）。"""
    conds = _conditions(rows)
    by_cond = _groups(rows, lambda r: r["condition"], conds)
    s: dict[str, Any] = {"conditions": conds, "n_records": len(rows), "n_utterances": len({r["id"] for r in rows}),
                         "asr_seconds": round(sum(r["elapsed_s"] for r in rows), 1)}
    s["cer"] = {"by_condition": {c: cer_summary(g) for c, g in by_cond.items()},
                "by_condition_voice": {c: {v: cer_summary(x) for v, x in _groups(g, lambda r: r["voice"], []).items()}
                                       for c, g in by_cond.items()},
                "by_condition_qtype": {c: {q: cer_summary(x) for q, x in _groups(g, lambda r: r["qtype"], QTYPE_ORDER).items()}
                                       for c, g in by_cond.items()}}
    s["polarity"] = {"by_condition": {c: polarity_summary(g) for c, g in by_cond.items()},
                     "by_condition_qtype": {c: {q: polarity_summary(x) for q, x in _groups(g, lambda r: r["qtype"], QTYPE_ORDER).items()}
                                            for c, g in by_cond.items()},
                     "flips": [{k: r[k] for k in ("id", "condition", "voice", "qtype", "q_ids", "ref", "hyp", "pol_ref",
                                                 "hyp_tw", "pol_hyp", "flip_dir", "flip_kind")} for r in rows if r["flip"]]}
    s["polarity"]["n_flip_records"] = len(s["polarity"]["flips"])                       # 句 × 條件
    s["polarity"]["n_flip_distinct_utterances"] = len({f["id"] for f in s["polarity"]["flips"]})
    s["extractor"] = {"by_condition": {c: extractor_summary(g) for c, g in by_cond.items()},
                      "by_condition_qtype": {c: {q: extractor_summary(x) for q, x in _groups(g, lambda r: r["qtype"], QTYPE_ORDER).items()}
                                             for c, g in by_cond.items()},
                      "differing_slots": {c: dict(Counter(k for r in g for k in r["ext_diff_slots"]).most_common())
                                          for c, g in by_cond.items()}}
    cal_groups = {**by_cond, "ALL": rows}
    s["calibration"] = {"cer_error_threshold": CER_ERROR_THRESHOLD, "thresholds": THRESHOLDS,
                        "policy_thresholds": {"critical": thr_critical, "other": thr_other},
                        "by_condition": {c: calibration_for(g) for c, g in cal_groups.items()},
                        "policy": {c: policy_for(g, thr_critical, thr_other) for c, g in cal_groups.items()}}
    return s


# ======================================================================== 報告（Markdown）
def pct(x: float | None, d: int = 1) -> str:
    return "—" if x is None else f"{x * 100:.{d}f}%"


def num(x: float | None, d: int = 3) -> str:
    return "—" if x is None else f"{x:.{d}f}"


def table(headers: list[str], rows: list[list[Any]]) -> str:
    esc = lambda c: str(c).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
                     + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]) + "\n"


def summary_bullets(s: dict[str, Any]) -> list[str]:
    conds, cal = s["conditions"], s["calibration"]
    gated = lambda c, k="n_flip": sum(s["polarity"]["by_condition_qtype"][c].get(q, {}).get(k, 0) for q in ("redflag", "critical"))
    pol = s["polarity"]
    out = ["- CER：" + "；".join(f"{c} {pct(s['cer']['by_condition'][c]['cer'])}（單句上限 100% 後 {pct(s['cer']['by_condition'][c]['cer_capped'])}，"
                                   f"重複幻覺 {s['cer']['by_condition'][c]['n_loops']} 句）" for c in conds) + "。",
           "- 極性翻轉（句，ref 與 hyp 的否定判定不同）：" + "；".join(
               f"{c} {s['polarity']['by_condition'][c]['n_flip']}/{s['polarity']['by_condition'][c]['n']}（紅旗＋關鍵題 {gated(c)}）" for c in conds) + "。",
           f"- 上述翻轉合計 {pol['n_flip_records']} 筆（句 × 條件），多是同一句在不同條件重複出現，實際只有 {pol['n_flip_distinct_utterances']} 個不同句子。",
           "- 明確 yes/no 互換（句首肯定詞↔否定詞）：" + "；".join(f"{c} {s['polarity']['by_condition'][c]['n_inversion']}" for c in conds)
           + "；句首肯定／否定詞被吞掉：" + "；".join(
               f"{c} {s['polarity']['by_condition'][c]['n_lead_lost_pos'] + s['polarity']['by_condition'][c]['n_lead_lost_neg']}/"
               f"{s['polarity']['by_condition'][c]['n_lead_ref_pos'] + s['polarity']['by_condition'][c]['n_lead_ref_neg']}" for c in conds) + "。",
           "- 抽取器輸出與 ref 不同：" + "；".join(f"{c} {pct(s['extractor']['by_condition'][c]['diff_rate'])}" for c in conds) + "。"]
    a = cal["by_condition"]["ALL"]
    out.append(f"- 信心值 AUC（全部條件，錯誤 {a['n_error']}／{a['n']} 句、翻轉 {a['n_flip']} 句）：" + "；".join(
        f"{f} 錯誤 {num(a['auc_error'][f])}、翻轉 {num(a['auc_flip'][f])}" for f in FEATURES) + "。")
    thr_c, thr_o = cal["policy_thresholds"]["critical"], cal["policy_thresholds"]["other"]
    for c in conds:
        p = cal["policy"][c]["min_word_prob"]
        out.append(f"- 現行政策（{thr_c}／{thr_o}，`min_word_prob`）{c}：重問 {pct(p['reask_rate'])}，抓到錯誤 {pct(p['error_caught'])}，"
                   f"抓到極性翻轉 {p['n_flip_caught']}/{p['n_flip']}。")
    rates = [cal["policy"][c]["min_word_prob"]["reask_rate"] for c in conds]
    out.append(f"- 注意：`min_word_prob` 在現行門檻（{thr_c}／{thr_o}）下會重問 {min(rates) * 100:.0f}–{max(rates) * 100:.0f}% 的句子，"
               "所以「抓到全部翻轉」不代表此門檻可用。")
    return out


def render_md(s: dict[str, Any], asr_meta: dict[str, Any], stem: str) -> str:
    conds = s["conditions"]
    cal = s["calibration"]
    thr_c, thr_o = cal["policy_thresholds"]["critical"], cal["policy_thresholds"]["other"]
    wall = sum(x["wall_s"] for x in asr_meta.get("sessions", []))
    L: list[str] = [f"# STT 評估：本機 Whisper × 合成電話語音（{stem.removeprefix('stt_whisper_')}）\n"]
    L.append("""> **限制（先讀）**：本報告用 macOS 系統語音合成「標準國語」病人回答，再模擬電話線路（300–3400 Hz 帶通、8 kHz G.711 μ-law）。
> 沒有台語、沒有國台語夾雜、沒有高齡口音與喘氣停頓、沒有環境噪音、沒有真實電話壓縮與回音，語速平穩、咬字清楚。
> 因此這裡的數字是 **樂觀上限**：真實病人只會更差，不能拿來宣稱 STT 達標，也**不能用來定案** 0.9／0.75 門檻。
> 它的用途是：(1) 驗證評估流程能跑通、(2) 找出指標與程式的問題、(3) 作為日後比較的基準線。
> 真實評估需要同仁經真實電話線路的角色扮演錄音（Q-01）與 Breeze-ASR-25（D-48，待新硬體）；屆時只換模型與音檔來源，流程不變。
> 病人回答文字來自 LLM 模擬病人（非真實病人資料）。\n""")
    L.append("## 摘要（由數字自動產生）\n")
    L.extend(summary_bullets(s))
    L.append("")
    L.append("## 0. 設定\n")
    L.append(f"- 模型：`{asr_meta['model']}`（本機快取，離線）；language={asr_meta['language']}、temperature=0、word_timestamps=True；音檔來源：{asr_meta['source']}。")
    L.append(f"- 句數：{s['n_utterances']} 句（開場白與病人回答依文字去重）× 條件 {len(conds)} = {s['n_records']} 筆轉寫。")
    L.append(f"- 條件：{', '.join(f'`{c}`' for c in conds)}（clean = 16 kHz 乾淨；phone = 電話音質；phone_prompt = phone + initial_prompt）。")
    L.append(f"- 耗時：Whisper 轉寫合計 {s['asr_seconds']:.0f} 秒（約 {s['asr_seconds'] / max(s['n_records'], 1):.2f} 秒／筆）；含合成與載入的牆鐘時間 {wall:.0f} 秒。")
    L.append("- 題型：紅旗題 = `priority: redflag`；關鍵題 = Q-CHARACTER-01／Q-REST-02（`stt_critical_questions`）；兩者系統門檻 0.9，其餘 0.75（D-43、D-46）。"
             "同一句出現在多種題型時取最嚴重者（紅旗 > 關鍵 > 其他 > 開場白）。\n")

    # ---- 1. CER
    L.append("## 1. 字錯率（CER）\n")
    L.append("CER = Σ 編輯距離 / Σ 參考字數（micro 平均），參考與轉寫皆經 NFKC、繁轉簡、阿拉伯數字轉中文數字、兩→二、去標點空白。"
             f"「CER>{CER_ERROR_THRESHOLD}」= 該句有超過一成字錯。Whisper 在 temperature=0（無 fallback）時偶爾陷入重複迴圈（壓縮比 > {LOOP_COMPRESSION_RATIO}），"
             "一句的插入字數可遠超參考長度而灌高 micro CER，所以另列「單句錯誤上限為參考長度」的 CER（= Σ min(編輯距離, 參考字數) / Σ 參考字數）。\n")
    L.append("**依條件**\n")
    L.append(table(["條件", "句數", "參考字數", "CER", "CER（單句上限 100%）", "重複幻覺句數", f"句 CER>{CER_ERROR_THRESHOLD}", "完全正確"],
                   [[c, v["n"], v["ref_chars"], pct(v["cer"]), pct(v["cer_capped"]), v["n_loops"], pct(v["share_cer_gt_threshold"]), pct(v["share_exact"])]
                    for c, v in s["cer"]["by_condition"].items()]))
    voices = sorted({v for c in s["cer"]["by_condition_voice"].values() for v in c})
    L.append("**依語音 × 條件**\n")
    L.append("（括號內為單句上限 100% 的 CER）\n")
    L.append(table(["語音"] + conds, [[v] + [f"{pct(s['cer']['by_condition_voice'][c].get(v, {}).get('cer'))}（{pct(s['cer']['by_condition_voice'][c].get(v, {}).get('cer_capped'))}；n={s['cer']['by_condition_voice'][c].get(v, {}).get('n', 0)}）"
                                          for c in conds] for v in voices]))
    L.append("**依題型 × 條件**\n")
    L.append(table(["題型"] + conds, [[QTYPE_LABEL[q]] + [f"{pct(s['cer']['by_condition_qtype'][c].get(q, {}).get('cer'))}（{pct(s['cer']['by_condition_qtype'][c].get(q, {}).get('cer_capped'))}；n={s['cer']['by_condition_qtype'][c].get(q, {}).get('n', 0)}）"
                                                       for c in conds] for q in QTYPE_ORDER]))

    # ---- 2. 極性
    L.append("## 2. 極性翻轉（有／沒有 聽反）\n")
    L.append("**否定判定**（`sim/stt_eval.py: polarity`，依任務定義）：去掉句首標點與語助詞後，以否定詞（沒有、沒、不會、不是、不、沒什麼、還沒）開頭 → 否定；"
             "以肯定詞（有、會、是、還在、對）開頭 → 肯定（其後的否定詞不翻轉它）；否則整句出現否定詞 → 否定；"
             "含「不舒服、不確定」等非否定片語先遮罩。ref 與 hyp（繁體化後）的否定判定不同 = **翻轉**。"
             "這是句子層級的表面判定（有無否定詞），不依賴標點；它會把「句首的『有／對』被吞掉、剩下的句子恰好含『還沒／不完』」也算成翻轉，語意未必反向，"
             "所以翻轉依性質再分四類：**明確互換**（ref、hyp 句首都是肯定／否定詞且相反，如「有」→「沒有」，真的 yes/no 聽反，D-42 的危險情境）、"
             "**句首詞消失**、**句首多出詞**（如「這個」被聽成「有個」）、**句中否定詞增減**（如「沒有在痛」→「的有贊通」）。"
             "`neg_gained` = 非否定被聽成否定（紅旗題答「有」被聽成「沒有」必降級）；`neg_lost` = 否定被聽成非否定。"
             "多個否定詞中只少了一個而整句仍為否定者不算翻轉，該類差異由第 3 節的抽取器差異反映。\n")
    pq = s["polarity"]["by_condition_qtype"]
    pc = s["polarity"]["by_condition"]
    L.append("**翻轉數（依題型）**\n")
    L.append(table(["條件", "全部（翻轉/句）", "紅旗題", "關鍵題", "其他", "開場白"],
                   [[c, f"{v['n_flip']}/{v['n']}（{pct(v['flip_rate'])}）"] +
                    [f"{pq[c].get(q, {}).get('n_flip', 0)}/{pq[c].get(q, {}).get('n', 0)}" for q in QTYPE_ORDER]
                    for c, v in pc.items()]))
    L.append("**翻轉的性質**（全部題型）\n")
    L.append(table(["條件", "翻轉數"] + [FLIP_KIND_LABEL[k] for k in FLIP_KINDS] + ["neg_gained", "neg_lost"],
                   [[c, v["n_flip"]] + [v["flip_kinds"][k] for k in FLIP_KINDS] + [v["n_neg_gained"], v["n_neg_lost"]] for c, v in pc.items()]))
    L.append("**句首 yes/no 詞的保留**（ref 以肯定／否定詞開頭的句子；明確互換 = 句首詞還在但極性相反；被吞掉 = hyp 句首不再是肯定／否定詞）\n")
    L.append(table(["條件", "ref 句首肯定詞", "ref 句首否定詞", "明確互換", "肯定詞被吞掉", "否定詞被吞掉"],
                   [[c, v["n_lead_ref_pos"], v["n_lead_ref_neg"], v["n_inversion"], v["n_lead_lost_pos"], v["n_lead_lost_neg"]] for c, v in pc.items()]))
    flips = s["polarity"]["flips"]
    sev = [f for f in flips if f["qtype"] in ("redflag", "critical")]
    kinds = Counter(f["flip_kind"] for f in sev)
    L.append(f"**紅旗題與關鍵題的翻轉共 {len(sev)} 筆**（" + "、".join(f"{FLIP_KIND_LABEL[k]} {kinds.get(k, 0)}" for k in FLIP_KINDS)
             + f"）；全部題型翻轉 {len(flips)} 筆。完整清單（hyp 為繁體化後的轉寫）：\n")
    if flips:
        L.append(table(["條件", "語音", "題型", "題目", "性質", "方向", "ref → hyp"],
                       [[f["condition"], f["voice"], QTYPE_LABEL[f["qtype"]], "／".join(f["q_ids"]) or "開場白", FLIP_KIND_LABEL[f["flip_kind"]],
                         f["flip_dir"], f"{f['ref']} → {f['hyp_tw'][:60]}"]
                        for f in sorted(flips, key=lambda f: (_QTYPE_RANK[f["qtype"]], f["id"], f["condition"]))]))
    else:
        L.append("（無）\n")

    # ---- 3. 抽取器
    L.append("## 3. 抽取器受 ASR 影響\n")
    L.append("對 ref（原始文字）與 hyp 各跑 `acs_triage.extract.extract()`，比較整份輸出是否相同。**只衡量 ASR 造成的差異，不評抽取器本身**；"
             "現行關鍵詞抽取器對許多否定回答本來就回傳空 dict，所以差異率是下限。"
             "hyp 先做 NFKC＋簡轉繁（`hyp_tw`，代表 STT adapter 應有的輸出）；「未轉換」欄是直接餵 Whisper 原文。"
             "「被問 slot」= 只比較該句對應題目的 slot。\n")
    ex = s["extractor"]["by_condition"]
    L.append(table(["條件", "句數", "ref 抽到東西", "輸出不同（繁體化後）", "輸出不同（原文）", "被問 slot 不同", "Whisper 輸出需簡轉繁的比例"],
                   [[c, v["n"], v["n_ref_nonempty"], f"{v['n_diff']}（{pct(v['diff_rate'])}）", f"{v['n_diff_raw']}（{pct(v['diff_rate_raw'])}）",
                     f"{v['n_asked_diff']}/{v['n_with_asked_slot']}（{pct(v['asked_diff_rate'])}）", pct(v["script_converted_rate"])]
                    for c, v in ex.items()]))
    eq = s["extractor"]["by_condition_qtype"]
    L.append("**輸出不同（繁體化後）依題型**\n")
    L.append(table(["條件"] + [QTYPE_LABEL[q] for q in QTYPE_ORDER],
                   [[c] + [f"{eq[c].get(q, {}).get('n_diff', 0)}/{eq[c].get(q, {}).get('n', 0)}" for q in QTYPE_ORDER] for c in conds]))
    ds = s["extractor"]["differing_slots"]
    L.append("**差異集中的 slot**（次數）：" + "；".join(f"{c}：" + "、".join(f"{k} {v}" for k, v in list(ds[c].items())[:6]) for c in conds if ds[c]) + "\n")

    # ---- 4. 校準
    L.append("## 4. 信心校準\n")
    L.append(f"錯誤 = CER>{CER_ERROR_THRESHOLD} **或** 極性翻轉。特徵：`mean_avg_logprob`（各 segment 平均）、`min_word_prob`、`mean_word_prob`（逐字機率，排除純標點 token）。"
             "AUC 以「信心越低越可能錯」計，0.5 = 無鑑別力、1.0 = 完美。重問 = 特徵 < 門檻（比照 runner 的 `conf < thr`）。\n")
    L.append("**AUC**\n")
    rows_auc = []
    for c, v in cal["by_condition"].items():
        rows_auc.append([c, v["n"], v["n_error"], v["n_flip"]] + [num(v["auc_error"][f]) for f in FEATURES]
                        + [num(v["auc_error_gated"][f]) for f in FEATURES] + [num(v["auc_flip"][f]) for f in FEATURES])
    L.append(table(["條件", "句數", "錯誤數", "翻轉數"] + [f"AUC錯誤·{f}" for f in FEATURES] + [f"AUC錯誤·紅旗+關鍵·{f}" for f in FEATURES]
                   + [f"AUC翻轉·{f}" for f in FEATURES], rows_auc))
    L.append("（`ALL` = 所有條件合併；AUC 翻轉欄在翻轉數太少時不穩定，僅供參考。）\n")
    for f in ("min_word_prob", "mean_word_prob"):
        L.append(f"**門檻表：`{f}`**（★ = 系統現行門檻 0.75／0.9）\n")
        for c, v in cal["by_condition"].items():
            L.append(f"{c}（句數 {v['n']}、錯誤 {v['n_error']}、翻轉 {v['n_flip']}）\n")
            L.append(table(["門檻", "被要求重問", "抓到的錯誤", "抓到的極性翻轉", "重問中真有錯"],
                           [[("★ " if t["threshold"] in MARK_THRESHOLDS else "") + f"{t['threshold']:.2f}",
                             f"{t['n_reask']}/{t['n']}（{pct(t['reask_rate'])}）",
                             f"{t['n_error_caught']}/{t['n_error']}（{pct(t['error_caught'])}）",
                             f"{t['n_flip_caught']}/{t['n_flip']}（{pct(t['flip_caught'])}）", pct(t["precision"])]
                            for t in v["threshold_table"][f]]))
    L.append(f"**依系統現行政策**（紅旗題＋關鍵題 < {thr_c}、其他 < {thr_o} 才重問）\n")
    prow = []
    for c, v in cal["policy"].items():
        for f in ("min_word_prob", "mean_word_prob"):
            p = v[f]
            prow.append([c, f, f"{p['n_reask']}/{p['n']}（{pct(p['reask_rate'])}）",
                         f"{p['subgroups']['gated']['n_reask']}/{p['subgroups']['gated']['n']}（{pct(p['subgroups']['gated']['reask_rate'])}）",
                         f"{p['subgroups']['other']['n_reask']}/{p['subgroups']['other']['n']}（{pct(p['subgroups']['other']['reask_rate'])}）",
                         f"{p['n_error_caught']}/{p['n_error']}（{pct(p['error_caught'])}）",
                         f"{p['n_flip_caught']}/{p['n_flip']}（{pct(p['flip_caught'])}）",
                         f"{p['n_flip'] - p['n_flip_caught']}"])
    L.append(table(["條件", "特徵", "重問（全部）", "重問（紅旗+關鍵）", "重問（其他）", "抓到的錯誤", "抓到的極性翻轉", "漏掉的翻轉"], prow))
    pa = cal["policy"]["ALL"]
    best = max(FEATURES, key=lambda f: cal["by_condition"]["ALL"]["auc_error"][f] or 0)
    L.append(f"**解讀注意**：Whisper 逐字機率不是校準過的機率（D-48 已註明）。本次（全部條件合併）：現行政策套在 `min_word_prob` 會重問 {pct(pa['min_word_prob']['reask_rate'])}、"
             f"套在 `mean_word_prob` 會重問 {pct(pa['mean_word_prob']['reask_rate'])}；錯誤鑑別力（AUC）最高者為 `{best}`。"
             "逐字最低機率容易被語助詞（耶、啦）與單一字的誤差拉低，直接把 0.75／0.9 套在 `min_word_prob` 的重問比例會偏高；"
             "且這是合成語音的樂觀情況，真正的 0.9／0.75 要用真實錄音重算。\n")

    L.append("## 5. 重現\n")
    L.append("""```
# 1) 建 utterance 清單（專案 .venv）
.venv/bin/python -m sim.stt_eval build
# 2) 合成 + Whisper（ASR 環境；全程離線，音檔放 scratch）
uv run --offline --no-project --python 3.14 --with mlx-whisper --with opencc-python-reimplemented \\
    python -P sim/stt_synth_asr.py --utterances reports/stt_utterances_2026-10-22.json \\
    --audio-dir <scratch>/stt_audio --out <scratch>/stt_asr_results.json
# 3) 計分、出報告（專案 .venv）
.venv/bin/python -m sim.stt_eval score --asr <scratch>/stt_asr_results.json
```
換模型：A 段加 `--model <MLX 格式的路徑或 repo>` 並用新的 `--out`；換真實錄音：`--recordings-dir <含 <id>.wav 的目錄>`（條件改為 rec／rec_prompt）。
報告 JSON 內含逐筆資料（`rows`），所有彙總數字可由 `rows` 重算（`analyze(rows)`）。""")
    return "\n".join(L) + "\n"


def cmd_score(args: argparse.Namespace) -> None:
    asr = json.loads(Path(args.asr).read_text(encoding="utf-8"))
    utts = json.loads(Path(args.utterances).read_text(encoding="utf-8"))
    th = load_clinical_rules()["thresholds"]
    rows = make_rows(asr, utts)
    summary = analyze(rows, th["stt_min_confidence_critical"], th["stt_min_confidence"])
    out_dir = Path(args.out_dir)
    (out_dir / f"{args.stem}.json").write_text(
        json.dumps({"meta": asr["meta"], "definitions": {"error": f"cer>{CER_ERROR_THRESHOLD} or polarity flip",
                                                         "reask": "feature < threshold"},
                    "summary": summary, "rows": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out_dir / f"{args.stem}.md").write_text(render_md(summary, asr["meta"], args.stem), encoding="utf-8")
    print(f"{summary['n_utterances']} 句 / {summary['n_records']} 筆 -> {out_dir / args.stem}.{{md,json}}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="從 LLM 病人逐字稿建 utterance 清單")
    b.add_argument("--transcripts", default=str(DEFAULT_TRANSCRIPTS))
    b.add_argument("--out", default=str(DEFAULT_UTTERANCES))
    b.set_defaults(func=cmd_build)
    sc = sub.add_parser("score", help="讀 A 段結果，計分並寫報告")
    sc.add_argument("--asr", required=True, help="sim/stt_synth_asr.py 的結果 JSON")
    sc.add_argument("--utterances", default=str(DEFAULT_UTTERANCES))
    sc.add_argument("--out-dir", default=str(REPO_ROOT / "reports"))
    sc.add_argument("--stem", default=DEFAULT_STEM)
    sc.set_defaults(func=cmd_score)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
