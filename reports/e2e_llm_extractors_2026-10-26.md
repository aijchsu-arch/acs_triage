# 實驗 2：完整流程重放（口語 → 文字 → 抽取器 → 規則）— 2026-10-26

> **限制（先讀）**
>
> 1. **重放不補問**：對話序列照逐字稿固定，抽取狀態不足時真實 runner 會再問（最多 11 題），重放不會 → Tier 9（轉護理師）可能偏多、under 可能偏少；抽取狀態一觸發 Hard stop 即停，其後各輪不再重放。
> 2. **合成語音**：phone 條件是 macOS `say` 合成標準國語、模擬電話線路後給本機 Whisper 轉寫（D-49），沒有台語、高齡口音、喘氣停頓與環境噪音，是 **樂觀上限**，不能代表真實來電。
> 3. **Opus 病人逐字稿**：病人回答由 LLM（Opus）依情境事實生成，句子比真實病人完整、少答非所問；正確答案＝情境事實（單一裁定者），本實驗是一致性檢查，不是準確度。
> 4. **雲端模型不可用於真實資料**：gpt-6.1-sol 只作「抽取能力上限」參考，真實病人資料不得送外部 API（D-10）；院內可部署的候選是本機模型。全部資料為合成資料。

## 結論（人工撰寫，依本報告數字；重產報告時此節不會自動生成）

1. **被問那題的抽取已接近結構化答案**：gpt-6.1-sol 正確 632/646（ref）／631/646（phone），紅旗題 346/346／344/346；紅旗題病人答「有」19 輪，gpt 與 Gemma 四格全部抽成「有」（keyword 漏 9／10）。與 D-40 重跑（slot 提示 0.3，`m3b_slots_2026-10-16`）的 638/653 相近。
2. **整條流程仍未達 D-42 的上線條件（Hard-stop miss 0、假警報趨近 0）**：gpt Hard-stop miss 4/27（ref）、5/27（phone），假 Hard stop 1；Gemma 4/27、6/27，假 Hard stop 21、30。under 全部 0（漏掉的 Hard stop 落在 T9／T0，T9 不計 under）。
3. **LLM 的 Hard-stop miss 沒有一例是紅旗題「有」被漏抽**；除 Gemma phone 的 2 例 premature（紅旗題「沒有」抽成「有」、提早觸發）外，都來自開場白（逐例見 §1 明細與「觸發點」）：
   - 開場白的症狀性質沒填：「胸口不太舒服」（S-INSUF-07#0，兩模型）、「胸悶」（S-ACUTE-05#0，Gemma）、「心絞痛」（S-MID-03#0，Gemma）；phone 另有 S-ACUTE-04#0（開場白「下午突然下顎和左肩有沉重不適」被 Whisper 轉成「下午突然下午合作兼有成重度事」）。之後「現在還在悶」雖抽成 ongoing_now=true，沒有胸部症狀就湊不成 RF-03。其實這 4 例的 Q-ONGOING-01 回答已說出性質（S-INSUF-07#0「胸口怪怪的」、S-ACUTE-04#0「下巴跟左肩那邊還是覺得沉沉的」、S-ACUTE-05#0「胸口還是悶悶的」、S-MID-03#0「被壓住的感覺」），但 LLM 有題目的輪只回被問那題、把它丟掉；keyword 則每句寫入全部抽到的 slot，兩者寫入方式不對等，這部分只會讓 LLM 看起來比實際差。補救路徑有二（皆**未驗證**）：回答句也抽全部 slot（BLUEPRINT §3.4），或真實 runner 補問 Q-CHARACTER-01（重放不補問）。
   - 開場白性質抽成 other：gpt 把「胸口脹脹的」抽成 other（結構化事實為 epigastric；S-MID-13#0、#1）。other 不在 `chest_symptom_characters`，RF-01／RF-03／RF-06 永遠不成立，且 slot 已知、真實 runner 也不會再問 → **真正會漏**。
   - premature：「晚上躺下會覺得比較喘要墊高枕頭」在 ref 被兩個 LLM 抽成 dyspnea_grade=rest（＋rest_symptom=true；gpt phone 只抽了 dyspnea_grade=rest，沒有 rest_symptom）→ 開場白即 RF-02 Hard stop（S-MID-11 假警報；S-MID-11#1 的真紅旗是第 2 句才揭露的 RF-04，提早觸發的 RF-02 依慣例計 miss，但病人實際仍走 119）。這違反 RF-02「端坐呼吸不算」，而抽取提示（slot 0.3 與開場白 0.1）都沒有這條臨床備註。Gemma phone 另 2 例 premature 來自 Q-ONGOING-01 極性翻轉（S-MID-10#0、S-MID-19#3；後者部分來自 Whisper 把句首「現在沒有」轉成「現在的油」）。
4. **Gemma 的主要問題是是非題「沒有」被抽成「有」**：ref 抽錯 83 輪，其中 Q-ONGOING-01「現在沒有了」→ true 29 輪、Q-SCREEN-01 13、Q-ANTIPLT-01 12、Q-ONSET-01 7 → 假 Hard stop 21（多為 RF-03）。方向偏急，但非 Hard stop 的 92 例中 21 例（ref）／30 例（phone）會被送進 119 流程，營運上不可用；而且抽成的是最嚴重值，D-50 複誦依設計不會觸發。
5. **phone 比 ref**：gpt 掉得少（Hard-stop miss +1、exact −3.4 pt、被問 slot 正確 −1）；Gemma Hard-stop miss +2、假 Hard stop +9、正確 −19；keyword 掉最多（Hard-stop miss +5、abstention FP +18、正確 −26）。
6. **本機延遲（Gemma，一次一句）**：回答句中位數 0.42 s、p95 0.50 s；開場白（一次輸出 40 欄）6.64／7.14 s；全部 1,111 次 0.42／6.51 s。gpt（8 路並行）2.71／22.61 s。
7. **D-50 複誦估算（phone，紅旗題抽錯）**：gpt 2 句全會觸發；Gemma 抽錯 64 輪（57 句）、會觸發 24 輪（22 句），不觸發的 40 輪全是「沒有→有」（最嚴重值不複誦）；keyword 抽錯 251 輪（162 句）、會觸發 240 輪（151 句）。LLM 沒有「有」被漏抽，這一類沒有東西需要複誦攔。本估算只算紅旗題，未含 D-50 範圍內的關鍵題 Q-CHARACTER-01、Q-REST-02（phone 兩格 LLM 這兩題抽錯皆 0，結論不變）。
8. **abstention FP**：gpt 16 例中 10 例、Gemma 21 例中 7 例，gate 缺的欄位是結構化開場白已知、LLM 開場白沒抽到的（如 ongoing_now、exertion_relation、symptom_character）；真實 runner 會補問，這部分是重放近似。

**建議（未實作，也未改提示，以免對同一批句子調參）**：(a) 開場白提示是否加入「端坐呼吸／夜間喘醒 → orthopnea_pnd，不是 rest」「提到胸口不適但說不出性質 → vague」「胸口脹 → epigastric」，涉及臨床判斷，需 Clinical Owner 裁定；(b) Gemma 是非題極性要另做提示或換模型再測，現況不能當院內抽取器；(c) 開場白缺欄的 case 有兩條補救路徑待驗證：回答句也抽全部 slot（BLUEPRINT §3.4；上述 4 例的回答已說出症狀性質），或以會補問的真實 runner 重跑，確認 S-INSUF-07#0、S-ACUTE-04#0、S-ACUTE-05#0、S-MID-03#0 能否救回。

