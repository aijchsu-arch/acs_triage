# Phase 0 評估報告 — mode=llm seed=0

- 日期：2026-10-15　rules_version：0.5.0
- cases：119（可評分 116；`expect.tier: null` 的變體不計分）
- 模擬病人：LLMPatientSimulator（claude-haiku-5-5，effort=low，回應 model_version=claude-haiku-5-5，prompt_version=0.1）；成功 119／119 case（失敗的 case 不計入任何指標，見「執行錯誤」）

## M2b：LLM 病人 vs ScriptedPatient（clean）

| 指標 | LLM 病人 | Scripted clean |
|---|---|---|
| Hard-stop miss | 1/27 | 0/27 |
| Hard-stop false alarm | 0 | 0 |
| Under-triage | 2 | 0 |
| Over-triage | 1 | 0 |
| Abstention FP / FN | 3 / 1 | 0 / 0 |
| Tier exact | 94.0% | 100.0% |
| Escalating recall | 96.8% | 96.6% |
| Questions-to-decision | 5.6 | 5.4 |

## 病人模型偏差（與 hidden sheet 比對，D-30）

- 總回答數：665；偏差 47（7.1%），分布 {'fabricated': 27, 'contradicted': 20}
- **編造率**（sheet 無此事實卻給出答案）：27/149（18.1%）
- 有偏差的 case：31

