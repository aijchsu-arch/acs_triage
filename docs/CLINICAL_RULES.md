# 臨床規則（Clinical Rules）

**rules_version**: 0.2.1 · 2026-10-10
**Clinical Owner**: Joseph（心臟內科）
**治理**：本文件與 `data/clinical_rules.yaml` 的任何變更，PR 必須由 Clinical Owner 核可，並 bump `rules_version`。Claude Code **不得**自行新增、刪除或改寫任何紅旗、閾值或等級定義；可以改措辭以外的事只有在 Clinical Owner 明確指示下進行。

來源：Claude Reviewer Prompt v0.2 + v0.2 盲性審查過程中 Clinical Owner 的裁定（含 2026-10-10 的呼吸困難分級與 Hard stop 規則、Tier 9 四列選項 A）。

---

## 1. 分流等級

| Tier | 名稱 | 定義 |
|---|---|---|
| 0 | T0 Emergency | 立即 EMS／急診緊急評估 |
| 1 | T1 Same-day | 當日必須接受醫療評估 |
| 2 | T2 24–72 h | 24–72 小時內快速評估 |
| 3 | T3 Routine | 一般門診追蹤 |
| 4 | T4 Self-care | 可先衛教／觀察，必須附 safety net |
| 9 | Unable to determine | 現有資訊不足，不能安全指定 0–4 |

- Tier 9 是**正確的臨床節制行為**，不是失敗。系統不得為了讓分布好看而避免 9。
- Hard stop（Y）只用於已足以立即啟動 EMS、不能為完成問診而延誤的情況。T0 不一定等於 Hard stop；Hard stop 一定是 T0。

---

## 2. 判斷原則（來自 Reviewer Prompt v0.2，原文意旨）

1. 新發、明顯惡化、活動閾值下降、開始在休息時出現，或合併明顯 instability 的 chest pain／anginal-equivalent presentation，通常需要 emergency evaluation。
2. 已知 CAD／prior PCI 本身不是 emergency trigger。
3. 病人已明確描述「長期固定、完全沒有近期變化、無休息時症狀、無新發 dyspnea／syncope」→ 可考慮 routine follow-up。
4. 來電開場沒有足夠資訊判斷「急性變化 vs 長期穩定」→ 不猜，Tier 9，並列出 decisive missing information。
5. 不因症狀輕微、沒有 literal chest pain、nitroglycerin 有效、先前 ECG 被說正常，就自行降低急迫度。
6. 工作是分流 urgency，不是診斷 ACS／MI。

---

## 3. 紅旗（Red Flags）＝ Stop Sign

命中任一條 → **立即 Hard stop**：推送腳本 S-HS、通報主管／護理師、停止問診。不等資訊足夠。

| RF | 條件 | 備註 |
|---|---|---|
| RF-01 | 胸部壓迫／疼痛／缺血等價症狀 **合併** 瀕厥或暈厥 | v0.2 審查中唯一判 Hard stop Y 的情境（ACS-LT-006 系列） |
| RF-02 | **靜止休息時仍有呼吸困難** | 即使同時存在心因性緊張／焦慮／恐慌的可能，仍一律 Y。不得因疑似焦慮下修。（Clinical Owner 2026-10-10 裁定） |
| RF-03 | 來電當下**症狀仍持續中**的胸部壓迫／疼痛或缺血等價症狀（下顎、左肩、上腹沉重等） | 對應審查表 boundary：「若確認目前仍持續發作 → Hard stop Y」 |
| RF-04 | 呼吸困難到**無法完整說完一句話**，或口唇發紺 | 對應審查表 C 組 boundary |
| RF-05 | 真正**意識喪失**（任何心臟相關症狀脈絡下） | RF-01 的加強版，獨立列出供規則比對 |

候選紅旗（**尚未裁定**，先不啟用，列在 `DECISIONS.md` Q-07）：
- 胸部不適合併明顯冒汗
- 單次發作 ≥ 20 分鐘未緩解（目前作為 RF-03 的子條件描述，是否獨立成條待定）

### 3.1 呼吸困難三段分級（追問程序）
客服依序確認，取最嚴重者：
1. 只有**激烈運動**時喘 →  `dyspnea_grade = exertional_heavy`
2. **普通日常勞動**即喘 → `dyspnea_grade = exertional_daily`
3. **靜止休息**時仍喘 → `dyspnea_grade = rest` → **RF-02 命中**

