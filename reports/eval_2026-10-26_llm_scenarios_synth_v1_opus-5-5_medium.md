# Phase 0 評估報告 — mode=llm seed=0

- 日期：2026-10-26　rules_version：0.8.0
- cases：150（可評分 0；`expect.tier: null` 的變體不計分）
- 模擬病人：LLMPatientSimulator（claude-opus-5-5，effort=medium，回應 model_version=claude-opus-5-5，prompt_version=0.3）；成功 150／150 case（失敗的 case 不計入任何指標，見「執行錯誤」）；情境檔 data/synth/scenarios_synth_v1.yaml（無 truth，下列 truth 指標不適用；與參考標註的比較見 sim.synth_eval）

> **注意——不適用：本次情境檔沒有 truth。** 下列表格與「核心安全指標」「混淆矩陣」「依模組」中以 truth 計算的欄位（Hard-stop miss／false alarm、Under／Over-triage、Tier exact、Abstention、混淆矩陣）一律不適用——顯示 0 或 0.0% **不代表沒有低估**。與 LLM 參考標註的比較見 `reports/synth_eval_<日期>.md`（sim.synth_eval）。不依賴 truth、可以讀的：Escalating／Decisive recall、題數、病人模型偏差、與 Scripted 不同的 case、Token 用量。

## M2b：LLM 病人 vs ScriptedPatient（clean）

| 指標 | LLM 病人 | Scripted clean |
|---|---|---|
| Hard-stop miss | 0/0 | 0/0 |
| Hard-stop false alarm | 0 | 0 |
| Under-triage | 0 | 0 |
| Over-triage | 0 | 0 |
| Abstention FP / FN | 0 / 0 | 0 / 0 |
| Tier exact | 0.0% | 0.0% |
| Escalating recall | 92.4% | 92.2% |
| Questions-to-decision | 5.9 | 5.9 |

## 病人模型偏差（與 hidden sheet 比對，D-30）

- 總回答數：1119；偏差 19（1.7%），分布 {'fabricated': 19}
- **編造率**（sheet 無此事實卻給出答案）：19/122（15.6%）
- 其中複誦確認（D-50）的回答 239 次：偏差 9，分布 {'fabricated': 9}（題目欄標「（複誦）」）
- 有偏差的 case：10

| case | 題目 | 類型 | sheet | LLM | 病人原話 |
|---|---|---|---|---|---|
| SYN-020 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 我其實沒有在喘耶，就只是那時候胸口悶悶的而已，平常走路、坐著都不會喘。 |
| SYN-020 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，我沒有喘，走路做事或坐著都不會喘。 |
| SYN-027 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 我是沒有在喘啦，主要是胸口那邊怪怪的而已。 |
| SYN-027 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，我沒有在喘，就是胸口怪怪的那樣而已。 |
| SYN-034 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 喘喔？我是沒有在喘啦，就是胸口怪怪的而已。 |
| SYN-034 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，我沒有在喘，只是胸口怪怪的。 |
| SYN-041 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 我其實沒有在喘啦，主要是胸口悶悶的而已。 |
| SYN-041 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，我沒有喘，就只是胸口悶悶的。 |
| SYN-062 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 我沒有在喘啦，走路做家事、坐著都不會喘。 |
| SYN-062 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，我沒有喘，怎樣都不會喘。 |
| SYN-067 | Q-PATTERN-01 | fabricated | None | 44 | 大概四十四個禮拜了吧，差不多十個月，一直都差不多這樣，沒有變嚴重。 |
| SYN-069 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 喘喔？我是沒有在喘啦，主要就是胸口悶悶的而已。 |
| SYN-069 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，我沒有在喘，就是胸口會悶而已。 |
| SYN-083 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 喘喔？我倒是沒有在喘耶，走路、做家事都還好，主要是腳腫跟體重一直上去。 |
| SYN-083 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，我沒有在喘，走路做家事都不會喘。 |
| SYN-147 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 她傳語音的時候沒有說會喘耶，就是講心跳亂亂的、眼前黑掉一下而已。 |
| SYN-147 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，她沒有說會喘，只有講心跳亂亂的跟眼前黑一下。 |
| SYN-150 | Q-DYSPNEA-GRADE-01 | fabricated | None | none | 她沒有在喘耶，她就是端烤盤的時候胃上面那邊悶，沒聽她說會喘。 |
| SYN-150 | Q-DYSPNEA-GRADE-01（複誦） | fabricated | None | none | 對，她沒有喘，只是用力端東西的時候胃上面悶悶的。 |

## 最終結果與 Scripted 不同的 case

（無）

