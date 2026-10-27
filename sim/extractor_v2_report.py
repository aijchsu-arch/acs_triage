"""抽取器 v2 報告（D-52 第 3 項）：組 reports/extractor_v2_<date>.{md,json}。不打 API，只讀各階段輸出。

python -m sim.extractor_v2_report [--inputs reports/extractor_v2_2026-10-27_inputs] [--out reports/]

- 輸入全部在 repo 內的 reports/extractor_v2_2026-10-27_inputs/（預設），重跑即逐位重產：
  stage_a_replay.json（sim.llm_extract_v2 replay 的輸出，gpt／gemma × ref／phone＋複誦回答）、
  closed_dev_*.json（sim.closed_loop run 的指標與逐例摘要；*.dev15 為修正前；*_limit3 為 3 例試跑）、
  ambiguity.json（模糊說法與表末兩列）、iterations.json、conclusions.md（人工撰寫，原樣放在限制之後）、
  extra.json（費用、改動檔案、重現指令、§4.1c 觀察等人工整理欄位）、status.json（凍結紀錄或目前 hash）。
- v1 對照：reports/e2e_llm_extractors_2026-10-26.json（同一份開發集逐字稿與 Whisper 轉寫）。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from acs_triage.loaders import REPO_ROOT, rules_version

V1 = REPO_ROOT / "reports" / "e2e_llm_extractors_2026-10-26.json"
LABEL = {"gpt": "gpt-6.1-sol", "gemma": "gemma-4-26b-a4b-it-mlx", "structured": "結構化值（對照）"}
COND = {"ref": "逐字稿原文", "phone": "電話語音＋Whisper"}

LIMITS = [
    "**合成病人**：病人回答由 Opus 5.5 依情境事實（hidden sheet）生成，句子比真實病人完整、少答非所問；正確答案＝情境事實（開發集為單一裁定者 truth）。這是一致性檢查，不是準確度，不能外推臨床表現。",
    "**合成語音或沒有語音**：階段 A 的 phone 條件是 macOS `say` 合成標準國語＋模擬電話線路＋本機 Whisper（D-49），沒有台語、高齡口音與環境噪音，是樂觀上限；階段 B 閉環完全沒有語音（病人文字直接進抽取器），等於 STT 完美。",
    "**LLM 參考標註**：保留集的「對照答案」是 Opus 5.5 與 gpt-6.1-sol 的獨立標註（暫定；Clinical Owner 尚在裁定 48 例），不是 truth；主分析用兩位標註者一致的子集。",
    "**雲端模型不可用於真實資料**：gpt-6.1-sol 只是「抽取能力上限」參考；真實病人資料不得送外部 API（D-10）。院內可部署的候選是本機模型（Gemma）。全部資料為合成資料。",
    "**病人回答重用（配對設計）**：閉環的病人以「對話前綴快取」包一層：同一 case、同一串客服問句（含複誦句）就重用已取得的 Opus 回答，種子是結構化值閉環的逐字稿（開發集 10-23、保留集 10-26），gpt 與 Gemma 兩個 arm 共用。問句序列相同時病人看到的對話完全相同，重用的是同一個樣本（三個 arm 之間是配對比較，不是獨立重抽）；序列一分岔，之後都是新的 API 呼叫。",
    "**開發集調整過、保留集只跑一次**：抽取提示只依開發集逐字稿調整（迭代紀錄見 §3.4）；凍結後才跑保留集，結果出來後未再修改提示。開發集數字因此偏樂觀，保留集才是凍結後的估計，但樣本小（參考一致子集的 Hard stop 只有數十例），信賴區間寬。",
]
LIMIT_UNFROZEN = ("**開發集調整過；保留集尚未執行**：抽取提示只依開發集逐字稿調整（迭代紀錄見 §3.4），本報告的數字全部來自開發集，"
                  "因此偏樂觀；提示尚未凍結，保留集（data/synth/）沒有執行、也沒有看任何保留集抽取結果。")


def _j(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _n(x: Any) -> int:
    return len(x) if isinstance(x, list) else int(x or 0)


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.1f}%"


def v1_cell(v1: dict[str, Any], key: str) -> dict[str, Any]:
    c = v1["cells"][key]
    m = c["metrics"]
    return {"hs_miss": len(m["hard_stop"]["miss"]), "hs_truth": m["hard_stop"]["truth"], "premature": len(c["premature"]),
            "false_hs": len(m["hard_stop"]["false_alarm"]), "under": len(m["under_triage"]["cases"]),
            "over": len(m["over_triage"]["cases"]), "exact": m["exact_rate"], "abstain_fp": len(m["abstention"]["fp"]),
            "rf_yes_missed": len(c["rf_yes_missed"]), "slot_correct": c["slot_by_priority"]["all"].get("correct", 0),
            "slot_n": c["slot_by_priority"]["all"]["n"], "rf_correct": c["slot_by_priority"]["redflag"].get("correct", 0),
            "rf_n": c["slot_by_priority"]["redflag"]["n"], "hs_miss_cases": m["hard_stop"]["miss"],
            "false_hs_cases": m["hard_stop"]["false_alarm"], "premature_cases": c["premature"]}


def v2_cell(rep: dict[str, Any], key: str) -> dict[str, Any]:
    c = rep["cells"][key]
    return {**{k: c[k] for k in ("hs_miss", "hs_truth", "premature", "false_hs", "under", "over", "exact", "abstain_fp",
                                 "rf_yes_missed", "hs_miss_cases", "false_hs_cases", "premature_cases")},
            "slot_correct": c["slot_all"].get("correct", 0), "slot_n": c["slot_all"]["n"],
            "rf_correct": c["slot_redflag"].get("correct", 0), "rf_n": c["slot_redflag"]["n"]}


def render(d: dict[str, Any], conclusions: str) -> str:
    limits = LIMITS if d["freeze"].get("frozen_at") else [*LIMITS[:-1], LIMIT_UNFROZEN]
    d["limitations"] = limits
    L = [f"# 抽取器 v2 與閉環模擬（D-52 第 3 項）— {d['date']}", "", "> **限制（先讀）**", ">"]
    L += [f"> {i}. {t}" for i, t in enumerate(limits, 1)]
    L += ["", "## 1. 結論（人工撰寫，依本報告數字）", "", conclusions.strip(), ""]
    fz = d["freeze"]
    if fz.get("frozen_at"):
        L += ["## 2. 凍結紀錄與保留集只跑一次的證據", "",
              f"- 凍結提示：`data/extractor_prompts_v2.yaml` prompts_version **{fz['prompts_version']}**",
              f"  - 提示檔 sha256：`{fz['prompt_file_sha256']}`",
              f"  - 實際送出的提示全文（兩種 system＋三種 user 模板）sha256：`{fz['rendered_sha256']}`",
              *[f"  - `{f}` sha256：`{h}`" for f, h in fz["files"].items()],
              f"  - 凍結時間：{fz['frozen_at']}（`sim.closed_loop freeze`；凍結紀錄存在就拒絕再凍結）",
              "- 保留集閉環（`sim.closed_loop run --set holdout`：檢查上列前三檔的 sha256 與凍結紀錄相同才執行；同一抽取器的輸出已存在就拒跑）："]
        for arm in ("gpt", "gemma"):
            h = d["closed"].get(f"holdout_{arm}")
            if h:
                same = all(h["meta"]["file_sha256"][f] == fz["files"][f] for f in fz["files"] if f != "sim/closed_loop.py")
                L.append(f"  - {LABEL[arm]}：開始 {h['meta']['started_at']}、結束 {h['meta']['finished_at']}（執行時 sha256 與凍結紀錄相符：{same}）")
    else:
        L += ["## 2. 凍結狀態", "", f"- **尚未凍結**：{fz['note']}",
              f"- 目前（最後一版開發集調整）prompts_version **{fz['prompts_version']}**；提示檔 sha256 `{fz['prompt_file_sha256']}`；"
              f"送出提示全文 sha256 `{fz['rendered_sha256']}`；" + "；".join(f"`{f}` `{h[:16]}…`" for f, h in fz["files"].items()),
              "- 保留集：**沒有執行任何保留集閉環、沒有看任何保留集抽取結果**（`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑）。"]
    L.append("")

    # ---------------- 階段 A
    L += ["## 3. 階段 A：抽取器改進（開發集重放；調整過）", "",
          "重放沿用 `sim.e2e_llm` 的指標（`run_cell`）：對話照 Opus 10-20 逐字稿固定、不補問；Hard-stop miss 含 premature。v1＝"
          "`reports/e2e_llm_extractors_2026-10-26.md`（回答句只抽被問那題；開場白 0.1）。v2 寫入方式：被問那題抽到值才寫入（未知不寫、保留原值）；"
          "順口提到的 slot 與閉環 runner 共用 `_write_mentions`：補未知的 slot，已知值只在紅旗是非題「有」或 confirm_back_severity 較嚴重時覆蓋，"
          "其他不同保留已知值（conflict）。閉環 runner 與此不同的一點：被問那題抽成未知時照既有 runner 寫入未知並標記已問（之後順口提到仍可補上）。", "",
          "| 抽取器 | 文字 | 版本 | Hard-stop miss（含 premature） | premature | 假 Hard stop | under | over | exact | abstention FP | 紅旗題「有」漏抽 | 被問那題正確 | 紅旗題正確 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for ext in ("gpt", "gemma"):
        for cond in ("ref", "phone"):
            for ver, c in (("v1", d["stage_a"]["v1"].get(f"{ext}/{cond}")), ("v2", d["stage_a"]["v2"].get(f"{ext}/{cond}"))):
                if c is None:
                    continue
                L.append(f"| {LABEL[ext]} | {COND[cond]} | {ver} | **{c['hs_miss']}/{c['hs_truth']}** | {c['premature']} | {c['false_hs']} | "
                         f"{c['under']} | {c['over']} | {_pct(c['exact'])} | {c['abstain_fp']} | {c['rf_yes_missed']} | "
                         f"{c['slot_correct']}/{c['slot_n']} | {c['rf_correct']}/{c['rf_n']} |")
    L += ["", "### 3.1 改善幅度（v2 − v1）", "", "| 抽取器 | 文字 | Hard-stop miss | 假 Hard stop | over | abstention FP | exact |", "|---|---|---|---|---|---|---|"]
    for ext in ("gpt", "gemma"):
        for cond in ("ref", "phone"):
            a, b = d["stage_a"]["v1"].get(f"{ext}/{cond}"), d["stage_a"]["v2"].get(f"{ext}/{cond}")
            if a and b:
                L.append(f"| {LABEL[ext]} | {COND[cond]} | {b['hs_miss'] - a['hs_miss']:+d} | {b['false_hs'] - a['false_hs']:+d} | "
                         f"{b['over'] - a['over']:+d} | {b['abstain_fp'] - a['abstain_fp']:+d} | {100 * (b['exact'] - a['exact']):+.1f} pt |")
    L += ["", "### 3.2 Hard-stop miss 與假 Hard stop 明細（v2）", ""]
    for k, c in d["stage_a"]["v2"].items():
        L.append(f"- {k}：miss {c['hs_miss_cases'] or '（無）'}；premature {c['premature_cases'] or '（無）'}；假 Hard stop {c['false_hs_cases'] or '（無）'}")
    L += ["", "### 3.3 複誦回答的解讀（開發集 10-23 逐字稿的複誦回答＋人工探針）", "",
          "題目原文與複誦句（`confirm_prompt`）一起當 context；正確答案＝逐字稿記下的確認值（10-23 的複誦全是「對」類回答）；"
          "探針 15 句含「不是，有啊」「不是。」等更正句（`sim/llm_extract_v2.py` CONFIRM_PROBES）。", "",
          "| 抽取器 | 開發集複誦回答 | 探針 |", "|---|---|---|"]
    for ext, c in d["stage_a"]["confirm"].items():
        g = c["dev_grades"]
        ok = sum(v for k, v in g.items() if k in ("correct", "unknown_equiv", "speechless"))
        L.append(f"| {LABEL[ext]} | {ok}/{sum(g.values())}（{g}） | {c['probe_ok']}/{c['probe_n']} |")
    L += ["", "### 3.4 迭代紀錄（全部只用開發集；Gemma 本機，不計費）", "", "| 版本 | 改了什麼 | 開發集結果 |", "|---|---|---|"]
    for it in d["iterations"]:
        L.append(f"| {it['version']} | {it['change']} | {it['eval']} |")
    L += ["", "### 3.5 延遲與費用（階段 A）", ""]
    for ext, s in d["stage_a"]["llm"].items():
        lat = s["latency"]
        L.append(f"- {LABEL[ext]}：呼叫 {s['n_calls']}、失敗 {s['n_failed']}；延遲中位數／p95：全部 {_sec(lat['all'])}、開場白 {_sec(lat['opening'])}、"
                 f"回答 {_sec(lat['turn'])}（並行 {s['workers']}）；程式保護觸發 {s['guards']}（費用見 §6）")

    # ---------------- 階段 B
    L += ["", "## 4. 階段 B：閉環模擬（Opus 病人 prompt 0.3、effort medium）", ""]
    sb = d.get("stage_b_status")
    if sb:
        L += [sb["summary"], ""]
        if sb.get("estimate_table"):
            L += ["| 項目 | 估算（USD） | 依據 |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in sb["estimate_table"]] + [""]
        for t in sb.get("notes", []):
            L.append(f"- {t}")
        L.append("")
    L += ["### 4.1 開發集 119 例（對 truth；提示依開發集調整過）", "",
          "| arm | HS 敏感度 | HS miss（含 premature） | premature | 假 Hard stop | under | over | exact | T9 | 平均題數 | 複誦（每通） | 執行錯誤 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm in ("structured", "gpt@dev15", "gemma@dev15", "gpt", "gemma"):
        r = d["closed"].get(f"dev_{arm}")
        if not r:
            continue
        m = r["metrics"]
        L.append(f"| {_lab(arm, r)} | {m['hs_hit']}/{m['hs_truth']}（{_pct(m['hs_sensitivity'])}） | {_n(m['hs_miss'])} | {_n(m['premature'])} | "
                 f"{_n(m['false_hs'])} | {_n(m['under'])} | {_n(m['over'])} | {_pct(m['exact'])} | {m['t9']} | {m['mean_questions']:.2f} | "
                 f"{m['confirms']}（{m['confirms_per_call']:.2f}） | {len(m['errors'])} |")
    L += ["", "under／over 不含 T9（T9 另計）；premature＝Hard stop 只靠抽錯的值成立（把當時已知的 slot 換回病人真正知道的事實後不再是 Hard stop），計為 miss。", ""]
    for arm in ("gpt@dev15", "gemma@dev15", "gpt", "gemma"):
        r = d["closed"].get(f"dev_{arm}")
        if r:
            m = r["metrics"]
            L.append(f"- {_lab(arm, r)}：HS miss {m['hs_miss'] or '（無）'}；premature {m['premature'] or '（無）'}；假 Hard stop {m['false_hs'] or '（無）'}；"
                     f"under {m['under'] or '（無）'}；over {m['over'] or '（無）'}")
    L += ["", "### 4.1b 每例 Hard stop 題次（truth 為 Hard stop 的開發集 case；最終版）", "",
          "題次＝觸發 Hard stop 時已問的題數（0＝開場白；不含複誦）；—＝沒有觸發。", "",
          "| case | truth RF | 結構化值 | gpt | Gemma | 比結構化值晚（gpt／Gemma） |", "|---|---|---|---|---|---|"]
    runs = {a: {c["case_id"]: c for c in d["closed"][f"dev_{a}"]["cases"]} for a in ("structured", "gpt", "gemma") if f"dev_{a}" in d["closed"]}
    if "structured" in runs:
        def turn(a: str, cid: str) -> Any:
            c = runs.get(a, {}).get(cid)
            return None if c is None or not c["final"]["hs"] else c["hard_stop_turn"]
        for cid in sorted(runs["structured"], key=lambda x: x):
            if not d["truth_hs"].get(cid):
                continue
            t0, tg, tm = turn("structured", cid), turn("gpt", cid), turn("gemma", cid)
            late = "／".join("—" if (x is None or t0 is None) else f"{x - t0:+d}" for x in (tg, tm))
            L.append(f"| {cid} | {d['truth_hs'][cid]} | {'—' if t0 is None else t0} | {'—' if tg is None else tg} | {'—' if tm is None else tm} | {late} |")
    L += ["", "### 4.1c 順口提到的值與已知值不同（conflict：保留已知值，最終版）", "",
          "規則：順口提到的值補未知的 slot；D-50 範圍（紅旗題＋stt_critical_questions）的未知 slot 只收「寫入後變成 Hard stop」或最嚴重一級，"
          "其他較不嚴重的值：該題沒問過 → 不收（d50_not_most_severe）但暫存，之後直接問到、答案仍未知時以暫存值當解讀值 D-50 複誦一次；"
          "問過而目前未知 → 立刻對該題 D-50 複誦一次（以順口值當解讀值，計入複誦）；這兩種複誦在目前已是 Hard stop、或寫入該值（連同同一句的其他值）後會變 Hard stop 時都不做，"
          "直接寫入並走 Hard stop（D-50 不延誤送醫）；"
          "已知值只在三種情況被覆蓋——紅旗是非題的「有」、`confirm_back_severity` 已核定順序中較嚴重的值、寫入後由非 Hard stop 變成 Hard stop；"
          "其他不同一律保留已知值（conflict）。下列為全部沒採用的順口值。", ""]
    for a in ("gpt", "gemma"):
        r = d["closed"].get(f"dev_{a}")
        if not r or "mention_conflicts" not in r:
            continue
        cfs = r["mention_conflicts"]
        L.append(f"- {LABEL[a]}：順口值觸發的複誦 {len(r.get('mention_confirms', []))} 次；沒採用 {len(cfs)} 次（{dict(Counter(c.get('kind', 'conflict') for c in cfs)) or '—'}）" + ("" if not cfs else "：" + "；".join(
            f"{c['case_id']} 第 {c['turn']} 題 {c['question_id']}（{c.get('kind', 'conflict')}）：{c['slot']} 已知 {c['known']}、順口 {c['mention']}「{c['utterance_zh']}」" for c in cfs)))
    L += [x for t in d.get("observations_41c", []) for x in ("", f"觀察：{t}")]
    L += ["", "### 4.2 保留集 150 例（對 LLM 參考標註；凍結後一次）", ""]
    if not any(k.startswith("holdout_") for k in d["closed"]):
        L += ["**未執行**（提示未凍結；`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑）。", ""]
    for rk, title in (("ref_agree", "參考一致子集（主分析）"), ("ref_cons", "全部（保守參考＝兩位標註者中較急者）")):
        if not any(k.startswith("holdout_") for k in d["closed"]):
            break
        L += [f"**{title}**", "", "| arm | n | HS 敏感度（95% CI） | HS miss（含 premature） | premature | 假 Hard stop | under（其中 T9） | over | exact | T9 | 平均題數 | 複誦 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for arm in ("structured", "gpt", "gemma"):
            r = d["closed"].get(f"holdout_{arm}")
            if not r:
                continue
            m = r["metrics"][rk]
            hs = m["hs_sensitivity"]
            ci = f"{100 * hs['ci95'][0]:.1f}–{100 * hs['ci95'][1]:.1f}%" if hs.get("ci95") else "—"
            L.append(f"| {LABEL[arm]} | {m['n']} | {hs['x']}/{hs['n']}（{_pct(hs['p'])}；{ci}） | {len(m['hs_miss'])} | {len(m['premature'])} | "
                     f"{len(m['false_hs'])} | {m['under']['x']}（{m['under_via_t9']['x']}） | {m['over']['x']} | {_pct(m['exact']['p'])} | "
                     f"{m['t9']['x']} | {m['mean_questions']} | {m['confirms']} |")
        L.append("")
        for arm in ("structured", "gpt", "gemma"):
            r = d["closed"].get(f"holdout_{arm}")
            if r:
                m = r["metrics"][rk]
                L.append(f"- {LABEL[arm]}：HS miss {m['hs_miss'] or '（無）'}；premature {m['premature'] or '（無）'}；假 Hard stop {m['false_hs'] or '（無）'}；"
                         f"under {m['under_cases'] or '（無）'}")
        L.append("")
    if any(k.startswith("holdout_") for k in d["closed"]):
        L += ["急迫度比較同 `sim.synth_eval`：Hard stop＝-1、T0–T4；T9 依 tier9_fallback 換算（under 含「系統 T9、備援較不急」者，括號內）。", ""]
    ext_runs = {k: r for k, r in d["closed"].items() if r.get("extraction") is not None}
    L += ["### 4.3 閉環中的抽取（被問那題確認前的值 vs 病人模擬的結構化值）", ""]
    if not ext_runs:
        L += ["（全量閉環未執行；3 例試跑見上。）", ""]
    else:
        L += ["| 資料 | arm | 被問那題 | 複誦回答 | 紅旗題「有」沒抽成「有」 | 病人呼叫：新／重用 | 抽取器費用 | 送進抽取器前被轉換的句子 |", "|---|---|---|---|---|---|---|---|"]
    for key, r in ext_runs.items():
        e, pu, eu = r["extraction"], r["patient_usage"], r["extractor_usage"]
        L.append(f"| {key.split('_')[0]} | {_lab(key.split('_', 1)[1], r)} | {e['asked']} | {e['confirm_reply']} | {len(e['rf_yes_missed'])} | "
                 f"{pu['live_calls']}／{pu['cached_calls']}（{pu['sources']}） | US${eu.get('cost_this_run_usd', eu['cost_total_usd']):.4f} | {eu['tw_changed']} |")
    L += ["", "## 5. 模糊說法清單（交 Clinical Owner 裁定；v2 一律留未知、讓系統追問）", "",
          f"裁定表：`reports/extractor_v2_ambiguous_{d['date']}.md`／`.xlsx`（含開發集原句、可能的歸類、提示是否已寫入例句、留空的裁定欄）。"
          "表末兩列：第 15 列 Prompter 設計缺口（symptom_character 未知時當成沒有胸部症狀）；第 16 列設計取捨（病人直接回答較不急的值、"
          "又在別句順口說出較急的值時，目前保留直接回答、只記 conflict、不升級；開發集升級方向的 conflict 0 次，驗收者窮舉已知值衝突 669 組）。"
          "**凍結前須先裁定**：第 12 項「不太會喘 → none」已以例句寫進提示。", "",
          d["ambiguity"]["note"], "", "| # | 說法 | 欄位 | 開發集出現處 | 關鍵詞抽取器（Phase 0）歸類 | v2 處理 | 待裁定 |", "|---|---|---|---|---|---|---|"]
    for i, a in enumerate(d["ambiguity"]["items"], 1):
        L.append(f"| {i} | 「{a['phrase']}」 | {a['slot']} | {a['where']} | {a['keyword']} | {a['v2']} | {a['question']} |")
    if d["ambiguity"].get("holdout_note"):
        L += ["", d["ambiguity"]["holdout_note"]]
    L += ["", "## 6. 費用與耗時", ""]
    for k, v in d["costs"].items():
        L.append(f"- {k}：{v}")
    L += ["", "## 7. 改動的檔案", ""] + [f"- `{f}`：{why}" for f, why in d["files_changed"]] + ["", "## 8. 重現", "", "```"] + d["repro"] + ["```", ""]
    return "\n".join(L)


ADJ_COLUMNS = ["編號", "說法原文（欄位）", "開發集出處 case 與原句", "目前處理方式", "可能的歸類選項", "提示裡是否已寫入例句",
               "Clinical Owner 裁定"]


def adjudication_rows(amb: dict[str, Any]) -> list[list[Any]]:
    rows = []
    extra = [(amb["gap"], "設計缺口")] + ([(amb["tradeoff"], "設計取捨")] if amb.get("tradeoff") else [])
    for i, (it, tag) in enumerate([*((x, None) for x in amb["items"]), *extra], 1):
        src = "\n".join(f"{s['case']}（{s['where']}）：「{s['sentence']}」" if s.get("case") else s["sentence"] for s in it["sources"])
        rows.append([i if tag is None else f"{i}（{tag}）", f"{it['phrase']}（{it['slot']}）", src,
                     it.get("v2") or it.get("current"), it["options"], it["in_prompt"], ""])     # 裁定欄寫入空字串（read_only 讀得到）
    return rows


def _fix_zip_times(path: Path, day: str) -> None:
    """xlsx（zip）各檔的時間戳改成報告日期 00:00，重產才會逐位相同（zipfile.writestr 預設用現在時間）。"""
    import zipfile
    y, m, d = map(int, day.split("-"))
    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            zi = zipfile.ZipInfo(info.filename, date_time=(y, m, d, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)


def write_adjudication(amb: dict[str, Any], out: Path, day: str) -> None:
    from .synth_eval import write_xlsx
    rows = adjudication_rows(amb)
    stem = f"extractor_v2_ambiguous_{day}"
    write_xlsx(out / f"{stem}.xlsx", [("模糊說法裁定", [ADJ_COLUMNS, *rows], [8, 28, 60, 40, 36, 36, 30])])
    _fix_zip_times(out / f"{stem}.xlsx", day)
    L = [f"# 抽取器 v2 模糊說法裁定表 — {day}", "",
         "> 只用開發集（119 例開發情境的 Opus 逐字稿與開發集閉環）；保留集未執行、未收集。v2 對這些說法不自行歸類（留未知、系統追問）。",
         "> 「提示裡是否已寫入例句」為「是」者，裁定結果若不同，提示要先改再凍結（保留集只能跑一次）。最後兩列是 Prompter 的設計缺口與順口值寫入規則的設計取捨。", "",
         "| " + " | ".join(ADJ_COLUMNS) + " |", "|" + "---|" * len(ADJ_COLUMNS)]
    for r in rows:
        L.append("| " + " | ".join(str(x).replace("\n", "<br>").replace("|", "\\|") for x in r) + " |")
    (out / f"{stem}.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def _lab(arm: str, r: dict[str, Any]) -> str:
    base, _, suf = arm.partition("@")
    if suf:
        return LABEL[base] + f"（{r['meta']['prompts_version']}，修正前）"
    if base == "structured":
        return LABEL[base]
    rc = r.get("recompute_check")
    return LABEL[base] + (f"（{r['meta']['prompts_version']} 執行；{rc['prompts_version']} 快取重算逐例相同）"
                          if rc and rc.get("per_case_identical") else f"（{r['meta']['prompts_version']}）")


def _sec(s: dict[str, Any]) -> str:
    return "—" if not s.get("n") else f"{s['median_s']:.2f}／{s['p95_s']:.2f} s"


DEFAULT_INPUTS = REPO_ROOT / "reports" / "extractor_v2_2026-10-27_inputs"


def main() -> None:
    """預設只讀 repo 內的輸入目錄（DEFAULT_INPUTS），逐位重產主報告與裁定表；個別參數可覆寫。"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=str(DEFAULT_INPUTS), help="輸入目錄（下列各檔的預設位置）")
    ap.add_argument("--replay", default=None, help="階段 A 最終重放（預設 <inputs>/stage_a_replay.json）")
    ap.add_argument("--runs", default=None, help="閉環輸出目錄（預設 <inputs>；closed_*_limit*.json 視為試跑）")
    ap.add_argument("--freeze", default=None, help="凍結紀錄或目前 hash（預設 <inputs>/status.json）")
    ap.add_argument("--iterations", default=None)
    ap.add_argument("--ambiguity", default=None)
    ap.add_argument("--conclusions", default=None)
    ap.add_argument("--extra", default=None, help="JSON：date、costs、files_changed、repro、stage_b_status、observations_41c（人工整理）")
    ap.add_argument("--date", default=None)
    ap.add_argument("--out", default=str(REPO_ROOT / "reports"))
    args = ap.parse_args()
    inp = Path(args.inputs)
    pick = lambda v, name: Path(v) if v else inp / name          # noqa: E731
    rep, v1 = _j(pick(args.replay, "stage_a_replay.json")), _j(V1)
    runs = pick(args.runs, "")
    closed, pilot = {}, {}
    for p in sorted(runs.glob("closed_*.json")):
        r = _j(p)
        if "_limit" in p.stem:
            pilot[p.stem] = r
            continue
        suffix = p.stem.split(".", 1)[1] if "." in p.stem else None          # closed_dev_gpt.dev15.json → 修正前的版本
        closed[f"{r['meta']['set']}_{r['meta']['arm']}" + (f"@{suffix}" if suffix else "")] = r
    extra = _j(pick(args.extra, "extra.json"))
    day = args.date or extra.pop("date", None) or date.today().isoformat()
    extra.pop("date", None)
    if pilot:
        extra["pilot"] = pilot
    d = {"date": day, "rules_version": rules_version(), "limitations": LIMITS, "freeze": _j(pick(args.freeze, "status.json")),
         "stage_a": {"meta": rep["meta"], "v1": {k: v1_cell(v1, k) for k in ("gpt/ref", "gpt/phone", "gemma/ref", "gemma/phone")},
                     "v2": {k: v2_cell(rep, k) for k in rep["cells"]}, "confirm": {e: {kk: c[kk] for kk in ("dev_grades", "probe_ok", "probe_n", "probe_rows")}
                                                                                  for e, c in rep["confirm"].items()},
                     "llm": rep["llm"], "detail": rep["cells"]},          # 逐輪抽取、開場白差異、Hard stop 觸發點（稽核用）
         "iterations": _j(pick(args.iterations, "iterations.json")), "closed": closed,
         "ambiguity": _j(pick(args.ambiguity, "ambiguity.json")), **extra}
    from .cases import all_cases
    d["truth_hs"] = {c.id: c.truth_rf for c in all_cases() if c.truth_hard_stop}
    md = render(d, pick(args.conclusions, "conclusions.md").read_text(encoding="utf-8"))
    out = Path(args.out)
    write_adjudication(d["ambiguity"], out, day)
    stem = f"extractor_v2_{day}"
    (out / f"{stem}.md").write_text(md, encoding="utf-8")
    slim = {**d, "closed": {k: {kk: vv for kk, vv in v.items() if kk != "cases"} for k, v in closed.items()},
            "stage_a": {**d["stage_a"], "llm": {e: {kk: vv for kk, vv in s.items() if kk != "unclassified"} for e, s in rep["llm"].items()}}}
    (out / f"{stem}.json").write_text(json.dumps(slim, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"→ {out / (stem + '.md')}")


if __name__ == "__main__":
    main()
