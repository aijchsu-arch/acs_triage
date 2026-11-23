# 抽取器 v2 與閉環模擬（D-52 第 3 項）— 2026-11-05

> **限制（先讀）**
>
> 1. **合成病人**：病人回答由 Opus 5.5 依情境事實（hidden sheet）生成，句子比真實病人完整、少答非所問；正確答案＝情境事實（開發集為單一裁定者 truth）。這是一致性檢查，不是準確度，不能外推臨床表現。
> 2. **合成語音或沒有語音**：階段 A 的 phone 條件是 macOS `say` 合成標準國語＋模擬電話線路＋本機 Whisper（D-49），沒有台語、高齡口音與環境噪音，是樂觀上限；階段 B 閉環完全沒有語音（病人文字直接進抽取器），等於 STT 完美。
> 3. **LLM 參考標註**：保留集的「對照答案」是 Opus 5.5 與 gpt-6.1-sol 的獨立標註（暫定；Clinical Owner 尚在裁定 48 例），不是 truth；主分析用兩位標註者一致的子集。
> 4. **雲端模型不可用於真實資料**：gpt-6.1-sol 只是「抽取能力上限」參考；真實病人資料不得送外部 API（D-10）。院內可部署的候選是本機模型（Gemma）。全部資料為合成資料。
> 5. **病人回答重用（配對設計）**：閉環的病人以「對話前綴快取」包一層：同一 case、同一串客服問句（含複誦句）就重用已取得的 Opus 回答，種子是結構化值閉環的逐字稿（開發集 10-23、保留集 10-26），gpt 與 Gemma 兩個 arm 共用。問句序列相同時病人看到的對話完全相同，重用的是同一個樣本（三個 arm 之間是配對比較，不是獨立重抽）；序列一分岔，之後都是新的 API 呼叫。
> 6. **開發集調整過；保留集尚未執行**：抽取提示只依開發集逐字稿調整（迭代紀錄見 §3.4），本報告的數字全部來自開發集，因此偏樂觀；提示尚未凍結，保留集（data/synth/）沒有執行、也沒有看任何保留集抽取結果。

## 1. 結論（人工撰寫，依本報告數字）

**本報告的範圍與版本（最終版）**：
- 抽取提示 2.0-dev26：刪掉 dev25 的開場白規則 17、18。
- `sim/llm_extract_v2.py`：開場白與順口提到的 rest_symptom＝false 一律不採用，只有直接回答 Q-REST-01 時才寫入。
- rules 0.10.0、題庫 0.6、題數上限 15、runner F2（D-55 的工作樹，未 commit；HEAD 9e408cc）。R1、R4 已撤回。

其他沿用與執行條件：
- 病人前綴快取：種子是 11-05 逐字稿（`reports/eval_2026-11-05_llm_opus-5-5_medium_transcripts.json`；保留集 `reports/eval_2026-11-05_llm_scenarios_synth_v1_opus-5-5_medium_transcripts.json`）。另以 `PatientCache.load` 依序載入 dev25 那輪與實作者 `--opus-budget 0` 試跑的病人快取。兩者同一個 meta、內容完全相同，共 1,643 筆。
- 抽取快取：全新，沒有沿用 dev25 的結果。
- 沿用 dev25 那輪、不重跑：結構化值 arm、開發集 Opus 病人 eval、保留集逐字稿與保留集三層。這些只依病人與規則，dev26 沒有改到。
- 同日 reports/ 下 6 個不帶 `_r2` 的 2026-11-03 eval 檔是作廢檔，本報告沒有使用。
- 提示未凍結，保留集閉環未執行。

**固定說明文字的更正（報告程式的文字是 10-27 版，本次不改程式）**：
- 限制第 5 點的種子：本次是 11-05 逐字稿，不是 10-23／10-26。
- §4.1c 的規則說明沒有寫 rest_symptom＝false 的兩層攔截：
  - 抽取器：開場白與順口提到的 false 不輸出，記在抽取診斷 guard＝rest_denial_not_used。
  - runner F2：順口的 false 不寫入，記為 kind＝rest_denial_not_used。dev26 的 false 都在抽取器就被攔下，runner F2 本輪 0 次。
- §5 標題「v2 一律留未知、讓系統追問」與前言：本次 §5 改列 dev26 付費結果中 **v2 已經抽錯或需要再問** 的說法（6 項），不是 10-27 的 16 項，也不是 11-03 的 10 項（已在 2026-11-04 裁定，D-55）。
  - 裁定表 `extractor_v2_ambiguous_2026-11-05.*` 的第 7 列是已知限制、第 8 列是「H3 兩題答不知道」，不是 10-27 的「Prompter 缺口／順口值取捨」。
  - 「第 12 項不太會喘 → none」那句不適用：裁定 #12 是 exertional_heavy，已以例句寫進提示。
  - 裁定表 md 的前言也是同一段寫死文字，已在該檔開頭加更正段。
- §3.4 迭代紀錄：2.0-dev24 列指 11-03 報告；2.0-dev25 列是本報告的 dev25 中間版（見下方「dev25 中間版紀錄」）。
- §4.1 表的「執行錯誤」只算 case 例外，抽取呼叫失敗不算在內（見「其他觀察」）。
- **驗收後的文件更正（2026-11-05，未重跑任何付費步驟）**：本節、§5 表第 6 列與 §7 直接改在 .md，並同步改 `reports/extractor_v2_2026-11-05_inputs/` 的 conclusions.md、ambiguity.json、extra.json。之後已以 inputs 重跑 `python -m sim.extractor_v2_report` 重產本報告、`reports/extractor_v2_2026-11-05.json` 與裁定表 `extractor_v2_ambiguous_2026-11-05.{md,xlsx}`（裁定表 md 開頭照 11-03 加更正段），三檔已與本報告一致。
- §4.3 的 gpt 列是重試那次的用量：病人新呼叫 0、抽取費用 US$0.10。第一次是病人新呼叫 106、抽取 US$1.95（`dev26_gpt_attempt1/`）。§3.5 的 gpt 延遲與呼叫數，是兩次合併的快取紀錄。
- §3 表有兩格是二次進位：0.6975 顯示為 69.8%（gpt 電話 v2；實際 83/119＝69.7%）；0.7395 顯示為 74.0%（Gemma 原文 v2；實際 88/119＝73.9%）。原因是重放 JSON 先存到小數 4 位，報告再進位一次。

### 結論
1. **Hard stop 沒有漏、沒有 under-triage**：
   - 開發集閉環三個 arm 都是 HS 27/27，沒有 premature、沒有假 Hard stop，under 0。
   - dev25 時 Gemma 的 1 例 under-triage（S-MID-08#0），在 dev26 回到 T0＝truth。
   - Opus 病人評估（結構化值）開發集 HS 27/27、under 0、over 0、exact 100%，與 Scripted 相同（`reports/eval_2026-11-05_llm_opus-5-5_medium.md`）。
2. **exact**：
   - gpt：11-03 113 → dev25 116 → dev26 115；over 2 → 1 → 2。
   - Gemma：107 → 114 → 115；over 7 → 3 → 2。
   - 偏差全部是較急或同級：T0；T9 的備援都是 T1。
3. **與結構化值不同**：gpt 4 例、Gemma 4 例（見下表）。原因共四類：
   - 裁定 #12 或 dyspnea 誤抽，造成 H3 兩題答不知道；
   - 時序或活動關係沒抽到；
   - 裁定 #14；
   - dev26 新攔截的副作用 1 例（Gemma S-MID-02）。
4. **15 題上限**：11-03 停在 12 題上限的 case 全部等於 truth。平均題數：結構化值 5.91 → 6.23、gpt 6.16 → 6.65、Gemma 6.24 → 6.92。
5. **dev26 的新攔截有一個副作用**：開場白裡正確、明確的「休息時從來沒有」也一併不採用。
   - Gemma S-MID-02：之後 Q-ONGOING-01「現在坐著休息，胸口都不會悶」被誤抽成 rest_symptom＝true。因為已沒有已知的 false，這個 true 直接寫入，沒有矛盾可觸發 #16 再問 → T0-REST-NEW（truth T2，偏急）。
   - 問到 Q-REST-01 的通話：gpt 40 → 42、Gemma 39 → 43（dev25 → dev26；結構化值 41）。
6. **階段 A 重放**（dev25 → dev26）：
   - gpt 原文：HS miss 1 → 0、exact 73.1% → 72.3%、abstention FP 32 → 33、被問那題正確 614 → 613。
     - **HS miss 0 不是改善**：S-MID-10#0 的 Q-SYNCOPE-02 回答在重試後仍逾時，當作沒抽到，dev25 那個 premature 的觸發條件因此不成立。
     - 其他格與 dev25 只差 S-ACUTE-03#2 多一例 abstain（開場白 symptom_character 沒抽到）。
   - gpt 電話：HS miss 3 → 3（S-INSUF-04#0、S-MID-06#0、S-MID-10#0）、exact 70.6% → 69.7%、FP 35 → 36。
   - Gemma 原文：HS miss 1 → 1（S-MID-10#0 premature）、over 1 → 1、exact 71.4% → 73.9%、FP 32 → 29。
   - Gemma 電話：HS miss 1 → 1、over 1 → 1、exact 69.7% → 72.3%、FP 35 → 32。不再 abstain 的有 S-STABLE-01、S-MID-05、S-MID-19#0（原文格則是 S-MID-12、S-MID-18、S-MID-19#0、S-STABLE-01）。
   - 與 11-03 比：
     - gpt 原文 1／73.1% → 0／72.3%，電話 3／69.7% → 3／69.7%；
     - Gemma 原文 1／74.8% → 1／73.9%，電話 1／71.4% → 1／72.3%。
     - 重放對話固定、不補問 Q-FREQ-01 與 H3，exact 仍受新 gate 欄位限制。