**執行註記**：
- 逐字稿：任務指定 10-16 r2，但 D-49 合成語音的實際來源是 `eval_2026-10-20_llm_opus-5-5_medium_transcripts.json`（`sim/stt_eval.py` 的 DEFAULT_TRANSCRIPTS；765/765 句對得上 utterance 清單），10-16 r2 只有 332/772 句文字對得上、做不了 phone 條件 → 6 格用 10-20。keyword 在 10-20 ref 為 14/27（D-42 報告為 10-16 r2 的 13/27；逐字稿與 rules 版本都不同）。
- Whisper 結果：任務指定的 scratch `stt_asr_results.json` 已不存在；改用 repo 內 `reports/stt_whisper_2026-10-22.json` 的 rows（make_rows 逐字複製 A 段的 hyp_tw）。以 OpenCC s2twp＋`to_tw()` 檢查：556 句 phone `hyp_tw` 再轉一次不變（已是繁體），且 `to_tw(hyp)` 與 `hyp_tw` 556/556 相同。
- keyword 重放不變：extract_fn 介面擴充後，(1) HEAD 規則下 `sim.extractor_e2e --extractor keyword [--asked-only]` 輸出與改前逐位元相同；(2) 把改後的 `sim/extractor_e2e.py` 放進產生 10-18 報告的 commit b2e718a 快照重跑，JSON 與 `reports/e2e_2026-10-18_keyword{,_askedonly}.json` 逐位元相同（MD 只差日期行）。今天直接重跑 10-18 的設定數字會不同（over 14→16、abstention FP 30→34、exact 55.2%→51.3%；Hard-stop miss 同為 13/27），來自 b2e718a 之後規則、抽取詞表（D-45）、題庫與情境檔的改動，與本次修改無關。
- LM Studio：實驗前伺服器開著（port 1234）、沒有載入模型；實驗以 `lms load gemma-4-26b-a4b-it-mlx -c 8192` 載入，跑完 `lms unload`，已恢復原狀。

## 0. 設定

- rules_version 0.8.0；逐字稿 `eval_2026-10-20_llm_opus-5-5_medium_transcripts.json`（119 cases、765 句：開場白 119＋回答 646；不同句子 556）。
- phone 文字：`stt_whisper_2026-10-22.json` rows（condition = phone，`hyp_tw` 已轉繁體）；對不到轉寫的句子 0 句（改用原文）；轉寫與原文逐字相同 0 句。
- 抽取提示：有題目的輪原封沿用 `data/openai_prompts.yaml` slot 提示 0.3（D-40 起的版本；D-39 用 0.1，規則 3b「說不上來」為 D-40 新增）；開場白為新增 `data/extractor_prompts.yaml` 0.1（一次輸出全部欄位，沒提到填 null；排除 consult_screen_positive）。兩個 LLM 用同一份提示與 schema。
- gpt：`gpt-6.1-sol` effort medium，Responses API strict json_schema、store false，8 路並行。gemma：`gemma-4-26b-a4b-it-mlx`（LM Studio，`/v1/chat/completions` response_format json_schema strict，temperature 0），一次一句。兩者輸出都再以 schema 驗證，不合法＝抽取失敗（該句不寫入）。
- 同一（題目, 句子）只呼叫一次（快取）；寫入方式＝該句抽到的所有 slot（§3.4）。LLM 有題目的輪只回被問那題，開場白可回多欄。結構化答案＝同一份逐字稿、同一版規則、每輪寫入結構化值（同 M2 runner；只寫被問那題）。
- Hard-stop miss 含 premature（抽取狀態在真紅旗那句之前就觸發 Hard stop，不算命中）。

## 1. 6 格結果（對照：結構化答案）

| 抽取器 | 文字 | Hard-stop miss（含 premature） | premature | 假 Hard stop | latency 最大 | under | over | exact | abstention FP（TP） | 抽取失敗 |
|---|---|---|---|---|---|---|---|---|---|---|
| 結構化答案 | — | **0/27** | 0 | 0 | 0 | 0 | 0 | 100.0% | 0（12） | 0 |
| keyword | 逐字稿原文 | **14/27** | 1 | 9 | 0 | 0 | 16 | 53.8% | 34（7） | 0 |
| keyword | 電話語音＋Whisper（hyp_tw） | **19/27** | 1 | 7 | 0 | 0 | 10 | 43.7% | 52（7） | 0 |
| gpt-6.1-sol | 逐字稿原文 | **4/27** | 1 | 1 | 0 | 0 | 0 | 86.6% | 16（12） | 0 |
| gpt-6.1-sol | 電話語音＋Whisper（hyp_tw） | **5/27** | 1 | 1 | 0 | 0 | 2 | 83.2% | 18（12） | 0 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | **4/27** | 1 | 21 | 0 | 0 | 14 | 66.4% | 21（7） | 0 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper（hyp_tw） | **6/27** | 2 | 30 | 0 | 0 | 20 | 63.0% | 17（5） | 0 |

under／over 不含 Tier 9（9 另計 abstention）；exact 分母為可評分 case。

### phone 比 ref 掉多少（phone − ref）

| 抽取器 | Hard-stop miss | 假 Hard stop | under | over | exact | abstention FP | 被問 slot 正確 | 紅旗「有」漏抽 |
|---|---|---|---|---|---|---|---|---|
| keyword | +5 | -2 | +0 | -6 | -10.1 pt | +18 | -26 | +1 |
| gpt-6.1-sol | +1 | +0 | +0 | +2 | -3.4 pt | +2 | -1 | +0 |
| gemma-4-26b-a4b-it-mlx | +2 | +9 | +0 | +6 | -3.4 pt | -4 | -19 | +0 |

### Hard-stop miss 明細

- structured：（無）
- keyword/ref：S-ACUTE-01#0, S-ACUTE-02#1, S-ACUTE-04#0, S-ACUTE-05#0, S-MID-03#0, S-MID-10#0, S-MID-11#0, S-MID-12#1, S-MID-13#0, S-MID-13#1, S-MID-16#1, S-MID-17#1, S-MID-19#2, S-MID-19#3；premature ['S-MID-19#3']；假 Hard stop S-STABLE-01, S-STABLE-01#1, S-STABLE-02#1, S-STABLE-03#0, S-INSUF-01#1, S-INSUF-05#1, S-INSUF-07, S-MID-08#2, S-MID-15#0
- keyword/phone：S-ACUTE-01#0, S-ACUTE-02#1, S-ACUTE-03#1, S-ACUTE-04#0, S-ACUTE-05#0, S-ACUTE-06, S-ACUTE-06#0, S-INSUF-04#0, S-MID-03#0, S-MID-06#0, S-MID-10#0, S-MID-11#0, S-MID-12#1, S-MID-13#0, S-MID-13#1, S-MID-16#1, S-MID-17#1, S-MID-19#2, S-MID-19#3；premature ['S-MID-19#3']；假 Hard stop S-STABLE-01, S-STABLE-01#1, S-STABLE-02#1, S-INSUF-01#1, S-INSUF-05#1, S-MID-08#2, S-MID-15#0
- gpt/ref：S-INSUF-07#0, S-MID-11#1, S-MID-13#0, S-MID-13#1；premature ['S-MID-11#1']；假 Hard stop S-MID-11
- gpt/phone：S-ACUTE-04#0, S-INSUF-07#0, S-MID-11#1, S-MID-13#0, S-MID-13#1；premature ['S-MID-11#1']；假 Hard stop S-MID-11
- gemma/ref：S-ACUTE-05#0, S-INSUF-07#0, S-MID-03#0, S-MID-11#1；premature ['S-MID-11#1']；假 Hard stop S-ACUTE-02, S-ACUTE-03#2, S-STABLE-01, S-STABLE-01#1, S-STABLE-01#2, S-INSUF-01#0, S-INSUF-02#1, S-INSUF-03, S-INSUF-03#0, S-INSUF-04#2, S-INSUF-05, S-INSUF-05#0, S-INSUF-05#1, S-INSUF-06#1, S-MID-11, S-MID-14#0, S-MID-16, S-MID-16#0, S-MID-17#0, S-MID-19#0, S-MID-19#1
- gemma/phone：S-ACUTE-04#0, S-ACUTE-05#0, S-INSUF-07#0, S-MID-03#0, S-MID-10#0, S-MID-19#3；premature ['S-MID-10#0', 'S-MID-19#3']；假 Hard stop S-ACUTE-02, S-STABLE-01, S-STABLE-01#1, S-INSUF-01#0, S-INSUF-02, S-INSUF-02#0, S-INSUF-02#1, S-INSUF-03, S-INSUF-03#0, S-INSUF-03#1, S-INSUF-04, S-INSUF-04#1, S-INSUF-04#2, S-INSUF-05, S-INSUF-05#0, S-INSUF-05#1, S-INSUF-06#1, S-MID-04#0, S-MID-06#1, S-MID-08, S-MID-08#0, S-MID-08#2, S-MID-11, S-MID-12, S-MID-14, S-MID-14#0, S-MID-15#0, S-MID-17#0, S-MID-19, S-MID-19#0

