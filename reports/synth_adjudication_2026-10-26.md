# Clinical Owner 裁定表 — 實驗 1 合成病人驗證集（2026-10-26）

- 收錄：兩位 LLM 標註者（Opus 5.5、gpt-6.1-sol）tier 或 Hard stop 不一致，或系統任一層（(a) 全資訊規則、(b) Scripted 病人、(c) Opus LLM 病人）比任一位標註者不急的案例。
- 標註者的分級只是 LLM 臨床判斷，不是 truth；請在每例最後的「Clinical Owner 裁定」填寫。同內容的試算表：同名 .xlsx。
- 全為虛構合成資料。

共 48 例。

## SYN-093（arrhythmia_syncope／elderly_slow）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「小姐喔，我八十一了，講慢一點齁……前天還是再前一天，我坐在桌邊吃稀飯，後面就不知道了。阮老伴說我頭垂下去，叫也沒應，醒來他就在旁邊拍我，說我有昏去。多久我實在不知道，現在人是好好的啦，可是這樣我會驚。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：over_24h（更早以前）
- nausea（有沒有想吐、噁心？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：true
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0 Hard stop（RF-05），信心 medium——81歲，2–3天前坐著進食時有人目擊的真正意識喪失：頭垂下、叫不應，屬首次發生，且無前驅症狀與姿勢性因素。高齡、靜坐時無預警昏厥屬高風險，須懷疑心律不整，符合RF-05。雖然目前已恢復、無再發且無胸痛與喘，仍應立即送急診評估。
- gpt-6.1-sol：T0 Hard stop（RF-05），信心 high——81歲首次於坐姿休息時真正失去意識，家屬目擊呼喚無反應，符合RF-05。即使已恢復、超過24小時且未再發作，仍須立即啟動EMS／急診評估，不應延誤於補問。
- 系統：(a) T0 Hard stop（RF-05）；(b) T9（備援 T3）（10 題，no_more_questions）；(c) T9（備援 T3）（10 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-105（arrhythmia_syncope／general）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我三十六歲，前天晚上打羽球，正在接球時突然倒下，隊友說我有四十秒左右完全沒反應。我醒來才知道發生什麼事，倒下前沒有頭暈或其他預兆，這兩天也沒再發生；想請問這件事要怎麼處理。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：0.67
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：over_24h（更早以前）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0.29
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：true
- third_party_call：false
```

- Opus 5.5：T0 Hard stop（RF-05），信心 medium——36歲於劇烈運動中突然倒下，無前驅症狀，約40秒完全無反應，屬真正意識喪失，符合RF-05。運動中無預兆暈厥是心因性猝死（心律不整、結構性心臟病）的高危表現，雖已過兩天且未再發，仍不得下修，應立即啟動急診評估。
- gpt-6.1-sol：T0 Hard stop（RF-05），信心 high——運動中無預兆突然倒下，確有約40秒意識喪失，屬高風險心因性暈厥情境，命中RF-05。即使已恢復且兩天未再發作，仍須立即啟動EMS／急診評估，不應延誤。
- 系統：(a) T0 Hard stop（RF-05）；(b) T9（備援 T3）（9 題，no_more_questions）；(c) T9（備援 T3）（9 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-096（arrhythmia_syncope／family_proxy）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我陪我媽在眼科等叫號，她坐著坐著突然抓住我的手，說眼睛黑掉、整個人快倒下去。她有一直回答我，沒有昏掉，現在比較好了，我們還在一起。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：true
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：true
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：4
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：true
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：true
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：true
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——母親靜坐時新發心悸，合併瀕厥（眼前發黑、快倒下）與冒冷汗，持續約4分鐘，今日首次發作，需懷疑心律不整，宜立即至急診評估。目前已緩解、無胸部不適、未失去意識、休息時不喘，未符合RF-01/03/05/06，故不啟動Hard stop。人在醫院，可直接轉急診。
- gpt-6.1-sol：T0，信心 high——首次在坐姿休息時突發心悸、眼前發黑及瀕厥，伴冷汗，需急診排除高風險心律不整。雖已緩解且未失去意識，仍不宜延後；無胸部不適、缺血等價症狀或靜止喘，未命中紅旗。
- 系統：(a) T0；(b) T3（6 題，gate_passed）；(c) T3（6 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-100（arrhythmia_syncope／elderly_slow）

- 列入原因：標註者不一致；系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「喂，歹勢，我七十八歲，耳朵比較重，妳慢慢講齁。早起在陽台夾那個衣服，眼前突然暗暗的，腳就軟了，我扶著牆，差一點、差一點就倒下去。人是有清醒啦，現在坐在屋內，已經沒有那樣了。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：true
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：1
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：unclear（不太清楚）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：true
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：unknown（不記得）
```

- Opus 5.5：T0，信心 medium——78歲，冠心症且放過支架，今日站立做事時突發眼前發黑、腿軟、冒冷汗，之後又再發作。非姿勢性，現已緩解，意識清楚。因無胸部或缺血等價症狀，不符RF-01或RF-06；但高齡CAD病人反覆瀕厥合併冒汗，需排除心律不整或缺血，建議急診評估。
- gpt-6.1-sol：T1，信心 high——78歲、有冠心症及支架史，今日反覆瀕厥並冒冷汗，非典型姿勢性頭暈，須當日評估心律與血流動力問題。目前已緩解，無胸部不適、呼吸困難或真正失去意識；單獨冒汗不構成紅旗。
- 系統：(a) T9（備援 T3）；(b) T9（備援 T3）（11 題，max_questions）；(c) T9（備援 T3）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-112（noncardiac_chest／general）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我五十歲，晚餐吃得比較晚，收完碗坐下來，胸口正中間就有一股灼熱往上跑，嘴巴還有酸味。大約十五分鐘，接連打嗝後就完全不燒了；這個月已經第三次，想請教要不要檢查。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：15
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：3
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pattern_unchanged_duration_months（這個情況維持一樣、完全沒有變嚴重，大概多久了？）：0.75
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：true
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：other（其他）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——50歲，三週前新發胸骨後灼熱，皆於休息時出現（首次休息發作），本月三次，每次約15分鐘，今日剛發作。雖餐後、酸味、打嗝緩解像胃食道逆流，但依原則不因非典型特徵降級；新發休息時胸部不適需緊急評估。目前未持續、無暈厥冒汗喘，故不啟動Hard stop。
- gpt-6.1-sol：T0，信心 high——近三週新發且反覆於休息時出現胸口灼熱，今日再發、持續15分鐘，需立即急診評估。雖有餐後酸味及打嗝後緩解，仍不能排除心肌缺血；目前已完全緩解，無其他紅旗，故不觸發Hard stop。
- 系統：(a) T0；(b) T9（備援 T3）（9 題，no_more_questions）；(c) T9（備援 T3）（9 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-116（noncardiac_chest／anxious_exaggerating）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「天啊，我剛剛胸口燒得像吞到火，是不是出大事了！下午公司慶生，我蛋糕、奶茶吃了一堆，後來連打幾個嗝，現在是不燒了，可是我嚇到一直不敢動。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：7
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：true
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：other（其他）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——今日首次發作、休息時出現的胸口灼熱，持續約7分鐘，目前已緩解。無暈厥、瀕厥、冒汗或休息時喘，未命中紅旗。雖然發生在飯後、打嗝後緩解，較像胃食道逆流，但依原則，新發的休息時胸部不適不能因疑似腸胃原因而降級，仍建議急診評估。
- gpt-6.1-sol：T0，信心 high——今日首次出現休息時胸口灼熱，持續7分鐘；雖餐後發生且打嗝後完全緩解，仍不能據此排除心肌缺血，應立即急診評估。目前無持續不適、喘、冷汗或暈厥，未命中紅旗。
- 系統：(a) T0；(b) T9（備援 T3）（9 題，no_more_questions）；(c) T9（備援 T3）（9 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-081（heart_failure／anxious_exaggerating）