7. **OpenAI 逾時**：dev26 的 gpt 閉環第一次執行，有 16 次抽取呼叫 TimeoutError（300 s），造成 S-MID-01#1、S-MID-04#0 落 T9。
   - 依規定只重試 1 次：同一快取重跑整個 arm，失敗的呼叫會重新呼叫。重試 802 次呼叫中，35 次是新的。
   - 重試仍有 1 次逾時：S-MID-10#0 的 Q-ONGOING-01 複誦回答 → 未知。Hard stop 題次與結構化值相同。
   - 本報告的 gpt arm 是重試結果；第一次的結果放在 `dev26_gpt_attempt1/`。
   - **階段 A 重放的 gpt 第一次有 7 例比 truth 不急**：1,250 次呼叫中 42 次逾時。結果在 `dev26_gpt_attempt1/v2_replay_gpt.attempt1.json`。
     - 原文 Hard-stop miss 3 例，都不是 premature，都是紅旗「有」的回答逾時、當作沒抽到 → T9：
       - S-MID-01#2（RF-06，Q-DIAPH-01「有，那時候有冒冷汗。」，備援 T1）；
       - S-MID-05#0（RF-01，Q-SYNCOPE-01「有耶，那時候有覺得快要昏倒的感覺。」，備援 T1）；
       - S-MID-12#1（RF-02，Q-DYSPNEA-GRADE-01「現在連坐著休息的時候也會覺得喘。」，備援 T3）。
     - 另有 4 例 truth T0 落 T9（備援 T1）：原文 S-STABLE-01#1、S-MID-06#2；電話 S-MID-09#0、S-MID-11。
     - 彙總：原文與電話的 exact 都是 68.1%（81/119）、abstention FP 38，原文紅旗「有」漏抽 2。
     - 以同一快取重試一次（只重新呼叫失敗的）後，這 7 例都不再是 Hard-stop miss 或 T9（與 dev25 相同）；仍失敗 1 次（S-MID-10#0 原文的 Q-SYNCOPE-02，見上一點）。
     - 這是已知限制 (9) 在沒有複誦補救的固定對話裡真的發生的例子。閉環有 D-50 複誦，所以同類逾時沒有造成 Hard stop 漏判。
   - Gemma 閉環與重放失敗都是 0。

### 11-03、dev25 與 dev26 並列（開發集）

| 項目 | 11-03（2.0-dev24、rules 0.9.0、上限 12） | dev25 中間版（11-05） | dev26 最終版（11-05） |
|---|---|---|---|
| Opus 病人評估（結構化值）HS／under／over／exact | 27/27／0／0／100% | 27/27／0／0／100% | 同 dev25（沿用） |
| 閉環 結構化值 exact／T9／平均題數／複誦 | 100%／12／5.91／165 | 100%／12／6.23／168 | 同 dev25（沿用） |
| 閉環 gpt HS／under／假 Hard stop／over／exact／T9／平均題數／複誦（再問） | 27/27／0／0／2／95.0%（113）／16／6.16／192（2） | 27/27／0／0／1／97.5%（116）／14／6.61／196（3） | 27/27／0／0／2／96.6%（115）／14／6.65／198（0） |
| 閉環 Gemma 同上（再問、再問後較不急） | 27/27／0／0／7／89.9%（107）／15／6.24／201（10、1） | 27/27／**1**／0／3／95.8%（114）／13／6.79／202（4、0） | 27/27／0／0／2／96.6%（115）／14／6.92／212（1、0） |
| 重放 gpt 原文 HS miss／exact／abstention FP／被問那題正確 | 1／73.1%／32／614 | 1／73.1%／32／614 | 0／72.3%／33／613（HS miss 0 是殘留的逾時造成，見結論 6） |
| 重放 gpt 電話 HS miss／exact／abstention FP | 3／69.7%／36 | 3／70.6%／35 | 3／69.7%／36 |
| 重放 Gemma 原文 HS miss／over／exact／abstention FP | 1／5／74.8%／25 | 1／1／71.4%／32 | 1／1／73.9%／29 |
| 重放 Gemma 電話 HS miss／over／exact／abstention FP／紅旗「有」漏抽 | 1／5／71.4%／29／0 | 1／1／69.7%／35／0 | 1／1／72.3%／32／0 |
| 複誦回答解讀（開發集 164 句；探針 15） | gpt 162＋1 說不出、錯 1；Gemma 160、錯 2、說不出 1、自編 1；探針 15/15 | gpt 同 11-03；Gemma 162、說不出 1、自編 1；探針 15/15 | gpt 同 11-03（162＋1 說不出、錯 1）；Gemma 161、錯 1（「對，我不太會喘…」依 #12 讀成 heavy，10-23 的確認值是 none）、說不出 1、自編 1；探針都 15/15 |

保留集三層與 dev25 那輪相同、本輪不重跑（只依病人逐字稿與規則）。只看 `sim.synth_eval` 的彙總行（D-52，沒有逐例閱讀）；重算：`python -m sim.synth_eval --llm-json reports/eval_2026-11-05_llm_scenarios_synth_v1_opus-5-5_medium.json --out <scratch>`。

| 保留集（參考一致子集 130 例） | 11-03 `_r2` | 11-05 |
|---|---|---|
| (a) HS／under／exact | 51/51／14／108 | 51/51／14／108 |
| (b) HS／under／exact／T9／平均題數 | 49/51／26／97／23／5.88 | 49/51／26／97／22／6.29 |
| (c) HS／under／exact／T9／平均題數 | 49/51／25／98／21／5.88 | 49/51／25／98／20／6.22 |
| 保守參考 under／over：(b)；(c) | 38／11；37／11 | 39／10；38／10 |

(c) 重放 150/150 與逐字稿一致（沒有「重放結果≠逐字稿」），逐字稿 errors 0。

### 與結構化值不同的 case（dev26 閉環；結構化值 arm 全部＝truth；逐例對最終 slot 重算確認）

| case | truth | gpt | Gemma | dev25 gpt／Gemma | 原因（證據在閉環 JSON 的 turns） |
|---|---|---|---|---|---|
| S-ACUTE-05#1 | T3 | T9（15 題） | T3 | T9／T3 | gpt：裁定 #12，Q-DYSPNEA-GRADE-01「我其實不太會喘耶，就是胸口悶而已」→ exertional_heavy。複誦讀成 none，依 D-50 取較嚴重仍 heavy → 加問講話與 H3 兩題。Q-DYSPNEA-ACUTE-01「我其實沒有在喘耶…不知道怎麼回答」gpt 抽成 false；Q-ORTHO-01 答不知道 → 最後只缺 orthopnea_pnd、問到 15 題 → T9（備援 T1）。重算：dyspnea 改 none，連同 D-25 推導 → T3-STABLE-REST-RECURRENT |
| S-MID-01 | T1 | T1 | T9（15 題） | T1／T1 | Gemma：同一機制。「我其實不太會喘耶，走路做家事都還好，休息的時候也不會」→ heavy；複誦讀成不明，保留原值 → H3 兩題答不知道 → T9（備援 T1，急迫度同 truth）。重算：dyspnea 改 none（連同 D-25 推導）→ T1-NEW-YESTERDAY。dev25 那次病人回答不同、沒觸發 |
| S-MID-07 | T1 | T1 | T9（15 題） | T1／T9 | Gemma：「我是不會喘啦，主要是走快一點胸口會悶悶的而已」→ heavy（把走快胸悶當成喘，不是 #12 的說法）；複誦讀成不明 → H3 兩題答不知道 → T9（備援 T1）。重算：dyspnea 改 none → T1。與 dev25 相同 |
| S-MID-08 | T3 | T9（15 題） | T3 | T9／T2 | gpt：開場白不再抽 exertion_only（規則 17 已刪）；Q-ONGOING-01 回答順口補上 exertion_only → T3-POST-PCI-MILDER，它要知道時序。Q-TIMING-01「不太確定最後一次是什麼時候好的」gpt 判成未知（null）；結構化值與 Gemma 是選項 unknown → 之後不再問、問到 15 題 → T9（備援 T1）。重算：時序改 unknown → T3。Gemma 在 dev26 回到 T3 |
| S-MID-08#2 | T1 | T0（5 題） | T1 | T1／T1 | gpt：開場白 exertion_relation 不填；第 3 題回答說到「走路的時候胸口有點悶」，gpt 也沒有順口抽成 exertion_only → DV-4 不適用。Q-TIMING-01 答 unknown → 新發、時序未知 → T0-NEW-TODAY，第 5 題定案，沒問到 Q-ANTIPLT-01。重算：exertion 補 exertion_only → 不再是 T0（還缺題，結構化值問完是 T1-ANTIPLT-SYMPTOMATIC）。即 11-03 §5 第 9 項的原機制；dev26 刪掉規則 17 後，gpt 的這一項退回 |
| S-MID-02 | T2 | T2 | T0（5 題） | T2／T2 | Gemma：dev26 新攔截的副作用。開場白「休息時從來沒有」的 rest_symptom＝false 不採用；Q-ONGOING-01「現在坐著休息，胸口都不會悶」被誤抽成 rest_symptom＝true，直接寫入（沒有已知值，不觸發 #16）。Q-REST-02 的複誦取較嚴重 → rest_symptom_first_time＝true → T0-REST-NEW。重算：rest 改 false → 不再是 T0（還缺題，結構化值問完是 T2-NEW-STABLE-WEEKS）。dev25 時開場白 false 已知，同一個誤抽成了矛盾，由 #16 再問改回 |
| S-MID-13 | T3 | T0 | T0 | T0／T0 | 裁定 #14：Q-EXERTION-01「吃飽坐著」→ rest_symptom（Clinical Owner 接受為偏急）→ T0-REST-NEW。與 11-03、dev25 相同 |

gpt S-ACUTE-05#1、S-MID-08 與 Gemma S-MID-01、S-MID-07 停在 15 題時，T9 的備援都是 T1（`tier9_fallback` 以最終 slot 重算）。

### 依原因量化（開發集 119 例；exact 的分母含 truth T9）
- **gpt exact 115**：與結構化值不同 4 例。
  - 原因：#12＋H3 答不知道 1（S-ACUTE-05#1）、Q-TIMING-01 null 1（S-MID-08）、活動關係沒抽到 1（S-MID-08#2）、裁定 #14 1（S-MID-13）。
  - over 2：S-MID-08#2、S-MID-13。
  - 相對 11-03：
    - 救回 4 例：S-INSUF-01#1、S-INSUF-05#1、S-MID-15#0（上限 15，第 13–14 題定案）、S-MID-18（R6 第 4 項）。
    - 新增 2 例：S-ACUTE-05#1、S-MID-08#2。
    - S-MID-08 由 T0 改成 T9，仍不等於 truth。
  - 相對 dev25：新增 S-MID-08#2。
