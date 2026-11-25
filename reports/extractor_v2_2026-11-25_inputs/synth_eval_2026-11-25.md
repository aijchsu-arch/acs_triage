# 實驗 1：獨立合成病人驗證集評估 — 2026-11-25

- rules_version 0.12.0；情境檔 `data/synth/scenarios_synth_v1.yaml`（150 例）；參考標註 `data/synth/reference_synth_v1.json`；LLM 病人報告 `reports/eval_2026-11-25_llm_scenarios_synth_v1_opus-5-5_medium.json`

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

## 結論摘要（數字）

- 參考標註一致（tier 與 Hard stop 都相同）：130/150（86.7%，95% CI 80.2–91.7%）；只看 tier 一致：130/150。

### 參考一致子集（主分析）

| 層 | n | HS 敏感度 | Under-triage | 其中系統為 T9（依備援換算才較不急） | Over-triage | Exact | T9 比例 | 急診負擔（參考 T1–T4 卻 HS／T0） | 平均題數 |
|---|---|---|---|---|---|---|---|---|---|
| (a) 全資訊規則 | 130 | 51/51（100.0%，95% CI 93.0–100.0%） | 14/130（10.8%，95% CI 6.0–17.4%） | 9/130 | 21/130（16.2%，95% CI 10.3–23.6%） | 95/130（73.1%，95% CI 64.6–80.5%） | 16/130（12.3%，95% CI 7.2–19.2%） | 4/34（11.8%，95% CI 3.3–27.5%） | — |
| (b) Scripted 病人 | 130 | 49/51（96.1%，95% CI 86.5–99.5%） | 24/130（18.5%，95% CI 12.2–26.2%） | 14/130 | 20/130（15.4%，95% CI 9.7–22.8%） | 86/130（66.2%，95% CI 57.3–74.2%） | 20/130（15.4%，95% CI 9.7–22.8%） | 2/34（5.9%，95% CI 0.7–19.7%） | 6.65 |
| (c) Opus LLM 病人 | 130 | 49/51（96.1%，95% CI 86.5–99.5%） | 23/130（17.7%，95% CI 11.6–25.4%） | 12/130 | 20/130（15.4%，95% CI 9.7–22.8%） | 87/130（66.9%，95% CI 58.1–74.9%） | 18/130（13.8%，95% CI 8.4–21.0%） | 2/34（5.9%，95% CI 0.7–19.7%） | 6.55 |

### 全部 150 例（保守參考＝兩位標註者中較急者）

| 層 | n | HS 敏感度 | Under-triage | 其中系統為 T9（依備援換算才較不急） | Over-triage | Exact | T9 比例 | 急診負擔（參考 T1–T4 卻 HS／T0） | 平均題數 |
|---|---|---|---|---|---|---|---|---|---|
| (a) 全資訊規則 | 150 | 51/51（100.0%，95% CI 93.0–100.0%） | 26/150（17.3%，95% CI 11.7–24.4%） | 18/150 | 25/150（16.7%，95% CI 11.1–23.6%） | 98/150（65.3%，95% CI 57.1–72.9%） | 25/150（16.7%，95% CI 11.1–23.6%） | 6/43（14.0%，95% CI 5.3–27.9%） | — |
| (b) Scripted 病人 | 150 | 49/51（96.1%，95% CI 86.5–99.5%） | 37/150（24.7%，95% CI 18.0–32.4%） | 24/150 | 23/150（15.3%，95% CI 10.0–22.1%） | 89/150（59.3%，95% CI 51.0–67.3%） | 30/150（20.0%，95% CI 13.9–27.3%） | 3/43（7.0%，95% CI 1.5–19.1%） | 7.09 |
| (c) Opus LLM 病人 | 150 | 49/51（96.1%，95% CI 86.5–99.5%） | 36/150（24.0%，95% CI 17.4–31.6%） | 21/150 | 23/150（15.3%，95% CI 10.0–22.1%） | 90/150（60.0%，95% CI 51.7–67.9%） | 27/150（18.0%，95% CI 12.2–25.1%） | 3/43（7.0%，95% CI 1.5–19.1%） | 6.98 |

### 對 truth（D-52：最終裁定 48 例＋其餘一致標註 102 例；無 truth 0 例不計）