### 假 Hard stop 與 premature 的觸發點（第一次觸發的那句與寫入的值；「正確」＝結構化值）

- **keyword/ref**（10）
  - S-STABLE-01（假警報，truth T3）第 4 句 Q-DIAPH-01 RF-01：寫入 {'symptom_character': 'vague', 'consult_topic': 'symptom'}，正確 {'diaphoresis': False}「沒有，不舒服的時候不會冒冷汗。」
  - S-STABLE-01#1（假警報，truth T0）第 3 句 Q-DYSPNEA-GRADE-01 RF-01：寫入 {'symptom_character': 'tightness', 'dyspnea_complaint': True, 'consult_topic': 'symptom'}，正確 {'dyspnea_grade': 'none'}「喘的話其實是沒有啦，我比較是胸口悶悶的，不會覺得喘。」
  - S-STABLE-02#1（假警報，truth T0）第 4 句 Q-DIAPH-01 RF-01：寫入 {'symptom_character': 'vague', 'consult_topic': 'symptom'}，正確 {'diaphoresis': False}「沒有，不舒服的時候不會冒冷汗。」
  - S-STABLE-03#0（假警報，truth T0）第 5 句 Q-DIAPH-01 RF-06：寫入 {'diaphoresis': True}，正確 {'diaphoresis': None}「冒冷汗喔……這個我沒什麼印象，不太確定耶。」
  - S-INSUF-01#1（假警報，truth T3）第 4 句 Q-DIAPH-01 RF-01：寫入 {'symptom_character': 'vague', 'consult_topic': 'symptom'}，正確 {'diaphoresis': False}「沒有耶，不舒服的時候不會冒冷汗。」
  - S-INSUF-05#1（假警報，truth T3）第 2 句 Q-SYNCOPE-01 RF-01：寫入 {'presyncope': True, 'consult_topic': 'symptom'}，正確 {'presyncope': False}「不會耶，沒有那種快昏倒或眼前發黑的感覺。」
  - S-INSUF-07（假警報，truth T9）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True, 'third_party_call': True, 'patient_reachable': False, 'consult_topic': 'symptom'}，正確 {'ongoing_now': None}「這個我不太確定耶，我爸現在不在我旁邊，我不知道他現在還有沒有在不舒服。」
  - S-MID-08#2（假警報，truth T1）第 2 句 Q-SYNCOPE-01 RF-01：寫入 {'presyncope': True, 'consult_topic': 'symptom'}，正確 {'presyncope': False}「沒有耶，不會有要昏倒或眼前發黑的感覺。」
  - S-MID-15#0（假警報，truth T1）第 5 句 Q-SYNCOPE-01 RF-01：寫入 {'presyncope': True, 'consult_topic': 'symptom'}，正確 {'presyncope': False}「沒有耶，不會有快要昏倒或眼前發黑的感覺。」
  - S-MID-19#3（premature，truth T0）第 2 句 Q-SYNCOPE-01 RF-01：寫入 {'presyncope': True, 'consult_topic': 'symptom'}，正確 {'presyncope': False}「不會，沒有快要昏倒或眼前發黑的感覺。」
- **keyword/phone**（8）
  - S-STABLE-01（假警報，truth T3）第 4 句 Q-DIAPH-01 RF-01：寫入 {'symptom_character': 'vague', 'consult_topic': 'symptom'}，正確 {'diaphoresis': False}「沒有,不舒服的時候不會冒冷汗。」
  - S-STABLE-01#1（假警報，truth T0）第 3 句 Q-DYSPNEA-GRADE-01 RF-01：寫入 {'symptom_character': 'tightness', 'dyspnea_complaint': True, 'consult_topic': 'symptom'}，正確 {'dyspnea_grade': 'none'}「喘的話其實是沒有啦,我比較是胸口悶悶的,不會覺得喘。」
  - S-STABLE-02#1（假警報，truth T0）第 4 句 Q-DIAPH-01 RF-01：寫入 {'symptom_character': 'vague', 'consult_topic': 'symptom'}，正確 {'diaphoresis': False}「沒有,不舒服的時候不會冒冷汗。」
  - S-INSUF-01#1（假警報，truth T3）第 4 句 Q-DIAPH-01 RF-01：寫入 {'symptom_character': 'vague', 'consult_topic': 'symptom'}，正確 {'diaphoresis': False}「沒有耶,不舒服的時候不會鬧人汗。」
  - S-INSUF-05#1（假警報，truth T3）第 2 句 Q-SYNCOPE-01 RF-01：寫入 {'presyncope': True, 'consult_topic': 'symptom'}，正確 {'presyncope': False}「不會也,沒有那種快昏老貨眼前發黑的感覺」
  - S-MID-08#2（假警報，truth T1）第 2 句 Q-SYNCOPE-01 RF-01：寫入 {'presyncope': True, 'consult_topic': 'symptom'}，正確 {'presyncope': False}「沒有耶,不會有藥昏倒或眼前發黑的感覺。」
  - S-MID-15#0（假警報，truth T1）第 5 句 Q-SYNCOPE-01 RF-01：寫入 {'presyncope': True, 'consult_topic': 'symptom'}，正確 {'presyncope': False}「沒有夜,不會有快要昏倒或眼前發黑的感覺。」
  - S-MID-19#3（premature，truth T0）第 2 句 Q-SYNCOPE-01 RF-01：寫入 {'presyncope': True, 'consult_topic': 'symptom'}，正確 {'presyncope': False}「不會,沒有快要昏倒過眼前發黑的感覺。」
- **gpt/ref**（2）
  - S-MID-11（假警報，truth T0）開場白 RF-02：寫入 {'dyspnea_grade': 'rest', 'rest_symptom': True, 'exertion_relation': 'rest_only', 'third_party_call': False, 'onset_weeks_ago': 2}，正確 {'dyspnea_grade': None, 'rest_symptom': None, 'exertion_relation': None, 'third_party_call': None, 'onset_weeks_ago': None}「我有冠心症，這兩個禮拜晚上躺下會覺得比較喘要墊高枕頭，白天走路還可以，胸口不會痛。」
  - S-MID-11#1（premature，truth T0）開場白 RF-02：寫入 {'dyspnea_grade': 'rest', 'rest_symptom': True, 'exertion_relation': 'rest_only', 'third_party_call': False, 'onset_weeks_ago': 2}，正確 {'dyspnea_grade': None, 'rest_symptom': None, 'exertion_relation': None, 'third_party_call': None, 'onset_weeks_ago': None}「我有冠心症，這兩個禮拜晚上躺下會覺得比較喘要墊高枕頭，白天走路還可以，胸口不會痛。」
