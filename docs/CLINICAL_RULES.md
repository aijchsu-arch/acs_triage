# 臨床規則（Clinical Rules）

**rules_version**: 0.5.1 · 2026-10-15（D-35：`rest_symptom` 餐後判定定義；判定邏輯不變）
**Clinical Owner**: Joseph（心臟內科）
**治理**：本文件與 `data/clinical_rules.yaml` 的任何變更，PR 必須由 Clinical Owner 核可，並 bump `rules_version`。Claude Code **不得**自行新增、刪除或改寫任何紅旗、閾值或等級定義；可以改措辭以外的事只有在 Clinical Owner 明確指示下進行。

來源：Claude Reviewer Prompt v0.2；v0.2 盲性審查過程中 Clinical Owner 的裁定（2026-10-10）；問卷 `ADJUDICATION_Q05_Q11.md` Part A／B／C 的裁定（2026-10-10 至 2026-10-12）。

**標記說明**：`(DV-n)` = 由 Clinical Owner 給的個案標籤反推出的門檻，已於 §9 確認。目前無待確認項。

---

## 1. 分流等級

| Tier | 名稱 | 定義 |
|---|---|---|
| 0 | T0 Emergency | 立即 EMS／急診緊急評估 |
| 1 | T1 Same-day | 當日必須接受醫療評估 |
| 2 | T2 24–72 h | 24–72 小時內快速評估 |
| 3 | T3 Routine | 一般門診追蹤（可附 `expedite` 動作提前） |
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
| RF-02 | **靜止休息時仍有呼吸困難** | 即使同時存在心因性緊張／焦慮／恐慌的可能，仍一律 Y。不得因疑似焦慮下修。（D-07） |
| RF-03 | 來電當下**症狀仍持續中**的胸部壓迫／疼痛或缺血等價症狀（下顎、左肩、上腹沉重等） | 對應審查表 boundary：「若確認目前仍持續發作 → Hard stop Y」 |
| RF-04 | 呼吸困難到**無法完整說完一句話**，或口唇發紺 | 對應審查表 C 組 boundary |
| RF-05 | 真正**意識喪失**（任何心臟相關症狀脈絡下） | RF-01 的加強版，獨立列出供規則比對 |
| RF-06 | 胸部不適／缺血等價症狀 **合併明顯冒汗**（diaphoresis） | C5 A（2026-10-12）。單獨冒汗不構成；需與胸部不適或缺血等價症狀同時出現 |

**不是紅旗、但一律 T0 的情況**（C1 B）：端坐呼吸（orthopnea）或夜間陣發性呼吸困難（PND）**不算 RF-02**，不觸發 Hard stop，但一律升至 T0（見 §5.3）。

候選紅旗（**尚未裁定**，先不啟用，`DECISIONS.md` Q-07）：
- 單次發作 ≥ 20 分鐘未緩解（目前作為 RF-03 的子條件描述，是否獨立成條待定）

### 3.1 呼吸困難三段分級（追問程序）
客服依序確認，取最嚴重者：
1. 只有**激烈運動**時喘 → `dyspnea_grade = exertional_heavy`
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
| ND-05 | 既往 CAD／PCI 本身不升級。抗血小板藥物近期中斷：**有症狀**時是升級因子；**無症狀**時 → T3 並附 `expedite` 動作（C7 C）。 |

---

## 5. Tier 規則引擎（Phase 0 規則版）

評估順序：§5.2 Hard stop → §5.3 T0 → §5.9 Sufficiency（不足 → Tier 9）→ §5.4 T1 → §5.5 T2 → §5.6 T3 → §5.7 T4 → 否則 Tier 9。
T0 永遠先於其他等級評估；§5.6 的 T3 carve-out 只在 **T0 條件全部不成立**時才生效。

### 5.1 Slot 清單
與 `data/question_bank_seed.yaml` 一致。v0.3.0 變更：`orthopnea_pnd_edema` 拆為 `orthopnea_pnd` 與 `edema`；新增 `last_episode_timing`、`recurrence`、`onset_weeks_ago`、`threshold_decrease_timescale`、`palpitations`、`postural_dizziness`、`new_medication_recent`、`reproducible_mechanical`、`cough_related`、`postprandial_relieved`、`pending_abnormal_test`、`consult_topic`、`recent_pci_months`、`symptom_vs_pre_pci`。

「缺血等價症狀」= `symptom_character ∈ {pressure, tightness, pain, jaw_shoulder_heaviness, epigastric}`。

### 5.2 Hard stop
任一 RF 命中（§3）→ `tier=0, hard_stop=True`。