適用於：C 組（無胸痛急性呼吸困難）與 Tier 9 的「呼吸困難資訊不足」組。後者沒有「今日突發」前提，所以長期靜止喘者（例如 COPD）也會觸發 Y——這是 Clinical Owner 接受的敏感度優先取捨。

---

## 4. 不得降級規則（程式碼層強制）

| 規則 | 說明 |
|---|---|
| ND-01 | 任何模型輸出若比規則引擎結果更不急（tier 數字更大），取規則引擎結果，標記 `model_downgrade_blocked`。 |
| ND-02 | ECG 只能升級：`final = min(symptom_tier, ecg_tier)`；ECG 正常不產生任何降級或安撫語句。 |
| ND-03 | 病人自述「可能是藥物副作用」「可能是緊張」等主觀歸因，不得作為降級依據。 |
| ND-04 | 先前 ECG 正常、NTG 有效、症狀輕微、無 literal chest pain → 皆不得作為降級依據。 |
| ND-05 | 既往 CAD／PCI 本身不升級；但抗血小板藥物近期中斷是升級因子。 |

---

## 5. Tier 規則引擎（Phase 0 規則版）

### 5.1 Slot 清單（與 `data/question_bank_seed.yaml` 一致）
`onset_new`、`threshold_decreased`、`rest_symptom`、`rest_symptom_first_time`、`ongoing_now`、`episode_duration_min`、`presyncope`、`syncope`、`dyspnea_grade`、`dyspnea_acute`、`cant_finish_sentence`、`diaphoresis`、`nausea`、`orthopnea_pnd_edema`、`cad_history`、`pci_history`、`antiplatelet_interrupted`、`ntg_use_increased`、`pattern_unchanged_duration_months`、`symptom_character`、`exertion_relation`、`third_party_call`、`patient_reachable`、`drug_time_correlation`

### 5.2 Hard stop
任一 RF 命中（§3）→ `tier=0, hard_stop=True`。

### 5.3 T0（非 hard stop）
以下任一成立：
- `onset_new == true` 且症狀為胸部壓迫／缺血等價（新發心絞痛）
- `threshold_decreased == true`（閾值在數天內下降）
- `rest_symptom == true` 且 `rest_symptom_first_time == true`（新發休息時症狀）
- `dyspnea_acute == true`（今日突發且與基線明顯不同）
- `onset_new == true` 且症狀為下顎／左肩／上腹沉重（新發 anginal equivalent）

### 5.4 T3（Routine）
**全部**成立：
- `cad_history == true` 或已知穩定型態
- `pattern_unchanged_duration_months >= 6`（病人明確表述「長期相同、近期無變化」）
- `rest_symptom == false`
- 無新發 `dyspnea_acute`、`presyncope`、`syncope`
- `threshold_decreased == false`

或：行政性來電且病人明確否認新發胸悶、喘、暈（ACS-LT-027 系列）。

### 5.5 T1／T2／T4
**目前 benchmark 無情境，規則留空**。待 Clinical Owner 補中間帶情境後定義（`DECISIONS.md` Q-05）。在那之前，規則引擎只會輸出 0、3、9。

### 5.6 Tier 9（資訊不足）
以下任一：
- 無法判定 `onset_new` 與 `pattern_unchanged`（既不知新發也不知穩定）
- `symptom_character` 未定性（「怪怪的」「不太舒服」「說不上來」）
- `third_party_call == true` 且 `patient_reachable == false`
- 呼吸困難但 `dyspnea_grade` 與 `dyspnea_acute` 皆未知
- 問題數達 `MAX_QUESTIONS` 仍未滿足 §5.3／§5.4 任一

### 5.7 必要 slot 集合（Sufficiency Gate 用）
- 判 T0：至少一個 §5.3 條件的 slot 有高信心值 **且** 紅旗題（Q priority=redflag）已問完或已被回答。
- 判 T3：§5.4 全部 slot 有高信心值。
- 其他 → 不足。

---

## 6. 流程對照（六條）