- **gpt/phone**（2）
  - S-MID-11（假警報，truth T0）開場白 RF-02：寫入 {'dyspnea_grade': 'rest', 'third_party_call': False}，正確 {'dyspnea_grade': None, 'third_party_call': None}「我有關心症,這樣個禮拜晚上行笑會覺得比較喘尿見高枕頭,白天走路還可以,胸口不會痛。」
  - S-MID-11#1（premature，truth T0）開場白 RF-02：寫入 {'dyspnea_grade': 'rest', 'third_party_call': False}，正確 {'dyspnea_grade': None, 'third_party_call': None}「我有關心症,這樣個禮拜晚上行笑會覺得比較喘尿見高枕頭,白天走路還可以,胸口不會痛。」
- **gemma/ref**（22）
  - S-ACUTE-02（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了，現在坐著休息就沒有不舒服。」
  - S-ACUTE-03#2（假警報，truth T2）第 2 句 Q-DYSPNEA-SENTENCE-01 RF-04：寫入 {'cant_finish_sentence': True}，正確 {'cant_finish_sentence': False}「不會啦，我現在講話都還好，一句話可以講完。」
  - S-STABLE-01（假警報，truth T3）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「沒有，現在沒有不舒服，都好好的。」
  - S-STABLE-01#1（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有喔，現在胸口不會悶。」
  - S-STABLE-01#2（假警報，truth T9）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有，現在胸口不會悶了。」
  - S-INSUF-01#0（假警報，truth T0）第 3 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了，這個當下是還好。」
  - S-INSUF-02#1（假警報，truth T3）第 3 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有，現在還好，沒有在悶。」
  - S-INSUF-03（假警報，truth T9）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了，現在胸口不會悶。」
  - S-INSUF-03#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有，現在胸口不會悶了。」
  - S-INSUF-04#2（假警報，truth T3）第 2 句 Q-DYSPNEA-SENTENCE-01 RF-04：寫入 {'cant_finish_sentence': True}，正確 {'cant_finish_sentence': False}「不會啦，我現在講話都很正常，不會喘到講不完。」
  - S-INSUF-05（假警報，truth T9）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了，現在坐著休息胸口不會悶。」
  - S-INSUF-05#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了，我現在坐著休息，胸口不會悶。」
  - S-INSUF-05#1（假警報，truth T3）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有啦，現在坐著都還好，沒有悶。」
  - S-INSUF-06#1（假警報，truth T9）第 3 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了，現在還好，沒有不舒服。」
  - S-MID-11（假警報，truth T0）開場白 RF-02：寫入 {'dyspnea_grade': 'rest', 'rest_symptom': True, 'exertion_relation': 'both', 'third_party_call': False, 'patient_reachable': True, 'onset_weeks_ago': 2}，正確 {'dyspnea_grade': None, 'rest_symptom': None, 'exertion_relation': None, 'third_party_call': None, 'patient_reachable': None, 'onset_weeks_ago': None}「我有冠心症，這兩個禮拜晚上躺下會覺得比較喘要墊高枕頭，白天走路還可以，胸口不會痛。」
  - S-MID-11#1（premature，truth T0）開場白 RF-02：寫入 {'dyspnea_grade': 'rest', 'rest_symptom': True, 'exertion_relation': 'both', 'third_party_call': False, 'patient_reachable': True, 'onset_weeks_ago': 2}，正確 {'dyspnea_grade': None, 'rest_symptom': None, 'exertion_relation': None, 'third_party_call': None, 'patient_reachable': None, 'onset_weeks_ago': None}「我有冠心症，這兩個禮拜晚上躺下會覺得比較喘要墊高枕頭，白天走路還可以，胸口不會痛。」
  - S-MID-14#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在這個時候沒有在痛了，是沒有不舒服的。」
  - S-MID-16（假警報，truth T3）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有在痛，現在沒咳就還好。」
  - S-MID-16#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有，現在沒在咳就不會痛。」
  - S-MID-17#0（假警報，truth T9）第 4 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了，他現在沒有不舒服。」
  - S-MID-19#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有，胸口沒在悶了。」
  - S-MID-19#1（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有，胸口這會兒不會悶。」
- **gemma/phone**（32）
  - S-ACUTE-02（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,現在坐著休息就沒有不舒服。」
  - S-STABLE-01（假警報，truth T3）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「沒有,現在沒有不舒服,都好好的。」
  - S-STABLE-01#1（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有喔現在胸口不會悶」
  - S-INSUF-01#0（假警報，truth T0）第 3 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,這個端像是還好。」
  - S-INSUF-02（假警報，truth T9）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,這個單下胸口沒有不舒服。」
  - S-INSUF-02#0（假警報，truth T0）第 3 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,這個端效不會不舒服。」
  - S-INSUF-02#1（假警報，truth T3）第 3 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有 現在還好 沒有在悶」
  - S-INSUF-03（假警報，truth T9）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,現在胸口不會悶。」
  - S-INSUF-03#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有,現在胸口不會扔了。」
  - S-INSUF-03#1（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了現在不會悶」
  - S-INSUF-04（假警報，truth T9）第 2 句 Q-DYSPNEA-SENTENCE-01 RF-04：寫入 {'cant_finish_sentence': True}，正確 {'cant_finish_sentence': False}「不會啦,現在講話還好,一句話講得完。」
  - S-INSUF-04#1（假警報，truth T0）第 2 句 Q-DYSPNEA-SENTENCE-01 RF-04：寫入 {'cant_finish_sentence': True}，正確 {'cant_finish_sentence': False}「不會啦,現在講話還好,一句話可以講完。」
  - S-INSUF-04#2（假警報，truth T3）第 2 句 Q-DYSPNEA-SENTENCE-01 RF-04：寫入 {'cant_finish_sentence': True}，正確 {'cant_finish_sentence': False}「不會啦,我現在講話都很正常,不會喘到講不完。」
  - S-INSUF-05（假警報，truth T9）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,現在坐著休息胸口不會悶。」
  - S-INSUF-05#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,我現在坐著休息,胸口不會悶。」
  - S-INSUF-05#1（假警報，truth T3）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了現在坐著都還好沒有悶」
  - S-INSUF-06#1（假警報，truth T9）第 3 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了現在還好沒有不舒服」
  - S-MID-04#0（假警報，truth T1）第 4 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,這個端效不會不舒服。」
  - S-MID-06#1（假警報，truth T0）第 1 句 Q-DYSPNEA-SENTENCE-01 RF-04：寫入 {'cant_finish_sentence': True}，正確 {'cant_finish_sentence': False}「不會啦,我現在坐著講話都還好,不會喘到講不完。」
  - S-MID-08（假警報，truth T3）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有我,我現在做住卷煉貨,胸口不會扔。」
  - S-MID-08#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,我現在坐住休息,胸口沒有悶。」
  - S-MID-08#2（假警報，truth T1）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,現在做助家還好,是走路的時候才會生。」
  - S-MID-10#0（premature，truth T0）第 4 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,這個單下胸口沒有不舒服。」
  - S-MID-11（假警報，truth T0）第 2 句 Q-DYSPNEA-SENTENCE-01 RF-04：寫入 {'cant_finish_sentence': True}，正確 {'cant_finish_sentence': False}「不會啦,現在講話都還好,不會喘到講不完。」
  - S-MID-12（假警報，truth T2）第 1 句 Q-DYSPNEA-SENTENCE-01 RF-04：寫入 {'cant_finish_sentence': True}，正確 {'cant_finish_sentence': False}「不會了,講話還好,不會傳到講不完。」
  - S-MID-14（假警報，truth T3）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在這個段下沒有不舒服,胸口還好。」
  - S-MID-14#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在這個時候沒有再痛了是沒有不舒服的」
  - S-MID-15#0（假警報，truth T1）第 4 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在的油窩,胸口這時候不會不舒服。」
  - S-MID-17#0（假警報，truth T9）第 4 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在沒有了,他現在沒有不舒服。」
  - S-MID-19（假警報，truth T1）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在的油,胸口現在不會扔。」
  - S-MID-19#0（假警報，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在的油,胸口沒在燈了。」
  - S-MID-19#3（premature，truth T0）第 1 句 Q-ONGOING-01 RF-03：寫入 {'ongoing_now': True}，正確 {'ongoing_now': False}「現在的油,胸口現在不會扔。」

