> **更正（2026-11-04）**：下方前言兩句是報告程式寫死的 10-27 文字，本表不適用。(1) 本表不是「v2 不自行歸類、留未知」的說法，而是 11-03 付費結果中 **v2 已經抽錯或需要再問** 的說法（第 1–10 項）；(2) 最後兩列不是「Prompter 設計缺口與順口值寫入規則的設計取捨」，而是第 11 列已知限制 6 項（含 L1；細節見報告 §1）與第 12 列 12 題上限／H3 取捨。10-27 的 16 項已在 2026-11-02 裁定（D-54）。本檔＝`sim.extractor_v2_report` 的輸出，再在開頭加上本段（`reports/extractor_v2_2026-11-03_inputs/ambiguous_md_fix.md`）。

# 抽取器 v2 模糊說法裁定表 — 2026-11-03

> 只用開發集（119 例開發情境的 Opus 逐字稿與開發集閉環）；保留集未執行、未收集。v2 對這些說法不自行歸類（留未知、系統追問）。
> 「提示裡是否已寫入例句」為「是」者，裁定結果若不同，提示要先改再凍結（保留集只能跑一次）。最後兩列是 Prompter 的設計缺口與順口值寫入規則的設計取捨。

| 編號 | 說法原文（欄位） | 開發集出處 case 與原句 | 目前處理方式 | 可能的歸類選項 | 提示裡是否已寫入例句 | Clinical Owner 裁定 |
|---|---|---|---|---|---|---|
| 1 | 我其實不太會喘（dyspnea_grade） | S-INSUF-01#1（閉環 Q-DYSPNEA-GRADE-01）：「我其實不太會喘耶，走路、做家事都還好，休息的時候也不會。」<br>S-INSUF-05#1（閉環 Q-DYSPNEA-GRADE-01）：「我其實不太會喘耶，就是走路的時候有時候胸口會悶悶的而已。」 | 依裁定 #12 抽成 exertional_heavy（gpt 11/20、Gemma 17/25）。複誦回覆「不是喔，我是不會喘」：gpt 9/11 讀成 none，D-50 取較嚴重仍留 heavy；Gemma 17/18 讀成不明，保留原值 | 維持（偏急）／複誦明確否認可降回 none，並改複誦解讀／#12 改回 none | 是：開場白規則 7 例句「我其實不太會喘」→ exertional_heavy（裁定 #12） |  |
| 2 | 坐著休息的時候就不會悶／休息完就好了（rest_symptom） | S-INSUF-05（閉環 Q-ONGOING-01）：「現在沒有了，坐著休息的時候就不會悶。」<br>S-ACUTE-01#2（閉環 Q-ONGOING-01）：「現在沒有了，休息完就好了，現在胸口不會不舒服。」<br>S-MID-08（閉環 Q-ONGOING-01）：「現在沒有，坐著休息的時候都還好，沒有在悶。」 | Gemma 抽成 rest_symptom＝true（把休息緩解當成休息時發作）；gpt 未見 | 加反例／維持 | 部分：有正例「剛剛就是吃飽坐著的時候 → rest_symptom」（裁定），沒有反例 |  |
| 3 | 以前只有運動才胸悶，今晚躺著看電視時也發作了（episode_frequency_increased） | S-ACUTE-05#1（開場白）：「以前只有運動才胸悶，今晚躺著看電視時也發作了。」 | Gemma 抽成 episode_frequency_increased＝true；gpt 未見 | 加反例／維持 | 否：只有「發作變頻繁」正例 |  |
| 4 | 昨天打完流感疫苗手臂痠（consult_topic） | S-MID-18（開場白）：「我有冠心症，昨天打完流感疫苗手臂痠，其他都沒有不舒服。」 | gpt 抽成 symptom（dev21 留 null） | minor_noncardiac 例句／維持 | 否 |  |
| 5 | 走路比平常喘一點（dyspnea_grade） | S-MID-12（開場白）：「我有冠心症，這幾天腳有點腫，走路比平常喘一點，坐著不喘，胸口不會悶。」 | Gemma 抽成 exertional_heavy（dev21 抽對）；gpt 抽對 | 加例句／維持 | 否 |  |
| 6 | 今天忘記吃早上的藥（antiplatelet_interrupted） | S-MID-17（開場白）：「我爸有冠心症，今天忘記吃早上的藥，現在補吃可以嗎？他沒有不舒服。」 | Gemma 抽成 true（10-27 相同） | 留 null 追問／維持 | 否 |  |
| 7 | 想問下次回診要不要空腹抽血（consult_topic） | S-MID-20（開場白）：「我有冠心症，想問下次回診要不要空腹抽血，最近沒有任何不舒服。」 | Gemma 抽成 appointment_admin（10-27 相同） | education_question 例句／appointment_admin | 否 |  |
| 8 | 前天開始…昨天含了一次舌下片…今天還沒發作（last_episode_timing） | S-MID-19（開場白）：「我有冠心症，前天開始走路會胸悶，昨天含了一次舌下片有效，今天還沒發作，休息時沒有。」 | Gemma 抽成 today（10-27 重放也抽錯） | 加反例／維持 | 否 |  |
| 9 | 最近走路會有一點悶（exertion_relation） | S-MID-08（開場白）：「上個月放支架，傷口沒問題，最近走路會有一點悶，比放支架前輕很多，但以前是完全沒有。」 | gpt 不填（null）、Gemma 抽成 unclear | 加例句／T0-NEW-TODAY 遇 DV-4 候選先問 Q-EXERTION-01／維持 | 否 |  |
| 10 | 比放支架前輕很多，但以前是完全沒有（threshold_decreased） | S-MID-08#2（開場白）：「上個月放支架，傷口沒問題，最近走路會有一點悶，比放支架前輕很多，但以前是完全沒有。」 | Gemma 抽成 threshold_decreased＝true（4 例都是；事實 false）；gpt 不填 | 加反例／維持 | 否 |  |
| 11（設計缺口） | 已知限制 6 項（含 L1）（流程） | #14 與 D-35 的張力；關鍵字開場白「沒有不舒服」→ none；third_party_call 缺「我姊姊」「我奶奶」；chest_discomfort_mentioned 誤觸（如胸部X光）；reask_downgrades 不重跑路徑；L1 回覆已會 Hard stop 仍先複誦 | 逐項的現象、方向、出處見報告 §1「已知限制（本輪驗收發現，待 Clinical Owner 確認是否處理）」與 D-54（同一份） | 逐項決定是否處理 | 不適用（流程與關鍵字） |  |
| 12（設計取捨） | 12 題上限與 H3（流程） | Scripted 隨機格 60,000 組中，全資訊 T0 卻掉級的有 1,511 組，全部停在 12 題上限（沒問到 REST 730、NTG 438、THRESHOLD 343）；本次付費閉環 T3 → T9 的 3 例（gpt 2 例、Gemma 3 例）也是第 1 項加上上限造成的 | 順序 D、活動題提前（Clinical Owner 2026-11-03 裁定）之後的結果 | 提高上限／再調排序／維持 | 不適用（流程） |  |
