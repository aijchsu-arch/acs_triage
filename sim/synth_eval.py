"""實驗 1：系統評估三層拆解 vs 獨立 LLM 參考標註 → 報告與 Clinical Owner 裁定表。

python -m sim.synth_eval --llm-json reports/eval_<date>_llm_scenarios_synth_v1_opus-5-5_medium.json
                         [--scenarios data/synth/scenarios_synth_v1.yaml] [--reference data/synth/reference_synth_v1.json]
                         [--pilot-cost-usd X] [--date YYYY-MM-DD] [--out reports/]

(a) 全資訊規則：病人知道的全部事實一次寫入 SlotState → RulesEngine（測規則本身的效度）
(b) Scripted 病人對話（clean）：開場白抽取 → Prompter 逐題問 → gate（測問診與 gate 的影響）
(c) Opus LLM 病人：重放 `python -m sim.run_llm_eval --scenarios ...` 的逐字稿（測病人表達的影響）

比較基準（皆為 LLM 參考標註，不是 truth）：
- 參考一致子集（主分析）：兩位標註者 tier 與 hard_stop 都一致。
- 全部（另列）：取兩位標註者中較急者（保守參考）。
急迫度：Hard stop = -1、T0–T4 = 0–4；T9 依 tier9_fallback（護理師不可得時的預設等級）換算——系統用自己結束時的 slot 狀態，
參考標註用全部事實。under = 系統比參考不急；over = 系統比參考急；exact = tier 與 hard_stop 都相同。

產出：reports/synth_eval_<date>.md／.json、reports/synth_adjudication_<date>.xlsx／.md。
.xlsx 以標準函式庫寫成（openpyxl 不在本專案環境、本實驗不安裝套件）。
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from datetime import date
from math import comb
from pathlib import Path
from statistics import mean
from typing import Any
from xml.sax.saxutils import escape

from acs_triage.extract import extract
from acs_triage.loaders import REPO_ROOT, question_by_id, rules_version
from acs_triage.pathway import tier9_fallback
from acs_triage.rules import RulesEngine, SlotState

from .cases import Case
from .llm_patient import render_sheet
from .patient import ScriptedPatient
from .runner import run_case
from .synth_annotate import DEFAULT_OUT as DEFAULT_REFERENCE, normalized
from .synth_gen import DEFAULT_OUT as DEFAULT_SCENARIOS, load_synth, synth_case

LAYERS = {"a": "(a) 全資訊規則", "b": "(b) Scripted 病人", "c": "(c) Opus LLM 病人"}
ANN = {"opus": "Opus 5.5", "gpt": "gpt-6.1-sol"}
_ENGINE = RulesEngine()


# ---------------------------------------------------------------- 統計
def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def _bisect(f, lo: float = 0.0, hi: float = 1.0) -> float:
    """f 在 [lo, hi] 單調、兩端異號；回傳根。"""
    flo = f(lo)
    for _ in range(100):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (flo > 0):
            lo, flo = mid, f(mid)
        else:
            hi = mid
    return (lo + hi) / 2


def clopper_pearson(x: int, n: int, alpha: float = 0.05) -> tuple[float, float] | None:
    if n == 0:
        return None
    lo = 0.0 if x == 0 else _bisect(lambda p: (1 - _binom_cdf(x - 1, n, p)) - alpha / 2)
    hi = 1.0 if x == n else _bisect(lambda p: _binom_cdf(x, n, p) - alpha / 2)
    return lo, hi


def prop(x: int, n: int) -> dict[str, Any]:
    ci = clopper_pearson(x, n)
    return {"x": x, "n": n, "p": (x / n) if n else None, "ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None}


def fmt_prop(d: dict[str, Any]) -> str:
    if not d["n"]:
        return "—（n=0）"
    lo, hi = d["ci95"]
    return f"{d['x']}/{d['n']}（{100 * d['p']:.1f}%，95% CI {100 * lo:.1f}–{100 * hi:.1f}%）"


# ---------------------------------------------------------------- 三層結果
def urgency(tier: int, hs: bool, state: SlotState) -> int:
    if hs:
        return -1
    return tier9_fallback(state)[0] if tier == 9 else tier


def _outcome(d, state: SlotState, n_q: int | None = None, stop: str | None = None) -> dict[str, Any]:
    return {"tier": d.tier, "hs": d.hard_stop, "rf": list(d.rf_hits), "urg": urgency(d.tier, d.hard_stop, state),
            "t9_fallback": tier9_fallback(state)[0] if d.tier == 9 else None, "n_q": n_q, "stop": stop}


def layer_a(case: Case) -> dict[str, Any]:
    state = SlotState(case.slots)
    return _outcome(_ENGINE.decide(state), state)


def layer_b(case: Case) -> dict[str, Any]:
    r = run_case(case, patient=ScriptedPatient(case))
    return _outcome(r.final, r.final_state, r.n_questions, r.stop_reason)


def replay(case: Case, transcript: dict[str, Any]) -> dict[str, Any]:
    """依逐字稿（每題確認後採用的值）重建結束時的 slot 狀態，與 runner 的寫入順序相同；最終結果須與逐字稿一致。"""
    qb = question_by_id()
    state = SlotState(extract(case.opening_zh))
    for k in case.reset_slots:
        state.set(k, None, source="reset_for_variant")
    for i, t in enumerate(transcript["turns"], 1):
        v = t["confirm"]["adopted_value"] if "confirm" in t else t["value"]
        state.set(qb[t["q"]].slot_id, v, asked_by=t["q"], source=f"turn{i}")
    d = _ENGINE.decide(state)
    key = f"{d.tier}{'Y' if d.hard_stop else ''}"
    if key != transcript["final"]:
        raise ValueError(f"{case.id}: 重放結果 {key} ≠ 逐字稿 {transcript['final']}")
    return _outcome(d, state, len(transcript["turns"]), transcript["stop"])


def ref_outcome(label: dict[str, Any], case: Case) -> dict[str, Any]:
    tier, hs = normalized(label)
    return {"tier": tier, "hs": hs, "rf": list(label["rf_ids"]), "urg": urgency(tier, hs, SlotState(case.slots)),
            "confidence": label["confidence"], "rationale_zh": label["rationale_zh"],
            "raw_inconsistent": bool(label["hard_stop"]) and label["tier"] != "T0"}


def conservative(a: dict[str, Any] | None, b: dict[str, Any] | None) -> dict[str, Any] | None:
    """兩位標註者中較急者；同急迫度時取非 T9 者。"""
    cands = [x for x in (a, b) if x is not None]
    return min(cands, key=lambda x: (x["urg"], x["tier"] == 9)) if cands else None


_NOT_CHEST = ("none", "other")   # 明確沒有胸部症狀，或性質「其他」（不算胸部症狀）


def slot_semantics(scenarios: list[dict[str, Any]]) -> dict[str, list[str]]:
    """生成器把只對胸部症狀有意義的 slot 用在非胸部症狀（與開場白不矛盾，但與規則的定義不一致）。"""
    cases = [synth_case(sc) for sc in scenarios]
    nochest = [c for c in cases if c.slots.get("symptom_character") in _NOT_CHEST]
    rest_only_t0 = []
    for c in nochest:
        d = _ENGINE.decide(SlotState(c.slots))
        if not d.hard_stop and d.tier == 0 and [e for e in d.evidence if e.startswith("T0-")] == ["T0-REST-NEW"]:
            rest_only_t0.append(c.id)
    return {"rest_symptom_true_no_chest": [c.id for c in nochest if c.slots.get("rest_symptom") is True],
            "rest_symptom_true_postprandial_relieved": [c.id for c in cases if c.slots.get("rest_symptom") is True
                                                        and c.slots.get("postprandial_relieved") is True],
            "exertion_relation_no_chest": [c.id for c in nochest if c.slots.get("exertion_relation") is not None],
            "a_t0_only_by_rest_new_no_chest": rest_only_t0}


def build_rows(scenarios: list[dict[str, Any]], reference: dict[str, Any], transcripts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs = {r["case_id"]: r for r in reference["cases"]}
    trs = {t["case_id"]: t for t in transcripts}
    rows = []
    for sc in scenarios:
        case = synth_case(sc)
        row: dict[str, Any] = {"id": case.id, "category": sc["category"], "persona_style": sc["persona_style"],
                               "name_zh": sc.get("name_zh"), "opening_zh": case.opening_zh, "sheet": render_sheet(case),
                               "errors": {}}
        labels = refs.get(case.id, {}).get("labels", {})
        for n in ANN:
            row[f"ref_{n}"] = ref_outcome(labels[n], case) if n in labels else None
            if n not in labels:
                row["errors"][f"ref_{n}"] = refs.get(case.id, {}).get("errors", {}).get(n, "沒有標註")
        ro, rg = row["ref_opus"], row["ref_gpt"]
        row["ref_agree"] = ro if (ro and rg and (ro["tier"], ro["hs"]) == (rg["tier"], rg["hs"])) else None
        row["ref_cons"] = conservative(ro, rg)
        for layer, fn in (("a", layer_a), ("b", layer_b)):
            try:
                row[layer] = fn(case)
            except Exception as e:  # noqa: BLE001 — 單案失敗要列出
                row[layer], row["errors"][layer] = None, f"{type(e).__name__}: {e}"
        try:
            row["c"] = replay(case, trs[case.id]) if case.id in trs else None
            if row["c"] is None:
                row["errors"]["c"] = "LLM 病人逐字稿沒有這個 case（執行錯誤，見 run_llm_eval 報告）"
        except Exception as e:  # noqa: BLE001
            row["c"], row["errors"]["c"] = None, f"{type(e).__name__}: {e}"
        row["extractor_conflicts"] = [k for k, v in extract(case.opening_zh).items()
                                      if v is not None and case.slots.get(k) is not None and case.slots[k] != v]
        rows.append(row)
    return rows


# ---------------------------------------------------------------- 指標
def metrics(rows: list[dict[str, Any]], layer: str, refkey: str) -> dict[str, Any]:
    rs = [r for r in rows if r[refkey] is not None and r[layer] is not None]
    hs_ref = [r for r in rs if r[refkey]["hs"]]
    under = [r for r in rs if r[layer]["urg"] > r[refkey]["urg"]]
    over = [r for r in rs if r[layer]["urg"] < r[refkey]["urg"]]
    exact = [r for r in rs if (r[layer]["tier"], r[layer]["hs"]) == (r[refkey]["tier"], r[refkey]["hs"])]
    ed_den = [r for r in rs if not r[refkey]["hs"] and r[refkey]["tier"] in (1, 2, 3, 4)]
    nq = [r[layer]["n_q"] for r in rs if r[layer]["n_q"] is not None]
    return {"n": len(rs),
            "hs_sensitivity": prop(sum(r[layer]["hs"] for r in hs_ref), len(hs_ref)),
            "hs_miss": [r["id"] for r in hs_ref if not r[layer]["hs"]],
            "under": prop(len(under), len(rs)), "under_cases": [r["id"] for r in under],
            "under_via_t9": prop(sum(r[layer]["tier"] == 9 for r in under), len(rs)),     # 系統 T9（轉護理師），護理師不可得時的備援較不急
            "over": prop(len(over), len(rs)), "over_cases": [r["id"] for r in over],
            "exact": prop(len(exact), len(rs)),
            "t9": prop(sum(r[layer]["tier"] == 9 for r in rs), len(rs)),
            "ed_burden": prop(sum(r[layer]["hs"] or r[layer]["tier"] == 0 for r in ed_den), len(ed_den)),
            "ed_burden_cases": [r["id"] for r in ed_den if r[layer]["hs"] or r[layer]["tier"] == 0],
            "mean_questions": round(mean(nq), 2) if nq else None}


def fmt_out(o: dict[str, Any] | None) -> str:
    if o is None:
        return "（無）"
    if o["hs"]:
        return f"T0 Hard stop（{','.join(o['rf']) or '—'}）"
    if o["tier"] == 9 and o.get("t9_fallback") is not None:
        return f"T9（備援 T{o['t9_fallback']}）"
    return f"T{o['tier']}"


def fmt_ref(o: dict[str, Any] | None) -> str:
    if o is None:
        return "（無）"
    s = f"T0 Hard stop（{','.join(o['rf']) or '—'}）" if o["hs"] else f"T{o['tier']}"
    return s + (f"，信心 {o['confidence']}" if "confidence" in o else "")


def adjudication_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """標註者不一致，或系統任一層比任一位標註者不急。"""
    out = []
    for r in rows:
        refs = [x for x in (r["ref_opus"], r["ref_gpt"]) if x is not None]
        reasons = []
        if r["ref_agree"] is None:
            reasons.append("標註者不一致")
        for layer in LAYERS:
            o = r[layer]
            if o is not None and refs and any(o["urg"] > x["urg"] for x in refs):
                who = "、".join(ANN[n] for n in ANN if r[f"ref_{n}"] and o["urg"] > r[f"ref_{n}"]["urg"])
                reasons.append(f"系統({layer})比{who}不急")
        if reasons:
            out.append({**r, "reasons": reasons})
    return out


def severity_key(r: dict[str, Any], refkey: str = "ref_cons") -> tuple:
    ref = r[refkey]
    gaps = [r[l]["urg"] - ref["urg"] for l in LAYERS if r[l] is not None]
    return (ref["urg"], -max(gaps, default=0))


# ---------------------------------------------------------------- xlsx（標準函式庫）
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _colname(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref: str, v: Any, style: int) -> str:
    if v is None:
        return ""   # 空字串照寫成空白儲存格：Clinical Owner 輸入欄要在 read_only 讀取時每列都有完整欄數
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f'<c r="{ref}" s="{style}"><v>{v}</v></c>'
    t = escape(_ILLEGAL.sub("", str(v)))
    return f'<c r="{ref}" t="inlineStr" s="{style}"><is><t xml:space="preserve">{t}</t></is></c>'


def write_xlsx(path: Path, sheets: list[tuple[str, list[list[Any]], list[int]]]) -> None:
    """sheets：[(名稱, 列（第一列為標題、粗體並凍結）, 欄寬)]。只用 inline string，不需 sharedStrings。"""
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    head = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    ct = (head + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                    for i in range(1, len(sheets) + 1)) + "</Types>")
    rels = (head + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel_ns}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    wb = (head + f'<workbook {ns} xmlns:r="{rel_ns}"><sheets>'
          + "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, (n, _, _) in enumerate(sheets, 1))
          + "</sheets></workbook>")
    wb_rels = (head + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               + "".join(f'<Relationship Id="rId{i}" Type="{rel_ns}/worksheet" Target="worksheets/sheet{i}.xml"/>'
                         for i in range(1, len(sheets) + 1))
               + f'<Relationship Id="rId{len(sheets) + 1}" Type="{rel_ns}/styles" Target="styles.xml"/></Relationships>')
    styles = (head + f'<styleSheet {ns}>'
              '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
              '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1">'
              '<alignment wrapText="1" vertical="top"/></xf>'
              '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">'
              '<alignment wrapText="1" vertical="top"/></xf></cellXfs>'
              '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        for i, (_, data, widths) in enumerate(sheets, 1):
            cols = "".join(f'<col min="{j}" max="{j}" width="{w}" customWidth="1"/>' for j, w in enumerate(widths, 1))
            dim = f"A1:{_colname(max(len(r) for r in data) - 1)}{len(data)}" if data else "A1"
            body = "".join(f'<row r="{ri}">' + "".join(_cell(f"{_colname(ci)}{ri}", v, 1 if ri == 1 else 0)
                                                       for ci, v in enumerate(row)) + "</row>"
                           for ri, row in enumerate(data, 1))
            z.writestr(f"xl/worksheets/sheet{i}.xml",
                       head + f'<worksheet {ns}><dimension ref="{dim}"/><sheetViews><sheetView workbookViewId="0">'
                       '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
                       + (f"<cols>{cols}</cols>" if cols else "") + f"<sheetData>{body}</sheetData></worksheet>")


ADJ_COLUMNS = ["case_id", "category", "persona_style", "列入原因", "開場白", "事實清單（病人知道的全部事實）",
               "Opus 5.5 分級", "Opus 5.5 理由", "gpt-6.1-sol 分級", "gpt-6.1-sol 理由",
               "系統 (a) 全資訊規則", "系統 (b) Scripted 病人", "系統 (c) Opus LLM 病人", "(c) 題數／結束原因",
               "Clinical Owner 裁定：分級（T0–T4／T9）", "Clinical Owner 裁定：Hard stop（Y／N）", "Clinical Owner 備註"]
ADJ_WIDTHS = [10, 16, 18, 26, 48, 70, 22, 48, 22, 48, 20, 20, 20, 16, 18, 18, 30]


def adjudication_table(adj: list[dict[str, Any]]) -> list[list[Any]]:
    out: list[list[Any]] = [ADJ_COLUMNS]
    for r in adj:
        c = r["c"]
        out.append([r["id"], r["category"], r["persona_style"], "；".join(r["reasons"]), r["opening_zh"], r["sheet"],
                    fmt_ref(r["ref_opus"]), (r["ref_opus"] or {}).get("rationale_zh", ""),
                    fmt_ref(r["ref_gpt"]), (r["ref_gpt"] or {}).get("rationale_zh", ""),
                    fmt_out(r["a"]), fmt_out(r["b"]), fmt_out(c),
                    f"{c['n_q']}／{c['stop']}" if c else "（無）", "", "", ""])
    return out


# ---------------------------------------------------------------- 報告
LIMITS = """\
## 限制（請先讀）

