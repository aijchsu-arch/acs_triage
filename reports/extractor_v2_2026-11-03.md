# 抽取器 v2 與閉環模擬（D-52 第 3 項）— 2026-11-03

> **限制（先讀）**
>
> 1. **合成病人**：病人回答由 Opus 5.5 依情境事實（hidden sheet）生成，句子比真實病人完整、少答非所問；正確答案＝情境事實（開發集為單一裁定者 truth）。這是一致性檢查，不是準確度，不能外推臨床表現。
> 2. **合成語音或沒有語音**：階段 A 的 phone 條件是 macOS `say` 合成標準國語＋模擬電話線路＋本機 Whisper（D-49），沒有台語、高齡口音與環境噪音，是樂觀上限；階段 B 閉環完全沒有語音（病人文字直接進抽取器），等於 STT 完美。
> 3. **LLM 參考標註**：保留集的「對照答案」是 Opus 5.5 與 gpt-6.1-sol 的獨立標註（暫定；Clinical Owner 尚在裁定 48 例），不是 truth；主分析用兩位標註者一致的子集。
> 4. **雲端模型不可用於真實資料**：gpt-6.1-sol 只是「抽取能力上限」參考；真實病人資料不得送外部 API（D-10）。院內可部署的候選是本機模型（Gemma）。全部資料為合成資料。
> 5. **病人回答重用（配對設計）**：閉環的病人以「對話前綴快取」包一層：同一 case、同一串客服問句（含複誦句）就重用已取得的 Opus 回答，種子是結構化值閉環的逐字稿（開發集 10-23、保留集 10-26），gpt 與 Gemma 兩個 arm 共用。問句序列相同時病人看到的對話完全相同，重用的是同一個樣本（三個 arm 之間是配對比較，不是獨立重抽）；序列一分岔，之後都是新的 API 呼叫。
> 6. **開發集調整過；保留集尚未執行**：抽取提示只依開發集逐字稿調整（迭代紀錄見 §3.4），本報告的數字全部來自開發集，因此偏樂觀；提示尚未凍結，保留集（data/synth/）沒有執行、也沒有看任何保留集抽取結果。

## 1. 結論（人工撰寫，依本報告數字）

**本報告的範圍與版本**：抽取提示 2.0-dev24、rules 0.9.0、題庫 0.5（D-54 五輪修正後的工作樹，未 commit）。病人前綴快取的種子改為 11-03 有效版逐字稿（`reports/eval_2026-11-03_llm_opus-5-5_medium_r2_transcripts.json`；保留集 `..._synth_v1_..._r2_transcripts.json`）。同日不帶 `_r2` 的 eval 檔是 N1 修正前跑的，hash 不符、**已作廢**（保留原樣，不採用）。提示未凍結，保留集閉環未執行。

**固定說明文字的更正（報告程式的文字是 10-27 版，本次不改程式）**：
- 限制第 5 點的種子：本次是 11-03 `_r2` 逐字稿，不是 10-23／10-26。
- §5 標題「v2 一律留未知、讓系統追問」與前言：本次 §5 不是 10-27 的 16 項（那 16 項已在 2026-11-02 裁定，D-54），改列這次付費結果中 **v2 已經抽錯或需要再問** 的說法（10 項）。
  - 裁定表 `extractor_v2_ambiguous_2026-11-03.*` 的第 11 列是下方「已知限制」6 項（含 L1）、第 12 列是題數上限取捨，不是 10-27 的「Prompter 缺口／順口值取捨」。
  - 「第 12 項不太會喘 → none」那句不適用：裁定 #12 已改成 exertional_heavy，並以例句寫進提示（本次第 1 項）。
  - 裁定表 md 的前言也是同一段寫死文字，已在該檔開頭加更正段。
- §3 表把 0.6975 顯示為 69.8%：實際是 83/119＝69.7%（11-03 gpt 電話、10-27 Gemma 電話）。原因是重放 JSON 先存到小數 4 位，報告再進位一次。

### 結論
1. **Hard stop 沒有漏**：
   - 開發集閉環三個 arm 都是 27/27，沒有 premature、沒有假 Hard stop、under 0。
   - Opus 病人評估（結構化值）開發集 HS 27/27、under 0、over 0、exact 100%，與 Scripted 相同。
2. **與 10-27 相比**：gpt exact 116 → 113（−3）。Gemma 110 → 107（−7、+4）；over 3 → 7。所有偏差都是較急方向（T0、T3 或 T9；T9 的備援都比 truth 急或相同）。主要原因有兩個：
   - **第 1 類**：裁定 #12「不太會喘 → exertional_heavy」，加上複誦更正沒能把值降回來。
     - gpt 11 句複誦中，9 句讀成 none，D-50 取較嚴重仍留 heavy；2 句讀成 heavy。
     - Gemma 18 句中，17 句把「不是喔，我是不會喘」讀成**不明**，依 §5.10-6 保留原值；1 句讀成 none。
     - 結果：有呼吸症狀 → 加問講話與 H3 兩題 → 12 題上限 → T3 變 T9。
   - **Gemma 的開場白與順口值抽取錯誤**：rest_symptom、episode_frequency_increased、threshold_decreased、exertion_relation、時序、dyspnea_grade、consult_topic。
3. **Gemma 救回 4 例**：S-MID-02、S-STABLE-01、S-MID-16、S-MID-15#0 在 10-27 都停在 11 題上限（T9）。11-03 分別用 9、10、11、12 題定案。只有 S-MID-15#0 用到第 12 題；上限 11 → 12 與提示改動各貢獻多少，拆不開。
4. **階段 A 重放**：
   - Hard-stop miss 降了：gpt 原文 4→1、電話 6→3；Gemma 原文 5→1、電話 6→1。剩下的 miss：S-MID-10#0 四格都有（premature）；gpt 電話另有 S-INSUF-04#0、S-MID-06#0。
   - exact 下降、abstention 增加有兩個來源：
     - 重放用的 10-20 對話固定、不補問：新 gate 要的 `episode_frequency_increased`（Q-FREQ-01）與 H3 呼吸兩題從沒被問到。gpt 逐字稿原文有 13 例只缺這些新 gate 欄位。
     - 和閉環第 1 類同一機制：gpt 原文「被問那題正確」631 → 614（−17）。新錯的 17 句中，16 句是 dyspnea_grade none → exertional_heavy（#12 例句對上 10-20 的 truth none），1 句是 Q-EXERTION-01 null → unclear。gpt 原文要 H3 欄位的 abstention 7 例中，6 例也是 dyspnea 被抽成 heavy。