- 列入原因：標註者不一致；系統(a)比gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我是不是快不行了啊，連把衣服從洗衣機拿去晾，都喘得像跑完操場！本來還能自己去市場，這三個禮拜越來越差，現在在家走來走去也要停下來，怎麼會變這樣？」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：true
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：exertional_daily（平常走路做家事就會）
- edema（腳有沒有腫？）：true
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：6
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：12
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：weeks_to_month（這幾個禮拜慢慢變的）
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：true
```

- Opus 5.5：T1，信心 medium——約12週前開始喘，近3週活動閾值明顯下降，日常家務即喘並合併腳腫，疑似心衰竭惡化或缺血等價症狀加重。無休息喘、端坐呼吸或夜間喘醒，無胸痛、暈厥、冷汗，說話完整，目前未持續發作，未命中紅旗。但為進行性惡化，需當日評估。
- gpt-6.1-sol：T0，信心 high——近三週呼吸困難明顯惡化、活動閾值下降，現日常走動即喘且合併腳腫，須立即急診評估心衰竭或缺血等可能。目前休息無症狀，無端坐呼吸、暈厥或其他紅旗，故不觸發 Hard stop。
- 系統：(a) T1；(b) T2（6 題，gate_passed）；(c) T2（6 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-086（heart_failure／elderly_slow）

- 列入原因：標註者不一致；系統(a)比gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我七十九歲啦，最近拖個地，拖不到房門就得坐下來歇，呼吸很趕齁。原本還能陪老伴繞公園，現在從客廳走去後陽台就喘……不是一天突然這樣，是慢慢變的。胸口倒沒有痛，你問慢一點，我想一下喔。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：true
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：exertional_daily（平常走路做家事就會）
- edema（腳有沒有腫？）：true
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：8
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：weeks_to_month（這幾個禮拜慢慢變的）
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：true
```

- Opus 5.5：T1，信心 medium——79歲，無心臟病史，近幾週新發且漸進惡化的日常活動性呼吸困難，活動閾值下降，合併腳腫，疑新發心衰竭或缺血等價症狀。休息時不喘，無端坐呼吸/PND，無胸痛、暈厥、冒汗，講話可成句，未命中紅旗。屬亞急性惡化，不宜等門診，建議當日就醫評估。
- gpt-6.1-sol：T0，信心 high——新發且逐漸惡化的活動性呼吸困難，活動閾值明顯下降並合併腳腫，需立即急診評估心衰竭或缺血等可能；無胸痛不降低急迫度。目前無休息喘、持續症狀或其他紅旗，故不觸發 Hard stop。
- 系統：(a) T1；(b) T2（6 題，gate_passed）；(c) T2（6 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-129（atypical／minimizer）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「七十九歲了，體力差一點很正常吧，不用弄得太麻煩啦。只是原本還能繞公園，這三天連從房間走到大門都要停一下喘口氣，腿也覺得累；胸口可是一點都沒痛、沒悶喔。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：true
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：exertional_daily（平常走路做家事就會）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：6
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：3
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：days（這幾天）
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：true
```

- Opus 5.5：T0，信心 medium——79歲有冠心症病史，近3週新發勞力性喘（可視為缺血等價症狀），近幾天活動閾值明顯下降，從能繞公園退步到走到大門就要停下來，今天也再發作。這屬於漸進惡化型表現，依原則1應急診評估；不因沒有胸痛而降級。目前無休息時喘、無持續症狀、暈厥或冒汗，未命中紅旗，故無須Hard stop。
- gpt-6.1-sol：T0，信心 high——已知冠心症，近三週新發活動喘，這幾天活動閾值明顯下降，日常短距離行走即需停下，屬疑似缺血等價症狀惡化，應立即急診評估。現已緩解，無休息喘、暈厥或冒汗，未命中紅旗。
- 系統：(a) T0；(b) T2（6 題，gate_passed）；(c) T2（6 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-006（acs_today／unclear）

- 列入原因：標註者不一致；系統(a)比Opus 5.5不急；系統(b)比Opus 5.5不急；系統(c)比Opus 5.5不急
- 開場白：「那個，我今天胸前有一陣很不對勁，悶還是痛，我也不會講，連左邊手臂裡面都怪怪的。什麼時候開始我沒看鐘啦，現在好像退了，這樣是要問哪一科？」

事實清單：

```
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：unclear（不太清楚）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：vague（說不上來，就是怪怪的）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：unknown（不記得）
```

- Opus 5.5：T0，信心 medium——今日新發一陣胸悶或胸痛，合併左臂內側不適，屬疑似缺血等價表現；症狀不受按壓、咳嗽或進食影響，與用力的關係不明，依原則1需急診評估。目前症狀已緩解，無暈厥、休息時喘或說話喘，也無冒汗資料，未命中紅旗，因此不啟動 Hard stop，但仍應盡速前往急診。
- gpt-6.1-sol：T9，信心 high——今日曾有胸前及左臂不適，目前已緩解，未命中紅旗。尚不清楚是否新發、近期惡化或長期固定，亦缺發作持續時間，無法安全定級；需轉護理師釐清，不可因症狀已退而降級。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-028（unstable／general）

- 列入原因：標註者不一致；系統(a)比gpt-6.1-sol不急；系統(b)比gpt-6.1-sol不急；系統(c)比gpt-6.1-sol不急
- 開場白：「我五十六歲，平常有騎腳踏車，之前只有踩很吃力的路段胸前才會緊。這四個星期一點一點變差，現在把洗好的衣服拿去陽台晾，就會緊、會喘，得放下來歇個幾分鐘。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：true
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：exertional_daily（平常走路做家事就會）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：6
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：156
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：weeks_to_month（這幾個禮拜慢慢變的）
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：true
```