- **Gemma exact 115**：與結構化值不同 4 例。
  - 原因：dyspnea 誤抽＋H3 答不知道 2（S-MID-01、S-MID-07）、新攔截副作用 1（S-MID-02）、裁定 #14 1（S-MID-13）。
  - over 2：S-MID-02、S-MID-13。
  - 相對 11-03 救回 11 例：
    - 上限 15：S-INSUF-01#1、S-INSUF-02#1、S-INSUF-05#1；
    - R6：S-ACUTE-05#1（第 3 項，第 13 題定案）、S-INSUF-05（第 2 項）、S-MID-12（第 5 項）、S-MID-17（第 6 項）、S-MID-20（第 7 項）、S-MID-19（第 8 項）、S-MID-08、S-MID-08#2（第 9、10 項）。
  - 新增 3 例：S-MID-01、S-MID-02、S-MID-07。
  - 相對 dev25：
    - 救回 S-MID-08、S-MID-08#0（onset_weeks_ago 不再是 4.0；本輪是 1.0，但開場白沒說發作多久，同一提示在本機重跑是 None 5/5，所以 1.0 是巧合，不能當作已修正的證據）、S-MID-14（不再抽成 exertion_only）；
    - 新增 S-MID-01、S-MID-02。
- **閉環裡「事實沒有喘、被抽成 exertional_heavy」**：gpt 11 → 13 → 15 句、Gemma 18 → 20 → 15 句（11-03 → dev25 → dev26）。
  - 分級受影響的只有 gpt S-ACUTE-05#1、Gemma S-MID-01、S-MID-07。其他句子要嘛 truth 本來就是 T9，要嘛病人對 H3 兩題答「沒有」、在 15 題內通過 gate。
  - dev26 的複誦讀成：gpt none 14、heavy 1；Gemma 不明 12、heavy 2、none 1。

### 上限 15 的效果（11-03 停在 12 題上限的 case 在 dev26 怎麼定案）
- **結構化值 12 例**（沿用；truth 全是 T9）：11 例到 15 題仍 T9；1 例（S-INSUF-04）第 14 題沒有可問的題，T9。
- **gpt 15 例**：
  - 12 例 truth T9，到 15 題仍 T9。
  - 3 例定案、都＝truth：S-INSUF-01#1 第 13 題 T3、S-INSUF-05#1 第 14 題 T3、S-MID-15#0 第 13 題 T1。
- **Gemma 14 例**：
  - 11 例 truth T9，到 15 題仍 T9。
  - 3 例定案為 T3＝truth：S-INSUF-01#1、S-INSUF-02#1 第 13 題，S-INSUF-05#1 第 14 題。
- **dev26 用超過 12 題**：結構化值 15 例、gpt 20 例、Gemma 21 例。
- **dev26 停在 15 題上限**：結構化值 11 例、gpt 14 例、Gemma 14 例。truth 不是 T9 的只有 gpt S-ACUTE-05#1、S-MID-08，Gemma S-MID-01、S-MID-07（原因見上表）。
- **H3 兩題答不知道的一型與題數多少無關**：上限 15 只救回病人對這兩題答「沒有」的通話。

### R6 對 11-03 §5 第 2–10 項的實際效果（閉環開場白與順口值；11-03 → dev25 → dev26）

| 項 | 說法 | gpt | Gemma | 分級（dev26） |
|---|---|---|---|---|
| 2 | 休息後緩解（Q-ONGOING-01 順口） | rest 寫 false 4 句 → 0 → 0 | 抽成 true：9 句 → 3 → 4（dev26 事實 true 1 句；S-MID-02、#0、S-MID-13#2 事實 false）；寫 false 的句子由抽取器攔下 | Gemma S-INSUF-05 T0 → T9＝truth；S-MID-02 見上表 |
| 3 | 「今晚躺著看電視時也發作了」 | 未見 | episode_frequency_increased true → null → null | Gemma S-ACUTE-05#1 T0 → T3＝truth |
| 4 | 「打完流感疫苗手臂痠」 | symptom → minor_noncardiac → minor_noncardiac | 原本就對 | gpt S-MID-18 T9 → T4＝truth |
| 5 | 「走路比平常喘一點」 | 原本就對 | heavy → daily（dev25 S-MID-12#0 仍 heavy）→ daily | Gemma S-MID-12 T9 → T2＝truth |
| 6 | 「今天忘記吃早上的藥」 | 原本就對 | true → null → null | Gemma S-MID-17 T3 → T4＝truth |
| 7 | 「空腹抽血」 | 原本就對 | appointment_admin → education_question → education_question | Gemma S-MID-20 T3 → T4＝truth |
| 8 | 「今天還沒發作」 | 原本就對 | today → yesterday_within_24h → yesterday_within_24h | Gemma S-MID-19 T0 → T1＝truth |
| 9 | 「最近走路會有一點悶」 | null → exertion_only → **null（規則 17 已刪，退回）** | unclear → exertion_only → exertion_only（刪掉規則 17 仍抽對） | gpt S-MID-08#2 T0（over）；Gemma S-MID-08、#2 ＝truth |
| 10 | 「比放支架前輕很多」 | 原本就不填 | threshold true → null → null（刪掉規則 18 仍不填） | 同上 |

- dev26 的 Gemma onset_weeks_ago：
  - S-MID-08 開場白 4.0 → 1.0。開場白沒說發作多久，同一提示在本機重跑是 None 5/5，所以 1.0 是巧合，不能當作已修正的證據。
  - S-MID-03（原句「這兩個禮拜」）、S-MID-05（「這兩天」）→ null。
- **時間單位誤讀（潛在 under-triage）**：Gemma dev26 把 S-MID-19「前天開始」與 S-INSUF-07「這兩天」都抽成 2.0 週。
  - 本機探針各 5/5；dev24 時分別是 0.0 與 None；拿掉規則 16 仍是 5/5。
  - 機制與 dev25 的 S-MID-08#0 under 相同：時序未知時，0.29 週會走 T0-NEW-TODAY，2.0 週會走 T2-NEW-STABLE-WEEKS。
  - **方向：可能偏不急（under-triage）；這次分級未受影響**（S-MID-19 系列與結構化值相同；S-INSUF-07 truth T9）。
- exertion_relation：
  - S-MID-14 回到不填；
  - S-MID-12 同一 run 的變體間 exertion_only 與不填都有；
  - S-MID-11 由 dev25 的 exertion_only 改成 both；
  - S-ACUTE-02 由 exertion_only 改成 unclear（事實 exertion_only）。
  - 這幾例分級都未受影響。

### rest_symptom＝false 的攔截（dev26 抽取器）與 F2
- **抽取器攔下的句子**（依抽取快取，每句一筆）：
  - gpt：開場白 5 句、回答句 6 句、複誦 2 句；
  - Gemma：開場白 7 句、回答句 19 句（Q-ONGOING-01 10 句、Q-EXERTION-01 4 句等）、複誦 1 句。
- **runner F2**：0 次。false 都在抽取器先被攔下。
- **開場白被攔下的 false 多數是正確、明確的否認**：「休息時從來沒有」（S-MID-02）、「休息時沒有」（S-MID-03、S-MID-19）、「沒有休息時發作」（S-MID-07）、「坐著不會」「坐著不喘」（S-MID-06、S-MID-12，講的是喘）。只有 Gemma 的「休息後才比較好」（S-ACUTE-01）是 dev25 擔心的那種誤抽。
- **代價**：
  - 這些通話都要直接問 Q-REST-01；
  - 若之後有誤抽的順口 true，會直接寫入（Gemma S-MID-02 T2 → T0，偏急）；
  - 開發集閉環沒有因此變得較不急。
- **攔對的一例**：Gemma S-STABLE-04#0「停下來休息一下就好了」→ 之後 Q-REST-01 答「有」（事實 true），T0＝truth。

### dev25 中間版紀錄（11-05 第一輪付費閉環，已由 dev26 取代；數字在 `dev25/`）
- **dev25 時 Gemma 曾有 under 1**：S-MID-08#0，truth T0 → T2。
  - 開場白「上個月放支架…最近走路會有一點悶」的 onset_weeks_ago 抽成 4.0 週（事實 1 週）。加上正確的 exertion_only → T2-NEW-STABLE-WEEKS。重算：onset 改 1 週 → T0。
  - 同機制讓 S-MID-08 T3 → T2。
  - 成因是 R6 的開場白規則 17（「最近走路會有一點悶」→ exertion_only）與 18（「比放支架前輕很多」≠ threshold_decreased）。獨立驗收以本機 Gemma 探針確認：dev24 0/5 → dev25 5/5；只刪其中一條仍 5/5；兩條都刪 → 0/5，目標效果（exertion_only、threshold 不填）仍保留。
  - dev26 已刪掉這兩條。dev25 報告曾寫「未能確定」，以此更正。
- **dev25 的其他副作用**：
  - S-MID-14（「走路不會更痛」）、S-MID-11、S-MID-12 被抽成 exertion_only。S-MID-14 因此 T3 → T0。
  - 開場白「停下來就好」被 Gemma 抽成 rest_symptom＝false（S-STABLE-04：dev24 0/5 → dev25 5/5）。F2 只擋回答句，開場白照常採用，Q-REST-01 就不問。開發集剛好在事實為 true 的變體用 reset_slots 清掉，所以看不出來；反事實是 S-STABLE-04#0 加上 rest＝false → T3-STABLE（truth T0）。dev26 改由抽取器一律不採用。
  - consult_topic（S-INSUF-01、S-MID-09、S-MID-10）、「這兩天」→ onset 2.0（S-INSUF-07、S-MID-05）等，分級未受影響（S-INSUF-07 在 dev26 仍是 2.0，見 R6 段的時間單位誤讀）。
- **dev26 下 gpt 的第 9 項退回成不填**：S-MID-08#2 T0（見上表）。
- **dev25 數字**：
  - gpt exact 116、over 1、T9 14、6.61 題；
  - Gemma exact 114、under 1、over 3、T9 13、6.79 題；
  - 重放 gpt 原文 1／73.1%、電話 3／70.6%；Gemma 原文 1／71.4%、電話 1／69.7%。
- **dev25 的 gpt 閉環有 2 次 OpenAI HTTP 504**（S-ACUTE-01#0 開場白空白，Hard stop 晚 1 題）。

### 其他觀察
- **再問（#16）**：gpt 0 次；Gemma 1 次（S-MID-14 symptom_character 由順口 vague 改回 pain）；再問後較不急 0。dev25 的 rest_symptom 再問（Q-ORTHO-01「躺平比較喘」）這次沒有發生，因為開場白的 rest false 不再是已知值。
- **抽取呼叫失敗只記在 `extractor_usage.failed`**，不算進 §4.1 的「執行錯誤」：dev26 gpt 1（重試後）、Gemma 0。

