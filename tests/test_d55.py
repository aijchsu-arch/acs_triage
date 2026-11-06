"""D-55（Clinical Owner 2026-11-04／05 裁定 D-54 待確認 6 項，rules 0.10.0）：R3 題數上限 15、F2 順口的 rest_symptom＝false 不採用、
R5 Q-FREQ-01 定稿、R6 抽取器提示 2.0-dev25（第五輪 dev26）；R1（呼吸分級複誦否認採用 none）與 R4（性質已否認後又提到胸口）試做後撤回。全部用假抽取器，不打 API。"""
import pytest
import yaml

from acs_triage.extract import extract
from acs_triage.loaders import DATA_DIR, load_clinical_rules, question_by_id
from acs_triage.pathway import tier9_fallback
from acs_triage.prompter.confirm import resolve_confirm
from acs_triage.rules import SlotState
from sim.cases import all_cases
from sim.llm_extract_v2 import load_prompts, system_prompt
from sim.patient import ScriptedPatient
from sim.runner import _write_mentions, run_case

QB = question_by_id()
CASES = {c.id: c for c in all_cases()}
DG = QB["Q-DYSPNEA-GRADE-01"]


def _qs(r):
    return [t.question_id for t in r.turns]


class Fake:
    """假抽取器：開場白回傳 opening；被問的題回傳病人事實；mentions（題號 → dict）加在直接回答。"""

    def __init__(self, case, opening=None, mentions=None):
        self.case, self.opening, self.mentions = case, opening or {}, mentions or {}

    def __call__(self, text, q, confirm_prompt=None):
        if q is None:
            return dict(self.opening)
        if confirm_prompt is not None:
            return {q.slot_id: self.case.slots.get(q.slot_id)}
        return {q.slot_id: ScriptedPatient(self.case).answer(q).value, **self.mentions.get(q.id, {})}


# ---------------------------------------------------------------- R1 撤回：D-50 照舊取較嚴重
def test_r1_withdrawn_d50_keeps_more_severe():
    """Clinical Owner 2026-11-04 撤回 R1（試做時 S-MID-11#1 Hard stop → T0、S-ACUTE-03#2 T2 → T9）：只有激烈運動才喘、複誦答沒有 → 保留原值。"""
    assert "confirm_back_accept_less_severe" not in load_clinical_rules()
    assert resolve_confirm(DG, "exertional_heavy", "none") == ("exertional_heavy", True)


# ---------------------------------------------------------------- R3：題數上限 15
def test_r3_cap_is_fifteen_and_sixteenth_not_asked():
    assert load_clinical_rules()["thresholds"]["max_questions"] == 15
    c = CASES["S-INSUF-01"]                              # 資訊不足組：每題都答不知道，問到上限
    r = run_case(c)
    assert r.n_questions == len(r.turns) == 15 and r.stop_reason == "max_questions" and r.final.tier == 9
    assert all(t.question_id for t in r.turns[12:15])                      # 第 13–15 題問得到
    at12 = run_case(c, max_questions=12)
    assert _qs(r)[:12] == _qs(at12) and at12.n_questions == 12            # 前 12 題與舊上限相同，之後才多問
    more = run_case(c, max_questions=16)
    assert more.n_questions == 16 and _qs(more)[:15] == _qs(r)            # 有第 16 題可問，但上限 15 不問


def test_r3_confirms_do_not_count():
    r = run_case(CASES["S-INSUF-01"])
    assert r.n_confirms > 0 and r.n_questions == len(r.turns) == 15


# ---------------------------------------------------------------- R4 撤回：L7 回到 HEAD 行為
def test_r4_withdrawn_flag_after_none_ignored():
    """Clinical Owner 2026-11-05 撤回 R4（試做三種做法都有比 HEAD 與全資訊不急的路徑）：性質已是 none 之後只設旗標的胸口提及照 HEAD 不處理。"""
    c = CASES["S-MID-20"]
    op = {k: v for k, v in extract(c.opening_zh).items() if v is not None}
    assert op["symptom_character"] == "none"
    base = run_case(c, extractor=Fake(c, opening=op))
    first = _qs(base)[0]
    r = run_case(c, extractor=Fake(c, opening=op, mentions={first: {"chest_discomfort_mentioned": True}}))
    assert _lab(r) == _lab(base) and _qs(r) == _qs(base) and not r.reasks
    assert r.final_state.get("symptom_character") == "none"
    st = SlotState({"symptom_character": "none"})
    _write_mentions(st, {"chest_discomfort_mentioned": True}, "dyspnea_grade", source="m")
    assert st.get("symptom_character") == "none"


def _lab(r):
    return "HS" if r.final.hard_stop else (f"T9(fb{tier9_fallback(r.final_state)[0]})" if r.final.tier == 9 else f"T{r.final.tier}")