| 層 | n | HS 敏感度 | Under-triage | 其中系統為 T9（依備援換算才較不急） | Over-triage | Exact | T9 比例 | 急診負擔（參考 T1–T4 卻 HS／T0） | 平均題數 |
|---|---|---|---|---|---|---|---|---|---|
| (a) 全資訊規則 | 150 | 51/51（100.0%，95% CI 93.0–100.0%） | 13/150（8.7%，95% CI 4.7–14.4%） | 11/150 | 27/150（18.0%，95% CI 12.2–25.1%） | 104/150（69.3%，95% CI 61.3–76.6%） | 25/150（16.7%，95% CI 11.1–23.6%） | 10/57（17.5%，95% CI 8.8–29.9%） | — |
| (b) Scripted 病人 | 150 | 49/51（96.1%，95% CI 86.5–99.5%） | 26/150（17.3%，95% CI 11.7–24.4%） | 19/150 | 25/150（16.7%，95% CI 11.1–23.6%） | 95/150（63.3%，95% CI 55.1–71.0%） | 30/150（20.0%，95% CI 13.9–27.3%） | 7/57（12.3%，95% CI 5.1–23.7%） | 7.09 |
| (c) Opus LLM 病人 | 150 | 49/51（96.1%，95% CI 86.5–99.5%） | 25/150（16.7%，95% CI 11.1–23.6%） | 16/150 | 25/150（16.7%，95% CI 11.1–23.6%） | 96/150（64.0%，95% CI 55.8–71.7%） | 27/150（18.0%，95% CI 12.2–25.1%） | 7/57（12.3%，95% CI 5.1–23.7%） | 6.98 |

- truth 的最終裁定：`reports/synth_adjudication_2026-10-26_final.json`（AI 代理裁定（Fable 5.2，2026-11-25，Clinical Owner 授權），未經 Clinical Owner 逐例審閱）。

- 待 Clinical Owner 裁定：46 例（標註者不一致 20 例；系統任一層比任一位標註者不急 39 例）。

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
| chronic_stable | 15（全部 15） | — | 0/15 | 14/15 | 1/15 | 1/15 | 0/15 | — |
| family_proxy | 4（全部 5） | 2/2 | 0/4 | 0/4 | 4/4 | 0/4 | 1/5 | — |
| heart_failure | 10（全部 15） | 9/9 | 0/10 | 0/10 | 10/10 | 0/10 | 4/15 | — |
| noncardiac_chest | 8（全部 15） | 3/3 | 0/8 | 2/8 | 6/8 | 2/8 | 3/15 | — |
| post_pci | 14（全部 15） | 4/4 | 6/14 | 0/14 | 8/14 | 5/14 | 7/15 | — |
| unstable | 19（全部 20） | 5/5 | 4/19 | 0/19 | 15/19 | 4/19 | 5/20 | — |

### (b) Scripted 病人 × category

| category | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| acs_today | 24（全部 25） | 16/16 | 0/24 | 1/24 | 23/24 | 0/24 | 1/25 | 2.96 |
| admin_followup | 8（全部 10） | — | 2/8 | 0/8 | 6/8 | 0/8 | 2/10 | 5.62 |
| arrhythmia_syncope | 13（全部 15） | 4/6 | 6/13 | 0/13 | 7/13 | 3/13 | 7/15 | 5.77 |
| atypical | 15（全部 15） | 6/6 | 2/15 | 2/15 | 11/15 | 3/15 | 2/15 | 6.27 |
| chronic_stable | 15（全部 15） | — | 0/15 | 15/15 | 0/15 | 1/15 | 0/15 | 10.67 |
| family_proxy | 4（全部 5） | 2/2 | 0/4 | 0/4 | 4/4 | 0/4 | 1/5 | 4.5 |
| heart_failure | 10（全部 15） | 9/9 | 0/10 | 0/10 | 10/10 | 0/10 | 5/15 | 2 |
| noncardiac_chest | 8（全部 15） | 3/3 | 2/8 | 2/8 | 4/8 | 3/8 | 5/15 | 7.12 |
| post_pci | 14（全部 15） | 4/4 | 6/14 | 0/14 | 8/14 | 4/14 | 7/15 | 8.86 |
| unstable | 19（全部 20） | 5/5 | 6/19 | 0/19 | 13/19 | 6/19 | 7/20 | 10.53 |

### (c) Opus LLM 病人 × category

