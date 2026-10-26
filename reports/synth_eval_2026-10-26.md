# 實驗 1：獨立合成病人驗證集評估 — 2026-10-26

- rules_version 0.8.0；情境檔 `data/synth/scenarios_synth_v1.yaml`（150 例）；參考標註 `data/synth/reference_synth_v1.json`；LLM 病人報告 `reports/eval_2026-10-26_llm_scenarios_synth_v1_opus-5-5_medium.json`

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
10. **生成資料的 slot 語意問題**：生成器把只對胸部症狀有意義的 slot 用在非胸部症狀（症狀性質為「沒有」或「其他」）——rest_symptom=true 但無胸部症狀 16 例（SYN-077、SYN-078、SYN-079、SYN-082、SYN-087、SYN-091、SYN-092、SYN-093、SYN-095、SYN-096、SYN-101、SYN-108、SYN-112、SYN-116、SYN-120、SYN-133）；餐後打嗝很快緩解卻填 rest_symptom=true（與 D-35 相反）5 例（SYN-108、SYN-112、SYN-116、SYN-120、SYN-130）；無胸部症狀卻填 exertion_relation 27 例。後果：(a) 只靠 T0-REST-NEW 判 T0 的無胸部症狀病人 7 例（SYN-078、SYN-091、SYN-092、SYN-095、SYN-096、SYN-112、SYN-116），這些例子的 (a) 結果（不論算 over 或 exact）都受這個假象影響。根源是 `data/synth/synth_prompts.yaml` 生成器說明沒有交代這些 slot 只用於胸部症狀；v2 生成時要修。
    （以下為人工逐例分類，獨立驗收 2026-10-26；重跑 `sim.synth_eval` 會覆蓋這句）開場白與 slots 直接矛盾只有 SYN-012、SYN-015 兩例
    （開場白只描述休息時發作，slots 卻填 exertion_relation=both）；「資料」節列的 66 例開場白抽取值與 slots 不同，其中 49 例是抽取器錯誤
    （否定詞、中文數字、時間詞、症狀性質詞），其餘多為粒度或分類差異，不是資料錯誤。

## 結論摘要（數字）

- 參考標註一致（tier 與 Hard stop 都相同）：130/150（86.7%，95% CI 80.2–91.7%）；只看 tier 一致：130/150。

### 參考一致子集（主分析）

| 層 | n | HS 敏感度 | Under-triage | 其中系統為 T9（依備援換算才較不急） | Over-triage | Exact | T9 比例 | 急診負擔（參考 T1–T4 卻 HS／T0） | 平均題數 |
|---|---|---|---|---|---|---|---|---|---|
| (a) 全資訊規則 | 130 | 51/51（100.0%，95% CI 93.0–100.0%） | 14/130（10.8%，95% CI 6.0–17.4%） | 9/130 | 8/130（6.2%，95% CI 2.7–11.8%） | 108/130（83.1%，95% CI 75.5–89.1%） | 16/130（12.3%，95% CI 7.2–19.2%） | 4/34（11.8%，95% CI 3.3–27.5%） | — |
| (b) Scripted 病人 | 130 | 49/51（96.1%，95% CI 86.5–99.5%） | 26/130（20.0%，95% CI 13.5–27.9%） | 16/130 | 7/130（5.4%，95% CI 2.2–10.8%） | 97/130（74.6%，95% CI 66.2–81.8%） | 22/130（16.9%，95% CI 10.9–24.5%） | 2/34（5.9%，95% CI 0.7–19.7%） | 5.48 |
| (c) Opus LLM 病人 | 130 | 49/51（96.1%，95% CI 86.5–99.5%） | 26/130（20.0%，95% CI 13.5–27.9%） | 16/130 | 7/130（5.4%，95% CI 2.2–10.8%） | 97/130（74.6%，95% CI 66.2–81.8%） | 22/130（16.9%，95% CI 10.9–24.5%） | 2/34（5.9%，95% CI 0.7–19.7%） | 5.48 |

### 全部 150 例（保守參考＝兩位標註者中較急者）

