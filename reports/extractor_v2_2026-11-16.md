# 抽取器 v2 與閉環模擬（D-52 第 3 項；D-56）— 2026-11-16

> **限制（先讀）**
>
> 1. **合成病人**：病人回答由 Opus 5.5 依情境事實（hidden sheet）生成，句子比真實病人完整、少答非所問；正確答案＝情境事實（開發集為單一裁定者 truth，本輪依 D-56 有 12 例 T3 → T2）。這是一致性檢查，不是準確度，不能外推臨床表現。
> 2. **合成語音或沒有語音**：階段 A 的 phone 條件是 macOS `say` 合成標準國語＋模擬電話線路＋本機 Whisper（D-49），是樂觀上限；階段 B 閉環完全沒有語音（病人文字直接進抽取器），等於 STT 完美。
> 3. **LLM 參考標註**：保留集的「對照答案」是 Opus 5.5 與 gpt-6.1-sol 的獨立標註（暫定），不是 truth；主分析用兩位標註者一致的子集。保留集本輪只看 `sim.synth_eval` 的彙總行（D-52）。
> 4. **雲端模型不可用於真實資料**：gpt-6.1-sol 只是「抽取能力上限」參考；真實病人資料不得送外部 API（D-10）。院內可部署的候選是本機模型（Gemma）。全部資料為合成資料。
> 5. **病人回答重用（配對設計）**：閉環病人以「對話前綴快取」包一層，gpt 與 Gemma 兩個 arm 共用快取。最終版（裁定 #3）的種子是 11-17 結構化值逐字稿（`reports/eval_2026-11-17_llm_opus-5-5_medium_transcripts.json`），之前的批次是 11-16 逐字稿。問句序列相同時重用同一個樣本，序列一分岔才是新的 API 呼叫。
> 6. **開發集調整過；提示未凍結；保留集閉環未執行**：本報告的閉環與重放數字全部來自開發集，偏樂觀。
>
> 本報告為人工撰寫（沒有用 `sim.extractor_v2_report` 產生，原因見 §8）；每個數字的來源檔列在各節，彙總另存 `reports/extractor_v2_2026-11-16.json`。

## 1. 結論（人工撰寫，依本報告數字）

**本報告的範圍與版本（最終版）**：
- rules 0.11.0、題庫 bank **0.7**（D-56 裁定 #3：0.6 → 0.7）、`max_questions` 18、抽取器提示 **2.0-dev27**（送出的提示全文與 dev27 相同）。
- 包含 D-56 R7–R9、2026-11-16 的 truth 與 5 項細節、2026-11-17 裁定 #3（「改成提到就問一次確認」）。HEAD 057f8d1，工作樹未 commit。
- pytest **721** passed。

這份報告前後經過三批付費執行：
- **「11-16 批」**（防護前程式，`sim/llm_extract_v2.py` `5845a1fd…`）：
  - Opus 病人 eval（11-16）；
  - gpt 閉環（11-16 23:14–23:26）；
  - Gemma 閉環（11-17 08:09–08:14）；
  - gpt 重放（11-17 08:09–08:20）；
  - Gemma 重放（11-16 23:09–23:54）。
- **「11-17 按壓證據防護版」**（`palpation_pain()`，`19f23b57…`；**已取代**）：
  - 以 11-16 批快取重跑閉環；
  - 這個防護兩輪對抗探針都找到誤採用，已撤回、程式已刪（見 D-56）。
- **「11-17 最終版（裁定 #3 旗標）」**（`57b3950d…`，與目前工作樹逐檔相同）：
  - Opus 病人 eval（11-17）；
  - 結構化值、gpt、Gemma 三個閉環 arm（11-17 21:58–22:00）。
- 重放沒有重跑：以快取、用目前的 parse 離線重算，四格逐例不變（§3.2）。

輸入檔（`reports/extractor_v2_2026-11-16_inputs/`）：
- **最終版**：閉環 `closed_dev_structured_final_flag.json`（自我檢查 119/119）、`closed_dev_gpt_final_flag.json`、`closed_dev_gemma_final_flag.json`；重放 `v2_replay_gpt.json`、`v2_replay_gemma.json`。
- **已取代**：
  - 11-17 按壓證據防護版：`closed_dev_gpt_final.json`、`closed_dev_gemma_final.json`；
  - 11-16 批：`closed_dev_structured.json`、`closed_dev_gpt.json`、`closed_dev_gemma_1116_superseded.json`。
- **執行紀錄**：`logs/`，scratch 與 repo 路徑已改寫成 `<scratch>`／`<repo>`。
- **離線重算**：`guard_rescore/`。`flag_replay_*` 是裁定 #3 版；`cl_*_v2`、`replay_*_v2`、`tightened_*` 是已撤回的按壓證據防護版。

### 結論
1. **Hard stop 沒有漏、沒有 under-triage（最終版）**：
   - 開發集閉環三個 arm 都是 HS 27/27，premature 0、假 Hard stop 0、under 0。
   - 11-16 批的 Gemma 有 under 1（S-MID-16，truth T2 → T3）。這例先促成按壓證據防護，最後由裁定 #3 取代；最終版是 T2＝truth。
   - **D-34 正式紀錄改為 11-17 的 Opus 病人評估**（`reports/eval_2026-11-17_llm_opus-5-5_medium.md`）：HS miss 0/27、under 0、over 0、exact 100%，「最終結果與 Scripted 不同的 case」**0 例**，病人偏差 2（皆 fabricated），估算 US$5.659。11-16 的結果相同，保留為歷史紀錄。
2. **exact（對 11-16 truth；11-05 是對當時的 truth，12 例 truth 不同，只能概略比較）**：
   - gpt：11-05 115 → 最終版 114（95.8%）；over 2 → 2。
   - Gemma：11-05 115 → 11-16 批 112 → 最終版 113（95.0%）；over 2 → 2。
   - 偏差全部是較急或同級：T0；或 T9，而 T9 的備援都是 T1。
3. **與結構化值不同**：gpt 5 例、Gemma 6 例（結構化值 arm 全部＝truth；見下表）。和按壓證據防護版是同樣的 case、同樣的題數與結果。原因：
   - 裁定 #12「不太會喘」被抽成 exertional_heavy，H3 兩題答不知道 → 18 題 T9：gpt 3 例、Gemma 2 例；
   - Gemma 把「有沒有喘我說不上來」抽成 heavy → 同一機制，1 例；
   - S-MID-08#2 → T0-NEW-TODAY（gpt 活動關係沒抽到；Gemma 把「休息後緩解」誤抽成 rest_symptom＝true）；
   - S-MID-13 裁定 #14 → T0；
   - Gemma S-INSUF-07 頻率誤抽 → T0。
4. **裁定 #3 在閉環裡**：旗標觸發的 Q-REPRO-01，gpt 問了 2 通、Gemma 問了 4 通，結果都＝truth，每通多 1 題。
   - S-MID-14、S-MID-14#0：第 5 題，病人答「會」→ T3／T0。
   - S-MID-14#1：旗標有設，但第 4 題已 Hard stop，沒問。
   - Gemma S-MID-16：第 5 題，病人答不確定，Gemma 卻抽成 false → T2。
   - Gemma S-MID-16#0：第 6 題，答不確定 → 未知 → T0。
   - gpt 在 S-MID-16 系列沒有設旗標，所以沒問。
   - 平均題數：gpt 7.19 → 7.21、Gemma 7.13 → 7.16（相對按壓證據防護版）。