| Tier | 流程 | 客服腳本 | 後續動作 | Safety net |
|---|---|---|---|---|
| Hard stop | 立即 EMS | S-HS | 唸稿、保持通話至確認已撥 119、通報主管／護理師 | — |
| 0 | 急診 | S-T0 | 指示立即前往急診或撥 119；通報護理師 | S-SN-A |
| 1 | 當日 | S-T1 | 轉護理師當日回撥／安排當日評估（門診或急診由護理師定） | S-SN-A |
| 2 | 24–72 h | S-T2 | 安排 24–72 h 快速門診 | S-SN-A |
| 3 | 一般門診 | S-T3 | 依例行排程 | S-SN-B |
| 4 | 自我照護 | S-T4 | 衛教腳本；必附 S-SN-A | S-SN-A |
| 9 | 轉護理師 | S-T9 | 同步轉接；不可同步時 ≤30 分鐘回撥。護理師不可得時的預設升級規則待定（Q-04） | S-SN-A |

Safety net 腳本：
- **S-SN-A**（強）：「如果接下來出現胸口壓迫感持續不退、坐著也會喘、快昏倒或昏倒、冒冷汗，請立刻撥打 119，不要再打客服。」
- **S-SN-B**（例行）：同上，但語氣為例行提醒。

腳本逐字內容由 Clinical Owner 與客服主管定稿，放 `data/scripts_zh.yaml`（M1）。

---

## 7. Benchmark v0.2 情境 → reviewer 標籤摘要

| 子模組 | 情境 | reviewer tier | HS | 升級／降級 boundary |
|---|---|---|---|---|
| 急性 | 新發活動時胸部壓迫 | 0 | N | 仍持續或休息時發作 → HS；多年不變 → T3 |
| 急性 | 穩定症狀突然惡化 | 0 | N | 休息時發作或 ≥20 min → HS；閾值已回復 → T1 |
| 急性 | 無胸痛急性呼吸困難 | 0 | N | 靜止仍喘／說話斷續／發紺 → HS；數週漸進 → 降級 |
| 急性 | 新發下顎不適 | 0 | N | 仍持續 → HS |
| 急性 | 休息時新症狀 | 0 | N | 仍在發作 → HS；一年來相同 → T2/T3 |
| 急性 | 急性症狀合併瀕厥 | 0 | **Y** | 即使純姿勢性頭暈仍不低於 T0 |
| 穩定 | 穩定運動性胸悶 | 3 | N | 休息時發作或閾值下降 → T0；無法確認範圍 → 9 |
| 穩定 | PCI 後穩定症狀 | 3 | N | 抗血小板中斷或休息時症狀 → T0/T1 |
| 穩定 | 已知 CAD 無症狀變化 | 3 | N | 補述任何新症狀 → 重新分流 |
| 穩定 | 長期固定運動誘發 | 3 | N | 休息時發作或誘發時間縮短 → T0 |
| 不足 | CAD 病史＋模糊胸悶 | 9 | N | 新發／閾值下降 → T0；長期相同 → T3 |
| 不足 | PCI 病史＋未描述變化 | 9 | N | 新發壓迫或休息時 → T0；多年相同 → T3 |
| 不足 | 胸部不適資訊不足 | 9 | N | 近期新發或休息時 → T0；多年固定 → T3 |
| 不足 | 呼吸困難資訊不足 | 9 | N | **靜止仍喘 → HS（即使疑似焦慮）**；今日突發 → T0；數月緩變 → T3 |
| 不足 | 運動症狀未給基線 | 9 | N | 近數週新發或閾值下降 → T0；長期固定 → T3 |
| 不足 | 遠端詢問用藥後不適 | 9 | N | 活動誘發或新發壓迫 → T0；與服藥時間一致且與活動無關 → T3 |
| 不足 | 家屬描述不完整 | 9 | N | 病人仍有持續不適或曾瀕厥／冒汗 → T0 + EMS |
| 不足 | 長期胸悶但近期狀態未知 | 9 | N | 閾值下降或休息時 → T0；近期完全相同 → T3 |

完整欄位見 `data/benchmark/v0.2/ACS_Claude_LowerTier_Review_Result_v0.2.csv`。這些是 **Claude v0.2 reviewer 的盲性標籤**，ground truth 待 Clinical Owner 裁定。