### ref → phone 結果改變的 case

- keyword（21）：S-ACUTE-03#1（truth 0＋HS：HS → T0）；S-ACUTE-03#2（truth 2：T0 → T9）；S-ACUTE-06（truth 0＋HS：HS → T9）；S-ACUTE-06#0（truth 0＋HS：HS → T9）；S-STABLE-02（truth 3：T0 → T9）；S-STABLE-03#0（truth 0：HS → T9）；S-INSUF-04#0（truth 0＋HS：HS → T0）；S-INSUF-07（truth 9：HS → T0）；S-MID-01（truth 1：T0 → T9）；S-MID-03（truth 0：T0 → T9）；S-MID-03#0（truth 0＋HS：T0 → T9）；S-MID-06#0（truth 0＋HS：HS → T9）；S-MID-06#1（truth 0：T0 → T9）；S-MID-06#2（truth 0：T0 → T9）；S-MID-07#2（truth 0：T0 → T9）；S-MID-08#1（truth 0：T0 → T9）；S-MID-11（truth 0：T0 → T9）；S-MID-12（truth 2：T0 → T9）；S-MID-12#0（truth 0：T0 → T9）；S-MID-13（truth 3：T0 → T9）；S-MID-14（truth 3：T0 → T9）
- gpt-6.1-sol（6）：S-ACUTE-04（truth 0：T0 → T9）；S-ACUTE-04#0（truth 0＋HS：HS → T9）；S-MID-08（truth 3：T3 → T0）；S-MID-08#2（truth 1：T1 → T0）；S-MID-10（truth 2：T2 → T9）；S-MID-18（truth 4：T9 → T4）
- gemma-4-26b-a4b-it-mlx（33）：S-ACUTE-03#2（truth 2：HS → T0）；S-ACUTE-04（truth 0：T0 → T9）；S-ACUTE-04#0（truth 0＋HS：HS → T9）；S-STABLE-01#2（truth 9：HS → T0）；S-STABLE-02（truth 3：T0 → T9）；S-STABLE-03（truth 3：T3 → T9）；S-STABLE-04（truth 3：T9 → T0）；S-INSUF-01#1（truth 3：T9 → T0）；S-INSUF-02（truth 9：T9 → HS）；S-INSUF-02#0（truth 0：T0 → HS）；S-INSUF-03#1（truth 0：T0 → HS）；S-INSUF-04（truth 9：T9 → HS）；S-INSUF-04#1（truth 0：T0 → HS）；S-INSUF-08#1（truth 3：T9 → T3）；S-MID-01#1（truth 2：T2 → T0）；S-MID-04#0（truth 1：T0 → HS）；S-MID-06#1（truth 0：T0 → HS）；S-MID-08（truth 3：T9 → HS）；S-MID-08#0（truth 0：T0 → HS）；S-MID-08#2（truth 1：T9 → HS）；S-MID-10#0（truth 0＋HS：HS → T0）；S-MID-11#1（truth 0＋HS：T0 → HS）；S-MID-12（truth 2：T0 → HS）；S-MID-13（truth 3：T0 → T3）；S-MID-14（truth 3：T9 → HS）；S-MID-15#0（truth 1：T9 → HS）；S-MID-16（truth 3：HS → T0）；S-MID-16#0（truth 0：HS → T9）；S-MID-19（truth 1：T1 → HS）；S-MID-19#1（truth 0：HS → T0）；S-MID-19#3（truth 0＋HS：HS → T0）；S-MID-20（truth 4：T9 → T4）；S-MID-20#0（truth 3：T9 → T3）

## 2. 被問那題的抽取（每一輪都算，不因 Hard stop 截斷；正確答案＝逐字稿結構化值）

| 抽取器 | 文字 | 全部 正確 | 紅旗題 | 關鍵題（decisive） | 補充題（refine） | 漏抽 | 抽錯 | 多抽 | 互換／說不上來 |
|---|---|---|---|---|---|---|---|---|---|
| keyword | 逐字稿原文 | 249/646（38.5%） | 111/346（32.1%） | 130/283（45.9%） | 8/17（47.1%） | 316 | 40 | 18 | 23 |
| keyword | 電話語音＋Whisper（hyp_tw） | 223/646（34.5%） | 95/346（27.5%） | 125/283（44.2%） | 3/17（17.6%） | 361 | 24 | 15 | 23 |
| gpt-6.1-sol | 逐字稿原文 | 632/646（97.8%） | 346/346（100.0%） | 269/283（95.1%） | 17/17（100.0%） | 0 | 0 | 0 | 14 |
| gpt-6.1-sol | 電話語音＋Whisper（hyp_tw） | 631/646（97.7%） | 344/346（99.4%） | 270/283（95.4%） | 17/17（100.0%） | 3 | 0 | 0 | 12 |
| gemma-4-26b-a4b-it-mlx | 逐字稿原文 | 531/646（82.2%） | 299/346（86.4%） | 227/283（80.2%） | 5/17（29.4%） | 11 | 83 | 6 | 15 |
| gemma-4-26b-a4b-it-mlx | 電話語音＋Whisper（hyp_tw） | 512/646（79.3%） | 282/346（81.5%） | 225/283（79.5%） | 5/17（29.4%） | 16 | 100 | 5 | 13 |

### 紅旗題病人答「有」卻沒抽成「有」

- **keyword/ref**：9/19：S-ACUTE-01#0#t1 Q-ONGOING-01→None「嗯，現在胸口還是有一點壓壓的感覺，還沒完全好。」；S-ACUTE-02#1#t1 Q-ONGOING-01→None「有，現在胸口還是悶悶的，還沒退。」；S-ACUTE-04#0#t1 Q-ONGOING-01→None「嗯，現在還是有，下巴跟左肩那邊還是覺得沉沉的。」；S-ACUTE-05#0#t1 Q-ONGOING-01→None「還在耶，現在胸口還是悶悶的。」；S-MID-03#0#t1 Q-ONGOING-01→None「有，現在胸口還是有那種被壓住的感覺，還沒退。」；S-MID-13#0#t3 Q-DIAPH-01→None「有耶，那時候有冒一點冷汗。」；S-MID-13#1#t1 Q-ONGOING-01→None「嗯…其實現在胸口還是有一點不舒服，還沒完全好。」；S-MID-17#1#t4 Q-ONGOING-01→None「還在，他說現在胸口還是有那種壓壓的感覺。」；S-MID-19#2#t1 Q-ONGOING-01→None「有，現在胸口還是有那種悶悶的感覺。」
- **keyword/phone**：10/19：S-ACUTE-01#0#t1 Q-ONGOING-01→None「現在胸口還是有一點壓壓的感覺,還沒完全好。」；S-ACUTE-02#1#t1 Q-ONGOING-01→None「現在胸口還是嫩嫩的還內退」；S-ACUTE-03#1#t2 Q-DYSPNEA-SENTENCE-01→None「會兒,講話講一講就要停下來傳一下,一句話長長短。」；S-ACUTE-04#0#t1 Q-ONGOING-01→None「嗯,現在還是有,小胖跟左肩那邊還是覺得沉沉的。」；S-ACUTE-05#0#t1 Q-ONGOING-01→None「還在噎現在胸口還是悶悶的」；S-MID-03#0#t1 Q-ONGOING-01→None「現在胸口還是有那種被壓住的感覺還沒睡」；S-MID-13#0#t3 Q-DIAPH-01→None「有耶,那時候有冒一點冷汗。」；S-MID-13#1#t1 Q-ONGOING-01→None「其實現在胸口還是有一點不舒服還沒完全好」；S-MID-17#1#t4 Q-ONGOING-01→None「他說現在胸口還是有那種咬咬的感覺」；S-MID-19#2#t1 Q-ONGOING-01→None「喲,現在胸口還是有那種悶悶的感覺。」
- **gpt/ref**：0/19
- **gpt/phone**：0/19
- **gemma/ref**：0/19
- **gemma/phone**：0/19

