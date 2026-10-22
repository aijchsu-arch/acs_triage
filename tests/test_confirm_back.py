"""D-50：紅旗題與關鍵題有條件複誦確認（confirm-back，rules 0.8.0，CLINICAL_RULES §5.10）。"""
import json

import pytest

from acs_triage.audit import AuditLog
from acs_triage.extract import extract
from acs_triage.decision.merge import urgency_rank
from acs_triage.loaders import load_clinical_rules, load_extraction_patterns, load_scripts, question_by_id, slot_defs
from acs_triage.prompter.confirm import (confirm_prompt, in_scope, leading_yes_no, needs_confirm, resolve_confirm, severity,
                                         should_confirm)
from acs_triage.rules import RulesEngine, SlotState
from sim.cases import all_cases
from sim.patient import PatientReply, ScriptedPatient
from sim.metrics import compute
from sim.run_eval import render_md, run_all
from sim.runner import run_case

QB = question_by_id()


# ---------------------------------------------------------------- 句首判定
@pytest.mark.parametrize("text,expect", [
    ("有，現在胸口還是悶悶的", True),
    ("有。", True),
    ("會欸，躺平比較喘", True),
    ("是最近才開始的", True),
    ("還在悶", True),
    ("對，休息的時候會悶是最近才開始的", True),
    ("有，不過沒有冒汗", True),                       # 只看句首：其後的否定詞不翻轉
    ("沒有。", False),
    ("沒有，那時候沒有冒冷汗。", False),
    ("沒冒汗", False),
    ("不會耶，我躺平睡都還好", False),
    ("不是，是壓著的感覺", False),
    ("還沒好", False),
    ("沒什麼特別的", False),
    # 句首標點與語助詞
    ("嗯，沒有耶", False),
    ("呃……有耶，最近有停過", True),
    ("喔，對啊", True),
    ("「有」", True),
    ("唉，沒有啦", False),
    # 不明確
    ("現在胸口還是悶悶的，還沒好。", None),           # D-49：句首「有」被吞掉
    ("現在沒有了，已經好了。", None),                 # 「現在」開頭：不是明確的句首否定詞
    ("不知道，我沒有注意。", None),                   # 非否定片語先遮罩
    ("不太確定耶", None),
    ("不舒服的時候會冒汗", None),
    ("說不上來", None),
    ("這個我不清楚欸", None),
    ("喲，現在胸口還是悶悶的", None),                 # 「喲」不在語助詞清單
    ("", None),
    ("，。…", None),
])
def test_leading_yes_no(text, expect):
    assert leading_yes_no(text) is expect


def test_simplified_input_is_unclear_not_flipped():
    """詞表是繁體：簡體漏網時含簡體字的詞比不到 → 不明確 → 會觸發確認（安全方向）。"""
    for simp in ["没有，那时候没有冒冷汗", "没", "还没好", "对，会悶", "会欸", "还在痛", "没什么"]:
        assert leading_yes_no(simp) is None, simp
    assert leading_yes_no("有") is True and leading_yes_no("是") is True        # 繁簡同形
    assert leading_yes_no("不会") is False                                     # 「不」繁簡同形，仍是否定
    # 已知限制（docstring 有寫）：以「不」開頭的簡體非否定片語遮罩不到 → 被當成否定詞；所以轉繁不能省
    assert leading_yes_no("不确定耶") is False and leading_yes_no("不確定耶") is None


def test_lexicon_single_source_shared_with_stt_eval():
    from sim import stt_eval as se
    lx = load_extraction_patterns()["leading_yes_no"]
    assert se.NEG_TOKENS == lx["negative"] and se.POS_STARTS == lx["affirmative"]
    assert se.NON_NEGATION == lx["non_negation_phrases"] and se.FILLER_CHARS == lx["filler_chars"]
    for t in ["有，還在痛", "沒有冒汗", "嗯，不會", "現在沒有", "不知道", "對啊", "還沒好"]:
        assert se.lead_polarity(t) == {True: "pos", False: "neg", None: None}[leading_yes_no(t)], t


