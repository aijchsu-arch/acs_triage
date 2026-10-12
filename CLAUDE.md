# CLAUDE.md — acs_triage 工作守則

你正在實作一個**醫療電話分流的 AI 旁聽系統**。輸出錯誤可能延誤心肌梗塞病人送醫。請先讀完 `docs/BLUEPRINT.md`，再動手。

## 讀取順序
1. `docs/BLUEPRINT.md` — 設計真相來源
2. `docs/CLINICAL_RULES.md` — 臨床規則（唯讀，見下）
3. `docs/DECISIONS.md` — 已決／待決；Q-xx 範圍內的事先問
4. `data/` — benchmark、情境、問題庫

## 絕對禁止
- **不得**修改 `docs/CLINICAL_RULES.md` 與 `data/clinical_rules.yaml` 的任何紅旗、閾值、等級定義、流程對照。需要改 → 停下來，在回覆中引用條目並請 Clinical Owner 裁定。
- **不得**實作任何會讓分流等級變得更不急的自動邏輯（違反 ND-01～ND-05）。
- **不得**把 Tier 9 當成「低信心的替代品」；它是獨立判斷，有自己的規則（`CLINICAL_RULES.md §5.8`）。
- **不得**在任何路徑把真實病人資料送到外部 API（D-10）。
- **不得**在客服 UI 或 log 以外的輸出中顯示「ACS 機率」「心肌梗塞」等診斷字眼。
- **不得**用 `rm -rf`、`git push --force`、改寫 `data/benchmark/` 下的原始 CSV。

## 編碼原則
- 問，不要猜：需求有多種合理實作路徑時，列出選項與取捨後停下來。
- 最簡解：先寫能過驗收條件的最少程式碼，不預先抽象。
- 範圍紀律：只改任務需要的檔案與行數；不順手重構、不順手修 lint。
- 該反對就反對：若指示會引入 bug、安全漏洞或違反臨床規則，說明並提出替代。
- 文件與程式衝突時以 `docs/BLUEPRINT.md` 為準，並回頭修文件；若文件本身有錯，先提出再改。

## 語言與命名
- 文件、commit message、PR 描述：繁體中文。
- 程式碼識別字、YAML key、enum 值：英文。
- 病人／客服腳本字串：繁體中文，放 `data/*.yaml`，不寫死在程式碼。

## 測試要求
- 每條紅旗（RF-01～RF-06）至少 3 個正例、3 個含否定詞的反例（「沒有昏倒」不得命中 RF-01；「沒有冒汗」不得命中 RF-06）。
- `tests/test_no_downgrade.py` 覆蓋 ND-01～ND-05。
- `tests/test_benchmark_v0_2.py`：18 個情境只給開場白 → `provisional_tier` 與 `hard_stop` 必須等於 `data/scenarios_v0.2.yaml` 的 `truth_tier`／`truth_hard_stop`（D-12）。比對的是 **provisional**，不是經 sufficiency gate 的 final（見 `BLUEPRINT.md §3.7`）。
- `tests/test_benchmark_midband.py`：`data/scenarios_midband_v0.1.yaml` 20 個情境同上（D-13、D-17）。
- `tests/test_boundary_variants.py`：兩份情境檔的每個 `boundary_variants`，以 `hidden_slots` + `override` 直接餵規則引擎 → `provisional_tier`／`hard_stop`／`rf` 等於 `expect`。`expect.tier: null` 的變體跳過並列印。
- 規則中標 `[derived DV-n]` 的門檻（`CLINICAL_RULES.md §9.2`）照寫，但在程式碼註解標 `# DV-n pending`，Clinical Owner 確認後移除；`(DV-n)` 已確認，照一般規則處理。
- `pytest` 不綠不交付。

## 版本紀律
- 改 `data/clinical_rules.yaml` → bump `rules_version`，並在 `docs/CLINICAL_RULES.md` 頂部同步。
- 所有模型 adapter 回傳 `model_version`。
- 里程碑完成 → 更新 `docs/BLUEPRINT.md §11` 狀態與 `docs/DECISIONS.md`。

## 目前任務
從 **M0** 開始（`docs/BLUEPRINT.md §11`）。M0 不需要任何模型呼叫、不需要網路。
