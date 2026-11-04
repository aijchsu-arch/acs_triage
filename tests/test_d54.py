"""D-54（Clinical Owner 2026-11-02 裁定，rules 0.9.0）：(A) 發作變頻繁、(B) 概括否認照原流程逐題問、(C) 提到胸口不適但性質未知、
(D) 開場白 vague 再問、(E) 順口值矛盾再問、題數上限 12，與抽取器提示 2.0-dev24。全部用假抽取器，不打 API。"""
import dataclasses
import json

import pytest
import yaml

from acs_triage.audit import AuditLog
from acs_triage.extract import extract
from acs_triage.loaders import DATA_DIR, bank_version, load_clinical_rules, question_by_id, rules_version, slot_defs
from acs_triage.pathway import tier9_fallback
from acs_triage.prompter import Prompter
from acs_triage.prompter.confirm import in_scope, reask_prompt
from acs_triage.rules import RulesEngine, SlotState
from helpers import decide_slots
from sim.cases import _complete, all_cases
from sim import closed_loop as cl
from sim import synth_eval as se
from sim.closed_loop import dev_metrics, hs_supported
from pathlib import Path

from sim.llm_extract_v2 import build_request, load_prompts, mention_slots, parse, system_prompt
from sim.metrics import compute
from sim.patient import ScriptedPatient
from sim.run_eval import render_md, run_all
from sim.run_llm_eval import transcript_meta, transcripts_json
from sim.runner import run_case

QB = question_by_id()
CASES = {c.id: c for c in all_cases()}
RAW_QUESTIONS = {q["id"]: q for q in yaml.safe_load((DATA_DIR / "question_bank_seed.yaml").read_text(encoding="utf-8"))["questions"]}
CHEST_RF = {"Q-ONGOING-01", "Q-SYNCOPE-01", "Q-DIAPH-01"}


class Echo:
    """假抽取器：開場白回傳指定值；被問的題目回傳病人事實（可用 override 改），順口值由 mentions 依題目給。"""

    def __init__(self, case, opening=None, mentions=None, override=None):
        self.case, self.opening, self.mentions, self.override = case, opening or {}, mentions or {}, override or {}
        self.confirm_prompts = []

    def __call__(self, text, q, confirm_prompt=None):
        if q is None:
            return dict(self.opening)
        if confirm_prompt is not None:
            self.confirm_prompts.append((q.id, confirm_prompt))
        v = self.override[q.id] if q.id in self.override else ScriptedPatient(self.case).answer(q).value
        return {q.slot_id: v, **({} if confirm_prompt else self.mentions.get(q.id, {}))}


def _case(cid="S-MID-20", opening=None, **slots):
    base = CASES[cid]
    opening = opening or base.opening_zh
    merged = {**base.slots, **slots}
    return dataclasses.replace(base, opening_zh=opening, slots=_complete(merged))


def _qs(r):
    return [t.question_id for t in r.turns]


EDU = {"cad_history": True, "consult_topic": "education_question"}


# ---------------------------------------------------------------- 版本與題庫
def test_versions_and_draft_questions():
    assert rules_version() == "0.9.0"
    assert load_prompts()["prompts_version"] == "2.0-dev24"
    assert load_clinical_rules()["thresholds"]["max_questions"] == 12
    assert yaml.safe_load((DATA_DIR / "question_bank_seed.yaml").read_text(encoding="utf-8"))["bank_version"] == "0.5"
    assert RAW_QUESTIONS["Q-FREQ-01"]["status"] == "DRAFT" and "DRAFT" in RAW_QUESTIONS["Q-FREQ-01"]["why_zh"]
    assert QB["Q-FREQ-01"].priority == "decisive"
    assert QB["Q-FREQ-01"].script_zh == "最近發作的次數有比以前多嗎？"


def test_draft_marker_never_in_spoken_text():
    for q in QB.values():
        assert "DRAFT" not in q.script_zh, q.id


# ---------------------------------------------------------------- (A) 發作變頻繁（比照 ntg_use_increased）
BASE_STABLE = {"symptom_character": "tightness", "pattern_unchanged_duration_months": 24, "rest_symptom": False,
               "threshold_decreased": False, "dyspnea_acute": False, "ongoing_now": False, "presyncope": False, "diaphoresis": False,
               "ntg_use_increased": False}


def test_a_frequency_is_t0_not_hard_stop(engine):
    d = decide_slots(engine, {**BASE_STABLE, "episode_frequency_increased": True})
    assert d.provisional_tier == 0 and not d.hard_stop and "T0-FREQ-INCREASED" in d.evidence


def test_a_mirrors_ntg_everywhere(engine):
    """gate、穩定型排除、反覆休息時症狀、無症狀判斷、Prompter 相關性都和 ntg_use_increased 一樣。"""
    d = decide_slots(engine, BASE_STABLE)
    assert d.provisional_tier == 3 and d.tier == 9 and d.missing == ["episode_frequency_increased"]
    ok = decide_slots(engine, {**BASE_STABLE, "episode_frequency_increased": False})
    assert ok.tier == 3 and ok.gate_passed
    assert not SlotState({"episode_frequency_increased": True}).no_symptoms()
    rec = {"symptom_character": "tightness", "pattern_unchanged_duration_months": 12, "rest_symptom": True, "rest_symptom_first_time": False,
           "onset_new": False, "threshold_decreased": False, "ntg_use_increased": False, "cad_history": True, "dyspnea_acute": False,
           "ongoing_now": False, "presyncope": False, "diaphoresis": False, "antiplatelet_interrupted": False}
    d2 = decide_slots(engine, rec)
    assert d2.provisional_tier == 3 and "episode_frequency_increased" in d2.missing     # 明確否認才能定案（D-45）
    assert decide_slots(engine, {**rec, "episode_frequency_increased": True}).provisional_tier == 0
    assert decide_slots(engine, {**rec, "episode_frequency_increased": False}).tier == 3
    p = Prompter()
    q = QB["Q-FREQ-01"]
    assert p.next_question(SlotState({"symptom_character": "none", "dyspnea_grade": "none"}), asked=set()) != q
    from acs_triage.prompter.prompter import _relevant
    assert _relevant(q, SlotState({"symptom_character": "pressure"})) and not _relevant(q, SlotState({"symptom_character": "none"}))


def test_a12_t0_freq_gate_requires_chest_red_flags(engine):
    d = decide_slots(engine, {"symptom_character": "pressure", "episode_frequency_increased": True})
    assert d.provisional_tier == 0 and not d.gate_passed and {"ongoing_now", "presyncope", "diaphoresis"} <= set(d.missing)
    ok = decide_slots(engine, {"symptom_character": "pressure", "episode_frequency_increased": True, "ongoing_now": False, "presyncope": False, "diaphoresis": False})
    assert ok.gate_passed and ok.tier == 0


@pytest.mark.parametrize("text,expect", [
    ("我的胸悶最近發作的次數變多了", True),
    ("發作越來越頻繁，走路也會", True),
    ("最近越來越常發作", True),
    ("發作沒有變多，都一樣", False),
    ("沒有發作變多的情形", None),                          # 否定詞在前 → 不算有（留給題目問）
])
def test_a_keyword_extraction_and_negation(text, expect):
    assert extract(text).get("episode_frequency_increased") is expect


def test_a_patient_without_the_field_answers_no_not_unknown():
    """舊情境 hidden_slots 沒有這個欄位 → 模擬病人答「沒有」，gate 不卡住（sim/cases.py _complete）。"""
    assert all(c.slots["episode_frequency_increased"] is False for c in CASES.values())
    c = CASES["S-STABLE-01"]
    r = run_case(c)
    assert "Q-FREQ-01" in _qs(r) and r.final.tier == c.truth_tier
    assert ScriptedPatient(c).answer(QB["Q-FREQ-01"]).utterance_zh == "沒有。"


def test_a_yes_escalates_to_t0_in_a_full_call():
    c = CASES["S-STABLE-01"]
    r = run_case(dataclasses.replace(c, slots={**c.slots, "episode_frequency_increased": True}))
    assert r.final.tier == 0 and not r.final.hard_stop and "T0-FREQ-INCREASED" in r.final.evidence


@pytest.mark.parametrize("cid", ["S-ACUTE-05#1", "S-INSUF-01#1", "S-INSUF-02#1", "S-MID-04#0", "S-MID-15#0"])
def test_a_cap_cases_asked_within_twelve_and_keep_truth(cid):
    """這 5 例上限 11 時放不下 Q-FREQ-01；上限 12（Clinical Owner 2026-11-02）全部問得完，分級等於 truth；答「有」→ T0。"""
    c = CASES[cid]
    r = run_case(c)
    assert "Q-FREQ-01" in _qs(r) and r.final.tier == c.truth_tier and r.n_questions == len(r.turns) <= 12
    up = run_case(dataclasses.replace(c, slots={**c.slots, "episode_frequency_increased": True}))
    assert up.final.tier == 0 and not up.final.hard_stop


def test_a_every_question_counts_and_over_cap_goes_t9():
    """所有問題都計入；只有再說一次、複誦、矛盾再問不計。超過上限照常走 T9，Q-FREQ-01 沒有例外。"""
    results, m = run_all("clean", seed=0)
    assert all(r.n_questions == len(r.turns) <= 12 for r in results)
    assert m.pending_test_asked == 20 and m.pending_test_skipped_at_cap == 2
    c = CASES["S-INSUF-02#1"]
    capped = run_case(c, max_questions=11)
    assert capped.n_questions == 11 and capped.final.tier == 9 and capped.stop_reason == "max_questions" and capped.final.provisional_tier == 3
    assert capped.final.missing                                 # 差必問題 → gate 沒過


# ---------------------------------------------------------------- (B) 概括否認照原流程逐題問（合併題試做後放棄，D-54）
def test_b_red_flag_question_set_is_back_to_the_six_before_d54():
    assert sorted(q.id for q in QB.values() if q.priority == "redflag") == sorted(
        ["Q-ONGOING-01", "Q-SYNCOPE-01", "Q-SYNCOPE-02", "Q-DYSPNEA-GRADE-01", "Q-DYSPNEA-SENTENCE-01", "Q-DIAPH-01"])
    assert all(c.slots.keys() <= set(slot_defs()) for c in CASES.values())


@pytest.mark.parametrize("cid,tier,qs", [("S-MID-20", 4, ["Q-DYSPNEA-GRADE-01", "Q-SCREEN-01", "Q-SYNCOPE-01"]),
                                         ("S-MID-09", 1, ["Q-DYSPNEA-GRADE-01", "Q-SYNCOPE-01"])])
def test_b_denying_openings_same_level_and_questions_as_before_d54(cid, tier, qs):
    r = run_case(CASES[cid])
    assert r.final.tier == tier == CASES[cid].truth_tier and not r.final.hard_stop and _qs(r) == qs


def test_b_third_party_s_mid_17_1_stays_hard_stop():
    r = run_case(CASES["S-MID-17#1"])
    assert r.final.hard_stop and "RF-03" in r.final.rf_hits
    assert run_case(CASES["S-MID-17"]).final.tier == CASES["S-MID-17"].truth_tier


