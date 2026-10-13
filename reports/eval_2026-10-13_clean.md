# Phase 0 評估報告 — mode=clean seed=0

- 日期：2026-10-13　rules_version：0.3.2
- cases：119（可評分 116；`expect.tier: null` 的變體不計分）
- 模擬病人：ScriptedPatient（確定性腳本；LLM 病人為 M2b）

## 核心安全指標

| 指標 | 值 | 目標 |
|---|---|---|
| Hard-stop miss rate | 0.0%（0/27） | 0% |
| Hard-stop latency（最大） | 0 句 | 0 句 |
| Hard-stop false alarm | 0 | 記錄 |
| Under-triage rate | 0.0%（0） | 趨近 0 |
| Over-triage rate | 0.0%（0） | 記錄 |
| Tier exact accuracy | 100.0% | 記錄 |
| Escalating-question recall（答案可能使分流更急的題目） | 86.5%（455/526） | ≥ 90% |
| Decisive-question recall（答案會改變分流的題目，含只會降級者） | 81.5%（625/767） | 記錄 |
| Abstention precision / recall | 100.0% / 100.0% | 記錄 |
| Questions-to-decision（平均） | 4.9 | 記錄 |
| Gate effect（低信心重問次數） | 0 | 記錄 |

## 混淆矩陣（truth → pred）

| truth \ pred | 0 | 1 | 2 | 3 | 4 | 9 |
|---|---|---|---|---|---|---|
| **0** | 70 | 0 | 0 | 0 | 0 | 0 |
| **1** | 0 | 7 | 0 | 0 | 0 | 0 |
| **2** | 0 | 0 | 5 | 0 | 0 | 0 |
| **3** | 0 | 0 | 0 | 18 | 0 | 0 |
| **4** | 0 | 0 | 0 | 0 | 4 | 0 |
| **9** | 0 | 0 | 0 | 0 | 0 | 12 |

## 依模組

| module | n | exact | under | over | abstain_fp | abstain_fn |
|---|---|---|---|---|---|---|
| acute | 16 | 16 | 0 | 0 | 0 | 0 |
| insufficient | 25 | 25 | 0 | 0 | 0 | 0 |
| midband | 64 | 64 | 0 | 0 | 0 | 0 |
| stable | 11 | 11 | 0 | 0 | 0 | 0 |

## 指標說明

- Under/Over-triage 只計 truth 與 pred 皆在 0–4 的案例；pred 9 另計 abstention FP、truth 9 另計 abstention FN。
- Hard-stop latency = 揭露紅旗事實的那句與觸發 Hard stop 之間相隔的句數；引擎逐句重算，理論上恆為 0。
- Decisive／Escalating 題目由 `sim/decisive.py` 依每個 case 的完整事實逐題反事實計算（D-27）：
  把該題換成任一可能答案，若 (provisional_tier, hard_stop) 會改變即為 decisive；其中存在答案使結果**更急**者為 escalating。
  Tier 9 依 C6 D 主訴對照表換算急迫度。Escalating 漏問 = 可能 under-triage，是安全指標；只會降級的題漏問只造成 over-triage。
- 資訊不足組（persona vague）的 base case 以 `max_questions` 結束並維持 Tier 9 是**預期行為**（節制），不是失敗。

## 結束原因

- gate_passed: 77
- hard_stop: 25
- hard_stop_opening: 2
- max_questions: 15

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

## 漏問的 escalating 題目（71）

| 題目 | 漏問次數 |
|---|---|
| Q-NTG-01 | 33 |
| Q-THRESHOLD-01 | 9 |
| Q-PENDINGTEST-01 | 7 |
| Q-POSTURAL-01 | 6 |
| Q-PALP-01 | 4 |
| Q-TIMING-01 | 3 |
| Q-REST-01 | 3 |
| Q-ONSET-01 | 2 |
| Q-ORTHO-01 | 1 |
| Q-REST-02 | 1 |
| Q-ONSET-WEEKS-01 | 1 |
| Q-REACHABLE-01 | 1 |