5. **上限 18**：
   - 平均題數（11-05 → 最終版）：結構化值 6.23 → 6.50、gpt 6.65 → 7.21、Gemma 6.92 → 7.16。
   - 停在上限：結構化值 11 例，全部 truth T9。gpt 15 例＝12 例 truth T9＋3 例 #12／H3 型。Gemma 14 例＝11＋3。
   - Gemma S-INSUF-02#1 在第 16 題定案 T2＝truth。
   - H3 兩題答不知道的一型，與題數多少無關。
6. **R8**：閉環開場白 Gemma「前天開始」「這兩天」2.0 → 0.29 週（S-MID-19 系列 5 例、S-INSUF-07 系列 3 例）。R8 的程式防護（`onset_days_as_weeks`）在付費執行中觸發 0 次。
7. **R9**：所有閉環與重放的抽取呼叫失敗 0、需要重試 0。
   - 11-05 gpt 重放第一次因逾時漏掉的 3 例 Hard stop，本輪都是 Hard stop：S-MID-01#2、S-MID-05#0、S-MID-12#1。
   - 重試路徑本輪沒有被真實錯誤觸發，只有假 client 測試涵蓋。
8. **階段 A 重放（11-05 dev26 → 11-16 dev27）**：
   - gpt 原文：HS miss 0 → 1、exact 72.3% → 73.9%。HS miss 增加不是退步：S-MID-10#0 的 premature 在 11-05 被逾時遮住，本輪 0 失敗、重新出現。
   - gpt 電話：3／69.7% 不變。
   - Gemma 原文：1／73.9% → 1／74.8%。
   - Gemma 電話：1／72.3% → 1／70.6%。
   - 用裁定 #3 的 parse 離線重算，四格逐例不變。
9. **保留集**（與開發集分開；只看彙總行；參考一致子集 130 例）：
   - (a) HS 51/51、under 14 → 14、over 8 → 21、exact 108 → 95。
   - (b) HS 49/51、under 26 → 24、over 7 → 20、exact 97 → 86、T9 22 → 20、平均 6.29 → 6.65 題。
   - 裁定 #3 的免費驗證中，(a)(b)(c) 都與加旗標前逐欄相同（D-56）。
   - (c) 沒有用新的 LLM 病人重跑。
10. **費用**（依 repo PRICES 估算，以帳單為準；算式見 §6）：
    - Anthropic US$17.0185；
    - OpenAI US$5.3047；
    - 合計 US$22.3232；
    - Gemma 本機不計費。

### 11-05 與本輪並列（開發集 119 例）

| 項目 | 11-05（2.0-dev26、rules 0.10.0、上限 15、bank 0.6） | 11-16 批（防護前） | 11-17 按壓證據防護版（已取代） | **11-17 最終版（裁定 #3、bank 0.7）** |
|---|---|---|---|---|
| Opus 病人評估（結構化值）HS／under／over／exact | 27/27／0／0／100% | 27/27／0／0／100%（與 Scripted 不同 0） | 同 11-16 | 27/27／0／0／100%（與 Scripted 不同 0；偏差 2） |
| 閉環 結構化值 exact／T9／平均題數／複誦 | 100%／12／6.23／168 | 100%／12／6.50／170 | 同 11-16 | 100%／12／6.50／170（與 11-16 逐例相同；自我檢查 119/119） |
| 閉環 gpt HS／under／假 Hard stop／over／exact／T9／平均題數／複誦（再問） | 27/27／0／0／2／96.6%（115）／14／6.65／198（0） | 27/27／0／0／2／95.8%（114）／15／7.20／200（0） | 27/27／0／0／2／95.8%（114）／15／7.19／200（0） | 27/27／0／0／2／95.8%（114）／15／7.21／200（0） |
| 閉環 Gemma 同上（再問、再問後較不急） | 27/27／0／0／2／96.6%（115）／14／6.92／212（1、0） | 27/27／**1**／0／2／94.1%（112）／14／7.13／208（1、0） | 27/27／0／0／2／95.0%（113）／14／7.13／208（1、0） | 27/27／0／0／2／95.0%（113）／14／7.16／208（0、0） |
| 重放 gpt 原文 HS miss／exact／abstention FP／被問那題正確 | 0／72.3%／33／613 | 1／73.9%／31／615 | 離線重算逐例相同 | 離線重算逐例相同 |
| 重放 gpt 電話 HS miss／exact／abstention FP | 3／69.7%／36 | 3／69.7%／36 | 同上 | 同上 |
| 重放 Gemma 原文 HS miss／over／exact／abstention FP | 1／1／73.9%／29 | 1／1／74.8%／28 | 同上 | 同上 |
| 重放 Gemma 電話 HS miss／over／exact／abstention FP／紅旗「有」漏抽 | 1／1／72.3%／32／0 | 1／0／70.6%／35／0 | 同上 | 同上 |
| robustness 翻轉／較不急／嚴重降級 | 1,418／167／8 | 1,483／170／8（仍全為 Q-CHARACTER-01） | — | 與加旗標前逐筆相同（D-56） |

來源：
- 11-05：`reports/extractor_v2_2026-11-05_inputs/`、`reports/eval_2026-11-05_llm_opus-5-5_medium.md`、`reports/robustness_2026-11-05.md`。
- 11-16：本目錄 inputs、`reports/eval_2026-11-16_llm_opus-5-5_medium.{md,json}`、`reports/robustness_2026-11-16.md`。
- 11-17：`closed_dev_*_final.json`、`closed_dev_*_final_flag.json`、`reports/eval_2026-11-17_llm_opus-5-5_medium.{md,json}`、`guard_rescore/`。

### 保留集 (a)(b)（與開發集分開；免費重算；參考一致子集 130 例）

重算指令：`python -m sim.synth_eval --llm-json reports/eval_2026-11-05_llm_scenarios_synth_v1_opus-5-5_medium.json --out <scratch>/synth1116`，rules 0.11.0。只看彙總行，沒有逐例閱讀。HEAD 057f8d1 的數字來自 `<scratch>/d56/synth/head_summary.json`。

| 保留集 | HEAD 057f8d1（rules 0.10.0、上限 15） | 最終版（rules 0.11.0、上限 18） |
|---|---|---|
| (a) 全資訊規則 HS／under／over／exact／T9 | 51/51／14／8／108／16 | 51/51／14／21／95／16 |
| (b) Scripted HS／under（其中 T9）／over／exact／T9／平均題數 | 49/51／26／7／97／22／6.29 | 49/51／24（14）／20／86／20／6.65 |
| 保守參考（150 例）(b) under／over | 39／10 | 37／23 |
| (c) Opus LLM 病人 | 11-05 逐字稿 | **未以新的 LLM 病人重跑**（病人聽到的措辭未改；上限改動由 (b) 涵蓋） |

- over 與 exact 的變化來自 R7：有胸部症狀至少 T2，參考標註是在 R7 之前做的。逐例方向見 D-56 免費驗證段；本報告沒有逐例閱讀保留集。
- (b) 全部 150 例的平均題數，上限 15 → 18 是 6.72 → 7.09（`<scratch>/d56/out/holdout_cap_cost.json`）。
- 這個指令的 (c) 層只是重放 11-05 的舊逐字稿：14 例「重放結果≠逐字稿」，不作為本輪結果。
- 裁定 #3 的免費驗證：(a)(b)(c) 與加旗標前逐欄相同（D-56，證據在 `<scratch>/d56repro/synth_base`、`synth_new`）。