### 開場白抽取 vs 結構化事實（依不同開場白計）

- keyword/ref：0/40 句有差異；漏 0（—）、多 0（—）、值不同 0（—）
- keyword/phone：26/40 句有差異；漏 45（cad_history 19、consult_topic 5、symptom_character 5、exertion_relation 3）、多 1（dyspnea_complaint 1）、值不同 0（—）
- gpt/ref：35/40 句有差異；漏 22（ongoing_now 5、symptom_character 4、last_episode_timing 3、episode_duration_min 2）、多 57（third_party_call 20、recurrence 8、ongoing_now 7、onset_new 5）、值不同 2（symptom_character 2）
- gpt/phone：38/40 句有差異；漏 32（ongoing_now 5、exertion_relation 5、cad_history 5、symptom_character 4）、多 48（third_party_call 19、ongoing_now 7、recurrence 6、onset_new 4）、值不同 2（symptom_character 2）
- gemma/ref：36/40 句有差異；漏 43（symptom_character 14、ongoing_now 5、onset_new 4、consult_topic 3）、多 119（patient_reachable 18、third_party_call 17、dyspnea_grade 9、exertion_relation 8）、值不同 3（last_episode_timing 1、consult_topic 1、symptom_character 1）
- gemma/phone：38/40 句有差異；漏 66（cad_history 17、symptom_character 16、consult_topic 6、ongoing_now 5）、多 107（dyspnea_grade 12、patient_reachable 11、third_party_call 10、exertion_relation 8）、值不同 3（last_episode_timing 2、cad_history 1）

（開場白的結構化事實＝關鍵詞抽取逐字稿，因此 keyword/ref 必為 0；LLM 的「多」不一定是錯，可能是關鍵詞漏掉的真資訊。）

### Abstention FP（該判 0–4 卻判 9）：gate 缺的 slot

＊＝結構化開場白已知、這個抽取器的開場白沒抽到（真實 runner 會補問這題，重放不補問 → 這類 9 部分來自重放近似）。