| case | 題目 | 類型 | sheet | LLM | 病人原話 |
|---|---|---|---|---|---|
| S-ACUTE-03 | Q-ONGOING-01 | fabricated | None | False | 已經沒有了，今天不舒服的感覺好了，現在胸口不會痛。 |
| S-ACUTE-03#0 | Q-ONGOING-01 | fabricated | None | False | 胸口現在沒有痛，也沒有悶悶的感覺。 |
| S-ACUTE-03#1 | Q-ONGOING-01 | fabricated | None | False | 不在了，剛剛就好了，現在胸口沒有痛。 |
| S-ACUTE-03#2 | Q-THRESHOLD-01 | fabricated | None | False | 沒有耶，我還是只有很激烈的運動才會喘，走平路或做家事都沒問題。 |
| S-ACUTE-03#2 | Q-REST-01 | fabricated | None | False | 沒有耶，我坐著或躺著休息的時候都不會喘。 |
| S-ACUTE-03#2 | Q-EXERTION-01 | fabricated | None | exertion_only | 就是很激烈的運動才會喘，停下來休息就好，坐著或躺著休息的時候不會喘。 |
| S-STABLE-01#0 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 就是很激烈的運動才會喘，平常走路做家事都還好，坐著休息也不會喘。 |
| S-STABLE-01#1 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 只有做很激烈的運動才會喘，平常走路、做家事都沒有喘。 |
| S-STABLE-01#2 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 就只有快走上坡的時候會喘，平常走路做家事都還好，坐著休息也不會喘。 |
| S-STABLE-01#2 | Q-DYSPNEA-SENTENCE-01 | fabricated | None | False | 不會，講話很正常，沒有喘到講不完。 |
| S-STABLE-01#2 | Q-PATTERN-01 | fabricated | None | 24 | 大概兩年了，這兩年都差不多一樣，沒有變嚴重。 |
| S-STABLE-02 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 就是很用力運動才會喘，平常走路做家事都不會喘，坐著休息也不會。 |
| S-STABLE-02#0 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 就是很用力運動的時候才會喘，平常走路做家事都還好，坐著休息也不會喘。 |
| S-STABLE-02#1 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 就是比較用力運動的時候才會喘，平常走路做家事都還好，坐著休息的時候完全不會。 |
| S-STABLE-03#0 | Q-ONSET-01 | contradicted | True | False | 這種感覺以前就有過了，不是最近才第一次出現的。 |
| S-STABLE-04 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 我的喘只有在做很激烈的運動的時候才會，平常走路、做家事都還好，坐著休息也不會喘。 |
| S-STABLE-04#1 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 我的喘是只有做很激烈的運動才會喘，平常走路做家事都不會。 |
| S-INSUF-01 | Q-REST-01 | fabricated | None | False | 坐著或躺著休息的時候，我沒有印象有發作過，都是在走路或做事的時候比較會。 |
| S-INSUF-01 | Q-EXERTION-01 | fabricated | None | exertion_only | 通常是走路或用力的時候才會，停下來休息就會好，休息的時候我沒有印象會發作。 |
| S-INSUF-01#0 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 我現在坐著休息的時候完全不會喘，平常走路做家事也沒有喘，只有很激烈的運動才會。 |
| S-INSUF-02#0 | Q-ONSET-01 | contradicted | True | False | 這幾天才開始的，以前沒有這樣的感覺。 |
| S-INSUF-03#1 | Q-ONSET-01 | fabricated | None | True | 這種悶悶的感覺之前比較少有，最近才比較常出現，大概這一兩個禮拜開始的。 |
| S-INSUF-04 | Q-DYSPNEA-GRADE-01 | fabricated | None | exertional_daily | 我現在坐著休息也會喘嗎？不會啦，我坐著的時候都還好，比較是走路或做家事的時候才會喘。 |
| S-INSUF-04 | Q-PALP-01 | fabricated | None | False | 心跳突然很快或不規則這個我不太確定耶。不舒服的時候我沒有覺得快昏倒或眼前發黑。 |
| S-INSUF-04 | Q-CONSULT-01 | fabricated | None | symptom | 我是因為最近覺得比較喘，不知道是不是心臟的問題，所以想打來問看看，身體有不舒服才打來的。 |
| S-INSUF-04 | Q-DRUGTIME-01 | fabricated | None | True | 吃藥後固定時間出現這個我不太確定耶。但我是走路或做家事比較容易喘，這個有關係。 |
| S-INSUF-04#1 | Q-DYSPNEA-GRADE-01 | fabricated | None | exertional_daily | 我就是平常走路、做家事就會喘，坐著休息的時候還好，不用特別去做很激烈的運動。 |
| S-INSUF-04#1 | Q-DYSPNEA-ACUTE-01 | contradicted | True | False | 不是今天忽然的，是這幾個月慢慢變明顯的。 |
| S-INSUF-05 | Q-REST-01 | fabricated | None | False | 坐著或躺著休息的時候都沒有發作過，都是走路的時候才會胸悶。 |
| S-INSUF-05 | Q-PALP-01 | fabricated | None | False | 心跳好像沒有特別快或不規則，我感覺就是胸口悶悶的，沒有覺得快昏倒。 |
| S-INSUF-05 | Q-POSTURAL-01 | fabricated | None | False | 我沒有頭暈的感覺，所以站起來或坐著躺著都沒有這種情況。 |
| S-INSUF-05#0 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_daily | 只有走路或用力的時候才會喘，平常坐著休息是不會的。 |
| S-INSUF-05#1 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_daily | 我只有走路或用力的時候才會喘，平常坐著休息是不會的。 |
| S-INSUF-06 | Q-REST-01 | fabricated | None | False | 坐著或躺著休息的時候，沒有發作過，都是吃藥後比較活動的時候才會悶。 |
| S-INSUF-06 | Q-EXERTION-01 | fabricated | None | exertion_only | 通常是走路或用力的時候才會悶，停下來休息就會慢慢好，休息的時候一般不會發作。 |
| S-INSUF-06#1 | Q-THRESHOLD-01 | fabricated | None | False | 這個我不太確定耶，我也沒有特別注意以前是怎樣，好像就是最近走路或做家事的時候比較常覺得怪怪的。 |
| S-INSUF-06#1 | Q-REST-01 | fabricated | None | False |  |
| S-MID-03#1 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_daily | 我是走路、做家事就會喘，不是只有激烈運動才會，坐著休息的時候就不會喘了。 |
| S-MID-03#1 | Q-NTG-01 | contradicted | False | True | 有，最近比以前多，以前一個月含一次，這兩個禮拜變成一個禮拜兩三次。 |
| S-MID-06#2 | Q-DYSPNEA-ACUTE-01 | contradicted | True | False | 不是今天忽然變的，是這一個禮拜慢慢開始比較會喘。 |
| S-MID-11 | Q-ONGOING-01 | fabricated | None | False | 現在坐著休息，胸口是不會痛啦，不舒服的感覺已經沒有了。 |
| S-MID-11#0 | Q-ONGOING-01 | fabricated | None | True | 現在坐著休息，胸口是不會痛啦，不舒服的感覺是今天有比較明顯。 |
| S-MID-11#1 | Q-ONGOING-01 | fabricated | None | False | 現在坐著休息，胸口是不痛了，也不會不舒服，沒有在痛。 |
| S-MID-11#1 | Q-DYSPNEA-SENTENCE-01 | contradicted | True | False | 不會啊，講話很順，一句話可以講完，沒有喘。 |
| S-MID-13#2 | Q-ONSET-01 | contradicted | True | False | 是最近才第一次這樣，以前沒有過一樣的感覺。 |
| S-MID-17#0 | Q-DYSPNEA-GRADE-01 | contradicted | none | exertional_heavy | 我爸現在坐著休息也不會喘，平常走路做家事也都沒有喘，只有很激烈的運動才會喘。 |
| S-MID-17#0 | Q-EXERTION-01 | fabricated | None | rest_only | 休息的時候沒有發作過，但他走路或用力的時候會不會不舒服，我不太確定。 |

