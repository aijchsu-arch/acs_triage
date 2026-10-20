# ACS Triage Copilot — 設計藍圖（交接版）

**版本**：v0.3 · 2026-10-12（規則 0.3.1、中間帶 20 情境、provisional／final tier）
**臨床負責人（Clinical Owner）**：Joseph（心臟內科）
**本文件讀者**：Claude Code（實作）、後續加入的工程師與護理／客服流程負責人
**狀態**：Phase 0 — M0／M1／M2 完成（2026-10-13，commit 見 git log）；M3 待 Q-02；M4 待 Q-01。本文件是唯一的設計真相來源，程式碼與本文件衝突時以本文件為準，並回頭修文件。

相關文件：
- `docs/CLINICAL_RULES.md` — 分流等級、紅旗、追問規則（**只有 Clinical Owner 能改**）
- `docs/DECISIONS.md` — 已決／待決事項
- `CLAUDE.md` — Claude Code 工作守則
- `data/` — benchmark、情境、問題庫種子

---

## 0. 一句話定義

病人打進醫療客服時，一個**不出聲的 AI 旁聽者**即時轉譯雙方對話，逐句偵測紅旗、提示客服下一題該問什麼，等資訊足夠後給出分流等級（0–4，或 9＝資訊不足），並對應到固定的後續流程；居家 12 導程心電圖可作為**只升不降**的輔助訊號。

### 非目標（Non-goals）
- 不診斷 ACS／MI，只分流 urgency。
- 不取代 119，不自動派遣，不自動預約。
- Phase 0–2 的任何輸出都**不能單獨決定病人處置**，最終動作由人執行。
- 不做語音合成／AI 直接對病人說話。AI 只對客服說話（螢幕文字）。

---

## 1. 背景：為什麼會有這個系統

- v0.2 盲性審查（`data/benchmark/v0.2/`）測的是：AI 能否分辨 clearly acute / clearly chronic stable，以及資訊不足時是否願意填 Tier 9 而非硬猜。
- 審查結果：80 列（實際 18 個唯一情境）→ T0 24、T3 24、Tier 9 32、Hard stop Y 4；T1／T2／T4 完全沒出現，因為資料集沒有中間帶情境。
- 審查表的「仍缺少的關鍵資訊／必問問題」欄位，就是本系統**問題提示器的規格**；「哪一個單一事實改變最可能讓分流升級或降級」欄位，就是**模擬測試的 boundary test case**。
- 換句話說：Tier 9 不是研究的失敗輸出，而是產品的核心觸發點——系統的價值在於把 Tier 9 即時轉成「下一題問什麼」。

---

## 2. 系統總覽

```
 病人 ──電話──► 客服（一般客服，非護理師）
                    │ 雙向音訊（含同意聲明後開始）
                    ▼
            ┌──────────────┐
            │ 1 Audio/STT   │ 逐段轉譯，附 confidence、speaker
            └──────┬───────┘
                   ▼
            ┌──────────────┐   低信心片段 → 提示客服「請病人再說一次」
            │ 2 Confidence  │   （不餵下游）
            │   Gate        │
            └──────┬───────┘
                   ▼ 高信心 utterance
   ┌───────────────┴────────────────┐
   ▼                                ▼
┌──────────────┐            ┌──────────────┐
│ 3 Red-flag    │ 每句都跑   │ 4 Slot State  │ 把回答填進結構化欄位
│   Detector    │ 規則 OR 模型│   Extractor   │
└──────┬───────┘            └──────┬───────┘
       │ 命中 ──► HARD STOP ◄──────┤（任何時刻命中都立即停）
       │          （腳本 S-HS + 主管通報 + 停止問診）
       ▼                           ▼
                            ┌──────────────┐
                            │ 5 Prompter    │ 從問題庫選「下一題」給客服逐字唸
                            └──────┬───────┘
                                   ▼
                            ┌──────────────┐
                            │ 6 Sufficiency │ 資訊足夠？否 → 回到 5；達上限 → Tier 9
                            │   Gate        │
                            └──────┬───────┘
                                   ▼
                            ┌──────────────┐    ┌──────────────┐
                            │ 7 Tier        │◄───│ 8 ECG Adjunct │ 只升不降
                            │   Classifier  │    │  (12-lead+AI) │
                            └──────┬───────┘    └──────────────┘
                                   ▼
                            ┌──────────────┐
                            │ 9 Pathway     │ tier → 6 條固定流程 + 腳本
                            │   Router      │
                            └──────┬───────┘
                                   ▼
                            客服畫面（提示、腳本、分流結果）
                                   │
                            ┌──────┴───────┐
                            │ 10 Audit Log  │ 每一個建議、每一個客服動作、每一個模型輸出
                            └──────────────┘
```