### 與結構化值不同的 case（11-17 最終版；結構化值 arm 全部＝truth；逐例以最終 slot 重算確認）

重算方式：
- 把該 arm 結束時的 `final_slots` 放進 `RulesEngine.decide`，T9 再用 `tier9_fallback`。
- 「重算」欄是把錯的欄位改回病人事實（或結構化值）後的結果。
- 腳本 `<scratch>/report1117/recompute.py`、`cf2.py`，不呼叫模型。
- 下表 7 例在最終版與按壓證據防護版的問題序列、題數、結果都相同（逐例比對）。

| case | truth | gpt | Gemma | 11-05 gpt／Gemma | 原因（證據在閉環 JSON 的 turns） |
|---|---|---|---|---|---|
| S-ACUTE-05#1 | T2（D-56 由 T3 改） | T9（18 題，備援 T1） | T2 | T9／T3 | gpt：裁定 #12。Q-DYSPNEA-GRADE-01「我其實不太會喘，主要是胸口悶悶的而已」→ exertional_heavy；複誦「不是喔，我是不會喘…」依 D-50 取較嚴重，仍是 heavy。Q-DYSPNEA-ACUTE-01「我其實沒有在喘耶，所以也說不上是忽然還是慢慢變的」→ 未知 → 只缺 dyspnea_acute，問到 18 題 → T9。重算：dyspnea 改 none → T3-STABLE-REST-RECURRENT＋T2-CHEST-FLOOR＝T2。11-05 同一機制，當時缺的是 orthopnea_pnd |
| S-MID-01 | T1 | T9（18 題，備援 T1） | T9（18 題，備援 T1） | T1／T9 | 兩個 arm 都是裁定 #12：「我其實不太會喘耶，平常走路做家事都還好，休息的時候也不會」→ heavy。<br>gpt：Q-ORTHO-01「這個我就不太確定耶」、Q-DYSPNEA-ACUTE-01「說不上來」→ 缺 orthopnea_pnd、dyspnea_acute。<br>Gemma：Q-DYSPNEA-ACUTE-01 抽成 false，只缺 orthopnea_pnd。<br>重算：dyspnea 改 none → T1-NEW-YESTERDAY（急迫度同 truth） |
| S-MID-02 | T2 | T2 | T9（18 題，備援 T1） | T2／T0 | Gemma：Q-DYSPNEA-GRADE-01「喘的話我不太確定耶，我主要是快走上坡的時候胸口會悶，有沒有喘我說不上來」→ exertional_heavy（結構化值為未知，屬自編）。Q-DYSPNEA-ACUTE-01「喘的部分我真的不清楚耶」→ 缺 dyspnea_acute → 18 題 T9。重算：dyspnea 改回未知 → T2-NEW-STABLE-WEEKS。11-05 Gemma 的 T0 是另一機制（rest_symptom 誤抽），本輪沒有出現 |
| S-MID-08 | T2（D-56 由 T3 改） | T9（18 題，備援 T1） | T9（18 題，備援 T1） | T9／T3 | 兩個 arm 都是裁定 #12：「我不太會喘耶，主要是走路的時候胸口有點悶而已」→ heavy。Q-ORTHO-01「這個我沒有特別注意耶，不太確定」→ 缺 orthopnea_pnd（Gemma 另缺 dyspnea_acute）。重算：dyspnea 改 none → T3-POST-PCI-MILDER＋T2-CHEST-FLOOR＝T2。11-05 gpt 的 T9 原因是 Q-TIMING-01 抽成 null；本輪 gpt 抽成 unknown，已不是原因 |
| S-MID-08#2 | T1 | T0（8 題） | T0（9 題） | T0／T1 | gpt：開場白「最近走路會有一點悶」不抽 exertion_relation（同 11-05；dev26 已刪規則 17）→ DV-4 不適用 → 新發、時序 unknown → T0-NEW-TODAY。<br>Gemma：開場白有 exertion_only，但 Q-ONGOING-01「現在坐著休息就沒什麼感覺了」被抽成 rest_symptom＝true（D-55 第 2 項「休息後緩解」型），DV-4 不適用 → T0-NEW-TODAY。<br>重算：gpt 補 exertion_only、或 Gemma 的 rest 改 false／未知 → 都不再是 T0（還缺題；結構化值問完是 T1-ANTIPLT-SYMPTOMATIC）。方向較急 |
| S-MID-13 | T2（D-56 由 T3 改） | T0（6 題） | T0（7 題） | T0／T0 | 裁定 #14：Q-EXERTION-01「吃飽坐著」→ rest_symptom（Clinical Owner 接受為偏急）→ T0-REST-NEW。Q-REST-02 答不確定；T0 不因 gate 變 T9。與 11-05 相同 |
| S-INSUF-07 | T9 | T9 | T0（5 題） | T9／T9 | Gemma：第三人來電。Q-ONSET-01「這個我不太確定耶，他這兩天才跟我說不舒服，但以前有沒有過一樣的感覺，我不清楚。」→ episode_frequency_increased＝true（evidence「他這兩天才跟我說不舒服」）→ T0-FREQ-INCREASED。重算：該欄改回未知 → T9-THIRD-PARTY-UNREACHABLE（備援 T1，附 family_relay_safety_net）。較急方向；D-56 11-17 已知限制 (c) |

- 11-16 批的 Gemma 另有 **S-MID-16**：truth T2，Gemma T3（12 題）。重算：T3-MECHANICAL＋T3-COUGH＝T3；reproducible_mechanical 改回未知 → T3-COUGH＋T2-CHEST-FLOOR＝T2。見下一節。
- gpt S-MID-07（11-16 → 11-17 按壓證據防護版）：
  - 11-16 執行時，同一句開場白在 4 個變體間抽取結果不同：S-MID-07、#0 沒有 onset_new；#1、#2 是 false。這是 D-55 (10) 快取併發競態，快取只留最後一筆（false）。
  - 11-17 只用快取，開場白就有 onset_new＝false，少問 Q-ONSET-01（8 → 7 題）。
  - 三版都是 T1＝truth。

### 依原因量化（開發集 119 例；exact 的分母含 truth T9）
- **gpt exact 114**：與結構化值不同 5 例。
  - 原因：#12＋H3 3 例（S-ACUTE-05#1、S-MID-01、S-MID-08）、活動關係沒抽到 1 例（S-MID-08#2）、#14 1 例（S-MID-13）。
  - over 2：S-MID-08#2、S-MID-13。
  - T9 而 truth 非 T9：3 例，備援都是 T1。
- **Gemma exact 113**：與結構化值不同 6 例。
  - 原因：#12＋H3 2 例（S-MID-01、S-MID-08）、「不確定」被抽成 heavy＋H3 1 例（S-MID-02）、rest_symptom 誤抽 1 例（S-MID-08#2）、#14 1 例（S-MID-13）、頻率誤抽 1 例（S-INSUF-07）。
  - over 2：S-MID-08#2、S-MID-13。另有 abstention FN 1：S-INSUF-07，truth T9 → T0。
- **停在 18 題上限、truth 不是 T9**：gpt 3 例、Gemma 3 例，全部是「dyspnea_grade 抽成 exertional_heavy、病人對 H3 題答不知道」。上限再高也不會結束。

