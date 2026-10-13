# acs_triage

醫療客服電話的 ACS／慢性冠心症分流 AI 旁聽系統（ambient triage copilot）。

- 設計藍圖：[`docs/BLUEPRINT.md`](docs/BLUEPRINT.md)
- 臨床規則（Clinical Owner 專屬）：[`docs/CLINICAL_RULES.md`](docs/CLINICAL_RULES.md)
- 已決／待決：[`docs/DECISIONS.md`](docs/DECISIONS.md)
- Claude Code 工作守則：[`CLAUDE.md`](CLAUDE.md)

## 狀態
Phase 0（模擬）— M0／M1／M2 完成（2026-10-13）。`pytest`：170 passed, 3 skipped。基線報告見 `reports/`。

## 執行
```bash
pip install -e '.[dev]'          # 或：pip install pydantic pyyaml pytest
pytest                           # 全部驗收測試
python -m sim.run_eval --mode clean     # 產出 reports/eval_<date>_clean.md／.json（另有 vague、low_stt）
```

## 程式結構
- `src/acs_triage/extract/` 關鍵詞 Slot Extractor（規則路徑）
- `src/acs_triage/rules/` SlotState、紅旗、Tier 規則、Sufficiency Gate、RulesEngine（含 ND-01／ND-02 強制）
- `src/acs_triage/prompter/` 固定問題庫選題　`pathway/` 流程對照　`audit/` append-only log　`decision/` DecisionModel 介面
- `sim/` hidden case sheet 展開、ScriptedPatient、對話 runner、指標、報告

## 資料
- `data/benchmark/v0.2/` — v0.2 盲性審查表與 Claude reviewer 結果（80 列＝18 唯一情境）
- `data/scenarios_v0.2.yaml` — 18 情境＋boundary 變體（模擬器種子）
- `data/question_bank_seed.yaml` — 問題庫種子（slot + 客服腳本草稿）

## 免責
研究與開發用途。任何輸出不構成醫療建議；系統設計上不診斷 ACS，只分流 urgency，且最終處置由人執行。