| category | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| acs_today | 24（全部 25） | 16/16 | 0/24 | 1/24 | 23/24 | 0/24 | 1/25 | 2.96 |
| admin_followup | 8（全部 10） | — | 2/8 | 0/8 | 6/8 | 0/8 | 2/10 | 5.62 |
| arrhythmia_syncope | 13（全部 15） | 4/6 | 6/13 | 0/13 | 7/13 | 3/13 | 7/15 | 5.77 |
| atypical | 15（全部 15） | 6/6 | 2/15 | 2/15 | 11/15 | 3/15 | 2/15 | 6.27 |
| chronic_stable | 15（全部 15） | — | 0/15 | 15/15 | 0/15 | 1/15 | 0/15 | 10.67 |
| family_proxy | 4（全部 5） | 2/2 | 0/4 | 0/4 | 4/4 | 0/4 | 1/5 | 4.5 |
| heart_failure | 10（全部 15） | 9/9 | 0/10 | 0/10 | 10/10 | 0/10 | 5/15 | 2 |
| noncardiac_chest | 8（全部 15） | 3/3 | 2/8 | 2/8 | 4/8 | 3/8 | 5/15 | 7.12 |
| post_pci | 14（全部 15） | 4/4 | 6/14 | 0/14 | 8/14 | 4/14 | 7/15 | 8.86 |
| unstable | 19（全部 20） | 5/5 | 5/19 | 0/19 | 14/19 | 4/19 | 6/20 | 9.84 |

### (a) 全資訊規則 × persona_style

| persona_style | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| anxious_exaggerating | 17（全部 21） | 5/5 | 1/17 | 4/17 | 12/17 | 0/17 | 4/21 | — |
| elderly_slow | 17（全部 21） | 3/3 | 2/17 | 4/17 | 11/17 | 2/17 | 4/21 | — |
| family_proxy | 24（全部 26） | 13/13 | 4/24 | 2/24 | 18/24 | 3/24 | 6/26 | — |
| general | 37（全部 41） | 13/13 | 5/37 | 8/37 | 24/37 | 5/37 | 7/41 | — |
| minimizer | 19（全部 21） | 12/12 | 1/19 | 2/19 | 16/19 | 0/19 | 2/21 | — |
| unclear | 16（全部 20） | 5/5 | 1/16 | 1/16 | 14/16 | 6/16 | 3/20 | — |

### (b) Scripted 病人 × persona_style

| persona_style | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| anxious_exaggerating | 17（全部 21） | 5/5 | 3/17 | 3/17 | 11/17 | 1/17 | 6/21 | 5.53 |
| elderly_slow | 17（全部 21） | 2/3 | 3/17 | 4/17 | 10/17 | 4/17 | 5/21 | 8.82 |
| family_proxy | 24（全部 26） | 13/13 | 5/24 | 2/24 | 17/24 | 2/24 | 7/26 | 5.42 |
| general | 37（全部 41） | 12/13 | 9/37 | 7/37 | 21/37 | 7/37 | 12/41 | 6.78 |
| minimizer | 19（全部 21） | 12/12 | 3/19 | 2/19 | 14/19 | 0/19 | 4/21 | 4.47 |
| unclear | 16（全部 20） | 5/5 | 1/16 | 2/16 | 13/16 | 6/16 | 3/20 | 9.62 |

### (c) Opus LLM 病人 × persona_style

