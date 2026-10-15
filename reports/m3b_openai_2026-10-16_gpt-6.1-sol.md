# M3b：OpenAI vs 規則引擎（shadow）— 2026-10-16

- 模型：要求 `gpt-6.1-sol` effort=medium，回應 model：gpt-6.1-sol；prompts_version 0.3；rules 0.5.1
- cases：119；紅旗步數 772；分級 119；錯誤 0

## 逐句紅旗（每步判斷到目前為止的對話；正確答案 = 規則引擎）

| RF | TP | FN | FP | TN | 敏感度 | 特異度 |
|---|---|---|---|---|---|---|
| RF-01 | 4 | 0 | 1 | 767 | 100.0% | 99.9% |
| RF-02 | 6 | 0 | 0 | 766 | 100.0% | 100.0% |
| RF-03 | 10 | 0 | 7 | 755 | 100.0% | 99.1% |
| RF-04 | 2 | 0 | 0 | 770 | 100.0% | 100.0% |
| RF-05 | 1 | 0 | 0 | 771 | 100.0% | 100.0% |
| RF-06 | 3 | 1 | 0 | 768 | 75.0% | 100.0% |

- 規則判紅旗成立的步數 27；模型漏掉 1；模型多判（規則未成立）8——若接進決策（規則 OR 模型），多判的會變成額外 Hard stop。

### 紅旗不一致的步（9）

- S-STABLE-03#0 第 3 步：規則 無／模型 ['RF-03']
- S-MID-04#0 第 3 步：規則 無／模型 ['RF-03']
- S-MID-10#0 第 4 步：規則 無／模型 ['RF-01']
- S-MID-13#0 第 3 步：規則 ['RF-06']／模型 無
- S-MID-14 第 0 步：規則 無／模型 ['RF-03']
- S-MID-14#0 第 0 步：規則 無／模型 ['RF-03']
- S-MID-14#1 第 0 步：規則 無／模型 ['RF-03']
- S-MID-17#1 第 3 步：規則 無／模型 ['RF-03']
- S-MID-18#0 第 3 步：規則 無／模型 ['RF-03']

## 分級（與 Jev 相同題目、第二版輸入）

| 指標 | 值 |
|---|---|
| 與規則完全一致 | 77/119 |
| 模型比規則不急（ND-01 會擋） | 16 |
| 模型比規則更急 | 24 |
| 模型判 T9 | 44 |
| 模型 vs truth exact／under／over | 75／16／23 |
| 「資訊足夠」與規則一致 | 88/119 |

- S-ACUTE-01#2：truth 3，規則 3，模型 9（model_more_urgent）
- S-STABLE-01：truth 3，規則 3，模型 9（model_more_urgent）
- S-STABLE-01#1：truth 0，規則 0，模型 9（model_less_urgent）
- S-STABLE-02#0：truth None，規則 3，模型 9（model_more_urgent）
- S-STABLE-04#1：truth 0，規則 0，模型 9（model_less_urgent）
- S-INSUF-04#0：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-INSUF-04#2：truth 3，規則 3，模型 9（model_more_urgent）
- S-INSUF-05#1：truth 3，規則 3，模型 9（model_more_urgent）
- S-INSUF-06#0：truth 0，規則 0，模型 9（model_less_urgent）
- S-INSUF-07#0：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-INSUF-08#1：truth 3，規則 3，模型 9（model_more_urgent）
- S-MID-01：truth 1，規則 1，模型 9（same_urgency_diff_tier）
- S-MID-01#1：truth 2，規則 2，模型 0（model_more_urgent）
- S-MID-01#2：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-MID-02：truth 2，規則 2，模型 0（model_more_urgent）
- S-MID-04：truth 3，規則 3，模型 1（model_more_urgent）
- S-MID-04#0：truth 1，規則 1，模型 0（model_more_urgent）
- S-MID-05：truth 3，規則 3，模型 9（model_more_urgent）
- S-MID-06：truth 2，規則 2，模型 0（model_more_urgent）
- S-MID-07：truth 1，規則 1，模型 0（model_more_urgent）
- S-MID-08：truth 3，規則 3，模型 0（model_more_urgent）
- S-MID-08#2：truth 1，規則 1，模型 0（model_more_urgent）
- S-MID-09：truth 1，規則 1，模型 9（model_less_urgent）
- S-MID-10：truth 2，規則 2，模型 9（same_urgency_diff_tier）
- S-MID-10#0：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-MID-11：truth 0，規則 0，模型 9（model_less_urgent）
- S-MID-12：truth 2，規則 2，模型 9（model_more_urgent）
- S-MID-12#0：truth 0，規則 0，模型 9（model_less_urgent）
- S-MID-12#1：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-MID-13：truth 3，規則 3，模型 9（model_more_urgent）
- S-MID-13#0：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-MID-13#1：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-MID-14：truth 3，規則 3，模型 9（model_more_urgent）
- S-MID-14#1：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-MID-15：truth 4，規則 4，模型 9（model_more_urgent）
- S-MID-15#0：truth 1，規則 1，模型 0（model_more_urgent）
- S-MID-16：truth 3，規則 3，模型 9（model_more_urgent）
- S-MID-16#1：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-MID-17：truth 4，規則 4，模型 9（model_more_urgent）
- S-MID-17#1：truth 0，規則 0Y，模型 9（model_less_urgent）
- S-MID-18：truth 4，規則 4，模型 3（model_more_urgent）
- S-MID-19：truth 1，規則 1，模型 0（model_more_urgent）

## 費用（依牌價估算，以帳單為準；output 含 reasoning tokens）

- 本次實際：紅旗 US$1.5365、分級 US$0.2352，合計 US$1.7716
- 每次呼叫平均：紅旗 US$0.00199、分級 US$0.00198
- **全量推估**（119 cases、紅旗 772 步）：紅旗 US$1.54 ＋ 分級 US$0.24 ＋ slot 抽取（尚未實作，以紅旗每次費用 × 653 輪推估）US$1.30 ＝ **US$3.07**

## 執行錯誤（0）

（無）