@pytest.mark.parametrize("opening", [None, dict(EDU)], ids=["keyword", "llm_null"])
def test_b_opening_says_fine_but_dyspnea_at_rest_stays_hard_stop(opening):
    case = _case(dyspnea_grade="rest")
    r = run_case(case) if opening is None else run_case(case, extractor=Echo(case, opening=opening))
    assert r.final.hard_stop and "RF-02" in r.final.rf_hits and _qs(r)[0] == "Q-DYSPNEA-GRADE-01"


# ---------------------------------------------------------------- (C) 提到胸口不適但性質未知
def test_c_chest_symptom_present_rules():
    assert SlotState({"chest_discomfort_mentioned": True}).chest_symptom_present()
    assert not SlotState({"chest_discomfort_mentioned": True, "symptom_character": "none"}).chest_symptom_present()
    assert not SlotState({"chest_discomfort_mentioned": True, "symptom_character": "other"}).chest_symptom_present()
    assert SlotState({"chest_discomfort_mentioned": True, "symptom_character": "vague"}).chest_symptom_present()
    assert not SlotState({}).chest_symptom_present() and not SlotState({"chest_discomfort_mentioned": False}).chest_symptom_present()


@pytest.mark.parametrize("slot,rf", [("presyncope", "RF-01"), ("ongoing_now", "RF-03"), ("diaphoresis", "RF-06")])
def test_c_red_flags_fire_with_flag_and_not_without(engine, slot, rf):
    assert rf in decide_slots(engine, {"chest_discomfort_mentioned": True, slot: True}).rf_hits
    assert not decide_slots(engine, {"chest_discomfort_mentioned": True, slot: False}).hard_stop
    assert not decide_slots(engine, {slot: True}).hard_stop                                       # 沒提胸口：單獨冒汗等不構成（既有）
    assert not decide_slots(engine, {"chest_discomfort_mentioned": True, "symptom_character": "none", slot: True}).hard_stop


@pytest.mark.parametrize("text,flag", [("胸口有點卡卡的", True), ("我胸部怪怪", True), ("胸口沒有不舒服", False), ("胸口不會痛", False),
                                       ("沒有胸口的問題", False), ("想問回診要不要空腹", False)])
def test_c_keyword_path_sets_flag(text, flag):
    assert bool(extract(text).get("chest_discomfort_mentioned")) is flag


def test_c_keyword_flag_does_not_touch_benchmark_openings():
    for c in CASES.values():
        assert not extract(c.opening_zh).get("chest_discomfort_mentioned"), c.id


@pytest.mark.parametrize("cid,first_rf", [("S-MID-13#0", "Q-DIAPH-01"), ("S-MID-13#1", "Q-ONGOING-01"), ("S-INSUF-07#0", "Q-ONGOING-01")])
def test_c_red_flags_before_dyspnea_grade_and_character(cid, first_rf):
    """裁定 #15 列舉的三例：開場白性質未知（「胸口脹脹的」）或 vague（「胸口不太舒服」），Hard stop 的紅旗題排在呼吸分級、性質題之前。"""
    c = CASES[cid]
    opening = {"cad_history": True}
    if cid.startswith("S-MID-13"):
        opening |= {"chest_discomfort_mentioned": True, "postprandial_relieved": True, "last_episode_timing": "today"}
        if cid == "S-MID-13#0":
            opening["ongoing_now"] = False
    else:
        opening |= {"symptom_character": "vague", "third_party_call": True}
    r = run_case(c, extractor=Echo(c, opening=opening))
    qs = _qs(r)
    assert r.final.hard_stop and qs[-1] == first_rf
    assert "Q-DYSPNEA-GRADE-01" not in qs and "Q-CHARACTER-01" not in qs
    assert set(qs) <= CHEST_RF


def test_c_order_when_no_red_flag_then_character_then_decisive():
    c = CASES["S-MID-13"]
    opening = {"cad_history": True, "chest_discomfort_mentioned": True, "postprandial_relieved": True, "ongoing_now": False,
               "last_episode_timing": "today"}
    r = run_case(c, extractor=Echo(c, opening=opening))
    qs = _qs(r)
    assert qs.index("Q-DIAPH-01") < qs.index("Q-DYSPNEA-GRADE-01") < qs.index("Q-CHARACTER-01")
    assert qs.index("Q-SYNCOPE-01") < qs.index("Q-DYSPNEA-GRADE-01")
    assert r.final.tier == c.truth_tier                         # 問到性質（上腹）後回到既有 carve-out T3


def test_c_mention_not_written_still_marks_chest_symptom():
    """順口提到較不嚴重的性質（D-50 不直接寫入）：性質仍未知，但視為胸部症狀，胸部紅旗題要先問（裁定 #15）。"""
    c = CASES["S-INSUF-07#0"]
    ex = Echo(c, opening={"cad_history": True, "third_party_call": True, "patient_reachable": True},
              mentions={"Q-DYSPNEA-GRADE-01": {"symptom_character": "vague"}})
    r = run_case(c, extractor=ex)
    qs = _qs(r)
    assert qs[0] == "Q-DYSPNEA-GRADE-01" and r.final.hard_stop and qs[1] == "Q-ONGOING-01" and "Q-CHARACTER-01" not in qs
    st = SlotState({})
    from sim.runner import _write_mentions
    _write_mentions(st, {"symptom_character": "none"}, "__none__", source="m")
    assert not st.chest_symptom_present()                     # 否認不算


def test_c_known_character_order_unchanged():
    s = SlotState({"symptom_character": "pressure", "ongoing_now": False, "presyncope": False})
    assert Prompter().next_question(s, asked=set()).id == "Q-DYSPNEA-GRADE-01"        # 性質已知：沿用題庫順序


def test_c_hs_supported_uses_fact_sheet_for_flag():
    c = CASES["S-MID-13#1"]
    st = SlotState({"chest_discomfort_mentioned": True, "ongoing_now": True})
    assert hs_supported(c, st)                                  # 事實清單性質為上腹 → 不是抽錯造成的假 Hard stop
    no_chest = dataclasses.replace(c, slots={**c.slots, "symptom_character": "none"})
    assert not hs_supported(no_chest, st)


def test_c_parse_sets_flag_from_unclassified_or_model():
    obj = {"evidence": [{"slot": "symptom_character", "quote": "胸口脹脹的"}], **{k: None for k in mention_slots()},
           "unclassified": [{"slot": "symptom_character", "phrase": "胸口脹脹的"}]}
    slots, _ = parse(obj, "胸口脹脹的。", None)
    assert slots.get("chest_discomfort_mentioned") is True and "symptom_character" not in slots
    obj2 = {**obj, "unclassified": [{"slot": "symptom_character", "phrase": "不舒服"}]}          # 單獨的「不舒服」不算
    assert "chest_discomfort_mentioned" not in parse(obj2, "不舒服。", None)[0]
    obj3 = {**obj, "unclassified": [{"slot": "symptom_character", "phrase": "胸口沒有脹"}]}
    assert "chest_discomfort_mentioned" not in parse(obj3, "胸口沒有脹。", None)[0]
    obj4 = {"evidence": [{"slot": "chest_discomfort_mentioned", "quote": "胸口沒有不舒服"}], **{k: None for k in mention_slots()},
            "unclassified": []}
    obj4["chest_discomfort_mentioned"] = True
    assert "chest_discomfort_mentioned" not in parse(obj4, "胸口沒有不舒服。", None)[0]          # 肯定值但原句是否定 → 丟棄


# ---------------------------------------------------------------- (D) 開場白 vague 再問
VAGUE_TODAY = {"symptom_character": "tightness", "onset_new": True, "last_episode_timing": "today", "ongoing_now": False}


def _vague_case(**facts):
    c = CASES["S-INSUF-01"]
    return dataclasses.replace(c, slots={**c.slots, **facts}, persona="normal", reset_slots=[])


def test_d_opening_vague_asks_character_after_chest_red_flags_and_takes_more_severe():
    case = _vague_case(**VAGUE_TODAY)
    r = run_case(case, extractor=Echo(case, opening={"symptom_character": "vague", "cad_history": True}))
    qs = _qs(r)
    assert "Q-CHARACTER-01" in qs and all(qs.index(x) < qs.index("Q-CHARACTER-01") for x in ("Q-SYNCOPE-01", "Q-DIAPH-01"))
    assert r.final_state.get("symptom_character") == "tightness" and r.final.tier == 0 and "T0-NEW-TODAY" in r.final.evidence
    assert qs.index("Q-ONSET-01") < qs.index("Q-CHARACTER-01")   # 再問排在後面，不搶 gate 必問題的題數


def test_d_vague_recheck_earlier_when_dyspnea_present():
    """呼吸類決定題會用掉題數：有呼吸症狀時性質再問提前（順序 D：H3 兩題、新發之後），否則問不到（新發今天的壓迫會落 T9）；沒有呼吸症狀時排在時序題之後。"""
    facts = {"symptom_character": "pressure", "onset_new": True, "last_episode_timing": "today", "ongoing_now": False, "presyncope": False, "diaphoresis": False,
             "rest_symptom": False, "threshold_decreased": False, "ntg_use_increased": False, "episode_frequency_increased": False, "exertion_relation": "both"}
    op = {"symptom_character": "vague", "cad_history": True}
    for grade in ("exertional_heavy", "exertional_daily"):
        case = _vague_case(**facts, dyspnea_grade=grade, cant_finish_sentence=False, dyspnea_acute=False, orthopnea_pnd=False)
        r = run_case(case, extractor=Echo(case, opening=op))
        qs = _qs(r)
        assert r.final.tier == 0 and "T0-NEW-TODAY" in r.final.evidence, grade
        assert qs.index("Q-DYSPNEA-GRADE-01") < qs.index("Q-ONSET-01") < qs.index("Q-CHARACTER-01")     # 順序 D（Clinical Owner 2026-11-03）
    no_dyspnea = _vague_case(**facts, dyspnea_grade="none")
    r = run_case(no_dyspnea, extractor=Echo(no_dyspnea, opening=op))
    assert r.final.tier == 0 and _qs(r).index("Q-ONSET-01") < _qs(r).index("Q-CHARACTER-01")
    assert _qs(r).index("Q-TIMING-01") < _qs(r).index("Q-CHARACTER-01")                      # P7：排在時序題「之後」


def test_r13_character_followup_respects_cap():
    """只提過胸口、性質未知：胸部紅旗題後問性質，但到題數上限就不問（所有問題都計入，沒有例外）。"""
    c = CASES["S-MID-13"]
    op = {"cad_history": True, "chest_discomfort_mentioned": True, "ongoing_now": False}
    r = run_case(c, extractor=Echo(c, opening=op), max_questions=3)
    assert r.n_questions == 3 and "Q-CHARACTER-01" not in _qs(r) and r.stop_reason == "max_questions"
    assert "Q-CHARACTER-01" in _qs(run_case(c, extractor=Echo(c, opening=op), max_questions=4))


