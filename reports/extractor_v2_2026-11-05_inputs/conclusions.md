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