### 5.3 T0（非 hard stop）
以下任一成立：
- 新發缺血等價症狀且 `last_episode_timing ∈ {today, ongoing}`（含「今天第一次」已緩解者；A1、A4）(DV-1)。病人答「現在還在」→ 同時視為 `ongoing_now=true`（RF-03）（Q-14g）
  - **時序與豁免（Q-14d C）**：非缺血型豁免（§5.6 刺痛可重現、刺痛咳嗽、上腹餐後）不論時序一律適用、不進 T0；勞累型豁免（DV-2 新發穩定 ≥2 週、DV-4 PCI 後較輕）**只在時序不明時**適用——病人明確說今天或仍在發作 → T0。
- `threshold_decreased == true` 且 `threshold_decrease_timescale ∈ {days, unknown}`（C3 B；A2）
- `rest_symptom == true` 且 `rest_symptom_first_time == true`（新發休息時症狀；A5）
  - **`rest_symptom` 餐後判定（D-35）**：吃飽後胸口不適，**快速緩解**（如打嗝後就好）不算 `rest_symptom`（可適用 §5.6 DV-5 carve-out）；**沒有快速緩解** → `rest_symptom = true`，依本條判定（首次 → T0）。
- `dyspnea_acute == true`（今日突發且與基線明顯不同；A3）
- `ntg_use_increased == true`（NTG 用量明顯增加，即使仍為勞累性；C4 A；B3）。指**既有型態下**用量增加；新發病人首次使用不算（B19）(DV-6)
- `orthopnea_pnd == true`（端坐呼吸／PND；C1 B；B11）

### 5.4 T1（Same-day）
T0 不成立，且以下任一：
- 新發缺血等價症狀、已緩解、`last_episode_timing == yesterday_within_24h`、今日無發作（B1 單次；B19 兩天內多次亦同）(DV-1)。若確認為休息時首次發作，§5.3 T0 優先。非缺血型豁免除外（Q-14d C）
- `threshold_decreased == true` 且 `threshold_decrease_timescale == weeks_to_month`（C3 B；B7）
- `pending_abnormal_test == true` 且目前無症狀（檢查異常待追蹤未掛號；B9）
- 新發缺血等價症狀 + `antiplatelet_interrupted == true`（ND-05 有症狀分支）(DV-3)

### 5.5 T2（24–72 h）
T0／T1 不成立，且以下任一：
- 新發缺血等價症狀、已緩解、`last_episode_timing == over_24h`、`recurrence == false`、`rest_symptom == false`（C2 C）。非缺血型豁免除外（Q-14d C）
- 新發勞累性缺血等價症狀、`onset_weeks_ago >= 2`、型態穩定、`rest_symptom == false`、`threshold_decreased == false`（B2）(DV-2)
- 新發 `dyspnea_grade == exertional_daily`、`dyspnea_acute == false`、無缺血等價症狀（B6）
- `postural_dizziness == true` 且 `new_medication_recent == true`、無缺血等價症狀、無 presyncope 合併胸部症狀（B10）
- `edema == true` 且 `dyspnea_grade == exertional_daily`、無缺血等價症狀（B12）

### 5.6 T3（Routine）
T0／T1／T2 不成立，且以下任一：
- **穩定型**（A7、A8、A10）：全部成立 — `cad_history == true` 或已知穩定型態；`pattern_unchanged_duration_months >= 6`；`rest_symptom == false`；無 `dyspnea_acute`、`presyncope`、`syncope`；`threshold_decreased == false`
- **行政性來電**（A9）：`consult_topic == appointment_admin`（門診時間、排程等事務）且病人明確否認新發胸悶、喘、暈 (DV-7)
- `antiplatelet_interrupted == true` 且無症狀 → T3 + `expedite`（C7 C；B4）
- `palpitations == true`、無缺血等價症狀、無 presyncope／syncope（B5）。**系統不建議居家 ECG**（C8 B）
- `symptom_vs_pre_pci == milder`、`exertion_relation == exertion_only`、`rest_symptom == false`、`threshold_decreased == false`（PCI 後輕症較術前輕；B8）(DV-4)
- **Carve-out**：`symptom_character == epigastric`（Q-14e）、`postprandial_relieved == true`、`ongoing_now == false`、`exertion_relation ∈ {rest_only, unclear}`、`diaphoresis == false`（吃飽脹氣、打嗝後完全緩解；B13）(DV-5)
- `symptom_character == pain`（Q-14e）、`reproducible_mechanical == true` 且活動不加重（按壓／深呼吸可重現；B14）。壓迫、悶、下顎肩膀沉重**不適用**
- `symptom_character == pain`（Q-14e）、`cough_related == true` 且 `exertion_relation != exertion_only`（咳嗽時才痛；B16）