### reproducible_mechanical：從 S-MID-16 到裁定 #3

**發現**：11-16 批 Gemma 閉環的 S-MID-16 under-triage。
- 該 run 實際執行時間是 11-17 08:09–08:14，檔案 `closed_dev_gemma_1116_superseded.json`。
- Gemma 抽成 reproducible_mechanical＝true 的句子：
  - Q-ONGOING-01「現在沒有，現在沒在咳就不會痛。」；
  - Q-CHARACTER-01「比較像是會痛，就咳嗽的時候胸口會痛。」（含複誦回答）；
  - Q-EXERTION-01「…我只知道是咳嗽的時候會痛…」。
- 系統因此走 T3-MECHANICAL（R7 下限的例外）定案 T3；truth T2（裁定 (3)：T3-COUGH 不是例外）。
- 欄位已經填了，所以 Q-REPRO-01 沒有問。
- gpt 同一例沒有抽出 true，T2＝truth。

**處理經過（D-56 2026-11-17 段；同日三輪）**：
- **#1**：順口的 true 一律不採用。離線重跑時 S-MID-14 先問 Q-ONSET-01，定案 T0（truth T3）。
- **#2**：「按壓會痛，維持T3」，用 `palpation_pain()` 判斷原句。
  - 本報告上一版的閉環與重放離線重算都是這一版：`closed_dev_*_final.json`、`guard_rescore/cl_*_v2`、`replay_*_v2`、`tightened_*`。
  - 兩輪對抗探針都找到誤採用，已撤回、程式已刪。
- **#3（最終）**：「改成提到就問一次確認」。
  - LLM 抽取器路徑上，開場白與其他題回答（含複誦、再問回覆）裡的 true 都不寫入，只記旗標 `reproducible_mechanical_mentioned`。
  - reproducible_mechanical 仍未知時，Prompter（`repro_confirm_question`；`sim/runner.py` 為此改 2 行）在紅旗題問完後的第一個機會問一次 Q-REPRO-01，計入題數。
  - Hard stop 不問；T0 只在只靠 T0-NEW-TODAY 時問。
  - 只有直接回答寫入。
  - 關鍵詞路徑不變（已知限制 (a)）。

**最終版閉環裡問到 Q-REPRO-01 的通話（實際付費執行）**：

| case | truth | arm | 第幾題（總題數） | 病人回答 | 抽取 | 結果 |
|---|---|---|---|---|---|---|
| S-MID-14（旗標來自開場白「胸口肌肉按下去會痛」） | T3 | gpt、Gemma | 第 5 題（12 題，+1） | 「會，按胸口跟深呼吸的時候會痛，不過走路倒不會更痛。」 | true | T3＝truth |
| S-MID-14#0（同上） | T0 | gpt、Gemma | 第 5 題（7 題，+1） | 「會耶，用手按胸口跟深呼吸的時候會痛，不過走路倒是不會比較痛。」 | true | T0＝truth |
| S-MID-14#1（同上） | Hard stop | gpt、Gemma | 沒問：第 4 題 Q-DIAPH-01 已 Hard stop | — | — | Hard stop＝truth |
| S-MID-16（旗標來自 Q-ONGOING-01「現在沒在咳就不會痛」） | T2 | Gemma | 第 5 題（13 題，+1） | 「這個我不太確定耶，沒有特別注意按壓或深呼吸會不會痛，我只知道咳嗽的時候會痛。」 | **false**（結構化值為未知；Gemma 自編否認） | T2＝truth |
| S-MID-16#0（旗標來自 Q-CHARACTER-01 複誦回覆，依 D-56；閉環 JSON 的 turns 不記複誦的抽取） | T0 | Gemma | 第 6 題（9 題，+1） | 「這個我沒有特別注意耶，按胸口或深呼吸會不會痛我不太確定。」 | 未知 | T0＝truth |
| S-MID-16、S-MID-16#0 | T2、T0 | gpt | 沒問：gpt 沒有抽出 true、沒有旗標 | — | — | T2、T0＝truth |

- 另外，停在 18 題上限的通話照原本題序在後段問到 Q-REPRO-01，不是旗標觸發的：
  - gpt 15 通、Gemma 14 通、結構化值 11 通；
  - 病人全部答不確定 → 未知，結果都是 T9。
- 最終版相對按壓證據防護版，問題序列有變的只有：gpt S-MID-14、#0；Gemma S-MID-14、#0、S-MID-16、#0。最終結果全部相同。
- Gemma 的再問由 1 次變 0 次：防護版的 S-MID-14 Q-CHARACTER-01 再問，因序列改變而不再發生。
- **與離線預測一致**：實作者在付費重跑前，以快取、無快取時用情境事實代答的方式做了離線重跑（`<scratch>/d56repro/flag_cl_*.json`）。它與付費最終版逐例相同，包括問題序列與最終結果。

**重放不受影響**（新證據，本報告產生，不呼叫模型）：
- 以 11-16 批重放快取的模型原始輸出、用目前（裁定 #3）的 parse 重算，存在 `guard_rescore/flag_replay_{gpt,gemma}.json`。
- 四個 cell 的逐例最終結果與原始重放（防護前）完全相同。cache miss 0、extract_failed 0。
- 不採用的順口 true：
  - gpt 2 句：S-MID-14 開場白，原文與電話；
  - Gemma 6 句：S-MID-14 開場白 2 句，S-MID-16 的 Q-ONGOING-01、Q-REST-01 回答 4 句（原文、電話）。
- 為什麼結果不變：重放的對話固定、不會補問 Q-REPRO-01。S-MID-14 在原始重放本來就停在 T9，因為固定逐字稿走不到 gate；其他句子都不是分級的決定因素。

### R8 時序單位（「前天開始」「這兩天」）

閉環開場白的 onset_weeks_ago，比較 11-05 dev26 → 本輪 dev27。最終版與按壓證據防護版的開場白抽取逐例相同，只多了旗標欄位。

| 開場白說法 | case（變體數） | gpt | Gemma | 分級 |
|---|---|---|---|---|
| 「前天開始走路會胸悶」 | S-MID-19（5） | 0.2857 → 0.29 | **2.0 → 0.29** | 5 例兩個 arm＝truth（11-05 也是） |
| 「這兩天說胸口不太舒服」 | S-INSUF-07（3） | null → 0.29 | **2.0 → 0.29** | gpt 3 例＝truth；Gemma S-INSUF-07 T0（頻率誤抽，與時序無關），#0、#1＝truth |
| 「這兩天心跳有時候會突然很快」 | S-MID-05（3） | null → 0.29 | null → 0.29 | 3 例＝truth |
| 「這兩個禮拜」 | S-MID-03（2）、S-MID-11 | null、2.0 不變 | S-MID-03 null → 2.0；S-MID-11 2.0 不變 | ＝truth |
| 「最近走路會有一點悶」（上個月放支架） | S-MID-08（4） | null | 1.0 不變（事實 1 週；開場白沒說發作多久） | 見上表 |
| 「這幾天偶爾不太舒服」 | S-INSUF-02 | null | null → 0.29（提示沒有這個例句） | T9＝truth |