### 已知限制（本輪新增，D-55 編為 (9)–(11)；(1)–(8) 與「規則不對稱」照 D-55）
1. **抽取呼叫失敗不重試、當作沒抽到**。OpenAI 504 或逾時、LM Studio finish_reason=length 都一樣：開場白全空；被問那題記為已問但未知，之後不再問。
   - 複誦回答失敗時，連直接回答已經清楚的值也會變成未知（dev26 第一次執行的 gpt S-MID-04#0：Q-ONGOING-01「現在沒有了」→ 複誦失敗 → ongoing_now 未知 → T9）。
   - 驗收模擬（Scripted 病人＋只回結構化值的抽取器，開發集 119 例，每次抽取呼叫各失敗一次，共 976 組）：
     - Hard stop 掉級 0；
     - 較不急 1 組：S-MID-04 開場白失敗，「停了保栓通三天」丟失，T3 → T4；
     - 落到 T9 的 154 組中，37 組的備援比原本不急，多數是 T0 → T9（備援 T1）；
     - 另有 8 組沒算進上一行：S-INSUF-01～08 開場白失敗時 T9 → T9，但備援由 T1 變 T3。
   - 本輪實際發生：
     - dev26 gpt 閉環第一次 16 次逾時：2 例落 T9，備援與 truth 同級或較急。重試後剩 1 次，分級不變。
     - **gpt 重放第一次 42 次逾時：3 例 Hard-stop miss（紅旗「有」的回答逾時）、4 例 T0 → T9（備援 T1），共 7 例比 truth 不急**（見結論 7）。重試後剩 1 次。
   - 方向：偏不急，已實際發生。
2. **抽取快取有併發競態**：同一 run 裡同一句會拿到不同結果。`LLMExtractorV2.record` 先查快取、再呼叫，中間沒有加鎖，併發時會重複呼叫，快取只留最後一筆。
   - 例：dev25 gpt S-ACUTE-01 的開場白只存了 504 那一筆；本輪 Gemma S-INSUF-01 的 consult_topic 在同一 run 的變體間有 symptom 與 appointment_admin。
   - 影響：以快取重算無法精確重現；同一句開場白的變體不一定得到同一結果。
3. **dev26 的 rest_symptom＝false 攔截範圍比目標寬**：開場白正確、明確的否認也不採用，見上節。方向：本輪偏急（S-MID-02）；代價是多問 Q-REST-01。

### 待 Clinical Owner 確認（凡要改提示者須在凍結前改）
1. **H3 兩題答不知道**：dyspnea 被誤抽成有、病人根本不喘時，H3 的兩題（至少一題）答不知道，H3 永遠不過。gpt S-ACUTE-05#1 只缺 Q-ORTHO-01；Gemma 兩例缺兩題。
   - gpt S-ACUTE-05#1、Gemma S-MID-01 起因是裁定 #12「我其實不太會喘」；Gemma S-MID-07 是把走快胸悶當成喘。
   - 結果 T9（備援 T1），方向偏急或同級。
2. **Q-TIMING-01 答不記得**：gpt 判成未知（null），結構化值與 Gemma 是選項 unknown。null 時，要時序的規則永遠缺這一欄（gpt S-MID-08 T9）。要寫成 unknown（提示或程式）嗎？
3. **11-03 §5 第 9 項在 gpt 退回**：開場白「最近走路會有一點悶」不填，S-MID-08#2 T0（偏急）。
   - 另一個做法是 11-03 §5 的「T0-NEW-TODAY 遇到 DV-4 候選時先問活動題」（規則，不改提示）。
4. **rest_symptom＝false 攔截的範圍**：開場白明確否認（「休息時從來沒有」）要不要放行，或只攔「休息後緩解」類說法？
5. **時間單位誤讀（潛在 under-triage）**：Gemma 把「前天開始」「這兩天」抽成 2.0 週（S-MID-19、S-INSUF-07；dev24 不會）。方向可能偏不急，這次分級未受影響。可選做法：
   - 加單位例句（兩天＝0.3 週）；
   - 或開場白順帶的 onset_weeks_ago 不採用、改問 Q-ONSET-WEEKS-01。
6. **抽取呼叫失敗的處理（待 Clinical Owner／設計決定，M4 前要定）**：目前是「當作沒抽到」，已實際造成紅旗「有」被漏掉（gpt 重放第一次 3 例 Hard-stop miss）。正式系統要怎麼處理？例如：
   - 請病人再說一次；
   - 轉人工；
   - 視為未知並升級；
   - 或先重試。
7. **費用**：見下表；依 repo PRICES 估算，以帳單為準。

| 項目 | Anthropic（Opus 5.5 病人） | OpenAI（gpt-6.1-sol 抽取） |
|---|---|---|
| 本輪 dev26：閉環 gpt（第一次＋重試） | US$0.84＋US$0.00 | US$1.95＋US$0.10 |
| 本輪 dev26：閉環 Gemma | US$1.13 | — |
| 本輪 dev26：階段 A 重放 | — | US$2.47＋US$0.07 |
| **本輪小計** | **US$1.97** | **US$4.59** |
| 上一輪 dev25（閉環＋重放） | US$5.22 | US$4.76 |
| 開發集 Opus 病人 eval | US$5.49 | — |
| 保留集逐字稿 eval | US$9.43 | — |
| **合計** | **US$22.11** | **US$9.36** |

另：D-55 前段 R6 提示自我檢查 OpenAI 約 US$0.44（見 D-55，不在本報告重算範圍）；Gemma 本機不計費。

## 2. 凍結狀態