- Opus 5.5：T1，信心 medium——三年穩定型運動性胸悶，近四週活動閾值逐步下降，現在日常家務即胸悶、喘（CCS III），符合漸進性不穩定心絞痛，今日仍有發作。無休息時症狀，來電時未發作，無冒汗、暈厥或瀕厥，未命中紅旗。惡化屬數週漸進而非數天急遽，判當日評估；若轉為休息時發作或持續不緩解，應立即叫救護車。
- gpt-6.1-sol：T0，信心 high——已知冠心症，近四週胸悶與喘逐漸惡化，活動閾值由劇烈運動降至晾衣等日常活動，今日仍有發作，需立即急診評估。當下症狀已緩解，無休息喘、暈厥或冒冷汗，未命中紅旗。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-030（unstable／elderly_slow）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「歹勢喔，我八十一了，講慢一點……我那罐放舌頭下面的藥，怎麼這陣子用得很快。以前隔很久才拿一顆，現在一個禮拜要拿四、五回，都是去廟口那段路胸坎悶才含的，藥師說叫我打來講一下。今早也拿了一顆，現在是沒有悶了啦。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：8
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：true
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——81歲、冠心症曾放支架，舌下硝化甘油用量由偶爾一顆增至每週四、五次，屬心絞痛發作頻率明顯惡化（crescendo）。依原則1與5，不因硝化甘油有效或目前已緩解而降級，建議急診評估。現無持續胸悶、休息時症狀、暈厥、冒汗或喘，未命中紅旗，故不啟動Hard stop。
- gpt-6.1-sol：T0，信心 high——已知冠心症及支架史，近期活動性胸悶反覆、舌下含片需求明顯增加，屬心絞痛模式惡化，需立即急診評估。雖今日症狀已緩解且無休息發作，仍不可降級；目前未命中紅旗。
- 系統：(a) T0；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-033（unstable／family_proxy）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我媽七十六歲，我今天陪她住，她可以跟你們講。這一個多月看她越來越不對勁，原本推整車菜回來才說胸前緊，現在光在廚房端幾盤菜就說緊、會喘，昨天晚餐又只好換我弄。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：true
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：exertional_daily（平常走路做家事就會）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：8
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：104
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：18
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：same（差不多）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：true
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：weeks_to_month（這幾個禮拜慢慢變的）
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：true
```

- Opus 5.5：T0，信心 medium——76歲女性，有冠心症且18個月前放過支架。原本穩定的胸悶近一個月活動閾值明顯下降，從推菜車才發作變成端幾盤菜就胸悶、喘，屬漸強型心絞痛。依原則1，活動閾值下降需緊急評估，不因病程漸進或已知CAD而降級。目前無持續症狀、無休息時症狀，也無暈厥、冒汗、靜止喘等紅旗，故判T0但非Hard stop。
- gpt-6.1-sol：T0，信心 high——已知冠心症及支架史，近幾週至一個月胸悶活動閾值明顯下降，日常家事即胸緊、喘，昨仍發作，應立即急診評估。現無持續胸悶、休息喘、暈厥或冒汗，未命中紅旗。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-035（unstable／general）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我有把胸悶跟含藥的時間記在手機裡，這週已經有兩次，含第一顆後還沒完全退，後來又用到第二顆，以前一顆就夠了。最近送孫子走同一段路，胸口也比以前常悶，昨天那回拖了十八分鐘，今天目前沒有。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：18
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：true
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：true
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：156
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：60
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：same（差不多）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——已知冠心症、曾放支架，原有穩定型心絞痛近期明顯惡化：發作變頻繁、需含兩顆舌下含片（以前一顆即可）、昨天一次持續18分鐘且伴噁心，屬漸強型心絞痛。依原則1與原則5，症狀明顯惡化需急診評估，不因目前無症狀或含片有效而降級。目前未持續發作，也無休息時症狀、暈厥、冒汗或休息喘，未命中紅旗，故不啟動hard stop。
- gpt-6.1-sol：T0，信心 high——已知冠心症及支架病史，近期同等活動下胸悶更頻繁、硝酸甘油需求增加，昨次持續18分鐘且伴噁心，屬心絞痛惡化，需立即急診評估。目前無症狀，亦無所列紅旗，故不觸發Hard stop。
- 系統：(a) T0；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-036（unstable／general）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我在做修改衣服的，之前偶爾出去送件才胸口悶，這五天連一天跑的幾趟都會碰到。以前三分鐘左右就散了，現在得停十二、十五分鐘，今天上午已經三次了，最後一次是半小時前好的。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：15
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：40
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 high——已知冠心病，原本偶發勞力性胸悶，近五天發作變頻繁、每次持續由約3分鐘延長至12–15分鐘，今日上午已發作三次，屬漸強型（crescendo）惡化，依原則1需緊急評估。來電時症狀已緩解，且無暈厥、瀕厥、冒汗或休息時喘，未命中紅旗，故不啟動hard stop。
- gpt-6.1-sol：T0，信心 high——已知冠心症，近五天胸悶發作明顯變頻繁，持續由約3分鐘延長至15分鐘，今晨已三次，屬近期惡化，須立即急診評估。目前已緩解，無休息喘、暈厥或冒冷汗，未命中紅旗。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-040（unstable／family_proxy）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我陪我媽在陶藝教室，她現在坐我旁邊，可以自己講。她叫我幫忙拿舌下藥，我才看到她記的小本子，過去兩個月才用一次，這禮拜已經用五次了，都是搬陶土時胸前緊。今天這次也含了一顆，歇了十一分鐘才完全好，我想替她問問這個變化。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：11
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：true
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：260
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：48
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：same（差不多）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：true
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——已知冠心症、曾放支架，原本穩定型心絞痛，但舌下含片用量由兩個月一次增至本週五次，屬明顯惡化（漸增型）。今日發作歇11分鐘才緩解。目前無持續症狀、無休息痛、無暈厥、冒汗或喘，未命中紅旗，但依原則1應急診評估，不因含片有效而降級。
- gpt-6.1-sol：T0，信心 high——已知冠心症及支架病史，近期活動性胸悶頻率與舌下藥使用明顯增加，今日發作持續11分鐘，屬症狀惡化，須立即急診評估。現已完全緩解，無休息喘、暈厥或冒汗，未命中紅旗。
- 系統：(a) T0；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-041（unstable／unclear）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我也不知道要怎麼說，胸口就卡卡悶悶的，最近老是來。以前一下就散掉，這幾天等很久還在，一天又來好幾輪……到底哪時開始變這樣，我也沒記。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- dyspnea_complaint：false
- edema（腳有沒有腫？）：false
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：unclear（不太清楚）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
```

- Opus 5.5：T0，信心 medium——已知冠心症病人，胸悶並非新發，但近幾天明顯惡化：每次持續時間變長、一天發作好幾輪，今天仍有發作，屬漸強型（crescendo）缺血症狀，依原則1需緊急評估。目前無持續症狀、無暈厥、無冒汗、無靜止喘，未命中紅旗，故不列 Hard stop。
- gpt-6.1-sol：T0，信心 high——已知冠心症，胸悶近期發作時間延長且一天反覆多次，最後發作於今日，屬明顯惡化的疑似缺血症狀，需立即急診評估。當下已緩解，未有足以觸發紅旗的資訊，故不啟動 Hard stop。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-043（unstable／general）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我在倉庫管出貨，胸前那種被束住的感覺，現在連拉空的推車都會出現。六個星期前還要扛整袋飼料才有，後來搬小紙箱也不行，是一點一點變的，不是哪天突然這樣。昨天停了兩次工作等它退，想問這個變化。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：exertional_daily（平常走路做家事就會）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：7
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：78
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：weeks_to_month（這幾個禮拜慢慢變的）
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：true
```

- Opus 5.5：T0，信心 medium——已知冠心症，原本穩定的胸悶，近六週活動閾值逐步下降，現在拉空推車即發作（漸進型心絞痛），最近一次在24小時內。目前無持續症狀、休息時發作、暈厥、冒汗或休息喘，未命中紅旗。依原則1，活動閾值下降屬不穩定表現，雖為漸進變化仍不下修，建議急診評估。
- gpt-6.1-sol：T0，信心 high——已知冠心症，胸悶反覆且近數週活動閾值持續下降，輕微活動即誘發，屬惡化型缺血症狀，應立即急診評估；漸進變化不降低急迫性。目前無持續胸悶、休息喘、暈厥或冒冷汗，未命中紅旗。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-044（unstable／elderly_slow）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「喂，聽得到喔……我七十九啦，讓我慢慢講。昨天坐在藤椅上拆毛線，手也沒怎麼動，胸坎就重重的，好像有東西頂住；前幾天也是坐著等吃飯就來了。以前喔，要在院子挖土、弄那個花盆才會，坐著不曾這樣，這是最近才有的。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：both（走路會，休息也會）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：true
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：pressure（像被壓住）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：same（差不多）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 high——79歲，有冠心症與支架史。原本只在勞動時胸悶，最近首次出現休息時壓迫感，且反覆發作、伴噁心，最後一次在昨天，屬不穩定型心絞痛型態，需急診評估。來電當下無症狀，也無暈厥、冷汗或休息時喘，未命中紅旗，故不啟動Hard stop。
- gpt-6.1-sol：T0，信心 high——已知冠心症及支架史，原為活動時胸部壓迫，近期新增休息時反覆發作，最近一次於昨日，合併噁心，需立即急診評估。現無持續胸悶、休息喘、暈厥或冒汗，未命中紅旗。
- 系統：(a) T0；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-063（post_pci／general）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我五十五歲，支架放完兩個月了，這兩週騎腳踏車接小孩，才騎一小段，上腹就像塞住一樣，還會喘、想吐。手術以前要騎很遠才這樣，而且沒現在這麼難受；今天這次停車休息了二十五分鐘才完全退掉。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：true
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：exertional_daily（平常走路做家事就會）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：25
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：true
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：2
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：2
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：epigastric（上腹悶脹）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：worse（比較重）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：weeks_to_month（這幾個禮拜慢慢變的）
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：true
```

- Opus 5.5：T0，信心 high——支架術後2個月，近2週出現缺血等價症狀（上腹悶脹合併喘、噁心），活動閾值明顯下降、比術前更嚴重，今日發作持續25分鐘才緩解，屬明顯惡化型，需考慮支架再狹窄或血栓，應立即急診評估。目前症狀已緩解，無暈厥、冒汗或靜止時喘，未命中紅旗，故不列Hard stop。
- gpt-6.1-sol：T0，信心 high——近兩週上腹悶脹合併喘、噁心，較支架前加重且活動閾值下降；今日發作休息25分鐘才緩解，屬惡化缺血等價症狀，需立即急診評估。目前已緩解，無靜止喘、暈厥或冒汗，未命中紅旗。
- 系統：(a) T1；(b) T1（11 題，gate_passed）；(c) T1（11 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-067（post_pci／anxious_exaggerating）