| 層 | n | HS 敏感度 | Under-triage | 其中系統為 T9（依備援換算才較不急） | Over-triage | Exact | T9 比例 | 急診負擔（參考 T1–T4 卻 HS／T0） | 平均題數 |
|---|---|---|---|---|---|---|---|---|---|
| (a) 全資訊規則 | 150 | 51/51（100.0%，95% CI 93.0–100.0%） | 26/150（17.3%，95% CI 11.7–24.4%） | 18/150 | 12/150（8.0%，95% CI 4.2–13.6%） | 111/150（74.0%，95% CI 66.2–80.8%） | 25/150（16.7%，95% CI 11.1–23.6%） | 6/43（14.0%，95% CI 5.3–27.9%） | — |
| (b) Scripted 病人 | 150 | 49/51（96.1%，95% CI 86.5–99.5%） | 38/150（25.3%，95% CI 18.6–33.1%） | 26/150 | 11/150（7.3%，95% CI 3.7–12.7%） | 100/150（66.7%，95% CI 58.5–74.1%） | 33/150（22.0%，95% CI 15.7–29.5%） | 3/43（7.0%，95% CI 1.5–19.1%） | 5.87 |
| (c) Opus LLM 病人 | 150 | 49/51（96.1%，95% CI 86.5–99.5%） | 38/150（25.3%，95% CI 18.6–33.1%） | 26/150 | 11/150（7.3%，95% CI 3.7–12.7%） | 100/150（66.7%，95% CI 58.5–74.1%） | 33/150（22.0%，95% CI 15.7–29.5%） | 3/43（7.0%，95% CI 1.5–19.1%） | 5.87 |

- 待 Clinical Owner 裁定：48 例（標註者不一致 20 例；系統任一層比任一位標註者不急 41 例）。

## 主要發現（Claude Code 逐例查規則引擎、Prompter 與抽取器後人工整理，經獨立驗收修訂；待 Clinical Owner 裁定。重跑 `sim.synth_eval` 會覆蓋本節）

「低估」「過度」都是相對於 LLM 參考標註；T9 在護理師可接手時是轉護理師，下列「備援 Tn」是護理師不可得時的預設等級。
(c) 與 (b) 150 例逐例結果相同：Opus LLM 病人的偏差是 10 例、10 題的編造（另 9 筆是複誦確認時重複同一答案），沒有一筆改變分級。
在結構化答案的條件下，病人表達不是落差來源；落差集中在 (a)→(b)（24 例結果不同）。下面分三類，裁定方向不同。

### 一、系統缺口（依嚴重度排序）

1. **對話中漏掉 2 例 Hard stop：沒有胸部症狀的真正暈厥（SYN-093、SYN-105）。** 開場白用「有昏去」「倒下…四十秒左右完全沒反應」
   描述意識喪失，抽取器沒抓到；Prompter 只在 presyncope 或姿勢性頭暈為「有」時才問 Q-SYNCOPE-02，而 Q-SYNCOPE-01 只在有胸部症狀時問
   → 暈厥從未被問到，結束於 T9（`no_more_questions`）。(a) 全資訊時 RF-05 正常命中；把抽取補上 syncope=true，開場白即 Hard stop。
   **給 Clinical Owner 的發現**：備援是 T3，是因為 T9 備援表沒有暈厥／瀕厥類別，這類病人被歸成 `consult_no_symptoms`
   （`src/acs_triage/pathway/router.py:9–18`、`data/clinical_rules.yaml` 的 `tier9_nurse_unavailable_fallback`）。
2. **沒有胸部症狀的瀕厥＋心悸／冒汗，規則沒有通往 T0 的路徑（SYN-096；同型 SYN-092、SYN-100）。** RF-01／RF-06 都要求胸部症狀，
   Q-DIAPH-01 與休息時症狀題（Q-REST-01）都在 `_CHEST_ONLY`，無胸部症狀不會被問。SYN-096 的「沒有昏掉」被抽成 presyncope=false，
   但這只決定 T3（T3-PALPITATIONS）或 T9：抽取改對後 (b) 仍是 T9（備援 T2），比參考 T0 低兩級。SYN-096 的 (a) T0 來自 T0-REST-NEW
   套到非胸部發作（第三類的資料假象），不是規則看到了瀕厥＋冒汗。SYN-092 (b) T9 備援 T3（參考 T1）；SYN-100 三層皆 T9 備援 T3（標註者 T0／T1）。