def test_d_recheck_only_when_room_left_after_gate_questions():
    """gate 必問題優先：開場白 vague 判穩定型，題數夠才再問；不夠就不問、也不會因此變 T9。"""
    c = CASES["S-INSUF-01#1"]
    tight = run_case(c)
    assert tight.n_questions == 12 and tight.final.tier == 3 and "Q-CHARACTER-01" not in _qs(tight) and tight.pending_test_asked
    roomy = run_case(c, max_questions=13)
    qs = _qs(roomy)
    assert roomy.final.tier == 3 and qs[-1] == "Q-PENDINGTEST-01" and "Q-CHARACTER-01" in qs
    p, e = Prompter(), RulesEngine()
    s = SlotState({"symptom_character": "vague"})
    assert p.vague_recheck_question(s, e.decide(s), set()) == QB["Q-CHARACTER-01"]
    assert p.vague_recheck_question(s, e.decide(s), {"Q-CHARACTER-01"}) is None


@pytest.mark.parametrize("answer", [None, "none", "other"])
def test_d_less_severe_or_unknown_answer_keeps_vague(answer):
    case = _vague_case()
    ex = Echo(case, opening={"symptom_character": "vague", "cad_history": True}, override={"Q-CHARACTER-01": answer})
    r = run_case(case, extractor=ex)
    assert "Q-CHARACTER-01" in _qs(r) and r.final_state.get("symptom_character") == "vague"
    assert r.final_state.chest_symptom_present() and tier9_fallback(r.final_state)[0] == 1


def test_d_direct_answer_vague_is_not_reasked():
    case = _vague_case()
    r = run_case(case, extractor=Echo(case, opening={"cad_history": True, "chest_discomfort_mentioned": True}))
    assert _qs(r).count("Q-CHARACTER-01") == 1 and r.final_state.get("symptom_character") == "vague"
    p, e = Prompter(), RulesEngine()
    s = SlotState({"ongoing_now": False, "presyncope": False, "diaphoresis": False, "dyspnea_grade": "none"})
    s.set("symptom_character", "vague", asked_by="Q-CHARACTER-01")
    assert p.vague_recheck_question(s, e.decide(s), set()) is None                        # asked_by 有值 ＝ 直接回答
    assert p.character_followup_question(s, e.decide(s), set()) is None
    assert p.next_question(s, asked=set()) != QB["Q-CHARACTER-01"]


def test_d_hard_stop_or_t0_is_not_delayed():
    p, e = Prompter(), RulesEngine()
    base = {"symptom_character": "vague", "ongoing_now": False, "presyncope": False, "diaphoresis": False, "dyspnea_grade": "none"}
    s = SlotState({**base, "ntg_use_increased": True})                                    # T0
    assert e.decide(s).provisional_tier == 0 and p.vague_recheck_question(s, e.decide(s), set()) is None
    hs = SlotState({**base, "diaphoresis": True})
    assert e.decide(hs).hard_stop and p.vague_recheck_question(hs, e.decide(hs), set()) is None
    flag_hs = SlotState({"chest_discomfort_mentioned": True, "ongoing_now": True, "presyncope": False, "diaphoresis": False, "dyspnea_grade": "none"})
    assert e.decide(flag_hs).hard_stop and p.character_followup_question(flag_hs, e.decide(flag_hs), set()) is None
    pending = SlotState({"chest_discomfort_mentioned": True})                             # 胸部紅旗題還沒問完 → 先問紅旗
    assert p.character_followup_question(pending, e.decide(pending), set()) is None
    assert p.next_question(pending, asked=set()).id == "Q-ONGOING-01"


def test_m2_mentioned_vague_then_none_same_as_opening_vague():
    """順口 vague 暫存，之後性質題答 none → 與開場白 vague 同結果：保留 vague、備援 T1（規格 (D) 取較嚴重者）。"""
    case = _vague_case()
    answers = {"Q-CHARACTER-01": "none"}
    from_opening = run_case(case, extractor=Echo(case, opening={"symptom_character": "vague", "cad_history": True}, override=answers))
    mentioned = run_case(case, extractor=Echo(case, opening={"cad_history": True}, override=answers,
                                              mentions={"Q-DYSPNEA-GRADE-01": {"symptom_character": "vague"}}))
    for r in (from_opening, mentioned):
        assert r.final_state.get("symptom_character") == "vague" and r.final_state.chest_symptom_present()
        assert r.final.tier == 9 and tier9_fallback(r.final_state)[0] == 1
    more = run_case(case, extractor=Echo(case, opening={"cad_history": True}, override={"Q-CHARACTER-01": "pressure"},
                                         mentions={"Q-DYSPNEA-GRADE-01": {"symptom_character": "vague"}}))
    assert more.final_state.get("symptom_character") == "pressure"      # 答得較嚴重 → 用回答


def test_d_scripted_vague_openings_keep_truth():
    results, m = run_all("clean", seed=0)
    assert m.exact_rate == 1.0 and m.under_triage == [] and m.hard_stop_miss == []
    by_id = {r.case_id: r for r in results}
    assert "Q-CHARACTER-01" in _qs(by_id["S-INSUF-01"]) and by_id["S-INSUF-01"].final.tier == 9
    assert by_id["S-INSUF-01#1"].final.tier == 3                        # 例外 A 仍成立


def test_d10_synth_replay_takes_more_severe_like_runner():
    c = CASES["S-INSUF-01"]
    r = run_case(c)
    t = next(x for x in r.turns if x.question_id == "Q-CHARACTER-01")
    assert t.answer is None and r.final_state.get("symptom_character") == "vague"     # persona vague 答不知道
    out = se.replay(c, transcripts_json([r], [c])[0])
    assert out["tier"] == 9 and out["urg"] == 1                         # 保留 vague：備援 T1


# ---------------------------------------------------------------- (E) 順口值矛盾再問
def _conflict_run(known_slot="onset_new", known=True, mention=False, reply=None, reply_conf=1.0, case_id="S-ACUTE-01", mention_at=None,
                  reply_mentions=None, tw=None, confirm_back=None):
    c = CASES[case_id]
    opening = {**extract(c.opening_zh), known_slot: known}
    q_of_slot = next(q for q in QB.values() if q.slot_id == known_slot)

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            out = super().__call__(text, q, confirm_prompt)
            if q is not None and q.id != q_of_slot.id and confirm_prompt is None and (mention_at is None or q.id == mention_at):
                out[known_slot] = mention
            if q is not None and q.id == q_of_slot.id and confirm_prompt and reply_mentions:
                out.update(reply_mentions)                  # 再問回覆裡順口提到的其他 slot
            self.texts.append(text)
            return out

    class P(ScriptedPatient):
        def confirm(self, q, prompt_zh):
            r = super().confirm(q, prompt_zh)
            return dataclasses.replace(r, stt_confidence=reply_conf) if q.id == q_of_slot.id else r

    audit = AuditLog()
    ex = E(c, opening=opening, override={q_of_slot.id: reply})
    ex.texts = []
    return run_case(c, patient=P(c), extractor=ex, audit=audit, to_traditional=tw, confirm_back=confirm_back), audit, ex, q_of_slot


def test_e_non_d50_slot_takes_reask_answer_and_records_downgrade():
    r, audit, ex, q = _conflict_run(reply=False)
    assert len(r.reasks) == 1 and r.reasks[0]["question_id"] == q.id and r.reasks[0]["value"] is False
    assert r.final_slots["onset_new"] is False and not in_scope(q)
    assert r.reask_downgrades == r.reasks                           # 新發 → 不是新發：最終較不急，要數得出來
    assert len([e for e in audit.events if e.kind == "mention_reask"]) == 1
    assert len([e for e in audit.events if e.kind == "reask_downgrade"]) == 1
    assert any(x["kind"] == "conflict" and x.get("reasked") for x in r.mention_conflicts)
    assert (q.id, reask_prompt(q)) in ex.confirm_prompts


def test_m3_reask_downgrade_counterfactual_at_end_of_call():
    """當下分級沒變、之後才分岔的也要記到：再問把 onset_new 改成 False，最後抗血小板中斷 T1-ANTIPLT 不成立（驗收 fm_flip|2|S-MID-08#2）。"""
    c = CASES["S-MID-08#2"]
    assert c.slots["antiplatelet_interrupted"] is True

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            out = super().__call__(text, q, confirm_prompt)
            if q is not None and q.id == "Q-ONSET-01" and confirm_prompt:
                out[q.slot_id] = False                      # 再問聽成「不是新發」
            elif q is not None and q.id == "Q-DYSPNEA-GRADE-01":
                out["onset_new"] = False                    # 順口矛盾
            return out

    op = {**{k: v for k, v in extract(c.opening_zh).items() if v is not None}, "onset_new": True}
    r = run_case(c, extractor=E(c, opening=op))
    assert r.reasks and r.final_slots["onset_new"] is False
    assert r.reask_downgrades == r.reasks
    # 再問沒有造成差別的不算
    same = run_case(c, extractor=Echo(c, opening=op))
    assert same.reask_downgrades == []


def test_e_non_d50_unknown_answer_keeps_original_and_no_downgrade():
    r, *_ = _conflict_run(reply=None)
    assert r.reasks[0]["value"] is True and r.final_slots["onset_new"] is True and r.reask_downgrades == []
    r2, *_ = _conflict_run(reply=True)
    assert r2.final_slots["onset_new"] is True and r2.reask_downgrades == []


def test_e_low_confidence_answer_treated_as_unknown():
    r, *_ = _conflict_run(reply=False, reply_conf=0.3)
    assert r.reasks[0]["value"] is True and r.final_slots["onset_new"] is True


def test_e_at_most_once_per_slot_and_not_counted():
    r, _, ex, q = _conflict_run(reply=True)
    assert len(r.reasks) == 1 and sum(1 for qid, _ in ex.confirm_prompts if qid == q.id) == 1
    assert len([x for x in r.mention_conflicts if x["slot"] == "onset_new"]) >= 1
    base = run_case(CASES["S-ACUTE-01"], extractor=Echo(CASES["S-ACUTE-01"], opening={**extract(CASES["S-ACUTE-01"].opening_zh), "onset_new": True}))
    assert r.n_questions == base.n_questions and q.id not in _qs(r)      # 再問不算題數、不是一般題


def test_e_d50_slot_keeps_more_severe():
    """D-50 範圍內：再問不覆蓋「取較嚴重者」的既有裁定。"""
    c = CASES["S-MID-06"]
    opening = {"dyspnea_grade": "exertional_daily", "dyspnea_complaint": True}

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            if q is None:
                return dict(self.opening)
            if q.id == "Q-DYSPNEA-GRADE-01":
                return {q.slot_id: "none"}                  # 再問答「沒有」
            out = super().__call__(text, q, confirm_prompt)
            if confirm_prompt is None:
                out["dyspnea_grade"] = "exertional_heavy"   # 順口說比較輕
            return out

    r = run_case(c, extractor=E(c, opening=opening))
    assert r.reasks and r.reasks[0]["slot"] == "dyspnea_grade" and r.reasks[0]["value"] == "exertional_daily"
    assert r.final_slots["dyspnea_grade"] == "exertional_daily" and r.reask_downgrades == []
    assert in_scope(QB["Q-DYSPNEA-GRADE-01"])