## 最終結果與 Scripted 不同的 case

- S-STABLE-01#2：truth 9，LLM 3，Scripted 9（病人偏差）
- S-STABLE-03#0：truth 0，LLM 9，Scripted 0（病人偏差）
- S-INSUF-02#0：truth 0，LLM 9，Scripted 0（病人偏差）
- S-INSUF-04#1：truth 0，LLM 2，Scripted 0（病人偏差）
- S-MID-03#1：truth 3，LLM 0，Scripted 3（病人偏差）
- S-MID-06#2：truth 0，LLM 2，Scripted 0（病人偏差）
- S-MID-11#1：truth 0Y，LLM 0，Scripted 0Y（病人偏差）
- S-MID-13#2：truth 0，LLM 9，Scripted 0（病人偏差）

## 執行錯誤（0）

（無）

## 核心安全指標（LLM 病人）

| 指標 | 值 | 目標 |
|---|---|---|
| Hard-stop miss rate | 3.7%（1/27） | 0% |
| Hard-stop latency（最大） | 0 句 | 0 句 |
| Hard-stop false alarm | 0 | 記錄 |
| Under-triage rate | 1.7%（2） | 趨近 0 |
| Over-triage rate | 0.9%（1） | 記錄 |
| Tier exact accuracy | 94.0% | 記錄 |
| Escalating-question recall（答案可能使分流更急的題目） | 96.8%（513/530） | ≥ 90% |
| Decisive-question recall（答案會改變分流的題目，含只會降級者） | 95.1%（681/716） | 記錄 |
| Abstention precision / recall | 78.6% / 91.7% | 記錄 |
| Questions-to-decision（平均） | 5.6 | 記錄 |
| Gate effect（低信心重問次數） | 0 | 記錄 |

## 混淆矩陣（truth → pred）

| truth \ pred | 0 | 1 | 2 | 3 | 4 | 9 |
|---|---|---|---|---|---|---|
| **0** | 65 | 0 | 2 | 0 | 0 | 3 |
| **1** | 0 | 7 | 0 | 0 | 0 | 0 |
| **2** | 0 | 0 | 5 | 0 | 0 | 0 |
| **3** | 1 | 0 | 0 | 17 | 0 | 0 |
| **4** | 0 | 0 | 0 | 0 | 4 | 0 |
| **9** | 0 | 0 | 0 | 1 | 0 | 11 |

## 依模組

| module | n | exact | under | over | abstain_fp | abstain_fn |
|---|---|---|---|---|---|---|
| acute | 16 | 16 | 0 | 0 | 0 | 0 |
| insufficient | 25 | 23 | 1 | 0 | 1 | 0 |
| midband | 64 | 61 | 1 | 1 | 1 | 0 |
| stable | 11 | 9 | 0 | 0 | 1 | 1 |

## 指標說明

- Under/Over-triage 只計 truth 與 pred 皆在 0–4 的案例；pred 9 另計 abstention FP、truth 9 另計 abstention FN。
- Hard-stop latency = 揭露紅旗事實的那句與觸發 Hard stop 之間相隔的句數；引擎逐句重算，理論上恆為 0。
- Decisive／Escalating 題目由 `sim/decisive.py` 依每個 case 的完整事實逐題反事實計算（D-27）：
  把該題換成任一可能答案，若 (provisional_tier, hard_stop) 會改變即為 decisive；其中存在答案使結果**更急**者為 escalating。
  Tier 9 依 C6 D 主訴對照表換算急迫度。Escalating 漏問 = 可能 under-triage，是安全指標；只會降級的題漏問只造成 over-triage。