- **尚未凍結**：開發集付費評估（11-05 最終版：2.0-dev26、rules 0.10.0）已跑完；本報告「待 Clinical Owner 確認」各項，凡會改提示、抽取程式或規則者，都要在凍結前處理。凍結：（寫到固定位置 reports/extractor_v2_freeze.json、只能寫一次），之後才跑保留集。
- 目前（最後一版開發集調整）prompts_version **2.0-dev26**；提示檔 sha256 `3b1697ca85c80335d8066ffa3180d80152d1cce8de4039f906ad91c6bc26665c`；送出提示全文 sha256 `213f0b5a65b4e0d2e08c2b1e177360d4e98ddba88dbbc49ec303227b08edb49a`；`data/extractor_prompts_v2.yaml` `3b1697ca85c80335…`；`sim/llm_extract_v2.py` `4d903ce387861dea…`；`sim/runner.py` `4c3b46f6324e4617…`；`sim/closed_loop.py` `a673436d2b52624c…`；`sim/stt_synth_asr.py` `322699400c306c4d…`；`data/clinical_rules.yaml` `1590f41bc0e7ecbf…`；`data/question_bank_seed.yaml` `395c2d36a362a662…`；`data/extraction_patterns.yaml` `814767506e5daa17…`；`data/scripts_zh.yaml` `8e174e1d94e29ed4…`；`data/llm_patient.yaml` `b8cf49b27b11c4b3…`；`sim/cases.py` `1a30cec0ddc079c7…`；`sim/patient.py` `02fbf781c886cabf…`；`sim/llm_patient.py` `553c398bf30bfab8…`；`sim/metrics.py` `f96f2aab64bd8d18…`；`sim/synth_eval.py` `f6727fc42a0ea0d1…`；`sim/synth_gen.py` `79ba62b92244bb9f…`；`sim/llm_extract.py` `01c4ddf74710fc6f…`；`src/acs_triage/decision/openai_adapter.py` `546881c53a0f3f88…`；`src/acs_triage/loaders.py` `140b58b580ee4c4f…`；`src/acs_triage/schemas.py` `35c215b94c526e53…`；`src/acs_triage/extract/__init__.py` `9dc74f58d081e08e…`；`src/acs_triage/extract/rule_extractor.py` `a9ce66b960a1acae…`；`src/acs_triage/pathway/__init__.py` `c96c56bb0ebb9f9a…`；`src/acs_triage/pathway/router.py` `00b95c0378267ec3…`；`src/acs_triage/prompter/__init__.py` `d1ade26107520064…`；`src/acs_triage/prompter/confirm.py` `9e03622387f9dd47…`；`src/acs_triage/prompter/prompter.py` `68e40c94aadf37fe…`；`src/acs_triage/rules/__init__.py` `0f8ec6e704c6b345…`；`src/acs_triage/rules/engine.py` `5f9f329c2ca5abff…`；`src/acs_triage/rules/redflags.py` `42b0b878db4914a3…`；`src/acs_triage/rules/state.py` `daa27eaa3f2f6549…`；`src/acs_triage/rules/sufficiency.py` `26e769a0b27afbdf…`；`src/acs_triage/rules/tiers.py` `a9ec1e1a2fb5f264…`；`data/synth/reference_synth_v1.json` `0228d3d4980f65e5…`；`data/synth/scenarios_synth_v1.yaml` `f949037d048d562e…`；`data/synth/synth_prompts.yaml` `841eeeacced8a4a6…`
- 保留集：**沒有執行任何保留集閉環、沒有看任何保留集抽取結果**（`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑）。

## 3. 階段 A：抽取器改進（開發集重放；調整過）

重放沿用 `sim.e2e_llm` 的指標（`run_cell`）：對話照 Opus 10-20 逐字稿固定、不補問；Hard-stop miss 含 premature。v1＝`reports/e2e_llm_extractors_2026-10-26.md`（回答句只抽被問那題；開場白 0.1）。v2 寫入方式：被問那題抽到值才寫入（未知不寫、保留原值）；順口提到的 slot 與閉環 runner 共用 `_write_mentions`：補未知的 slot，已知值只在紅旗是非題「有」或 confirm_back_severity 較嚴重時覆蓋，其他不同保留已知值（conflict）。閉環 runner 與此不同的一點：被問那題抽成未知時照既有 runner 寫入未知並標記已問（之後順口提到仍可補上）。

| 抽取器 | 文字 | 版本 | Hard-stop miss（含 premature） | premature | 假 Hard stop | under | over | exact | abstention FP | 紅旗題「有」漏抽 | 被問那題正確 | 紅旗題正確 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-6.1-sol | 逐字稿原文 | v1 | **4/27** | 1 | 1 | 0 | 0 | 86.6% | 16 | 0 | 632/646 | 346/346 |
| gpt-6.1-sol | 逐字稿原文 | v2 | **0/27** | 0 | 0 | 0 | 0 | 72.3% | 33 | 0 | 613/646 | 329/346 |
| gpt-6.1-sol | 電話語音＋Whisper | v1 | **5/27** | 1 | 1 | 0 | 2 | 83.2% | 18 | 0 | 631/646 | 344/346 |
| gpt-6.1-sol | 電話語音＋Whisper | v2 | **3/27** | 1 | 0 | 0 | 0 | 69.8% | 36 | 0 | 603/646 | 321/346 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | v1 | **4/27** | 1 | 21 | 0 | 14 | 66.4% | 21 | 0 | 531/646 | 299/346 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | v2 | **1/27** | 1 | 0 | 0 | 1 | 74.0% | 29 | 0 | 614/646 | 329/346 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | v1 | **6/27** | 2 | 30 | 0 | 20 | 63.0% | 17 | 0 | 512/646 | 282/346 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | v2 | **1/27** | 1 | 0 | 0 | 1 | 72.3% | 32 | 0 | 609/646 | 324/346 |

### 3.1 改善幅度（v2 − v1）

| 抽取器 | 文字 | Hard-stop miss | 假 Hard stop | over | abstention FP | exact |
|---|---|---|---|---|---|---|
| gpt-6.1-sol | 逐字稿原文 | -4 | -1 | +0 | +17 | -14.3 pt |
| gpt-6.1-sol | 電話語音＋Whisper | -2 | -1 | -2 | +18 | -13.4 pt |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | -3 | -21 | -13 | +8 | +7.6 pt |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | -5 | -30 | -19 | +15 | +9.2 pt |

### 3.2 Hard-stop miss 與假 Hard stop 明細（v2）

- gpt/ref：miss （無）；premature （無）；假 Hard stop （無）
- gpt/phone：miss ['S-INSUF-04#0', 'S-MID-06#0', 'S-MID-10#0']；premature ['S-MID-10#0']；假 Hard stop （無）
- gemma/ref：miss ['S-MID-10#0']；premature ['S-MID-10#0']；假 Hard stop （無）
- gemma/phone：miss ['S-MID-10#0']；premature ['S-MID-10#0']；假 Hard stop （無）

### 3.3 複誦回答的解讀（開發集 10-23 逐字稿的複誦回答＋人工探針）

題目原文與複誦句（`confirm_prompt`）一起當 context；正確答案＝逐字稿記下的確認值（10-23 的複誦全是「對」類回答）；探針 15 句含「不是，有啊」「不是。」等更正句（`sim/llm_extract_v2.py` CONFIRM_PROBES）。

| 抽取器 | 開發集複誦回答 | 探針 |
|---|---|---|
| gpt-6.1-sol | 163/164（{'correct': 162, 'speechless': 1, 'wrong': 1}） | 15/15 |
| gemma-4-26b-a4b-it-mlx | 162/164（{'correct': 161, 'speechless': 1, 'invented': 1, 'wrong': 1}） | 15/15 |

### 3.4 迭代紀錄（全部只用開發集；Gemma 本機，不計費）

| 版本 | 改了什麼 | 開發集結果 |
|---|---|---|
| 2.0-dev1 | 初版：回答句與開場白共用一份提示；每句輸出 asked（evidence→是非題 stance yes/no/unclear）＋稀疏 mentions＋unclassified；程式極性保護（mentions 的 true 若片段含否定詞→丟；D-50 範圍內被問那題 stance 與句首明確肯定／否定詞相反→未知）。 | Gemma 7 句開發集冒煙：「現在沒有了」等 4 句極性全對；開場白稀疏格式漏抽（S-MID-11 漏 orthopnea_pnd、symptom_character none，onset_weeks_ago 輸出亂碼）。 |
| 2.0-dev2 | 開場白改為逐欄填寫（稠密）；symptom_character 只在用了選項字眼時才填，其他形容寫 unclassified；unclassified 與值同欄時不寫值（程式）。 | Gemma 開場白 40 句：幾乎全填 null（symptom_character 漏 35、cad_history 漏 13）；unclassified 被濫用（「像被壓住」「今天第一次」也放進去）。 |
| 2.0-dev3 | unclassified 只限選擇題欄位，並說明對得上選項就直接填。 | 同上，開場白仍幾乎全 null。 |
| 2.0-dev4 | 開場白改用獨立提示（以 v1 開場白提示 0.1 為底＋規則 6 沒把握就不填），扁平 schema；回答句另一份提示。 | 開場白 40 句：symptom_character 漏 25；出現憑空否認（沒提到喘卻填 dyspnea_grade none 等）。 |
| 2.0-dev5 | 症狀性質改成明列字眼（壓→pressure、悶→tightness、痛→pain、下顎肩膀手臂沉重、上腹悶脹、說不上來→vague、明確說胸口沒有不舒服→none；脹脹的、緊緊的、怪怪的、不舒服→不填）。 | 開場白 symptom_character 漏 9；但憑空否認變多（dyspnea_grade none 15 句）、「胸口不太舒服」被抽成 none。 |
| 2.0-dev6 | 開場白加規則 7（沒提到不是否認）與 evidence 清單；程式：紅旗 slot＋symptom_character 的否認若沒有含否定詞的原句片段→丟棄。 | 憑空否認消失；symptom_character 漏 21。 |
| 2.0-dev7 | 開場白 schema 改成先寫 evidence 再填欄位；極性保護擴及肯定方向（紅旗 slot 的 true／非 none 值，片段含否定詞→丟棄；last_episode_timing＝ongoing 也算）。 | 開場白 symptom_character 漏 14（其中 8 句是刻意留未知的說法）。全量重放 ref（Gemma）：Hard-stop miss 7/27、premature 0、假 Hard stop 1、abstention FP 29、紅旗題抽錯 6（皆 dyspnea none→未知）。 |
| 2.0-dev8 | 回答句：說不上來指的是位置／時間時不影響症狀感覺；mentions 要寫順帶描述的症狀感覺（以開發集句子「有，現在胸口還是悶悶的」為例），不得從題目推論 ongoing_now／rest_symptom_first_time。程式：asked 沒填、mentions 卻寫了被問那題 → 採用。 | 回答句含症狀字眼時 mentions 有 symptom_character 60/62；但 Q-DYSPNEA-GRADE-01「不太會喘」被填 null 增為 16–19 句。 |
| 2.0-dev9 | 選擇題／時間題的 asked 改成先判斷 status（answered／dont_know／cannot_classify）再填 value（value 不給 null），並以開發集句子舉例。 | Q-DYSPNEA-GRADE-01 正確 87/91（多抽 none 3：「有沒有喘我不知道」）；Q-PATTERN-01 單位錯 4（兩年→2）。 |
| 2.0-dev10 | 時間單位換算例（兩年＝24）；dont_know 例句；程式：回答句順口說的 ongoing_now＝true／last_episode_timing＝ongoing 片段要有「現在、還在…」字眼；asked 選擇題的紅旗否認也要有否定詞；遮罩「有沒有、會不會、是不是」。 | Q-DYSPNEA-GRADE-01 90/91、Q-CHARACTER-01 17/18（另 1 句說不上來）、Q-PATTERN-01 19/20。 |
| 2.0-dev11 | 複誦回答改用專屬 schema：agreement（同不同意複誦的答案）＋restated（病人有沒有重新回答原題）；程式由兩者決定值（是非題只說「不是」→ 相反；選擇題只說「不是」→ 未知）；從複誦句反查客服說的答案（scripts_zh 的值中文）。 | （全量重放 dev10 時 Gemma 複誦回答 110/164、探針 9/15：「對，現在沒有了」被讀成「有」51 句。）dev11：Gemma 仍把 restated 讀成「有沒有重新回答」（yes），探針與開發集多半仍錯。 |
| 2.0-dev12 | restated 改名 reply_answer、選項改中文（「有（情況成立）」「沒有（情況不成立）」「沒有重新回答」）；程式：選擇題複誦回答的否認也要有否定詞。 | Gemma 複誦回答 159/164（多抽 none 4：「我不太清楚」）、探針 15/15。全量重放（4 路並行）：ref Hard-stop miss 5（premature 1）、假 Hard stop 0；phone 6、假 Hard stop 2（開場白 last_episode_timing＝ongoing）。 |
| 2.0-dev13 | 程式：開場白也套「現在還在」字眼規則；句首規則擴大到所有「只問一件事」的是非題（題目一個問號、不是「…還是…」）；轉繁檢查改成不把 NFKC 的全形→半形標點算成簡轉繁。 | Gemma ref 假 Hard stop 1（「現在比較輕一點的活動就會悶」被當成此刻）；symptom_character 的否定詞保護誤丟「現在不會悶了」這類句子的性質。 |
| 2.0-dev14 | 程式：symptom_character 的性質值不套肯定方向保護（只保留 none 要有否定詞）；dyspnea_grade 只對 rest 套；「此刻仍在」字眼不含單獨的「現在」；可用原始輸出重算（送出的提示全文 sha256 相同才可）。 | 正式重放（gpt 8 路、Gemma 一次一句）。 |
| 2.0-dev15 | 程式：紅旗欄位的否認若片段同時表示不確定（不清楚、沒注意、他沒跟我講…）→ 丟棄。送出的提示全文與 dev13／dev14 相同（rendered sha256 不變），以原始輸出重算。 | 最終：見 §3。Gemma 複誦回答 164/164；gpt 163＋1。 |
| 2.0-dev16 | 開發集閉環後的唯一一次修正（程式，送出的提示全文不變）：回答句順口提到的紅旗欄位否認（含 symptom_character＝none）一律不採用；sim/runner.py 順口提到的值不得把已知的值改得較不急（是非題 有→沒有、→none、symptom_character／dyspnea_grade 依 confirm_back_severity）。 | dev15 閉環：病人回答 Q-ONGOING-01「現在沒有，胸口目前不會悶」被抽成 symptom_character＝none、蓋掉開場白的 tightness → 胸部紅旗題不再問：gpt under 4（S-STABLE-01#0、S-STABLE-02#1、S-STABLE-04#0、#1，T0→T3）＋HS miss S-MID-14#1；Gemma under 1（S-STABLE-01#0）＋HS miss S-MID-10#0（「我不會喘」被抽成 symptom_character＝none）。dev16：兩者 HS 27/27、under 0（見 §4.1）；階段 A 重放以原始輸出重算，數字幾乎不變。 |
| 2.0-dev17 | 依獨立驗收修正（程式；送出的提示全文不變）：順口提到的值只補未知的 slot（含問過但答不知道的，修正「問過就永遠擋住」）；已知值只在紅旗是非題「有」或 confirm_back_severity 較嚴重時覆蓋，其他不同保留已知值並記為 conflict（取代 dev16 的「較不急」判斷，該判斷對 reproducible_mechanical 等方向相反、也沒涵蓋 last_episode_timing 等）。 | 開發集閉環只用快取重算（0 次 API）：兩個 arm 逐例最終結果、題序、值、複誦、Hard stop 題次都與 dev16 相同；conflict gpt 1、Gemma 3；Gemma S-MID-13#3 結束時 symptom_character 由 epigastric 變 tightness（順口提到的較嚴重值，結果不變）。階段 A 重放數字不變。 |
| 2.0-dev18 | 第三輪驗收修正（程式；送出的提示全文不變）：(1) 已知值的第三種可覆蓋情況——寫入後規則引擎由非 Hard stop 變成 Hard stop（涵蓋 last_episode_timing＝ongoing 推導 RF-03 等）；(2) D-50 範圍（紅旗題＋stt_critical_questions：含 rest_symptom_first_time、symptom_character、dyspnea_grade）的未知 slot，順口值只收最嚴重一級，較不嚴重的不採用、照常直接問並依 D-50 複誦（記為 d50_not_most_severe）；(3) 閉環 CLI 的前置檢查（金鑰、opencc、LM Studio 連線與模型已載入、輸入檔、凍結 hash）全部移到登記保留集 arm 之前。 | 開發集閉環只用快取重算（0 次 API）：兩個 arm 逐例與 dev16／dev17 相同，結束時 slot 與 dev17 相同；d50_not_most_severe 0 次、因「寫入後 Hard stop」而覆蓋 0 次；conflict 仍為 gpt 1、Gemma 3。階段 A 重放數字不變。驗收者窮舉（595 狀態、49,510 組單一順口值）：被擋下的 Hard stop 升級 0 組（原 15 組）。 |
| 2.0-dev19 | 第四輪驗收修正（程式；送出的提示全文不變）：D-50 範圍 slot 未知時的順口值改三條——(i) 寫入後由非 Hard stop 變成 Hard stop → 收；(ii) 最嚴重一級 → 收；(iii) 其他較不嚴重的值：該題沒問過 → 不收、照常直接問並依 D-50 複誦；該題問過而目前未知 → 立刻對該題做一次 D-50 複誦（以順口值當解讀值、既有複誦模板與 resolve 規則；不算題數、計入複誦次數；每個 slot 一次）。修正 dev18 的「Q-CHARACTER-01 問過但抽不出、之後順口說上腹悶脹／會痛／說不上來被拒收 → 胸部紅旗永遠不成立」。 | 開發集閉環只用快取重算（0 次 API）：兩個 arm 逐例與 dev16／dev18 相同；順口值觸發的複誦 0 次、d50_not_most_severe 0 次；conflict 仍為 gpt 1、Gemma 3。階段 A 重放不變。驗收者 stuck_character_test 6 組全部 Hard stop；enum_r4（1,281 狀態、102,936 組）被擋 Hard stop 升級 0。 |
| 2.0-dev20 | 最終驗收修正（程式；送出的提示全文不變）：D-50 範圍 slot 在「該題還沒問過」時被拒收的較不嚴重順口值改為暫存（同一 slot 留較嚴重者）；之後直接問到、答案仍未知時，以暫存值當解讀值做一次 D-50 複誦（取代一般的未知複誦，不多問一次）；順口值觸發的複誦也計入 n_confirm_changed（以解讀值為基準）。 | 開發集閉環只用快取重算（0 次 API）：兩個 arm 逐例與 dev16／dev19 相同；暫存與順口值觸發的複誦 0 次。階段 A 重放不變。驗收者 d50_injection（578 組注入）：比「沒有順口值」或「全部收下」更不急的組合 0（原本 3 組：S-INSUF-01／02／06 順口說「說不上來」，現改為經複誦定案）；極端壓力測試每通每個 slot 最多複誦一次、題數 ≤ 11。 |
| 2.0-dev21 | 第六輪驗收修正（程式；送出的提示全文不變）：D-50 範圍 slot 的兩種順口值複誦——問過而目前未知時由順口值觸發的立刻複誦、暫存值在直接問到仍未知時的複誦——在「目前已是 Hard stop，或寫入該值（連同同一句順口提到或被問那題的其他值）後會變 Hard stop」時都不做，直接寫入並走 Hard stop（D-50「寫入後即 Hard stop 者不複誦，不得延誤送醫」；條件比照 should_confirm）。 | 開發集閉環只用快取重算（0 次 API）：兩個 arm 逐例與 dev16／dev20 相同；順口值與暫存值觸發的複誦 0 次。階段 A 重放不變。驗收者 stash_hs_delay 兩個情境（暫存 pain 後，Q-CHARACTER-01 的回答說昏倒；Q-CHARACTER-01 答未知後，同一句說昏倒與痛）由「先複誦再 Hard stop」改為不複誦、直接 Hard stop，已納入 pytest；另加「痛」單獨不會 Hard stop、與同一句的冒汗／快暈倒／還在合起來才會的組合（另一個值是順口提到或被問那題的回答各 3 組），同樣不複誦。 |
| 2.0-dev22 | D-54 第一輪：依 Clinical Owner 2026-11-02 對 16 項模糊說法的裁定改提示例句（胸口脹脹的不填、悶悶脹脹的 → tightness、胸口不太舒服 → vague、不太會喘 → exertional_heavy、晚上躺下比較喘 → orthopnea_pnd＋rest_symptom、剛剛就是吃飽坐著的時候 → rest_symptom 等）；新欄位 episode_frequency_increased、chest_discomfort_mentioned。 | 只跑免費驗證（Scripted、假抽取器），未以 LLM 重放 |
| 2.0-dev23 | D-54 第三輪：拿掉開場白概括否認的合併題相關說明；補「發作變頻繁 → episode_frequency_increased」例句。 | 只跑免費驗證，未以 LLM 重放 |
| 2.0-dev24 | D-54 第五輪：「裁定 #7 的說法」說明由送給模型的提示文字移到 YAML 註解（送出的例句不變）。 | 11-03 報告：開發集付費閉環（gpt、Gemma）與階段 A 重放（gpt US$2.48；Gemma 本機，失敗 2 筆） |
| 2.0-dev25 | D-55 R6（Clinical Owner 2026-11-04 裁定 11-03 報告 §5 第 2–10 項；例句只用開發集原句）：開場白規則 7、9、13–18（休息後緩解≠休息時發作、這次休息時也發作≠次數變多、疫苗手臂痠 → minor_noncardiac、走路比平常喘一點 → exertional_daily、忘記吃早上的藥 → antiplatelet_interrupted 留 null、空腹抽血 → education_question、今天還沒發作≠today、最近走路會有一點悶 → exertion_only、比放支架前輕很多≠threshold_decreased）；回答句一般規則 7 與 mentions 例句（休息後緩解不寫 rest_symptom；F6 改字）。程式（sim/runner.py，F2）：順口提到的 rest_symptom＝false 不寫入。抽取程式 sim/llm_extract_v2.py 未改。 | 本報告的 dev25 中間版：開發集付費閉環 Gemma under 1（S-MID-08#0，onset_weeks_ago 4.0）、重放 gpt US$2.61；數字在 inputs/dev25/ |
| 2.0-dev26 | D-55 第五輪（2026-11-05）：刪除開場白規則 17（最近走路會有一點悶 → exertion_only）、18（比放支架前輕很多≠threshold_decreased）。獨立驗收以本機 Gemma 探針確認這兩條讓 S-MID-08 開場白的 onset_weeks_ago 抽成 4.0（dev24 0/5 → dev25 5/5，兩條都刪 → 0/5）。程式（sim/llm_extract_v2.py）：開場白與順口提到的 rest_symptom＝false 一律不採用，只有直接回答 Q-REST-01 才寫入。 | 本報告（最終版）：開發集付費閉環（gpt 逾時後重試一次、Gemma）與階段 A 重放（gpt US$2.54，逾時重試一次後仍失敗 1 筆；Gemma 本機，失敗 0） |

### 3.5 延遲與費用（階段 A）

- gpt-6.1-sol：呼叫 1250、失敗 1；延遲中位數／p95：全部 2.95／9.74 s、開場白 11.83／17.53 s、回答 2.88／6.33 s（並行 8）；程式保護觸發 {'mention_redflag_denial_not_used': 110, 'rest_denial_not_used': 16}（費用見 §6）
- gemma-4-26b-a4b-it-mlx：呼叫 1250、失敗 0；延遲中位數／p95：全部 1.47／7.18 s、開場白 7.53／8.30 s、回答 1.41／2.32 s（並行 1）；程式保護觸發 {'rest_denial_not_used': 28, 'denial_without_negated_evidence': 6, 'mention_redflag_denial_not_used': 48, 'asked_value_from_mentions': 61, 'affirm_with_negated_evidence': 23, 'ongoing_mention_without_present_marker': 3, 'choice_listed_unclassified': 2, 'asked_stance_vs_leading_word': 2}（費用見 §6）

## 4. 階段 B：閉環模擬（Opus 病人 prompt 0.3、effort medium）

**階段 B：開發集閉環 2026-11-05 最終版（2.0-dev26、rules 0.10.0、上限 15，種子為 11-05 逐字稿）；保留集閉環未執行、未凍結。** 結構化值 arm 沿用 dev25 那輪（自我檢查 119/119；只依病人與規則，dev26 沒有改到）。

| 項目 | 估算（USD） | 依據 |
|---|---|---|
| 保留集 gpt arm Opus 病人 | ≈5.5 | 以 dev25 那輪（新呼叫 453 次、病人快取只有種子）US$3.19 × 保留集／開發集結構化值 eval 費用比 1.72（US$9.43／US$5.49）；dev26 的 US$0.84 有重用前一輪快取，不能外推 |
| 保留集 Gemma arm Opus 病人 | ≈3.5 | dev25 那輪 US$2.04 × 1.72 |
| 保留集 gpt 抽取 | ≈2.8 | dev26 第一次 US$1.95＋重試 US$0.10 × 1.35（同 10-27 的例數與呼叫數比） |
| 合計（只跑一次） | ≈12（估 9–15） | 凍結後執行 |

- Opus 病人評估（結構化值，付費，沿用）：開發集 HS 27/27、under 0、over 0、exact 100%，與 Scripted 相同（US$5.49）。保留集三層（sim.synth_eval，參考一致子集 130 例；以 11-05 逐字稿，US$9.43）：(a) HS 51/51、under 14、exact 108；(b) HS 49/51、under 26、exact 97、平均 6.29 題；(c) HS 49/51、under 25、exact 98、平均 6.22 題，重放 150/150 與逐字稿一致（11-03 `_r2`：(c) under 25、exact 98）。

### 4.1 開發集 119 例（對 truth；提示依開發集調整過）

| arm | HS 敏感度 | HS miss（含 premature） | premature | 假 Hard stop | under | over | exact | T9 | 平均題數 | 複誦（每通） | 執行錯誤 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 結構化值（對照） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 0 | 100.0% | 12 | 6.23 | 168（1.41） | 0 |
| gpt-6.1-sol（2.0-dev26） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 96.6% | 14 | 6.65 | 198（1.66） | 0 |
| gemma-4-26b-a4b-it-mlx（2.0-dev26） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 96.6% | 14 | 6.92 | 212（1.78） | 0 |

under／over 不含 T9（T9 另計）；premature＝Hard stop 只靠抽錯的值成立（把當時已知的 slot 換回病人真正知道的事實後不再是 Hard stop），計為 miss。

- gpt-6.1-sol（2.0-dev26）：HS miss （無）；premature （無）；假 Hard stop （無）；under （無）；over [['S-MID-08#2', 1, 0], ['S-MID-13', 3, 0]]
- gemma-4-26b-a4b-it-mlx（2.0-dev26）：HS miss （無）；premature （無）；假 Hard stop （無）；under （無）；over [['S-MID-02', 2, 0], ['S-MID-13', 3, 0]]

### 4.1b 每例 Hard stop 題次（truth 為 Hard stop 的開發集 case；最終版）

題次＝觸發 Hard stop 時已問的題數（0＝開場白；不含複誦）；—＝沒有觸發。

| case | truth RF | 結構化值 | gpt | Gemma | 比結構化值晚（gpt／Gemma） |
|---|---|---|---|---|---|
| S-ACUTE-01#0 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-ACUTE-02#0 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-ACUTE-02#1 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-ACUTE-03#0 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-ACUTE-03#1 | RF-04 | 2 | 2 | 2 | +0／+0 |
| S-ACUTE-04#0 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-ACUTE-05#0 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-ACUTE-06 | RF-01 | 0 | 0 | 0 | +0／+0 |
| S-ACUTE-06#0 | RF-05 | 0 | 0 | 0 | +0／+0 |
| S-INSUF-04#0 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-INSUF-07#0 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-01#2 | RF-06 | 3 | 3 | 4 | +0／+1 |
| S-MID-03#0 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-05#0 | RF-01 | 3 | 4 | 4 | +1／+1 |
| S-MID-06#0 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-10#0 | RF-01 | 5 | 5 | 5 | +0／+0 |
| S-MID-10#1 | RF-05 | 1 | 1 | 1 | +0／+0 |
| S-MID-11#0 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-11#1 | RF-04 | 2 | 2 | 2 | +0／+0 |
| S-MID-12#1 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-13#0 | RF-06 | 3 | 2 | 3 | -1／+0 |
| S-MID-13#1 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-14#1 | RF-06 | 4 | 4 | 4 | +0／+0 |
| S-MID-16#1 | RF-02 | 3 | 3 | 4 | +0／+1 |
| S-MID-17#1 | RF-03 | 4 | 4 | 4 | +0／+0 |
| S-MID-19#2 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-19#3 | RF-06 | 4 | 3 | 4 | -1／+0 |

### 4.1c 順口提到的值與已知值不同（conflict：保留已知值，最終版）

規則：順口提到的值補未知的 slot；D-50 範圍（紅旗題＋stt_critical_questions）的未知 slot 只收「寫入後變成 Hard stop」或最嚴重一級，其他較不嚴重的值：該題沒問過 → 不收（d50_not_most_severe）但暫存，之後直接問到、答案仍未知時以暫存值當解讀值 D-50 複誦一次；問過而目前未知 → 立刻對該題 D-50 複誦一次（以順口值當解讀值，計入複誦）；這兩種複誦在目前已是 Hard stop、或寫入該值（連同同一句的其他值）後會變 Hard stop 時都不做，直接寫入並走 Hard stop（D-50 不延誤送醫）；已知值只在三種情況被覆蓋——紅旗是非題的「有」、`confirm_back_severity` 已核定順序中較嚴重的值、寫入後由非 Hard stop 變成 Hard stop；其他不同一律保留已知值（conflict）。下列為全部沒採用的順口值。

- gpt-6.1-sol：順口值矛盾再問 0 次；因再問而最終較不急 0 次（只把再問前的值放回最後狀態重算、不重跑對話，路徑分岔造成的差異記不到；明細見閉環 JSON 的 reasks）
- gpt-6.1-sol：順口值觸發的複誦 0 次；沒採用 2 次（{'d50_not_most_severe': 1, 'conflict': 1}）：S-INSUF-06#1 第 1 題 Q-DYSPNEA-GRADE-01（d50_not_most_severe）：symptom_character 已知 None、順口 vague「喔，我其實不會喘耶，走路做家事都還好，就只是胸口偶爾怪怪的而已。」；S-MID-03#0 第 1 題 Q-ONGOING-01（conflict）：symptom_character 已知 pain、順口 vague「有，現在這個時候胸口還是有不舒服。」
- gemma-4-26b-a4b-it-mlx：順口值矛盾再問 1 次；因再問而最終較不急 0 次（只把再問前的值放回最後狀態重算、不重跑對話，路徑分岔造成的差異記不到；明細見閉環 JSON 的 reasks）
- gemma-4-26b-a4b-it-mlx：順口值觸發的複誦 0 次；沒採用 13 次（{'conflict': 9, 'd50_not_most_severe': 4}）：S-ACUTE-01#0 第 1 題 Q-ONGOING-01（conflict）：symptom_character 已知 pressure、順口 tightness「嗯，現在還是有，胸口還是覺得悶悶壓壓的。」；S-STABLE-01#2 第 6 題 Q-DYSPNEA-ACUTE-01（conflict）：dyspnea_complaint 已知 True、順口 False「不是今天忽然變明顯的啦，其實我本來就沒什麼在喘。」；S-STABLE-03#0 第 4 題 Q-ONGOING-01（conflict）：symptom_character 已知 pressure、順口 vague「這個我不太確定耶，講不太上來。」；S-STABLE-04#0 第 6 題 Q-DYSPNEA-ACUTE-01（conflict）：dyspnea_complaint 已知 False、順口 True「不是今天突然變明顯的啦，我本來就不太會喘。」；S-INSUF-04 第 1 題 Q-DYSPNEA-GRADE-01（d50_not_most_severe）：symptom_character 已知 None、順口 vague「這個我也說不太上來耶，不太確定是做什麼的時候比較會喘。」；S-INSUF-08#1 第 3 題 Q-DYSPNEA-GRADE-01（conflict）：dyspnea_complaint 已知 True、順口 False「不是喔，我是都不會喘，就算動一動也還好。」；S-MID-01 第 6 題 Q-DYSPNEA-ACUTE-01（conflict）：dyspnea_complaint 已知 True、順口 False「這個我不太會講耶，我本身其實沒有覺得在喘。」；S-MID-01 第 13 題 Q-EXERTION-01（conflict）：symptom_character 已知 tightness、順口 vague「這個我也說不太上來耶，不太清楚跟走路用力有沒有關係。」；S-MID-01 第 15 題 Q-ONSET-WEEKS-01（conflict）：symptom_character 已知 tightness、順口 vague「確切多久我也講不太準耶，只知道是最近才開始有這種感覺的。」；S-MID-06#1 第 3 題 Q-ONGOING-01（d50_not_most_severe）：symptom_character 已知 None、順口 vague「這個我不太確定耶，我主要是走路做事會喘，胸口現在有沒有怎樣我說不上來。」；S-MID-06#1 第 3 題 Q-ONGOING-01（d50_not_most_severe）：symptom_character 已知 None、順口 vague「歹勢，這個我真的不確定，沒辦法說有還是沒有，我主要就是活動的時候會喘。」；S-MID-14 第 5 題 Q-EXERTION-01（conflict）：symptom_character 已知 pain、順口 vague「這個我也說不太清楚耶，好像跟走路用力沒有很明顯的關係，我分不太出來。」；S-MID-16#1 第 1 題 Q-ONGOING-01（d50_not_most_severe）：symptom_character 已知 None、順口 pain「對，現在沒有在痛，胸口不舒服已經沒了。」

觀察：dev26 的 rest_symptom＝false 在抽取器就被攔下（guard rest_denial_not_used；不在本節的 mention_conflicts 裡），runner F2 本輪 0 次。Gemma 的 Q-ONGOING-01 回答仍有 4 句抽成 rest_symptom＝true（S-STABLE-04#0 事實 true；S-MID-02、#0、S-MID-13#2 事實 false）；S-MID-02 因開場白的 false 不再採用、沒有矛盾可再問，落 T0（見 §1）。

### 4.2 保留集 150 例（對 LLM 參考標註；凍結後一次）

**未執行**（提示未凍結；`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑）。