def test_e_no_reask_when_same_level_or_already_most_severe():
    c = CASES["S-ACUTE-01"]
    every = lambda m: {qid: m for qid in QB}
    same = run_case(c, extractor=Echo(c, opening={**extract(c.opening_zh), "symptom_character": "pressure"}, mentions=every({"symptom_character": "tightness"})))
    assert same.reasks == [] and any(x["slot"] == "symptom_character" and x["kind"] == "conflict" and not x.get("reasked") for x in same.mention_conflicts)
    c2 = CASES["S-ACUTE-05"]
    top = run_case(c2, extractor=Echo(c2, opening={**extract(c2.opening_zh), "rest_symptom_first_time": True}, mentions=every({"rest_symptom_first_time": False})))
    assert top.reasks == [] and any(x["slot"] == "rest_symptom_first_time" and x["kind"] == "conflict" for x in top.mention_conflicts)
    assert top.final_slots["rest_symptom_first_time"] is True


def test_l1_direct_confirm_and_reask_at_most_one_extra():
    """同一欄位複誦與再問合計最多一次額外確認：直接問＋D-50 複誦之後，順口矛盾只記 conflict，不問第三次。"""
    c = CASES["S-MID-06"]

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            if q is None:
                return {"dyspnea_complaint": True}
            if q.id == "Q-DYSPNEA-GRADE-01":
                return {q.slot_id: "exertional_daily"}      # 直接問：非最嚴重 → D-50 複誦
            out = super().__call__(text, q, confirm_prompt)
            if confirm_prompt is None:
                out["dyspnea_grade"] = "exertional_heavy"   # 之後順口矛盾
            return out

    class P(ScriptedPatient):
        n = 0

        def confirm(self, q, prompt_zh):
            P.n += q.id == "Q-DYSPNEA-GRADE-01"
            return super().confirm(q, prompt_zh)

    r = run_case(c, patient=P(c), extractor=E(c))
    assert next(x for x in r.turns if x.question_id == "Q-DYSPNEA-GRADE-01").confirm_prompt_zh is not None
    assert P.n == 1 and r.reasks == []
    assert any(x["slot"] == "dyspnea_grade" and x["kind"] == "conflict" and not x.get("reasked") for x in r.mention_conflicts)


def test_e_d50_yes_no_unknown_reply_clears_unconfirmed_denial():
    """D-50 範圍內的否認，再問答不明 → 未經確認的紅旗否認不採信（resolve_confirm 既有行為），不是保留。"""
    q = QB["Q-REST-02"]
    from acs_triage.prompter.confirm import resolve_confirm
    assert resolve_confirm(q, False, None)[0] is None and resolve_confirm(q, True, None)[0] is True


def test_e_no_reask_when_already_hard_stop_or_same_sentence_hard_stops():
    c = CASES["S-MID-13#0"]
    opening = {"symptom_character": "epigastric", "onset_new": True}

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            if q is None:
                return dict(self.opening)
            if q.id == "Q-DIAPH-01":
                return {"diaphoresis": True, "onset_new": False}       # 這句有冒汗（Hard stop）又順口矛盾 → 不再問
            return {q.slot_id: ScriptedPatient(self.case).answer(q).value}

    r = run_case(c, extractor=E(c, opening=opening))
    assert r.final.hard_stop and r.reasks == []
    assert any(x["slot"] == "onset_new" and x["kind"] == "conflict" and not x.get("reasked") for x in r.mention_conflicts)


def test_e_slot_without_question_only_records_conflict():
    c = CASES["S-MID-06#2"]

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            out = super().__call__(text, q, confirm_prompt)
            if q is not None:
                out["dyspnea_complaint"] = False
            return out

    r = run_case(c, extractor=E(c, opening={"dyspnea_complaint": True}))
    assert r.reasks == [] and any(x["slot"] == "dyspnea_complaint" and x["kind"] == "conflict" for x in r.mention_conflicts)


def test_e_reask_prompt_wording():
    assert reask_prompt(QB["Q-NTG-01"]) == f"我再跟您確認一次，{QB['Q-NTG-01'].script_zh}請您回答『有』還是『沒有』。"
    assert reask_prompt(QB["Q-ONSET-01"]) == f"我再跟您確認一次，{QB['Q-ONSET-01'].script_zh}"    # 二選一問法不能答有／沒有
    assert reask_prompt(QB["Q-TIMING-01"]) == f"我再跟您確認一次，{QB['Q-TIMING-01'].script_zh}"
    for qid in ("Q-ORTHO-01", "Q-PALP-01", "Q-REPRO-01", "Q-THRESHOLD-01"):          # 一題兩個問句：答有／沒有會指向不明
        assert reask_prompt(QB[qid]) == f"我再跟您確認一次，{QB[qid].script_zh}", qid


# ---------------------------------------------------------------- 第四輪：H1、H2、R4、R13、R27、R29
def test_h1_reask_answer_unknown_keeps_original():
    """再問答「不記得」（unknown）也是不明 → 保留原值（今天新發不會因此套用 DV-2 豁免變 T2）。"""
    r, *_ = _conflict_run(known_slot="last_episode_timing", known="today", mention="over_24h", reply="unknown")
    assert r.reasks and r.reasks[0]["reply_value"] == "unknown" and r.reasks[0]["value"] == "today"
    assert r.final_slots["last_episode_timing"] == "today" and r.final.tier == 0
    r2, *_ = _conflict_run(known_slot="threshold_decrease_timescale", known="weeks_to_month", mention="days", reply="unknown",
                           case_id="S-MID-07")
    assert all(x["value"] == "weeks_to_month" for x in r2.reasks)


def test_h2_reask_reply_mentions_are_written():
    """再問回覆裡順口說「現在還在、冒冷汗」→ 照一般回答寫入 → Hard stop（只記 conflict，不再遞迴再問）。"""
    r, *_ = _conflict_run(reply=True, reply_mentions={"ongoing_now": True, "diaphoresis": True, "onset_weeks_ago": 5.0})
    assert r.final.hard_stop and {"RF-03", "RF-06"} & set(r.final.rf_hits) and len(r.reasks) == 1


def test_h2_d50_confirm_reply_mentions_are_written():
    c = CASES["S-ACUTE-01"]

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            if q is None:
                return {**extract(c.opening_zh), "onset_new": True}
            if q.id == "Q-DYSPNEA-GRADE-01":
                return {q.slot_id: "exertional_heavy", **({"ongoing_now": True} if confirm_prompt else {})}   # D-50 複誦回覆裡說「現在還在」
            return super().__call__(text, q, confirm_prompt)

    r = run_case(c, extractor=E(c))
    t = next(x for x in r.turns if x.question_id == "Q-DYSPNEA-GRADE-01")
    assert t.confirm_prompt_zh is not None and r.final.hard_stop and "RF-03" in r.final.rf_hits
    assert any(x.get("from_reply") for x in r.mention_conflicts) or r.final_slots["ongoing_now"] is True


def test_h2_mention_confirm_reply_mentions_are_written():
    """D-50 順口複誦（該題問過答不明，之後順口給較不嚴重的值）的回覆裡說「現在還在」→ 照一般回答寫入 → Hard stop。"""
    c = CASES["S-ACUTE-01"]
    seen = {"confirms": 0, "mentioned": False}

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            if q is None:
                return {**extract(c.opening_zh), "onset_new": True}
            if q.id == "Q-DYSPNEA-GRADE-01":
                if confirm_prompt is None:
                    return {q.slot_id: None}
                seen["confirms"] += 1
                return {q.slot_id: None} if seen["confirms"] == 1 else {q.slot_id: "exertional_heavy", "ongoing_now": True}
            out = super().__call__(text, q, confirm_prompt)
            if confirm_prompt is None and seen["confirms"] and not seen["mentioned"]:
                seen["mentioned"] = True
                out["dyspnea_grade"] = "exertional_heavy"    # 問過答不明，之後順口說「爬樓梯會喘」
            return out

    r = run_case(c, extractor=E(c))
    assert [x["stage"] for x in r.mention_confirms] == ["asked_unknown"]
    assert r.final.hard_stop and "RF-03" in r.final.rf_hits and r.final_slots["ongoing_now"] is True


class _ScriptE:
    """假抽取器：ment＝直接回答時同句順口值；reply／reply_ment＝再問或複誦回覆的值與順口值（依題目）。"""

    def __init__(self, case, opening, ment=None, reply=None, reply_ment=None):
        self.case, self.opening, self.ment, self.reply, self.reply_ment = case, opening, ment or {}, reply or {}, reply_ment or {}

    def __call__(self, text, q, confirm_prompt=None):
        if q is None:
            return dict(self.opening)
        if confirm_prompt is not None:
            v = self.reply[q.id] if q.id in self.reply else ScriptedPatient(self.case).answer(q).value
            return {q.slot_id: v, **self.reply_ment.get(q.id, {})}
        return {q.slot_id: ScriptedPatient(self.case).answer(q).value, **self.ment.get(q.id, {})}


def _n1_case():
    c = CASES["S-INSUF-01"]
    facts = dict(symptom_character="pressure", onset_new=False, ongoing_now=False, presyncope=False, diaphoresis=False, dyspnea_grade="none",
                 rest_symptom=False, threshold_decreased=False, ntg_use_increased=False, pattern_unchanged_duration_months=24, cad_history=True)
    return dataclasses.replace(c, slots=_complete({**c.slots, **facts}), persona="normal", reset_slots=[])


@pytest.mark.parametrize("qid, slot, rf", [("Q-ONGOING-01", "ongoing_now", "RF-03"), ("Q-SYNCOPE-01", "presyncope", "RF-01"),
                                           ("Q-DIAPH-01", "diaphoresis", "RF-06")])
def test_n1_reask_reply_red_flag_yes_overrides_same_turn_direct_no(qid, slot, rf):
    """N1：紅旗題直接答「沒有」、同句順口矛盾觸發再問，再問回覆說該紅旗「有」→ 回覆的順口值在直接回答寫入後才寫，紅旗「有」照規則覆蓋 → Hard stop。"""
    c = _n1_case()
    r = run_case(c, extractor=_ScriptE(c, {"symptom_character": "pressure", "onset_new": False}, ment={qid: {"onset_new": True}},
                                       reply={"Q-ONSET-01": False}, reply_ment={"Q-ONSET-01": {slot: True}}))
    assert r.final.hard_stop and rf in r.final.rf_hits and r.final_slots[slot] is True and len(r.reasks) == 1


def test_n1_counterexample_non_red_flag_reply_contradiction_only_recorded():
    """反例：非紅旗題直接答「沒有」、再問回覆順口說「有」→ 以直接回答為準，只記 conflict（from_reply），不再遞迴再問。"""
    c = _n1_case()
    r = run_case(c, extractor=_ScriptE(c, {"symptom_character": "pressure", "onset_new": False}, ment={"Q-THRESHOLD-01": {"onset_new": True}},
                                       reply={"Q-ONSET-01": False}, reply_ment={"Q-ONSET-01": {"threshold_decreased": True}}))
    assert r.final_slots["threshold_decreased"] is False and [x["slot"] for x in r.reasks] == ["onset_new"]
    assert any(x.get("from_reply") and x["slot"] == "threshold_decreased" for x in r.mention_conflicts)