5. **Gemma 重放失敗 2 筆**：都是 Q-PATTERN-01 的回答，LM Studio 輸出到長度上限（`finish_reason=length`，約 32–34 秒）。
   - S-INSUF-04#2（逐字稿原文）：真的多 1 例 abstention。電話條件抽對，不 abstain。
   - S-INSUF-08#1（電話）：本來就因 dyspnea 抽成 heavy、H3／FREQ 沒問而落 T9；原文條件 pattern 抽對也一樣 abstain。失敗不改變結果。
6. **再問（#16）**：
   - gpt 2 次：都是順口把 rest_symptom 抽成「有」、與已知的「沒有」矛盾，再問後確認「沒有」。順口的「有」來自 Q-ORTHO-01 的回答「躺平比較喘、要墊高枕頭」，依裁定（晚上躺下比較喘 → orthopnea_pnd＋rest_symptom）會抽成 rest_symptom 有，但開發集事實是 rest＝false；因為端坐呼吸本來就判 T0，分級不受影響。
   - Gemma 10 次：9 次把先前抽錯的已知值改回（rest_symptom 6、threshold_decreased 3），1 次 onset_new 再問不明、保留原值。
   - Gemma 的 `reask_downgrades` 1 例是 S-ACUTE-01#2：Q-ONGOING-01「休息完就好了」被抽成 rest 有；Q-REST-02 的回答矛盾，再問 Q-REST-01 答「沒有」。最終 T3＝truth，不比 truth 不急。

### 10-27 與 11-03 並列（開發集）

| 項目 | 10-27（2.0-dev21） | 11-03（2.0-dev24） |
|---|---|---|
| 閉環 結構化值 exact／T9／平均題數 | 100%／12／5.60 | 100%／12／5.91 |
| 閉環 gpt HS／over／exact／T9／平均題數／複誦 | 27/27／2／97.5%（116）／13／5.74／186 | 27/27／2／95.0%（113）／16／6.16／192（再問 2） |
| 閉環 Gemma HS／over／exact／T9／平均題數／複誦 | 27/27／3／92.4%（110）／18／6.03／197 | 27/27／7／89.9%（107）／15／6.24／201（再問 10、再問後較不急 1） |
| 重放 gpt 原文 HS miss／exact／abstention FP／被問那題正確 | 4／79.8%／24／631 | 1／73.1%／32／614 |
| 重放 gpt 電話 HS miss／exact／abstention FP | 6／74.8%／30 | 3／69.7%／36 |
| 重放 Gemma 原文 HS miss／over／exact／abstention FP | 5／3／75.6%／26 | 1／5／74.8%／25 |
| 重放 Gemma 電話 HS miss／over／exact／abstention FP／紅旗「有」漏抽 | 6／3／69.7%／33／2 | 1／5／71.4%／29／0 |
| 複誦回答解讀（開發集 164 句；探針 15） | gpt 163＋1 說不出；Gemma 164 | gpt 162＋1 說不出、錯 1；Gemma 160、錯 2、說不出 1、自編 1；探針都 15/15 |

複誦解讀的錯誤全部是 dyspnea_grade 抽成 exertional_heavy：
- gpt 那 1 句是「對，我不太會喘」：依裁定 #12 其實正確，只是 10-23 的確認值仍是 none。
- Gemma 的 3 句（「我沒有在喘，就只是很用力的時候胸口會有點悶」等）：把胸悶當成喘。

### 與結構化值不同的 case（11-03 閉環；結構化值 arm 全部＝truth；逐例對最終 slot 重算確認）

| case | truth | gpt | Gemma | 10-27 gpt／Gemma | 原因（證據在閉環 JSON 的 turns） |
|---|---|---|---|---|---|
| S-INSUF-01#1 | T3 | T9（12 題） | T9（12 題） | T3／T3 | 第 1 類：Q-DYSPNEA-GRADE-01「我其實不太會喘耶…」→ exertional_heavy（事實 none）。複誦「不是喔…」gpt 讀成 none 後取較嚴重、Gemma 讀成不明保留，都仍是 heavy → 加問講話、H3 兩題 → 12 題用完仍缺 pattern → T9（備援 T1） |
| S-INSUF-05#1 | T3 | T9（12 題） | T9（12 題） | T3／T3 | 第 1 類（同上）；缺 NTG → T9（備援 T1） |
| S-INSUF-02#1 | T3 | T3 | T9（12 題） | T3／T3 | 第 1 類（Gemma）；gpt 那次病人回答不同（「喘的話其實沒有耶」），抽成 none |
| S-MID-08#2 | T1 | T1 | T0 | T1／T1 | 不屬第 1 類：第 9 題 `gate_passed_t0_asked` 定案，沒到上限。Gemma 開場白多抽 threshold_decreased＝有（「比放支架前輕很多，但以前是完全沒有」）、exertion_relation＝unclear（DV-4 不適用）→ T0-NEW-TODAY＋T0-THRESHOLD-DAYS。重算：dyspnea 改回 none 分級不變；threshold 改 false 且 exertion_only → T3，再加上事實的 antiplatelet → T1＝truth |
| S-MID-08 | T3 | T0 | T0 | T0／T0 | 既有：開場白「最近走路會有一點悶」沒抽成 exertion_only（gpt null、Gemma unclear；Gemma 另把 Q-ONGOING-01「坐著休息的時候都還好」抽成 rest 有、沒改回）→ DV-4（PCI 後較輕）不適用 → T0-NEW-TODAY；T0 定案前不問 Q-EXERTION-01。重算：exertion 補 exertion_only（Gemma 再加 rest＝false）→ T3-POST-PCI-MILDER＝truth；時序改 unknown、補 onset_weeks 仍是 T0。不是 Q-TIMING-01 的 null（Gemma 這題抽成 unknown，是對的） |
| S-MID-18 | T4 | T9（7 題，沒有可問的題） | T4 | T4／T4 | gpt 開場白把「昨天打完流感疫苗手臂痠」的 consult_topic 抽成 symptom（dev21 留 null，之後追問得 minor_noncardiac）→ 沒有 T4 路徑 → T9-NO-RULE（備援 T3）。不是 chest_discomfort_mentioned 誤觸（沒設），也不是 vague |
| S-MID-12 | T2 | T2 | T9（9 題，沒有可問的題） | T2／T2 | Gemma 開場白把「走路比平常喘一點」抽成 exertional_heavy（事實 exertional_daily；dev21 抽對；關鍵詞抽取器也是 daily）→ 改走 T2-DYSPNEA-HEAVY，它的 sufficiency 要知道 pattern（≥6 個月改 T3，D-45）→ Q-PATTERN-01 答不知道、無題可問 → T9（備援 T1）。不是旗標誤觸，也不是 vague。是否受 #12 例句影響：未能確定（要以 dev21 提示重放才能分開） |
| S-ACUTE-05#1 | T3 | T3 | T0 | T3／T3 | Gemma 開場白把「以前只有運動才胸悶，今晚躺著看電視時也發作了」抽成 episode_frequency_increased＝有（事實沒有）→ T0-FREQ-INCREASED（裁定 #7 的新欄位） |
| S-INSUF-05 | T9 | T9 | T0 | T9／T9 | Gemma 把 Q-ONGOING-01「現在沒有了，坐著休息的時候就不會悶」順口抽成 rest_symptom＝有（休息緩解當成休息時發作）→ T0-REST-NEW；Q-REST-02 答「不太清楚」→ D-45 不降級、直接定案；之後沒有矛盾，所以沒觸發再問 |
| S-MID-13 | T3 | T0 | T0 | T0／T9 | Q-EXERTION-01「吃飽坐著」→ rest_symptom（裁定，Clinical Owner 接受為偏急）→ T0-REST-NEW。10-27 的 Gemma 是在 11 題上限落 T9 |
| S-MID-19 | T1 | T1 | T0 | T1／T9 | Gemma 開場白把「前天開始…今天還沒發作」的時序抽成 today（事實 yesterday_within_24h；10-27 的重放也抽錯）→ T0-NEW-TODAY。10-27 在 11 題上限落 T9，所以看不出 |
| S-MID-15#0 | T1 | T9（12 題） | T1 | T9／T9 | 既有：開場白「舌下含片過期了可以用嗎」沒抽 ntg（照「沒說到填 null」），多問 Q-NTG-01，Q-ANTIPLT-01 被上限擠掉 → T9（備援 T1，急迫度同 truth） |
| S-MID-17 | T4 | T4 | T3 | T4／T3 | 既有（10-27 相同）：Gemma 把「今天忘記吃早上的藥」抽成 antiplatelet_interrupted＝有（沒說是哪種藥）→ T3 抗血小板中斷無症狀 |
| S-MID-20 | T4 | T4 | T3 | T4／T3 | 既有（10-27 相同）：Gemma 把「想問下次回診要不要空腹抽血」的 consult_topic 抽成 appointment_admin（事實 education_question）→ T3 行政 |