### 4.3 閉環中的抽取（被問那題確認前的值 vs 病人模擬的結構化值）

| 資料 | arm | 被問那題 | 複誦回答 | 紅旗題「有」沒抽成「有」 | 病人呼叫：新／重用 | 抽取器費用 | 送進抽取器前被轉換的句子 |
|---|---|---|---|---|---|---|---|
| dev | gemma-4-26b-a4b-it-mlx（2.0-dev26） | {'correct': 787, 'wrong': 15, 'invented': 5, 'unknown_equiv': 7, 'speechless': 9, 'missed': 1} | {'correct': 191, 'missed': 12, 'wrong': 2, 'speechless': 5, 'invented': 2} | 0 | 153／884（{'live_reused': 392, 'seed': 492, 'live': 153}） | US$0.0000 | 0 |
| dev | gpt-6.1-sol（2.0-dev26） | {'correct': 750, 'wrong': 15, 'invented': 3, 'unknown_equiv': 14, 'speechless': 9} | {'correct': 189, 'speechless': 5, 'wrong': 1, 'invented': 2, 'missed': 1} | 0 | 0／989（{'live_reused': 475, 'seed': 514}） | US$0.1004 | 0 |

## 5. 模糊說法清單（交 Clinical Owner 裁定；v2 一律留未知、讓系統追問）

