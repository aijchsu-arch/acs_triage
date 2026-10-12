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
| D-13 | 2026-10-12 | **Q-05 主體結案**：中間帶 18 個情境裁定完成（問卷 Part B；X1–X3 衝突解決：B3→0、B7→1、B11→0），存於 `data/scenarios_midband_v0.1.yaml`。T1 與 T4 各 3 個，各缺 1 個 → Q-05b。 | Clinical Owner |
| D-14 | 2026-10-12 | **規則裁定（問卷 Part C）**：C1 B 端坐呼吸／PND 不是 RF-02 但一律 T0；C2 C 新發已緩解 ≥24h 無再發無休息症狀 → T2；C3 B 閾值下降數天 → T0、數週～一月 → T1；C4 A NTG 用量明顯增加 → T0；C5 A 胸部不適＋明顯冒汗 → **RF-06 Hard stop**；C7 C 抗血小板中斷無症狀 → T3 + expedite；C8 B 心悸不由系統建議居家 ECG。`rules_version` 0.2.1 → 0.3.0。 | Clinical Owner |
| D-15 | 2026-10-12 | **Q-04 結案（C6 D）**：Tier 9 且護理師不可得時依主訴預設 — 胸部不適／缺血等價 → T1；呼吸困難（已排除靜止喘）→ T1；心悸／頭暈無胸悶 → T2；第三方且病人不可及 → T1 + 家屬轉達 S-SN-A；藥物／行政諮詢且否認症狀 → T3。 | Clinical Owner |
| D-16 | 2026-10-12 | 資料模型連動：slot `orthopnea_pnd_edema` 拆為 `orthopnea_pnd`（→ T0）與 `edema`；`Q-DIAPH-01` priority 升為 redflag；新增 14 個中間帶 slot。問題庫 `bank_version` 0.1 → 0.2。 | 設計（依 D-14 推導） |
| D-17 | 2026-10-12 | **Q-05b 結案**：B19（新發兩天、昨日 NTG 有效、今日未發作）= T1；B20（回診前空腹衛教問題）= T4。中間帶共 20 個情境，T0 2／T1 4／T2 4／T3 6／T4 4。 | Clinical Owner |
| D-18 | 2026-10-12 | DV-1～DV-5 全部確認（「照你的推論建立規則」），`[derived]` 標記移除。`rules_version` 0.3.0 → 0.3.1。 | Clinical Owner |
| D-19 | 2026-10-12 | `TierDecision` 分 `provisional_tier`（不經 sufficiency gate）與 `tier`（final）。開場白 benchmark 比對 provisional；端到端模擬比對 final。否則「只給開場白 → truth」測試與 §5.9 gate 必然矛盾。 | 設計 |
| D-20 | 2026-10-13 | **Q-13 結案**：DV-6、DV-7 確認。`rules_version` 0.3.1 → 0.3.2（僅移除待確認標記，規則內容不變）。Clinical Owner 指示：開始執行 M0→M2。 | Clinical Owner |
| D-21 | 2026-10-13 | M2 模擬病人先以 **ScriptedPatient**（確定性、依 hidden sheet 作答、可重現）實作；LLM 扮演病人移至 **M2b**（需院內可用 LLM 端點，D-10）。理由：本環境無 LLM 端點；確定性病人才能作為回歸測試的 oracle。 | 設計（執行中決定） |
| D-22 | 2026-10-13 | `max_questions` 8 → **10**。模擬顯示「模糊主訴 → 穩定型 T3」需 4 紅旗題 + 4 決定題 + ND-05 抗血小板題 = 9 題。 | 設計（執行中決定） |
| D-23 | 2026-10-13 | **provisional 0 永不因 gate 未過而變 9**（final = 0）；T0 的 gate 只驅動 Prompter 續問紅旗題與可下修等級的時序題（DV-1／C3 B）。「新發、時序未知」→ 以今天視之（T0），病人答「不記得」亦同。 | 設計（不得降級精神） |
| D-24 | 2026-10-13 | 資料層：(a) v0.2 的 18 情境補 `hidden_slots`（Claude 依 truth 與 reviewer boundary 撰寫，非 Clinical Owner 標籤）；資訊不足組標 `persona: vague`（紅旗題答沒有、決定題答不知道）以測節制；(b) `symptom_character` 新增 `none`（明確否認）、新增 extractor-only slot `dyspnea_complaint`；(c) `Q-DURATION-01`、`Q-DRUGTIME-01` 降為 refine；(d) S-MID-02 變體 `onset_weeks_ago=1` 期望 9 → 0（DV-2「落回其他規則」）；S-MID-14／16 hidden 補 `onset_new`。 | 設計（執行中決定） |
| D-25 | 2026-10-13 | 安全衍生：病人明確否認喘（`dyspnea_grade=none`）→ `dyspnea_acute／orthopnea_pnd／cant_finish_sentence=false`；明確否認胸部症狀 → `ongoing_now=false`。只往「無此症狀」方向推，只填未知欄位。 | 設計 |
| D-26 | 2026-10-13 | Sufficiency gate：ND-05 → 已知 CAD／PCI、有胸部症狀、provisional 1–3 時必問抗血小板是否中斷；T3 穩定型的必要 slot 依主訴（胸部／呼吸）動態決定。 | 設計 |

---

## 待決（Open）

| ID | 問題 | 影響範圍 | 誰決定 |
|---|---|---|---|
| Q-01 | STT 供應商：國語＋台語混合、高齡口音的辨識率誰最好？是否需本地部署？ | M4 `stt/` adapter | Clinical Owner + IT |
| Q-02 | Jev（TypeSafe AI）：取得存取？資料出境？有無本地／VPC 部署？費用？ | M3 `decision/jev_adapter.py` | Clinical Owner + IT + 法務 |
| Q-03 | 居家 12 導程 ECG 裝置型號與 API；AI-ECG 模型來源（院內 AI-ECG 專案？）；訊號品質判定由誰提供？ | `ecg/` | Clinical Owner |
| Q-06 | 錄音與逐字稿：同意聲明文字、加密方式、去識別化流程、保存期限、個資法合規審查。 | Phase 1 前置 | 法務 + IT + Clinical Owner |
| Q-07 | 候選紅旗：單次發作 ≥20 min 未緩解是否獨立成條（冒汗已於 D-14 定為 RF-06）。 | `CLINICAL_RULES.md §3` | Clinical Owner |
| Q-08 | 電話系統整合：客服用哪套 PBX／雲端客服？能否取得雙聲道即時音訊串流？ | M4 以後 | IT |
| Q-09 | Hard stop 通報管道：主管／護理師用什麼接收？（院內通訊軟體、簡訊、客服系統 escalation？） | `pathway/` | 客服主管 + 護理 |
| Q-10 | 客服腳本逐字稿（S-HS、S-T0…S-T9、S-SN-A/B）誰定稿？ | `data/scripts_zh.yaml` | Clinical Owner + 客服主管 |
| Q-12 | Phase 3 之前的法規諮詢：是否需 TFDA 智慧醫材申請？由誰啟動？ | Phase 3 | Clinical Owner + 院方 |