### 依原因量化（相對 10-27，開發集 119 例；exact 的分母含 truth T9）
- **gpt exact −3**＝第 1 類 2（S-INSUF-01#1、S-INSUF-05#1）＋開場白 consult_topic 1（S-MID-18）。gpt over 不變（S-MID-08、S-MID-13 兩例 10-27 就有）。
- **Gemma exact −7**＝第 1 類 3（S-INSUF-01#1、S-INSUF-02#1、S-INSUF-05#1）＋其他 4：
  - S-ACUTE-05#1：#7 新欄位誤抽；
  - S-INSUF-05：rest_symptom 誤抽；truth T9，計入 exact −1，但不算 over；
  - S-MID-08#2：開場白 threshold_decreased 誤抽＋exertion unclear；
  - S-MID-12：開場白 dyspnea_grade 誤抽。
- **Gemma exact +4**：見結論 3。
- **Gemma over +4**：
  - S-ACUTE-05#1（#7）；
  - S-MID-08#2（threshold＋exertion）；
  - S-MID-13（CO 已接受的 rest 例句；10-27 被 11 題上限遮住）；
  - S-MID-19（時序誤抽；10-27 被 11 題上限遮住）。
  - over 既有 3 例：S-MID-08、S-MID-17、S-MID-20。
- 閉環裡「事實沒有喘、被抽成 exertional_heavy」：gpt 11 例、Gemma 18 例；分級受影響的只有上列第 1 類。

### 已知限制（本輪驗收發現，待 Clinical Owner 確認是否處理）
1. #14 與 D-35 的張力：#14「剛剛就是吃飽坐著的時候 → rest_symptom」與 D-35「吃飽後快速緩解（如打嗝後就好）不算 rest_symptom」在餐後情境方向相反；目前以較新的 #14 為準（CLINICAL_RULES §5.3 已註記），S-MID-13 兩個 arm 因此 T0（truth T3）。方向：偏急。出處：D-54 實作回報、本次付費閉環 S-MID-13。
2. 關鍵字開場白會把「沒有不舒服」抽成 symptom_character＝none（HEAD 也一樣）：S-MID-20 開場白加上真實胸部紅旗，走關鍵字路徑時胸部紅旗題不問，仍判 T4；LLM 開場白照規則 7 抽成 null 時會 Hard stop。方向：偏不急（只在關鍵字路徑）。出處：第四、五輪獨立驗收（t_hs.py）。
3. `third_party_call` 的關鍵字樣式缺「我姊姊」（樣式只有「姐姐」）、「我奶奶」等稱呼，這類來電不會被認成第三方，因此不問 Q-REACHABLE-01。方向：可能偏不急（病人不在旁邊時沒走第三方的處理）。出處：D-54 實作回報；本輪以關鍵字抽取器核對。
4. `chest_discomfort_mentioned` 可能誤觸：樣式「胸口／胸部／心口」後面不是否定詞就設旗標，例如「照胸部X光」也會設；性質未知時視為胸部症狀、多問胸部紅旗題。方向：只會偏急。出處：D-54 實作回報；本輪以關鍵字抽取器核對。
5. `reask_downgrades` 只把再問前的值放回最後狀態重算、不重跑對話；路徑分岔造成的差異記不到（例如 S-MID-04#0 的 T0 → T1）。方向：不改變分級本身；較不急的改變可能漏記（例如 S-MID-04#0 T0→T1），監測偏樂觀。出處：第三輪獨立驗收、CLINICAL_RULES §5.13-3。
6. L1：同一回合中，再問或複誦的回覆已會 Hard stop 時，本題的 D-50 複誦仍先做一次（N1 把回覆的順口值延到直接回答寫入後才寫），下一步才 Hard stop；違反 §5.10「寫入後即 Hard stop 者不複誦」。方向：不影響分級（Hard stop 晚一步）。出處：第五輪獨立驗收（t_n1.py F）；本次付費閉環沒有發生。