**兩條鐵律**（寫在程式碼裡，不交給模型判斷）：
1. 紅旗 = stop sign。命中即 Hard stop，不等「資訊足夠」，不等問題清單問完。
2. ECG 只能讓等級變得更急，永遠不能讓等級變得更不急。

---

## 3. 模組規格

### 3.1 Audio Ingest & STT
- 介面：`STTAdapter.stream(audio) -> Iterator[TranscriptSegment]`
- 每段輸出：`text`, `speaker ∈ {patient, agent, unknown}`, `confidence ∈ [0,1]`, `lang_hint ∈ {zh-TW, nan-TW, mixed}`, `t_start`, `t_end`
- 語言現實：病人多為高齡 CAD 族群，台語、國台語夾雜常見。「有／沒有」「會／不會」轉錯一個字就整題反向。
- Phase 0 不需要真 STT：模擬器直接產生文字 utterance。真 STT 到 M4 才接。
- 供應商未定（見 `DECISIONS.md` Q-01）。Adapter 介面先定，實作可換。

### 3.2 Confidence Gate
- 規則：`confidence < STT_MIN_CONFIDENCE`（預設 0.75，可設定）→ 該段標記 `uncertain`，**不餵** red-flag／slot extractor，並向客服推一條提示：「請跟病人確認：『您剛才是說＿＿嗎？』」
- **關鍵題門檻（D-43）**：紅旗題（`priority: redflag`）與 `stt_critical_questions`（Q-CHARACTER-01；Q-REST-02 自 D-46）的回答，門檻提高為 `stt_min_confidence_critical`（0.9）。理由：翻轉測試（D-42）顯示紅旗題「有」被聽成「沒有」必降級，症狀性質聽錯是唯一會讓 HS／T0 掉到 T1–T4 的單點；D-45 的反覆休息時症狀規則使「是否首次」成為 T0→T3 的單一開關。代價：這些題偶爾多問一次。
- 例外：若低信心片段含紅旗關鍵詞（規則路徑命中），**仍然觸發紅旗確認**：提示客服「請立即確認病人是否現在仍有胸痛／是否快昏倒」。寧可多問一次，不漏。

### 3.3 Red-flag Detector（雙路徑）
- **規則路徑（永遠在）**：`clinical_rules.yaml` 的紅旗清單，用關鍵詞／片語＋否定詞處理做確定性比對。
- **模型路徑（可插拔）**：對每句問一個 typed yes/no：「這句話是否揭露了紅旗 RF-xx？」→ 機率。
- 合併邏輯：`hard_stop = rules_hit OR (model_p >= RF_MODEL_THRESHOLD)`。兩路徑任一命中即停。
- 命中後：
  1. 推送腳本 `S-HS`（「請您現在立刻撥打 119…」）到客服畫面，全螢幕、不可忽略。
  2. 通報主管／護理師（channel 待定）。
  3. 凍結問題提示器；只保留「保持通話直到確認已撥 119」提示。
  4. 寫 audit：觸發句、命中的 RF-id、路徑（rules/model/both）。
- 紅旗清單見 `CLINICAL_RULES.md §3`。清單內容只有 Clinical Owner 能改。

### 3.4 Slot State Extractor
- 把病人每句回答對應到結構化欄位（slot），例如 `onset_new`, `threshold_decreased`, `rest_symptom`, `ongoing_now`, `dyspnea_grade`, `presyncope`…（完整清單在 `data/question_bank_seed.yaml`）。
- 每個 slot 值：`{value, confidence, source_utterance_id, asked_by_question_id|None}`。
- 病人自發說出的資訊也要填 slot（不是只有被問到的才算）。
- 模型路徑：typed question「utterance 是否回答了 slot X？值為？」；規則路徑：關鍵詞做保底。