- 方向：11-05 擔心的 Gemma「2.0 週 → T2-NEW-STABLE-WEEKS」潛在 under-triage，本輪閉環沒有出現。
- R8 回答句防護（`onset_days_as_weeks`）在付費閉環與重放都觸發 0 次（各執行的 guards 統計）。
- D-56 本機探針（`<scratch>/d56/probe/`）：
  - Gemma 開場白 dev26 → dev27，各 5 次：S-MID-19 2.0 → 0.29、S-INSUF-07 2.0 → 0.29、S-MID-03 None → 2.0、S-MID-08 1.0 → 1.0、S-STABLE-04 12.0 → None。
  - gpt dev27，各 3 次：S-MID-19 0.29、S-INSUF-07 0.29、S-MID-08 None。
- D-56「付費閉環須再確認」的 gpt S-MID-12 開場白：付費閉環 3 個變體都抽成 exertion_only（11-05 是 null；事實沒有）。分級不受影響：T2、T0、Hard stop 都＝truth。

### R9 抽取呼叫逾時與重試（逾時 600 秒；逾時、5xx、連線錯誤最多重試 2 次）
- 失敗 0：
  - 閉環 `extract_failures` 全部是空的。新呼叫數：gpt 11-16 批 868、防護版 2、最終版 7；Gemma 11-16 批 192、防護版 0、最終版 19。
  - gpt 重放：1,235 個不同呼叫（`logs/v2_replay_gpt.log`；JSON `n_calls` 1,250）。Gemma 重放 1,250。
  - 重放與 11-16／11-17 防護版的六個抽取快取，紀錄全部 ok、`retry_errors` 0 筆。
  - 最終版：gpt、Gemma 兩個 arm 的 `extractor_usage.failed` 都是 0。
- **11-05 gpt 重放第一次逾時造成的 3 例 Hard-stop miss**：本輪 gpt 重放原文與電話兩個 cell 都抽對，三例都不在 HS miss 名單。
  - S-MID-01#2 Q-DIAPH-01「有，那時候有冒冷汗。」→ diaphoresis＝true；
  - S-MID-05#0 Q-SYNCOPE-01「有耶，那時候有覺得快要昏倒的感覺。」→ presyncope＝true；
  - S-MID-12#1 Q-DYSPNEA-GRADE-01「現在連坐著休息的時候也會覺得喘。」→ rest。
- **限制**：
  - 本輪沒有發生逾時或 5xx，「重試後成功」沒有實測，只有 D-56 的假 client 測試涵蓋。
  - 正式系統怎麼處理抽取失敗，仍待 M4 前決定（D-55 待確認第 6 項）。

### 已知限制（本輪仍成立或新增）
1. **#12／H3 答不知道**：dyspnea_grade 被抽成 exertional_heavy，而病人根本不喘、對 H3 題答不知道 → 18 題 T9（備援 T1）。gpt 3 例、Gemma 3 例。方向：同級或較急。上限救不了。
2. **關鍵詞路徑的 reproducible_mechanical**（D-56 已知限制 (a)）：
   - 不在裁定 #3 的確認流程內，仍直接寫 true。
   - 只有 positive 樣式：「按下去不會痛」「胸口按下去不會痛，深呼吸也不會痛」「搬東西的時候會悶」都設為 true，可能走 T3-MECHANICAL 而低判。
   - 用在 Scripted、`sim.run_llm_eval` 的開場白與 `sim/cases.py` 的情境事實。
   - Clinical Owner 決定 M4 前另外修。
3. **只有 LLM 路徑會記旗標**（D-56 (b)）：Scripted 的 Q-REPRO-01 仍只在資訊不足、問到後段的通話問到。
4. **Gemma 對 Q-REPRO-01 的「不確定」抽成 false**（本輪新增，最終版 S-MID-16）：病人說「不太確定…只知道咳嗽的時候會痛」，Gemma 寫 false。
   - 這次方向較急：false 排除 T3-MECHANICAL → T2＝truth。
   - 但屬自編否認；最終版 Gemma 被問那題 invented 6 → 7。
5. **Gemma S-INSUF-07 的頻率誤抽**（與 dev27 無關；D-56 (c)）：→ T0，較急，over-triage 風險。
   - 回答句提示 dev26 與 dev27 逐字相同。
   - 閉環實際句在各批都抽成 true（同一筆快取）。
   - D-56 探針用的是兩句縮寫句，實際句沒有以 dev26 重跑：**未取得**。
6. **撞上限而低於全資訊的格子 1,259 組**：全資訊 Hard stop 391、T0 868，全部 T9、備援 T1（`<scratch>/d56/out/grid_final18.json` 重算）。裁定 #3 後格子 88,540 組與加旗標前相同（D-56）。
7. **抽取快取併發競態**（D-55 (10)）：實例是 gpt S-MID-07。用快取重算不一定得到同一個問題序列。
8. **Gemma 複誦回答解讀**（§3.3）：
   - 新增 2 句讀錯成 exertional_heavy（較急）；
   - 探針「不是。」讀成 none（較不急）；
   - 原因：**未取得**。
9. **R8 防護與 DV-2 的不一致**（D-56 (b)）照舊。

### 待 Clinical Owner 確認
1. 關鍵詞路徑 reproducible_mechanical 的修正方式與時程（M4 前）。
2. D-56 既有的待確認項照舊：DV-2 要不要求胸部症狀；Q-CHARACTER-01 對沒提胸口的來電措辭（Q-10）。
3. #12／H3 答不知道一型的處理：gpt、Gemma 各 3 例，上限救不了。
4. 抽取呼叫失敗的正式處理（M4 前，D-55 待確認第 6 項）。

## 2. 凍結狀態

- **尚未凍結**。凍結紀錄要寫到 `reports/extractor_v2_freeze.json`，只能寫一次，之後才跑保留集閉環。
- prompts_version **2.0-dev27**：
  - 提示檔 sha256 `8421ab9d82e7d3043d3c2c74a161dfb6fe64f6ad23853abf844731fc4c9bee52`；
  - 送出提示全文 sha256 `608bdf5cbbfb26c359d19a04ddbcb8e7275e03514a21edfdf27db59cdd75af92`，與 11-16、按壓證據防護版相同。
- 11-17 最終版閉環執行時的檔案 hash，與目前工作樹逐檔相同：
  - 相對按壓證據防護版有變的：`data/extractor_prompts_v2.yaml` `8421ab9d82e7d304…`；`sim/llm_extract_v2.py` `57b3950d883714e2…`；`sim/runner.py` `d8bf8fb7ffd31da1…`；`sim/closed_loop.py` `de1ef21fa219f412…`；`data/question_bank_seed.yaml` `673740ed81ebe1b9…`（bank 0.7）；`src/acs_triage/prompter/prompter.py` `8f652424ce2b1566…`；`sim/synth_gen.py` `fb4e198e04d8ea21…`。
  - 沒變的：`data/clinical_rules.yaml` `cec498ca1dc14cd7…`；`src/acs_triage/pathway/router.py` `104fe6f64d5c1f8f…`；`src/acs_triage/rules/tiers.py` `7ca15a46f714a181…`；`src/acs_triage/rules/sufficiency.py` `74dd1cf4ff7b9f21…`。
  - 其餘檔見 `closed_dev_gpt_final_flag.json` 的 `meta.file_sha256`。
- 舊版程式：11-16 批的閉環與重放是 `sim/llm_extract_v2.py` `5845a1fd4d9eeb48…`；按壓證據防護版是 `19f23b57244e23a3…`。
- 保留集：**沒有執行任何保留集閉環、沒有看任何保留集抽取結果**。

