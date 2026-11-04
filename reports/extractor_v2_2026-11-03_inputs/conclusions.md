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