- structured（0，含＊ 0）：（無）
- keyword/ref（34，含＊ 0）：S-ACUTE-01#2（T3）dyspnea_grade、cant_finish_sentence、orthopnea_pnd、dyspnea_acute、presyncope；S-ACUTE-04（T0）；S-STABLE-02#0（T3）rest_symptom、ongoing_now、diaphoresis、presyncope、dyspnea_acute、ntg_use_increased、antiplatelet_interrupted；S-STABLE-03（T3）；S-STABLE-04（T3）rest_symptom、diaphoresis、presyncope、dyspnea_acute、ntg_use_increased；S-STABLE-04#1（T0）rest_symptom、diaphoresis、presyncope、threshold_decreased、dyspnea_acute、ntg_use_increased；S-INSUF-02#0（T0）；S-INSUF-02#1（T3）dyspnea_grade、cant_finish_sentence、orthopnea_pnd、dyspnea_acute、presyncope；S-INSUF-04#1（T0）；S-INSUF-06#0（T0）；S-INSUF-08#0（T0）；S-INSUF-08#1（T3）dyspnea_grade、cant_finish_sentence、orthopnea_pnd、dyspnea_acute、presyncope；S-MID-01#0（T0）cant_finish_sentence、orthopnea_pnd、dyspnea_acute；S-MID-02（T2）diaphoresis、presyncope、last_episode_timing、ntg_use_increased；S-MID-02#0（T0）diaphoresis、presyncope、threshold_decreased、last_episode_timing、ntg_use_increased；S-MID-04（T3）cant_finish_sentence、orthopnea_pnd、dyspnea_acute；S-MID-07（T1）diaphoresis、presyncope、onset_new、ntg_use_increased；S-MID-08（T3）rest_symptom、threshold_decreased、last_episode_timing、ntg_use_increased、antiplatelet_interrupted；S-MID-09（T1）presyncope；S-MID-09#0（T0）；S-MID-10（T2）cant_finish_sentence、orthopnea_pnd、dyspnea_acute、presyncope；S-MID-10#0（T0）；S-MID-13#0（T0）diaphoresis、exertion_relation、presyncope、rest_symptom、threshold_decreased、ntg_use_increased、antiplatelet_interrupted；S-MID-13#1（T0）；S-MID-15（T4）；S-MID-16（T3）ongoing_now、diaphoresis、presyncope、threshold_decreased、ntg_use_increased、antiplatelet_interrupted；S-MID-16#0（T0）diaphoresis、exertion_relation、presyncope、threshold_decreased、ntg_use_increased、antiplatelet_interrupted；S-MID-17（T4）；S-MID-17#1（T0）；S-MID-18（T4）；S-MID-19（T1）ongoing_now、diaphoresis、threshold_decreased、ntg_use_increased；S-MID-19#2（T0）ongoing_now、diaphoresis、presyncope、threshold_decreased、ntg_use_increased、antiplatelet_interrupted；S-MID-20（T4）；S-MID-20#0（T3）
- keyword/phone（52，含＊ 0）：S-ACUTE-01#2（T3）dyspnea_grade、cant_finish_sentence、orthopnea_pnd、dyspnea_acute、presyncope；S-ACUTE-03#2（T2）orthopnea_pnd、dyspnea_acute、pattern_unchanged_duration_months；S-ACUTE-04（T0）；S-ACUTE-06（T0）；S-ACUTE-06#0（T0）；S-STABLE-02（T3）rest_symptom、ongoing_now、presyncope、dyspnea_acute、ntg_use_increased、antiplatelet_interrupted；S-STABLE-02#0（T3）rest_symptom、ongoing_now、diaphoresis、presyncope、dyspnea_acute、ntg_use_increased、antiplatelet_interrupted；S-STABLE-03（T3）；S-STABLE-03#0（T0）；S-STABLE-04（T3）rest_symptom、diaphoresis、presyncope、dyspnea_acute、ntg_use_increased；S-STABLE-04#1（T0）rest_symptom、diaphoresis、presyncope、threshold_decreased、dyspnea_acute、ntg_use_increased；S-INSUF-02#0（T0）；S-INSUF-02#1（T3）dyspnea_grade、cant_finish_sentence、orthopnea_pnd、dyspnea_acute、presyncope；S-INSUF-04#1（T0）；S-INSUF-06#0（T0）；S-INSUF-08#0（T0）；S-INSUF-08#1（T3）rest_symptom、ongoing_now、presyncope、dyspnea_acute、ntg_use_increased；S-MID-01（T1）；S-MID-01#0（T0）cant_finish_sentence、orthopnea_pnd、dyspnea_acute；S-MID-02（T2）diaphoresis、presyncope、last_episode_timing、ntg_use_increased；S-MID-02#0（T0）diaphoresis、presyncope、threshold_decreased、last_episode_timing、ntg_use_increased；S-MID-03（T0）；S-MID-03#0（T0）；S-MID-04（T3）cant_finish_sentence、orthopnea_pnd、dyspnea_acute；S-MID-06#0（T0）；S-MID-06#1（T0）；S-MID-06#2（T0）cant_finish_sentence、orthopnea_pnd、dyspnea_acute、symptom_character；S-MID-07（T1）diaphoresis、presyncope、onset_new、ntg_use_increased；S-MID-07#2（T0）rest_symptom、ongoing_now、diaphoresis、presyncope、onset_new、ntg_use_increased；S-MID-08（T3）rest_symptom、threshold_decreased、last_episode_timing、ntg_use_increased、antiplatelet_interrupted；S-MID-08#1（T0）rest_symptom、ongoing_now、threshold_decreased、last_episode_timing、onset_weeks_ago、ntg_use_increased、antiplatelet_interrupted；S-MID-09（T1）presyncope；S-MID-09#0（T0）；S-MID-10（T2）cant_finish_sentence、orthopnea_pnd、dyspnea_acute；S-MID-10#0（T0）；S-MID-11（T0）；S-MID-12（T2）cant_finish_sentence、orthopnea_pnd；S-MID-12#0（T0）；S-MID-13（T3）；S-MID-13#0（T0）diaphoresis、exertion_relation、presyncope、rest_symptom、threshold_decreased、ntg_use_increased；S-MID-13#1（T0）；S-MID-14（T3）；S-MID-15（T4）dyspnea_grade、presyncope、palpitations、postural_dizziness、pending_abnormal_test；S-MID-16（T3）ongoing_now、diaphoresis、presyncope、threshold_decreased、ntg_use_increased；S-MID-16#0（T0）diaphoresis、exertion_relation、presyncope、threshold_decreased、ntg_use_increased；S-MID-17（T4）；S-MID-17#1（T0）；S-MID-18（T4）；S-MID-19（T1）ongoing_now、diaphoresis、threshold_decreased、ntg_use_increased；S-MID-19#2（T0）ongoing_now、diaphoresis、presyncope、threshold_decreased、ntg_use_increased；S-MID-20（T4）；S-MID-20#0（T3）
- gpt/ref（16，含＊ 10）：S-ACUTE-01#2（T3）ongoing_now＊；S-STABLE-03（T3）presyncope＊；S-STABLE-04（T3）ongoing_now＊；S-INSUF-06#0（T0）；S-INSUF-07#0（T0）；S-MID-02（T2）ongoing_now＊、threshold_decreased＊；S-MID-06（T2）dyspnea_acute＊；S-MID-13（T3）；S-MID-13#0（T0）；S-MID-13#1（T0）；S-MID-13#2（T0）；S-MID-14（T3）exertion_relation＊；S-MID-15（T4）symptom_character＊；S-MID-15#0（T1）ntg_use_increased＊；S-MID-16（T3）exertion_relation＊；S-MID-18（T4）symptom_character＊
- gpt/phone（18，含＊ 9）：S-ACUTE-01#2（T3）ongoing_now＊；S-ACUTE-04（T0）；S-ACUTE-04#0（T0）；S-STABLE-03（T3）presyncope＊；S-STABLE-04（T3）ongoing_now＊；S-INSUF-06#0（T0）；S-INSUF-07#0（T0）；S-MID-02（T2）ongoing_now＊、threshold_decreased＊；S-MID-06（T2）dyspnea_acute＊；S-MID-10（T2）；S-MID-13（T3）；S-MID-13#0（T0）；S-MID-13#1（T0）；S-MID-13#2（T0）；S-MID-14（T3）exertion_relation＊；S-MID-15（T4）symptom_character＊；S-MID-15#0（T1）ntg_use_increased＊；S-MID-16（T3）exertion_relation＊
- gemma/ref（21，含＊ 7）：S-ACUTE-05#1（T3）symptom_character＊、dyspnea_grade、palpitations、postural_dizziness、pending_abnormal_test；S-STABLE-02#0（T3）；S-STABLE-04（T3）ongoing_now＊、threshold_decreased＊、dyspnea_acute；S-INSUF-01#1（T3）；S-INSUF-07#0（T0）；S-INSUF-08#1（T3）；S-MID-02（T2）；S-MID-02#2（T0）；S-MID-03（T0）；S-MID-03#0（T0）；S-MID-04（T3）symptom_character＊、palpitations、postural_dizziness、pending_abnormal_test；S-MID-05（T3）symptom_character＊；S-MID-08（T3）；S-MID-08#2（T1）；S-MID-10（T2）symptom_character＊；S-MID-14（T3）exertion_relation＊；S-MID-15（T4）palpitations、postural_dizziness、pending_abnormal_test；S-MID-15#0（T1）ntg_use_increased＊；S-MID-18（T4）palpitations、postural_dizziness、pending_abnormal_test；S-MID-20（T4）palpitations、postural_dizziness、pending_abnormal_test；S-MID-20#0（T3）pending_abnormal_test
- gemma/phone（17，含＊ 6）：S-ACUTE-04（T0）；S-ACUTE-04#0（T0）；S-ACUTE-05#1（T3）symptom_character＊、dyspnea_grade、palpitations、postural_dizziness、pending_abnormal_test；S-STABLE-02（T3）threshold_decreased＊、dyspnea_acute；S-STABLE-02#0（T3）threshold_decreased＊、dyspnea_acute；S-STABLE-03（T3）presyncope＊、palpitations、postural_dizziness、pending_abnormal_test；S-INSUF-07#0（T0）；S-MID-02（T2）；S-MID-02#2（T0）；S-MID-03（T0）；S-MID-03#0（T0）；S-MID-04（T3）symptom_character＊、palpitations、postural_dizziness、pending_abnormal_test；S-MID-05（T3）symptom_character＊；S-MID-10（T2）；S-MID-15（T4）palpitations、postural_dizziness、pending_abnormal_test；S-MID-16#0（T0）；S-MID-18（T4）

## 3. 延遲與失敗

| 抽取器 | 呼叫數 | 失敗 | 全部 中位數／p95（秒） | 開場白 中位數／p95 | 回答 中位數／p95 | 並行 |
|---|---|---|---|---|---|---|
| gpt-6.1-sol | 1111 | 0（先前失敗後重試 0） | 2.71／22.61 | 9.65／22.20 | 2.61／22.61 | 8 |
| gemma-4-26b-a4b-it-mlx | 1111 | 0（先前失敗後重試 0） | 0.42／6.51 | 6.64／7.14 | 0.42／0.50 | 1 |

gpt 的延遲是 8 路並行下量到的單次呼叫牆鐘時間（含網路與重試）；gemma 為本機一次一句。

## 4. 費用（gpt-6.1-sol；依 `sim/openai_eval.py` PRICES 估算，以帳單為準）

- 本報告用到的呼叫合計 US$1.5767（1111 次，平均 US$0.00142）；快取檔累計實際花費（含估算用試跑、失敗呼叫）US$1.5767；上限 US$12.00。

## 5. 若有 D-50 複誦確認：phone 條件紅旗題抽錯的句子會不會觸發複誦（估算）