### 3.5 Prompter（問題提示器）
- 問題庫是**固定腳本**（`data/question_bank_seed.yaml`），客服逐字唸。理由：一般客服不是護理師，不做臨床判斷；逐字腳本可稽核、可訓練、可改版。
- 選題邏輯（Phase 0 用規則，之後可換模型）：
  1. 先問能觸發 Hard stop 的題（`priority: redflag`，含冒汗題 Q-DIAPH-01 → RF-06）。
  2. 再問「決定 acute vs chronic」的題（`priority: decisive`）。
  3. 最後才是修飾題（`priority: refine`）。
  4. 已有高信心 slot 值的題跳過。
- 每次只推**一題**到畫面，附「為什麼問這題」一行（給客服，不給病人）。
- 上限：`MAX_QUESTIONS`（預設 11，見 D-22、D-29）。到上限仍不足 → Tier 9。

### 3.6 Sufficiency Gate
- 判斷「現有 slot 是否足以安全指定 0–4」。
- Phase 0 規則：`CLINICAL_RULES.md §5.9` 定義每個 tier 的**必要 slot 集合**；任一 tier 的必要集合被滿足且無矛盾 → sufficient。
- 模型路徑：獨立 typed question「資訊是否足以決定 timing？」→ 機率。**不要**只用 tier 分類的低信心來推導 Tier 9；Tier 9 是獨立判斷。
- 不足 → 回 Prompter；達上限 → Tier 9。

### 3.7 Tier Classifier
- 輸入：slot state（結構化）＋ 原始對話（文字）。
- 輸出：`TierDecision`，含**兩個等級**：
  - `provisional_tier`：以目前已知 slot 套 `CLINICAL_RULES.md §5.2–§5.8` 的最佳估計，**不經** Sufficiency Gate。紅旗、T0 條件、§5.8 的 Tier 9 實質規則（症狀未定性、第三方不可及等）都在這裡生效。
  - `tier`（final）：`provisional_tier` 通過 §5.9 Sufficiency Gate 才等於它；未通過 → 9，並由 Prompter 繼續問。
  - 兩者的差就是「還缺什麼才能定案」，記進 `missing`。
- 用途分工：**開場白 benchmark 測試**比對 `provisional_tier`（Clinical Owner 的標籤本來就是只看開場白給的）；**端到端模擬**（M2）比對對話結束後的 `tier`。
- Phase 0：規則引擎（`CLINICAL_RULES.md §5`）。
- M3：模型路徑（LLM structured output 或 Jev）。模型輸出與規則引擎並列記錄，差異進比較報告。
- **約束**：`CLINICAL_RULES.md §4` 的「不得降級」規則在程式碼層強制：模型若輸出比規則引擎更不急的等級，取規則引擎結果並標記 `model_downgrade_blocked`。

### 3.8 ECG Adjunct（12 導程 + AI-ECG）
- 輸入：`ECGResult {device_id, quality_ok: bool, ai_findings: [...], ecg_tier_suggestion ∈ {0,1,None}}`。
- 只升不降：`final_tier = min(symptom_tier, ecg_tier)`（數字小＝更急；Tier 9 視為 ∞ 參與 min，但若 ECG 有發現，結果不可為 9）。
- `quality_ok == False` → 完全忽略，並提示客服「訊號不佳，請勿依此判斷」。
- **何時可以建議病人量**（全部條件同時成立才可以）：
  - `hard_stop == False`
  - 目前估計 ∈ {9, 1, 2}
  - 症狀屬於：模糊的休息時不適、單純頭暈（**心悸不在內**：C8 B，由護理師決定）
- **絕對不可建議量**：hard stop 案例、T0 案例、正在發作的胸痛。量測會延誤 EMS。
- 「量起來正常」永遠不產生任何降級、也不產生安撫語句。
- 裝置 API 未定（`DECISIONS.md` Q-03）；Phase 0 用 mock。