### 待 Clinical Owner 確認（與 D-54 同一份清單）
已裁定、不再列：Q-FREQ-01 新發答「有」→ T0（2026-11-02 裁定 #7）；vague 再問的排序（2026-11-03 依順序 D 裁定）。

1. 只提過胸口的不對稱：性質問不出來時新發今天保留 T0（vague 為 T9）；只提過胸口又答 none → 以已知值為準、可能 T4，開場白 vague 同答案則保留 vague。
2. Q-FREQ-01 的字句（DRAFT）。
3. 12 題上限取捨：Scripted 隨機格仍有 1,511 組全資訊 T0 卻掉級，全部停在上限。
4. L7：開場白說胸口沒事（性質 none）、之後順口說「胸口脹脹的」→ 以已知 none 為準、胸部紅旗題不問，T9（備援 T3）。
5. #12 與複誦：
   - gpt 是「讀成 none 後依 D-50 取較嚴重」；Gemma 是「讀成不明、保留原值」。
   - 只改 D-50 規則、讓明確否認可降回 none，修不到 Gemma，還要改複誦解讀（Gemma 要能把「不是喔，我是不會喘」讀成 none）。
   - 另一條路是重新考慮 #12。
6. 付費結果中的抽取問題（§5 第 2–10 項）：
   - rest_symptom：休息後緩解 ≠ 休息時發作；
   - episode_frequency_increased：這次在休息時發作 ≠ 次數變多；
   - consult_topic：打完疫苗手臂痠、空腹抽血；
   - dyspnea_grade：走路比平常喘一點；
   - antiplatelet_interrupted：忘記吃藥；
   - 時序：今天還沒發作；
   - threshold_decreased：比放支架前輕很多；
   - exertion_relation：「最近走路會有一點悶」沒抽成 exertion_only。這一項也可以改成「T0-NEW-TODAY 遇到 DV-4 候選時先問活動題」。
   
   凡要改提示者須在凍結前改。

## 2. 凍結狀態