對 phone 條件每一輪紅旗題抽錯（漏抽、抽錯、多抽）的句子，以 `confirm.needs_confirm(題目, 抽到的值, hyp_tw)` 判斷是否觸發複誦（句首判定 `leading_yes_no`）。只估算觸發，不模擬複誦回答，也不含「寫入後即 Hard stop 不複誦」；重放邏輯不變。範圍只含紅旗題，未含 D-50 範圍內的關鍵題（`stt_critical_questions`：Q-CHARACTER-01、Q-REST-02）。值為「有」（最嚴重一級）的多抽依設計不複誦（安全方向）。

| 抽取器 | 抽錯 輪（句） | 會觸發複誦 輪（句） | 其中答「有」被漏抽 輪（句） | 「有」被漏抽且會觸發 輪（句） |
|---|---|---|---|---|
| keyword | 251（162） | 240（151） | 10（10） | 10（10） |
| gpt-6.1-sol | 2（2） | 2（2） | 0（0） | 0（0） |
| gemma-4-26b-a4b-it-mlx | 64（57） | 24（22） | 0（0） | 0（0） |
- keyword 不會觸發的：S-STABLE-01#t2 Q-SYNCOPE-01 正確 False／抽出 True「不會耶,從來沒有快要昏老貨眼前發黑的感覺。」；S-STABLE-01#1#t2 Q-SYNCOPE-01 正確 False／抽出 True「不會耶,沒有快要昏老貨眼前發黑的感覺」；S-STABLE-02#1#t2 Q-SYNCOPE-01 正確 False／抽出 True「不會,沒有那種快要昏老後眼前發黑的感覺。」；S-INSUF-01#1#t2 Q-SYNCOPE-01 正確 False／抽出 True「不會噎,沒有那種快要昏倒或眼前發黑的感覺。」；S-INSUF-05#1#t2 Q-SYNCOPE-01 正確 False／抽出 True「不會也,沒有那種快昏老貨眼前發黑的感覺」；S-MID-04#t3 Q-SYNCOPE-01 正確 False／抽出 True「沒有耶,我都沒有覺得快婚老貨眼前發黑。」；S-MID-08#2#t2 Q-SYNCOPE-01 正確 False／抽出 True「沒有耶,不會有藥昏倒或眼前發黑的感覺。」；S-MID-15#0#t5 Q-SYNCOPE-01 正確 False／抽出 True「沒有夜,不會有快要昏倒或眼前發黑的感覺。」；S-MID-17#0#t5 Q-SYNCOPE-01 正確 False／抽出 True「沒有,他沒有說快要跟老婆眼前發黑」；S-MID-19#3#t2 Q-SYNCOPE-01 正確 False／抽出 True「不會,沒有快要昏倒過眼前發黑的感覺。」；S-MID-20#t3 Q-SYNCOPE-01 正確 False／抽出 True「沒有夜,從來沒有快要昏倒或眼前發黑過。」
- gemma-4-26b-a4b-it-mlx 不會觸發的：S-ACUTE-02#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,現在坐著休息就沒有不舒服。」；S-ACUTE-04#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,已經好了,現在沒有不舒服。」；S-STABLE-01#t1 Q-ONGOING-01 正確 False／抽出 True「沒有,現在沒有不舒服,都好好的。」；S-STABLE-01#1#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有喔現在胸口不會悶」；S-STABLE-01#2#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有,現在胸口不會扔了。」；S-INSUF-01#0#t3 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,這個端像是還好。」；S-INSUF-02#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,這個單下胸口沒有不舒服。」；S-INSUF-02#0#t3 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,這個端效不會不舒服。」；S-INSUF-02#1#t3 Q-ONGOING-01 正確 False／抽出 True「現在沒有 現在還好 沒有在悶」；S-INSUF-03#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,現在胸口不會悶。」；S-INSUF-03#0#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有,現在胸口不會扔了。」；S-INSUF-03#1#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了現在不會悶」；S-INSUF-04#t2 Q-DYSPNEA-SENTENCE-01 正確 False／抽出 True「不會啦,現在講話還好,一句話講得完。」；S-INSUF-04#1#t2 Q-DYSPNEA-SENTENCE-01 正確 False／抽出 True「不會啦,現在講話還好,一句話可以講完。」；S-INSUF-04#2#t2 Q-DYSPNEA-SENTENCE-01 正確 False／抽出 True「不會啦,我現在講話都很正常,不會喘到講不完。」；S-INSUF-05#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,現在坐著休息胸口不會悶。」；S-INSUF-05#0#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,我現在坐著休息,胸口不會悶。」；S-INSUF-05#1#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了現在坐著都還好沒有悶」；S-INSUF-06#0#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,現在不會不舒服。」；S-INSUF-06#1#t3 Q-ONGOING-01 正確 False／抽出 True「現在沒有了現在還好沒有不舒服」；S-INSUF-08#0#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有,現在胸口沒有悶悶的感覺。」；S-MID-04#0#t4 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,這個端效不會不舒服。」；S-MID-06#1#t1 Q-DYSPNEA-SENTENCE-01 正確 False／抽出 True「不會啦,我現在坐著講話都還好,不會喘到講不完。」；S-MID-07#t1 Q-ONGOING-01 正確 False／抽出 True「沒有,現在沒有不舒服,都是走路走比較快的時候才會悶,停下來就好了。」；S-MID-07#2#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有,現在胸口不會扔了。」；S-MID-08#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有我,我現在做住卷煉貨,胸口不會扔。」；S-MID-08#0#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,我現在坐住休息,胸口沒有悶。」；S-MID-08#2#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,現在做助家還好,是走路的時候才會生。」；S-MID-10#0#t4 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,這個單下胸口沒有不舒服。」；S-MID-11#t2 Q-DYSPNEA-SENTENCE-01 正確 False／抽出 True「不會啦,現在講話都還好,不會喘到講不完。」；S-MID-12#t1 Q-DYSPNEA-SENTENCE-01 正確 False／抽出 True「不會了,講話還好,不會傳到講不完。」；S-MID-14#t1 Q-ONGOING-01 正確 False／抽出 True「現在這個段下沒有不舒服,胸口還好。」；S-MID-14#0#t1 Q-ONGOING-01 正確 False／抽出 True「現在這個時候沒有再痛了是沒有不舒服的」；S-MID-15#0#t4 Q-ONGOING-01 正確 False／抽出 True「現在的油窩,胸口這時候不會不舒服。」；S-MID-16#t1 Q-ONGOING-01 正確 False／抽出 True「現在的有贊通現在的可就還好」；S-MID-16#0#t1 Q-ONGOING-01 正確 False／抽出 True「現在沒有現在沒在咳就不會痛」；S-MID-17#0#t4 Q-ONGOING-01 正確 False／抽出 True「現在沒有了,他現在沒有不舒服。」；S-MID-19#t1 Q-ONGOING-01 正確 False／抽出 True「現在的油,胸口現在不會扔。」；S-MID-19#0#t1 Q-ONGOING-01 正確 False／抽出 True「現在的油,胸口沒在燈了。」；S-MID-19#3#t1 Q-ONGOING-01 正確 False／抽出 True「現在的油,胸口現在不會扔。」

## 6. 重現

```
# 費用估算（前 3 個 case）
zsh -ic 'cd ~/Documents/GitHub/acs_triage && uv run python -m sim.e2e_llm --limit 3 --extractors keyword,gpt --cache-dir <scratch> --out <scratch>'
# 全量（LM Studio 需先 lms load gemma-4-26b-a4b-it-mlx）
zsh -ic 'cd ~/Documents/GitHub/acs_triage && uv run python -m sim.e2e_llm --cache-dir <scratch>'
```
關鍵詞抽取器的既有重放：`python -m sim.extractor_e2e --extractor keyword [--asked-only]`（extract_fn 介面擴充後輸出不變）。