class _SeqE:
    """腳本抽取器：script[(題目, "ask"|"confirm", 第 n 次)] = 抽取結果；沒列的照病人事實回答。"""

    def __init__(self, case, opening, script):
        self.case, self.opening, self.script, self.n = case, opening, script, {}

    def __call__(self, text, q, confirm_prompt=None):
        if q is None:
            return dict(self.opening)
        k = (q.id, "confirm" if confirm_prompt else "ask")
        self.n[k] = self.n.get(k, 0) + 1
        return dict(self.script.get((*k, self.n[k]), {q.slot_id: ScriptedPatient(self.case).answer(q).value}))


_N1_OPEN = {"symptom_character": "pressure", "onset_new": False}


@pytest.mark.parametrize("qid, slot, rf", [("Q-SYNCOPE-01", "presyncope", "RF-01"), ("Q-DIAPH-01", "diaphoresis", "RF-06")])
def test_v2_mention_confirm_reply_red_flag_yes_overrides_same_turn_direct_no(qid, slot, rf):
    """N1 的順口複誦路徑：Q-ONGOING-01 問過答不明；本題直接答「沒有」、同句順口說「現在沒在痛」→ 立刻複誦 Q-ONGOING-01，
    複誦回覆說本題的紅旗「有」→ 在直接回答寫入後才寫 → Hard stop。"""
    c = _n1_case()
    sc = {("Q-ONGOING-01", "ask", 1): {"ongoing_now": None}, ("Q-ONGOING-01", "confirm", 1): {"ongoing_now": None},
          (qid, "ask", 1): {slot: False, "ongoing_now": False}, ("Q-ONGOING-01", "confirm", 2): {"ongoing_now": False, slot: True}}
    r = run_case(c, extractor=_SeqE(c, _N1_OPEN, sc))
    assert [x["stage"] for x in r.mention_confirms] == ["asked_unknown"]
    assert r.final.hard_stop and rf in r.final.rf_hits and r.final_slots[slot] is True


def test_v4_every_reply_mention_in_the_turn_is_written():
    """同一句兩個矛盾 → 兩次再問；第二次再問的回覆才說紅旗「有」→ 同回合每個回覆的順口值都要寫（不是只寫第一個）。"""
    c = _n1_case()
    sc = {("Q-DIAPH-01", "ask", 1): {"diaphoresis": False, "onset_new": True, "cad_history": False},
          ("Q-ONSET-01", "confirm", 1): {"onset_new": False},
          ("Q-CAD-01", "confirm", 1): {"cad_history": True, "diaphoresis": True}}
    r = run_case(c, extractor=_SeqE(c, {**_N1_OPEN, "cad_history": True}, sc))
    assert [x["slot"] for x in r.reasks] == ["onset_new", "cad_history"]
    assert r.final.hard_stop and "RF-06" in r.final.rf_hits and r.final_slots["diaphoresis"] is True


def test_v16_mention_confirm_reply_below_threshold_is_unheard():
    """順口複誦的回覆信心低於該題門檻 → 視為不明：紅旗否認未經確認不採信（留未知），不採用回覆值。"""
    c = _n1_case()

    class P(ScriptedPatient):
        def __init__(self, case):
            super().__init__(case)
            self.k = 0

        def confirm(self, q, prompt_zh):
            r = super().confirm(q, prompt_zh)
            if q.id == "Q-ONGOING-01":
                self.k += 1
                if self.k == 2:
                    return dataclasses.replace(r, stt_confidence=0.8)     # 介於一般 0.75 與紅旗 0.9 門檻之間
            return r
    sc = {("Q-ONGOING-01", "ask", 1): {"ongoing_now": None}, ("Q-ONGOING-01", "confirm", 1): {"ongoing_now": None},
          ("Q-SYNCOPE-01", "ask", 1): {"presyncope": False, "ongoing_now": False}, ("Q-ONGOING-01", "confirm", 2): {"ongoing_now": False}}
    r = run_case(c, patient=P(c), extractor=_SeqE(c, _N1_OPEN, sc))
    mc = r.mention_confirms
    assert [x["stage"] for x in mc] == ["asked_unknown"] and mc[0]["reply_value"] is False and mc[0]["value"] is None


def test_n35_stash_keeps_more_severe_mention():
    """D-50 欄位還沒問到前順口提了兩次（先較嚴重、後較輕）→ 暫存留較嚴重者，問到答不明時以它複誦。"""
    c = CASES["S-INSUF-01"]
    said = []

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            if q is not None and q.id == "Q-DYSPNEA-GRADE-01":
                return {q.slot_id: None}
            out = super().__call__(text, q, confirm_prompt)
            if q is not None and confirm_prompt is None and len(said) < 2:
                out["dyspnea_grade"] = ("exertional_daily", "exertional_heavy")[len(said)]
                said.append(q.id)
            return out

    r = run_case(c, extractor=E(c, opening={"symptom_character": "vague", "cad_history": True}))
    st = [x for x in r.mention_confirms if x["stage"] == "stashed_then_asked_unknown"]
    qs = _qs(r)
    assert len(said) == 2 and all(qs.index(x) < qs.index("Q-DYSPNEA-GRADE-01") for x in said)
    assert st and st[0]["mention"] == "exertional_daily"


def test_n49_reask_reply_at_exact_threshold_is_heard():
    thr = load_clinical_rules()["thresholds"]["stt_min_confidence"]
    r, *_ = _conflict_run(reply=False, reply_conf=thr)
    assert r.reasks and r.reasks[0]["value"] is False


def test_n50_reask_of_d50_slot_uses_critical_threshold():
    """D-50 範圍的欄位再問，回覆信心介於一般與關鍵門檻之間 → 視為不明（保留原值），不採用。"""
    th = load_clinical_rules()["thresholds"]
    conf = (th["stt_min_confidence"] + th["stt_min_confidence_critical"]) / 2
    r, *_ = _conflict_run(known_slot="dyspnea_grade", known="exertional_daily", mention="exertional_heavy", reply="rest", reply_conf=conf)
    assert r.reasks and r.reasks[0]["question_id"] == "Q-DYSPNEA-GRADE-01" and r.reasks[0]["value"] == "exertional_daily"


def test_r13_reask_reply_goes_through_traditional_conversion():
    r, _, ex, q = _conflict_run(reply=False, tw=lambda s: s + "〔繁〕")
    assert r.reasks and all(x.endswith("〔繁〕") for x in ex.texts)            # 開場白、回答、再問回覆都先轉繁（D-49）


def test_r4_no_reask_when_confirm_back_switched_off():
    r, *_ = _conflict_run(reply=False, confirm_back=False)
    assert r.reasks == [] and any(x["kind"] == "conflict" for x in r.mention_conflicts)


def test_r29_slot_asked_directly_then_contradicted_is_reasked():
    """#16 的主情境：已直接問過、答案非 D-50 範圍，之後順口矛盾 → 再問一次。"""
    c = CASES["S-MID-01#1"]
    order = []

    class E(Echo):
        def __call__(self, text, q, confirm_prompt=None):
            out = super().__call__(text, q, confirm_prompt)
            if q is not None:
                order.append((q.id, bool(confirm_prompt)))
            if q is not None and not confirm_prompt and q.id != "Q-ONSET-01" and ("Q-ONSET-01", False) in order[:-1]:
                out["onset_new"] = False                    # 剛直接答過「第一次」，下一句又說「以前就有」
            return out

    op = {k: v for k, v in extract(c.opening_zh).items() if k != "onset_new"}
    r = run_case(c, extractor=E(c, opening=op))
    direct = [x for x in order if not x[1]]
    assert ("Q-ONSET-01", False) in direct and len(direct) > direct.index(("Q-ONSET-01", False)) + 1
    assert [x["question_id"] for x in r.reasks] == ["Q-ONSET-01"] and ("Q-ONSET-01", True) in order


def test_r27_urgency_uses_t9_fallback():
    from sim.runner import _urgency
    assert _urgency(SlotState({"symptom_character": "vague"})) == 1                 # T9 → 護理師不可得時的預設等級
    assert _urgency(SlotState({"third_party_call": True, "patient_reachable": False})) == 1
    assert _urgency(SlotState({"symptom_character": "pressure", "ongoing_now": True})) == -1


# ---------------------------------------------------------------- 第四輪：H3 呼吸 T0 因子必問（Clinical Owner 2026-11-03）
def test_h3_gate_requires_dyspnea_t0_factors_when_dyspnea_present(engine):
    base = {"symptom_character": "epigastric", "postprandial_relieved": True, "ongoing_now": False, "exertion_relation": "rest_only",
            "diaphoresis": False, "presyncope": False, "rest_symptom": False, "threshold_decreased": False, "ntg_use_increased": False,
            "episode_frequency_increased": False}
    assert decide_slots(engine, base).tier == 3
    with_dysp = {**base, "dyspnea_grade": "exertional_daily", "cant_finish_sentence": False}
    d = decide_slots(engine, with_dysp)
    assert d.provisional_tier == 3 and d.tier == 9 and {"orthopnea_pnd", "dyspnea_acute"} <= set(d.missing)
    assert decide_slots(engine, {**with_dysp, "orthopnea_pnd": False, "dyspnea_acute": False}).tier == 3
    assert decide_slots(engine, {**with_dysp, "dyspnea_acute": True}).tier == 0
    assert not {"orthopnea_pnd", "dyspnea_acute"} & set(decide_slots(engine, {**base, "dyspnea_grade": "none"}).missing)   # 否認喘：由 D-25 衍生


@pytest.mark.parametrize("opening", [{"symptom_character": "vague"}, {"chest_discomfort_mentioned": True}, {"symptom_character": "pressure"}],
                         ids=["vague", "flag", "pressure"])
def test_h3_chest_plus_dyspnea_asks_dyspnea_t0_factors_first(opening):
    c = CASES["S-INSUF-01"]
    case = dataclasses.replace(c, slots=_complete({**c.slots, "symptom_character": "pressure", "dyspnea_grade": "exertional_daily",
                                                   "cant_finish_sentence": False, "orthopnea_pnd": True}), persona="normal", reset_slots=[])
    r = run_case(case, extractor=Echo(case, opening={**opening, "cad_history": True}))
    qs = _qs(r)
    assert r.final.tier == 0 and "T0-ORTHOPNEA" in r.final.evidence and not r.final.hard_stop
    assert qs.index("Q-DYSPNEA-ACUTE-01") < qs.index("Q-ORTHO-01") and not {"Q-ONSET-01", "Q-THRESHOLD-01"} & set(qs)


@pytest.mark.parametrize("t0, ev", [("orthopnea_pnd", "T0-ORTHOPNEA"), ("dyspnea_acute", "T0-DYSPNEA-ACUTE")])
def test_h3_vague_answered_vague_again_still_asks_dyspnea_t0_factors_first(t0, ev):
    """性質再問仍答 vague（暫定 T9，gate 不強制呼吸題）：呼吸的 T0 因子題仍排在決定題之前，不被上限擠掉。"""
    c = CASES["S-INSUF-01"]
    case = dataclasses.replace(c, slots=_complete({**c.slots, "symptom_character": "vague", "dyspnea_grade": "exertional_daily",
                                                   "cant_finish_sentence": False, t0: True}), persona="normal", reset_slots=[])
    r = run_case(case, extractor=Echo(case, opening={"symptom_character": "vague"}))
    assert r.final.tier == 0 and ev in r.final.evidence and "Q-ONSET-01" not in _qs(r)