- **尚未凍結**：開發集付費評估（11-03 _r2）已跑完；凍結前要先處理本報告的待 Clinical Owner 確認項（凡會改提示、抽取程式或規則者都要在凍結前改）。凍結：`python -m sim.closed_loop freeze`（寫到固定位置 reports/extractor_v2_freeze.json、只能寫一次），之後才跑保留集。
- 目前（最後一版開發集調整）prompts_version **2.0-dev24**；提示檔 sha256 `01b8fc0916654f3410af88daa0540c32716934cdc09dc3531186f3436e3ca430`；送出提示全文 sha256 `1cdd6738afa5346ce0d193e8f7403d7c93fcf42997b7c7f0a2e2328a3cf175e6`；`data/extractor_prompts_v2.yaml` `01b8fc0916654f34…`；`sim/llm_extract_v2.py` `a86fed9066a7e61a…`；`sim/runner.py` `be852a1c1ae2cfbf…`；`sim/closed_loop.py` `f40d5efd7ffde0e3…`；`sim/stt_synth_asr.py` `322699400c306c4d…`；`data/clinical_rules.yaml` `078619e0be4d016b…`；`data/question_bank_seed.yaml` `8704bb1302d92f28…`；`data/extraction_patterns.yaml` `814767506e5daa17…`；`data/scripts_zh.yaml` `8e174e1d94e29ed4…`；`data/llm_patient.yaml` `b8cf49b27b11c4b3…`；`sim/cases.py` `1a30cec0ddc079c7…`；`sim/patient.py` `02fbf781c886cabf…`；`sim/llm_patient.py` `553c398bf30bfab8…`；`sim/metrics.py` `f96f2aab64bd8d18…`；`sim/synth_eval.py` `f6727fc42a0ea0d1…`；`sim/synth_gen.py` `79ba62b92244bb9f…`；`sim/llm_extract.py` `01c4ddf74710fc6f…`；`src/acs_triage/decision/openai_adapter.py` `546881c53a0f3f88…`；`src/acs_triage/loaders.py` `140b58b580ee4c4f…`；`src/acs_triage/schemas.py` `35c215b94c526e53…`；`src/acs_triage/extract/__init__.py` `9dc74f58d081e08e…`；`src/acs_triage/extract/rule_extractor.py` `a9ce66b960a1acae…`；`src/acs_triage/pathway/__init__.py` `c96c56bb0ebb9f9a…`；`src/acs_triage/pathway/router.py` `00b95c0378267ec3…`；`src/acs_triage/prompter/__init__.py` `d1ade26107520064…`；`src/acs_triage/prompter/confirm.py` `9e03622387f9dd47…`；`src/acs_triage/prompter/prompter.py` `68e40c94aadf37fe…`；`src/acs_triage/rules/__init__.py` `0f8ec6e704c6b345…`；`src/acs_triage/rules/engine.py` `5f9f329c2ca5abff…`；`src/acs_triage/rules/redflags.py` `42b0b878db4914a3…`；`src/acs_triage/rules/state.py` `daa27eaa3f2f6549…`；`src/acs_triage/rules/sufficiency.py` `26e769a0b27afbdf…`；`src/acs_triage/rules/tiers.py` `a9ec1e1a2fb5f264…`；`data/synth/reference_synth_v1.json` `0228d3d4980f65e5…`；`data/synth/scenarios_synth_v1.yaml` `f949037d048d562e…`；`data/synth/synth_prompts.yaml` `841eeeacced8a4a6…`
- 保留集：**沒有執行任何保留集閉環、沒有看任何保留集抽取結果**（`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑）。

## 3. 階段 A：抽取器改進（開發集重放；調整過）

重放沿用 `sim.e2e_llm` 的指標（`run_cell`）：對話照 Opus 10-20 逐字稿固定、不補問；Hard-stop miss 含 premature。v1＝`reports/e2e_llm_extractors_2026-10-26.md`（回答句只抽被問那題；開場白 0.1）。v2 寫入方式：被問那題抽到值才寫入（未知不寫、保留原值）；順口提到的 slot 與閉環 runner 共用 `_write_mentions`：補未知的 slot，已知值只在紅旗是非題「有」或 confirm_back_severity 較嚴重時覆蓋，其他不同保留已知值（conflict）。閉環 runner 與此不同的一點：被問那題抽成未知時照既有 runner 寫入未知並標記已問（之後順口提到仍可補上）。

| 抽取器 | 文字 | 版本 | Hard-stop miss（含 premature） | premature | 假 Hard stop | under | over | exact | abstention FP | 紅旗題「有」漏抽 | 被問那題正確 | 紅旗題正確 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-6.1-sol | 逐字稿原文 | v1 | **4/27** | 1 | 1 | 0 | 0 | 86.6% | 16 | 0 | 632/646 | 346/346 |
| gpt-6.1-sol | 逐字稿原文 | v2 | **1/27** | 1 | 0 | 0 | 0 | 73.1% | 32 | 0 | 614/646 | 330/346 |
| gpt-6.1-sol | 電話語音＋Whisper | v1 | **5/27** | 1 | 1 | 0 | 2 | 83.2% | 18 | 0 | 631/646 | 344/346 |
| gpt-6.1-sol | 電話語音＋Whisper | v2 | **3/27** | 1 | 0 | 0 | 0 | 69.8% | 36 | 0 | 602/646 | 319/346 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | v1 | **4/27** | 1 | 21 | 0 | 14 | 66.4% | 21 | 0 | 531/646 | 299/346 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | v2 | **1/27** | 1 | 0 | 0 | 5 | 74.8% | 25 | 0 | 608/646 | 330/346 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | v1 | **6/27** | 2 | 30 | 0 | 20 | 63.0% | 17 | 0 | 512/646 | 282/346 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | v2 | **1/27** | 1 | 0 | 0 | 5 | 71.4% | 29 | 0 | 605/646 | 327/346 |

### 3.1 改善幅度（v2 − v1）

| 抽取器 | 文字 | Hard-stop miss | 假 Hard stop | over | abstention FP | exact |
|---|---|---|---|---|---|---|
| gpt-6.1-sol | 逐字稿原文 | -3 | -1 | +0 | +16 | -13.4 pt |
| gpt-6.1-sol | 電話語音＋Whisper | -2 | -1 | -2 | +18 | -13.4 pt |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | -3 | -21 | -9 | +4 | +8.4 pt |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | -5 | -30 | -15 | +12 | +8.4 pt |

### 3.2 Hard-stop miss 與假 Hard stop 明細（v2）

- gpt/ref：miss ['S-MID-10#0']；premature ['S-MID-10#0']；假 Hard stop （無）
- gpt/phone：miss ['S-INSUF-04#0', 'S-MID-06#0', 'S-MID-10#0']；premature ['S-MID-10#0']；假 Hard stop （無）
- gemma/ref：miss ['S-MID-10#0']；premature ['S-MID-10#0']；假 Hard stop （無）
- gemma/phone：miss ['S-MID-10#0']；premature ['S-MID-10#0']；假 Hard stop （無）

### 3.3 複誦回答的解讀（開發集 10-23 逐字稿的複誦回答＋人工探針）

題目原文與複誦句（`confirm_prompt`）一起當 context；正確答案＝逐字稿記下的確認值（10-23 的複誦全是「對」類回答）；探針 15 句含「不是，有啊」「不是。」等更正句（`sim/llm_extract_v2.py` CONFIRM_PROBES）。

| 抽取器 | 開發集複誦回答 | 探針 |
|---|---|---|
| gpt-6.1-sol | 163/164（{'correct': 162, 'speechless': 1, 'wrong': 1}） | 15/15 |
| gemma-4-26b-a4b-it-mlx | 161/164（{'correct': 160, 'wrong': 2, 'speechless': 1, 'invented': 1}） | 15/15 |

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
| 2.0-dev24 | D-54 第五輪：「裁定 #7 的說法」說明由送給模型的提示文字移到 YAML 註解（送出的例句不變）。 | 本報告：開發集付費閉環（gpt、Gemma）與階段 A 重放（gpt US$2.48；Gemma 本機，失敗 2 筆） |

### 3.5 延遲與費用（階段 A）

- gpt-6.1-sol：呼叫 1250、失敗 0；延遲中位數／p95：全部 2.90／10.73 s、開場白 12.19／16.21 s、回答 2.81／6.64 s（並行 8）；程式保護觸發 {'mention_redflag_denial_not_used': 107, 'choice_listed_unclassified': 1}（費用見 §6）
- gemma-4-26b-a4b-it-mlx：呼叫 1250、失敗 2；延遲中位數／p95：全部 1.45／7.37 s、開場白 7.90／9.65 s、回答 1.39／2.53 s（並行 1）；程式保護觸發 {'mention_redflag_denial_not_used': 59, 'denial_without_negated_evidence': 11, 'asked_value_from_mentions': 40, 'affirm_with_negated_evidence': 15, 'choice_listed_unclassified': 2, 'asked_stance_vs_leading_word': 4, 'ongoing_mention_without_present_marker': 4}（費用見 §6）

## 4. 階段 B：閉環模擬（Opus 病人 prompt 0.3、effort medium）

**階段 B：開發集閉環 2026-11-03 重跑完成（2.0-dev24、rules 0.9.0，種子為 11-03 _r2 逐字稿）；保留集閉環未執行、未凍結。** 結構化值 arm 自我檢查 119/119。

| 項目 | 估算（USD） | 依據 |
|---|---|---|
| 保留集 gpt arm Opus 病人 | ≈5.0 | 開發集 gpt arm 實際 US$2.88 × 保留集／開發集結構化值 eval 費用比 1.73（US$9.11／US$5.27） |
| 保留集 Gemma arm Opus 病人 | ≈3.3 | 開發集 Gemma arm 實際 US$1.92 × 1.73 |
| 保留集 gpt 抽取 | ≈2.7 | 開發集實際 US$1.98 × 1.35（同 10-27 的例數與呼叫數比） |
| 合計（只跑一次） | ≈11（估 8–14） | 凍結後執行 |

- Opus 病人評估（結構化值，付費）：開發集 _r2 HS 27/27、under 0、over 0、exact 100%，與 Scripted 相同。保留集三層（sim.synth_eval，參考一致子集 130 例）：(a) HS 51/51、under 14；(b) HS 49/51、under 26、平均 5.88 題；(c) 以 _r2 逐字稿重放，HS 49/51、under 25、exact 98/130（10-26 為 26、97）。

### 4.1 開發集 119 例（對 truth；提示依開發集調整過）

| arm | HS 敏感度 | HS miss（含 premature） | premature | 假 Hard stop | under | over | exact | T9 | 平均題數 | 複誦（每通） | 執行錯誤 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 結構化值（對照） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 0 | 100.0% | 12 | 5.91 | 165（1.39） | 0 |
| gpt-6.1-sol（2.0-dev24） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 95.0% | 16 | 6.16 | 192（1.61） | 0 |
| gemma-4-26b-a4b-it-mlx（2.0-dev24） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 7 | 89.9% | 15 | 6.24 | 201（1.69） | 0 |

under／over 不含 T9（T9 另計）；premature＝Hard stop 只靠抽錯的值成立（把當時已知的 slot 換回病人真正知道的事實後不再是 Hard stop），計為 miss。

- gpt-6.1-sol（2.0-dev24）：HS miss （無）；premature （無）；假 Hard stop （無）；under （無）；over [['S-MID-08', 3, 0], ['S-MID-13', 3, 0]]
- gemma-4-26b-a4b-it-mlx（2.0-dev24）：HS miss （無）；premature （無）；假 Hard stop （無）；under （無）；over [['S-ACUTE-05#1', 3, 0], ['S-MID-08', 3, 0], ['S-MID-08#2', 1, 0], ['S-MID-13', 3, 0], ['S-MID-17', 4, 3], ['S-MID-19', 1, 0], ['S-MID-20', 4, 3]]

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
| S-MID-01#2 | RF-06 | 3 | 3 | 3 | +0／+0 |
| S-MID-03#0 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-05#0 | RF-01 | 3 | 4 | 4 | +1／+1 |
| S-MID-06#0 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-10#0 | RF-01 | 5 | 5 | 5 | +0／+0 |
| S-MID-10#1 | RF-05 | 1 | 1 | 1 | +0／+0 |
| S-MID-11#0 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-11#1 | RF-04 | 2 | 2 | 2 | +0／+0 |
| S-MID-12#1 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-13#0 | RF-06 | 3 | 2 | 2 | -1／-1 |
| S-MID-13#1 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-14#1 | RF-06 | 4 | 4 | 4 | +0／+0 |
| S-MID-16#1 | RF-02 | 3 | 3 | 3 | +0／+0 |
| S-MID-17#1 | RF-03 | 4 | 4 | 4 | +0／+0 |
| S-MID-19#2 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-19#3 | RF-06 | 4 | 3 | 4 | -1／+0 |

### 4.1c 順口提到的值與已知值不同（conflict：保留已知值，最終版）

規則：順口提到的值補未知的 slot；D-50 範圍（紅旗題＋stt_critical_questions）的未知 slot 只收「寫入後變成 Hard stop」或最嚴重一級，其他較不嚴重的值：該題沒問過 → 不收（d50_not_most_severe）但暫存，之後直接問到、答案仍未知時以暫存值當解讀值 D-50 複誦一次；問過而目前未知 → 立刻對該題 D-50 複誦一次（以順口值當解讀值，計入複誦）；這兩種複誦在目前已是 Hard stop、或寫入該值（連同同一句的其他值）後會變 Hard stop 時都不做，直接寫入並走 Hard stop（D-50 不延誤送醫）；已知值只在三種情況被覆蓋——紅旗是非題的「有」、`confirm_back_severity` 已核定順序中較嚴重的值、寫入後由非 Hard stop 變成 Hard stop；其他不同一律保留已知值（conflict）。下列為全部沒採用的順口值。

- gpt-6.1-sol：順口值矛盾再問 2 次；因再問而最終較不急 0 次（只把再問前的值放回最後狀態重算、不重跑對話，路徑分岔造成的差異記不到；明細見閉環 JSON 的 reasks）
- gpt-6.1-sol：順口值觸發的複誦 0 次；沒採用 5 次（{'d50_not_most_severe': 1, 'conflict': 4}）：S-INSUF-02#0 第 1 題 Q-DYSPNEA-GRADE-01（d50_not_most_severe）：symptom_character 已知 None、順口 vague「喘的話其實都還好，我沒有在喘耶，主要是胸口那邊會不太舒服。」；S-MID-06#0 第 1 題 Q-DYSPNEA-GRADE-01（conflict）：rest_symptom 已知 False、順口 True「嗯…現在想一想，其實坐著休息的時候也會喘。」；S-MID-06#1 第 2 題 Q-ORTHO-01（conflict）：rest_symptom 已知 False、順口 True「會欸，躺平比較喘，要墊高枕頭才好睡，半夜也有喘醒過。」；S-MID-12#0 第 2 題 Q-ORTHO-01（conflict）：rest_symptom 已知 False、順口 True「會耶，躺平會比較喘，要墊高枕頭才睡得著，半夜有時候也會喘醒。」；S-MID-12#1 第 1 題 Q-DYSPNEA-GRADE-01（conflict）：rest_symptom 已知 False、順口 True「現在連坐著休息的時候也會喘。」
- gemma-4-26b-a4b-it-mlx：順口值矛盾再問 10 次；因再問而最終較不急 1 次（只把再問前的值放回最後狀態重算、不重跑對話，路徑分岔造成的差異記不到；明細見閉環 JSON 的 reasks）
- gemma-4-26b-a4b-it-mlx：順口值觸發的複誦 0 次；沒採用 14 次（{'conflict': 13, 'd50_not_most_severe': 1}）：S-ACUTE-01 第 5 題 Q-REST-02（conflict）：rest_symptom 已知 True、順口 False「我休息的時候都沒有發作過耶，都是快走的時候才會，停下來就好了。」；S-ACUTE-01#0 第 1 題 Q-ONGOING-01（conflict）：symptom_character 已知 pressure、順口 tightness「嗯，現在還是有，胸口還是覺得悶悶壓壓的。」；S-ACUTE-01#2 第 5 題 Q-REST-02（conflict）：rest_symptom 已知 True、順口 False「這個我不太清楚怎麼回答耶，我印象中坐著休息的時候好像沒有發作過。」；S-STABLE-01#0 第 6 題 Q-REST-02（conflict）：onset_new 已知 False、順口 True「對，休息的時候發作是最近才開始的，以前不會這樣。」；S-STABLE-03#0 第 4 題 Q-ONGOING-01（conflict）：symptom_character 已知 pressure、順口 vague「這個我不太確定耶，說不上來。」；S-STABLE-04 第 8 題 Q-REST-02（conflict）：rest_symptom 已知 True、順口 False「沒有喔，我休息的時候從來沒有發作過，都是走很快才會。」；S-STABLE-04#1 第 5 題 Q-REST-02（conflict）：rest_symptom 已知 True、順口 False「沒有欸，我坐著或躺著休息的時候從來沒有發作過，都是走路走快才會悶。」；S-INSUF-04 第 1 題 Q-DYSPNEA-GRADE-01（d50_not_most_severe）：symptom_character 已知 None、順口 vague「嗯…這個我也說不太上來耶，沒有特別注意是做什麼的時候會喘。」；S-INSUF-05#0 第 5 題 Q-REST-02（conflict）：rest_symptom 已知 True、順口 False「嗯…這個我不太確定耶，我印象中是走路的時候才會悶，休息的時候發作這個我說不上來。」；S-MID-08 第 6 題 Q-THRESH-TIME-01（conflict）：threshold_decreased 已知 True、順口 False「其實沒有變成比較輕的活動就會悶耶，跟之前差不多，所以這個我也講不出是什麼時候變的。」；S-MID-08 第 7 題 Q-REST-02（conflict）：rest_symptom 已知 True、順口 False「不是耶，我是說我休息的時候根本沒有發作過，都是走路才會悶，所以沒有「最近才開始」這回事。」；S-MID-08#0 第 6 題 Q-THRESH-TIME-01（conflict）：threshold_decreased 已知 True、順口 False「嗯…其實沒有變成比較輕的活動就會悶耶，跟之前差不多，所以這個我也說不上來是什麼時候。」；S-MID-08#1 第 6 題 Q-THRESH-TIME-01（conflict）：threshold_decreased 已知 True、順口 False「嗯…其實沒有變成比較輕的活動就會悶耶，所以這個我也說不上來是什麼時候變的。」；S-MID-08#2 第 6 題 Q-DYSPNEA-ACUTE-01（conflict）：rest_symptom 已知 True、順口 False「嗯…我其實沒有在喘耶，這個我不知道怎麼回答，我就只是走路會有點悶而已。」

觀察：Gemma 會把「休息後就好了」「坐著休息的時候就不會悶」順口抽成 rest_symptom＝有。有後續矛盾的 6 例由 #16 再問改回；沒有矛盾的 S-INSUF-05 落 T0。

### 4.2 保留集 150 例（對 LLM 參考標註；凍結後一次）

**未執行**（提示未凍結；`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑）。