3. **只喘不痛、活動閾值下降不會被問閾值（SYN-129；同型 SYN-081、SYN-086）。** Q-THRESHOLD-01 在 `_CHEST_ONLY` → 以 T2-DYSPNEA-DAILY 定案；
   (a) 為 T0（數天，SYN-129，參考 T0）或 T1（數週）。
4. **11 題上限擠掉舌下含片題（SYN-030、SYN-035、SYN-040）。** 開場白已講用量變多，但抽取器沒抓到，Q-NTG-01 排在上限之後
   → T9（備援 T1）；(a) 為 T0-NTG-INCREASED（參考 T0）。
5. **開場白抽取錯誤直接改變分級**：SYN-136「藥也還夠」被抽成 consult_topic=medication_handling → T4；抽取改對後 T3（T3-ADMIN）＝參考。
   SYN-044「坐著不曾這樣」被抽成 rest_symptom=false → (b) T9 備援 T1（參考 T0）。反方向：SYN-014「列車到站前就退了」仍被抽成
   ongoing_now=true → (b) Hard stop（參考 T0，過度）。
6. **規則沒有對應條件 → T9（轉護理師）**：發作變頻繁、變久，但閾值未降、非休息時（SYN-036，備援 T1，參考 T0）；
   PCI 後症狀再現且與術前相同（SYN-071、SYN-072，備援 T1，參考 T0）。

### 二、LLM 參考不同意 Clinical Owner 既有裁定（不宜直接算成系統錯誤，請決定維持或重議）

- **SYN-112、SYN-116（餐後胸口灼熱、打嗝後很快緩解）**：D-35 規定吃飽後打嗝很快緩解不算 rest_symptom；B13／S-MID-13 的 truth 是 T3（DV-5）。
  這兩例的事實清單卻填 rest_symptom=true、性質「其他」，參考 T0 與既有裁定衝突。(a) 因此依 T0-REST-NEW 判 T0（與參考同、被算 exact），
  (b) 因「其他」不算胸部症狀而不問胸部題 → T9 備援 T3。另：Q-CHARACTER-01 的選項沒有 other（`data/question_bank_seed.yaml` 該題 choices），
  只有模擬病人（用 slot 全集回答）答得出 other；真實通話客服只能在題目選項中選，這兩例 (b)(c) 的 T9 有一部分是模擬設計造成的。
- **SYN-066、SYN-074（無症狀抗血小板中斷）**：C7 C → T3＋expedite；兩位 LLM 都判 T1（支架 3 個月內／6 週內自行停藥）。C7 C 沒有區分支架時程，值得重議。
- **SYN-063（PCI 後兩個月、兩週閾值下降）**：C3 B（數週）→ T1；兩位 LLM 都判 T0。這例另有一次 25 分鐘才退的發作（≥20 分鐘為候選紅旗 Q-07，未啟用）
  與「比術前重」，不只是規則衝突。

### 三、生成資料的假象（見限制第 10 點）

- 生成器把 rest_symptom 用在心悸、瀕厥、灼熱等非胸悶發作；T0-REST-NEW 不看症狀性質，也不套用非缺血型豁免，(a) 有 7 例只靠它判 T0：
  SYN-091、SYN-092、SYN-095（以及標註者不一致、對保守參考算的 SYN-078）算成 (a) over；**SYN-096、SYN-112、SYN-116 同一個假象卻被算成 (a) exact**。
  對話中無胸部症狀的病人不會被問休息時症狀，(b) 反而是 T3／T9，所以這些例子的 (a)→(b) 差異不宜解讀成「問診讓結果變差」。
- 其他過度分級（安全方向）：SYN-119 咳嗽才痛、答「休息時也發作過」→ 三層都 T0-REST-NEW（兩位 LLM 都 T4；§5.3 寫非缺血型豁免「不進 T0」，
  實作只套在 T0-NEW-TODAY，請確認是否也該擋 T0-REST-NEW）；SYN-106 按壓才痛，(b) 在問到可重現題之前就以 T0-NEW-TODAY 定案；
  SYN-057 抽取器把「六年」抽成 6 個月、新發題未問 → (b) T1-NEW-YESTERDAY（(a) T3，參考 T3）。