## Token 用量與估算成本

- input_tokens：4476
- output_tokens：72115
- cache_creation_input_tokens：1291455
- cache_read_input_tokens：2140843
- calls：1119
- est_cost_usd：8.7738
- 成本為依牌價估算（`PRICES`），以帳單為準；output 含 thinking token。

## 執行錯誤（0）

（無）

## 核心安全指標（LLM 病人）

| 指標 | 值 | 目標 |
|---|---|---|
| Hard-stop miss rate | 0.0%（0/0） | 0% |
| Hard-stop latency（最大） | 0 句 | 0 句 |
| Hard-stop false alarm | 0 | 記錄 |
| Under-triage rate | 0.0%（0） | 趨近 0 |
| Over-triage rate | 0.0%（0） | 記錄 |
| Tier exact accuracy | 0.0% | 記錄 |
| Escalating-question recall（答案可能使分流更急的題目） | 92.4%（522/565） | ≥ 90% |
| Escalating recall（嚴格：由否認推導出的值不算已知，D-42） | 88.7%（501/565） | 記錄 |
| Decisive-question recall（答案會改變分流的題目，含只會降級者） | 91.9%（667/726） | 記錄 |
| Abstention precision / recall | 100.0% / 100.0% | 記錄 |
| Questions-to-decision（平均） | 5.9 | 記錄 |
| Gate effect（低信心重問次數） | 0 | 記錄 |
| Confirm-back（紅旗／關鍵題複誦確認，D-50；不算題數） | 總數 239；平均每通 1.59；確認後改值 0；確認值較不嚴重而保留原值 0 | 記錄 |
| 待追蹤檢查加問（有症狀暫判 T2–T4，rules 0.8.0；算題數） | 加問 23 通；已達題數上限沒問 0 通 | 記錄 |

## 混淆矩陣（truth → pred）

| truth \ pred | 0 | 1 | 2 | 3 | 4 | 9 |
|---|---|---|---|---|---|---|
| **0** | 0 | 0 | 0 | 0 | 0 | 0 |
| **1** | 0 | 0 | 0 | 0 | 0 | 0 |
| **2** | 0 | 0 | 0 | 0 | 0 | 0 |
| **3** | 0 | 0 | 0 | 0 | 0 | 0 |
| **4** | 0 | 0 | 0 | 0 | 0 | 0 |
| **9** | 0 | 0 | 0 | 0 | 0 | 0 |

## 依模組

| module | n | exact | under | over | abstain_fp | abstain_fn |
|---|---|---|---|---|---|---|

## 指標說明

- Under/Over-triage 只計 truth 與 pred 皆在 0–4 的案例；pred 9 另計 abstention FP、truth 9 另計 abstention FN。
- Hard-stop latency = 揭露紅旗事實的那句與觸發 Hard stop 之間相隔的句數；引擎逐句重算，理論上恆為 0。
- Decisive／Escalating 題目由 `sim/decisive.py` 依每個 case 的完整事實逐題反事實計算（D-27）：
  把該題換成任一可能答案，若 (provisional_tier, hard_stop) 會改變即為 decisive；其中存在答案使結果**更急**者為 escalating。
  Tier 9 依 C6 D 主訴對照表換算急迫度。Escalating 漏問 = 可能 under-triage，是安全指標；只會降級的題漏問只造成 over-triage。
- 資訊不足組（persona vague）的 base case 以 `max_questions` 結束並維持 Tier 9 是**預期行為**（節制），不是失敗。

## 結束原因

- gate_passed: 61
- gate_passed_t0_asked: 5
- hard_stop: 46
- hard_stop_opening: 5
- max_questions: 22
- no_more_questions: 11

## Hard-stop miss（0）

（無）

## Hard-stop false alarm（0）

（無）

## Under-triage（case, truth, pred）（0）

（無）

## Over-triage（case, truth, pred）（0）

（無）

## Abstention FP（truth 0–4 但最終 9）（0）

（無）

## Abstention FN（truth 9 但給了 0–4）（0）

（無）

## RF 不一致（case, expected rf, got）（0）

（無）

## 漏問的 escalating 題目（43）

| 題目 | 漏問次數 |
|---|---|
| Q-NTG-01 | 16 |
| Q-REST-01 | 5 |
| Q-PENDINGTEST-01 | 5 |
| Q-REPRO-01 | 3 |
| Q-ONSET-01 | 2 |
| Q-ORTHO-01 | 2 |
| Q-THRESHOLD-01 | 2 |
| Q-SYNCOPE-01 | 1 |
| Q-DIAPH-01 | 1 |
| Q-DYSPNEA-ACUTE-01 | 1 |
| Q-SYNCOPE-02 | 1 |
| Q-EXERTION-01 | 1 |
| Q-ANTIPLT-01 | 1 |
| Q-CHARACTER-01 | 1 |
| Q-REACHABLE-01 | 1 |