- 資訊不足組（persona vague）的 base case 以 `max_questions` 結束並維持 Tier 9 是**預期行為**（節制），不是失敗。

## 結束原因

- gate_passed: 78
- hard_stop: 24
- hard_stop_opening: 2
- max_questions: 15

## Hard-stop miss（1）

- S-MID-11#1

## Hard-stop false alarm（0）

（無）

## Under-triage（case, truth, pred）（2）

- ('S-INSUF-04#1', 0, 2)
- ('S-MID-06#2', 0, 2)

## Over-triage（case, truth, pred）（1）

- ('S-MID-03#1', 3, 0)

## Abstention FP（truth 0–4 但最終 9）（3）

- ('S-STABLE-03#0', 0)
- ('S-INSUF-02#0', 0)
- ('S-MID-13#2', 0)

## Abstention FN（truth 9 但給了 0–4）（1）

- ('S-STABLE-01#2', 3)

## RF 不一致（case, expected rf, got）（1）

- ('S-MID-11#0', 'RF-02', ['RF-03'])

## 漏問的 escalating 題目（17）

| 題目 | 漏問次數 |
|---|---|
| Q-NTG-01 | 11 |
| Q-ONSET-01 | 2 |
| Q-ORTHO-01 | 1 |
| Q-THRESHOLD-01 | 1 |
| Q-REST-02 | 1 |
| Q-ONSET-WEEKS-01 | 1 |

明細（case, 題目, final tier, 結束原因）：

