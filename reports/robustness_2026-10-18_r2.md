# 穩健度：單一答案翻轉敏感度 — 2026-10-18

- 對 Scripted clean 每個 case 的每一輪，把答案換成另一個合法值（只換一題），重跑規則引擎；模擬 STT 聽反或病人答錯一題。
- 翻轉總數 1214；變得較不急 146（12.0%）；**嚴重降級（Hard stop／T0 → T1–T4）8**

## 降級轉移（原 → 翻轉後）

| 轉移 | 次數 |
|---|---|
| T0→T9 | 83 |
| HS→T9 | 29 |
| HS→T0 | 14 |
| T0→T4 | 4 |
| T9→T9 | 3 |
| T1→T3 | 3 |
| T3→T4 | 3 |
| T0→T3 | 2 |
| T0→T1 | 2 |
| T1→T4 | 2 |
| T1→T9 | 1 |

- T9 = 轉護理師（護理師不可得時依 C6 D 預設等級）；HS→T0 仍叫去急診，但少了「留在線上直到撥 119」。

## 嚴重降級明細（8）

- S-STABLE-03#0：Q-CHARACTER-01 pressure → other（T0→T3）
- S-STABLE-03#0：Q-CHARACTER-01 pressure → none（T0→T3）
- S-MID-09#0：Q-CHARACTER-01 pressure → other（T0→T1）
- S-MID-09#0：Q-CHARACTER-01 pressure → none（T0→T1）
- S-MID-18#0：Q-CHARACTER-01 jaw_shoulder_heaviness → other（T0→T4）
- S-MID-18#0：Q-CHARACTER-01 jaw_shoulder_heaviness → none（T0→T4）
- S-MID-20#1：Q-CHARACTER-01 pressure → other（T0→T4）
- S-MID-20#1：Q-CHARACTER-01 pressure → none（T0→T4）

## 最容易因一個答案翻錯而降級的題目

| 題目 | 優先級 | 降級／翻轉 |
|---|---|---|
| Q-TIMING-01 | decisive | 32/147 |
| Q-CHARACTER-01 | decisive | 26/127 |
| Q-DYSPNEA-GRADE-01 | redflag | 19/305 |
| Q-ONSET-01 | decisive | 14/44 |
| Q-ONGOING-01 | redflag | 10/80 |
| Q-REST-01 | decisive | 9/50 |
| Q-EXERTION-01 | decisive | 9/47 |
| Q-THRESH-TIME-01 | decisive | 5/12 |
| Q-DIAPH-01 | redflag | 4/76 |
| Q-THRESHOLD-01 | decisive | 4/45 |
| Q-SYNCOPE-01 | redflag | 3/91 |
| Q-CONSULT-01 | decisive | 3/16 |

## 紅旗題「有」被聽成「沒有」

| 題目 | 降級／答有的輪數 |
|---|---|
| Q-ONGOING-01 | 10/10 |
| Q-DYSPNEA-SENTENCE-01 | 2/2 |
| Q-DIAPH-01 | 4/4 |
| Q-SYNCOPE-01 | 2/2 |
| Q-SYNCOPE-02 | 1/1 |