## 資料

- 生成：gpt-6.1-sol（gpt-6.1-sol），effort medium，prompt 1.0。

類別 × 人物風格（實際分布）：

| category | anxious_exaggerating | elderly_slow | family_proxy | general | minimizer | unclear | 合計 |
|---|---|---|---|---|---|---|---|
| acs_today | 4 | 4 | 3 | 7 | 4 | 3 | 25 |
| unstable | 2 | 3 | 3 | 6 | 3 | 3 | 20 |
| chronic_stable | 3 | 2 | 2 | 4 | 2 | 2 | 15 |
| post_pci | 2 | 2 | 3 | 4 | 2 | 2 | 15 |
| heart_failure | 2 | 2 | 2 | 4 | 2 | 3 | 15 |
| arrhythmia_syncope | 2 | 2 | 2 | 5 | 2 | 2 | 15 |
| noncardiac_chest | 2 | 2 | 2 | 5 | 2 | 2 | 15 |
| atypical | 2 | 3 | 2 | 4 | 2 | 2 | 15 |
| admin_followup | 2 | 1 | 2 | 2 | 2 | 1 | 10 |
| family_proxy | 0 | 0 | 5 | 0 | 0 | 0 | 5 |
| 合計 | 21 | 21 | 26 | 41 | 21 | 20 | 150 |

- 與既有 119 個 case 的開場白（40 種）相似度：字元 3-gram 重疊係數（去標點）；另列 Jaccard，門檻 0.4；重生 0 例（共 0 次）；重生上限後仍太像 0 例；最高重疊係數 0.286、平均最高 0.066、最高 Jaccard 0.064；新 case 彼此超過門檻 0 對。
- 開場白抽取值與事實清單不一致（影響 (b)(c)：該 slot 已「已知」就不會再問）：66 例；依 slot：{'episode_duration_min': 21, 'last_episode_timing': 20, 'symptom_character': 17, 'consult_topic': 14, 'exertion_relation': 3, 'ongoing_now': 2, 'third_party_call': 2, 'pattern_unchanged_duration_months': 2, 'dyspnea_acute': 2, 'syncope': 1, 'rest_symptom': 1, 'new_medication_recent': 1, 'recurrence': 1, 'presyncope': 1, 'palpitations': 1}。

## 參考標註

- 一致 130/150；Hard stop 一致 150/150；hard_stop=true 但 tier≠T0 的原始輸出 0 筆（一律視為 T0）。
- 信心分布：Opus {'high': 77, 'medium': 73}；gpt {'high': 145, 'medium': 5}。

Opus（列）× gpt（欄）：

| Opus＼gpt | HS | T0 | T1 | T2 | T3 | T4 | T9 |
|---|---|---|---|---|---|---|---|
| HS | 51 | 0 | 0 | 0 | 0 | 0 | 0 |
| T0 | 0 | 41 | 1 | 0 | 0 | 0 | 2 |
| T1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 |
| T2 | 0 | 2 | 2 | 4 | 1 | 1 | 2 |
| T3 | 0 | 0 | 1 | 3 | 19 | 0 | 0 |
| T4 | 0 | 0 | 0 | 0 | 0 | 8 | 1 |
| T9 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |

## 依類別與人物風格（參考一致子集；格式 x/n）

### (a) 全資訊規則 × category

