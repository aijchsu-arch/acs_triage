# 抽取器 v2 與閉環模擬（D-52 第 3 項）— 2026-10-27

> **限制（先讀）**
>
> 1. **合成病人**：病人回答由 Opus 5.5 依情境事實（hidden sheet）生成，句子比真實病人完整、少答非所問；正確答案＝情境事實（開發集為單一裁定者 truth）。這是一致性檢查，不是準確度，不能外推臨床表現。
> 2. **合成語音或沒有語音**：階段 A 的 phone 條件是 macOS `say` 合成標準國語＋模擬電話線路＋本機 Whisper（D-49），沒有台語、高齡口音與環境噪音，是樂觀上限；階段 B 閉環完全沒有語音（病人文字直接進抽取器），等於 STT 完美。
> 3. **LLM 參考標註**：保留集的「對照答案」是 Opus 5.5 與 gpt-6.1-sol 的獨立標註（暫定；Clinical Owner 尚在裁定 48 例），不是 truth；主分析用兩位標註者一致的子集。
> 4. **雲端模型不可用於真實資料**：gpt-6.1-sol 只是「抽取能力上限」參考；真實病人資料不得送外部 API（D-10）。院內可部署的候選是本機模型（Gemma）。全部資料為合成資料。
> 5. **病人回答重用（配對設計）**：閉環的病人以「對話前綴快取」包一層：同一 case、同一串客服問句（含複誦句）就重用已取得的 Opus 回答，種子是結構化值閉環的逐字稿（開發集 10-23、保留集 10-26），gpt 與 Gemma 兩個 arm 共用。問句序列相同時病人看到的對話完全相同，重用的是同一個樣本（三個 arm 之間是配對比較，不是獨立重抽）；序列一分岔，之後都是新的 API 呼叫。
> 6. **開發集調整過；保留集尚未執行**：抽取提示只依開發集逐字稿調整（迭代紀錄見 §3.4），本報告的數字全部來自開發集，因此偏樂觀；提示尚未凍結，保留集（data/synth/）沒有執行、也沒有看任何保留集抽取結果。

## 1. 結論（人工撰寫，依本報告數字）

1. **開發集閉環（119 例；結構化值閉環對照：HS 27/27、under 0、over 0、exact 100%、T9 12、5.60 題、複誦 164）**。最終版 2.0-dev21（dev16 實跑；dev17–dev21 程式只用快取重算，逐例相同）：
   - gpt：HS **27/27**、HS miss 0（premature 0）、假 Hard stop 0、under **0**、over 2、exact 97.5%、T9 13、5.74 題、複誦 186（每通 1.56）。
   - Gemma：HS **27/27**、HS miss 0、假 Hard stop 0、under **0**、over 3、exact 92.4%、T9 18、6.03 題、複誦 197（每通 1.66）。
   - 閉環中被問那題的抽取（確認前 vs 結構化值）：gpt 正確 664＋說不上來 6＋不知道互換 12、漏 1；Gemma 687＋5＋20、漏 6；紅旗題「有」沒抽成「有」兩者 0；複誦回答 gpt 185＋1、Gemma 194＋3。
2. **第一次閉環（2.0-dev15）抓到一個重放看不到的 under-triage**：病人回答「現在還在嗎」時說「現在沒有，胸口目前不會悶」，抽取器把它當成順口提到 symptom_character＝none，蓋掉開場白的「悶」→ Prompter 認為沒有胸部症狀，休息時發作、冒汗等題不再問。gpt 4 例 T0→T3（S-STABLE-01#0、-02#1、-04#0、-04#1）＋漏 S-MID-14#1 的 RF-06；Gemma 1 例 under＋漏 S-MID-10#0 的 RF-01（「我不會喘」被抽成 none）。依指示只在開發集修正一次（2.0-dev16，程式；送出的提示全文 sha256 不變）：回答句順口提到的紅旗否認不採用（紅旗題一律直接問、照 D-50 複誦）。之後依四輪獨立驗收改寫順口值的寫入規則（2.0-dev17–dev20）：補未知的 slot（含問過但答不知道的）；D-50 範圍（紅旗題＋stt_critical_questions）的未知 slot 只收「寫入後變成 Hard stop」或最嚴重一級，其他較不嚴重的值沒問過就先暫存（直接問到仍未知時以它複誦）、問過就立刻對該題複誦一次（開發集皆 0 次）；已知值只在紅旗是非題「有」、confirm_back_severity 較嚴重、或寫入後由非 Hard stop 變成 Hard stop 時覆蓋，其他不同保留已知值、記為 conflict（gpt 1 次、Gemma 3 次，§4.1c）。修正後兩者 HS 27/27、under 0。這個修正只在開發集驗證過。
3. **「留未知讓系統追問」在閉環救回的開場白漏判**（重放中都是 Hard-stop miss）：S-INSUF-07#0（胸口不太舒服）、S-MID-13#0、S-MID-13#1（胸口脹脹的），兩個抽取器都在 Q-CHARACTER-01 問到性質後觸發 Hard stop；S-MID-14#1（胸口肌肉按下去會痛）Gemma 也是這樣救回。代價是 Hard stop 比結構化值晚 1–3 題；S-MID-05#0（變體把性質設回未知）兩者也晚 1 題。逐例題次見 §4.1b。
4. **閉環剩下的差異都是偏急或轉護理師**：gpt over 2（S-MID-08、S-MID-13 T3→T0）；Gemma over 3（另有 S-MID-17、S-MID-20 T4→T3）、T9 多 6 例——其中 4 例是 Gemma 把 Q-ANTIPLT-01「沒有，都有照時間吃」抽成「有」，被句首規則改成未知，gate 一直缺這題，問到 11 題上限。Gemma 的是非題極性仍是院內上線前要解決的問題。
5. **階段 A（重放）**：v2 修好 Gemma 的「沒有→有」——假 Hard stop 21→0（逐字稿）、30→0（電話＋Whisper），over 14→3、20→3，被問那題正確 531→618／646。重放的 Hard-stop miss 沒有下降（gpt 4→4、5→6；Gemma 4→5、6→6），原因是留未知的 case 重放不會追問（上面第 3 點在閉環救回）；S-MID-10#0 在重放算 premature，閉環中兩者都在第 5 題觸發、與結構化值相同。複誦回答解讀：開發集 164 句 gpt 163＋1、Gemma 164/164，15 句探針兩者 15/15。
6. **保留集未執行、提示未凍結**：要等 Clinical Owner 裁定（裁定表 `reports/extractor_v2_ambiguous_2026-10-27.*`：14 項模糊說法，第 12 項「不太會喘 → none」已以例句寫進提示；第 15 列 Prompter 設計缺口；第 16 列設計取捨——直接回答較不急、又順口說較急時保留直接回答、只記 conflict）後再凍結；凍結與保留集防護已加強（§4）。依開發集實際用量重新估價：保留集全量（gpt＋Gemma＋免費的 structured）約 **US$10**（估 8–14；只跑 Gemma 約 US$6）。整體上限 US$25 已用 US$9.70。
7. **給 Clinical Owner 的設計缺口（未修改）**：symptom_character 未知或被否認時，Prompter 視為沒有胸部症狀，胸部紅旗題不問或延後。第 2 點的 under-triage 就是從這裡漏出去；v2 已在抽取端擋住，但規則與 Prompter 本身沒有保護。待裁定（模糊說法清單第 4、5 項）。