### 4.3 閉環中的抽取（被問那題確認前的值 vs 病人模擬的結構化值）

| 資料 | arm | 被問那題 | 複誦回答 | 紅旗題「有」沒抽成「有」 | 病人呼叫：新／重用 | 抽取器費用 | 送進抽取器前被轉換的句子 |
|---|---|---|---|---|---|---|---|
| dev | gemma-4-26b-a4b-it-mlx（2.0-dev24） | {'correct': 701, 'invented': 6, 'wrong': 18, 'unknown_equiv': 7, 'speechless': 9, 'missed': 1} | {'correct': 177, 'missed': 17, 'speechless': 5, 'invented': 2} | 0 | 246／707（{'live_reused': 224, 'live': 246, 'seed': 483}） | US$0.0000 | 0 |
| dev | gpt-6.1-sol（2.0-dev24） | {'correct': 705, 'wrong': 11, 'unknown_equiv': 9, 'speechless': 8} | {'correct': 187, 'wrong': 2, 'speechless': 3} | 0 | 409／518（{'live': 409, 'seed': 518}） | US$1.9812 | 0 |

## 5. 模糊說法清單（交 Clinical Owner 裁定；v2 一律留未知、讓系統追問）

裁定表：`reports/extractor_v2_ambiguous_2026-11-03.md`／`.xlsx`（含開發集原句、可能的歸類、提示是否已寫入例句、留空的裁定欄）。表末兩列：第 15 列 Prompter 設計缺口（symptom_character 未知時當成沒有胸部症狀）；第 16 列設計取捨（病人直接回答較不急的值、又在別句順口說出較急的值時，目前保留直接回答、只記 conflict、不升級；開發集升級方向的 conflict 0 次，驗收者窮舉已知值衝突 669 組）。**凍結前須先裁定**：第 12 項「不太會喘 → none」已以例句寫進提示。