| category | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| acs_today | 24（全部 25） | 16/16 | 0/24 | 0/24 | 24/24 | 0/24 | 1/25 | — |
| admin_followup | 8（全部 10） | — | 1/8 | 0/8 | 7/8 | 0/8 | 1/10 | — |
| arrhythmia_syncope | 13（全部 15） | 6/6 | 0/13 | 3/13 | 10/13 | 0/13 | 1/15 | — |
| atypical | 15（全部 15） | 6/6 | 3/15 | 2/15 | 10/15 | 4/15 | 3/15 | — |
| chronic_stable | 15（全部 15） | — | 0/15 | 1/15 | 14/15 | 1/15 | 0/15 | — |
| family_proxy | 4（全部 5） | 2/2 | 0/4 | 0/4 | 4/4 | 0/4 | 1/5 | — |
| heart_failure | 10（全部 15） | 9/9 | 0/10 | 0/10 | 10/10 | 0/10 | 4/15 | — |
| noncardiac_chest | 8（全部 15） | 3/3 | 0/8 | 2/8 | 6/8 | 2/8 | 3/15 | — |
| post_pci | 14（全部 15） | 4/4 | 6/14 | 0/14 | 8/14 | 5/14 | 7/15 | — |
| unstable | 19（全部 20） | 5/5 | 4/19 | 0/19 | 15/19 | 4/19 | 5/20 | — |

### (b) Scripted 病人 × category

| category | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| acs_today | 24（全部 25） | 16/16 | 0/24 | 1/24 | 23/24 | 0/24 | 1/25 | 3.04 |
| admin_followup | 8（全部 10） | — | 2/8 | 0/8 | 6/8 | 0/8 | 2/10 | 5.38 |
| arrhythmia_syncope | 13（全部 15） | 4/6 | 6/13 | 0/13 | 7/13 | 3/13 | 7/15 | 5.77 |
| atypical | 15（全部 15） | 6/6 | 2/15 | 2/15 | 11/15 | 3/15 | 2/15 | 4.53 |
| chronic_stable | 15（全部 15） | — | 0/15 | 2/15 | 13/15 | 1/15 | 0/15 | 9.27 |
| family_proxy | 4（全部 5） | 2/2 | 0/4 | 0/4 | 4/4 | 0/4 | 1/5 | 4.5 |
| heart_failure | 10（全部 15） | 9/9 | 0/10 | 0/10 | 10/10 | 0/10 | 5/15 | 1.8 |
| noncardiac_chest | 8（全部 15） | 3/3 | 2/8 | 2/8 | 4/8 | 3/8 | 4/15 | 5.12 |
| post_pci | 14（全部 15） | 4/4 | 6/14 | 0/14 | 8/14 | 4/14 | 7/15 | 6.5 |
| unstable | 19（全部 20） | 5/5 | 8/19 | 0/19 | 11/19 | 8/19 | 9/20 | 7.74 |

### (c) Opus LLM 病人 × category

| category | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| acs_today | 24（全部 25） | 16/16 | 0/24 | 1/24 | 23/24 | 0/24 | 1/25 | 3.04 |
| admin_followup | 8（全部 10） | — | 2/8 | 0/8 | 6/8 | 0/8 | 2/10 | 5.38 |
| arrhythmia_syncope | 13（全部 15） | 4/6 | 6/13 | 0/13 | 7/13 | 3/13 | 7/15 | 5.77 |
| atypical | 15（全部 15） | 6/6 | 2/15 | 2/15 | 11/15 | 3/15 | 2/15 | 4.53 |
| chronic_stable | 15（全部 15） | — | 0/15 | 2/15 | 13/15 | 1/15 | 0/15 | 9.27 |
| family_proxy | 4（全部 5） | 2/2 | 0/4 | 0/4 | 4/4 | 0/4 | 1/5 | 4.5 |
| heart_failure | 10（全部 15） | 9/9 | 0/10 | 0/10 | 10/10 | 0/10 | 5/15 | 1.8 |
| noncardiac_chest | 8（全部 15） | 3/3 | 2/8 | 2/8 | 4/8 | 3/8 | 4/15 | 5.12 |
| post_pci | 14（全部 15） | 4/4 | 6/14 | 0/14 | 8/14 | 4/14 | 7/15 | 6.5 |
| unstable | 19（全部 20） | 5/5 | 8/19 | 0/19 | 11/19 | 8/19 | 9/20 | 7.74 |

### (a) 全資訊規則 × persona_style