- 列入原因：標註者不一致；系統(a)比gpt-6.1-sol不急；系統(b)比gpt-6.1-sol不急；系統(c)比gpt-6.1-sol不急
- 開場白：「完了完了，我是不是又要出事了！早上還躺在被窩，下巴連到肩頭忽然沉沉的，八分鐘才退；其實比裝支架以前輕，可是我現在怕得不敢動，裝了九個月怎麼還會這樣？」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：8
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：44
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：9
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：jaw_shoulder_heaviness（下顎和肩膀沉重）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：milder（比較輕）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T1，信心 medium——支架術後9個月，今晨休息時出現下顎至肩膀沉重8分鐘，屬缺血等價症狀。目前已緩解，無暈厥、冒汗或休息時喘，未命中紅旗。病人表示休息發作非新發、活動閾值未下降，但術後再現休息時症狀，不符合常規門診條件，應當日評估。
- gpt-6.1-sol：T0，信心 high——已知冠心症及支架病史，今日休息時出現下顎至肩部沉重，持續8分鐘，屬疑似缺血等價症狀，應立即急診評估；即使較術前輕、非首次發作也不能排除風險。目前已緩解，無喘、暈厥或冒汗，未命中紅旗。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-068（post_pci／family_proxy）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我幫七十三歲的媽媽問，她六年前有裝心臟支架，本來都能自己顧花。這兩個禮拜一提水壺在陽台澆花，就說胸前緊緊的，要把水壺擱下來歇一下，昨天傍晚也有；她坐我旁邊，可以自己跟你說。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：5
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：2
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pattern_unchanged_duration_months（這個情況維持一樣、完全沒有變嚴重，大概多久了？）：0.5
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：72
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：same（差不多）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：true
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——73歲，6年前置放支架，原本澆花無症狀，近2週再度出現用力時胸悶，休息可緩解，最後一次在昨天。雖與置放支架前相似，但屬多年無症狀後近期新發的勞力型心絞痛，型態僅穩定2週，不符長期穩定。依原則1宜緊急評估；目前無持續症狀、暈厥、冒汗或休息時喘，未命中紅旗。
- gpt-6.1-sol：T0，信心 high——近兩週反覆活動性胸悶，與支架前症狀相似，最近一次在昨日；僅半月模式固定，不足視為長期穩定，應立即急診評估。目前無持續胸悶、休息喘、暈厥或冒冷汗，未命中紅旗。
- 系統：(a) T9（備援 T1）；(b) T1（8 題，gate_passed）；(c) T1（8 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-071（post_pci／general）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我六十二歲，五個月前做了心臟支架，之後有一段時間都很順。最近去社區上書法課，爬到三樓胸前就像壓了一本厚書，感覺跟手術前差不多；今天也是到教室坐了六分鐘才消掉。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：6
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：2
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pattern_unchanged_duration_months（這個情況維持一樣、完全沒有變嚴重，大概多久了？）：0.5
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：5
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：pressure（像被壓住）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：same（差不多）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——支架術後5個月，原本無症狀，2週前再度出現與術前相同的勞力性壓迫感，今日又發作6分鐘。這屬術後新發復發心絞痛（疑支架再狹窄），依原則1應緊急評估。目前症狀已緩解，無休息痛、暈厥、冒汗或靜止喘，未命中紅旗，故不啟動hard stop。
- gpt-6.1-sol：T0，信心 high——支架術後曾無症狀，近兩週再發活動性胸部壓迫，與術前相似且今日仍曾發作，屬近期復發而非長期穩定，需立即急診評估。目前已緩解，無暈厥、冒汗或靜止喘，未命中紅旗。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-072（post_pci／elderly_slow）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「喂，讓我慢慢講喔，我七十九了……支架是八年前裝的，這個我記得。最近晚上睡一睡，胸坎會悶醒，坐到床沿一陣子才散掉，以前裝之前也有這樣啦。哪一晚開始的喔，我就記不清，反正這幾個禮拜才又有。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：10
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：unknown（不記得）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：96
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：tightness（悶悶的）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：same（差不多）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
```

- Opus 5.5：T0，信心 medium——79歲，八年前放支架。近幾週夜間休息時反覆胸悶悶醒，每次約10分鐘，性質與放支架前相同，屬術後多年再度出現的休息型心絞痛，提示病情不穩定，依原則1應緊急評估。來電時已無症狀，也沒有暈厥、冒汗或靜止喘，未命中紅旗，因此不啟動Hard stop。最後一次發作時間不明。
- gpt-6.1-sol：T0，信心 high——近幾週再度反覆於夜間休息時胸悶，約持續10分鐘，與支架前相似，並非已確認長期穩定的症狀，需立即急診評估。目前無持續胸悶、喘、暈厥或冒汗，未命中紅旗。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-121（atypical／elderly_slow）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「小姐喔，我八十四了，這陣子擦個飯桌、收個碗，就要坐下來歇，氣不太夠啦。胸坎沒有痛，也沒有悶，就是人沒什麼力。剛剛又喘了一陣，現在坐著有比較順……這樣也要看心臟科嗎？」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：true
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：exertional_daily（平常走路做家事就會）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：8
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：2
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：weeks_to_month（這幾個禮拜慢慢變的）
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：true
```

- Opus 5.5：T0，信心 medium——84歲，兩週前新發勞力性喘，數週內活動閾值下降至擦桌收碗即喘，今日又發作8分鐘，屬高齡者新發且漸進惡化的缺血等價症狀；無胸痛不得降級。目前已緩解、靜止不喘、無暈厥冷汗，未中紅旗，但應急診評估。
- gpt-6.1-sol：T0，信心 high——84歲，近兩週新發且反覆日常活動即喘，活動閾值下降，今日再發；須視為可能缺血等價症狀，立即急診評估。現已緩解，無休息喘、暈厥或其他紅旗，不觸發Hard stop。
- 系統：(a) T1；(b) T0（2 題，gate_passed）；(c) T0（2 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-131（atypical／family_proxy）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我媽六十四歲，昨天從圖書館走去搭公車，走到一半說下巴痠，背也痛，兩個肩膀沉沉的，後來在站牌坐一會兒才退。她說胸口沒事，就沒跟我們講，剛剛我才知道；她現在在我旁邊，可以自己回答。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：12
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：true
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0.14
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：jaw_shoulder_heaviness（下顎和肩膀沉重）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：true
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——64歲女性，昨日（24小時內）首次出現走路時下顎痠、背痛、雙肩沉重，伴噁心，持續12分鐘，休息後緩解，屬新發缺血等價症狀。目前無持續症狀，無暈厥、瀕厥、冒汗或休息時喘，未命中紅旗，故不啟動Hard stop。依原則1，新發缺血等價症狀需緊急評估，不因無胸痛而降級。
- gpt-6.1-sol：T0，信心 high——64歲，24小時內新發活動誘發下顎、肩膀沉重及背痛，持續12分鐘並伴噁心，屬疑似缺血等價症狀，需立即急診評估。雖休息後緩解且目前無症狀，仍不可下修；無已確認紅旗。
- 系統：(a) T9（備援 T1）；(b) T0（4 題，gate_passed）；(c) T0（4 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-134（atypical／general）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我五十八歲，有糖尿病，這兩週騎腳踏車去市場，騎一段胃上方就脹悶，還會噁心，停在路邊大概八分鐘就退。昨天傍晚又一次，跟有沒有吃東西沒什麼關係，也不是胸口痛，所以想問這要看哪一科。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：8
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：true
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：2
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pattern_unchanged_duration_months（這個情況維持一樣、完全沒有變嚴重，大概多久了？）：0.5
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：epigastric（上腹悶脹）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T0，信心 medium——58歲糖尿病患者，兩週前新發、騎車用力時上腹悶脹合併噁心，休息約8分鐘緩解，昨日仍復發。屬新發缺血等價症狀，依原則1需緊急評估，不因非胸痛或症狀輕微而下修。目前未持續發作，無冒汗、暈厥、瀕厥或休息時症狀，未命中紅旗，故不啟動Hard stop。
- gpt-6.1-sol：T0，信心 high——58歲糖尿病患者，近兩週新發且反覆活動誘發上腹悶脹合併噁心，休息約8分鐘緩解，最近發作在24小時內，屬疑似缺血等價症狀，應立即急診評估。目前無持續症狀或其他紅旗，未達Hard stop。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-147（family_proxy／family_proxy）