10-27 的 16 項已在 2026-11-02 裁定（D-54），本表不再列。下列是 11-03 開發集付費閉環與重放裡，**v2 已經抽錯或需要再問** 的說法（不是「留未知、讓系統追問」）。只用開發集（11-03 _r2 逐字稿的閉環、10-20 逐字稿的重放），沒有看任何保留集抽取結果。「v2 處理」是 2.0-dev24 的實際輸出，不代表已採用；以下都屬臨床歸類，本輪未改規則、題庫、提示或抽取程式。

| # | 說法 | 欄位 | 開發集出現處 | 關鍵詞抽取器（Phase 0）歸類 | v2 處理 | 待裁定 |
|---|---|---|---|---|---|---|
| 1 | 「我其實不太會喘」 | dyspnea_grade | 閉環 Q-DYSPNEA-GRADE-01 回答（gpt 20 句、Gemma 25 句含此說法） | （無值） | 依裁定 #12 抽成 exertional_heavy（gpt 11/20、Gemma 17/25）。複誦回覆「不是喔，我是不會喘」：gpt 9/11 讀成 none，D-50 取較嚴重仍留 heavy；Gemma 17/18 讀成不明，保留原值 | 事實沒有喘的病人因此加問呼吸題、到 12 題上限落 T9（備援 T1）：S-INSUF-01#1、S-INSUF-05#1（兩個 arm）、S-INSUF-02#1（Gemma）。只改 D-50 規則讓明確否認降回 none，修不到 Gemma（還要改複誦解讀）；或重新考慮 #12？ |
| 2 | 「坐著休息的時候就不會悶／休息完就好了」 | rest_symptom | 閉環 Q-ONGOING-01 回答（順口） | （無值） | Gemma 抽成 rest_symptom＝true（把休息緩解當成休息時發作）；gpt 未見 | S-INSUF-05 由 T9 變 T0（T0-REST-NEW）；S-MID-08 的「坐著休息的時候都還好」也被抽成 rest 有、沒改回；S-ACUTE-01#2 等 6 例由再問改回。要不要加反例「休息後緩解 ≠ 休息時發作」？ |
| 3 | 「以前只有運動才胸悶，今晚躺著看電視時也發作了」 | episode_frequency_increased | S-ACUTE-05 開場白（#0、#1 共用） | （無值；rest_symptom＝true） | Gemma 抽成 episode_frequency_increased＝true；gpt 未見 | S-ACUTE-05#1 由 T3 變 T0（T0-FREQ-INCREASED）。「這次休息時也發作」不是「次數變多」，要不要加反例？ |
| 4 | 「昨天打完流感疫苗手臂痠」 | consult_topic | S-MID-18 開場白 | minor_noncardiac | gpt 抽成 symptom（dev21 留 null） | S-MID-18 由 T4 變 T9（沒有 T4 路徑、7 題後沒有可問的題）。輕微非心臟不適要不要加 minor_noncardiac 例句？ |
| 5 | 「走路比平常喘一點」 | dyspnea_grade | S-MID-12 開場白 | exertional_daily | Gemma 抽成 exertional_heavy（dev21 抽對）；gpt 抽對 | S-MID-12 由 T2 變 T9：改走 T2-DYSPNEA-HEAVY，它的 sufficiency 要知道 pattern（≥6 個月改 T3，D-45），Q-PATTERN-01 答不知道、無題可問。是否受 #12 例句影響：未能確定。要不要加「走路就喘 → exertional_daily」例句？ |
| 6 | 「今天忘記吃早上的藥」 | antiplatelet_interrupted | S-MID-17 開場白 | （無值） | Gemma 抽成 true（10-27 相同） | S-MID-17 T4 → T3（抗血小板中斷無症狀）。沒說是哪種藥時要不要留 null？ |
| 7 | 「想問下次回診要不要空腹抽血」 | consult_topic | S-MID-20 開場白 | education_question | Gemma 抽成 appointment_admin（10-27 相同） | S-MID-20 T4 → T3（行政）。檢查前準備算衛教還是行政？ |
| 8 | 「前天開始…昨天含了一次舌下片…今天還沒發作」 | last_episode_timing | S-MID-19 開場白 | yesterday_within_24h | Gemma 抽成 today（10-27 重放也抽錯） | S-MID-19 由 T1 變 T0（T0-NEW-TODAY）。「今天還沒發作」要不要加反例？ |
| 9 | 「最近走路會有一點悶」 | exertion_relation | S-MID-08 開場白（#0–#2 共用） | exertion_only | gpt 不填（null）、Gemma 抽成 unclear | DV-4（PCI 後較輕）要 exertion_only，沒抽到就不適用 → T0-NEW-TODAY：S-MID-08（兩個 arm，10-27 起），S-MID-08#2（Gemma，另見下一項）。T0 定案前不會問 Q-EXERTION-01。要加「走路會悶 → exertion_only」例句，或 T0-NEW-TODAY 遇到 DV-4 候選時先問活動題？ |
| 10 | 「比放支架前輕很多，但以前是完全沒有」 | threshold_decreased | S-MID-08 開場白（#0–#2 共用） | （無值） | Gemma 抽成 threshold_decreased＝true（4 例都是；事實 false）；gpt 不填 | S-MID-08、#0、#1 由 #16 再問改回；S-MID-08#2 沒有後續矛盾、未改回 → T0-THRESHOLD-DAYS（加上 exertion unclear → T0，truth T1）。「比以前輕、以前沒有」不是閾值下降，要不要加反例？ |