裁定表：`reports/extractor_v2_ambiguous_2026-11-05.md`／`.xlsx`（含開發集原句、可能的歸類、提示是否已寫入例句、留空的裁定欄）。表末兩列：第 15 列 Prompter 設計缺口（symptom_character 未知時當成沒有胸部症狀）；第 16 列設計取捨（病人直接回答較不急的值、又在別句順口說出較急的值時，目前保留直接回答、只記 conflict、不升級；開發集升級方向的 conflict 0 次，驗收者窮舉已知值衝突 669 組）。**凍結前須先裁定**：第 12 項「不太會喘 → none」已以例句寫進提示。

11-03 的第 1–10 項已在 2026-11-04 裁定（D-55：第 1 項由 15 題上限處理，R1 已撤回；第 2–10 項改提示，最終為 2.0-dev26），本表不再列。下列是 11-05 開發集付費閉環（dev26 最終版）裡，**v2 已經抽錯或需要再問** 的說法（不是「留未知、讓系統追問」）。只用開發集（11-05 逐字稿的閉環、10-20 逐字稿的重放），沒有看任何保留集抽取結果。「v2 處理」是 2.0-dev26 的實際輸出，不代表已採用；以下都屬臨床歸類，本輪未改規則、題庫、提示或抽取程式。