1. **合成病人**：150 例全由 OpenAI gpt-6.1-sol 生成，不是真實來電。類別比例是指定的涵蓋矩陣，不是真實來電分布；
   病人說法、症狀組合也不代表真實世界。以下比例只能描述「這批合成病人」，不能外推成臨床表現。
2. **參考標註是 LLM 判斷，不是 truth**：Opus 5.5 與 gpt-6.1-sol 各自依 `CLINICAL_RULES.md` §1–§3 原文與自身臨床判斷標註，
   看不到彼此與系統結果。兩者一致只代表兩個模型一致，不代表正確；本報告所有 under／over／exact 都是「相對於 LLM 參考標註」。
   不一致與系統低估的案例列在裁定表，須由 Clinical Owner 裁定。
3. **同家族偏差**：(i) 生成器與其中一位標註者同為 gpt-6.1-sol，可能傾向把自己寫的情境標成「該有的樣子」；
   (ii) 另一位標註者 Opus 5.5 同時扮演 (c) 的病人，而本專案的規則、題庫與 v0.2 reviewer 標籤都有 Claude 參與，
   Opus 可能與規則共享判斷框架，使「系統 vs Opus」的一致性偏高；(iii) 生成提示詞的類別說明與情境方向由 Claude Code 依
   Clinical Owner 指定的矩陣起草，可能把規則作者的視角帶進題目分布。