# ---------------------------------------------------------------- 範圍與觸發條件
def test_scope_is_redflag_plus_critical_questions():
    th = load_clinical_rules()["thresholds"]
    assert th["stt_confirm_back"] is True                                   # D-50 開關
    scope = sorted(q.id for q in QB.values() if in_scope(q))
    assert scope == sorted([q.id for q in QB.values() if q.priority == "redflag"] + th["stt_critical_questions"])
    types = {q.id: q.answer_type for q in QB.values() if in_scope(q)}
    assert sum(t == "yes_no" for t in types.values()) == 6 and sum(t == "choice" for t in types.values()) == 2
    assert types["Q-REST-02"] == "yes_no" and types["Q-CHARACTER-01"] == types["Q-DYSPNEA-GRADE-01"] == "choice"
    assert not in_scope(QB["Q-NTG-01"])


def test_trigger_conditions():
    ongoing, char, dysp = QB["Q-ONGOING-01"], QB["Q-CHARACTER-01"], QB["Q-DYSPNEA-GRADE-01"]
    # yes_no、句首明確且與值一致 → 不複誦
    assert not needs_confirm(ongoing, True, "有，還在痛。")
    assert not needs_confirm(ongoing, False, "沒有，現在好了。")
    # yes_no 值為「有」→ 不論句首都不複誦（複誦只可能把較急的「有」改成較不急）
    assert not needs_confirm(ongoing, True, "現在胸口還是悶悶的，還沒好。")
    assert not needs_confirm(ongoing, True, "沒有啦，還在痛")
    # yes_no 值為「沒有」而句首不是明確否定詞 → 複誦
    assert needs_confirm(ongoing, False, "現在沒有了。")
    # 值不明 → 複誦（即使句首明確）
    assert needs_confirm(ongoing, None, "不知道，我沒有注意。")
    assert needs_confirm(ongoing, None, "有")
    # choice：值不明或不是最嚴重一級 → 複誦；最嚴重一級（典型症狀、坐著也喘）→ 不複誦
    for v in ("epigastric", "pain", "vague", "other", "none", None):
        assert needs_confirm(char, v, "…"), v
    for v in ("pressure", "tightness", "jaw_shoulder_heaviness"):
        assert not needs_confirm(char, v, "…"), v
    for v in ("exertional_daily", "exertional_heavy", "none", None):
        assert needs_confirm(dysp, v, "…"), v
    assert not needs_confirm(dysp, "rest", "…")
    # 實作補充：值為「沒有」但句首是肯定詞 → 複誦（安全方向）
    assert needs_confirm(ongoing, False, "有，還在痛。")


def test_confirm_prompt_uses_templates_and_question_text():
    sc = load_scripts()["scripts"]
    assert all(sc[k]["status"] == "DRAFT" for k in ("S-CONFIRM-BACK", "S-CONFIRM-BACK-ASK-YESNO", "S-CONFIRM-BACK-ASK"))
    diaph, char = QB["Q-DIAPH-01"], QB["Q-CHARACTER-01"]
    assert confirm_prompt(diaph, False) == f"我跟您確認一下，剛剛問您『{diaph.script_zh.strip()}』，您的回答是『沒有』，對嗎？"
    assert confirm_prompt(diaph, True).endswith("您的回答是『有』，對嗎？")
    assert confirm_prompt(diaph, None) == f"我再跟您確認一次，{diaph.script_zh.strip()}請您回答『有』還是『沒有』。"
    assert confirm_prompt(char, "pressure").endswith("您的回答是『被壓住』，對嗎？")
    assert confirm_prompt(char, "pain").endswith("您的回答是『刺痛』，對嗎？")             # 題目用語（不是「會痛」）
    assert confirm_prompt(QB["Q-DYSPNEA-GRADE-01"], "rest").endswith("您的回答是『現在坐著休息也會喘』，對嗎？")
    assert confirm_prompt(char, None) == f"我再跟您確認一次，{char.script_zh.strip()}"