| persona_style | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| anxious_exaggerating | 17（全部 21） | 5/5 | 1/17 | 1/17 | 15/17 | 0/17 | 4/21 | — |
| elderly_slow | 17（全部 21） | 3/3 | 2/17 | 2/17 | 13/17 | 2/17 | 4/21 | — |
| family_proxy | 24（全部 26） | 13/13 | 4/24 | 0/24 | 20/24 | 3/24 | 6/26 | — |
| general | 37（全部 41） | 13/13 | 5/37 | 4/37 | 28/37 | 5/37 | 7/41 | — |
| minimizer | 19（全部 21） | 12/12 | 1/19 | 0/19 | 18/19 | 0/19 | 2/21 | — |
| unclear | 16（全部 20） | 5/5 | 1/16 | 1/16 | 14/16 | 6/16 | 3/20 | — |

### (b) Scripted 病人 × persona_style

| persona_style | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| anxious_exaggerating | 17（全部 21） | 5/5 | 3/17 | 0/17 | 14/17 | 1/17 | 6/21 | 5.18 |
| elderly_slow | 17（全部 21） | 2/3 | 4/17 | 2/17 | 11/17 | 5/17 | 6/21 | 7.12 |
| family_proxy | 24（全部 26） | 13/13 | 5/24 | 0/24 | 19/24 | 2/24 | 6/26 | 4.5 |
| general | 37（全部 41） | 12/13 | 10/37 | 4/37 | 23/37 | 8/37 | 13/41 | 5.54 |
| minimizer | 19（全部 21） | 12/12 | 3/19 | 0/19 | 16/19 | 0/19 | 4/21 | 4.32 |
| unclear | 16（全部 20） | 5/5 | 1/16 | 1/16 | 14/16 | 6/16 | 3/20 | 6.81 |

### (c) Opus LLM 病人 × persona_style

| persona_style | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| anxious_exaggerating | 17（全部 21） | 5/5 | 3/17 | 0/17 | 14/17 | 1/17 | 6/21 | 5.18 |
| elderly_slow | 17（全部 21） | 2/3 | 4/17 | 2/17 | 11/17 | 5/17 | 6/21 | 7.12 |
| family_proxy | 24（全部 26） | 13/13 | 5/24 | 0/24 | 19/24 | 2/24 | 6/26 | 4.5 |
| general | 37（全部 41） | 12/13 | 10/37 | 4/37 | 23/37 | 8/37 | 13/41 | 5.54 |
| minimizer | 19（全部 21） | 12/12 | 3/19 | 0/19 | 16/19 | 0/19 | 4/21 | 4.32 |
| unclear | 16（全部 20） | 5/5 | 1/16 | 1/16 | 14/16 | 6/16 | 3/20 | 6.81 |

## Under-triage 明細（系統比參考不急）

急迫度：HS=-1、T0–T4=0–4、T9 依備援換算。「保守參考」= 兩位標註者中較急者。本表依保守參考急迫度與落差自動排序，沒有區分機制；機制分類與人工嚴重度排序見「主要發現」。