### 5.7 T4（Self-care）
T0–T3 不成立，且：
- `consult_topic ∈ {medication_handling, minor_noncardiac, education_question}` 且病人明確否認任何胸悶、喘、暈（B15、B17、B18；B20 回診前空腹等衛教問題）(DV-7)
- 必附 S-SN-A

### 5.8 Tier 9（資訊不足）
以下任一：
- 無法判定 `onset_new` 與 `pattern_unchanged`（既不知新發也不知穩定）
- `symptom_character` 未定性（「怪怪的」「不太舒服」「說不上來」）
- `third_party_call == true` 且 `patient_reachable == false`
- 呼吸困難但 `dyspnea_grade` 與 `dyspnea_acute` 皆未知
- 問題數達 `MAX_QUESTIONS` 仍未滿足 §5.3–§5.7 任一

**Tier 9 且護理師不可得時的預設等級**（C6 D，依主訴）：
| 主訴 | 預設 |
|---|---|
| 胸部不適／缺血等價症狀（下顎、肩、上腹） | T1 |
| 呼吸困難（已排除靜止喘） | T1 |
| 心悸／頭暈，無胸悶 | T2 |
| 第三方來電、病人不可及 | T1，請家屬轉達 S-SN-A |
| 藥物／行政諮詢且否認症狀 | T3 |

### 5.9 必要 slot 集合（Sufficiency Gate 用）
- 判 T0：至少一個 §5.3 條件的 slot 有高信心值 **且** 紅旗題（priority=redflag）已問完或已被回答。
- 判 T1／T2：對應條件的全部 slot 有高信心值，且 `rest_symptom`、`ongoing_now`、`diaphoresis` 已確認。
- 判 T3：對應條件的全部 slot 有高信心值；穩定型另需 `rest_symptom`、`threshold_decreased`、`dyspnea_acute` 皆為 false。
- 判 T4：`consult_topic` 已確認且三項否認（胸悶、喘、暈）皆有高信心值。
- **所有 T1–T4（Q-14b）**：有胸部症狀者，`rest_symptom`、`threshold_decreased`、`ntg_use_increased` 必須已知（三個 T0 觸發因子都排除才能定案）。
- **第三方來電（Q-14c）**：`patient_reachable` 必須已知。
- **勞累型豁免（DV-2、DV-4；Q-14d C）**：`last_episode_timing` 必須已知（答「不記得」算已知），否則不問就永遠豁免。
- **無症狀諮詢（T3 行政、T3 抗血小板中斷無症狀、T4；Q-14f）**：心悸、姿勢性頭暈、檢查異常待追蹤必須已知；以一題合併篩檢詢問，答「沒有」即三項皆 false。
- 其他 → 不足。

---

## 6. 流程對照（六條）

| Tier | 流程 | 客服腳本 | 後續動作 | Safety net |
|---|---|---|---|---|
| Hard stop | 立即 EMS | S-HS | 唸稿、保持通話至確認已撥 119、通報主管／護理師 | — |
| 0 | 急診 | S-T0 | 指示立即前往急診或撥 119；通報護理師 | S-SN-A |
| 1 | 當日 | S-T1 | 轉護理師當日回撥／安排當日評估（門診或急診由護理師定） | S-SN-A |
| 2 | 24–72 h | S-T2 | 安排 24–72 h 快速門診 | S-SN-A |
| 3 | 一般門診 | S-T3 | 依例行排程；可附 `expedite`（提前門診，C7 C） | S-SN-B |
| 4 | 自我照護 | S-T4 | 衛教腳本；必附 S-SN-A | S-SN-A |
| 9 | 轉護理師 | S-T9 | 同步轉接；不可同步時 ≤30 分鐘回撥。護理師不可得 → 依 §5.8 主訴對照表預設等級並走該流程 | S-SN-A |

Safety net 腳本：
- **S-SN-A**（強）：「如果接下來出現胸口壓迫感持續不退、坐著也會喘、快昏倒或昏倒、冒冷汗，請立刻撥打 119，不要再打客服。」
- **S-SN-B**（例行）：同上，但語氣為例行提醒。

腳本逐字內容由 Clinical Owner 與客服主管定稿，放 `data/scripts_zh.yaml`（M1）。

---

## 7. Benchmark v0.2 情境 → ground truth（D-12）

| 子模組 | 情境 | truth | HS | 升級／降級 boundary |
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
| 不足 | 家屬描述不完整 | 9 | N | 病人仍有持續不適或曾瀕厥／冒汗 → HS |
| 不足 | 長期胸悶但近期狀態未知 | 9 | N | 閾值下降或休息時 → T0；近期完全相同 → T3 |