def test_every_in_scope_choice_value_has_a_label():
    labels = load_scripts()["confirm_value_labels_zh"]
    assert labels["status"] == "DRAFT"
    for q in QB.values():
        if in_scope(q) and q.answer_type == "choice":
            for v in slot_defs()[q.slot_id]["choices"]:
                assert f"『{labels[q.slot_id][v]}』" in confirm_prompt(q, v), (q.id, v)
    # 題目 script_zh 列出的選項用題目原本的用語（E），其餘沿用模擬病人口語
    for qid, vals in {"Q-CHARACTER-01": ["pressure", "tightness", "pain", "vague"],
                      "Q-DYSPNEA-GRADE-01": ["exertional_heavy", "exertional_daily", "rest"]}.items():
        q = QB[qid]
        for v in vals:
            assert labels[q.slot_id][v] in q.script_zh, (qid, v, labels[q.slot_id][v])


def test_severity_table_from_rules():
    """Clinical Owner 2026-10-22 裁定的嚴重度順序（左最嚴重），放在 data/clinical_rules.yaml，程式只讀表。"""
    t = load_clinical_rules()["confirm_back_severity"]
    assert t["yes_no"] == [[True], [False]]
    assert t["dyspnea_grade"] == [["rest"], ["exertional_daily"], ["exertional_heavy"], ["none"]]
    assert t["symptom_character"] == [["pressure", "tightness", "jaw_shoulder_heaviness"], ["epigastric"], ["pain"], ["vague"],
                                      ["other"], ["none"]]
    # 範圍內選擇題的 slot：表恰好涵蓋全部選項（新增選項時必須先排進順序）
    for q in QB.values():
        if in_scope(q) and q.answer_type == "choice":
            assert sorted(v for lvl in t[q.slot_id] for v in lvl) == sorted(slot_defs()[q.slot_id]["choices"]), q.id
    char, dysp, yn = QB["Q-CHARACTER-01"], QB["Q-DYSPNEA-GRADE-01"], QB["Q-REST-02"]
    assert severity(char, "pressure") == severity(char, "tightness") == severity(char, "jaw_shoulder_heaviness") == 0
    assert severity(char, "epigastric") < severity(char, "pain") < severity(char, "vague") < severity(char, "other") < severity(char, "none")
    assert severity(dysp, "rest") < severity(dysp, "exertional_daily") < severity(dysp, "exertional_heavy") < severity(dysp, "none")
    assert severity(yn, True) < severity(yn, False)


def test_resolve_confirm_rules():
    yn, ch, dy = QB["Q-SYNCOPE-01"], QB["Q-CHARACTER-01"], QB["Q-DYSPNEA-GRADE-01"]
    # 確認回答不明（規則不變）
    assert resolve_confirm(yn, False, None) == (None, False)      # 未經確認的紅旗否認不採信
    assert resolve_confirm(yn, True, None) == (True, False)       # 其他情況保留原值
    assert resolve_confirm(yn, None, None) == (None, False)
    assert resolve_confirm(ch, "pain", None) == ("pain", False)
    # 原值不明 → 採用確認值
    assert resolve_confirm(yn, None, False) == (False, False)
    assert resolve_confirm(ch, None, "none") == ("none", False)
    # 兩者都有值：取較嚴重者；同級保留原值；確認值較不嚴重 → 保留原值並記 downgrade_blocked
    assert resolve_confirm(yn, False, True) == (True, False)
    assert resolve_confirm(yn, True, False) == (True, True)
    assert resolve_confirm(yn, False, False) == (False, False)
    assert resolve_confirm(ch, "pain", "pressure") == ("pressure", False)
    assert resolve_confirm(ch, "pressure", "tightness") == ("pressure", False)        # 同級 → 保留原值
    assert resolve_confirm(ch, "pressure", "vague") == ("pressure", True)
    assert resolve_confirm(ch, "epigastric", "pain") == ("epigastric", True)
    assert resolve_confirm(dy, "exertional_daily", "exertional_heavy") == ("exertional_daily", True)
    assert resolve_confirm(dy, "exertional_heavy", "exertional_daily") == ("exertional_daily", False)