def _next_q(slots, extra_asked=(), not_asked=()):
    s = SlotState(slots)
    d = RulesEngine().decide(s)
    asked = ({q.id for q in QB.values() if q.slot_id in slots and slots[q.slot_id] is not None} | set(extra_asked)) - set(not_asked)
    return Prompter().next_question(s, missing=d.missing, asked=asked).id


_E3 = {"symptom_character": "vague", "dyspnea_grade": "exertional_daily", "cant_finish_sentence": False, "ongoing_now": False,
       "presyncope": False, "diaphoresis": False, "dyspnea_acute": False, "orthopnea_pnd": False, "onset_new": True}


def test_exertion_first_rule_conditions():
    """活動題提前（Clinical Owner 2026-11-03 裁定保留）只在 vague＋呼吸症狀＋新發已確定＋活動未知時。"""
    assert _next_q(_E3) == "Q-EXERTION-01"
    assert _next_q({**_E3, "onset_new": None}, ["Q-ONSET-01"]) != "Q-EXERTION-01"            # 新發不明
    assert _next_q({**_E3, "dyspnea_grade": "none"}) != "Q-EXERTION-01"                      # 沒有呼吸症狀
    assert _next_q({**_E3, "exertion_relation": "both"}, not_asked=["Q-EXERTION-01"]) != "Q-EXERTION-01"   # 活動關係已知（開場白說的）
    flag = {**{k: v for k, v in _E3.items() if k != "symptom_character"}, "chest_discomfort_mentioned": True, "last_episode_timing": "over_24h"}
    assert _next_q(flag, ["Q-CHARACTER-01"]) != "Q-EXERTION-01"                               # 性質未知（只提過胸口）


def test_v6_order_d_chest_t0_factors_only_when_onset_known_not_new():
    """順序 D：新發問了仍不明 → 不提前胸部 T0 因子（只有確定不是新發才提前）。"""
    assert _next_q({**_E3, "onset_new": None}, ["Q-ONSET-01"]) != "Q-REST-01"
    flag = {**{k: v for k, v in _E3.items() if k != "symptom_character"}, "chest_discomfort_mentioned": True, "onset_new": None}
    assert _next_q(flag, ["Q-ONSET-01", "Q-CHARACTER-01"]) != "Q-REST-01"
    assert _next_q({**_E3, "onset_new": False}) == "Q-REST-01"                                 # 對照：確定不是新發才提前


def test_v15_exertion_first_rule_not_when_onset_false():
    """活動題提前只在新發為「是」：不是新發（4 個胸部 T0 因子已問完）不提前。"""
    f4 = {"rest_symptom": False, "ntg_use_increased": False, "threshold_decreased": False, "episode_frequency_increased": False}
    assert _next_q({**_E3, "onset_new": False, **f4}) != "Q-EXERTION-01"


def test_order_d_does_not_reask_known_slots():
    """順序 D：H3 兩題、新發、4 個胸部 T0 因子都只問未知的。"""
    s = {**_E3, "onset_new": False, "rest_symptom": False}
    asked = [q.id for q in QB.values() if q.slot_id in ("dyspnea_grade", "cant_finish_sentence", "ongoing_now", "presyncope", "diaphoresis")]
    st = SlotState(s)
    d = RulesEngine().decide(st)
    assert Prompter().next_question(st, missing=d.missing, asked=set(asked)).id == "Q-NTG-01"


def test_order_d_onset_then_chest_t0_factors_when_not_new():
    """順序 D（Clinical Owner 2026-11-03）：vague 或性質未知＋呼吸症狀 → H3 兩題後先問新發；不是新發 → 4 個胸部 T0 因子接著問，性質題延後。"""
    c = CASES["S-INSUF-01"]
    case = dataclasses.replace(c, slots=_complete({**c.slots, "symptom_character": "vague", "dyspnea_grade": "exertional_daily", "cant_finish_sentence": False,
                                                   "onset_new": False, "pattern_unchanged_duration_months": 24}), persona="normal", reset_slots=[])
    for op in ({"symptom_character": "vague"}, {"chest_discomfort_mentioned": True}):
        qs = _qs(run_case(case, extractor=Echo(case, opening=op)))
        i = qs.index("Q-ONSET-01")
        f4 = ["Q-REST-01", "Q-NTG-01", "Q-THRESHOLD-01", "Q-FREQ-01"][:12 - i - 1]      # 只提過胸口者先問性質題，第 4 題撞上限
        assert qs.index("Q-ORTHO-01") < i and qs[i + 1:i + 5] == f4 and len(qs) <= 12, (op, qs)


def test_order_d_applies_when_character_still_unknown():
    """只提過胸口、性質問了仍不明（None）也照順序 D：H3 兩題、新發，不是新發 → 胸部 T0 因子。"""
    c = CASES["S-INSUF-01"]
    case = dataclasses.replace(c, slots=_complete({**c.slots, "symptom_character": "pressure", "dyspnea_grade": "exertional_daily", "cant_finish_sentence": False,
                                                   "onset_new": False, "pattern_unchanged_duration_months": 24}), persona="normal", reset_slots=[])
    r = run_case(case, extractor=Echo(case, opening={"chest_discomfort_mentioned": True}, override={"Q-CHARACTER-01": None}))
    qs = _qs(r)
    i = qs.index("Q-ONSET-01")
    assert r.final_state.get("symptom_character") is None and qs.index("Q-ORTHO-01") < i and qs[i + 1] == "Q-REST-01", qs


def test_n39_freq_mirrors_ntg_without_chest_prerequisite():
    from acs_triage.rules.tiers import t0_rules
    for extra in ({"symptom_character": "pressure"}, {"symptom_character": "none", "dyspnea_grade": "exertional_daily"}):
        assert ("T0-NTG-INCREASED" in t0_rules(SlotState({**extra, "ntg_use_increased": True}))) == \
               ("T0-FREQ-INCREASED" in t0_rules(SlotState({**extra, "episode_frequency_increased": True})))


def test_h3_s_mid_13_epigastric_with_acute_dyspnea_is_t0():
    c = CASES["S-MID-13"]
    case = dataclasses.replace(c, slots=_complete({**c.slots, "dyspnea_grade": "exertional_daily", "cant_finish_sentence": False, "dyspnea_acute": True}),
                               reset_slots=[])
    for op in ({"cad_history": True, "chest_discomfort_mentioned": True, "postprandial_relieved": True, "ongoing_now": False},
               {"cad_history": True, "symptom_character": "epigastric", "postprandial_relieved": True, "ongoing_now": False}):
        r = run_case(case, extractor=Echo(case, opening=op))
        assert r.final.tier == 0 and "T0-DYSPNEA-ACUTE" in r.final.evidence


def test_p3_vague_opening_chest_red_flags_before_dyspnea_grade():
    case = _vague_case(diaphoresis=True)
    r = run_case(case, extractor=Echo(case, opening={"symptom_character": "vague", "cad_history": True}))
    assert r.final.hard_stop and "RF-06" in r.final.rf_hits and "Q-DYSPNEA-GRADE-01" not in _qs(r)


def test_e_reports_can_count_reasks_and_downgrades():
    r, *_ = _conflict_run(reply=False)
    m = compute([r])
    assert m.reasks == 1 and m.reask_downgrades == 1 and m.to_dict()["mention_reask"] == {"n": 1, "downgrades": 1}
    assert "不重跑對話，路徑分岔造成的差異記不到" in render_md("clean", 0, [r], m)
    c = CASES["S-ACUTE-01"]
    assert dev_metrics([{"case": c, "result": r, "error": None}])["reask_downgrades"] == 1


def test_closed_loop_report_has_reask_row_only_when_available(tmp_path, monkeypatch):
    import json
    import shutil
    import sys

    from acs_triage.loaders import REPO_ROOT
    from sim import extractor_v2_report as rep
    inp = tmp_path / "inputs"
    shutil.copytree(REPO_ROOT / "reports" / "extractor_v2_2026-10-27_inputs", inp)
    f = inp / "closed_dev_gpt.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["metrics"].update(reasks=3, reask_downgrades=1)
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["sim.extractor_v2_report", "--inputs", str(inp), "--out", str(tmp_path)])
    rep.main()
    md = next(tmp_path.glob("extractor_v2_*.md")).read_text(encoding="utf-8")
    assert "順口值矛盾再問 3 次；因再問而最終較不急 1 次" in md and md.count("順口值矛盾再問") == 1    # 舊紀錄沒有這個欄位 → 不印
    assert "不重跑對話，路徑分岔造成的差異記不到" in md


def test_m4_frozen_files_cover_rules_flow_patient_and_scoring():
    must = {"data/clinical_rules.yaml", "data/question_bank_seed.yaml", "data/extraction_patterns.yaml", "data/scripts_zh.yaml", "sim/cases.py", "sim/patient.py",
            "src/acs_triage/rules/tiers.py", "src/acs_triage/rules/state.py", "src/acs_triage/rules/sufficiency.py", "src/acs_triage/rules/redflags.py",
            "src/acs_triage/prompter/prompter.py", "src/acs_triage/prompter/confirm.py", "src/acs_triage/extract/rule_extractor.py",
            "src/acs_triage/pathway/router.py", "src/acs_triage/loaders.py", "src/acs_triage/schemas.py", "sim/synth_eval.py", "sim/synth_gen.py", "sim/metrics.py",
            "data/synth/scenarios_synth_v1.yaml", "data/synth/reference_synth_v1.json", "data/synth/synth_prompts.yaml"}
    assert must <= set(cl.FROZEN_FILES)
    assert set(cl.file_hashes()) == set(cl.FROZEN_FILES)


def _freeze_env(tmp_path, monkeypatch):
    monkeypatch.setattr(cl, "FREEZE_PATH", tmp_path / "freeze.json")
    monkeypatch.setattr(cl, "HOLDOUT_REGISTRY", tmp_path / "runs.json")
    monkeypatch.setattr(cl, "load_set", lambda name: (_ for _ in ()).throw(RuntimeError("reached load_set")))


def test_m5_stale_transcripts_refused_before_holdout_registered(tmp_path, monkeypatch):
    _freeze_env(tmp_path, monkeypatch)
    # 舊稿明確做出來（bank 版本不符），不依賴 repo 目前指向的逐字稿新舊
    trh, _ = _dev_report(tmp_path, name="eval_old_h", bank_version="0.4", scenario_sha256=cl.scenario_hashes([cl.HOLDOUT_SCENARIOS]),
                         case_ids_in_set=list(CASES))
    trd, _ = _dev_report(tmp_path, name="eval_old_d", bank_version="0.4")
    monkeypatch.setattr(cl, "HOLDOUT_STRUCTURED", trh)
    monkeypatch.setattr(cl, "DEV_STRUCTURED", trd)
    cl.freeze_main([])
    args = ["--set", "holdout", "--arm", "structured", "--cache-dir", str(tmp_path / "c"), "--out", str(tmp_path / "o")]
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.run_main(args)
    assert not cl.HOLDOUT_REGISTRY.exists()                     # 舊逐字稿不會把一次性的 arm 用掉
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.run_main(["--set", "dev", "--arm", "structured", "--cache-dir", str(tmp_path / "c"), "--out", str(tmp_path / "o2")])