### 3.9 Pathway Router
- tier → 流程對照表（固定六條，見 `CLINICAL_RULES.md §6`）。
- 每條流程 = 客服腳本 id + 後續動作清單 + safety net 腳本。
- Tier 9 **必須**對應動作（轉護理師），不能停在客服端；護理師不可得時依 `CLINICAL_RULES.md §5.8` 主訴對照表取預設等級（D-15）。

### 3.10 Agent UI（客服畫面）
- M4 才做。Phase 0–M3 用 CLI／log 即可。
- 最低需求：即時逐字稿、目前一題（大字）、紅旗全螢幕警示、分流結果與腳本、「我已執行」按鈕（寫 audit）。
- 絕不顯示：ACS 機率、診斷字眼。

### 3.11 Audit Log
- 每一筆：`AuditEvent {ts, call_id, kind, payload, model_version, rules_version}`。
- kind：`stt_segment`, `gate_uncertain`, `redflag_hit`, `question_shown`, `slot_update`, `sufficiency`, `tier_decision`, `ecg_result`, `pathway_shown`, `agent_action`。
- 不可刪改（append-only）。研究用的 shadow 比對、法規稽核都靠它。

---

## 4. 資料模型（Pydantic v2）

```python
class TranscriptSegment(BaseModel):
    id: str
    call_id: str
    speaker: Literal["patient", "agent", "unknown"]
    text: str
    confidence: float          # 0..1
    lang_hint: Literal["zh-TW", "nan-TW", "mixed", "unknown"]
    t_start: float
    t_end: float

class RedFlagHit(BaseModel):
    rf_id: str                 # "RF-01"
    segment_id: str
    path: Literal["rules", "model", "both"]
    model_p: float | None

class SlotValue(BaseModel):
    slot_id: str
    value: str | bool | int | None
    confidence: float
    source_segment_id: str
    asked_by_question_id: str | None

class Question(BaseModel):
    id: str                    # "Q-ONSET-01"
    slot_id: str
    priority: Literal["redflag", "decisive", "refine"]
    script_zh: str             # 客服逐字唸
    why_zh: str                # 給客服看的一行理由
    answer_type: Literal["yes_no", "choice", "duration", "free"]
    choices: list[str] | None

class TierDecision(BaseModel):
    provisional_tier: Literal[0, 1, 2, 3, 4, 9]   # 不經 sufficiency gate
    tier: Literal[0, 1, 2, 3, 4, 9]               # final；gate 未過 → 9
    gate_passed: bool
    hard_stop: bool
    rf_hits: list[str]                            # ["RF-03"]
    confidence: float
    evidence: list[str]        # slot_ids
    missing: list[str]         # slot_ids
    source: Literal["rules", "model", "merged"]
    model_downgrade_blocked: bool = False

class ECGResult(BaseModel):
    device_id: str
    quality_ok: bool
    ai_findings: list[str]
    ecg_tier_suggestion: Literal[0, 1] | None

class Pathway(BaseModel):
    tier: Literal[0, 1, 2, 3, 4, 9]
    script_id: str
    actions: list[str]
    safety_net_script_id: str

class AuditEvent(BaseModel):
    ts: datetime
    call_id: str
    kind: str
    payload: dict
    rules_version: str
    model_version: str | None
```

---

## 5. 決策模型抽象層

所有「問模型一個 typed 問題」的地方都走同一個介面，實作可換：

```python
class TypedQuestion(BaseModel):
    kind: Literal["yes_no", "choice", "ordinal"]
    prompt: str
    choices: list[str] | None
    context: str              # 對話片段或 slot 摘要

class Decision(BaseModel):
    answer: str | bool | int
    confidence: float         # calibrated 0..1

class DecisionModel(Protocol):
    def decide(self, q: TypedQuestion) -> Decision: ...
    def decide_many(self, qs: list[TypedQuestion]) -> list[Decision]: ...
```

實作順序：
1. `RulesEngine` — 確定性，Phase 0 唯一實作，之後永遠作為紅旗保底。
2. `LLMStructuredAdapter` — 任一 LLM 的 structured output（JSON schema 強制 enum）。
3. `JevAdapter` — TypeSafe AI 的 Jev（System One model，typed probabilistic decisions，不產生文字，延遲約 70–500 ms）。適合：逐句紅旗 yes/no、Tier enum、sufficiency yes/no、「下一題選哪個」。