| case | category | persona | 參考一致？ | Opus | gpt | (a) | (b) | (c) | (a)(b)(c) 哪幾層低估 |
|---|---|---|---|---|---|---|---|---|---|
| SYN-093 | arrhythmia_syncope | elderly_slow | 是 | T0 Hard stop（RF-05），信心 medium | T0 Hard stop（RF-05），信心 high | T0 Hard stop（RF-05） | T9（備援 T3） | T9（備援 T3） | bc |
| SYN-105 | arrhythmia_syncope | general | 是 | T0 Hard stop（RF-05），信心 medium | T0 Hard stop（RF-05），信心 high | T0 Hard stop（RF-05） | T9（備援 T3） | T9（備援 T3） | bc |
| SYN-096 | arrhythmia_syncope | family_proxy | 是 | T0，信心 medium | T0，信心 high | T0 | T3 | T3 | bc |
| SYN-100 | arrhythmia_syncope | elderly_slow | 否 | T0，信心 medium | T1，信心 high | T9（備援 T3） | T9（備援 T3） | T9（備援 T3） | abc |
| SYN-112 | noncardiac_chest | general | 是 | T0，信心 medium | T0，信心 high | T0 | T9（備援 T3） | T9（備援 T3） | bc |
| SYN-116 | noncardiac_chest | anxious_exaggerating | 是 | T0，信心 medium | T0，信心 high | T0 | T9（備援 T3） | T9（備援 T3） | bc |
| SYN-081 | heart_failure | anxious_exaggerating | 否 | T1，信心 medium | T0，信心 high | T1 | T2 | T2 | abc |
| SYN-086 | heart_failure | elderly_slow | 否 | T1，信心 medium | T0，信心 high | T1 | T2 | T2 | abc |
| SYN-129 | atypical | minimizer | 是 | T0，信心 medium | T0，信心 high | T0 | T2 | T2 | bc |
| SYN-006 | acs_today | unclear | 否 | T0，信心 medium | T9，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-028 | unstable | general | 否 | T1，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-030 | unstable | elderly_slow | 是 | T0，信心 medium | T0，信心 high | T0 | T9（備援 T1） | T9（備援 T1） | bc |
| SYN-033 | unstable | family_proxy | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-035 | unstable | general | 是 | T0，信心 medium | T0，信心 high | T0 | T9（備援 T1） | T9（備援 T1） | bc |
| SYN-036 | unstable | general | 是 | T0，信心 high | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-040 | unstable | family_proxy | 是 | T0，信心 medium | T0，信心 high | T0 | T9（備援 T1） | T9（備援 T1） | bc |
| SYN-041 | unstable | unclear | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-043 | unstable | general | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-044 | unstable | elderly_slow | 是 | T0，信心 high | T0，信心 high | T0 | T9（備援 T1） | T9（備援 T1） | bc |
| SYN-063 | post_pci | general | 是 | T0，信心 high | T0，信心 high | T1 | T1 | T1 | abc |
| SYN-067 | post_pci | anxious_exaggerating | 否 | T1，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-068 | post_pci | family_proxy | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T1 | T1 | abc |
| SYN-071 | post_pci | general | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-072 | post_pci | elderly_slow | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-121 | atypical | elderly_slow | 是 | T0，信心 medium | T0，信心 high | T1 | T0 | T0 | a |
| SYN-131 | atypical | family_proxy | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T0 | T0 | a |
| SYN-134 | atypical | general | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-147 | family_proxy | family_proxy | 否 | T0，信心 medium | T9，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-066 | post_pci | minimizer | 是 | T1，信心 medium | T1，信心 high | T3 | T3 | T3 | abc |
| SYN-074 | post_pci | anxious_exaggerating | 是 | T1，信心 medium | T1，信心 high | T3 | T3 | T3 | abc |
| SYN-078 | heart_failure | general | 否 | T2，信心 medium | T1，信心 high | T0 | T9（備援 T3） | T9（備援 T3） | bc |
| SYN-088 | heart_failure | anxious_exaggerating | 否 | T2，信心 medium | T1，信心 high | T9（備援 T3） | T9（備援 T3） | T9（備援 T3） | abc |
| SYN-092 | arrhythmia_syncope | general | 是 | T1，信心 medium | T1，信心 high | T0 | T9（備援 T3） | T9（備援 T3） | bc |
| SYN-083 | heart_failure | unclear | 否 | T2，信心 medium | T9，信心 high | T9（備援 T3） | T9（備援 T3） | T9（備援 T3） | abc |
| SYN-091 | arrhythmia_syncope | general | 是 | T2，信心 medium | T2，信心 high | T0 | T3 | T3 | bc |
| SYN-095 | arrhythmia_syncope | anxious_exaggerating | 是 | T2，信心 medium | T2，信心 high | T0 | T3 | T3 | bc |
| SYN-108 | noncardiac_chest | minimizer | 否 | T2，信心 medium | T4，信心 high | T9（備援 T3） | T9（備援 T3） | T9（備援 T3） | abc |
| SYN-110 | noncardiac_chest | family_proxy | 否 | T3，信心 medium | T2，信心 medium | T3 | T9（備援 T1） | T9（備援 T1） | a |
| SYN-120 | noncardiac_chest | general | 否 | T2，信心 medium | T3，信心 high | T9（備援 T3） | T9（備援 T3） | T9（備援 T3） | abc |
| SYN-136 | admin_followup | minimizer | 是 | T3，信心 high | T3，信心 high | T3 | T4 | T4 | bc |
| SYN-145 | admin_followup | family_proxy | 是 | T3，信心 high | T3，信心 high | T4 | T4 | T4 | abc |