def test_hard_stop_exception_in_should_confirm():
    """寫入解讀值後即 Hard stop → 不複誦（不得因確認延誤送醫）。例：胸口現在還在不舒服（ongoing_now）已知，
    症狀性質答「上腹」（非最嚴重一級、本來要複誦）→ RF-03 成立 → 不複誦；答「其他」（非胸部症狀）→ 不是 Hard stop → 複誦。"""
    engine, q = RulesEngine(), QB["Q-CHARACTER-01"]
    st = SlotState({"ongoing_now": True})
    assert needs_confirm(q, "epigastric", "上腹悶脹。") and engine.decide(SlotState({"ongoing_now": True, "symptom_character": "epigastric"})).hard_stop
    assert not should_confirm(engine, st, q, "epigastric", "上腹悶脹。")
    assert should_confirm(engine, st, q, "other", "其他。")
    assert not should_confirm(engine, st, QB["Q-NTG-01"], None, "不知道")            # 範圍外


# ---------------------------------------------------------------- 對話流程
class SwallowedLeadPatient(ScriptedPatient):
    """句首「有／沒有」被 STT 吞掉（D-49）：是非題回答沒有明確句首詞，但值正確；複誦時照實再答一次。"""

    def _render(self, q, value):
        if q.answer_type == "yes_no" and value is not None:
            return "現在胸口還是悶悶的，還沒好。" if value else "現在沒有了，已經好了。"
        return super()._render(q, value)


class HeardLessUrgentOnConfirm(SwallowedLeadPatient):
    """驗收者情境：複誦回答被解讀成相反（STT 聽錯，或「對，以前沒有」這種相對回答）。
    是非題 → 相反值；選擇題 → 最不急的「沒有」（none）。"""

    def confirm(self, q, prompt_zh):
        v = self._said.get(q.id)
        if q.answer_type == "yes_no" and v is not None:
            v = not v
        elif q.answer_type == "choice" and v is not None and "none" in slot_defs()[q.slot_id]["choices"]:
            v = "none"
        return PatientReply(value=v, utterance_zh="對，以前沒有。", stt_confidence=1.0)


class UnsureOnConfirmPatient(SwallowedLeadPatient):
    """複誦時答不出來（確認回答不明）。"""

    def confirm(self, q, prompt_zh):
        return PatientReply(value=None, utterance_zh="這個我不太確定耶。", stt_confidence=1.0)


def _case_with_confirmed_denial():
    """第一個「是非題答『沒有』且被複誦」的 case（句首被吞掉的病人）。"""
    for c in all_cases():
        r = run_case(c, patient=SwallowedLeadPatient(c))
        if any(t.confirm_prompt_zh and t.pre_confirm_answer is False for t in r.turns):
            return c
    raise AssertionError("no case")


@pytest.fixture(scope="module")
def swallowed():
    cases = all_cases()
    return cases, [run_case(c, patient=SwallowedLeadPatient(c)) for c in cases]


def test_confirms_not_counted_as_questions_and_do_not_change_flow(swallowed):
    cases, runs = swallowed
    for c, r in zip(cases, runs):
        off = run_case(c, patient=SwallowedLeadPatient(c), confirm_back=False)
        assert off.n_confirms == 0
        assert (r.final.tier, r.final.hard_stop, r.n_questions, [t.question_id for t in r.turns], r.stop_reason) == \
               (off.final.tier, off.final.hard_stop, off.n_questions, [t.question_id for t in off.turns], off.stop_reason), c.id
        assert r.n_confirms == sum(t.confirm_prompt_zh is not None for t in r.turns)
        assert r.n_questions <= load_clinical_rules()["thresholds"]["max_questions"]
    assert sum(r.n_confirms for r in runs) > 100
    capped = [r for r in runs if r.stop_reason == "max_questions" and r.n_confirms]
    assert capped and all(r.n_questions == load_clinical_rules()["thresholds"]["max_questions"] for r in capped)


def test_hard_stop_answer_is_not_confirmed(swallowed):
    _, runs = swallowed
    hs = [r for r in runs if r.stop_reason == "hard_stop"]
    assert hs
    for r in hs:
        last = r.turns[-1]
        assert last.confirm_prompt_zh is None, (r.case_id, last.question_id)     # 寫入即 Hard stop → 不複誦
    for r in runs:                                                               # 最嚴重一級從不複誦
        assert not any(t.confirm_prompt_zh and t.pre_confirm_answer is not None and severity(QB[t.question_id], t.pre_confirm_answer) == 0
                       for t in r.turns), r.case_id