| persona_style | n 一致 | HS 敏感度 | Under | Over | Exact | T9 | Under（全部，保守參考） | 平均題數 |
|---|---|---|---|---|---|---|---|---|
| anxious_exaggerating | 17（全部 21） | 5/5 | 3/17 | 3/17 | 11/17 | 1/17 | 6/21 | 5.53 |
| elderly_slow | 17（全部 21） | 2/3 | 3/17 | 4/17 | 10/17 | 4/17 | 5/21 | 8.82 |
| family_proxy | 24（全部 26） | 13/13 | 4/24 | 2/24 | 18/24 | 1/24 | 6/26 | 5.17 |
| general | 37（全部 41） | 12/13 | 9/37 | 7/37 | 21/37 | 6/37 | 12/41 | 6.59 |
| minimizer | 19（全部 21） | 12/12 | 3/19 | 2/19 | 14/19 | 0/19 | 4/21 | 4.47 |
| unclear | 16（全部 20） | 5/5 | 1/16 | 2/16 | 13/16 | 6/16 | 3/20 | 9.62 |

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
| SYN-036 | unstable | general | 是 | T0，信心 high | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T2 | abc |
| SYN-067 | post_pci | anxious_exaggerating | 否 | T1，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T2 | abc |
| SYN-081 | heart_failure | anxious_exaggerating | 否 | T1，信心 medium | T0，信心 high | T1 | T2 | T2 | abc |
| SYN-086 | heart_failure | elderly_slow | 否 | T1，信心 medium | T0，信心 high | T1 | T2 | T2 | abc |
| SYN-129 | atypical | minimizer | 是 | T0，信心 medium | T0，信心 high | T0 | T2 | T2 | bc |
| SYN-006 | acs_today | unclear | 否 | T0，信心 medium | T9，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-028 | unstable | general | 否 | T1，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-033 | unstable | family_proxy | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-040 | unstable | family_proxy | 是 | T0，信心 medium | T0，信心 high | T0 | T9（備援 T1） | T0 | b |
| SYN-041 | unstable | unclear | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-043 | unstable | general | 是 | T0，信心 medium | T0，信心 high | T9（備援 T1） | T9（備援 T1） | T9（備援 T1） | abc |
| SYN-044 | unstable | elderly_slow | 是 | T0，信心 high | T0，信心 high | T0 | T9（備援 T1） | T9（備援 T1） | bc |
| SYN-063 | post_pci | general | 是 | T0，信心 high | T0，信心 high | T1 | T1 | T1 | abc |
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
| SYN-110 | noncardiac_chest | family_proxy | 否 | T3，信心 medium | T2，信心 medium | T3 | T3 | T3 | abc |
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

- (a) 全資訊規則 vs (b) Scripted 病人 結果不同：22 例 ['SYN-014', 'SYN-040', 'SYN-044', 'SYN-055', 'SYN-057', 'SYN-068', 'SYN-078', 'SYN-081', 'SYN-086', 'SYN-091', 'SYN-092', 'SYN-093', 'SYN-095', 'SYN-096', 'SYN-105', 'SYN-106', 'SYN-112', 'SYN-116', 'SYN-121', 'SYN-129', 'SYN-131', 'SYN-136']
- (b) Scripted 病人 vs (c) Opus LLM 病人 結果不同：3 例 ['SYN-036', 'SYN-040', 'SYN-067']
- (a) 全資訊規則 vs (c) Opus LLM 病人 結果不同：23 例 ['SYN-014', 'SYN-036', 'SYN-044', 'SYN-055', 'SYN-057', 'SYN-067', 'SYN-068', 'SYN-078', 'SYN-081', 'SYN-086', 'SYN-091', 'SYN-092', 'SYN-093', 'SYN-095', 'SYN-096', 'SYN-105', 'SYN-106', 'SYN-112', 'SYN-116', 'SYN-121', 'SYN-129', 'SYN-131', 'SYN-136']
- (b) Scripted 病人 結束原因：{'hard_stop': 46, 'gate_passed': 64, 'max_questions': 17, 'gate_passed_t0_asked': 5, 'hard_stop_opening': 5, 'no_more_questions': 13}
- (c) Opus LLM 病人 結束原因：{'hard_stop': 46, 'gate_passed': 67, 'max_questions': 14, 'gate_passed_t0_asked': 5, 'hard_stop_opening': 5, 'no_more_questions': 13}

## (c) LLM 病人忠實度（與事實清單比對，sim.run_llm_eval）

- 模型 claude-opus-5-5（claude-opus-5-5），effort medium，prompt 0.3；偏差紀錄 22 筆，分布 {'fabricated': 22}＝13 例、13 題（原題 13 筆＋複誦確認時重複同一答案 9 筆）；執行錯誤 0。

## 花費（依 repo PRICES 牌價估算，以帳單為準）

| 項目 | US$ |
|---|---|
| 生成（gpt-6.1-sol） | 0.8932 |
| 參考標註（Opus 5.5） | 2.2667 |
| 參考標註（gpt-6.1-sol） | 0.5651 |
| LLM 病人（Opus 5.5） | 9.7886 |
| 試跑（3 例：生成＋兩位標註＋LLM 病人；--pilot-cost-usd 命令列輸入，試跑輸出不在 repo） | 0.0000 |
| 合計 | 13.5136 |

## 執行錯誤與失敗

（無）

- (a)(b)(c) 跑完：150／150／150（共 150）