## 3. 階段 A：抽取器重放（開發集；調整過）

重放沿用 `sim.e2e_llm` 的指標：對話照 Opus 10-20 逐字稿固定、不補問；Hard-stop miss 含 premature。truth 為 11-16 版，與 11-05 不同的 12 例會影響 exact 的比較。重放在 11-16 批執行；之後的程式改動以離線重算確認不改結果（§3.2）。

| 抽取器 | 文字 | 版本 | Hard-stop miss（含 premature） | premature | 假 Hard stop | under | over | exact | abstention FP | 紅旗題「有」漏抽 | 被問那題正確 | 紅旗題正確 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-6.1-sol | 逐字稿原文 | 11-05 dev26 | 0/27 | 0 | 0 | 0 | 0 | 72.3% | 33 | 0 | 613/646 | 329/346 |
| gpt-6.1-sol | 逐字稿原文 | 11-16 dev27 | **1/27** | 1 | 0 | 0 | 0 | 73.9%（88/119） | 31 | 0 | 615/646 | 330/346 |
| gpt-6.1-sol | 電話語音＋Whisper | 11-05 dev26 | 3/27 | 1 | 0 | 0 | 0 | 69.7% | 36 | 0 | 603/646 | 321/346 |
| gpt-6.1-sol | 電話語音＋Whisper | 11-16 dev27 | **3/27** | 1 | 0 | 0 | 0 | 69.7%（83/119） | 36 | 0 | 602/646 | 320/346 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | 11-05 dev26 | 1/27 | 1 | 0 | 0 | 1 | 73.9% | 29 | 0 | 614/646 | 329/346 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | 11-16 dev27 | **1/27** | 1 | 0 | 0 | 1 | 74.8%（89/119） | 28 | 0 | 616/646 | 332/346 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | 11-05 dev26 | 1/27 | 1 | 0 | 0 | 1 | 72.3% | 32 | 0 | 609/646 | 324/346 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | 11-16 dev27 | **1/27** | 1 | 0 | 0 | 0 | 70.6%（84/119） | 35 | 0 | 607/646 | 324/346 |

### 3.1 Hard-stop miss 明細（11-16 dev27）
- gpt 原文：miss ['S-MID-10#0']，premature ['S-MID-10#0']。11-05 的 0 是 Q-SYNCOPE-02 逾時造成的（11-05 報告結論 6）；本輪 0 失敗，premature 回到 dev25 與 Gemma 的狀態。
- gpt 電話：miss ['S-INSUF-04#0', 'S-MID-06#0', 'S-MID-10#0']，premature ['S-MID-10#0']；與 11-05 相同。
- Gemma 原文、電話：miss ['S-MID-10#0']，premature ['S-MID-10#0']；與 11-05 相同。Gemma 原文 over 1：S-MID-07，T1 → T0。
- 假 Hard stop：四格都 0。

### 3.2 離線重算（不呼叫模型）
- 方法：以重放快取的模型原始輸出、用當時的 parse 重算 `run_cell`。
- **裁定 #3（最終）**：`guard_rescore/flag_replay_*.json`。四個 cell 的逐例最終結果與原始重放相同；cache miss 0、extract_failed 0。理由見 §1「重放不受影響」。
- 已撤回的按壓證據防護版：`guard_rescore/replay_*_v2.json`、`tightened_replay_*.json`，也逐例相同。

### 3.3 複誦回答的解讀（開發集 10-23 逐字稿的複誦回答 164 句＋探針 15 句）

| 抽取器 | 11-05 dev26 | 11-16 dev27 |
|---|---|---|
| gpt-6.1-sol | 163/164（correct 162、speechless 1、wrong 1）；探針 15/15 | 163/164（correct 162、speechless 1、wrong 1）；探針 15/15 |
| gemma-4-26b-a4b-it-mlx | 162/164（correct 161、speechless 1、invented 1、wrong 1）；探針 15/15 | **160/164**（correct 159、speechless 1、invented 1、wrong 3）；**探針 14/15** |

Gemma 的變化（逐句對照 11-05）：
- 新增 wrong 2 句：S-STABLE-02#0「對，我沒有在喘，就只是很用力的時候胸口會有點悶。」與 S-STABLE-04「對，我沒有在喘，就只是走快的時候胸口會悶而已。」讀成 exertional_heavy，確認值 none。
- 探針「不是。」（Q-DYSPNEA-GRADE-01，複誦值 none）讀成 none；應為未知，11-05 是未知。
- 送出的複誦提示與 dev26 相同，原因：**未取得**。

### 3.4 迭代紀錄（2.0-dev27；2.0-dev1～dev26 見 `reports/extractor_v2_2026-11-05.md` §3.4）

| 版本 | 改了什麼 | 開發集結果 |
|---|---|---|
| 2.0-dev27 | **提示（D-56 R8，Clinical Owner 2026-11-15）**：開場白規則 4 加一句「用『天』說的時間要換算成週：『前天開始』填 0.29、『這兩天』填 0.29（不是 2）；『這兩個禮拜』填 2。」例句只用開發集說法。回答句與複誦提示與 dev26 逐字相同。<br>**程式**（`sim/llm_extract_v2.py`，送出的提示全文不受影響）：<br>(1) R8 回答句防護：onset_weeks_ago ≥ 1 週而 evidence 只有日數用語 → 天數÷7；說不出天數 → 未知。<br>(2) R9：逾時 300 → 600 秒；逾時、5xx、連線錯誤重試最多 2 次。<br>(3) 2026-11-17 先加 `palpation_pain()`，後撤回。<br>(4) 2026-11-17 裁定 #3：順口的 reproducible_mechanical＝true 改記旗標 `reproducible_mechanical_mentioned`；Prompter 在紅旗題後問一次 Q-REPRO-01（題庫 bank 0.6 → 0.7，`sim/runner.py`、`src/acs_triage/prompter/prompter.py`）。 | 本報告：<br>開發集付費閉環三批：11-16 批（Gemma under 1：S-MID-16）、按壓證據防護版、**裁定 #3 最終版**（under 0、exact gpt 114／Gemma 113）。<br>階段 A 重放：gpt US$2.60，1,235 個不同呼叫、失敗 0；Gemma 本機，失敗 0；裁定 #3 離線重算逐例不變。<br>Gemma 開場白「前天開始」「這兩天」2.0 → 0.29 週 |

### 3.5 延遲與費用（階段 A）
- gpt-6.1-sol（11-17 08:09–08:20，並行 8）：
  - 呼叫 1,250、失敗 0。
  - 延遲中位數／p95：全部 2.50／8.81 s、開場白 10.60／14.99 s、回答 2.43／5.91 s。
  - 程式保護觸發 {'mention_redflag_denial_not_used': 107, 'rest_denial_not_used': 14}；費用 US$2.5995。
- gemma-4-26b-a4b-it-mlx（11-16 23:09–23:54，並行 1）：
  - 呼叫 1,250、失敗 0。
  - 延遲中位數／p95：全部 1.66／8.39 s、開場白 8.91／9.90 s、回答 1.60／2.76 s。
  - 程式保護觸發 {'rest_denial_not_used': 27, 'mention_redflag_denial_not_used': 43, 'asked_value_from_mentions': 57, 'affirm_with_negated_evidence': 25, 'denial_without_negated_evidence': 4, 'choice_listed_unclassified': 3, 'ongoing_mention_without_present_marker': 1, 'asked_stance_vs_leading_word': 1}。
