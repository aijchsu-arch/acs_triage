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
| D-27 | 2026-10-13 | **決定性問題改為反事實定義**（依 Reviewer Prompt「只列會真正改變 disposition 的問題」）：在 case 的完整事實下，把某題換成任一可能答案，若 (provisional_tier, hard_stop) 改變即為 decisive；存在答案使結果**更急**者為 escalating（Tier 9 依 C6 D 換算急迫度）。安全指標改為 **escalating recall**（目標 ≥ 90%）；decisive recall 僅記錄。實作 `sim/decisive.py`；情境檔 `decisive_questions` 由 `python -m sim.decisive --write` 產生，`tests/test_decisive.py` 確保一致。重訂基線：escalating 86.5%（455/526）。舊的人工清單同時過寬（列入不改變結果的題）與過窄（漏列紅旗題與 NTG 題）。 | 設計（Clinical Owner 指示重訂基線） |
| D-28 | 2026-10-13 | **Q-14 裁定（a／b／c／e／f／g 同意）並實作，rules_version 0.3.2 → 0.4.0**：(a) Q-NTG-01 升為 decisive；(b) 胸部症狀定在 T1–T4 前，休息時症狀、閾值下降、NTG 增加必須已知；(c) 第三方來電須確認病人可及；(e) 可重現／咳嗽豁免限 `pain`、餐後豁免限 `epigastric`——新發下顎肩膀沉重或壓迫感不再能被豁免降級；(f A) 無症狀諮詢加一題合併篩檢 Q-SCREEN-01（心悸／姿勢性頭暈／檢查異常待追蹤），答「沒有」即三項 false，答「有」或「不知道」才逐項追問；(g) `last_episode_timing=ongoing` 視同今天並帶出 `ongoing_now=true`（RF-03）。資料：17 個胸部症狀情境 sheet 補 `ntg_use_increased: false`（C4 A 下唯一與 truth 一致的值）、7 個無症狀情境補三項篩檢事實。新基線（clean）：escalating **95.9%（510/532）**、Hard-stop miss 0/27、under 0、over 0、exact 115/116（S-INSUF-02#1 題數上限，見 Q-15）、平均 5.3 題。 | Clinical Owner（Q-14） |
| D-29 | 2026-10-14 | **Q-14d 選 C、Q-15 同意，rules_version 0.4.0 → 0.5.0**：非缺血型豁免（刺痛可重現、刺痛咳嗽、上腹餐後；已由 Q-14e 限縮）不論時序都適用，不進 T0／T1-昨天／T2->24h；勞累型豁免（DV-2 新發穩定 ≥2 週、DV-4 PCI 後較輕）**只在時序不明時**適用，病人明確說今天或仍在發作 → T0。配套：DV-2／DV-4 定案前 gate 必須問過時序（答「不記得」算已知），否則不問就永遠豁免。`max_questions` 10 → **11**。新增 `tests/test_q14.py` 時序單調性測試（24 個胸部症狀情境：仍在 ≥ 今天 ≥ 昨天 ≥ >24h）。所有 truth 不變。新基線（clean，`reports/eval_2026-10-14_*`）：exact **116/116**、escalating **96.6%（512/530）**、Hard-stop miss 0/27、under 0、over 0、平均 5.5 題。 | Clinical Owner（Q-14d、Q-15） |
| D-30 | 2026-10-14 | **M2b 端點更正**：M2b 的 LLM 只扮演病人、只讀合成 hidden sheet，不含真實病人資料，D-10 不適用；本地 llama.cpp（llama-server 的 OpenAI 相容 API）或任何雲端 API 皆可。先前「需院內端點」為 Claude 誤寫。實際限制：雲端開發環境連不到外部 LLM 也無金鑰 → 在 Clinical Owner 可連到端點的電腦上以 Claude Code Desktop 執行。規則：金鑰只放環境變數、不得進 repo；扮演病人的模型與分類器模型應不同家，避免自己出題自己答。驗收：LLM 病人下 Hard-stop miss 與 under-triage 仍為 0，並量測病人模型編造 sheet 以外事實的比率。 | 設計（Clinical Owner 確認） |
| D-31 | 2026-10-14 | **M2b 選 B：病人模擬用雲端 Claude API**。金鑰環境變數名稱固定為 `ACS_PATIENT_LLM_KEY`（Jev 為 `ACS_JEV_API_KEY`），程式一律以 `api_key=os.environ[...]` 明確傳入 SDK。**不得使用 `ANTHROPIC_API_KEY`**：Claude Code 讀到這個變數會改用 API 金鑰計費、取代訂閱登入（官方文件）。金鑰存在作業系統的鑰匙圈／使用者環境變數，不貼進對話、不寫入任何檔案；任何指令與 log 都不得印出金鑰，檢查只印 OK／MISSING。依 D-30，病人模型用 Claude 時，M3 的 LLM 版分類器改用本地模型或 Jev，避免同一家模型自己出題自己答。 | Clinical Owner（M2b 選 B）＋設計 |
| D-32 | 2026-10-15 | **M2b 實作方式**：`LLMPatientSimulator` 每題以 structured output 回傳 `{utterance_zh, dont_know, answer}`（answer 型別／選項依題目 `answer_type` 以 JSON schema 限定），**answer 直接進 runner、不經 extractor**——M2b 量的是病人模型的偏差，slot 抽取模型化屬 M3。每題答案與 oracle（ScriptedPatient 無噪音答案）比對，偏差分 fabricated（sheet 無此事實卻作答＝D-30 的編造率）／contradicted／omitted。persona vague 時 sheet 只給紅旗題事實，選擇題「不知道」對應規則與 ScriptedPatient 相同。預設 `claude-haiku-5-5`（2026-10-15 Clinical Owner 指定；Haiku 無 server-side fallback，以 `--model` 換其他模型時才帶 fallback `default`）、effort low；提示詞在 `data/llm_patient.yaml`（`prompt_version`）。驗收：`python -m sim.run_llm_eval` 產 `reports/eval_<date>_llm.md`，Hard-stop miss 與 under-triage 為 0，並列出與 Scripted 結果不同的 case 及是否由病人偏差造成。 | 設計；Clinical Owner 2026-10-15 同意 |
| D-33 | 2026-10-15 | **M2b 實跑結果（119 cases，`claude-haiku-5-5`，effort low）**。提示詞 v0.1：Hard-stop miss 1/27（S-MID-11#1）、under-triage 2（S-INSUF-04#1、S-MID-06#2），全部因病人模型偏差：S-MID-11#1、S-MID-06#2 是在 boundary variant 中「相信開場白、推翻 sheet」，S-INSUF-04#1 是誤解二選一題的「是」（`reports/eval_2026-10-15_llm_prompt0.1.md`）。提示詞改 v0.2（事實清單優先於開場白；answer 照抄清單值；二選一題 true＝第一選項，已確認 onset_new／dyspnea_acute 兩題皆符合）後：**Hard-stop miss 0/27、under-triage 0（達 D-30 驗收）**；over-triage 2、abstention FP 4／FN 1、exact 94.0%（Scripted 100%），7 個與 Scripted 不同的 case 全由病人偏差造成；偏差率 5.9%（39/658），**編造率 18.6%（27/145）**。待 Clinical Owner 處理：(1) S-MID-03#1 variant 設 `ntg_use_increased: false`，但開場白明講舌下片用量增加，sheet 與開場白矛盾；(2) S-MID-13「飯後坐著胸口脹」是否算 `rest_symptom`，定義不明；(3) S-STABLE-01#2 病人編造「兩年沒變」使 truth 9 被判 T3——編造會讓系統跳過 Tier 9 節制，M3／真實資料階段須注意。編造多為從開場白推論 sheet 未記錄的事實，部分可能是 extractor 未抽出而非真的編造，未逐筆裁定。LLM 非確定性：結果為單次執行。 | 設計（執行結果） |