class Rest02HeardAsNoOnConfirm(SwallowedLeadPatient):
    """獨立驗收的情境：只有 Q-REST-02 的複誦回答被解讀成「沒有」（STT 聽錯，或「對，以前沒有」這種相對回答）。"""

    def confirm(self, q, prompt_zh):
        if q.id == "Q-REST-02":
            return PatientReply(value=False, utterance_zh="對，以前沒有。", stt_confidence=1.0)
        return super().confirm(q, prompt_zh)


@pytest.mark.parametrize("case_id", ["S-STABLE-01#0", "S-MID-07#2", "S-MID-19#1"])
def test_regression_rest02_yes_not_downgraded_by_confirm(case_id):
    """獨立驗收找到的三例：Q-REST-02 答「有」（T0）被複誦、複誦回答被解讀成「沒有」→ 曾 T0→T3／T1。"""
    case = next(c for c in all_cases() if c.id == case_id)
    assert run_case(case, patient=ScriptedPatient(case)).final.tier == 0
    r = run_case(case, patient=Rest02HeardAsNoOnConfirm(case))
    assert (r.final.tier, r.final.hard_stop) == (0, False)
    t = next(t for t in r.turns if t.question_id == "Q-REST-02")
    assert t.answer is True and t.confirm_prompt_zh is None                   # 「有」是最嚴重一級 → 不複誦
    assert resolve_confirm(QB["Q-REST-02"], True, False) == (True, True)       # 就算被複誦：確認值較不嚴重 → 保留原值


def test_regression_insuf04_2_daily_heard_as_heavy_stays_t2():
    """獨立驗收的反例：S-INSUF-04#2 病人答呼吸分級「平常走路做家事就喘」，複誦被聽成「只有很激烈的運動才喘」→ 曾 T2 變 T3。
    嚴重度順序 exertional_daily > exertional_heavy → 保留原值，維持 T2。"""
    q = QB["Q-DYSPNEA-GRADE-01"]

    class DailyHeardHeavy(SwallowedLeadPatient):
        def answer(self, qq):
            r = super().answer(qq)
            if qq.id == q.id:
                self._said[qq.id] = "exertional_daily"
                return PatientReply(value="exertional_daily", utterance_zh="平常走路做家事就會。", stt_confidence=1.0)
            return r

        def confirm(self, qq, prompt_zh):
            if qq.id == q.id:
                return PatientReply(value="exertional_heavy", utterance_zh="只有很激烈的運動才會。", stt_confidence=1.0)
            return super().confirm(qq, prompt_zh)

    case = next(c for c in all_cases() if c.id == "S-INSUF-04#2")
    off = run_case(case, patient=DailyHeardHeavy(case), confirm_back=False)
    on = run_case(case, patient=DailyHeardHeavy(case))
    t = next(t for t in on.turns if t.question_id == q.id)
    assert off.final.tier == 2 and (on.final.tier, on.final.hard_stop) == (2, False)
    assert (t.pre_confirm_answer, t.confirm_answer, t.answer, t.confirm_downgrade_blocked) == \
           ("exertional_daily", "exertional_heavy", "exertional_daily", True)


def _final_urgency(r):
    return -1 if r.final.hard_stop else urgency_rank(r.final.tier, r.final_state)


def test_confirm_never_makes_any_case_less_urgent():
    """對抗式：複誦回答一律被解讀成較不嚴重的答案（原值已知時）。與同一病人不複誦相比，沒有任何 case 的最終急迫度變得較不急；
    擋下的降級記在 n_confirm_downgrade_blocked。"""
    blocked = changed = 0
    for c in all_cases():
        off = run_case(c, patient=HeardLessUrgentOnConfirm(c), confirm_back=False)
        on = run_case(c, patient=HeardLessUrgentOnConfirm(c))
        assert _final_urgency(on) <= _final_urgency(off), (c.id, off.final.tier, on.final.tier)
        assert on.n_confirm_downgrade_blocked == sum(t.confirm_downgrade_blocked for t in on.turns)
        for t in on.turns:
            if t.confirm_downgrade_blocked:
                assert t.answer == t.pre_confirm_answer and t.confirm_answer != t.answer
        blocked += on.n_confirm_downgrade_blocked
        changed += on.n_confirm_changed
    assert blocked > 5 and changed > 0            # changed：「沒有」被複誦成「有」→ 升級，允許（最嚴重一級不複誦，故 blocked 較少）