Jev 的保留事項（寫進 `DECISIONS.md` Q-02）：
- 目前為早期存取；效能數字為供應商自述，未獨立驗證。
- 「零幻覺」指保證符合 schema，不代表答案正確；臨床驗證一樣要做。
- 美國 API；**真實病人逐字稿在確認資料出境／本地部署方案前，不得送出**。Phase 0 只用合成資料。
- Jev 不產生文字 → 問題庫必須是固定腳本（本設計本來就如此）。
- 以英文為主、中日韓文準確度不穩（第三方資料，見 Q-02）→ 輸入以結構化 slot 狀態（英文 key／enum）為主，不送中文逐字稿；若要測逐句紅旗，先在合成資料上量測，規則引擎保底不變。鎖定版本 `jev-1.13.0`，`model_version` 寫入 audit。

---

## 6. 評估與模擬（Phase 0 Harness）

目前**沒有真實錄音**，所以 Phase 0 全靠模擬。

### 6.1 情境資料
- 來源：`data/scenarios_v0.2.yaml`（18 個唯一情境，含 v0.2 審查的 reviewer 標籤與 boundary）。
- 每個情境展開成 **hidden case sheet**：
  ```yaml
  case_id: ACS-LT-001-v1
  opening_line: "今天第一次在快走時胸口像被壓住，休息後才比較好。"
  hidden_slots: {onset_new: true, ongoing_now: false, rest_symptom: false, presyncope: false, ...}
  truth_tier: 0
  truth_hard_stop: false
  decisive_questions: [...]   # 由 sim/decisive.py 反事實計算（D-27），非人工列舉
  ```
- 每條 boundary 句展開成 1–2 個變體（例：同一開場 + `ongoing_now: true` → `truth_hard_stop: true`）。18 → 預估 50–60 個 case。
- 中間帶情境：`data/scenarios_midband_v0.1.yaml`（20 個，D-13／D-17；分布 T0 2／T1 4／T2 4／T3 6／T4 4）。

### 6.2 模擬病人
- LLM 扮演病人，只能看 hidden case sheet，**只回答被問到的事**，不主動補充（除非 sheet 標 `volunteers: [...]`）。
- 噪音模式（可開關）：`vague`（含糊）、`taiwanese`（台語詞彙）、`contradict`（前後矛盾一次）、`low_stt`（隨機把 20% utterance 標低信心）。

### 6.3 指標（每次跑完產 `reports/eval_<date>.md`）
| 指標 | 定義 | 目標 |
|---|---|---|
| Hard-stop latency | 紅旗事實揭露的那句 → 觸發 hard stop，相隔幾句 | 0 句 |
| Hard-stop miss rate | truth_hard_stop=true 但沒觸發 | 0% |
| Under-triage rate | 預測 tier 數字 > truth（更不急） | 主要安全指標，趨近 0 |
| Over-triage rate | 預測 tier 數字 < truth | 記錄，不作硬目標 |
| Tier exact accuracy | 完全一致 | 記錄 |
| Escalating-question recall | 「答案可能使分流更急」的題目（反事實計算，D-27）在結束前被問到或已知的比例；漏問 = 可能 under-triage | ≥ 90% |
| Decisive-question recall | 「答案會改變分流」的全部題目（含只會降級者）之覆蓋率 | 記錄 |
| Abstention precision/recall | Tier 9 對應 truth「資訊不足」的 P/R | 記錄 |
| Questions-to-decision | 平均問幾題才分類 | 記錄 |
| Gate effect | 低信心片段被正確擋下、重問的比例 | 記錄 |

### 6.4 Benchmark 的統計注意事項
- `data/benchmark/v0.2/` 的 80 列只有 18 個唯一情境；分析以 18 個 cluster 為單位。
- 裡面的 tier 原為 Claude v0.2 reviewer 的盲性標籤；Clinical Owner 已於 2026-10-10 全部裁定為 ground truth（D-12），存於 `data/scenarios_v0.2.yaml` 的 `truth_tier`／`truth_hard_stop`。

---