## 參考非緊急卻被叫去急診（HS／T0）明細

| case | category | Opus | gpt | (a) | (b) | (c) |
|---|---|---|---|---|---|---|
| SYN-078 | heart_failure | T2，信心 medium | T1，信心 high | T0 | T9（備援 T3） | T9（備援 T3） |
| SYN-091 | arrhythmia_syncope | T2，信心 medium | T2，信心 high | T0 | T3 | T3 |
| SYN-092 | arrhythmia_syncope | T1，信心 medium | T1，信心 high | T0 | T9（備援 T3） | T9（備援 T3） |
| SYN-095 | arrhythmia_syncope | T2，信心 medium | T2，信心 high | T0 | T3 | T3 |
| SYN-106 | noncardiac_chest | T4，信心 medium | T4，信心 high | T9（備援 T1） | T0 | T0 |
| SYN-107 | noncardiac_chest | T3，信心 medium | T1，信心 medium | T0 | T0 | T0 |
| SYN-119 | noncardiac_chest | T4，信心 medium | T4，信心 high | T0 | T0 | T0 |

## 層間差異

- (a) 全資訊規則 vs (b) Scripted 病人 結果不同：24 例 ['SYN-014', 'SYN-030', 'SYN-035', 'SYN-040', 'SYN-044', 'SYN-057', 'SYN-068', 'SYN-078', 'SYN-081', 'SYN-086', 'SYN-091', 'SYN-092', 'SYN-093', 'SYN-095', 'SYN-096', 'SYN-105', 'SYN-106', 'SYN-110', 'SYN-112', 'SYN-116', 'SYN-121', 'SYN-129', 'SYN-131', 'SYN-136']
- (b) Scripted 病人 vs (c) Opus LLM 病人 結果不同：0 例 []
- (a) 全資訊規則 vs (c) Opus LLM 病人 結果不同：24 例 ['SYN-014', 'SYN-030', 'SYN-035', 'SYN-040', 'SYN-044', 'SYN-057', 'SYN-068', 'SYN-078', 'SYN-081', 'SYN-086', 'SYN-091', 'SYN-092', 'SYN-093', 'SYN-095', 'SYN-096', 'SYN-105', 'SYN-106', 'SYN-110', 'SYN-112', 'SYN-116', 'SYN-121', 'SYN-129', 'SYN-131', 'SYN-136']
- (b) Scripted 病人 結束原因：{'hard_stop': 46, 'gate_passed': 61, 'max_questions': 22, 'gate_passed_t0_asked': 5, 'hard_stop_opening': 5, 'no_more_questions': 11}
- (c) Opus LLM 病人 結束原因：{'hard_stop': 46, 'gate_passed': 61, 'max_questions': 22, 'gate_passed_t0_asked': 5, 'hard_stop_opening': 5, 'no_more_questions': 11}

## (c) LLM 病人忠實度（與事實清單比對，sim.run_llm_eval）

- 模型 claude-opus-5-5（claude-opus-5-5），effort medium，prompt 0.3；偏差紀錄 19 筆，分布 {'fabricated': 19}＝10 例、10 題（原題 10 筆＋複誦確認時重複同一答案 9 筆）；執行錯誤 0。

## 花費（依 repo PRICES 牌價估算，以帳單為準）

| 項目 | US$ |
|---|---|
| 生成（gpt-6.1-sol） | 0.8932 |
| 參考標註（Opus 5.5） | 2.2667 |
| 參考標註（gpt-6.1-sol） | 0.5651 |
| LLM 病人（Opus 5.5） | 8.7738 |
| 試跑（3 例：生成＋兩位標註＋LLM 病人；--pilot-cost-usd 命令列輸入，試跑輸出不在 repo） | 0.2161 |
| 合計 | 12.7149 |

## 執行錯誤與失敗

（無）

- (a)(b)(c) 跑完：150／150／150（共 150）