- 列入原因：標註者不一致；系統(a)比Opus 5.5不急；系統(b)比Opus 5.5不急；系統(c)比Opus 5.5不急
- 開場白：「我媽七十六歲，早上跟廟裡的人搭車出去，傳語音說心跳亂亂的，有一下眼前黑掉。她手機後來就沒接，我人在台中，不曉得她現在怎樣，想先替她問一下。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：true
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- dyspnea_complaint：false
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：unclear（不太清楚）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：unknown（不記得）
- new_medication_recent（最近有沒有換藥或加新的藥？）：true
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：true
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：false
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：true
- third_party_call：true
```

- Opus 5.5：T0，信心 medium——76歲女性，心悸合併眼前發黑（瀕厥），近期新換藥，疑似心律不整，需急診評估。未述胸痛、未確認意識喪失，故未命中RF-01/05紅旗。但病人目前失聯、狀況不明，應立即設法聯繫同行廟友確認現況；若仍不適或聯絡不上則通報119。
- gpt-6.1-sol：T9，信心 high——家屬代述心悸合併眼前發黑，但病人無法聯繫，症狀是否持續、是否新發或惡化及有無真正昏厥均不明。未能確認紅旗，亦不能安全指定急迫度，須立即轉護理師協助確認現況。
- 系統：(a) T9（備援 T1）；(b) T9（備援 T1）（10 題，no_more_questions）；(c) T9（備援 T1）（10 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-066（post_pci／minimizer）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我只是問一下藥啦，不用緊張。上禮拜鼻血流了兩回，我想說阿斯匹靈先不要吃，停到今天第四天了；心臟那個支架裝三個月，現在人好好的，應該沒差吧？」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：true
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：medication_handling（想問藥怎麼吃）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：3
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T1，信心 medium——支架置放僅3個月，自行停用阿斯匹靈已4天，支架血栓風險高；目前無胸痛、喘、暈厥、冒汗等症狀，未命中紅旗。仍須當日由醫師評估是否立即恢復抗血小板藥並處理鼻出血，勿自行續停；並衛教若出現胸悶等症狀立即撥119。
- gpt-6.1-sol：T1，信心 high——支架置放僅3個月，因鼻血自行停用阿斯匹靈已4天，有支架血栓風險，須當日聯絡心臟科評估抗血小板用藥及出血處置。目前無胸部不適、呼吸困難或其他紅旗，不需立即啟動EMS。
- 系統：(a) T3；(b) T3（4 題，gate_passed）；(c) T3（4 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-074（post_pci／anxious_exaggerating）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「天啊，我是不是闖大禍了！後天要割背上的粉瘤，我怕流血，就自己把保栓通停了兩天，剛剛查網路越看越恐怖。我的支架才放六個星期，現在身體沒不舒服，可是這個藥接下來到底怎麼吃？」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：true
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：medication_handling（想問藥怎麼吃）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：1.5
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T1，信心 medium——支架僅放置6週，自行停用保栓通已2天，支架血栓風險高，屬高風險用藥中斷。目前無胸痛、無喘、無暈厥等紅旗，故不啟動Hard stop；但需當日聯絡心臟科醫師，處理是否立即恢復服藥及延後擇期粉瘤手術，並交代出現胸悶或冒汗立即撥119。
- gpt-6.1-sol：T1，信心 high——支架置放僅六週，自行停用保栓通兩天，早期抗血小板中斷有支架血栓風險；目前無症狀且未命中紅旗，應當日聯絡心臟科確認用藥及手術安排，不宜等到術前才處理。
- 系統：(a) T3；(b) T3（3 題，gate_passed）；(c) T3（3 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-078（heart_failure／general）

- 列入原因：標註者不一致；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我的鞋這幾天突然變得很難穿，兩隻腳踝腫到用手壓會留一個凹。每天早上都有量體重，十天從七十二變七十五公斤，吃的量沒變，想請你們幫我問一下這樣要怎麼辦。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：true
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：14400
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：both（走路會，休息也會）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：ongoing
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：true
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：1.43
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：18
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——新發雙側凹陷性水腫，10天體重增3公斤，有冠心症及支架病史，疑似新發或惡化的心衰竭液體滯留。無喘（含靜止時）、無端坐呼吸或PND、無暈厥或冒汗。症狀性質為「無」，持續的不適應為水腫而非胸痛，不符RF-03。建議24–72小時內評估；若出現喘或胸悶，需立即升級。
- gpt-6.1-sol：T1，信心 high——新發雙側凹陷性水腫，十天體重增加三公斤，疑有體液滯留，須當日評估心臟功能與腎功能。持續症狀為水腫，未描述胸痛或缺血等價症狀，亦無呼吸困難、端坐呼吸或暈厥，未命中紅旗。
- 系統：(a) T0；(b) T9（備援 T3）（9 題，no_more_questions）；(c) T9（備援 T3）（9 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-088（heart_failure／anxious_exaggerating）

- 列入原因：標註者不一致；系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「天啊，我的腳是不是要爆開了！本來腳背看得到筋，現在兩邊都鼓起來，連涼鞋帶子都扣不上。健身房同一台體重計，上週五六十一，今天六十四，我又沒有大吃，這樣是不是整個人都出問題了？」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：true
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：1
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——一週內新發雙側下肢水腫，體重增加約3公斤，需排除新發心衰竭、腎臟或肝臟等原因。目前無胸部不適、無呼吸困難、無端坐呼吸或夜間陣發性呼吸困難、無暈厥，也無冒汗或心悸，未命中紅旗。建議24–72小時內快速評估。若出現喘、躺平會喘或胸悶，應立即就醫。
- gpt-6.1-sol：T1，信心 high——一週內新發明顯雙側足部水腫，體重增加約3公斤，需當日評估是否有體液滯留及心、腎等病因。無胸部不適、呼吸困難、端坐呼吸或暈厥，未命中紅旗。
- 系統：(a) T9（備援 T3）；(b) T9（備援 T3）（9 題，no_more_questions）；(c) T9（備援 T3）（9 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-092（arrhythmia_syncope／general）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「昨晚九點多，我坐在浴室的小椅子洗澡，突然眼前整片暗掉，覺得人快撐不住，趕快叫太太進來。我沒有真的昏過去，可是身上都是冷汗，還有點想吐，大約三分鐘才緩過來。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：true
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：3
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：true
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0.14
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：true
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T1，信心 medium——昨晚坐著洗澡時首次出現瀕厥（眼前發黑），伴隨冷汗與噁心，持續約3分鐘後緩解，之後未再發作。否認胸悶或胸痛，因此不符合 RF-01 或 RF-06；目前無症狀，也沒有休息時呼吸困難。熱水澡誘發的血管迷走反應可能性高，但新發瀕厥合併冒汗，仍需排除心律不整或非典型缺血，建議當日就醫做心電圖等評估。若再發作、出現胸悶或昏倒，應立即撥打119。
- gpt-6.1-sol：T1，信心 high——新發靜坐時瀕厥，伴冷汗、噁心，約3分鐘後緩解，目前無症狀。無胸部不適、呼吸困難或真正意識喪失，未命中紅旗；仍須當日評估，排除心律不整等原因。
- 系統：(a) T0；(b) T9（備援 T3）（9 題，no_more_questions）；(c) T9（備援 T3）（9 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-083（heart_failure／unclear）

- 列入原因：標註者不一致；系統(a)比Opus 5.5不急；系統(b)比Opus 5.5不急；系統(c)比Opus 5.5不急
- 開場白：「那個，襪子脫掉，腳上那一圈好久都不退，肉好像也泡泡的。體重機的數字這陣子一直往上，可是多幾公斤喔，我沒抄，褲頭也有點勒……這到底算不算不舒服，我不會講。」

事實清單：

```
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- dyspnea_complaint：false
- edema（腳有沒有腫？）：true
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：unclear（不太清楚）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：unknown（不記得）
- nausea（有沒有想吐、噁心？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decrease_timescale（變成比較輕的活動就會不舒服，是這幾天的事，還是這幾個禮拜慢慢變的？）：unknown（不記得）
```

- Opus 5.5：T2，信心 medium——主訴為下肢水腫久未消退、體重持續上升、褲頭變緊，疑似體液滯留或心衰竭惡化。無胸痛、無喘、無冒汗、無暈厥或瀕厥，症狀目前也未持續，未命中任何紅旗，亦無端坐呼吸或夜間陣發性呼吸困難。增重幅度與時程不明，宜於24–72小時內安排評估；若出現喘、躺平會喘或體重快速上升，應立即就醫。
- gpt-6.1-sol：T9，信心 high——有下肢水腫及體重上升，但缺水腫起始與惡化速度、增重幅度及時間，亦未確認端坐呼吸或夜間喘醒。未命中紅旗，現有資訊不足以安全定級，需轉護理師補問。
- 系統：(a) T9（備援 T3）；(b) T9（備援 T3）（10 題，no_more_questions）；(c) T9（備援 T3）（10 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-091（arrhythmia_syncope／general）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我四十六歲，最近在家踩縫紉機，心跳會突然咚咚咚很快，中間又像漏一拍。今天上午那次大概十二分鐘才停，現在正常了，想問這種要怎麼處理。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：true
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：12
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：2
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：true
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——46歲，無冠心病史。近2週新發陣發性心悸，今日一次持續12分鐘，已緩解且曾復發。無胸悶、暈厥、瀕厥、冒汗或喘，無紅旗，血行動力學應屬穩定。新發且反覆的持續性心悸需在24–72小時內安排心電圖與Holter評估。若再發作且合併胸痛、喘或頭暈，或持續不停，應立即就醫。
- gpt-6.1-sol：T2，信心 high——近兩週新發且反覆心悸，今日發作約12分鐘後已緩解，無胸部不適、呼吸困難、暈厥或瀕厥，未命中紅旗。建議24–72小時內評估心律；若合併胸痛、喘或快昏倒，立即急診。
- 系統：(a) T0；(b) T3（5 題，gate_passed）；(c) T3（5 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-095（arrhythmia_syncope／anxious_exaggerating）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「救命，我心臟是不是要爆掉了！我三十四歲，剛剛靠在沙發聽音樂，心跳突然快到我整個嚇死，手錶顯示一百一十二，兩分鐘後又掉回來。昨天也有一次，我現在雖然沒在跳那麼快，還是怕下一秒會出事！」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：true
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：2
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0.14
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：true
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——34歲無心臟病史，近兩天休息時新發心悸兩次，心率112、約2分鐘自行緩解，目前未發作。無胸悶、暈厥、瀕厥、冒汗或喘，未命中紅旗。新發反覆心悸宜於24–72小時內安排心電圖或Holter評估。若再發作且持續、合併胸悶、頭暈欲昏或喘，應立即就醫。
- gpt-6.1-sol：T2，信心 high——新發且反覆的短暫心悸，心率約112次／分、持續2分鐘後自行恢復，目前無症狀；無胸部不適、呼吸困難、暈厥或瀕厥，未命中紅旗。宜於24–72小時內評估並安排心電圖；若合併胸痛、喘或暈厥應立即急診。
- 系統：(a) T0；(b) T3（5 題，gate_passed）；(c) T3（5 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-108（noncardiac_chest／minimizer）

- 列入原因：標註者不一致；系統(a)比Opus 5.5不急；系統(b)比Opus 5.5不急；系統(c)比Opus 5.5不急
- 開場白：「應該只是我太貪吃啦，中午吃了麻辣鍋，胸口一路熱熱辣辣到喉嚨。後來打幾個嗝就全退了，現在好好的，不想為這個麻煩醫師，只是太太叫我一定要問一下。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：15
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：8
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pattern_unchanged_duration_months（這個情況維持一樣、完全沒有變嚴重，大概多久了？）：2
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：true
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：other（其他）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——飯後灼熱感上達喉嚨，打嗝即緩解，持續15分鐘，目前已無症狀；無冒汗、瀕厥、喘或暈厥，未命中紅旗。但症狀約8週前開始、休息時發作，且未曾評估。雖型態穩定兩個月、偏向胃食道逆流，仍不符第3條「無休息時症狀」的常規門診條件，故安排24–72小時內評估。
- gpt-6.1-sol：T4，信心 high——餐後胸口灼熱至喉嚨，打嗝後完全緩解，型態兩個月未變，目前無症狀且無紅旗，可先飲食調整觀察。若胸部不適持續、加劇，或伴喘、冷汗、暈厥，立即急診；反覆發作則門診評估。
- 系統：(a) T9（備援 T3）；(b) T9（備援 T3）（9 題，no_more_questions）；(c) T9（備援 T3）（9 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-110（noncardiac_chest／family_proxy）

- 列入原因：標註者不一致；系統(a)比gpt-6.1-sol不急
- 開場白：「護理師你好，我替先生問，他六十一歲，前天搭車把大行李舉上架子，當下左胸靠腋下就拉痛了。現在伸手拿高處東西，或按到那個地方才會痛；他就在我旁邊，可以自己跟你說。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：0.2
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：unclear（不太清楚）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0.29
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：60
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：true
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：pain（會痛）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：true
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T3，信心 medium——舉重物後出現左側胸壁拉痛，可由按壓及伸手動作重現，每次僅約十幾秒。目前無症狀，無休息痛、冒汗、喘、瀕厥或暈厥，活動閾值未下降，符合肌肉骨骼性胸痛，未命中紅旗。但病人有冠心症及支架病史，且是新發胸痛，用力與疼痛的關係也不清楚，故安排門診追蹤並建議提前就診。須告知：若出現胸悶壓迫、休息時痛、冒汗、喘或快昏倒，立即就醫。
- gpt-6.1-sol：T2，信心 medium——搬重物後新發局部疼痛，僅抬手或按壓誘發、每次約12秒，偏向肌肉骨骼性；目前無痛，無休息痛、喘或暈厥，未命中紅旗。考量冠心症及支架史，宜24–72小時內評估；若持續胸痛、喘或冒冷汗，立即急診。
- 系統：(a) T3；(b) T9（備援 T1）（11 題，max_questions）；(c) T9（備援 T1）（11 題，max_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-120（noncardiac_chest／general）

- 列入原因：標註者不一致；系統(a)比Opus 5.5不急；系統(b)比Opus 5.5不急；系統(c)比Opus 5.5不急
- 開場白：「我六十四歲，有放過支架，想問一種跟以前不太一樣的感覺。昨天廟裡聚餐吃得很撐，坐著泡茶時胸骨後面熱熱燒燒的，後來打了嗝就完全好了；這兩個月偶爾吃太飽會這樣，散步倒不會。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_acute（這個喘是今天忽然變明顯的，還是這幾個禮拜、幾個月慢慢變的？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：10
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：rest_only（休息的時候）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：yesterday_within_24h（昨天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：false
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：8
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pattern_unchanged_duration_months（這個情況維持一樣、完全沒有變嚴重，大概多久了？）：2
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：true
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：60
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：other（其他）
- symptom_vs_pre_pci（跟放支架之前比，現在的不舒服是比較輕、差不多、還是比較重？）：milder（比較輕）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——曾放支架，近兩個月飽餐後靜坐出現胸骨後灼熱，打嗝即緩解，約10分鐘，模式未加重、活動閾值未下降，散步不誘發。目前無症狀，無暈厥、冒汗、喘等紅旗，較像胃食道逆流。但症狀發生於休息時，且為兩個月內出現的新模式，不符例行追蹤條件，仍需排除餐後心絞痛，建議24–72小時內評估。
- gpt-6.1-sol：T3，信心 high——餐後胸骨後灼熱已兩個月且模式不變，打嗝後完全緩解，無活動誘發、近期惡化或目前症狀，亦無紅旗。既往支架本身不構成急症，宜門診追蹤，可提前；若持續胸部不適、冒冷汗或休息喘應立即急診。
- 系統：(a) T9（備援 T3）；(b) T9（備援 T3）（9 題，no_more_questions）；(c) T9（備援 T3）（9 題，no_more_questions）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-136（admin_followup／minimizer）

- 列入原因：系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「歹勢啦，這種小事還打來問，我下禮拜要回南部幫忙採收，原來排的診跟車班撞到了。人都好好的，藥也還夠，可以幫我查那位醫師週五有沒有看診嗎？」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：appointment_admin（想問門診時間）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：true
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recent_pci_months（支架是多久以前放的？）：9
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T3，信心 high——本人來電詢問門診時間（行政事務），無胸部不適、無喘、無暈厥或瀕厥、無冒汗，無休息時症狀或活動閾值下降，抗血小板藥未中斷。已知CAD及9個月前放支架本身非急症指標。屬一般門診追蹤，協助改約並提醒若出現胸悶、喘或暈厥應立即就醫。
- gpt-6.1-sol：T3，信心 high——本次僅詢問門診改期，無胸部不適、呼吸困難、暈厥或其他異常。支架置放已9個月，抗血小板藥未中斷；冠心症病史本身不需急診，可協助調整一般回診。
- 系統：(a) T3；(b) T4（4 題，gate_passed）；(c) T4（4 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-145（admin_followup／family_proxy）

- 列入原因：系統(a)比Opus 5.5、gpt-6.1-sol不急；系統(b)比Opus 5.5、gpt-6.1-sol不急；系統(c)比Opus 5.5、gpt-6.1-sol不急
- 開場白：「我替先生問的，他六十二歲，以前醫師說瓣膜有一點窄，安排每年照一次心臟超音波。這次通知又來了，他說自己游泳、買菜都沒不舒服，想把檢查取消，沒症狀也還是要照嗎？他就在旁邊，可以自己跟你講。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：education_question（想問回診前要注意什麼）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：true
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T3，信心 high——病人本人在旁可確認：已知輕度瓣膜狹窄，游泳、買菜皆無症狀。無胸痛、喘、暈厥、瀕厥、心悸、水腫或端坐呼吸，活動閾值未下降，無紅旗。瓣膜狹窄可能無聲進展，建議不要取消，依原計畫每年心臟超音波及門診追蹤；若出現胸悶、喘、頭暈或昏倒，應立即就醫。
- gpt-6.1-sol：T3，信心 high——已知瓣膜狹窄，活動無不適，無胸痛、呼吸困難、暈厥或活動耐受下降，無紅旗。適合一般門診及原定超音波追蹤；無症狀不代表可取消檢查，應先與原醫師確認。若新發胸痛、喘或暈厥應立即就醫。
- 系統：(a) T4；(b) T4（6 題，gate_passed）；(c) T4（6 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-114（noncardiac_chest／elderly_slow）

- 列入原因：標註者不一致
- 開場白：「小姐喔，我七十六，耳朵比較差，你等一下講大聲一點齁。前幾日把陽台那盆桂花挪開，盆子很重，後來右邊胸前就痠痛，啊今天擦桌子扭到又痛。手指壓下去也會，坐好不動就不痛……我不曉得是不是筋拉到了。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：0.5
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：exertion_only（走路用力的時候才會，停下來就好）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：true
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：pain（會痛）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——76歲，搬重盆後新發右前胸痛，按壓、扭轉可重現，每次約30秒，休息不痛，無持續發作、冒汗、喘、瀕厥或暈厥，無紅旗，較像肌肉骨骼痛。但高齡新發、與用力相關的胸痛不宜直接自我照護，建議24–72小時內就醫評估，並衛教若轉為休息時痛、持續、冒冷汗或喘即撥119。
- gpt-6.1-sol：T0，信心 high——76歲新發且今日再發的用力相關胸痛，休息緩解；雖短暫且可按壓、轉身誘發，仍不足排除心肌缺血，應立即急診評估。目前已無症狀，無喘、暈厥或冒汗，未命中紅旗。
- 系統：(a) T0；(b) T0（5 題，gate_passed）；(c) T0（5 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-115（noncardiac_chest／minimizer）

- 列入原因：標註者不一致
- 開場白：「不用太擔心啦，我四十六，這兩晚一陣咳起來，胸骨下面會像針扎一下，沒咳的空檔都好好的。剛剛又咳痛，太太硬要我打來問，我覺得忍一下就過了，應該不用特地請假吧？」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：true
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：true
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：0.05
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：both（走路會，休息也會）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0.29
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：pain（會痛）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——新發胸骨下刺痛，僅在咳嗽時出現、每次約3秒，不咳即無痛，屬咳嗽誘發的短暫刺痛，不像缺血型態。目前未持續發作，也無冒汗、瀕厥、暈厥或喘，未命中紅旗。休息時發作是因咳嗽而起，非缺血性休息痛。但有冠心病史且咳嗽原因未明，宜24–72小時內評估，並給予安全網：若出現壓迫感、持續痛、喘或冒汗即就醫。
- gpt-6.1-sol：T0，信心 medium——近兩日新發且反覆胸痛，休息時亦發作，合併已知冠心症；雖僅咳嗽時短暫刺痛，仍宜立即急診評估。目前無持續胸痛、呼吸困難、暈厥或冒冷汗，未命中紅旗。
- 系統：(a) T0；(b) T0（7 題，gate_passed）；(c) T0（7 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-139（admin_followup／unclear）

- 列入原因：標註者不一致
- 開場白：「那個，有人打來說我那張心臟的報告有一項不對，要找醫師再看，我也分不清是哪張……紙被我收去哪裡了。叫我回去的那次我沒去成，現在是要重新約，還是先拿報告給你們？我身體倒是沒什麼不舒服。」

事實清單：

```
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：true
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：appointment_admin（想問門診時間）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- nausea（有沒有想吐、噁心？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：true
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T2，信心 medium——病人目前無任何症狀：無胸痛、喘、心悸、暈厥、水腫或端坐呼吸，未命中紅旗。但院方曾來電告知心臟檢查異常、需回診，病人未回診，且不清楚是哪項檢查、何種異常。異常內容可能具臨床意義，不宜僅排一般門診，應於24–72小時內安排回診並調閱報告，同時提供症狀出現即就醫的安全提醒。
- gpt-6.1-sol：T9，信心 high——目前無胸部不適、喘、暈厥等紅旗，但心臟檢查異常且未依通知回診；缺檢查種類、異常內容、通知時間及原建議回診急迫度，無法安全決定分級，需轉護理師查核報告。
- 系統：(a) T1；(b) T1（8 題，gate_passed）；(c) T1（8 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-107（noncardiac_chest／elderly_slow）