---

## 待決（Open）

| ID | 問題 | 影響範圍 | 誰決定 |
|---|---|---|---|
| Q-01 | **STT 供應商**（2026-10-14 更新）。<br>**必要規格**：院內或私有雲部署（真實音訊不出院，D-10）；國台語夾雜、高齡口音；電話窄頻（多為 8 kHz）音訊；串流、延遲約 1 秒；**每段輸出信心分數**（Confidence Gate 依賴，無則淘汰）；自訂詞彙（保栓通、舌下含片、支架、冠心症）；授權可用於醫療。<br>**候選（準確率皆為廠商自述，須實測）**：MediaTek Research Breeze-ASR-26（2026-02-26 開源，Apache-2.0，Hugging Face `MediaTek-Research/Breeze-ASR-26`，Whisper 架構，約 1 萬小時合成台語含國台語夾雜，輸出中文字；官方台語基準 CER 30.1%，並註明重口音、方言、專業術語表現下降）；台灣大哥大開源 ASR（2024，國台英客混用，可私有雲／院內部署，自家客服使用）；myVoca（台灣大哥大＋長問科技，2026-03，部署方式未公開）；本地 Whisper 為基準。<br>**評選方法（不需真實病人）**：以 38 情境＋變體為劇本，客服同仁（含慣用台語的年長志工）經真實電話線路角色扮演錄音，分國語／台語／混合；量 CER、**關鍵詞正確率**（有／沒有、今天／昨天、坐著也喘）、信心分數是否在錯字處偏低、以轉寫稿跑系統的分流一致率。錄音前取得同仁書面同意。<br>**依賴**：Q-08 雙聲道串流；M3 模型版 slot 抽取（現行關鍵詞 extractor 對真實口語會掉分，否則量到的是 extractor 而非 ASR）。 | M4 `stt/` adapter | Clinical Owner + IT + 客服主管 |
| Q-02 | **Jev（TypeSafe AI）**（2026-10-14 更新）：**Clinical Owner 已有測試用 API key → M3 可用合成資料開工**（D-10 只限制真實病人資料）。<br>**已知狀態（第三方整理，待原廠文件確認）**：early access；僅美國西岸託管 API，不開放權重、不可自架、未見 VPC；宣稱不以客戶輸入訓練，企業方案可零保留；有 DPA；未見 BAA；SOC 2 須索取報告；以英文為主、中日韓文準確度不穩；可鎖定版本（`jev-1.13.0`，勿用 `jev-latest`）。<br>**設計對策**：Jev 輸入以結構化 slot 狀態（英文 key／enum）為主，不送中文逐字稿；逐句紅旗維持規則引擎保底。<br>**真實資料前（Phase 1）仍待決**：向原廠索取零保留企業合約、DPA 與次處理者清單、SOC 2 Type II、VPC／本地部署時程；請法務判斷「僅送去識別結構化臨床欄位」的境外傳輸評估。否決則真實資料路徑改用院內模型，Jev 僅留研究用。 | M3 `decision/jev_adapter.py` | Clinical Owner + IT 資安 + 法務 |
| Q-03 | 居家 12 導程 ECG 裝置型號與 API；AI-ECG 模型來源（院內 AI-ECG 專案？）；訊號品質判定由誰提供？ | `ecg/` | Clinical Owner |
| Q-06 | 錄音與逐字稿：同意聲明文字、加密方式、去識別化流程、保存期限、個資法合規審查。 | Phase 1 前置 | 法務 + IT + Clinical Owner |
| Q-07 | 候選紅旗：單次發作 ≥20 min 未緩解是否獨立成條（冒汗已於 D-14 定為 RF-06）。 | `CLINICAL_RULES.md §3` | Clinical Owner |
| Q-08 | 電話系統整合：客服用哪套 PBX／雲端客服？能否取得雙聲道（客服一軌、病人一軌）即時音訊串流？請 IT／電話廠商確認是否支援 SIPREC 或 media forking。 | M4 以後 | IT |
| Q-09 | Hard stop 通報管道：主管／護理師用什麼接收？（院內通訊軟體、簡訊、客服系統 escalation？） | `pathway/` | 客服主管 + 護理 |
| Q-10 | 客服腳本逐字稿（S-HS、S-T0…S-T9、S-SN-A/B）誰定稿？ | `data/scripts_zh.yaml` | Clinical Owner + 客服主管 |
| Q-12 | Phase 3 之前的法規諮詢：是否需 TFDA 智慧醫材申請？由誰啟動？ | Phase 3 | Clinical Owner + 院方 |