## 2. 凍結狀態

- **尚未凍結**：未凍結：依獨立驗收，要等 Clinical Owner 裁定模糊說法（reports/extractor_v2_ambiguous_2026-10-27.*；第 12 項已以例句寫進提示）後才凍結。凍結：`python -m sim.closed_loop freeze`（寫到固定位置 reports/extractor_v2_freeze.json、只能寫一次），之後才跑保留集。
- 目前（最後一版開發集調整）prompts_version **2.0-dev21**；提示檔 sha256 `1e3ce7887dbb1152e23b914e5e9557bcb9dd19d9c322b0a1cf811ddb60f17d27`；送出提示全文 sha256 `7357783d6e1318dd669038ec907f9bc62d23659b2ace74ae075052a81c400518`；`data/extractor_prompts_v2.yaml` `1e3ce7887dbb1152…`；`sim/llm_extract_v2.py` `26143627d3bbb754…`；`sim/runner.py` `4e8023b2ed661520…`；`sim/closed_loop.py` `6acca795aa4df3a4…`；`sim/stt_synth_asr.py` `322699400c306c4d…`
- 保留集：**沒有執行任何保留集閉環、沒有看任何保留集抽取結果**（`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑）。

## 3. 階段 A：抽取器改進（開發集重放；調整過）

重放沿用 `sim.e2e_llm` 的指標（`run_cell`）：對話照 Opus 10-20 逐字稿固定、不補問；Hard-stop miss 含 premature。v1＝`reports/e2e_llm_extractors_2026-10-26.md`（回答句只抽被問那題；開場白 0.1）。v2 寫入方式：被問那題抽到值才寫入（未知不寫、保留原值）；順口提到的 slot 與閉環 runner 共用 `_write_mentions`：補未知的 slot，已知值只在紅旗是非題「有」或 confirm_back_severity 較嚴重時覆蓋，其他不同保留已知值（conflict）。閉環 runner 與此不同的一點：被問那題抽成未知時照既有 runner 寫入未知並標記已問（之後順口提到仍可補上）。

| 抽取器 | 文字 | 版本 | Hard-stop miss（含 premature） | premature | 假 Hard stop | under | over | exact | abstention FP | 紅旗題「有」漏抽 | 被問那題正確 | 紅旗題正確 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-6.1-sol | 逐字稿原文 | v1 | **4/27** | 1 | 1 | 0 | 0 | 86.6% | 16 | 0 | 632/646 | 346/346 |
| gpt-6.1-sol | 逐字稿原文 | v2 | **4/27** | 1 | 0 | 0 | 0 | 79.8% | 24 | 0 | 631/646 | 346/346 |
| gpt-6.1-sol | 電話語音＋Whisper | v1 | **5/27** | 1 | 1 | 0 | 2 | 83.2% | 18 | 0 | 631/646 | 344/346 |
| gpt-6.1-sol | 電話語音＋Whisper | v2 | **6/27** | 1 | 0 | 0 | 0 | 74.8% | 30 | 0 | 618/646 | 335/346 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | v1 | **4/27** | 1 | 21 | 0 | 14 | 66.4% | 21 | 0 | 531/646 | 299/346 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | v2 | **5/27** | 1 | 0 | 0 | 3 | 75.6% | 26 | 0 | 618/646 | 345/346 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | v1 | **6/27** | 2 | 30 | 0 | 20 | 63.0% | 17 | 0 | 512/646 | 282/346 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | v2 | **6/27** | 1 | 0 | 0 | 3 | 69.8% | 33 | 2 | 603/646 | 338/346 |

### 3.1 改善幅度（v2 − v1）

| 抽取器 | 文字 | Hard-stop miss | 假 Hard stop | over | abstention FP | exact |
|---|---|---|---|---|---|---|
| gpt-6.1-sol | 逐字稿原文 | +0 | -1 | +0 | +8 | -6.7 pt |
| gpt-6.1-sol | 電話語音＋Whisper | +1 | -1 | -2 | +12 | -8.4 pt |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | +1 | -21 | -11 | +5 | +9.2 pt |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper | +0 | -30 | -17 | +16 | +6.7 pt |

### 3.2 Hard-stop miss 與假 Hard stop 明細（v2）

- gpt/ref：miss ['S-INSUF-07#0', 'S-MID-10#0', 'S-MID-13#0', 'S-MID-13#1']；premature ['S-MID-10#0']；假 Hard stop （無）
- gpt/phone：miss ['S-INSUF-04#0', 'S-INSUF-07#0', 'S-MID-06#0', 'S-MID-10#0', 'S-MID-13#0', 'S-MID-13#1']；premature ['S-MID-10#0']；假 Hard stop （無）
- gemma/ref：miss ['S-INSUF-07#0', 'S-MID-10#0', 'S-MID-13#0', 'S-MID-13#1', 'S-MID-14#1']；premature ['S-MID-10#0']；假 Hard stop （無）
- gemma/phone：miss ['S-ACUTE-02#1', 'S-INSUF-07#0', 'S-MID-10#0', 'S-MID-13#0', 'S-MID-13#1', 'S-MID-14#1']；premature ['S-MID-10#0']；假 Hard stop （無）

### 3.3 複誦回答的解讀（開發集 10-23 逐字稿的複誦回答＋人工探針）

題目原文與複誦句（`confirm_prompt`）一起當 context；正確答案＝逐字稿記下的確認值（10-23 的複誦全是「對」類回答）；探針 15 句含「不是，有啊」「不是。」等更正句（`sim/llm_extract_v2.py` CONFIRM_PROBES）。

| 抽取器 | 開發集複誦回答 | 探針 |
|---|---|---|
| gpt-6.1-sol | 164/164（{'correct': 163, 'speechless': 1}） | 15/15 |
| gemma-4-26b-a4b-it-mlx | 164/164（{'correct': 164}） | 15/15 |

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

### 3.5 延遲與費用（階段 A）

- gpt-6.1-sol：呼叫 1250、失敗 0；延遲中位數／p95：全部 2.51／9.32 s、開場白 11.14／15.43 s、回答 2.44／5.63 s（並行 8）；程式保護觸發 {'mention_redflag_denial_not_used': 120}（費用見 §6）
- gemma-4-26b-a4b-it-mlx：呼叫 1250、失敗 0；延遲中位數／p95：全部 1.23／6.80 s、開場白 7.19／9.28 s、回答 1.20／2.13 s（並行 1）；程式保護觸發 {'ongoing_mention_without_present_marker': 11, 'mention_redflag_denial_not_used': 50, 'asked_stance_vs_leading_word': 10, 'denial_without_negated_evidence': 7, 'asked_value_from_mentions': 11, 'choice_listed_unclassified': 1, 'affirm_with_negated_evidence': 3}（費用見 §6）

## 4. 階段 B：閉環模擬（Opus 病人 prompt 0.3、effort medium）

**階段 B：開發集閉環已完成（指揮官 2026-10-27 核准，上限 US$15，實際 US$7.03）；保留集未執行、未凍結。** 先以 2.0-dev15 跑 gpt 與 Gemma 各 119 例，發現 under-triage（見下），依指示只在開發集做一次修正（2.0-dev16，程式；送出的提示全文不變），再重跑兩個 arm（病人前綴快取讓重跑只需 84 次新的 Opus 呼叫）。之後依五輪獨立驗收再修寫入規則與保留集防護（2.0-dev17–dev21），只用快取重算、0 次 API，數字不變。§4.1 列修正前與最終版。

| 項目 | 估算（USD） | 依據 |
|---|---|---|
| 保留集 150 例，第一個 arm（gpt）Opus 病人 | ≈5.9 | 開發集第一個 arm 實際 US$3.42 × 保留集／開發集結構化值閉環的費用比 1.73（US$8.77／US$5.07） |
| 保留集，第二個 arm（Gemma）Opus 病人 | ≈3.3 | 開發集第二個 arm 實際 US$1.91（289 次新呼叫，627 次重用）× 1.73 |
| 保留集 gpt 抽取 | ≈1.1 | 開發集第一輪實際 US$0.84 × 1.35（150／119 例 × 每例呼叫數 7.46／6.97） |
| 保留集 structured arm（對照） | 0 | 只用 10-26 逐字稿當快取 |
| 合計（只跑一次、不再修正） | ≈10.3（估 8–14） | 整體上限 US$25 已用 US$9.70，剩 US$15.3；只跑 Gemma 約 US$6 |

- 修正前（2.0-dev15）的問題：回答句順口提到的「現在沒有，胸口目前不會悶」「我不會喘」被抽成 symptom_character＝none，蓋掉開場白的性質 → Prompter 視為沒有胸部症狀，冒汗、休息時發作等題不再問。gpt：S-STABLE-01#0、S-STABLE-02#1、S-STABLE-04#0、S-STABLE-04#1 由 T0 判成 T3（under），S-MID-14#1 漏掉 RF-06；Gemma：S-STABLE-01#0 under，S-MID-10#0 漏掉 RF-01。
- 修正（2.0-dev16→dev21）：回答句順口提到的紅旗欄位否認（含 symptom_character＝none）不採用；順口值補未知的 slot——D-50 範圍（紅旗題＋stt_critical_questions）的未知 slot 只收「寫入後變成 Hard stop」或最嚴重一級，其他較不嚴重的值：該題沒問過就先不收但暫存，直接問到仍未知時以暫存值複誦一次；問過而目前未知就立刻對該題複誦一次（以順口值當解讀值）；這兩種複誦在目前已是 Hard stop、或寫入該值（連同同一句的其他值）後會變 Hard stop 時都不做，直接寫入並走 Hard stop（D-50 不延誤送醫）；已知值只在紅旗是非題「有」、confirm_back_severity 較嚴重、或寫入後變成 Hard stop 時覆蓋，其他不同保留已知值並記為 conflict（§4.1c）。dev17–dev21 都只用快取重算，數字與 dev16 逐例相同。
- 「留未知讓系統追問」在閉環救回的開場白漏判（重放中是 Hard-stop miss；gpt 與 Gemma 結果相同）：S-INSUF-07#0 家屬說「胸口不太舒服」→ 第 3 題 Q-CHARACTER-01 答「講不太上來、怪怪的」（vague）→ 第 4 題 Q-ONGOING-01「還在」→ RF-03（結構化值第 1 題）；S-MID-13#0「胸口脹脹的」→ 第 2 題 Q-CHARACTER-01 答「上腹悶悶脹脹」（epigastric）→ 第 4 題 Q-DIAPH-01「有冒冷汗」→ RF-06（結構化值第 3 題）；S-MID-13#1 同一開場白 → Q-CHARACTER-01 → 第 3 題 Q-ONGOING-01「還有一點不舒服」→ RF-03（結構化值第 1 題）；S-MID-14#1（只有 Gemma 開場白沒歸類「胸口肌肉按下去會痛」）→ 第 2 題 Q-CHARACTER-01 答「會痛」（pain）→ 第 5 題 Q-DIAPH-01 → RF-06（結構化值第 4 題；gpt 開場白已抽 pain，第 4 題）。代價是 Hard stop 晚 1–3 題；另 S-MID-05#0（開場白「沒有胸悶」、變體把性質設回未知）兩個 arm 都比結構化值晚 1 題（第 4 vs 3 題）。逐例題次見 §4.1b。
- 重放裡算 premature 的 S-MID-10#0，閉環中兩個抽取器都在第 5 題（與結構化值相同）以 RF-01 觸發。
- 其餘與結構化值不同的 case（2.0-dev16）：gpt over 2（S-MID-08、S-MID-13 由 T3 判成 T0：前者開場白沒抽到「走路才悶」、Q-TIMING-01 答不記得；後者 Q-EXERTION-01 回答「是休息的時候…吃飽坐著」被抽成 rest_symptom＝true，屬模糊說法第 14 項）、T9 1（S-MID-15#0 題數上限）；Gemma over 3（S-MID-08；S-MID-17、S-MID-20 由 T4 判成 T3：開場白 consult_topic 歸成門診事務）、T9 6（S-STABLE-01、S-MID-02、S-MID-13、S-MID-15#0、S-MID-16、S-MID-19，都是問到 11 題上限；其中 4 例是 Q-ANTIPLT-01「沒有，都有照時間吃」被 Gemma 抽成「有」→ 句首規則改成未知 → gate 一直缺這題，另 2 例是 Q-TIMING-01「記不太清楚」沒抽成 unknown、或題數不夠）。
- 繼續保留集的步驟（Clinical Owner 裁定模糊說法、必要時改提示之後）：`sim.closed_loop freeze`（固定位置、只寫一次）→ `run --set holdout --arm structured`→ `--arm gpt` → `--arm gemma`。三個 arm 都要求凍結紀錄存在、全部凍結檔（提示、抽取器、runner、closed_loop、stt_synth_asr）與提示全文 sha256 相符、不得 --limit；前置檢查（金鑰、opencc、LM Studio 連線與模型已載入、輸入檔、凍結 hash）全部通過後才登記到 reports/extractor_v2_holdout_runs.json，同一 arm 已登記或 --out 已有輸出就拒跑。

### 4.1 開發集 119 例（對 truth；提示依開發集調整過）

| arm | HS 敏感度 | HS miss（含 premature） | premature | 假 Hard stop | under | over | exact | T9 | 平均題數 | 複誦（每通） | 執行錯誤 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 結構化值（對照） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 0 | 100.0% | 12 | 5.60 | 164（1.38） | 0 |
| gpt-6.1-sol（2.0-dev15，修正前） | 26/27（96.3%） | 1 | 0 | 0 | 4 | 2 | 89.9% | 18 | 5.61 | 185（1.55） | 0 |
| gemma-4-26b-a4b-it-mlx（2.0-dev15，修正前） | 26/27（96.3%） | 1 | 0 | 0 | 1 | 3 | 91.6% | 18 | 6.05 | 196（1.65） | 0 |
| gpt-6.1-sol（2.0-dev16 執行；2.0-dev21 快取重算逐例相同） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 2 | 97.5% | 13 | 5.74 | 186（1.56） | 0 |
| gemma-4-26b-a4b-it-mlx（2.0-dev16 執行；2.0-dev21 快取重算逐例相同） | 27/27（100.0%） | 0 | 0 | 0 | 0 | 3 | 92.4% | 18 | 6.03 | 197（1.66） | 0 |

under／over 不含 T9（T9 另計）；premature＝Hard stop 只靠抽錯的值成立（把當時已知的 slot 換回病人真正知道的事實後不再是 Hard stop），計為 miss。

- gpt-6.1-sol（2.0-dev15，修正前）：HS miss ['S-MID-14#1']；premature （無）；假 Hard stop （無）；under [['S-STABLE-01#0', 0, 3], ['S-STABLE-02#1', 0, 3], ['S-STABLE-04#0', 0, 3], ['S-STABLE-04#1', 0, 3]]；over [['S-MID-08', 3, 0], ['S-MID-13', 3, 0]]
- gemma-4-26b-a4b-it-mlx（2.0-dev15，修正前）：HS miss ['S-MID-10#0']；premature （無）；假 Hard stop （無）；under [['S-STABLE-01#0', 0, 3]]；over [['S-MID-08', 3, 0], ['S-MID-17', 4, 3], ['S-MID-20', 4, 3]]
- gpt-6.1-sol（2.0-dev16 執行；2.0-dev21 快取重算逐例相同）：HS miss （無）；premature （無）；假 Hard stop （無）；under （無）；over [['S-MID-08', 3, 0], ['S-MID-13', 3, 0]]
- gemma-4-26b-a4b-it-mlx（2.0-dev16 執行；2.0-dev21 快取重算逐例相同）：HS miss （無）；premature （無）；假 Hard stop （無）；under （無）；over [['S-MID-08', 3, 0], ['S-MID-17', 4, 3], ['S-MID-20', 4, 3]]

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
| S-INSUF-07#0 | RF-03 | 1 | 4 | 4 | +3／+3 |
| S-MID-01#2 | RF-06 | 3 | 3 | 3 | +0／+0 |
| S-MID-03#0 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-05#0 | RF-01 | 3 | 4 | 4 | +1／+1 |
| S-MID-06#0 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-10#0 | RF-01 | 5 | 5 | 5 | +0／+0 |
| S-MID-10#1 | RF-05 | 1 | 1 | 1 | +0／+0 |
| S-MID-11#0 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-11#1 | RF-04 | 2 | 2 | 2 | +0／+0 |
| S-MID-12#1 | RF-02 | 1 | 1 | 1 | +0／+0 |
| S-MID-13#0 | RF-06 | 3 | 4 | 4 | +1／+1 |
| S-MID-13#1 | RF-03 | 1 | 3 | 3 | +2／+2 |
| S-MID-14#1 | RF-06 | 4 | 4 | 5 | +0／+1 |
| S-MID-16#1 | RF-02 | 3 | 3 | 3 | +0／+0 |
| S-MID-17#1 | RF-03 | 4 | 4 | 4 | +0／+0 |
| S-MID-19#2 | RF-03 | 1 | 1 | 1 | +0／+0 |
| S-MID-19#3 | RF-06 | 4 | 3 | 4 | -1／+0 |

### 4.1c 順口提到的值與已知值不同（conflict：保留已知值，最終版）

規則：順口提到的值補未知的 slot；D-50 範圍（紅旗題＋stt_critical_questions）的未知 slot 只收「寫入後變成 Hard stop」或最嚴重一級，其他較不嚴重的值：該題沒問過 → 不收（d50_not_most_severe）但暫存，之後直接問到、答案仍未知時以暫存值當解讀值 D-50 複誦一次；問過而目前未知 → 立刻對該題 D-50 複誦一次（以順口值當解讀值，計入複誦）；這兩種複誦在目前已是 Hard stop、或寫入該值（連同同一句的其他值）後會變 Hard stop 時都不做，直接寫入並走 Hard stop（D-50 不延誤送醫）；已知值只在三種情況被覆蓋——紅旗是非題的「有」、`confirm_back_severity` 已核定順序中較嚴重的值、寫入後由非 Hard stop 變成 Hard stop；其他不同一律保留已知值（conflict）。下列為全部沒採用的順口值。

- gpt-6.1-sol：順口值觸發的複誦 0 次；沒採用 1 次（{'conflict': 1}）：S-MID-06#2 第 1 題 Q-DYSPNEA-SENTENCE-01（conflict）：dyspnea_complaint 已知 True、順口 False「不會啦，講話還好，一句話可以講完，不會喘。」
- gemma-4-26b-a4b-it-mlx：順口值觸發的複誦 0 次；沒採用 3 次（{'conflict': 3}）：S-ACUTE-05 第 6 題 Q-REST-02（conflict）：threshold_decreased 已知 True、順口 False「對，休息的時候發作是最近才開始的，以前都只有運動才會。」；S-MID-11 第 5 題 Q-REST-02（conflict）：rest_symptom 已知 True、順口 False「這個我不太確定怎麼回答欸，我平常坐著休息好像不會喘，這個不太清楚。」；S-MID-11 第 5 題 Q-REST-02（conflict）：dyspnea_complaint 已知 True、順口 False「這個我不太確定怎麼回答欸，我平常坐著休息好像不會喘，這個不太清楚。」

觀察：選擇題（如 dyspnea_grade）用暫存值複誦時，若複誦回答聽不清，依 D-50「選擇題保留原值」會採用順口值；驗收者第三種注入情境 4/578 組比「該題未知」不急（T9 備援 T1→T2／T3），結果等於真實值與全部收下，與直接回答時的 D-50 規則一致。

### 4.2 保留集 150 例（對 LLM 參考標註；凍結後一次）

**未執行**（提示未凍結；`sim.closed_loop run --set holdout` 沒有凍結紀錄會拒跑）。

### 4.3 閉環中的抽取（被問那題確認前的值 vs 病人模擬的結構化值）

| 資料 | arm | 被問那題 | 複誦回答 | 紅旗題「有」沒抽成「有」 | 病人呼叫：新／重用 | 抽取器費用 | 送進抽取器前被轉換的句子 |
|---|---|---|---|---|---|---|---|
| dev | gemma-4-26b-a4b-it-mlx（2.0-dev15，修正前） | {'correct': 690, 'unknown_equiv': 21, 'speechless': 5, 'missed': 4} | {'correct': 193, 'speechless': 3} | 0 | 289／627（{'live_reused': 216, 'seed': 411, 'live': 289}） | US$0.0000 | 0 |
| dev | gemma-4-26b-a4b-it-mlx（2.0-dev16 執行；2.0-dev21 快取重算逐例相同） | {'correct': 687, 'unknown_equiv': 20, 'missed': 6, 'speechless': 5} | {'correct': 194, 'speechless': 3} | 0 | 29／886（{'live_reused': 416, 'seed': 470, 'live': 29}） | US$0.0000 | 0 |
| dev | gpt-6.1-sol（2.0-dev15，修正前） | {'correct': 652, 'unknown_equiv': 8, 'speechless': 4, 'missed': 3} | {'correct': 184, 'speechless': 1} | 0 | 213／639（{'live_reused': 302, 'seed': 337, 'live': 213}） | US$0.3370 | 0 |
| dev | gpt-6.1-sol（2.0-dev16 執行；2.0-dev21 快取重算逐例相同） | {'correct': 664, 'unknown_equiv': 12, 'speechless': 6, 'missed': 1} | {'correct': 185, 'speechless': 1} | 0 | 55／814（{'live_reused': 316, 'live': 55, 'seed': 498}） | US$0.1901 | 0 |

## 5. 模糊說法清單（交 Clinical Owner 裁定；v2 一律留未知、讓系統追問）

裁定表：`reports/extractor_v2_ambiguous_2026-10-27.md`／`.xlsx`（含開發集原句、可能的歸類、提示是否已寫入例句、留空的裁定欄）。表末兩列：第 15 列 Prompter 設計缺口（symptom_character 未知時當成沒有胸部症狀）；第 16 列設計取捨（病人直接回答較不急的值、又在別句順口說出較急的值時，目前保留直接回答、只記 conflict、不升級；開發集升級方向的 conflict 0 次，驗收者窮舉已知值衝突 669 組）。**凍結前須先裁定**：第 12 項「不太會喘 → none」已以例句寫進提示。

來源：只用開發集（10-20／10-23 Opus 逐字稿與 10-20 的 Whisper 轉寫）；抽取器 v2 的 unclassified 輸出＋人工檢視開發集中描述症狀性質、喘的程度與時序的說法。v2 對這些說法不自行歸類（不填值、寫進 unclassified，由系統追問 Q-CHARACTER-01 等）；「v2 處理」欄是兩個模型在階段 A 重放（第 14 項為開發集閉環）中的實際輸出，供裁定參考，不代表已採用。以下皆屬臨床歸類，未修改規則、題庫或抽取詞表。

| # | 說法 | 欄位 | 開發集出現處 | 關鍵詞抽取器（Phase 0）歸類 | v2 處理 | 待裁定 |
|---|---|---|---|---|---|---|
| 1 | 「胸口脹脹的」 | symptom_character | S-MID-13 開場白（S-MID-13、#0–#3 共用） | epigastric | gpt、Gemma 皆不填，列入 unclassified | 歸 tightness、epigastric、vague，或維持追問？（v1 gpt 抽成 other → RF 永遠不成立） |
| 2 | 「悶悶脹脹的」 | symptom_character | S-MID-13#3 Q-DIAPH-01 回答 | epigastric | gpt、Gemma 皆抽成 tightness（依「悶」） | 「悶」與「脹」並存時歸哪一類？ |
| 3 | 「肚子上面悶脹」 | symptom_character | S-MID-13#3 Q-DYSPNEA-GRADE-01 回答 | tightness | gpt、Gemma 皆抽成 epigastric（對應選項「上腹悶脹」） | 「肚子上面」是否等同上腹（epigastric，屬缺血等價）？ |
| 4 | 「胸口不太舒服（沒有描述性質）」 | symptom_character | S-INSUF-06、S-INSUF-07 開場白 | vague（算胸部症狀） | gpt、Gemma 皆不填（gpt 列入 unclassified） | 未描述性質的「胸口不舒服」可否直接視為胸部症狀（vague）？注意：symptom_character 未知時 Prompter 視為沒有胸部症狀，胸部紅旗題要等 Q-CHARACTER-01 答完才問。 |
| 5 | 「胸口怪怪的（沒說「說不上來」）」 | symptom_character | S-INSUF-01 開場白；S-INSUF-07#0 Q-ONGOING-01 回答 | vague | gpt、Gemma 皆不填（列入 unclassified） | 同上；「怪怪的」是否等同「說不上來」（vague，D-40）？ |
| 6 | 「胸口緊感／緊緊的」 | symptom_character | S-STABLE-04 開場白；S-STABLE-04#1 回答 | tightness | 開場白 gpt、Gemma 皆不填（列入 unclassified） | 「緊」是否等同「悶」（tightness）？ |
| 7 | 「心絞痛（以診斷名稱描述症狀）」 | symptom_character | S-MID-03 開場白「我的心絞痛以前一個月含一次舌下片」 | pain | gpt、Gemma 皆抽成 pain | 「心絞痛又發作」記成哪一類性質（pain？或要追問）？ |
| 8 | 「胸口肌肉按下去會痛、深呼吸也痛」 | symptom_character | S-MID-14 開場白 | pain | gpt 抽成 pain；Gemma 不填（列入 unclassified） | 可重現的胸壁痛記 pain（屬胸部症狀，可與冒汗湊成 RF-06）還是 other？ |
| 9 | 「下巴跟左肩那邊沉沉的／沉沉重重」 | symptom_character | S-ACUTE-04#0 Q-ONGOING-01 回答；S-MID-18#0 Q-CHARACTER-01 回答 | jaw_shoulder_heaviness | gpt、Gemma 皆抽成 jaw_shoulder_heaviness | 「沉沉的」是否等同選項的「沉重」？（兩模型目前視為等同） |
| 10 | 「晚上躺下會覺得比較喘、要墊高枕頭」 | dyspnea_grade／rest_symptom | S-MID-11 開場白 | orthopnea_pnd＝true，dyspnea_grade 未知 | gpt 只填 orthopnea_pnd＝true（其餘列 unclassified）；Gemma 填 orthopnea_pnd＝true、rest_symptom＝true、symptom_character＝none；兩者都不再抽成 dyspnea_grade＝rest | 躺下才喘是否算「坐著或躺著休息的時候發作」（rest_symptom）？是否影響 dyspnea_grade？（v1 兩模型抽成 dyspnea_grade＝rest → RF-02 假警報） |
| 11 | 「最近沒有任何不舒服／他沒有不舒服（概括否認）」 | 各紅旗 slot | S-MID-20、S-MID-17 開場白 | symptom_character＝none | 只寫有否定詞證據的欄位（gpt：ongoing_now＝false）；沒點名的紅旗不寫、照問 | 概括否認可否視為各紅旗皆否認、省略紅旗題？ |
| 12 | 「不太會喘（委婉否認）」 | dyspnea_grade | Q-DYSPNEA-GRADE-01 回答 19 句（例：S-STABLE-02#0） | 未知 | gpt、Gemma 皆抽成 none（v2 提示以開發集句子為例） | 「不太會喘」是否等同沒有喘（none）？ |
| 13 | 「剛才胸口一陣壓迫感（沒說現在還在不在）」 | last_episode_timing／ongoing_now | S-ACUTE-06 開場白 | today | gpt：today；Gemma 抽成 ongoing → 程式丟棄（片段沒有「還在」等字眼）→ 未知 | 「剛才…」只記今天、不推定仍在發作（現行作法：追問 Q-ONGOING-01）是否可接受？ |
| 14 | 「剛剛就是吃飽坐著的時候（飯後坐著發作）」 | rest_symptom | S-MID-13 閉環 Q-EXERTION-01 回答「不是走路用力的時候，是休息的時候出現的，剛剛就是吃飽坐著的時候」 | （結構化事實 rest_symptom＝false） | gpt 抽成 rest_symptom＝true（順口提到）→ 走 T0-REST-NEW，閉環判 T0（truth T3） | 飯後坐著時發作、打嗝後緩解，算不算「休息時發作」（rest_symptom）？ |

保留集尚未執行閉環，沒有收集保留集的說法（避免在凍結前看到保留集）。

## 6. 費用與耗時

- 實際花費合計（依 repo PRICES 估算，以帳單為準）：**US$9.70**（整體上限 US$25；階段 A US$2.54、階段 B 試跑 US$0.13、開發集閉環 US$7.03）
- 階段 A gpt-6.1-sol 重放：US$2.54＝全量 1,235 次 US$2.373＋3 例試跑 US$0.094＋探針重呼叫 US$0.069；dev16 重算另呼叫探針 US$0.017（算在閉環這段）
- 階段 B 3 例試跑：US$0.130（Opus 13 次 US$0.081＋gpt 抽取 US$0.049）
- 開發集閉環（指揮官核准上限 US$15）：US$7.03＝Opus 病人 US$5.98（dev15：gpt arm 502 次新呼叫 US$3.42、Gemma arm 289 次 US$1.91；dev16 重跑 84 次 US$0.66）＋gpt 抽取 US$1.03（dev15 US$0.84、dev16 US$0.19）＋階段 A 重算的探針 US$0.017
- Gemma（本機，不計費）：階段 A 正式重放（一次一句）1,250 次、03:14–03:50；閉環 dev15 04:12–04:23、dev16 04:28–04:30（4 路並行，新呼叫延遲中位數 2.97 秒）；模型 00:59 載入、03:54 卸載，04:03 為閉環重新載入、跑完 `lms unload --all`，伺服器維持開著、沒有載入模型
- gpt 牆鐘時間：階段 A 03:04–03:15（8 路）；閉環 dev15 04:03–04:12、dev16 04:27–04:28（8 路）
- 本輪（獨立驗收修正）：US$0（五輪修正都只用快取重算：開發集閉環 0 次 API／LM Studio；階段 A 重放 0 次新呼叫）

## 7. 改動的檔案

- `sim/runner.py`：新增 extractor／to_traditional 選項（預設 None，行為不變）：開場白與病人每句話（含再說一次、複誦回答）交給抽取器，抽出的值決定 slot、紅旗、gate、下一題與 D-50 複誦；順口提到的值補未知的 slot（D-50 範圍：會 Hard stop 或最嚴重一級才收，否則沒問過先暫存、直接問到仍未知時以暫存值複誦，問過就立刻複誦；目前已是或寫入後會變 Hard stop 時都不複誦、直接寫入），已知值只在紅旗是非題「有」、confirm_back_severity 較嚴重或寫入後變成 Hard stop 時覆蓋，其他記為 conflict；結構化值留在 Turn.structured_answer
- `sim/extractor_e2e.py`：replay() 加可選的 writer（自訂寫入方式），預設行為不變（keyword 重放輸出逐位相同）
- `sim/e2e_llm.py`：run_cell()／hs_trigger_diag() 把 writer 傳下去，預設行為不變
- `data/extractor_prompts_v2.yaml（新）`：抽取器 v2 提示（開場白、回答句、複誦回答三種）與程式保護用詞表
- `sim/llm_extract_v2.py（新）`：抽取器 v2：schema、解析、極性保護、快取／預算／以原始輸出重算，與階段 A 重放 CLI
- `sim/closed_loop.py（新）`：閉環模擬 CLI：病人對話前綴快取（鍵含病人模型、effort、prompt_version）、structured 自我檢查、premature 判定、conflict 紀錄；保留集防護：固定位置的凍結紀錄（全部凍結檔＋提示全文 sha256＋時間）、三個 arm 都要凍結、不得 --limit、固定位置的執行登記（同一 arm 只跑一次）；可用階段 A 抽取快取當種子；所有前置檢查（金鑰、opencc、LM Studio、輸入檔、凍結 hash）先於登記
- `sim/extractor_v2_report.py（新）`：組本報告與模糊說法裁定表（.md／.xlsx）；輸入全部在 reports/extractor_v2_2026-10-27_inputs/，可只靠 repo 逐位重產
- `tests/test_extractor_v2.py（新）、tests/test_closed_loop.py（新）`：不打 API 的單元測試（假 client）
- `reports/extractor_v2_2026-10-27.{md,json}、reports/extractor_v2_ambiguous_2026-10-27.{md,xlsx}（新）`：本報告與模糊說法裁定表
- `reports/extractor_v2_2026-10-27_inputs/（新）`：報告的輸入：階段 A 重放輸出、開發集閉環各 arm 的指標與逐例摘要（含試跑）、模糊說法、迭代紀錄、結論、目前 hash 與其他人工整理的欄位

## 8. 重現

```
# 送進抽取器前要能轉繁：專案 .venv 沒有 opencc，以 PYTHONPATH 指向本機 uv 快取裡的 opencc-python-reimplemented 0.1.7（D-49 ASR 環境同一版，不下載）
export OPENCC_PATH=$(dirname $(find ~/.cache/uv/archive-v0 -maxdepth 2 -name 'opencc_python_reimplemented-*.dist-info' | head -1))
# 階段 A：開發集重放（gpt 需 ACS_OPENAI_API_KEY；Gemma 需 lms load gemma-4-26b-a4b-it-mlx -c 8192）
zsh -ic 'cd ~/Documents/GitHub/acs_triage && PYTHONPATH=$OPENCC_PATH uv run python -m sim.llm_extract_v2 replay --extractors gpt,gemma --conditions ref,phone --budget 6 --cache-dir <scratch> --out <scratch>'
# 階段 B：結構化值對照（免費、自我檢查）與閉環（Opus 需 ACS_PATIENT_LLM_KEY）
uv run python -m sim.closed_loop run --set dev --arm structured --cache-dir <scratch> --out <scratch>
zsh -ic 'cd ~/Documents/GitHub/acs_triage && PYTHONPATH=$OPENCC_PATH uv run python -m sim.closed_loop run --set dev --arm gpt --opus-budget 4 --gpt-budget 2.5 --seed-extract <scratch>/v2_cache_gpt.json --cache-dir <scratch>/devrun --out <scratch>/devrun'   # 再 --arm gemma --seed-extract <scratch>/v2_cache_gemma.json
zsh -ic 'cd ~/Documents/GitHub/acs_triage && PYTHONPATH=$OPENCC_PATH uv run python -m sim.closed_loop run --set dev --arm gpt --limit 3 --opus-budget 1 --gpt-budget 1 --cache-dir <scratch> --out <scratch>'
# 報告與裁定表（只用 repo 內的輸入，逐位重產）
uv run python -m sim.extractor_v2_report
```