- 列入原因：標註者不一致
- 開場白：「喂，歹勢喔，我七十八了，講比較慢……這幾日喉嚨癢，咳、咳下去這個胸坎就會痛一下。沒有咳就沒代誌啦，啊我想問，這要不要另外掛心臟的？」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：true
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：0.05
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：unclear（不太清楚）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：true
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- rest_symptom_first_time（休息時發作是最近才開始的嗎？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：pain（會痛）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T3，信心 medium——78歲，無冠心病史，近日喉嚨癢咳嗽，胸痛只在咳嗽時出現、約數秒即止，不咳不痛；與活動無關，目前無症狀，無喘、冒汗、瀕厥或暈厥，未命中紅旗。「休息時發作」是咳嗽所致，不屬缺血型態，較像咳嗽引起的胸壁或肋膜痛。高齡且近期換藥（需排除藥物性咳嗽），建議一般門診提前追蹤；若出現不咳也痛、喘、發燒或冒冷汗，立即就醫。
- gpt-6.1-sol：T1，信心 medium——疼痛僅咳嗽時出現、每次約3秒，目前已緩解，無喘、冷汗或暈厥，未命中紅旗。惟78歲新發反覆胸痛合併咳嗽，宜當日評估心肺原因；若持續胸痛或出現喘、冷汗、暈厥，立即急診。
- 系統：(a) T0；(b) T0（6 題，gate_passed）；(c) T0（6 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-111（noncardiac_chest／unclear）