明細（case, 題目, final tier, 結束原因）：

- ('SYN-006', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-014', 'Q-SYNCOPE-01', 0, 'hard_stop')
- ('SYN-014', 'Q-DIAPH-01', 0, 'hard_stop')
- ('SYN-028', 'Q-REST-01', 9, 'max_questions')
- ('SYN-028', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-033', 'Q-REST-01', 9, 'max_questions')
- ('SYN-033', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-036', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-041', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-043', 'Q-REST-01', 9, 'max_questions')
- ('SYN-043', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-048', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-053', 'Q-ONSET-01', 3, 'gate_passed')
- ('SYN-057', 'Q-ONSET-01', 1, 'gate_passed')
- ('SYN-057', 'Q-PENDINGTEST-01', 1, 'gate_passed')
- ('SYN-062', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-063', 'Q-DYSPNEA-ACUTE-01', 1, 'gate_passed')
- ('SYN-063', 'Q-ORTHO-01', 1, 'gate_passed')
- ('SYN-069', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-071', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-072', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-100', 'Q-SYNCOPE-02', 9, 'max_questions')
- ('SYN-106', 'Q-THRESHOLD-01', 0, 'gate_passed')
- ('SYN-106', 'Q-REST-01', 0, 'gate_passed')
- ('SYN-106', 'Q-EXERTION-01', 0, 'gate_passed')
- ('SYN-106', 'Q-REPRO-01', 0, 'gate_passed')
- ('SYN-106', 'Q-NTG-01', 0, 'gate_passed')
- ('SYN-106', 'Q-PENDINGTEST-01', 0, 'gate_passed')
- ('SYN-110', 'Q-REPRO-01', 9, 'max_questions')
- ('SYN-110', 'Q-ANTIPLT-01', 9, 'max_questions')
- ('SYN-110', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-110', 'Q-PENDINGTEST-01', 9, 'max_questions')
- ('SYN-118', 'Q-REPRO-01', 9, 'max_questions')
- ('SYN-118', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-118', 'Q-PENDINGTEST-01', 9, 'max_questions')
- ('SYN-121', 'Q-CHARACTER-01', 0, 'gate_passed')
- ('SYN-121', 'Q-ORTHO-01', 0, 'gate_passed')
- ('SYN-125', 'Q-PENDINGTEST-01', 9, 'max_questions')
- ('SYN-131', 'Q-THRESHOLD-01', 0, 'gate_passed')
- ('SYN-131', 'Q-REST-01', 0, 'gate_passed')
- ('SYN-131', 'Q-NTG-01', 0, 'gate_passed')
- ('SYN-135', 'Q-NTG-01', 9, 'max_questions')
- ('SYN-145', 'Q-REACHABLE-01', 4, 'gate_passed')

## 每案摘要

| case | truth | final | HS | stop | Q | 問到的題 |
|---|---|---|---|---|---|---|
| SYN-001 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-002 | — | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| SYN-003 | — | 0Y | RF-06 | hard_stop | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-004 | — | 0Y | RF-01 | hard_stop | 2 | ONGOING-01 SYNCOPE-01 |
| SYN-005 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-006 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 PALP-01 POSTURAL-01 |
| SYN-007 | — | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 |
| SYN-008 | — | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-009 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-010 | — | 0Y | RF-03 | hard_stop | 3 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 |
| SYN-011 | — | 0 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| SYN-012 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-013 | — | 0Y | RF-01 | hard_stop | 2 | ONGOING-01 SYNCOPE-01 |
| SYN-014 | — | 0Y | RF-03 | hard_stop | 2 | DYSPNEA-GRADE-01 CHARACTER-01 |
| SYN-015 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-016 | — | 0 |  | gate_passed | 4 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 |
| SYN-017 | — | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-018 | — | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| SYN-019 | — | 0Y | RF-03 | hard_stop | 2 | DYSPNEA-GRADE-01 CHARACTER-01 |
| SYN-020 | — | 0 |  | gate_passed_t0_asked | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 |
| SYN-021 | — | 0Y | RF-03 | hard_stop_opening | 0 |  |
| SYN-022 | — | 0Y | RF-01,RF-05 | hard_stop_opening | 0 |  |
| SYN-023 | — | 0 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| SYN-024 | — | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-025 | — | 0 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| SYN-026 | — | 0Y | RF-06 | hard_stop | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-027 | — | 0 |  | gate_passed_t0_asked | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-028 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-029 | — | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 REST-02 |
| SYN-030 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 PALP-01 POSTURAL-01 |
| SYN-031 | — | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-032 | — | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-033 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 REACHABLE-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-034 | — | 0 |  | gate_passed_t0_asked | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 REST-02 |
| SYN-035 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 PALP-01 POSTURAL-01 |
| SYN-036 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 PALP-01 POSTURAL-01 |
| SYN-037 | — | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-038 | — | 0Y | RF-06 | hard_stop | 7 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 |
| SYN-039 | — | 0Y | RF-06 | hard_stop_opening | 0 |  |
| SYN-040 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 REACHABLE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 |
| SYN-041 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| SYN-042 | — | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-043 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-044 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 PATTERN-01 EXERTION-01 TIMING-01 RECUR-01 |
| SYN-045 | — | 0Y | RF-06 | hard_stop | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-046 | — | 3 |  | gate_passed | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-047 | — | 3 |  | gate_passed | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-048 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| SYN-049 | — | 3 |  | gate_passed | 10 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-050 | — | 3 |  | gate_passed | 9 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-051 | — | 3 |  | gate_passed | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-052 | — | 3 |  | gate_passed | 9 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-053 | — | 3 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 NTG-01 PENDINGTEST-01 |
| SYN-054 | — | 3 |  | gate_passed | 10 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REACHABLE-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-055 | — | 3 |  | gate_passed | 9 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-056 | — | 3 |  | gate_passed | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-057 | — | 1 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 NTG-01 |
| SYN-058 | — | 3 |  | gate_passed | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-059 | — | 3 |  | gate_passed | 9 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-060 | — | 3 |  | gate_passed | 9 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 PENDINGTEST-01 |
| SYN-061 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-062 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| SYN-063 | — | 1 |  | gate_passed | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 REST-01 NTG-01 ANTIPLT-01 |
| SYN-064 | — | 0 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-065 | — | 0 |  | gate_passed | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 REST-02 |
| SYN-066 | — | 3 |  | gate_passed | 4 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 SYNCOPE-01 |
| SYN-067 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 REST-02 PATTERN-01 NTG-01 |
| SYN-068 | — | 1 |  | gate_passed | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 NTG-01 ANTIPLT-01 |
| SYN-069 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| SYN-070 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-071 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 |
| SYN-072 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 REST-02 PATTERN-01 EXERTION-01 PALP-01 |
| SYN-073 | — | 0Y | RF-06 | hard_stop_opening | 0 |  |
| SYN-074 | — | 3 |  | gate_passed | 3 | DYSPNEA-GRADE-01 SCREEN-01 SYNCOPE-01 |
| SYN-075 | — | 0Y | RF-06 | hard_stop | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 |
| SYN-076 | — | 0 |  | gate_passed | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 ONSET-01 THRESHOLD-01 THRESH-TIME-01 |
| SYN-077 | — | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| SYN-078 | — | 9 |  | no_more_questions | 9 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 DRUGTIME-01 CAD-01 PCI-01 PCI-RECENT-01 |
| SYN-079 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-080 | — | 0Y | RF-02 | hard_stop | 2 | SYNCOPE-01 DYSPNEA-GRADE-01 |
| SYN-081 | — | 2 |  | gate_passed | 6 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 PENDINGTEST-01 |
| SYN-082 | — | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| SYN-083 | — | 9 |  | no_more_questions | 10 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 PENDINGTEST-01 |
| SYN-084 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-085 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-086 | — | 2 |  | gate_passed | 6 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 PENDINGTEST-01 |
| SYN-087 | — | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| SYN-088 | — | 9 |  | no_more_questions | 9 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 |
| SYN-089 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-090 | — | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| SYN-091 | — | 3 |  | gate_passed | 5 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 SYNCOPE-02 PENDINGTEST-01 |
| SYN-092 | — | 9 |  | no_more_questions | 9 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 |
| SYN-093 | — | 9 |  | no_more_questions | 10 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 PENDINGTEST-01 |
| SYN-094 | — | 2 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SYNCOPE-02 SYNCOPE-01 PENDINGTEST-01 |
| SYN-095 | — | 3 |  | gate_passed | 5 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 SYNCOPE-02 PENDINGTEST-01 |
| SYN-096 | — | 3 |  | gate_passed | 6 | DYSPNEA-GRADE-01 REACHABLE-01 CHARACTER-01 PALP-01 SYNCOPE-02 PENDINGTEST-01 |
| SYN-097 | — | 0Y | RF-05 | hard_stop_opening | 0 |  |
| SYN-098 | — | 2 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SYNCOPE-02 SYNCOPE-01 PENDINGTEST-01 |
| SYN-099 | — | 0 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| SYN-100 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 PENDINGTEST-01 PCI-RECENT-01 |
| SYN-101 | — | 0Y | RF-05 | hard_stop | 5 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 SYNCOPE-01 SYNCOPE-02 |
| SYN-102 | — | 2 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SYNCOPE-02 SYNCOPE-01 PENDINGTEST-01 |
| SYN-103 | — | 0Y | RF-03 | hard_stop | 3 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 |
| SYN-104 | — | 0Y | RF-01 | hard_stop | 2 | ONGOING-01 SYNCOPE-01 |
| SYN-105 | — | 9 |  | no_more_questions | 9 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 |
| SYN-106 | — | 0 |  | gate_passed | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-107 | — | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| SYN-108 | — | 9 |  | no_more_questions | 9 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 |
| SYN-109 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-110 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 RECUR-01 ONSET-01 THRESHOLD-01 EXERTION-01 ONSET-WEEKS-01 PALP-01 |
| SYN-111 | — | 0 |  | gate_passed_t0_asked | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 REST-02 |
| SYN-112 | — | 9 |  | no_more_questions | 9 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 |
| SYN-113 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-114 | — | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 |
| SYN-115 | — | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 REST-01 REST-02 |
| SYN-116 | — | 9 |  | no_more_questions | 9 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-01 |
| SYN-117 | — | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| SYN-118 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 PALP-01 POSTURAL-01 |
| SYN-119 | — | 0 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 REST-01 REST-02 |
| SYN-120 | — | 9 |  | no_more_questions | 9 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 DRUGTIME-01 CAD-01 PCI-RECENT-01 |
| SYN-121 | — | 0 |  | gate_passed | 2 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| SYN-122 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-123 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-124 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-125 | — | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 PATTERN-01 PALP-01 POSTURAL-01 CONSULT-01 DRUGTIME-01 EDEMA-01 |
| SYN-126 | — | 0Y | RF-03 | hard_stop | 3 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 |
| SYN-127 | — | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 |
| SYN-128 | — | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| SYN-129 | — | 2 |  | gate_passed | 6 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 PENDINGTEST-01 |
| SYN-130 | — | 0 |  | gate_passed | 6 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| SYN-131 | — | 0 |  | gate_passed | 4 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 |
| SYN-132 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-133 | — | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| SYN-134 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 NTG-01 ONSET-01 EXERTION-01 RECUR-01 ONSET-WEEKS-01 |
| SYN-135 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 RECUR-01 ONSET-01 THRESHOLD-01 PATTERN-01 EXERTION-01 PALP-01 |
| SYN-136 | — | 4 |  | gate_passed | 4 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 SYNCOPE-01 |
| SYN-137 | — | 4 |  | gate_passed | 6 | DYSPNEA-GRADE-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 SYNCOPE-01 |
| SYN-138 | — | 4 |  | gate_passed | 4 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 SYNCOPE-01 |
| SYN-139 | — | 1 |  | gate_passed | 8 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 SYNCOPE-01 PENDINGTEST-01 |
| SYN-140 | — | 4 |  | gate_passed | 3 | DYSPNEA-GRADE-01 SCREEN-01 SYNCOPE-01 |
| SYN-141 | — | 3 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 SYNCOPE-01 |
| SYN-142 | — | 4 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 SYNCOPE-01 |
| SYN-143 | — | 4 |  | gate_passed | 6 | DYSPNEA-GRADE-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 SYNCOPE-01 |
| SYN-144 | — | 1 |  | gate_passed | 3 | CHARACTER-01 SYNCOPE-02 PENDINGTEST-01 |
| SYN-145 | — | 4 |  | gate_passed | 6 | DYSPNEA-GRADE-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 SYNCOPE-01 |
| SYN-146 | — | 0Y | RF-03 | hard_stop | 4 | DYSPNEA-GRADE-01 REACHABLE-01 CHARACTER-01 ONGOING-01 |
| SYN-147 | — | 9 |  | no_more_questions | 10 | SYNCOPE-02 DYSPNEA-GRADE-01 REACHABLE-01 CHARACTER-01 POSTURAL-01 SCREEN-01 DRUGTIME-01 CAD-01 PCI-01 PENDINGTEST-01 |
| SYN-148 | — | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| SYN-149 | — | 4 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 SYNCOPE-01 |
| SYN-150 | — | 0 |  | gate_passed_t0_asked | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REACHABLE-01 ONSET-01 |