def _dev_report(tmp_path, name="eval_x", ids=None, **over):
    from sim.closed_loop import DEV_SCENARIO_FILES
    meta = {"model": "claude-opus-5-5", "effort": "medium", "errors": [],
            **transcript_meta(DEV_SCENARIO_FILES, list(CASES.values()), None), **over}
    tr = tmp_path / f"{name}_transcripts.json"
    tr.write_text(json.dumps([{"case_id": i} for i in (ids if ids is not None else CASES)]), encoding="utf-8")
    (tmp_path / f"{name}.json").write_text(json.dumps(meta), encoding="utf-8")
    return tr, meta


def test_m5_version_check_compares_versions_and_file_hashes(tmp_path):
    tr, meta = _dev_report(tmp_path)
    assert meta["rules_version"] == rules_version() and meta["bank_version"] == bank_version() and set(meta["file_sha256"]) == set(cl.FROZEN_FILES)
    cl.check_structured_version(tr, "dev")                                          # 現行版本、完整、規定設定 → 通過
    for over in ({"file_sha256": {**meta["file_sha256"], "src/acs_triage/prompter/prompter.py": "0" * 64}},   # 同版改 Prompter → 舊稿
                 {"bank_version": "0.4"}, {"file_sha256": {}}):
        tr2, _ = _dev_report(tmp_path, **over)
        with pytest.raises(SystemExit, match="逐字稿版本"):
            cl.check_structured_version(tr2, "dev")
    for f in ("sim/closed_loop.py", "data/extractor_prompts_v2.yaml", "sim/llm_extract_v2.py"):      # 不影響問句序列與病人回答
        tr3, _ = _dev_report(tmp_path, file_sha256={**meta["file_sha256"], f: "0" * 64})
        cl.check_structured_version(tr3, "dev")
    (tmp_path / "eval_x.json").unlink()
    with pytest.raises(SystemExit, match="逐字稿版本"):                             # 沒有報告 → 拒跑
        cl.check_structured_version(tr, "dev")


@pytest.mark.parametrize("over", [{"model": "claude-haiku-5-5"}, {"effort": "low"}, {"errors": [["S-ACUTE-01", "timeout"]]}, {"limit": 3},
                                  {"scenario_sha256": {}}, {"case_ids_in_set": []}])
def test_m1_transcript_must_be_full_official_run(tmp_path, over):
    tr, _ = _dev_report(tmp_path, **over)
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.check_structured_version(tr, "dev" if "case_ids_in_set" not in over else "holdout")


def test_m1_transcript_case_ids_must_cover_the_set(tmp_path):
    ids = list(CASES)
    for bad in (ids[:-1], ids + ids[:1], ids[:-1] + ["X-1"]):
        tr, _ = _dev_report(tmp_path, ids=bad)
        with pytest.raises(SystemExit, match="逐字稿版本"):
            cl.check_structured_version(tr, "dev")
    tr, _ = _dev_report(tmp_path, name="eval_x_limit3")
    with pytest.raises(SystemExit, match="逐字稿版本"):                             # 檔名是 --limit 跑的
        cl.check_structured_version(tr, "dev")


def test_m1_holdout_limit3_refused_before_registration(tmp_path, monkeypatch):
    """HOLDOUT_STRUCTURED 指到 _limit3 這類檔案 → 登記前拒跑，不會用掉一次性的 arm。"""
    tr, _ = _dev_report(tmp_path, name="eval_y_limit3")
    _freeze_env(tmp_path, monkeypatch)
    monkeypatch.setattr(cl, "HOLDOUT_STRUCTURED", tr)
    cl.freeze_main([])
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.run_main(["--set", "holdout", "--arm", "structured", "--cache-dir", str(tmp_path / "c"), "--out", str(tmp_path / "o")])
    assert not cl.HOLDOUT_REGISTRY.exists()


def test_m1_synth_listing_skips_hidden_files_and_subdirs_and_deleted_files_refused(tmp_path, monkeypatch):
    from acs_triage.loaders import REPO_ROOT
    folder = REPO_ROOT / "sim"                               # 用不是保留集的目錄測列檔規則
    listed = cl._synth_files(folder)
    assert listed and all(not Path(f).name.startswith(".") for f in listed) and all((REPO_ROOT / f).is_file() for f in listed)
    assert "sim/__pycache__" not in listed
    fake = tmp_path / "d"
    fake.mkdir()
    (fake / ".DS_Store").write_text("x")
    (fake / "sub").mkdir()
    (fake / "a.yaml").write_text("x")
    monkeypatch.setattr(cl, "REPO_ROOT", tmp_path)
    assert cl._synth_files(fake) == ["d/a.yaml"]
    monkeypatch.setattr(cl, "REPO_ROOT", REPO_ROOT)
    _freeze_env(tmp_path, monkeypatch)
    cl.freeze_main([])
    rec = json.loads(cl.FREEZE_PATH.read_text(encoding="utf-8"))
    rec["files"]["data/synth/deleted_later.yaml"] = "0" * 64       # 凍結時有、現在沒有
    cl.FREEZE_PATH.write_text(json.dumps(rec), encoding="utf-8")
    with pytest.raises(SystemExit, match="改動"):
        cl.check_holdout_allowed("gpt", None, tmp_path / "o")


def test_l9_l10_closed_loop_json_keeps_reasks():
    r, *_ = _conflict_run(reply=False)
    c = CASES["S-ACUTE-01"]
    from types import SimpleNamespace
    p = SimpleNamespace(n_live=0, n_cached=0, sources={}, cost=0.0, deviations=[])
    rec = cl.case_record({"case": c, "result": r, "patient": p, "error": None, "wall_s": 0.0})
    assert rec["reasks"] == r.reasks and rec["reask_downgrades"] == r.reask_downgrades
    assert cl.all_reasks([{"result": r}, {"result": None}]) == r.reasks
    rows = cl.holdout_rows([{"case": c, "result": r}])
    assert rows[c.id]["reasks"] == 1 and rows[c.id]["reask_downgrades"] == 1


def test_l9_closed_loop_report_json_keeps_reasks(tmp_path, monkeypatch):
    """L9：run_main 實際寫出的閉環 JSON 帶 reasks 明細與彙總（假病人、假快取，不打 API）。"""
    from collections import Counter
    from types import SimpleNamespace
    r, *_ = _conflict_run(reply=False)
    c = CASES["S-ACUTE-01"]
    p = SimpleNamespace(n_live=0, n_cached=0, sources=Counter(), cost=0.0, deviations=[])

    class Cache:
        def __init__(self, *a): pass
        def load(self, path): pass
        def seed(self, structured, source): return 0
        def save(self, path): pass
    tr = tmp_path / "dev_transcripts.json"
    tr.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(cl, "DEV_STRUCTURED", tr)
    monkeypatch.setattr(cl, "check_structured_version", lambda *a: None)
    monkeypatch.setattr(cl, "PatientCache", Cache)
    monkeypatch.setattr(cl, "load_set", lambda name: ([c], [{"case_id": c.id, "final": "T0"}]))
    monkeypatch.setattr(cl, "run_arm", lambda cases, **kw: [{"case": c, "result": r, "patient": p, "error": None, "wall_s": 0.0}])
    cl.run_main(["--set", "dev", "--arm", "structured", "--cache-dir", str(tmp_path / "c"), "--out", str(tmp_path / "o")])
    rep = json.loads((tmp_path / "o" / "closed_dev_structured.json").read_text(encoding="utf-8"))
    assert [x["slot"] for x in rep["reasks"]] == [x["slot"] for x in r.reasks] == ["onset_new"]
    assert rep["cases"][0]["reasks"] and rep["cases"][0]["reask_downgrades"]


def test_l10_holdout_metrics_count_reasks(tmp_path, monkeypatch):
    """L10：保留集彙總（與 sim.synth_eval 同一套）也數再問與再問後較不急（假參考標註，不讀保留集）。"""
    r, *_ = _conflict_run(reply=False)
    c = CASES["S-ACUTE-01"]
    lab = {"tier": "T1", "hard_stop": False, "rf_ids": [], "confidence": "high", "rationale_zh": ""}
    ref = tmp_path / "ref.json"
    ref.write_text(json.dumps({"cases": [{"case_id": c.id, "labels": {"opus": lab, "gpt": lab}}]}), encoding="utf-8")
    monkeypatch.setattr(cl, "HOLDOUT_REFERENCE", ref)
    m = cl.holdout_metrics(cl.holdout_rows([{"case": c, "result": r}]), [c])
    assert m["ref_agree"]["reasks"] == m["ref_cons"]["reasks"] == 1 and m["ref_agree"]["reask_downgrades"] == 1


def test_m1_holdout_transcript_checked_against_holdout_scenario_hash(tmp_path):
    """保留集逐字稿比保留集情境檔 hash（只算 hash，不讀內容）；開發集的 hash 不算數，反之亦然。"""
    hold = cl.scenario_hashes([cl.HOLDOUT_SCENARIOS])
    tr, _ = _dev_report(tmp_path, name="eval_h", scenario_sha256=hold, case_ids_in_set=list(CASES))
    cl.check_structured_version(tr, "holdout")
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.check_structured_version(tr, "dev")
    tr2, _ = _dev_report(tmp_path, name="eval_d", case_ids_in_set=list(CASES))
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.check_structured_version(tr2, "holdout")


def test_m1_scenario_hash_keys_repo_relative_and_outside_repo_absolute(tmp_path):
    assert cl.scenario_hashes(cl.DEV_SCENARIO_FILES) and all(k.startswith("data/") for k in cl.scenario_hashes(cl.DEV_SCENARIO_FILES))
    f = tmp_path / "x.yaml"
    f.write_text("a", encoding="utf-8")
    assert list(cl.scenario_hashes([f])) == [f.resolve().as_posix()]


def test_n29_n30_run_llm_eval_scenarios_meta_has_own_hash_and_all_case_ids(tmp_path, monkeypatch):
    """--scenarios 的報告要寫那份情境檔的 hash 與完整 case id（寫成開發集 hash 或截斷 → 保留集閉環永遠拒跑，或得重付保留集 eval）。"""
    import sys
    from test_synth import CASES as SYN, _multi_case_client, _write_synth
    from sim import run_llm_eval, synth_gen as sg
    path = _write_synth(tmp_path, [*SYN, {**SYN[1], "id": "SYN-T04", "opening_zh": "請問下個月的回診可以改時間嗎？"}])
    cases = sg.load_synth_cases(path)
    monkeypatch.setenv(run_llm_eval.KEY_ENV, "fake")
    monkeypatch.setattr(run_llm_eval, "make_client", lambda: _multi_case_client(cases))
    monkeypatch.setattr(sys, "argv", ["run_llm_eval", "--scenarios", str(path), "--out", str(tmp_path / "r"), "--workers", "1"])
    run_llm_eval.main()
    rep = json.loads(next(p for p in (tmp_path / "r").glob("*.json") if not p.name.endswith("_transcripts.json")).read_text(encoding="utf-8"))
    assert rep["scenario_sha256"] == cl.scenario_hashes([path]) != cl.scenario_hashes(cl.DEV_SCENARIO_FILES)
    assert rep["case_ids_in_set"] == ["SYN-T01", "SYN-T02", "SYN-T03", "SYN-T04"]