- 以上是 11-16 批的統計。裁定 #3 的離線重算多出 repro_mention_not_used：gpt 2、Gemma 6。

## 4. 階段 B：閉環模擬（Opus 病人 prompt 0.3、effort medium）

### 4.1 開發集 119 例（對 11-16 truth；提示依開發集調整過）

| arm | HS 敏感度 | HS miss（含 premature） | premature | 假 Hard stop | under | over | exact | T9 | 平均題數 | 複誦（每通） | 執行錯誤 | 抽取失敗 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **結構化值（對照，最終版）** | 27/27（100.0%） | 0 | 0 | 0 | 0 | 0 | 100.0% | 12 | 6.50 | 170（1.43） | 0 | — |
| **gpt-6.1-sol（最終版，裁定 #3）** | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 95.8% | 15 | 7.21 | 200（1.68） | 0 | 0 |
| **gemma-4-26b-a4b-it-mlx（最終版，裁定 #3）** | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 95.0% | 14 | 7.16 | 208（1.75） | 0 | 0 |
| gpt-6.1-sol（按壓證據防護版，已取代） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 95.8% | 15 | 7.19 | 200（1.68） | 0 | 0 |
| gemma-4-26b-a4b-it-mlx（按壓證據防護版，已取代） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 95.0% | 14 | 7.13 | 208（1.75） | 0 | 0 |
| gpt-6.1-sol（11-16 批，已取代） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 95.8% | 15 | 7.20 | 200（1.68） | 0 | 0 |
| gemma-4-26b-a4b-it-mlx（11-16 批，已取代） | 27/27（100.0%） | 0 | 0 | 0 | **1** | 2 | 94.1% | 14 | 7.13 | 208（1.75） | 0 | 0 |

- under／over 不含 T9（T9 另計）。
- 最終版明細：
  - gpt：HS miss（無）；premature（無）；假 Hard stop（無）；under（無）；over [['S-MID-08#2', 1, 0], ['S-MID-13', 2, 0]]；abstention FP [['S-ACUTE-05#1', 2], ['S-MID-01', 1], ['S-MID-08', 2]]。
  - Gemma：HS miss（無）；premature（無）；假 Hard stop（無）；under（無）；over 同 gpt；abstention FP [['S-MID-01', 1], ['S-MID-02', 2], ['S-MID-08', 2]]；abstention FN [['S-INSUF-07', 0]]。
- 11-16 批 Gemma 的 under：[['S-MID-16', 2, 3]]。
- 結束原因（最終版）：
  - gpt：gate_passed 64、gate_passed_t0_asked 13、hard_stop 25、hard_stop_opening 2、max_questions 15。
  - Gemma：72、6、25、2、14。
  - 結構化值：gate_passed 77、t0_asked 3、hard_stop 25、opening 2、max_questions 11、no_more_questions 1。
- 結構化值最終版與 11-16 版逐例相同。

### 4.1b Hard stop 題次（truth 為 Hard stop 的 27 例；最終版）
- 題次＝觸發 Hard stop 時已問的題數（0＝開場白；不含複誦）。
- 27 例都在三個 arm 觸發 Hard stop。
- 題次與結構化值不同的只有下列 6 格（gpt 4、Gemma 2），與按壓證據防護版相同：
  - gpt：S-MID-05#0 3 → 4（+1）、S-MID-10#0 5 → 3（−2）、S-MID-13#0 3 → 2（−1）、S-MID-19#3 4 → 3（−1）。
  - Gemma：S-MID-05#0 3 → 4（+1）、S-MID-16#1 3 → 4（+1）。

### 4.1c 順口提到的值與已知值不同（沒採用；最終版）
- gpt：沒採用 3 次（conflict 2、d50_not_most_severe 1），與之前相同：
  - S-ACUTE-01#0 第 1 題 Q-ONGOING-01：symptom_character 已知 pressure、順口 vague；
  - S-INSUF-08 第 17 題 Q-COUGH-01：已知 tightness、順口 pain；
  - S-MID-06#1 第 3 題 Q-ONGOING-01：未知、順口 vague（d50_not_most_severe）。
  - 再問 0 次、順口值觸發的複誦 0 次。
- Gemma：沒採用 9 次（conflict 5、d50_not_most_severe 4）：
  - S-STABLE-03#0：symptom_character 順口 vague；
  - S-STABLE-04、S-INSUF-03#1、S-MID-08#2、S-MID-18：dyspnea_complaint 與已知值相反；
  - S-MID-16、#0、#1（×2）：未知、順口 pain，d50_not_most_severe。
  - 再問 0 次；按壓證據防護版的 S-MID-14 再問與 conflict 因序列改變而沒有發生。
  - 順口值觸發的複誦 0 次。