- ('S-ACUTE-03#2', 'Q-ORTHO-01', 9, 'max_questions')
- ('S-ACUTE-05#1', 'Q-ONSET-01', 0, 'gate_passed')
- ('S-ACUTE-05#1', 'Q-THRESHOLD-01', 0, 'gate_passed')
- ('S-ACUTE-05#1', 'Q-REST-02', 0, 'gate_passed')
- ('S-ACUTE-05#1', 'Q-NTG-01', 0, 'gate_passed')
- ('S-INSUF-01', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-02', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-03', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-05', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-06', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-06#1', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-07', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-07#1', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-08', 'Q-NTG-01', 9, 'max_questions')
- ('S-MID-07', 'Q-ONSET-01', 1, 'gate_passed')
- ('S-MID-08', 'Q-ONSET-WEEKS-01', 3, 'gate_passed')
- ('S-MID-17#0', 'Q-NTG-01', 9, 'max_questions')

## 每案摘要

| case | truth | final | HS | stop | Q | 問到的題 |
|---|---|---|---|---|---|---|
| S-ACUTE-01 | 0 | 0 |  | gate_passed | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-01#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-01#1 | 0 | 0 |  | gate_passed | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-01#2 | 3 | 3 |  | gate_passed | 8 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 |
| S-ACUTE-02 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-02#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-02#1 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-03 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| S-ACUTE-03#0 | 0Y | 0Y | RF-02 | hard_stop | 3 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 |
| S-ACUTE-03#1 | 0Y | 0Y | RF-04 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| S-ACUTE-03#2 | — | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 DYSPNEA-ACUTE-01 PATTERN-01 EXERTION-01 |
| S-ACUTE-04 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-04#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-05 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-05#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-05#1 | — | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-06 | 0Y | 0Y | RF-01 | hard_stop_opening | 0 |  |
| S-ACUTE-06#0 | 0Y | 0Y | RF-01 | hard_stop_opening | 0 |  |
| S-STABLE-01 | 3 | 3 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 NTG-01 ANTIPLT-01 |
| S-STABLE-01#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 REST-01 |
| S-STABLE-01#1 | 0 | 0 |  | gate_passed | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 REST-01 THRESHOLD-01 THRESH-TIME-01 |
| S-STABLE-01#2 | 9 | 3 ⚠ |  | gate_passed | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 REST-01 DYSPNEA-ACUTE-01 PATTERN-01 NTG-01 ANTIPLT-01 |
| S-STABLE-02 | 3 | 3 |  | gate_passed | 9 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 REST-01 DYSPNEA-ACUTE-01 NTG-01 ANTIPLT-01 |
| S-STABLE-02#0 | — | 3 |  | gate_passed | 9 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 REST-01 DYSPNEA-ACUTE-01 NTG-01 ANTIPLT-01 |
| S-STABLE-02#1 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 REST-01 |
| S-STABLE-03 | 3 | 3 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SCREEN-01 |
| S-STABLE-03#0 | 0 | 9 ⚠ |  | max_questions | 11 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 REPRO-01 |
| S-STABLE-04 | 3 | 3 |  | gate_passed | 7 | SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 REST-01 DYSPNEA-ACUTE-01 NTG-01 |
| S-STABLE-04#0 | 0 | 0 |  | gate_passed | 4 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-STABLE-04#1 | 0 | 0 |  | gate_passed | 7 | SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 REST-01 THRESHOLD-01 THRESH-TIME-01 |
| S-INSUF-01 | 9 | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| S-INSUF-01#0 | 0 | 0 |  | gate_passed | 10 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DYSPNEA-ACUTE-01 PATTERN-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-01#1 | 3 | 3 |  | gate_passed | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 ANTIPLT-01 |
| S-INSUF-02 | 9 | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| S-INSUF-02#0 | 0 | 9 ⚠ |  | max_questions | 11 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 |
| S-INSUF-02#1 | 3 | 3 |  | gate_passed | 11 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 ANTIPLT-01 |
| S-INSUF-03 | 9 | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| S-INSUF-03#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-03#1 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-04 | 9 | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 PATTERN-01 PALP-01 POSTURAL-01 CONSULT-01 DRUGTIME-01 EDEMA-01 |
| S-INSUF-04#0 | 0Y | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| S-INSUF-04#1 | 0 | 2 ⚠ |  | gate_passed | 5 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 |
| S-INSUF-04#2 | 3 | 3 |  | gate_passed | 6 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DYSPNEA-ACUTE-01 PATTERN-01 ORTHO-01 SYNCOPE-01 |
| S-INSUF-05 | 9 | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 TIMING-01 PALP-01 POSTURAL-01 |
| S-INSUF-05#0 | 0 | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-05#1 | 3 | 3 |  | gate_passed | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 DYSPNEA-ACUTE-01 PATTERN-01 NTG-01 |
| S-INSUF-06 | 9 | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| S-INSUF-06#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-06#1 | 9 | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 |
| S-INSUF-07 | 9 | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| S-INSUF-07#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-INSUF-07#1 | 9 | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 REACHABLE-01 TIMING-01 |
| S-INSUF-08 | 9 | 9 |  | max_questions | 11 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 POSTURAL-01 |
| S-INSUF-08#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 THRESH-TIME-01 |
| S-INSUF-08#1 | 3 | 3 |  | gate_passed | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 REST-01 PATTERN-01 NTG-01 |
| S-MID-01 | 1 | 1 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 NTG-01 |
| S-MID-01#0 | 0 | 0 |  | gate_passed | 5 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-MID-01#1 | 2 | 2 |  | gate_passed | 8 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 REST-01 THRESHOLD-01 NTG-01 |
| S-MID-01#2 | 0Y | 0Y | RF-06 | hard_stop | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-02 | 2 | 2 |  | gate_passed | 5 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 TIMING-01 NTG-01 |
| S-MID-02#0 | 0 | 0 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 TIMING-01 THRESH-TIME-01 |
| S-MID-02#1 | 0 | 0 |  | gate_passed | 5 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 TIMING-01 |
| S-MID-02#2 | 0 | 0 |  | gate_passed | 4 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 TIMING-01 |
| S-MID-03 | 0 | 0 |  | gate_passed | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-03#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-MID-03#1 | 3 | 0 ⚠ |  | gate_passed | 8 | SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 THRESHOLD-01 DYSPNEA-ACUTE-01 PATTERN-01 NTG-01 |
| S-MID-04 | 3 | 3 |  | gate_passed | 3 | DYSPNEA-GRADE-01 SCREEN-01 SYNCOPE-01 |
| S-MID-04#0 | 1 | 1 |  | gate_passed | 10 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 REST-01 THRESHOLD-01 NTG-01 |
| S-MID-05 | 3 | 3 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-02 |
| S-MID-05#0 | 0Y | 0Y | RF-01 | hard_stop | 3 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 |
| S-MID-05#1 | 0 | 0 |  | gate_passed | 5 | DYSPNEA-GRADE-01 CHARACTER-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-MID-06 | 2 | 2 |  | gate_passed | 3 | DYSPNEA-SENTENCE-01 ORTHO-01 CHARACTER-01 |
| S-MID-06#0 | 0Y | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| S-MID-06#1 | 0 | 0 |  | gate_passed | 2 | DYSPNEA-SENTENCE-01 ORTHO-01 |
| S-MID-06#2 | 0 | 2 ⚠ |  | gate_passed | 4 | DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 CHARACTER-01 |
| S-MID-07 | 1 | 1 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 NTG-01 ANTIPLT-01 |
| S-MID-07#0 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESH-TIME-01 |
| S-MID-07#1 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESH-TIME-01 |
| S-MID-07#2 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-MID-08 | 3 | 3 |  | gate_passed | 9 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 TIMING-01 NTG-01 ANTIPLT-01 |
| S-MID-08#0 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 TIMING-01 |
| S-MID-08#1 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 TIMING-01 |
| S-MID-08#2 | 1 | 1 |  | gate_passed | 9 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 TIMING-01 NTG-01 ANTIPLT-01 |
| S-MID-09 | 1 | 1 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-09#0 | 0 | 0 |  | gate_passed | 6 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-MID-10 | 2 | 2 |  | gate_passed | 3 | SYNCOPE-02 DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-10#0 | 0Y | 0Y | RF-01 | hard_stop | 4 | SYNCOPE-02 DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 |
| S-MID-10#1 | 0Y | 0Y | RF-05 | hard_stop | 1 | SYNCOPE-02 |
| S-MID-11 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| S-MID-11#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-MID-11#1 | 0Y | 0 ⚠ |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| S-MID-12 | 2 | 2 |  | gate_passed | 3 | DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 |
| S-MID-12#0 | 0 | 0 |  | gate_passed | 2 | DYSPNEA-SENTENCE-01 ORTHO-01 |
| S-MID-12#1 | 0Y | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| S-MID-13 | 3 | 3 |  | gate_passed | 8 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 REST-01 THRESHOLD-01 NTG-01 ANTIPLT-01 |
| S-MID-13#0 | 0Y | 0Y | RF-06 | hard_stop | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-13#1 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-MID-13#2 | 0 | 9 ⚠ |  | max_questions | 11 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 TIMING-01 PALP-01 POSTURAL-01 |
| S-MID-14 | 3 | 3 |  | gate_passed | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 NTG-01 ANTIPLT-01 |
| S-MID-14#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 ONSET-01 |
| S-MID-14#1 | 0Y | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-15 | 4 | 4 |  | gate_passed | 3 | DYSPNEA-GRADE-01 SCREEN-01 SYNCOPE-01 |
| S-MID-15#0 | 1 | 1 |  | gate_passed | 10 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 REST-01 THRESHOLD-01 ANTIPLT-01 |
| S-MID-16 | 3 | 3 |  | gate_passed | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 NTG-01 ANTIPLT-01 |
| S-MID-16#0 | 0 | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 ONSET-01 TIMING-01 |
| S-MID-16#1 | 0Y | 0Y | RF-02 | hard_stop | 3 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 |
| S-MID-17 | 4 | 4 |  | gate_passed | 4 | DYSPNEA-GRADE-01 SCREEN-01 SYNCOPE-01 REACHABLE-01 |
| S-MID-17#0 | 9 | 9 |  | max_questions | 11 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DYSPNEA-ACUTE-01 PATTERN-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 EXERTION-01 |
| S-MID-17#1 | 0Y | 0Y | RF-03 | hard_stop | 4 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 ONGOING-01 |
| S-MID-18 | 4 | 4 |  | gate_passed | 3 | DYSPNEA-GRADE-01 SCREEN-01 SYNCOPE-01 |
| S-MID-18#0 | 0 | 0 |  | gate_passed | 7 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-MID-19 | 1 | 1 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 NTG-01 ANTIPLT-01 |
| S-MID-19#0 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 TIMING-01 |
| S-MID-19#1 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-MID-19#2 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-MID-19#3 | 0Y | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-20 | 4 | 4 |  | gate_passed | 3 | DYSPNEA-GRADE-01 SCREEN-01 SYNCOPE-01 |
| S-MID-20#0 | 3 | 3 |  | gate_passed | 6 | DYSPNEA-GRADE-01 PALP-01 POSTURAL-01 SCREEN-01 CONSULT-01 SYNCOPE-01 |
| S-MID-20#1 | 0 | 0 |  | gate_passed | 7 | DYSPNEA-GRADE-01 SCREEN-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