@pytest.mark.parametrize("set_name", ["dev", "holdout"])
def test_n31_closed_loop_checks_transcript_against_its_own_set(tmp_path, monkeypatch, set_name):
    calls = []

    def rec(*a):
        calls.append(a)
        raise SystemExit("stop")
    for name in ("DEV_STRUCTURED", "HOLDOUT_SCENARIOS", "HOLDOUT_STRUCTURED", "HOLDOUT_REFERENCE"):
        f = tmp_path / f"{name}.json"
        f.write_text("[]", encoding="utf-8")
        monkeypatch.setattr(cl, name, f)
    monkeypatch.setattr(cl, "check_holdout_allowed", lambda *a: {})
    monkeypatch.setattr(cl, "check_structured_version", rec)
    with pytest.raises(SystemExit, match="stop"):
        cl.run_main(["--set", set_name, "--arm", "structured", "--cache-dir", str(tmp_path / "c"), "--out", str(tmp_path / "o")])
    assert calls == [(tmp_path / ("DEV_STRUCTURED.json" if set_name == "dev" else "HOLDOUT_STRUCTURED.json"), set_name)]
    assert not (tmp_path / "o" / "closed_holdout_structured.json").exists()


def test_n15_n16_n21_transcript_check_gaps(tmp_path):
    """逐字稿檢查：報告多出現行已刪的檔、報告沒有 errors 欄、保留集逐字稿與 case_ids_in_set 不一致 → 都拒跑。"""
    tr, meta = _dev_report(tmp_path, name="eval_del", file_sha256={**cl.file_hashes(), "data/removed_file.yaml": "0" * 64})
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.check_structured_version(tr, "dev")
    tr, meta = _dev_report(tmp_path, name="eval_noerr")
    rep = tr.with_name("eval_noerr.json")
    rep.write_text(json.dumps({k: v for k, v in meta.items() if k != "errors"}), encoding="utf-8")
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.check_structured_version(tr, "dev")
    hold = cl.scenario_hashes([cl.HOLDOUT_SCENARIOS])
    tr, _ = _dev_report(tmp_path, name="eval_hx", scenario_sha256=hold, case_ids_in_set=[*CASES, "SYN-EXTRA"])
    with pytest.raises(SystemExit, match="逐字稿版本"):
        cl.check_structured_version(tr, "holdout")


def test_n32_opening_chest_flag_false_with_negated_evidence_not_written():
    """旗標只表示「有提到」：開場白抽成 false（證據「胸口沒事」）也不寫，否則之後順口說胸口不舒服會變成 conflict、不算胸部症狀。"""
    obj = {"evidence": [{"slot": "chest_discomfort_mentioned", "quote": "胸口沒事"}], **{k: None for k in mention_slots()}, "unclassified": []}
    obj["chest_discomfort_mentioned"] = False
    assert "chest_discomfort_mentioned" not in parse(obj, "胸口沒事，想問門診。", None)[0]


def test_l6_parse_drops_flag_false():
    obj = {"evidence": [], **{k: None for k in mention_slots()}, "unclassified": []}
    obj["chest_discomfort_mentioned"] = False
    assert "chest_discomfort_mentioned" not in parse(obj, "想問門診。", None)[0]


def test_e_scripted_path_has_no_reask():
    results, m = run_all("clean", seed=0)
    assert m.reasks == 0 and m.reask_downgrades == 0


# ---------------------------------------------------------------- 裁定的具體情境（結構化值代替抽取結果）
def test_ruling_10_orthopnea_with_rest_symptom_is_t0_not_hard_stop():
    c = CASES["S-MID-11"]
    r = run_case(c, extractor=Echo(c, opening={"cad_history": True, "orthopnea_pnd": True, "rest_symptom": True}))
    assert r.final.tier == 0 and not r.final.hard_stop and "T0-ORTHOPNEA" in r.final.evidence
    assert r.opening_extracted.get("dyspnea_grade") is None and "Q-DYSPNEA-GRADE-01" in _qs(r)   # 分級由題目問，不推定 rest


def test_ruling_14_rest_symptom_mention_gives_t0_accepted_by_owner():
    c = CASES["S-MID-13"]
    ex = Echo(c, opening={"cad_history": True, "chest_discomfort_mentioned": True, "postprandial_relieved": True, "ongoing_now": False},
              mentions={"Q-EXERTION-01": {"rest_symptom": True}})
    r = run_case(c, extractor=ex)
    assert r.final.tier == 0 and "T0-REST-NEW" in r.final.evidence and not r.final.hard_stop


def test_ruling_8_mechanical_pain_keeps_asking_red_flags():
    c = CASES["S-MID-14"]
    r = run_case(c, extractor=Echo(c, opening={"cad_history": True, "symptom_character": "pain", "reproducible_mechanical": True}))
    assert CHEST_RF - {"Q-ONGOING-01"} <= set(_qs(r)) | {"Q-ONGOING-01"} and "Q-DIAPH-01" in _qs(r)      # 不推定其他紅旗否認
    assert r.final.tier == 3 and "T3-MECHANICAL" in r.final.evidence


def test_ruling_12_exertional_heavy_is_confirmed_and_not_a_denial():
    c = CASES["S-STABLE-02#0"]
    ex = Echo(c, opening=extract(c.opening_zh), override={"Q-DYSPNEA-GRADE-01": "exertional_heavy"})
    r = run_case(c, extractor=ex)
    t = next(t for t in r.turns if t.question_id == "Q-DYSPNEA-GRADE-01")
    assert r.final_slots["dyspnea_grade"] == "exertional_heavy" and t.confirm_prompt_zh is not None


# ---------------------------------------------------------------- 抽取器提示
def test_prompt_examples_follow_rulings():
    ans, op = system_prompt(False), system_prompt(True)
    assert "「我其實不太會喘」→ answered、exertional_heavy" in ans and "「我不會喘」「喘的話倒是沒有」→ answered、none" in ans
    assert "「我其實不太會喘」「喘的話倒是沒有」→ answered、none" not in ans
    for phrase in ("悶悶脹脹的", "肚子上面悶脹", "胸口不太舒服", "胸口怪怪的", "胸口緊感", "下巴跟左肩那邊沉沉的", "心絞痛", "胸口肌肉按下去會痛"):
        assert phrase in ans, phrase
    assert "剛剛就是吃飽坐著的時候" in ans and "rest_symptom＝true" in ans
    assert "單獨的「不舒服」不算" in ans and "單獨的「不舒服」不算" in op
    assert "晚上躺下會覺得比較喘要墊高枕頭" in op and "dyspnea_grade 填 null" in op
    assert "剛才胸口一陣壓迫感" in op and "ongoing_now 填 null" in op
    assert "reproducible_mechanical＝true" in op and "ntg_use_increased＝true" in op and "episode_frequency_increased＝true" in op
    for text in (ans, op):
        assert "chest_discomfort_mentioned" in text and "胸口脹脹的" in text
    assert "「緊緊的」" not in ans and "「怪怪的」「不舒服」" not in op               # 舊的「不填」例句已改掉
    _, _, schema, _ = build_request("胸口脹脹的。", None)
    assert "chest_discomfort_mentioned" in schema["properties"]
    assert "只說「沒有不舒服」，沒說到的症狀一樣填 null" in op                    # 概括否認不推定紅旗否認
    assert "episode_frequency_increased" in schema["properties"]


def test_c_unknown_character_after_asking_follows_vague_rule_but_keeps_new_today_t0(engine):
    """提過胸口不適、問了性質仍未知：比照 vague（§5.8）落 T9、不會定在 T2／T3；新發今天保留 T0（較急方向，待確認）。"""
    flag = {"chest_discomfort_mentioned": True, "ongoing_now": False, "presyncope": False, "diaphoresis": False, "rest_symptom": False,
            "threshold_decreased": False, "ntg_use_increased": False, "episode_frequency_increased": False}
    assert decide_slots(engine, {**flag, "onset_new": True, "last_episode_timing": "over_24h", "recurrence": False}).provisional_tier == 9
    assert decide_slots(engine, {**flag, "symptom_vs_pre_pci": "milder", "exertion_relation": "exertion_only"}).provisional_tier == 9
    assert decide_slots(engine, {**flag, "onset_new": True, "last_episode_timing": "today"}).provisional_tier == 0
    assert decide_slots(engine, {**flag, "pattern_unchanged_duration_months": 24, "dyspnea_acute": False}).provisional_tier == 3   # 例外 A
    p, e = Prompter(), RulesEngine()
    s = SlotState({**flag, "onset_new": True, "last_episode_timing": "today", "dyspnea_grade": "none"})
    assert p.character_followup_question(s, e.decide(s), set()) == QB["Q-CHARACTER-01"]     # T0 只靠新發今天 → 仍問性質
    s2 = SlotState({**flag, "ntg_use_increased": True, "dyspnea_grade": "none"})
    assert p.character_followup_question(s2, e.decide(s2), set()) is None                    # 其他 T0 因子 → 不延誤


def test_d_epigastric_answer_still_reaches_carveout_for_flag_only_opening():
    c = CASES["S-MID-13#2"]            # 新發今天、活動相關（carve-out 不成立）→ T0
    op = {"cad_history": True, "chest_discomfort_mentioned": True, "postprandial_relieved": True}
    r = run_case(c, extractor=Echo(c, opening=op))
    assert "Q-CHARACTER-01" in _qs(r) and r.final.tier == c.truth_tier


def test_c7_llm_eval_report_writes_transcript_meta():
    from acs_triage.loaders import REPO_ROOT
    assert "**transcript_meta(" in (REPO_ROOT / "sim" / "run_llm_eval.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("grade", ["exertional_heavy", "exertional_daily"])
@pytest.mark.parametrize("reset", [True, False])
def test_h3_single_fact_s_insuf_06_0_with_dyspnea_stays_t0(grade, reset):
    """H3 試做的代價（單一事實較不急 4 組，都是 S-INSUF-06#0 加上會喘）：vague＋呼吸＋新發時先問活動題，例外 B 在上限內成立。"""
    c = CASES["S-INSUF-06#0"]
    case = dataclasses.replace(c, slots=_complete({**c.slots, "dyspnea_grade": grade}),
                               reset_slots=sorted(set(c.reset_slots) | {"dyspnea_grade"}) if reset else c.reset_slots)
    r = run_case(case)
    assert r.final.tier == 0 and not r.final.hard_stop and r.n_questions <= 12
    qs = _qs(r)
    assert qs.index("Q-EXERTION-01") < qs.index("Q-THRESHOLD-01") if "Q-THRESHOLD-01" in qs else "Q-EXERTION-01" in qs