## 7. 分期上線與法規邊界

| Phase | 內容 | AI 是否影響病人處置 | 風險等級 |
|---|---|---|---|
| 0 模擬 | 全合成資料，CLI harness，指標報告 | 否 | — |
| 1 Shadow | 接真實通話（有同意），系統全程靜默記錄建議，事後與客服實際處置比對 | 否 | 低 |
| 2 Prompter live | 客服看得到「下一題」與紅旗警示；分流等級仍不顯示 | 間接 | 低–中（仍是人問、人判） |
| 3 Classifier assist | 顯示分流等級與流程；護理師覆核 | 是 | **可能落入 SaMD（TFDA 智慧醫材）**，進入前先法規諮詢 |

- Phase 1 開始即需：通話開始的同意聲明、錄音與逐字稿加密、去識別化流程、保存期限（`DECISIONS.md` Q-06）。
- 「問題提示器」與「分流分類器」刻意切成可獨立部署的模組，就是為了讓 Phase 2 不必等 Phase 3 的法規流程。

---

## 8. 安全與隱私（工程層強制）
- 真實病人資料不出院內網路，直到 Q-02／Q-06 解決。
- 所有模型呼叫記錄 `model_version`；所有規則判斷記錄 `rules_version`。
- 任何對 `data/clinical_rules.yaml` 的變更：PR 需 Clinical Owner 核可、版本號 bump、對應測試更新。
- 紅旗規則路徑的測試覆蓋率要求 100%（每條 RF 至少 3 個正例、3 個否定詞反例）。

---

## 9. 技術選型（預設值，可改但要改 `DECISIONS.md`）
- Python 3.12、Pydantic v2、FastAPI（M4 起）、PyYAML、pytest、structlog
- 儲存：dev 用 SQLite（audit log）；prod 候選 PostgreSQL
- STT adapter：dev 預設 faster-whisper（本地）；台語供應商待定
- 模擬病人 LLM：任一支援 structured output 的模型，透過 `DecisionModel`／`PatientSimulator` 介面接
- 不引入前端框架直到 M4；M4 先用 FastAPI + 單頁 HTML

---

## 10. Repo 結構

```
acs_triage/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── BLUEPRINT.md          ← 本文件
│   ├── CLINICAL_RULES.md
│   └── DECISIONS.md
├── data/
│   ├── clinical_rules.yaml   ← M0 從 CLINICAL_RULES.md 轉出，程式讀這個
│   ├── question_bank_seed.yaml
│   ├── scenarios_v0.2.yaml
│   ├── scenarios_midband_v0.1.yaml
│   └── benchmark/v0.2/*.csv
├── src/acs_triage/
│   ├── schemas.py            ← §4
│   ├── rules/                ← RulesEngine：redflag、sufficiency、tier
│   ├── decision/             ← DecisionModel 介面 + adapters
│   ├── prompter/
│   ├── state/                ← slot state machine
│   ├── ecg/
│   ├── pathway/
│   ├── stt/                  ← adapter 介面（M4 實作）
│   └── audit/
├── sim/                      ← Phase 0 harness：patient simulator、runner、metrics
├── tests/
└── reports/
```

---

## 11. 里程碑與驗收