4. **病人用結構化答案，未經 STT／抽取**：(b)(c) 每題答案以結構化值直接寫入 slot（M2b 設計，D-30），沒有語音辨識、
   沒有逐句抽取；只有開場白經過規則抽取器。真實通話的 STT 錯誤、口語抽取錯誤、複誦確認時的相對回答都沒有模擬，
   (b)(c) 是樂觀情況。
5. **人物風格只在開場白**：persona_style 只表現在開場白文字與哪些事實未知；(c) 的 LLM 病人沿用 prompt 0.3，
   回答時不帶人物風格（不會在問答中淡化或誇大）。
6. **(a) 全資訊**：病人知道的事實一次寫入；病人不知道的事仍是未知，所以 (a) 也可能是 T9。
7. **T9 換算**：系統 T9 依 `tier9_fallback`（護理師不可得時的預設等級）換算急迫度後比較；參考標註的 T9 用全部事實換算。
   Hard stop 視為比 T0 更急一級（同 `sim/decisive.py`）。
8. **樣本小**：比例附 Clopper-Pearson 95% 信賴區間；類別與人物風格分表的 n 很小，只供找問題，不供下結論。
9. **本資料集不得用於規則、題庫、Prompter 調整**（否則驗證集就變成開發集）。
"""


def _table(L: list[str], header: list[str], rows: list[list[Any]]) -> None:
    L.append("| " + " | ".join(header) + " |")
    L.append("|" + "---|" * len(header))
    for row in rows:
        L.append("| " + " | ".join(str(x).replace("|", "\\|").replace("\n", " ") for x in row) + " |")
    L.append("")


def _xn(d: dict[str, Any]) -> str:
    return f"{d['x']}/{d['n']}" if d["n"] else "—"


def semantics_limit(sem: dict[str, list[str]]) -> str:
    def ids(k: str) -> str:
        return f"{len(sem[k])} 例（{'、'.join(sem[k])}）"
    return ("10. **生成資料的 slot 語意問題**：生成器把只對胸部症狀有意義的 slot 用在非胸部症狀（症狀性質為「沒有」或「其他」）——"
            f"rest_symptom=true 但無胸部症狀 {ids('rest_symptom_true_no_chest')}；餐後打嗝很快緩解卻填 rest_symptom=true"
            f"（與 D-35 相反）{ids('rest_symptom_true_postprandial_relieved')}；無胸部症狀卻填 exertion_relation "
            f"{len(sem['exertion_relation_no_chest'])} 例。後果：(a) 只靠 T0-REST-NEW 判 T0 的無胸部症狀病人 "
            f"{ids('a_t0_only_by_rest_new_no_chest')}，這些例子的 (a) 結果（不論算 over 或 exact）都受這個假象影響。"
            "根源是 `data/synth/synth_prompts.yaml` 生成器說明沒有交代這些 slot 只用於胸部症狀；v2 生成時要修。\n")


def render_report(rows, m: dict, meta: dict, adj: list, costs: dict, llm_info: dict, day: str,
                  sem: dict[str, list[str]] | None = None) -> str:
    L = [f"# 實驗 1：獨立合成病人驗證集評估 — {day}", "",
         f"- rules_version {rules_version()}；情境檔 `{meta['scenarios']}`（{len(rows)} 例）；參考標註 `{meta['reference']}`；"
         f"LLM 病人報告 `{meta['llm_json']}`", "", LIMITS + (semantics_limit(sem) if sem else "")]
    n_agree = sum(r["ref_agree"] is not None for r in rows)
    agr = m["agree"]
    L += ["## 結論摘要（數字）", "",
          f"- 參考標註一致（tier 與 Hard stop 都相同）：{fmt_prop(prop(n_agree, len(rows)))}；只看 tier 一致：{_xn(agr['tier_only'])}。",
          ""]
    hdr = ["層", "n", "HS 敏感度", "Under-triage", "其中系統為 T9（依備援換算才較不急）", "Over-triage", "Exact", "T9 比例",
           "急診負擔（參考 T1–T4 卻 HS／T0）", "平均題數"]
    for refkey, title in (("ref_agree", "參考一致子集（主分析）"), ("ref_cons", "全部 150 例（保守參考＝兩位標註者中較急者）")):
        L.append(f"### {title}")
        L.append("")
        _table(L, hdr, [[LAYERS[l], m[refkey][l]["n"], fmt_prop(m[refkey][l]["hs_sensitivity"]), fmt_prop(m[refkey][l]["under"]),
                         _xn(m[refkey][l]["under_via_t9"]), fmt_prop(m[refkey][l]["over"]), fmt_prop(m[refkey][l]["exact"]), fmt_prop(m[refkey][l]["t9"]),
                         fmt_prop(m[refkey][l]["ed_burden"]), m[refkey][l]["mean_questions"] or "—"] for l in LAYERS])
    L += [f"- 待 Clinical Owner 裁定：{len(adj)} 例（標註者不一致 {sum(r['ref_agree'] is None for r in adj)} 例；"
          f"系統任一層比任一位標註者不急 {sum(any(s.startswith('系統') for s in r['reasons']) for r in adj)} 例）。", ""]

    L += ["## 資料", "", f"- 生成：{meta['gen']['generated_by']['model']}（{', '.join(meta['gen']['generated_by']['model_versions'])}），"
          f"effort {meta['gen']['generated_by']['reasoning_effort']}，prompt {meta['gen']['generated_by']['prompt_version']}。", ""]
    cat = Counter(r["category"] for r in rows)
    per = Counter(r["persona_style"] for r in rows)
    L.append("類別 × 人物風格（實際分布）：")
    L.append("")
    pers = sorted(per)
    _table(L, ["category"] + pers + ["合計"],
           [[c] + [sum(1 for r in rows if r["category"] == c and r["persona_style"] == p) for p in pers] + [cat[c]] for c in cat]
           + [["合計"] + [per[p] for p in pers] + [len(rows)]])
    s = meta["gen"]["similarity"]
    L += [f"- 與既有 119 個 case 的開場白（{s['existing_openings']} 種）相似度：{s['metric']}，門檻 {s['threshold']}；"
          f"重生 {s['regenerated_cases']} 例（共 {s['regen_attempts']} 次）；重生上限後仍太像 {len(s['still_similar_after_max_regen'])} 例；"
          f"最高重疊係數 {s['max_overlap_vs_existing']}、平均最高 {s['mean_max_overlap_vs_existing']}、最高 Jaccard {s['max_jaccard_vs_existing']}；"
          f"新 case 彼此超過門檻 {len(s['new_vs_new_pairs_over_threshold'])} 對。",
          f"- 開場白抽取值與事實清單不一致（影響 (b)(c)：該 slot 已「已知」就不會再問）：{sum(bool(r['extractor_conflicts']) for r in rows)} 例；"
          f"依 slot：{dict(Counter(k for r in rows for k in r['extractor_conflicts']).most_common())}。", ""]

    L += ["## 參考標註", "",
          f"- 一致 {n_agree}/{len(rows)}；Hard stop 一致 {_xn(agr['hs'])}；hard_stop=true 但 tier≠T0 的原始輸出 {agr['raw_inconsistent']} 筆（一律視為 T0）。",
          f"- 信心分布：Opus {agr['conf_opus']}；gpt {agr['conf_gpt']}。", "", "Opus（列）× gpt（欄）："]
    L.append("")
    labs = ["HS", "T0", "T1", "T2", "T3", "T4", "T9"]

    def lab(o):
        return "HS" if o["hs"] else f"T{o['tier']}"
    _table(L, ["Opus＼gpt"] + labs, [[a] + [sum(1 for r in rows if r["ref_opus"] and r["ref_gpt"] and lab(r["ref_opus"]) == a
                                               and lab(r["ref_gpt"]) == b) for b in labs] for a in labs])

    L.append("## 依類別與人物風格（參考一致子集；格式 x/n）")
    L.append("")
    for group in ("category", "persona_style"):
        for l in LAYERS:
            L.append(f"### {LAYERS[l]} × {group}")
            L.append("")
            body = []
            for g in sorted({r[group] for r in rows}):
                sub = [r for r in rows if r[group] == g]
                mm = metrics(sub, l, "ref_agree")
                mc = metrics(sub, l, "ref_cons")
                body.append([g, f"{mm['n']}（全部 {mc['n']}）", _xn(mm["hs_sensitivity"]), _xn(mm["under"]), _xn(mm["over"]),
                             _xn(mm["exact"]), _xn(mm["t9"]), f"{_xn(mc['under'])}", mm["mean_questions"] or "—"])
            _table(L, [group, "n 一致", "HS 敏感度", "Under", "Over", "Exact", "T9", "Under（全部，保守參考）", "平均題數"], body)

    L += ["## Under-triage 明細（系統比參考不急）", "",
          "急迫度：HS=-1、T0–T4=0–4、T9 依備援換算。「保守參考」= 兩位標註者中較急者。"
          "本表依保守參考急迫度與落差自動排序，沒有區分機制；機制分類與人工嚴重度排序見「主要發現」。", ""]
    und = [r for r in rows if r["ref_cons"] and any(r[l] and r[l]["urg"] > r["ref_cons"]["urg"] for l in LAYERS)]
    und.sort(key=severity_key)
    _table(L, ["case", "category", "persona", "參考一致？", "Opus", "gpt", "(a)", "(b)", "(c)", "(a)(b)(c) 哪幾層低估"],
           [[r["id"], r["category"], r["persona_style"], "是" if r["ref_agree"] else "否", fmt_ref(r["ref_opus"]),
             fmt_ref(r["ref_gpt"]), fmt_out(r["a"]), fmt_out(r["b"]), fmt_out(r["c"]),
             "".join(l for l in LAYERS if r[l] and r[l]["urg"] > r["ref_cons"]["urg"])] for r in und])
    L += ["## 參考非緊急卻被叫去急診（HS／T0）明細", ""]
    ed = [r for r in rows if r["ref_cons"] and not r["ref_cons"]["hs"] and r["ref_cons"]["tier"] in (1, 2, 3, 4)
          and any(r[l] and (r[l]["hs"] or r[l]["tier"] == 0) for l in LAYERS)]
    _table(L, ["case", "category", "Opus", "gpt", "(a)", "(b)", "(c)"],
           [[r["id"], r["category"], fmt_ref(r["ref_opus"]), fmt_ref(r["ref_gpt"]), fmt_out(r["a"]), fmt_out(r["b"]), fmt_out(r["c"])]
            for r in ed])

    L += ["## 層間差異", ""]
    for x, y in (("a", "b"), ("b", "c"), ("a", "c")):
        diff = [r["id"] for r in rows if r[x] and r[y] and (r[x]["tier"], r[x]["hs"]) != (r[y]["tier"], r[y]["hs"])]
        L.append(f"- {LAYERS[x]} vs {LAYERS[y]} 結果不同：{len(diff)} 例 {diff}")
    for l in ("b", "c"):
        L.append(f"- {LAYERS[l]} 結束原因：{dict(Counter(r[l]['stop'] for r in rows if r[l]))}")
    L += ["", "## (c) LLM 病人忠實度（與事實清單比對，sim.run_llm_eval）", "",
          f"- 模型 {llm_info.get('model')}（{', '.join(llm_info.get('model_versions', []))}），effort {llm_info.get('effort')}，"
          f"prompt {llm_info.get('prompt_version')}；偏差紀錄 {llm_info.get('n_deviations')} 筆，分布 {llm_info.get('deviation_kinds')}"
          f"＝{llm_info.get('n_deviation_cases')} 例、{llm_info.get('n_deviation_questions')} 題"
          f"（原題 {llm_info.get('n_deviation_original')} 筆＋複誦確認時重複同一答案 {llm_info.get('n_deviation_confirm')} 筆）；"
          f"執行錯誤 {len(llm_info.get('errors', []))}。", ""]

    L += ["## 花費（依 repo PRICES 牌價估算，以帳單為準）", ""]
    _table(L, ["項目", "US$"], [[k, f"{v:.4f}"] for k, v in costs.items()])
    L += ["## 執行錯誤與失敗", ""]
    errs = [(r["id"], k, v) for r in rows for k, v in r["errors"].items()]
    L.append("（無）" if not errs else "\n".join(f"- {a} {b}：{c}" for a, b, c in errs))
    L += ["", f"- (a)(b)(c) 跑完：{sum(r['a'] is not None for r in rows)}／{sum(r['b'] is not None for r in rows)}／"
          f"{sum(r['c'] is not None for r in rows)}（共 {len(rows)}）", ""]
    return "\n".join(L)


def render_adjudication_md(adj: list[dict[str, Any]], day: str) -> str:
    L = [f"# Clinical Owner 裁定表 — 實驗 1 合成病人驗證集（{day}）", "",
         "- 收錄：兩位 LLM 標註者（Opus 5.5、gpt-6.1-sol）tier 或 Hard stop 不一致，或系統任一層（(a) 全資訊規則、(b) Scripted 病人、"
         "(c) Opus LLM 病人）比任一位標註者不急的案例。",
         "- 標註者的分級只是 LLM 臨床判斷，不是 truth；請在每例最後的「Clinical Owner 裁定」填寫。同內容的試算表：同名 .xlsx。",
         "- 全為虛構合成資料。", "", f"共 {len(adj)} 例。", ""]
    for r in adj:
        c = r["c"]
        L += [f"## {r['id']}（{r['category']}／{r['persona_style']}）", "",
              f"- 列入原因：{'；'.join(r['reasons'])}",
              f"- 開場白：「{r['opening_zh']}」", "", "事實清單：", "", "```", r["sheet"], "```", "",
              f"- Opus 5.5：{fmt_ref(r['ref_opus'])}——{(r['ref_opus'] or {}).get('rationale_zh', '')}",
              f"- gpt-6.1-sol：{fmt_ref(r['ref_gpt'])}——{(r['ref_gpt'] or {}).get('rationale_zh', '')}",
              f"- 系統：(a) {fmt_out(r['a'])}；(b) {fmt_out(r['b'])}（{(r['b'] or {}).get('n_q')} 題，{(r['b'] or {}).get('stop')}）；"
              f"(c) {fmt_out(c)}（{c['n_q'] if c else '—'} 題，{c['stop'] if c else '—'}）",
              "- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿", ""]
    return "\n".join(L)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    both = [r for r in rows if r["ref_opus"] and r["ref_gpt"]]
    m: dict[str, Any] = {k: {l: metrics(rows, l, k) for l in LAYERS} for k in ("ref_agree", "ref_cons")}
    m["vs_annotator"] = {n: {l: metrics(rows, l, f"ref_{n}") for l in LAYERS} for n in ANN}
    m["agree"] = {"n": len(rows), "both_labelled": len(both),
                  "tier_and_hs": prop(sum(r["ref_agree"] is not None for r in rows), len(rows)),
                  "tier_only": prop(sum(r["ref_opus"]["tier"] == r["ref_gpt"]["tier"] for r in both), len(both)),
                  "hs": prop(sum(r["ref_opus"]["hs"] == r["ref_gpt"]["hs"] for r in both), len(both)),
                  "raw_inconsistent": sum(bool(r[k] and r[k]["raw_inconsistent"]) for r in rows for k in ("ref_opus", "ref_gpt")),
                  "conf_opus": dict(Counter(r["ref_opus"]["confidence"] for r in rows if r["ref_opus"])),
                  "conf_gpt": dict(Counter(r["ref_gpt"]["confidence"] for r in rows if r["ref_gpt"]))}
    return m


def _rel(p: str) -> str:
    q = Path(p).resolve()
    return str(q.relative_to(REPO_ROOT)) if q.is_relative_to(REPO_ROOT) else str(q)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    ap.add_argument("--llm-json", required=True, help="sim.run_llm_eval --scenarios 產出的 .json（同名 _transcripts.json 會一起讀）")
    ap.add_argument("--pilot-cost-usd", type=float, default=0.0,
                    help="試跑（估算用）已花費用＝試跑三個輸出檔（生成 YAML、標註 JSON、run_llm_eval JSON）的 est_cost_usd 加總")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    gen = load_synth(Path(args.scenarios))
    reference = json.loads(Path(args.reference).read_text(encoding="utf-8"))
    llm = json.loads(Path(args.llm_json).read_text(encoding="utf-8"))
    transcripts = json.loads(Path(args.llm_json.removesuffix(".json") + "_transcripts.json").read_text(encoding="utf-8"))
    rows = build_rows(gen["scenarios"], reference, transcripts)
    m = summarize(rows)
    adj = adjudication_rows(rows)
    adj.sort(key=lambda r: (not any(x.startswith("系統") for x in r["reasons"]), severity_key(r), r["id"]))   # 系統低估在前、最急的在前
    costs = {"生成（gpt-6.1-sol）": gen["cost"]["est_cost_usd"],
             **{f"參考標註（{ANN[n]}）": v for n, v in reference["_meta"]["est_cost_usd"].items()},
             "LLM 病人（Opus 5.5）": llm["usage"]["est_cost_usd"], "試跑（3 例：生成＋兩位標註＋LLM 病人；--pilot-cost-usd 命令列輸入，試跑輸出不在 repo）": args.pilot_cost_usd}
    costs["合計"] = round(sum(costs.values()), 4)
    from .llm_patient import _prompt_cfg
    llm_info = {"model": llm["model"], "model_versions": llm["model_versions"], "effort": llm["effort"],
                "prompt_version": _prompt_cfg()["prompt_version"], "n_deviations": len(llm["deviations"]),
                "n_deviation_cases": len({d["case_id"] for d in llm["deviations"]}),
                "n_deviation_questions": len({(d["case_id"], d["question_id"]) for d in llm["deviations"]}),
                "n_deviation_original": sum(not d.get("confirm") for d in llm["deviations"]),
                "n_deviation_confirm": sum(bool(d.get("confirm")) for d in llm["deviations"]),
                "deviation_kinds": dict(Counter(d["kind"] for d in llm["deviations"])), "errors": llm["errors"]}
    meta = {"scenarios": _rel(args.scenarios), "reference": _rel(args.reference), "llm_json": _rel(args.llm_json), "gen": gen}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"synth_eval_{args.date}"
    sem = slot_semantics(gen["scenarios"])
    (out / f"{stem}.md").write_text(render_report(rows, m, meta, adj, costs, llm_info, args.date, sem), encoding="utf-8")
    slim = [{k: v for k, v in r.items() if k != "sheet"} for r in rows]
    (out / f"{stem}.json").write_text(json.dumps(
        {"date": args.date, "rules_version": rules_version(), "inputs": {k: meta[k] for k in ("scenarios", "reference", "llm_json")},
         "limitations": LIMITS + semantics_limit(sem), "slot_semantics": sem, "metrics": m, "costs_usd": costs, "llm_patient": llm_info,
         "adjudication_case_ids": [r["id"] for r in adj], "cases": slim}, ensure_ascii=False, indent=2), encoding="utf-8")
    adj_stem = f"synth_adjudication_{args.date}"
    (out / f"{adj_stem}.md").write_text(render_adjudication_md(adj, args.date), encoding="utf-8")
    notes = [["項目", "說明"],
             ["資料", "全為虛構合成資料（LLM 生成）；標註者分級為 LLM 暫定判斷，不是 truth"],
             ["收錄", "標註者不一致，或系統任一層比任一位標註者不急"],
             ["系統 (a)", "全資訊規則：病人知道的全部事實一次寫入規則引擎"],
             ["系統 (b)", "Scripted 病人對話（clean）"], ["系統 (c)", "Opus 5.5 LLM 病人對話（prompt 0.3、medium）"],
             ["T9（備援 Tn）", "Tier 9＝資訊不足轉護理師；括號為護理師不可得時的預設等級"],
             ["裁定欄", "請填分級（T0–T4／T9）、Hard stop（Y／N）與備註"]]
    write_xlsx(out / f"{adj_stem}.xlsx", [("裁定表", adjudication_table(adj), ADJ_WIDTHS), ("說明", notes, [16, 80])])
    print(json.dumps({"n": len(rows), "agree": m["agree"]["tier_and_hs"], "adjudication": len(adj), "costs": costs,
                      **{f"{k}_{l}": {x: m[k][l][x]["x"] for x in ("under", "over", "exact", "t9")} | {"hs_miss": m[k][l]["hs_miss"]}
                         for k in ("ref_agree", "ref_cons") for l in LAYERS}}, ensure_ascii=False))
    for p in (f"{stem}.md", f"{stem}.json", f"{adj_stem}.md", f"{adj_stem}.xlsx"):
        print(f"→ {out / p}")


if __name__ == "__main__":
    main()