| # | 說法 | 欄位 | 開發集出現處 | 關鍵詞抽取器（Phase 0）歸類 | v2 處理 | 待裁定 |
|---|---|---|---|---|---|---|
| 1 | 「我其實不太會喘耶／我是不會喘啦，主要是走快一點胸口會悶悶的而已」 | dyspnea_grade | 閉環 Q-DYSPNEA-GRADE-01 回答（gpt S-ACUTE-05#1；Gemma S-MID-01、S-MID-07） | （無值） | 抽成 exertional_heavy（事實 none）。前者是裁定 #12；後者是 Gemma 把走快胸悶當成喘。複誦「不是喔，我是不會喘」：gpt 讀成 none、依 D-50 取較嚴重仍 heavy；Gemma 讀成不明、保留原值 | 有呼吸症狀 → H3 兩題；病人根本不喘、答「不知道」→ H3 永遠缺 → 15 題 T9（備援 T1；truth T3、T1、T1）。重算：dyspnea 改 none（連同 D-25 推導）→ truth。上限救不了這一型（見表末「H3 兩題答不知道」） |
| 2 | 「這個我沒特別記欸，不太確定最後一次是什麼時候好的」 | last_episode_timing | 閉環 Q-TIMING-01 回答（gpt） | （無值） | gpt 判成 dont_know → 未知（null）；結構化值與 Gemma 是 slot 選項 unknown。Q-TIMING-01 的 choices 沒有 unknown，slot 有 | gpt S-MID-08：順口補上 exertion_only 後走 T3-POST-PCI-MILDER，它要知道時序；null 之後不再問 → 15 題 T9（備援 T1）。重算：改 unknown → T3＝truth。題目答「不記得」要不要寫成 unknown（提示或程式）？ |
| 3 | 「最近走路會有一點悶」 | exertion_relation | S-MID-08 開場白（#0–#2 共用）；閉環回答句「就是走路的時候胸口有點悶」 | exertion_only | dev26 刪掉規則 17 後，gpt 開場白不填（同 11-03）；S-MID-08#2 的回答句也沒順口抽成 exertion_only。Gemma 仍抽成 exertion_only | gpt S-MID-08#2 由 T1 變 T0（DV-4 不適用 → 新發、時序未知 → T0-NEW-TODAY，第 5 題定案，偏急）。重算：補 exertion_only 就不是 T0。是回到 11-03 第 9 項的另一個做法「T0-NEW-TODAY 遇到 DV-4 候選時先問 Q-EXERTION-01」（規則），還是維持？ |
| 4 | 「現在沒有啦，現在坐著休息，胸口都不會悶」 | rest_symptom | 閉環 Q-ONGOING-01 回答（順口；Gemma S-MID-02、#0、S-MID-13#2） | （無值） | Gemma 抽成 rest_symptom＝true（事實 false） | S-MID-02 由 T2 變 T0：dev26 不再採用開場白「休息時從來沒有」的 false，這個誤抽的 true 直接寫入（沒有已知值可矛盾、不觸發 #16）→ T0-REST-NEW。dev25 時由 #16 再問改回。要不要加例句？ |
| 5 | 「休息時從來沒有／休息時沒有／沒有休息時發作」 | rest_symptom | S-MID-02、S-MID-03、S-MID-07、S-MID-19 開場白（gpt、Gemma） | false | dev26 的抽取器一律不採用開場白與順口的 rest_symptom＝false（記 guard rest_denial_not_used；開場白 gpt 5 句、Gemma 7 句），包括這些正確、明確的否認 | 代價：這些通話都要再問 Q-REST-01（問到的通話 gpt 40 → 42、Gemma 39 → 43）；之後若有誤抽的順口 true 會直接寫入（上一項）。開發集閉環沒有因此變得較不急。要不要只攔「休息後緩解」類說法、放行明確否認？ |
| 6 | 「前天開始走路會胸悶／這兩天」 | onset_weeks_ago | S-MID-19、S-INSUF-07 開場白（Gemma） | （無值） | 方向：可能偏不急（under-triage），這次分級未受影響。Gemma dev26 都抽成 2.0 週（前天、兩天當成兩週）；本機探針各 5/5，dev24 時分別是 0.0 與 None，拿掉規則 16 仍是 5/5。gpt 對 S-MID-19 抽成 0.2857 週（正確），S-INSUF-07 不填 | 方向：可能偏不急（under-triage）；這次分級未受影響（S-MID-19 系列與結構化值相同；S-INSUF-07 truth T9）。機制與 dev25 的 S-MID-08#0 under 相同：時序未知時，0.29 週走 T0-NEW-TODAY，2.0 週走 T2-NEW-STABLE-WEEKS。要不要加單位例句（兩天＝0.3 週），或開場白順帶的 onset_weeks_ago 改問 Q-ONSET-WEEKS-01？ |

## 6. 費用與耗時

- 合計（依 repo PRICES 估算，以帳單為準）：Anthropic **US$22.11**；OpenAI **US$9.36**（逐項見 §1 費用表；另 D-55 前段 R6 提示自我檢查 OpenAI 約 US$0.44，見 D-55）
- 本輪 dev26（最終版）：Anthropic US$1.97＝閉環 gpt arm US$0.84（第一次 106 次新呼叫；重試 0 次）＋Gemma arm US$1.13（153 次新呼叫）；OpenAI US$4.59＝閉環 US$1.95＋重試 US$0.10＋階段 A 重放 US$2.47＋重試 US$0.07
- 上一輪 dev25（中間版）：Anthropic US$5.22＝閉環 gpt arm US$3.19＋Gemma arm US$2.04；OpenAI US$4.76＝閉環 US$2.16＋重放 US$2.61
- 開發集 Opus 病人 eval（沿用）：Anthropic US$5.49
- 保留集逐字稿 eval（沿用）：Anthropic US$9.43
- OpenAI 逾時：dev26 gpt 閉環第一次 16 次 TimeoutError（300 s），重試後 1 次；重放第一次 42 次，重試後 1 次（失敗不計費）
- Gemma（本機，不計費）：閉環 2026-11-05 19:20–19:41；重放 19:42–20:20（一次一句，1,250 次、失敗 0）

## 7. 改動的檔案

- `sim/closed_loop.py`：DEV_STRUCTURED／HOLDOUT_STRUCTURED 改指 11-05 逐字稿（只改路徑；dev25 那輪改的）
- `reports/extractor_v2_2026-11-05_inputs/`：本報告輸入（dev26 閉環與重放、目前 hash、迭代、待確認說法、結論、費用）；dev25/ 是中間版的閉環與重放；dev26_gpt_attempt1/ 是 gpt 閉環與重放第一次（逾時）的結果
- `reports/extractor_v2_2026-11-05.{md,json}、reports/extractor_v2_ambiguous_2026-11-05.{md,xlsx}`：本報告與裁定表（sim.extractor_v2_report 產生；裁定表 md 開頭加更正段）
- `docs/DECISIONS.md`：D-55「付費評估」改為最終結果摘要
- `（D-55 既有、本報告未改）data/extractor_prompts_v2.yaml、sim/llm_extract_v2.py、sim/runner.py、data/clinical_rules.yaml、data/question_bank_seed.yaml`：2.0-dev26（刪規則 17、18）、rest_symptom＝false 攔截、F2、rules 0.10.0、題庫 0.6、max_questions 15

## 8. 重現

```
病人快取：PatientCache.load(<scratch>/closed1105/cache/patient_cache_dev.json)＋PatientCache.load(<scratch>/closed1105b/cache/patient_cache_dev.json) → save(<scratch>/closed1105c/cache/patient_cache_dev.json)（同 meta、內容相同）
PYTHONPATH=<本機 opencc>:src:. python -m sim.closed_loop run --set dev --arm gpt|gemma --cache-dir <scratch>/closed1105c/cache --out <scratch>/closed1105c/out（gpt --opus-budget 4.5 --gpt-budget 3.5，逾時後以同一 cache 重跑一次：--opus-budget 2.0 --gpt-budget 3.0；Gemma --opus-budget 4.0）；結構化值 arm 沿用 dev25 那輪
PYTHONPATH=<本機 opencc>:src:. python -m sim.llm_extract_v2 replay --extractors gpt --tag gpt --workers 8 --budget 3.5（逾時後同一 cache 重跑一次）；--extractors gemma --tag gemma --local-workers 1；--cache-dir <scratch>/replay1105c/cache --out <scratch>/replay1105c/out；兩檔合併成本目錄的 stage_a_replay.json
python -m sim.synth_eval --llm-json reports/eval_2026-11-05_llm_scenarios_synth_v1_opus-5-5_medium.json --out <scratch>/synth1105（保留集三層，只看彙總行；dev26 不影響）
python -m sim.extractor_v2_report --inputs reports/extractor_v2_2026-11-05_inputs --out reports
裁定表 md：上一步產生 reports/extractor_v2_ambiguous_2026-11-05.md 後，在開頭加上 reports/extractor_v2_2026-11-05_inputs/ambiguous_md_fix.md（cat fix md > tmp && mv tmp md）
```