### 4.2 保留集 150 例
**未執行**：提示未凍結；`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑。保留集只跑免費層，見 §1。

### 4.3 閉環中的抽取（被問那題確認前的值 vs 病人模擬的結構化值；最終版）

| arm | 被問那題 | 複誦回答 | 紅旗題「有」沒抽成「有」 | 病人呼叫：新／重用 | 抽取：新呼叫／重用 | 抽取器費用（本次） |
|---|---|---|---|---|---|---|
| gpt-6.1-sol | {'correct': 812, 'wrong': 21, 'unknown_equiv': 16, 'speechless': 7, 'missed': 1, 'invented': 1} | {'correct': 192, 'speechless': 4, 'wrong': 4} | 0 | 0／1,058（seed 510、live_reused 548） | 7／864 | US$0.0260（快取累計 1.7635 − 防護版 1.7375） |
| gemma-4-26b-a4b-it-mlx | {'correct': 805, 'wrong': 20, 'speechless': 12, 'unknown_equiv': 7, 'invented': 7, 'missed': 1} | {'correct': 190, 'missed': 12, 'wrong': 1, 'speechless': 4, 'invented': 1} | 0 | 25／1,035（seed 487、live_reused 548） | 19／853 | US$0 |

- 最終版執行順序：Gemma（21:59–22:00）先跑，新的病人回答由它取得（Opus US$0.1663）；gpt（22:00）重用。
- 之前的批次：
  - 按壓證據防護版：gpt 病人 2 次新呼叫、抽取 2 次新呼叫；Gemma 0 次。
  - 11-16 批：gpt 病人 545 次新呼叫、抽取 868 次；Gemma 病人 260 次、抽取 192 次。

## 5. 模糊說法清單

本輪沒有另出裁定表。本輪付費結果中 v2 抽錯或要裁定的說法，都已列在 §1 的表、已知限制與待確認：
- #12／H3；
- 「說不上來」→ heavy；
- 休息後緩解 → rest true；
- 頻率誤抽；
- Q-REPRO-01「不確定」→ false；
- 複誦「不是。」。

## 6. 費用與耗時

依 repo PRICES 估算，以帳單為準；Gemma 本機不計費。每一項的來源檔都在 inputs 目錄或 `reports/`。

**Anthropic（Opus 5.5 病人）**

| 項目 | US$ | 來源 |
|---|---|---|
| 開發集 Opus 病人 eval（11-16） | 5.6637 | `reports/eval_2026-11-16_llm_opus-5-5_medium.json` usage.est_cost_usd（944 次呼叫） |
| 閉環 gpt arm（11-16 批） | 3.6760 | `closed_dev_gpt.json` patient_usage.opus_cost_usd（新呼叫 545） |
| 閉環 Gemma arm（11-16 批） | 1.8371 | `closed_dev_gemma_1116_superseded.json`（新呼叫 260） |
| 閉環 gpt arm（按壓證據防護版） | 0.0164 | `closed_dev_gpt_final.json`（新呼叫 2） |
| 閉環 Gemma arm（按壓證據防護版） | 0.0000 | `closed_dev_gemma_final.json`（新呼叫 0） |
| 開發集 Opus 病人 eval（11-17，D-34 正式紀錄） | 5.6590 | `reports/eval_2026-11-17_llm_opus-5-5_medium.json` usage.est_cost_usd（944 次呼叫） |
| 閉環 結構化值 arm（最終版） | 0.0000 | `closed_dev_structured_final_flag.json`（新呼叫 0） |
| 閉環 Gemma arm（最終版） | 0.1663 | `closed_dev_gemma_final_flag.json`（新呼叫 25） |
| 閉環 gpt arm（最終版） | 0.0000 | `closed_dev_gpt_final_flag.json`（新呼叫 0） |
| **小計** | **17.0185** | 5.6637＋3.6760＋1.8371＋0.0164＋0＋5.6590＋0＋0.1663＋0＝17.0185 |

**OpenAI（gpt-6.1-sol 抽取）**

| 項目 | US$ | 來源 |
|---|---|---|
| D-56 免費驗證階段的 gpt 探針（11-15） | 0.4720 | `logs/d56_probe_gpt_answers.log` 0.0561＋`d56_probe_gpt_dev26_rep1.log` 0.1223＋`d56_probe_gpt_dev27_openings.log` 0.2936 |
| 閉環 gpt arm（11-16 批） | 2.1969 | `closed_dev_gpt.json` extractor_usage.cost_this_run_usd（新呼叫 868） |
| 階段 A 重放 gpt | 2.5995 | `logs/v2_replay_gpt.log`（JSON cost_total 2.5994819） |
| 閉環 gpt arm（按壓證據防護版） | 0.0103 | `closed_dev_gpt_final.json` cost_this_run_usd（新呼叫 2） |
| 閉環 gpt arm（最終版） | 0.0260 | `closed_dev_gpt_final_flag.json` cost_this_run_usd（新呼叫 7）＝快取累計 1.7635 − 1.7375 |
| **小計** | **5.3047** | 0.4720＋2.1969＋2.5995＋0.0103＋0.0260＝5.3047 |

- **D-56 合計**：17.0185＋5.3047＝**US$22.3232**。
- 不計費、沒有呼叫付費 API：robustness、保留集各層、格子、Gemma 閉環抽取與重放、所有離線重算、本報告的重算。
- 耗時：
  - 11-16 批：gpt 閉環 11-16 23:14–23:26（704.8 s）；Gemma 閉環 11-17 08:09–08:14（285.8 s）。
  - 重放：gpt 11-17 08:09–08:20；Gemma 11-16 23:09–23:54。
  - 最終版：結構化值 11-17 21:58；Gemma 21:59–22:00；gpt 22:00（20 s）。

## 7. 改動的檔案

- `reports/extractor_v2_2026-11-16_inputs/`：本報告新增檔，沒有覆蓋既有檔。
  - 最終版：`closed_dev_{structured,gpt,gemma}_final_flag.json`；
  - 已取代：按壓證據防護版 `closed_dev_{gpt,gemma}_final.json`、11-16 批 `closed_dev_gemma_1116_superseded.json`；
  - `v2_replay_gpt.json`；
  - `logs/`：執行紀錄、探針費用紀錄、`eval_2026-11-17_run_llm_eval.log`；
  - `guard_rescore/`：`flag_replay_*` 為本報告產生；`tightened_*` 由主對話加入。
  - 既有的 `closed_dev_gpt.json`、`closed_dev_structured.json`、`v2_replay_gemma.json` 不動。
- `reports/extractor_v2_2026-11-16.{md,json}`：本報告與彙總。更新前備份 `.md.bak-20261117-3`、`.json.bak-20261117`；之前的 `.md.bak-20261117`、`-2` 是主對話留的。
- `docs/DECISIONS.md`：D-56 結果段改為最終狀態（備份 `docs/DECISIONS.md.bak-20261117-6`）。
- `CLAUDE.md`：pytest 基線 721（已由主對話改；本輪核對）。
- D-56 既有、本報告未改：
  - `data/extractor_prompts_v2.yaml`、`data/extractor_prompts.yaml`、`data/question_bank_seed.yaml`（bank 0.7）；
  - `sim/llm_extract_v2.py`、`sim/runner.py`、`src/acs_triage/prompter/prompter.py`、`sim/synth_gen.py`；
  - `sim/closed_loop.py`（DEV_STRUCTURED 改指 11-17 逐字稿）；
  - `data/clinical_rules.yaml`、`src/acs_triage/rules/`、`src/acs_triage/pathway/router.py`；
  - 情境檔 truth、tests。

## 8. 重現

```
# 11-16 批（防護前）
PYTHONPATH=<本機 opencc>:src:. python -m sim.run_llm_eval                      # Opus 病人 eval（US$5.66）
python -m sim.robustness
python -m sim.synth_eval --llm-json reports/eval_2026-11-05_llm_scenarios_synth_v1_opus-5-5_medium.json --out <scratch>/synth1116
PYTHONPATH=<本機 opencc>:src:. python -m sim.closed_loop run --set dev --arm structured|gpt|gemma --cache-dir <scratch>/closed1116/cache --out <scratch>/closed1116/out…
PYTHONPATH=<本機 opencc>:src:. python -m sim.llm_extract_v2 replay --extractors gpt --tag gpt --workers 8 …（<scratch>/replay1116gpt）；--extractors gemma --tag gemma --local-workers 1（<scratch>/replay1116）
# 11-17 按壓證據防護版（已取代）：<scratch>/closed1117
# 11-17 最終版（裁定 #3）
PYTHONPATH=<本機 opencc>:src:. python -m sim.run_llm_eval                      # → reports/eval_2026-11-17_llm_opus-5-5_medium.*（US$5.659）
PYTHONPATH=<本機 opencc>:src:. python -m sim.closed_loop run --set dev --arm structured|gemma|gpt --cache-dir <scratch>/closed1117b/cache --out <scratch>/closed1117b/out_<arm>
# 離線重算（不呼叫模型；不帶金鑰環境變數）
python <scratch>/d56repro/rescore_replay.py gpt|gemma <重放快取> <scratch>/report1117/flag_replay_<arm>.json   # 裁定 #3 版重放
PYTHONPATH=src:. python <scratch>/report1117/recompute.py <scratch>；… cf2.py <scratch>
PYTHONPATH=src:. python <scratch>/report1117/build_json.py <scratch> reports/extractor_v2_2026-11-16.json
```

沒有用 `sim.extractor_v2_report` 產生本報告，原因有兩個：
- 它把同一 arm 的多個 closed_*.json 合成一個鍵，三批會互相覆蓋；
- 它的 §5 會依 ambiguity.json 產出裁定表，本輪沒有新的裁定表。

scratch 內的腳本與快取不在 repo。
