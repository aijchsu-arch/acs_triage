# acs_triage

醫療客服電話的 ACS／慢性冠心症分流 AI 旁聽系統（ambient triage copilot）。

- 設計藍圖：[`docs/BLUEPRINT.md`](docs/BLUEPRINT.md)
- 臨床規則（Clinical Owner 專屬）：[`docs/CLINICAL_RULES.md`](docs/CLINICAL_RULES.md)
- 已決／待決：[`docs/DECISIONS.md`](docs/DECISIONS.md)
- Claude Code 工作守則：[`CLAUDE.md`](CLAUDE.md)

## 狀態
Phase 0（模擬）— 設計完成，M0 未開工。

## 資料
- `data/benchmark/v0.2/` — v0.2 盲性審查表與 Claude reviewer 結果（80 列＝18 唯一情境）
- `data/scenarios_v0.2.yaml` — 18 情境＋boundary 變體（模擬器種子）
- `data/question_bank_seed.yaml` — 問題庫種子（slot + 客服腳本草稿）

## 免責
研究與開發用途。任何輸出不構成醫療建議；系統設計上不診斷 ACS，只分流 urgency，且最終處置由人執行。