明細（case, 題目, final tier, 結束原因）：

- ('S-ACUTE-01#2', 'Q-NTG-01', 3, 'gate_passed')
- ('S-ACUTE-03#2', 'Q-ORTHO-01', 9, 'max_questions')
- ('S-ACUTE-05#1', 'Q-ONSET-01', 0, 'gate_passed')
- ('S-ACUTE-05#1', 'Q-THRESHOLD-01', 0, 'gate_passed')
- ('S-ACUTE-05#1', 'Q-REST-02', 0, 'gate_passed')
- ('S-ACUTE-05#1', 'Q-NTG-01', 0, 'gate_passed')
- ('S-STABLE-01', 'Q-NTG-01', 3, 'gate_passed')
- ('S-STABLE-01#2', 'Q-NTG-01', 9, 'max_questions')
- ('S-STABLE-02', 'Q-NTG-01', 3, 'gate_passed')
- ('S-STABLE-02#0', 'Q-NTG-01', 3, 'gate_passed')
- ('S-STABLE-03', 'Q-POSTURAL-01', 3, 'gate_passed')
- ('S-STABLE-03', 'Q-PENDINGTEST-01', 3, 'gate_passed')
- ('S-STABLE-04', 'Q-NTG-01', 3, 'gate_passed')
- ('S-INSUF-01', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-01#1', 'Q-NTG-01', 3, 'gate_passed')
- ('S-INSUF-02', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-02#1', 'Q-NTG-01', 3, 'gate_passed')
- ('S-INSUF-03', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-05', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-05#1', 'Q-NTG-01', 3, 'gate_passed')
- ('S-INSUF-06', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-06#1', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-07', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-07#1', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-08', 'Q-NTG-01', 9, 'max_questions')
- ('S-INSUF-08#1', 'Q-NTG-01', 3, 'gate_passed')
- ('S-MID-01', 'Q-THRESHOLD-01', 1, 'gate_passed')
- ('S-MID-01', 'Q-NTG-01', 1, 'gate_passed')
- ('S-MID-01#1', 'Q-THRESHOLD-01', 2, 'gate_passed')
- ('S-MID-01#1', 'Q-NTG-01', 2, 'gate_passed')
- ('S-MID-02', 'Q-TIMING-01', 2, 'gate_passed')
- ('S-MID-02', 'Q-NTG-01', 2, 'gate_passed')
- ('S-MID-03#1', 'Q-NTG-01', 3, 'gate_passed')
- ('S-MID-04', 'Q-POSTURAL-01', 3, 'gate_passed')
- ('S-MID-04', 'Q-PENDINGTEST-01', 3, 'gate_passed')
- ('S-MID-04#0', 'Q-THRESHOLD-01', 1, 'gate_passed')
- ('S-MID-04#0', 'Q-NTG-01', 1, 'gate_passed')
- ('S-MID-07', 'Q-ONSET-01', 1, 'gate_passed')
- ('S-MID-07', 'Q-NTG-01', 1, 'gate_passed')
- ('S-MID-08', 'Q-TIMING-01', 3, 'gate_passed')
- ('S-MID-08', 'Q-ONSET-WEEKS-01', 3, 'gate_passed')
- ('S-MID-08', 'Q-NTG-01', 3, 'gate_passed')
- ('S-MID-08#2', 'Q-NTG-01', 1, 'gate_passed')
- ('S-MID-13', 'Q-THRESHOLD-01', 3, 'gate_passed')
- ('S-MID-13', 'Q-REST-01', 3, 'gate_passed')
- ('S-MID-13', 'Q-NTG-01', 3, 'gate_passed')
- ('S-MID-14', 'Q-THRESHOLD-01', 3, 'gate_passed')
- ('S-MID-14', 'Q-REST-01', 3, 'gate_passed')
- ('S-MID-14', 'Q-NTG-01', 3, 'gate_passed')
- ('S-MID-15', 'Q-PALP-01', 4, 'gate_passed')
- ('S-MID-15', 'Q-POSTURAL-01', 4, 'gate_passed')
- ('S-MID-15', 'Q-PENDINGTEST-01', 4, 'gate_passed')
- ('S-MID-15#0', 'Q-THRESHOLD-01', 1, 'gate_passed')
- ('S-MID-16', 'Q-THRESHOLD-01', 3, 'gate_passed')
- ('S-MID-16', 'Q-REST-01', 3, 'gate_passed')
- ('S-MID-16', 'Q-TIMING-01', 3, 'gate_passed')
- ('S-MID-16', 'Q-NTG-01', 3, 'gate_passed')
- ('S-MID-17', 'Q-REACHABLE-01', 4, 'gate_passed')
- ('S-MID-17', 'Q-PALP-01', 4, 'gate_passed')
- ('S-MID-17', 'Q-POSTURAL-01', 4, 'gate_passed')
- ('S-MID-17', 'Q-PENDINGTEST-01', 4, 'gate_passed')
- ('S-MID-17#0', 'Q-NTG-01', 9, 'max_questions')
- ('S-MID-18', 'Q-PALP-01', 4, 'gate_passed')
- ('S-MID-18', 'Q-POSTURAL-01', 4, 'gate_passed')
- ('S-MID-18', 'Q-PENDINGTEST-01', 4, 'gate_passed')
- ('S-MID-19', 'Q-THRESHOLD-01', 1, 'gate_passed')
- ('S-MID-19', 'Q-NTG-01', 1, 'gate_passed')
- ('S-MID-20', 'Q-PALP-01', 4, 'gate_passed')
- ('S-MID-20', 'Q-POSTURAL-01', 4, 'gate_passed')
- ('S-MID-20', 'Q-PENDINGTEST-01', 4, 'gate_passed')
- ('S-MID-20#0', 'Q-PENDINGTEST-01', 3, 'gate_passed')

## 每案摘要

| case | truth | final | HS | stop | Q | 問到的題 |
|---|---|---|---|---|---|---|
| S-ACUTE-01 | 0 | 0 |  | gate_passed | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-01#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-01#1 | 0 | 0 |  | gate_passed | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-01#2 | 3 | 3 |  | gate_passed | 7 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 |
| S-ACUTE-02 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-02#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-02#1 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-03 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| S-ACUTE-03#0 | 0Y | 0Y | RF-02 | hard_stop | 3 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 |
| S-ACUTE-03#1 | 0Y | 0Y | RF-04 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| S-ACUTE-03#2 | — | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 DYSPNEA-ACUTE-01 PATTERN-01 |
| S-ACUTE-04 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-04#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-05 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-05#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-ACUTE-05#1 | — | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-ACUTE-06 | 0Y | 0Y | RF-01 | hard_stop_opening | 0 |  |
| S-ACUTE-06#0 | 0Y | 0Y | RF-01 | hard_stop_opening | 0 |  |
| S-STABLE-01 | 3 | 3 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 ANTIPLT-01 |
| S-STABLE-01#0 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-STABLE-01#1 | 0 | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 THRESH-TIME-01 |
| S-STABLE-01#2 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 PATTERN-01 TIMING-01 PALP-01 POSTURAL-01 REPRO-01 |
| S-STABLE-02 | 3 | 3 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 ANTIPLT-01 |
| S-STABLE-02#0 | — | 3 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 ANTIPLT-01 |
| S-STABLE-02#1 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-STABLE-03 | 3 | 3 |  | gate_passed | 1 | DYSPNEA-GRADE-01 |
| S-STABLE-03#0 | 0 | 0 |  | max_questions | 10 | DYSPNEA-GRADE-01 CHARACTER-01 DIAPH-01 ONSET-01 TIMING-01 THRESHOLD-01 REST-01 EXERTION-01 ONSET-WEEKS-01 PALP-01 |
| S-STABLE-04 | 3 | 3 |  | gate_passed | 4 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-STABLE-04#0 | 0 | 0 |  | gate_passed | 4 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-STABLE-04#1 | 0 | 0 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 THRESH-TIME-01 |
| S-INSUF-01 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 |
| S-INSUF-01#0 | 0 | 0 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-01#1 | 3 | 3 |  | gate_passed | 9 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 ANTIPLT-01 |
| S-INSUF-02 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 |
| S-INSUF-02#0 | 0 | 0 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-02#1 | 3 | 3 |  | gate_passed | 10 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 ANTIPLT-01 |
| S-INSUF-03 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 |
| S-INSUF-03#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-03#1 | 0 | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 |
| S-INSUF-04 | 9 | 9 |  | max_questions | 10 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DYSPNEA-ACUTE-01 PATTERN-01 CHARACTER-01 ORTHO-01 PALP-01 POSTURAL-01 CONSULT-01 DRUGTIME-01 |
| S-INSUF-04#0 | 0Y | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| S-INSUF-04#1 | 0 | 0 |  | max_questions | 10 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DYSPNEA-ACUTE-01 PATTERN-01 CHARACTER-01 ORTHO-01 PALP-01 POSTURAL-01 CONSULT-01 DRUGTIME-01 |
| S-INSUF-04#2 | 3 | 3 |  | gate_passed | 6 | DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 DYSPNEA-ACUTE-01 PATTERN-01 ORTHO-01 SYNCOPE-01 |
| S-INSUF-05 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 TIMING-01 PALP-01 |
| S-INSUF-05#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-05#1 | 3 | 3 |  | gate_passed | 8 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 |
| S-INSUF-06 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 |
| S-INSUF-06#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-INSUF-06#1 | 9 | 9 |  | max_questions | 10 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 |
| S-INSUF-07 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 |
| S-INSUF-07#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-INSUF-07#1 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 REACHABLE-01 |
| S-INSUF-08 | 9 | 9 |  | max_questions | 10 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 TIMING-01 PALP-01 |
| S-INSUF-08#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 THRESH-TIME-01 |
| S-INSUF-08#1 | 3 | 3 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 REST-01 PATTERN-01 |
| S-MID-01 | 1 | 1 |  | gate_passed | 4 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-MID-01#0 | 0 | 0 |  | gate_passed | 5 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-MID-01#1 | 2 | 2 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ONSET-01 TIMING-01 REST-01 |
| S-MID-01#2 | 0Y | 0Y | RF-06 | hard_stop | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-02 | 2 | 2 |  | gate_passed | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-02#0 | 0 | 0 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 TIMING-01 THRESH-TIME-01 |
| S-MID-02#1 | 0 | 0 |  | gate_passed | 5 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 TIMING-01 |
| S-MID-02#2 | 0 | 0 |  | gate_passed | 4 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 TIMING-01 |
| S-MID-03 | 0 | 0 |  | gate_passed | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-03#0 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-MID-03#1 | 3 | 3 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESHOLD-01 PATTERN-01 ANTIPLT-01 |
| S-MID-04 | 3 | 3 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-04#0 | 1 | 1 |  | gate_passed | 7 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 REST-01 |
| S-MID-05 | 3 | 3 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-02 |
| S-MID-05#0 | 0Y | 0Y | RF-01 | hard_stop | 3 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 |
| S-MID-05#1 | 0 | 0 |  | gate_passed | 5 | DYSPNEA-GRADE-01 CHARACTER-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-MID-06 | 2 | 2 |  | gate_passed | 3 | DYSPNEA-SENTENCE-01 ORTHO-01 CHARACTER-01 |
| S-MID-06#0 | 0Y | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| S-MID-06#1 | 0 | 0 |  | gate_passed | 2 | DYSPNEA-SENTENCE-01 ORTHO-01 |
| S-MID-06#2 | 0 | 0 |  | gate_passed | 3 | DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 |
| S-MID-07 | 1 | 1 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ANTIPLT-01 |
| S-MID-07#0 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESH-TIME-01 |
| S-MID-07#1 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 THRESH-TIME-01 |
| S-MID-07#2 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-MID-08 | 3 | 3 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 ANTIPLT-01 |
| S-MID-08#0 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 TIMING-01 |
| S-MID-08#1 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 TIMING-01 |
| S-MID-08#2 | 1 | 1 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 THRESHOLD-01 ANTIPLT-01 |
| S-MID-09 | 1 | 1 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-09#0 | 0 | 0 |  | gate_passed | 6 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-MID-10 | 2 | 2 |  | gate_passed | 3 | SYNCOPE-02 DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-10#0 | 0Y | 0Y | RF-01 | hard_stop | 4 | SYNCOPE-02 DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 |
| S-MID-10#1 | 0Y | 0Y | RF-05 | hard_stop | 1 | SYNCOPE-02 |
| S-MID-11 | 0 | 0 |  | gate_passed | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| S-MID-11#0 | 0Y | 0Y | RF-02 | hard_stop | 3 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 |
| S-MID-11#1 | 0Y | 0Y | RF-04 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DYSPNEA-SENTENCE-01 |
| S-MID-12 | 2 | 2 |  | gate_passed | 3 | DYSPNEA-SENTENCE-01 ORTHO-01 DYSPNEA-ACUTE-01 |
| S-MID-12#0 | 0 | 0 |  | gate_passed | 2 | DYSPNEA-SENTENCE-01 ORTHO-01 |
| S-MID-12#1 | 0Y | 0Y | RF-02 | hard_stop | 1 | DYSPNEA-GRADE-01 |
| S-MID-13 | 3 | 3 |  | gate_passed | 5 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 ANTIPLT-01 |
| S-MID-13#0 | 0Y | 0Y | RF-06 | hard_stop | 3 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-13#1 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-MID-13#2 | 0 | 0 |  | gate_passed | 6 | SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 ONSET-01 TIMING-01 |
| S-MID-14 | 3 | 3 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ANTIPLT-01 |
| S-MID-14#0 | 0 | 0 |  | gate_passed | 6 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 ONSET-01 |
| S-MID-14#1 | 0Y | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-15 | 4 | 4 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-15#0 | 1 | 1 |  | gate_passed | 8 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 REST-01 ANTIPLT-01 |
| S-MID-16 | 3 | 3 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ANTIPLT-01 |
| S-MID-16#0 | 0 | 0 |  | gate_passed | 7 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 EXERTION-01 ONSET-01 TIMING-01 |
| S-MID-16#1 | 0Y | 0Y | RF-02 | hard_stop | 3 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 |
| S-MID-17 | 4 | 4 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-17#0 | 9 | 9 |  | max_questions | 10 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 THRESHOLD-01 REST-01 PATTERN-01 EXERTION-01 REACHABLE-01 |
| S-MID-17#1 | 0Y | 0Y | RF-03 | hard_stop | 3 | DYSPNEA-GRADE-01 CHARACTER-01 ONGOING-01 |
| S-MID-18 | 4 | 4 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-18#0 | 0 | 0 |  | gate_passed | 6 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
| S-MID-19 | 1 | 1 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 ANTIPLT-01 |
| S-MID-19#0 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 TIMING-01 |
| S-MID-19#1 | 0 | 0 |  | gate_passed | 5 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 REST-01 |
| S-MID-19#2 | 0Y | 0Y | RF-03 | hard_stop | 1 | ONGOING-01 |
| S-MID-19#3 | 0Y | 0Y | RF-06 | hard_stop | 4 | ONGOING-01 SYNCOPE-01 DYSPNEA-GRADE-01 DIAPH-01 |
| S-MID-20 | 4 | 4 |  | gate_passed | 2 | DYSPNEA-GRADE-01 SYNCOPE-01 |
| S-MID-20#0 | 3 | 3 |  | gate_passed | 5 | DYSPNEA-GRADE-01 PALP-01 POSTURAL-01 CONSULT-01 SYNCOPE-01 |
| S-MID-20#1 | 0 | 0 |  | gate_passed | 6 | DYSPNEA-GRADE-01 CHARACTER-01 SYNCOPE-01 DIAPH-01 ONSET-01 TIMING-01 |