# ---------------------------------------------------------------- F2：順口的 rest_symptom＝false 不採用
@pytest.mark.parametrize("cid", ["S-STABLE-01#0", "S-STABLE-02#1", "S-INSUF-03#1", "S-MID-08#1"])
def test_f2_mentioned_rest_denial_not_used(cid):
    """驗收注入法：Q-ONGOING-01 的回答順口帶 rest_symptom＝false（Gemma 對「休息後緩解」的寫法）→ 不寫入，Q-REST-01 照問、分級同不注入。"""
    c = CASES[cid]
    op = {k: v for k, v in extract(c.opening_zh).items() if v is not None}
    base = run_case(c, extractor=Fake(c, opening=op))
    r = run_case(c, extractor=Fake(c, opening=op, mentions={"Q-ONGOING-01": {"rest_symptom": False}}))
    assert _lab(r) == _lab(base) == "T0" and "Q-REST-01" in _qs(r)
    assert any(x["kind"] == "rest_denial_not_used" for x in r.mention_conflicts)


def test_f2_direct_answer_and_mentioned_yes_unchanged():
    st = SlotState({})
    _write_mentions(st, {"rest_symptom": False}, "ongoing_now", source="m")
    assert st.get("rest_symptom") is None
    _write_mentions(st, {"rest_symptom": True}, "ongoing_now", source="m")
    assert st.get("rest_symptom") is True                                                     # 順口的「有」照舊
    st2 = SlotState({})
    _write_mentions(st2, {"rest_symptom": False}, "rest_symptom", source="m")                  # 被問那題由 run_case 直接寫入
    assert st2.get("rest_symptom") is None
    c = CASES["S-STABLE-01"]
    assert run_case(c, extractor=Fake(c, opening={})).final_state.get("rest_symptom") is False  # 直接回答 Q-REST-01 的「沒有」照寫


# ---------------------------------------------------------------- R5、R6
def test_r5_q_freq_01_final_and_bank_version():
    raw = yaml.safe_load((DATA_DIR / "question_bank_seed.yaml").read_text(encoding="utf-8"))
    q = next(x for x in raw["questions"] if x["id"] == "Q-FREQ-01")
    assert raw["bank_version"] == "0.6" and "status" not in q and "DRAFT" not in q["why_zh"]
    assert q["script_zh"] == "最近發作的次數有比以前多嗎？"
    assert not any(x.get("status") == "DRAFT" for x in raw["questions"])


def test_r6_prompt_version_and_examples():
    assert load_prompts()["prompts_version"] == "2.0-dev26"
    opening, answer = system_prompt(opening=True), system_prompt(opening=False)
    for s in ("坐著休息的時候就不會悶", "今晚躺著看電視時也發作了", "打完流感疫苗手臂痠", "走路比平常喘一點", "今天忘記吃早上的藥",
              "要不要空腹抽血", "今天還沒發作"):
        assert s in opening, s
    # 2.0-dev26：規則 17、18 已刪（Gemma 因此把 S-MID-08 的 onset_weeks_ago 抽成 4.0、「走路不會更痛」抽成 exertion_only）
    assert "最近走路會有一點悶" not in opening and "比放支架前輕很多" not in opening
    for s in ("坐著休息的時候就不會悶", "休息完就好了", "坐著休息的時候都還好", "今晚躺著看電視時也發作了"):
        assert s in answer, s
    # 「走路比平常喘一點」只放開場白提示：放進回答句提示時本機 Gemma 的「不太會喘」改判較多（裁定 #12 不得受影響）
    assert "走路比平常喘一點" not in answer
    assert "「我其實不太會喘」→ answered、exertional_heavy" in answer and "「我不會喘」→ none" in opening    # 裁定 #12 不變


def test_dev26_opening_rest_denial_not_used_llm_path_only():
    """D-55 第五輪：LLM 抽取器（開場白與順口）不收 rest_symptom＝false，只有直接回答 Q-REST-01 才寫；「有」照收；關鍵詞路徑與 HEAD 相同。"""
    from sim.llm_extract_v2 import mention_slots, parse
    obj = {"evidence": [{"slot": "rest_symptom", "quote": "停下來就好了"}], **{k: None for k in mention_slots()}, "unclassified": []}
    slots, diag = parse({**obj, "rest_symptom": False}, "走路會悶，停下來就好了。", None)
    assert "rest_symptom" not in slots and any(g["guard"] == "rest_denial_not_used" for g in diag["guards"])
    assert parse({**obj, "rest_symptom": True}, "坐著看電視也會悶。", None)[0].get("rest_symptom") is True
    q = QB["Q-REST-01"]
    asked = {"asked": {"evidence": "沒有，休息的時候不會", "stance": "no"}, "mentions": [], "unclassified": []}
    assert parse(asked, "沒有，休息的時候不會。", q)[0]["rest_symptom"] is False          # 直接回答照寫
    assert extract("我有冠心症，前天開始走路會胸悶，今天還沒發作，休息時沒有。").get("rest_symptom") is False   # 關鍵詞路徑不變
