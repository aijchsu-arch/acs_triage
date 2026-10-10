# 決策紀錄（Decisions）

格式：已決事項用 D-xx，待決事項用 Q-xx。Claude Code 遇到 Q-xx 範圍內的事**先問，不要自行決定**；遇到 D-xx 直接照做。

---

## 已決（Decided）

| ID | 日期 | 決定 | 來源 |
|---|---|---|---|
| D-01 | 2026-10-10 | 紅旗 = stop sign，命中即 Hard stop，不等資訊足夠。架構拆為「逐句紅旗偵測器」＋「結尾分流分類器」兩層。 | Clinical Owner |
| D-02 | 2026-10-10 | 五個 tier 各對應一條固定後續流程；Tier 9 另對應第六條（轉護理師）。合計六條。 | Clinical Owner |
| D-03 | 2026-10-10 | 居家裝置為 12 導程 ECG，可配合 AI-ECG。只升不降，程式碼強制。Hard stop／T0／正在發作者不建議量。 | Clinical Owner |
| D-04 | 2026-10-10 | STT 低信心片段 → 提示客服請病人再說一次做確認，不直接餵分類器。 | Clinical Owner |
| D-05 | 2026-10-10 | 問題提示器可先以 shadow 模式上線（Phase 1），分流分類器需另走驗證／法規流程。 | Clinical Owner |
| D-06 | 2026-10-10 | 接電話者為一般客服（非護理師）→ 問題庫為固定逐字腳本；客服不做臨床判斷；Tier 9 必須轉護理師。 | Clinical Owner |
| D-07 | 2026-10-10 | 呼吸困難以三段分級追問（激烈運動／日常勞動／靜止）；靜止仍喘 → Hard stop Y，即使疑似焦慮恐慌。適用 C 組與 Tier 9 呼吸困難組（選項 A）。 | Clinical Owner |
| D-08 | 2026-10-10 | 目前沒有真實錄音 → Phase 0 以模擬病人＋hidden case sheet 建立評估；同時規劃在客服端加同意聲明開始錄音。 | Clinical Owner |
| D-09 | 2026-10-10 | 決策模型走 `DecisionModel` 抽象層；`RulesEngine` 永遠作為紅旗保底；Jev（TypeSafe AI）為候選 adapter 之一，不硬綁。 | 設計 |
| D-10 | 2026-10-10 | 真實病人資料在資料出境／本地部署方案確認前，不送任何外部 API。Phase 0 只用合成資料。 | 設計（安全預設） |
| D-11 | 2026-10-10 | 技術預設：Python 3.12 / Pydantic v2 / PyYAML / pytest；FastAPI 到 M4 才引入；不引入前端框架。 | 設計 |
| D-12 | 2026-10-10 | **Q-11 結案**：v0.2 benchmark 18 個情境的 ground truth = Claude v0.2 reviewer 標籤（A1–A18 全部同意）。已回填 `data/scenarios_v0.2.yaml` 的 `truth_tier`／`truth_hard_stop`；`tests/test_benchmark_v0_2.py` 以 `truth_tier` 為準。 | Clinical Owner（問卷 Part A） |

---

## 待決（Open）

| ID | 問題 | 影響範圍 | 誰決定 |
|---|---|---|---|
| Q-01 | STT 供應商：國語＋台語混合、高齡口音的辨識率誰最好？是否需本地部署？ | M4 `stt/` adapter | Clinical Owner + IT |
| Q-02 | Jev（TypeSafe AI）：取得存取？資料出境？有無本地／VPC 部署？費用？ | M3 `decision/jev_adapter.py` | Clinical Owner + IT + 法務 |
| Q-03 | 居家 12 導程 ECG 裝置型號與 API；AI-ECG 模型來源（院內 AI-ECG 專案？）；訊號品質判定由誰提供？ | `ecg/` | Clinical Owner |
| Q-04 | Tier 9 轉護理師但護理師不可得時，預設升級到哪一級？（提案：有 CAD 病史者視為 T1，當日回撥） | `pathway/` | Clinical Owner |
| Q-05 | 中間帶情境（T1／T2／T4）目前為零。候選 18 個已列於 `docs/ADJUDICATION_Q05_Q11.md` Part B，待 Clinical Owner 逐題給等級；Part C 規則題（C1–C8）同時待答。 | `data/scenarios_*.yaml`、`CLINICAL_RULES.md §5.5` | Clinical Owner |
| Q-06 | 錄音與逐字稿：同意聲明文字、加密方式、去識別化流程、保存期限、個資法合規審查。 | Phase 1 前置 | 法務 + IT + Clinical Owner |
| Q-07 | 候選紅旗是否啟用：胸部不適合併明顯冒汗；單次發作 ≥20 min 未緩解是否獨立成條。 | `CLINICAL_RULES.md §3` | Clinical Owner |
| Q-08 | 電話系統整合：客服用哪套 PBX／雲端客服？能否取得雙聲道即時音訊串流？ | M4 以後 | IT |
| Q-09 | Hard stop 通報管道：主管／護理師用什麼接收？（院內通訊軟體、簡訊、客服系統 escalation？） | `pathway/` | 客服主管 + 護理 |
| Q-10 | 客服腳本逐字稿（S-HS、S-T0…S-T9、S-SN-A/B）誰定稿？ | `data/scripts_zh.yaml` | Clinical Owner + 客服主管 |
| Q-12 | Phase 3 之前的法規諮詢：是否需 TFDA 智慧醫材申請？由誰啟動？ | Phase 3 | Clinical Owner + 院方 |