完整欄位見 `data/benchmark/v0.2/ACS_Claude_LowerTier_Review_Result_v0.2.csv`。Clinical Owner 已於 2026-10-10 全部裁定為 ground truth（D-12），以 `data/scenarios_v0.2.yaml` 的 `truth_tier`／`truth_hard_stop` 為準。

---

## 8. 中間帶情境 → ground truth（D-13，問卷 Part B）

| # | 開場白（縮） | truth | 依據 |
|---|---|---|---|
| B1 | 昨晚胸悶十分鐘自己好，今天沒再發 | 1 | §5.4 |
| B2 | 三週前開始快走上坡會悶，穩定，休息時從沒 | 2 | §5.5 |
| B3 | 舌下片一月一次→一週兩三次，仍勞累性 | **0** | C4 A（X1） |
| B4 | 拔牙停保栓通三天，無症狀 | 3 + expedite | C7 C |
| B5 | 新發心悸，無胸悶無暈 | 3 | C8 B：不建議居家 ECG |
| B6 | 一週來走路做家事較喘，坐著不會 | 2 | §5.5 |
| B7 | 一個月內快走距離縮短才悶 | **1** | C3 B（X2） |
| B8 | 上月 PCI，走路一點悶，比術前輕很多 | 3 | §5.6 |
| B9 | 運動心電圖異常叫回診未掛號，無症狀 | 1 | §5.4 |
| B10 | 新降壓藥後站起來頭暈幾秒，無胸悶 | 2 | §5.5 |
| B11 | 兩週來躺下較喘要墊高枕頭 | **0** | C1 B（X3） |
| B12 | 腳腫＋走路較喘，坐著不喘 | 2 | §5.5 |
| B13 | 吃太飽胸口脹，打嗝後好了 | 3 | §5.6 carve-out |
| B14 | 搬重物後胸口按壓痛、深呼吸痛 | 3 | §5.6 |
| B15 | 舌下片過期可不可用，無發作 | 4 | §5.7 |
| B16 | 咳嗽時胸口痛，不咳不痛 | 3 | §5.6 |
| B17 | 爸忘記吃藥補吃可以嗎，無不適 | 4 | §5.7 |
| B18 | 打流感疫苗手臂痠 | 4 | §5.7 |
| B19 | 前天開始走路胸悶，昨天含一次舌下片有效，今天未發作，休息時沒有 | 1 | §5.4 (DV-1, DV-6) |
| B20 | 問下次回診要不要空腹抽血，無不適 | 4 | §5.7 (DV-7) |

完整結構見 `data/scenarios_midband_v0.1.yaml`（20 個；D-13、D-17）。分布：T0 2／T1 4／T2 4／T3 6／T4 4。

---

## 9. 推導門檻（DV）

### 9.1 已確認（DV-1～5：2026-10-12；DV-6～7：2026-10-13）

| # | 推導內容 | 來源 |
|---|---|---|
| DV-1 | 新發缺血等價症狀已緩解：**今天**發生 → T0；最後一次在**昨天（<24h）**且今日無發作 → T1（單次或多次皆同）；**≥24h** 且無再發、無休息症狀 → T2 | A1=0、B1=1、B19=1、C2=T2 |
| DV-2 | 新發勞累性症狀、型態穩定、無休息症狀：**≥2 週** → T2；<2 週 → 不適用此條（落回其他規則或 Tier 9） | B2「三個禮拜」=2 |
| DV-3 | 有症狀 + 抗血小板中斷 → 至少 T1 | ND-05 文字 + C7 C 反推 |
| DV-4 | PCI 後新輕症、較術前輕、純勞累、無休息、無閾值下降 → T3；任一不成立 → 不適用 | B8=3 |
| DV-5 | B13 carve-out 的條件（上腹不適〔Q-14e 增列〕、吃飽後、打嗝完全緩解、非活動相關、無冒汗）缺一即不適用，回到一般規則 | B13=3 |

| DV-6 | `ntg_use_increased` 指既有型態下用量增加；新發病人首次使用 NTG（即使有效）不觸發 C4 A 的 T0，仍依 DV-1 時序判定 | B19=1 與 C4 A 並存 |
| DV-7 | 無症狀諮詢的分流：門診時間／排程事務 → T3（走例行門診流程）；衛教性問題（回診前空腹、飲食、運動）、藥物處理、輕微非心臟問題 → T4 | A9=3 vs B20=4 |

### 9.2 待確認

（無）