| M | 狀態 | 範圍 | 驗收條件 |
|---|---|---|---|
| M0 | ✅ 2026-10-13 | repo 骨架、`schemas.py`、`clinical_rules.yaml` + loader、`question_bank_seed.yaml` loader、pytest 跑通 | `pytest` 綠；YAML 與 `CLINICAL_RULES.md` 內容一致（有測試比對版本號與 RF 數量） |
| M1 | ✅ 2026-10-13 | `RulesEngine`：紅旗（RF-01～06）、slot 規則、sufficiency、tier 0–4／9；Prompter 規則選題；Pathway 對照（含 Tier 9 護理師不可得預設） | v0.2 的 18 個 + 中間帶 20 個情境只給開場白 → `provisional_tier`／`hard_stop` 與 `truth_*` 一致；所有 boundary_variants 以 `hidden_slots`+`override` 直接餵 slot → `provisional_tier`／`hard_stop`／`rf` 與 `expect` 一致；紅旗測試 100% 覆蓋 |
| M2 | ✅ 2026-10-13（ScriptedPatient；LLM 病人 → M2b） | 模擬器：hidden case sheets 展開、PatientSimulator、對話 runner、指標報告 | 38 個情境 + 全部 boundary_variants 展開為 hidden case sheets（預估 100+ cases）跑完產 `reports/eval_*.md`；對話結束後的 final `tier` 與 truth 比對；Hard-stop miss = 0；Under-triage 報表 |
| M2b | ✅ 2026-10-15（提示詞 v0.2；預設 `claude-opus-5-5` effort medium，三次全量皆 Hard-stop miss 0、under 0：`reports/eval_2026-10-15_llm_opus-5-5_medium*.md`；D-32～D-34） | `LLMPatientSimulator`（LLM 扮演病人，只看 hidden sheet）；與 ScriptedPatient 結果比對 | 需任一 LLM 端點：只用合成資料，D-10 不適用，本地 llama.cpp 或雲端 API 皆可（D-30）；Hard-stop miss 與 under-triage 仍為 0；指標與 clean 模式差異報告 |
| M3 | ✅ 2026-10-15（shadow）：M3a Jev 不適合做分級決策（D-37）；M3b `gpt-6.1-sol` 逐句紅旗敏感度 100%、slot 抽取 97.7%、分級一致 80/119（D-38、D-39）；`model_downgrade_blocked` 有測試；報告 `reports/m3a_jev_*`、`reports/m3b_*` | `LLMStructuredAdapter`、`JevAdapter`；模型 vs 規則比較報告；downgrade 阻擋測試 | 比較報告；`model_downgrade_blocked` 有測試 |
| M4 | ⏳ 待 Q-01 | STT adapter + Confidence Gate；shadow-mode logger；最小客服 UI | 以錄製的合成音檔端到端跑通；UI 顯示紅旗全螢幕 |
| 後續 | ⏳ | ECG adapter、電話系統整合、Phase 1 準備 | 依 `DECISIONS.md` 解決 Q-01/02/03/06 後排程 |

每個 M 完成時更新本文件的狀態列與 `DECISIONS.md`。

**M2 基線（2026-10-13，`reports/eval_2026-10-13_*.md`）**：119 cases／116 可評分。clean：Hard-stop miss 0/27、latency 0、under-triage 0、over-triage 0、exact 100%、abstention P/R 100%/100%、平均 4.9 題。vague（25% 答不知道）：under-triage 0、Hard-stop miss 0、24 例轉護理師（預期）。low_stt（20% 低信心）：130 次重問，結果與 clean 完全相同。

**M2 重訂基線（2026-10-13，D-27）**：decisive 改為反事實定義後，clean 的 escalating recall **86.5%（455/526）**、decisive recall 81.5%；未達 90% 目標。71 次漏問集中在 Q-NTG-01（33）、Q-THRESHOLD-01（9）、無症狀諮詢的篩檢題（PENDINGTEST 7、POSTURAL 6、PALP 4），成因與修正選項見 `DECISIONS.md` Q-14。

**Q-14 修正後基線（2026-10-13，D-28，rules 0.4.0）**：clean escalating recall **95.9%（510/532）**、Hard-stop miss 0/27、latency 0、under 0、over 0、exact 115/116、平均 5.3 題。剩餘 22 次漏問中 15 次結束於 Tier 9 或 T0（無 under-triage 風險）；4 次（S-MID-02／08／16 時序題）源自待裁定的 Q-14d。

**Q-14d C＋Q-15 後基線（2026-10-14，D-29，rules 0.5.0，`reports/eval_2026-10-14_*`）**：clean exact **116/116**、escalating recall **96.6%（512/530）**、Hard-stop miss 0/27、latency 0、under 0、over 0、平均 5.5 題。剩餘 18 次漏問中 16 次結束於 Tier 9 或 T0；其餘 2 次：S-MID-07（逐月閾值下降的 CAD 病人若被認定為「新發」→ 依 D-23 時序不明視為今天 → T0）、S-MID-08（PCI 後較輕的新症狀若已 ≥2 週 → DV-2 的 T2 先於 DV-4 的 T3）。