def test_turn_record_and_audit_event():
    case = _case_with_confirmed_denial()
    audit = AuditLog()
    r = run_case(case, patient=SwallowedLeadPatient(case), audit=audit)
    t = next(t for t in r.turns if t.confirm_prompt_zh is not None and QB[t.question_id].answer_type == "yes_no")
    assert t.pre_confirm_answer == t.answer == t.confirm_answer
    assert QB[t.question_id].script_zh.strip() in t.confirm_prompt_zh and t.confirm_utterance_zh
    evs = [e for e in audit.events if e.kind == "confirm_back"]
    assert len(evs) == r.n_confirms
    e = next(e for e in evs if e.payload["question_id"] == t.question_id)
    assert {"pre_value", "prompt_zh", "reply_text", "reply_value", "value"} <= set(e.payload)


def test_unconfirmed_redflag_denial_becomes_unknown():
    seen_false = seen_other = 0
    for c in all_cases():
        r = run_case(c, patient=UnsureOnConfirmPatient(c))
        for t in r.turns:
            if t.confirm_prompt_zh is None:
                continue
            q = QB[t.question_id]
            if q.answer_type == "yes_no" and t.pre_confirm_answer is False:
                assert t.answer is None
                assert r.final_state.get(q.slot_id) is None or r.final_state.is_derived(q.slot_id)
                seen_false += 1
            else:
                assert t.answer == t.pre_confirm_answer and not (q.answer_type == "yes_no" and t.answer is True)
                seen_other += 1
        assert r.n_confirm_changed == sum(t.answer != t.pre_confirm_answer for t in r.turns if t.confirm_prompt_zh)
    assert seen_false > 10 and seen_other > 10


def test_low_confidence_confirm_reply_treated_as_unconfirmed():
    class LowConfConfirm(SwallowedLeadPatient):
        def confirm(self, q, prompt_zh):
            r = super().confirm(q, prompt_zh)
            return PatientReply(value=r.value, utterance_zh=r.utterance_zh, stt_confidence=0.5)
    case = _case_with_confirmed_denial()
    r = run_case(case, patient=LowConfConfirm(case))
    falses = [t for t in r.turns if t.confirm_prompt_zh and QB[t.question_id].answer_type == "yes_no" and t.pre_confirm_answer is False]
    assert falses and all(t.answer is None for t in falses)


def test_scripted_clean_confirms_only_choice_or_unknown_and_report_line():
    results, m = run_all("clean", seed=0)
    for r in results:
        for t in r.turns:
            if t.confirm_prompt_zh:
                q = QB[t.question_id]
                assert q.answer_type == "choice" or t.pre_confirm_answer is None, (r.case_id, t.question_id)
    assert m.confirms == sum(r.n_confirms for r in results) > 0 and m.confirm_changed == m.confirm_downgrade_blocked == 0
    assert m.to_dict()["confirm_back"] == {"n": m.confirms, "per_call": m.confirms / m.n_cases, "changed": 0,
                                           "downgrade_blocked": 0}
    md = render_md("clean", 0, results, m)
    assert f"總數 {m.confirms}；平均每通 {m.mean_confirms:.2f}；確認後改值 0；確認值較不嚴重而保留原值 0" in md
    runs = [run_case(c, patient=HeardLessUrgentOnConfirm(c)) for c in all_cases()]
    m2 = compute(runs)
    assert m2.confirm_downgrade_blocked == sum(r.n_confirm_downgrade_blocked for r in runs) > 0
    assert f"確認值較不嚴重而保留原值 {m2.confirm_downgrade_blocked}" in render_md("x", 0, runs, m2)