- 列入原因：標註者不一致
- 開場白：「那個，我胸前有個地方不太對，位置我也不會講……咳一下就抽一下，咳完又沒有了。是從哪一天開始喔，我現在想不起來，想問這個要怎麼辦。」

事實清單：

```
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：symptom（身體有不舒服）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：true
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：0.03
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：both（走路會，休息也會）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：true
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：pain（會痛）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T4，信心 medium——胸痛只在咳嗽時出現，每次約2秒、不咳就消失；休息時發作也是因咳嗽，屬咳嗽誘發的短暫刺痛，不像缺血型胸痛。目前無症狀，無喘、冒汗、瀕厥或暈厥，未命中紅旗。起始日不明，但型態偏非心因性，可先衛教觀察，並須給 safety net：若出現持續胸悶、喘、冒汗、暈厥或發燒，應立即就醫。
- gpt-6.1-sol：T9，信心 high——疼痛僅咳嗽時短暫出現，現已緩解，無喘、冷汗或暈厥，未命中紅旗。但起始時間及近期是否新發或惡化不明，不能確認長期穩定；需轉護理師釐清後分流。
- 系統：(a) T0；(b) T0（8 題，gate_passed_t0_asked）；(c) T0（8 題，gate_passed_t0_asked）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-098（arrhythmia_syncope／general）

- 列入原因：標註者不一致
- 開場白：「我六十二歲，泌尿科四天前加了睡前吃的排尿藥。這三天半夜下床上廁所，腳一站直就頭暈，等個二十秒左右才敢走；躺著沒有，想問跟這顆藥有沒有關係。」

事實清單：

```
- antiplatelet_interrupted（抗血小板的藥（例如阿斯匹靈、保栓通）最近有沒有停過或漏吃？）：false
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：true
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：medication_handling（想問藥怎麼吃）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- drug_time_correlation（不舒服是每次都在吃藥後固定的時間出現嗎？跟走路、用力有沒有關係？）：true
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- episode_duration_min（這一次不舒服持續了大概多久？幾分鐘、還是超過半小時？）：0.33
- exertion_relation（不舒服通常是在走路、用力的時候出現，停下來就好？還是休息的時候也會？）：unclear（不太清楚）
- last_episode_timing（最後一次不舒服是什麼時候好的？是今天、昨天、還是更早以前？）：today（今天）
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：true
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- onset_new（這種不舒服是最近才第一次出現的，還是以前就有過一樣的感覺？）：true
- onset_weeks_ago（這種情況大概是多久以前開始的？幾天、幾個禮拜、還是幾個月？）：0.43
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pattern_unchanged_duration_months（這個情況維持一樣、完全沒有變嚴重，大概多久了？）：0.1
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：false
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：true
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- recurrence（那次之後到現在，有沒有再發作過？）：true
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T3，信心 medium——62歲，四天前新加睡前排尿藥（疑α阻斷劑），之後夜間起身出現約20秒姿勢性頭暈，躺坐時無症狀。無胸痛、喘、心悸、瀕厥、暈厥或冒汗，未命中紅旗。研判為藥物相關姿勢性低血壓，需衛教緩慢起身，並提前聯絡處方醫師調藥（expedite）。若出現眼前發黑、昏倒、跌倒、胸痛或心悸，應立即就醫。
- gpt-6.1-sol：T2，信心 high——新增排尿藥後反覆出現短暫站立性頭暈，疑藥物相關姿勢性低血壓；無瀕厥、昏厥、胸部不適或喘，未命中紅旗。宜24–72小時內評估血壓並由開藥醫師檢視用藥；若昏厥、胸痛或休息喘應立即急診。
- 系統：(a) T2；(b) T2（7 題，gate_passed）；(c) T2（7 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿

## SYN-144（admin_followup／anxious_exaggerating）

- 列入原因：標註者不一致
- 開場白：「天啊，我戴兩天那個心電圖機，診所說睡覺時有幾段心跳太慢，要我回去給醫師看，我是不是晚上睡著就醒不來了？通知後我還沒回診，現在一直盯著手錶看，嚇都嚇死了。可是我真的沒有胸口不舒服，也沒有喘、暈或心跳亂的感覺。」

事實清單：

```
- cad_history（請問有沒有被醫師診斷過冠心症或心臟血管的問題？）：false
- cant_finish_sentence（您現在講話會不會喘到一句話講不完？）：false
- consult_screen_positive（另外再確認一下：最近有沒有心跳突然很快或亂跳、站起來會頭暈，或是有做過檢查被說異常、還沒回診的？）：true
- consult_topic（請問今天主要是想問什麼？是門診時間、回診前的準備、藥怎麼吃、還是身體有不舒服？）：education_question（想問回診前要注意什麼）
- cough_related（是咳嗽的時候才痛嗎？不咳就不會痛？）：false
- diaphoresis（不舒服的時候有沒有冒冷汗？）：false
- dyspnea_complaint：false
- dyspnea_grade（請問您的喘，是只有做很激烈的運動才會喘、還是平常走路做家事就會喘、還是現在坐著休息也會喘？）：none（沒有）
- edema（腳有沒有腫？）：false
- nausea（有沒有想吐、噁心？）：false
- new_medication_recent（最近有沒有換藥或加新的藥？）：false
- ntg_use_increased（舌下含片最近用得比以前多嗎？）：false
- ongoing_now（請問您現在這個當下，胸口的不舒服還在嗎？）：false
- orthopnea_pnd（躺平會不會更喘、要墊高枕頭？半夜會不會喘醒？）：false
- palpitations（是心跳突然很快或不規則嗎？發作的時候有沒有胸悶或快昏倒？）：false
- patient_reachable（現在能不能請病人本人來接電話，或有人在他身邊可以確認他現在的狀況？）：true
- pci_history（有沒有放過心臟支架？）：false
- pending_abnormal_test（最近有沒有做過心臟檢查被說異常、醫師叫您回診但還沒回去的？）：true
- postprandial_relieved（是吃飽後出現，打嗝或排氣之後就完全好了嗎？）：false
- postural_dizziness（頭暈是站起來的時候才有、幾秒就好嗎？坐著躺著會不會？）：false
- presyncope（不舒服的時候，有沒有覺得快要昏倒、眼前發黑？）：false
- reproducible_mechanical（用手按胸口、深呼吸或轉身的時候會不會痛？走路或用力會不會更痛？）：false
- rest_symptom（坐著或躺著休息的時候，有沒有發作過？）：false
- symptom_character（您說的不舒服，比較像被壓住、悶悶的、刺痛，還是說不上來？位置在哪裡？）：none（沒有）
- syncope（有沒有真的昏過去、失去意識？）：false
- third_party_call：false
- threshold_decreased（跟以前比，是不是比較輕的活動就會不舒服？例如以前要爬樓梯才會，現在走平路也會？）：false
```

- Opus 5.5：T3，信心 medium——Holter報告睡眠時有數段心跳過慢，診所請病人回診但未表示緊急。病人目前完全無症狀，沒有胸悶、喘、暈、昏厥或心悸，也沒有冠心病史或換藥。夜間心搏過慢常見且多屬良性，無紅旗，可安排門診並提前回診。若出現頭暈、快昏倒或昏厥，應立即就醫。
- gpt-6.1-sol：T2，信心 medium——動態心電圖顯示睡眠時心跳過慢，異常結果尚未回診釐清；目前無胸部不適、喘、暈厥或瀕厥，未命中紅旗。宜於24–72小時內由醫師檢視報告，確認最低心率、停頓及傳導異常。
- 系統：(a) T1；(b) T1（3 題，gate_passed）；(c) T1（3 題，gate_passed）
- **Clinical Owner 裁定**：分級＿＿＿＿　Hard stop（Y／N）＿＿　備註＿＿＿＿＿＿＿＿