## 6. 費用與耗時

- 合計（依 repo PRICES 估算，以帳單為準）：**US$38.04**＝有效 US$23.64＋作廢 US$14.39
- Anthropic（Opus 5.5 病人）有效：US$19.18＝開發集 eval _r2 US$5.27＋保留集 eval _r2 US$9.11＋閉環 gpt arm US$2.88（409 次新呼叫）＋閉環 Gemma arm US$1.92（246 次新呼叫）
- Anthropic 作廢（N1 修正前，不帶 _r2，hash 不符）：US$14.39＝開發集 US$5.27＋保留集 US$9.12
- OpenAI（gpt-6.1-sol 抽取）：US$4.46＝閉環 US$1.98＋階段 A 重放 US$2.48（1,250 次，失敗 0）
- Gemma（本機，不計費）：閉環 2026-11-03 23:25–11-04 00:01；重放 11-04 00:02–00:44（一次一句，1,250 次、失敗 2：LM Studio finish_reason=length）
- 閉環前兩次失敗：gpt 第一次缺 opencc、Gemma 兩次未載入模型（協調者紀錄 status.txt；日誌已被後來的執行覆蓋，費用以協調者紀錄為準）

## 7. 改動的檔案

- `data/extractor_prompts_v2.yaml`：2.0-dev21 → 2.0-dev24：D-54 裁定例句、新欄位、說明移到 YAML 註解
- `sim/llm_extract_v2.py`：chest_discomfort_mentioned 解析與 unclassified 胸口後備
- `sim/runner.py`：#16 矛盾再問、reask_downgrades 反事實、回覆的順口值寫入（H2、N1）、上限 12 全部計入
- `src/acs_triage/rules/、src/acs_triage/prompter/`：T0-FREQ-INCREASED、H3 gate、順序 D、活動題提前、vague 再問、旗標視為胸部症狀
- `sim/closed_loop.py、sim/run_llm_eval.py`：FROZEN_FILES 擴充、逐字稿版本與設定檢查、情境 hash；DEV_STRUCTURED／HOLDOUT_STRUCTURED 改指 11-03 _r2（協調者）
- `data/clinical_rules.yaml、data/question_bank_seed.yaml`：rules 0.9.0、題庫 0.5、max_questions 12、Q-FREQ-01（DRAFT）
- `reports/extractor_v2_2026-11-03_inputs/`：本報告輸入（重放合併、閉環輸出複本、凍結狀態、迭代、待確認說法、結論、費用）

## 8. 重現

```
PYTHONPATH=<本機 opencc>:src:. python -m sim.closed_loop run --set dev --arm structured|gpt|gemma --cache-dir <scratch>/closed1103/cache --out <scratch>/closed1103/out
python -m sim.llm_extract_v2 replay（gpt、Gemma 各一次，協調者在 scratchpad/replay1103 執行；輸出 v2_replay_gpt.json、v2_replay_gemma.json，合併成本目錄的 stage_a_replay.json）
python -m sim.extractor_v2_report --inputs reports/extractor_v2_2026-11-03_inputs --out reports
裁定表 md：上一步產生 reports/extractor_v2_ambiguous_2026-11-03.md 後，在開頭加上 reports/extractor_v2_2026-11-03_inputs/ambiguous_md_fix.md（cat fix md > tmp && mv tmp md）
```