def test_transcripts_value_matches_utterance_and_old_readers_work():
    """逐字稿 turns 一題一筆；value 是同一筆 utterance_zh 的值（= 確認前的值），確認後的值與複誦內容在 confirm 欄位。
    舊讀取端（openai_eval、extractor_e2e、openai_slots、stt_eval build）讀到的 value 都是該句話的正解。"""
    from sim import stt_eval
    from sim.extractor_e2e import replay
    from sim.openai_eval import rf_steps
    from sim.openai_slots import turns as slot_turns
    from sim.run_llm_eval import transcripts_json
    cases = all_cases()
    runs = [run_case(c, patient=UnsureOnConfirmPatient(c)) for c in cases]      # 確認回答不明 → 有些值會被改成 None
    tr = json.loads(json.dumps(transcripts_json(runs, cases), ensure_ascii=False, default=str))
    said = {}
    for r, t in zip(runs, tr):
        assert len(t["turns"]) == r.n_questions
        for i, (turn, x) in enumerate(zip(r.turns, t["turns"]), 1):
            pre = turn.pre_confirm_answer if turn.confirm_prompt_zh else turn.answer
            said[(r.case_id, i)] = pre
            assert (x["q"], x["value"], x["utterance_zh"]) == (turn.question_id, pre, turn.utterance_zh)
            assert ("confirm" in x) == (turn.confirm_prompt_zh is not None)
            if "confirm" in x:
                assert x["confirm"] == {"prompt_zh": turn.confirm_prompt_zh, "utterance_zh": turn.confirm_utterance_zh,
                                        "value": turn.confirm_answer, "adopted_value": turn.answer,
                                        "downgrade_blocked": turn.confirm_downgrade_blocked}
    assert any("confirm" in x and x["confirm"]["adopted_value"] != x["value"] for t in tr for x in t["turns"])
    assert len(rf_steps(tr)) == sum(len(t["turns"]) + 1 for t in tr)
    results, slot_rows, _ = replay(tr, extract)
    assert len(results) == len(tr) and all(row["truth"] == said[(row["case_id"], row["turn"])] for row in slot_rows)
    items = slot_turns(tr, None)
    assert len(items) == len(said) and all(it["truth"] == said[(it["case_id"], it["turn"])] for it in items)
    for u in stt_eval.build_utterances(tr, QB, stt_eval.critical_question_ids()):
        for src in u["sources"]:
            if src["kind"] == "answer":
                assert src["value"] == said[(src["case_id"], src["turn"])]



def test_exhaustive_known_original_never_less_urgent():
    """窮舉（嚴重度順序版）：每個 case 的每一次複誦，把複誦回答換成該題每個合法值（含 None）。原值已知時，最終急迫度都不得比
    不複誦時較不急；原值不明而複誦得到較不嚴重答案（等同重問）的只限已知的 3 組（見 CLINICAL_RULES §5.10 第 8 點）。"""
    class OneAlt(SwallowedLeadPatient):
        def __init__(self, case, qid, alt):
            super().__init__(case)
            self.qid, self.alt = qid, alt

        def confirm(self, q, prompt_zh):
            if q.id == self.qid:
                return PatientReply(value=self.alt, utterance_zh="（模擬）", stt_confidence=1.0)
            return super().confirm(q, prompt_zh)

    n, from_unknown = 0, set()
    for c in all_cases():
        off = run_case(c, patient=SwallowedLeadPatient(c), confirm_back=False)
        for t in run_case(c, patient=SwallowedLeadPatient(c)).turns:
            if not t.confirm_prompt_zh:
                continue
            q = QB[t.question_id]
            alts = [True, False, None] if q.answer_type == "yes_no" else list(slot_defs()[q.slot_id]["choices"]) + [None]
            for alt in alts:
                on = run_case(c, patient=OneAlt(c, q.id, alt))
                n += 1
                if _final_urgency(on) > _final_urgency(off):
                    assert t.pre_confirm_answer is None, (c.id, q.id, t.pre_confirm_answer, alt)
                    from_unknown.add((c.id, q.id, alt))
    assert n > 1000
    assert from_unknown == {("S-INSUF-04", "Q-DYSPNEA-GRADE-01", "none"), ("S-INSUF-04#1", "Q-DYSPNEA-GRADE-01", "none"),
                            ("S-MID-13#3", "Q-REST-02", False)}
