"""抽取器 v2（sim/llm_extract_v2.py）：提示／schema、解析與極性保護、快取與預算、重放寫入方式。全部用假 client，不打 API。"""
import pytest

from acs_triage.loaders import question_by_id, slot_defs
from acs_triage.rules import SlotState
from sim.llm_extract_v2 import (LLMExtractorV2, build_request, choices, load_prompts, mention_slots, negated, parse,
                                protect_asked_writer, request_schema, validate)
from sim.runner import _write_mentions

QB = question_by_id()


def opening_obj(evidence=(), unclassified=(), **vals):
    return {"evidence": [{"slot": s, "quote": t} for s, t in evidence],
            **{k: vals.get(k) for k in mention_slots()}, "unclassified": [{"slot": s, "phrase": p} for s, p in unclassified]}


def answer_obj(asked, mentions=(), unclassified=()):
    return {"asked": asked, "mentions": [{"slot": s, "evidence": e, "value": v} for s, e, v in mentions],
            "unclassified": [{"slot": s, "phrase": p} for s, p in unclassified]}


class FakeClient:
    def __init__(self, obj=None, exc=None):
        self.obj, self.exc, self.calls = obj, exc, []

    def ask(self, system, user, schema, name):
        self.calls.append((system, user, schema, name))
        if self.exc:
            raise self.exc
        return self.obj, {"input_tokens": 2000, "input_tokens_details": {"cached_tokens": 1000}, "output_tokens": 300}, "fake"


# ---------------------------------------------------------------- 提示與 schema
def test_requests_opening_answer_confirm():
    s, u, sc, name = build_request("胸口悶。", None)
    assert name == "opening_v2" and "開場白" in s and "胸口悶。" in u
    assert list(sc["properties"])[0] == "evidence" and "unclassified" in sc["properties"]
    assert "consult_screen_positive" not in sc["properties"]                     # 只在被問那題時有意義
    assert "other" not in sc["properties"]["symptom_character"]["enum"]          # 不硬塞 other（D-52）
    q = QB["Q-ONGOING-01"]
    s2, u2, sc2, name2 = build_request("還在。", q)
    assert name2 == "answer_v2" and s2 != s and q.script_zh.strip() in u2
    assert sc2["properties"]["asked"]["properties"]["stance"]["enum"] == ["yes", "no", "unclear"]
    s3, u3, sc3, name3 = build_request("對。", q, confirm_prompt="我跟您確認一下…對嗎？")
    assert name3 == "confirm_v2" and s3 == s2 and "我跟您確認一下…對嗎？" in u3 and "對。" in u3
    assert set(sc3["properties"]["asked"]["properties"]) == {"evidence", "agreement", "reply_answer"}


def test_choice_and_duration_asked_schema_have_status_and_no_null():
    a = request_schema(QB["Q-CHARACTER-01"])["properties"]["asked"]["properties"]
    assert a["status"]["enum"] == ["answered", "dont_know", "cannot_classify"]
    assert None not in a["value"]["enum"] and "other" not in a["value"]["enum"]
    d = request_schema(QB["Q-PATTERN-01"])["properties"]["asked"]["properties"]
    assert d["value"] == {"type": "number"}
    assert choices("dyspnea_grade") == list(slot_defs()["dyspnea_grade"]["choices"])


def test_prompt_versions_and_v1_untouched():
    assert load_prompts()["prompts_version"].startswith("2.")
    from sim.llm_extract import load_prompts as v1
    assert v1()["slot_prompts_version"] == "0.3" and v1()["opening_prompts_version"] == "0.1"


def test_validate():
    sc = request_schema(QB["Q-DIAPH-01"])
    validate(answer_obj({"evidence": "沒有", "stance": "no"}), sc)
    with pytest.raises(ValueError):
        validate(answer_obj({"evidence": "沒有", "stance": "maybe"}), sc)
    with pytest.raises(ValueError):
        validate({"asked": {"evidence": "x", "stance": "no"}, "mentions": []}, sc)          # 少了 unclassified
    with pytest.raises(ValueError):
        validate(answer_obj({"evidence": "x", "stance": "no"}, mentions=[("other_slot", "x", "true")]), sc)


# ---------------------------------------------------------------- 解析與極性保護
def test_negated_masks_non_negation_phrases():
    assert negated("沒有冒冷汗") and negated("不會喘") and negated("現在沒有了")
    assert not negated("胸口不舒服") and not negated("不太確定") and not negated("喘到一句話講不完") and not negated("還沒好")


def test_yes_no_stance_and_leading_word_guard():
    q = QB["Q-ONGOING-01"]
    assert parse(answer_obj({"evidence": "還在", "stance": "yes"}), "還在，現在胸口悶悶的。", q)[0] == {"ongoing_now": True}
    assert parse(answer_obj({"evidence": "現在沒有了", "stance": "no"}), "現在沒有了。", q)[0] == {"ongoing_now": False}
    assert parse(answer_obj({"evidence": "", "stance": "unclear"}), "不知道耶。", q)[0] == {"ongoing_now": None}
    slots, diag = parse(answer_obj({"evidence": "沒有", "stance": "yes"}), "沒有，現在不會了。", q)   # 「沒有→有」
    assert slots == {"ongoing_now": None} and diag["guards"][0]["guard"] == "asked_stance_vs_leading_word"
    # 二選一問法、一題問兩件事的題目不套句首規則；只問一件事的（D-50 範圍外也算）要套
    assert parse(answer_obj({"evidence": "沒有，第一次", "stance": "yes"}), "沒有，這是第一次。", QB["Q-ONSET-01"])[0] == {"onset_new": True}
    assert parse(answer_obj({"evidence": "不會", "stance": "yes"}), "不會，站起來才會。", QB["Q-POSTURAL-01"])[0] == {"postural_dizziness": True}
    assert parse(answer_obj({"evidence": "沒有", "stance": "yes"}), "沒有，都有照時間吃。", QB["Q-ANTIPLT-01"])[0] == {"antiplatelet_interrupted": None}
    from sim.llm_extract_v2 import single_proposition
    assert all(single_proposition(q) for q in QB.values() if q.priority == "redflag" and q.answer_type == "yes_no")


def test_mentions_written_and_guarded():
    q = QB["Q-DYSPNEA-GRADE-01"]
    slots, diag = parse(answer_obj({"evidence": "不會喘", "status": "answered", "value": "none"},
                                   mentions=[("symptom_character", "胸口悶悶的", "tightness"),
                                             ("diaphoresis", "沒有冒冷汗", "true"),          # 否定片段卻是 true → 丟
                                             ("presyncope", "還好", "false"),                # 否認卻沒有否定詞 → 丟
                                             ("syncope", "沒有昏倒", "false"),
                                             ("ongoing_now", "最近有悶過", "true"),           # 沒有「現在」字眼 → 丟
                                             ("onset_new", "最近才有", "maybe")]),            # 值不合法 → 丟
                        "我不會喘，胸口悶悶的，沒有冒冷汗，沒有昏倒。", q)
    assert slots == {"dyspnea_grade": "none", "symptom_character": "tightness"}       # 回答句順口的紅旗否認不採用
    assert {g["guard"] for g in diag["guards"]} == {"affirm_with_negated_evidence", "mention_redflag_denial_not_used",
                                                    "ongoing_mention_without_present_marker"}
    s3, d3 = parse(answer_obj({"evidence": "現在沒有", "stance": "no"}, mentions=[("symptom_character", "胸口目前不會悶", "none")]),
                   "現在沒有喔，胸口目前不會悶。", QB["Q-ONGOING-01"])
    assert s3 == {"ongoing_now": False} and d3["guards"][0]["guard"] == "mention_redflag_denial_not_used"
    s2, _ = parse(answer_obj({"evidence": "", "stance": "no"}, mentions=[("ongoing_now", "現在還在悶", "true")]),
                  "沒有冒汗，現在還在悶。", QB["Q-DIAPH-01"])
    assert s2 == {"diaphoresis": False, "ongoing_now": True}


def test_present_marker_and_character_not_affirm_guarded():
    q = QB["Q-THRESHOLD-01"]
    slots, diag = parse(answer_obj({"evidence": "好像是", "stance": "yes"},
                                   mentions=[("ongoing_now", "現在比較輕一點的活動就會悶", "true"),   # 「這陣子」不是「此刻」
                                             ("symptom_character", "以前從來沒有這樣悶過", "tightness")]),
                        "好像是耶，現在比較輕一點的活動就會悶，以前從來沒有這樣悶過。", q)
    assert slots == {"threshold_decreased": True, "symptom_character": "tightness"}
    assert [g["guard"] for g in diag["guards"]] == ["ongoing_mention_without_present_marker"]
    s2, _ = parse(answer_obj({"evidence": "", "stance": "no"}, mentions=[("dyspnea_grade", "坐著不喘", "rest")]), "坐著不喘。",
                  QB["Q-DIAPH-01"])
    assert s2 == {"diaphoresis": False}                          # rest（RF-02）的片段含否定詞 → 丟


def test_reparse_cached_raw_with_current_code(tmp_path):
    from sim.llm_extract_v2 import meta_for
    meta = meta_for("gemma")
    raw = answer_obj({"evidence": "沒有", "stance": "yes"})
    rec = {"q": "Q-DIAPH-01", "confirm_prompt": None, "text": "沒有冒汗。", "sent": "沒有冒汗。", "ok": True,
           "slots": {"diaphoresis": True}, "diag": {}, "raw": raw, "cost": 0.0, "latency_s": 0.1, "usage": {}, "model": "m"}
    p = tmp_path / "c.json"
    p.write_text(__import__("json").dumps({"meta": {**meta, "code_sha256": "old"}, "records": [rec]}), encoding="utf-8")
    ex = LLMExtractorV2(FakeClient(exc=RuntimeError("no call")), name="m")
    with pytest.raises(SystemExit):
        ex.load(p, meta)
    ex.load(p, meta, reparse=True)
    assert ex("沒有冒汗。", QB["Q-DIAPH-01"]) == {"diaphoresis": None}     # 以目前的句首規則重算，不重新呼叫
    p.write_text(__import__("json").dumps({"meta": {**meta, "rendered_sha256": "other"}, "records": [rec]}), encoding="utf-8")
    with pytest.raises(SystemExit):
        LLMExtractorV2(FakeClient(), name="m").load(p, meta, reparse=True)   # 送出的提示不同 → 不得沿用


def test_unclassified_and_conflicting_mentions_are_not_written():
    q = QB["Q-DIAPH-01"]
    slots, diag = parse(answer_obj({"evidence": "沒有", "stance": "no"},
                                   mentions=[("symptom_character", "胸口脹脹的", "tightness"), ("nausea", "想吐", "true"),
                                             ("nausea", "不想吐", "false")],
                                   unclassified=[("symptom_character", "胸口脹脹的")]), "沒有，胸口脹脹的。", q)
    assert slots == {"diaphoresis": False}
    assert diag["unclassified"] == [{"slot": "symptom_character", "phrase": "胸口脹脹的"}]


def test_asked_value_from_mentions_and_status():
    q = QB["Q-DYSPNEA-GRADE-01"]
    slots, diag = parse(answer_obj({"evidence": "喘是不會喘啦", "status": "dont_know", "value": "rest"},
                                   mentions=[("dyspnea_grade", "喘是不會喘啦", "none")]), "喘是不會喘啦。", q)
    assert slots == {"dyspnea_grade": "none"} and diag["guards"][0]["guard"] == "asked_value_from_mentions"
    c = QB["Q-CHARACTER-01"]
    s2, d2 = parse(answer_obj({"evidence": "脹脹的", "status": "cannot_classify", "value": "pressure"}), "脹脹的。", c)
    assert s2 == {"symptom_character": None} and d2["unclassified"] == [{"slot": "symptom_character", "phrase": "脹脹的"}]
    s3, _ = parse(answer_obj({"evidence": "有沒有喘我不知道", "status": "answered", "value": "none"}), "有沒有喘我不知道。", q)
    assert s3 == {"dyspnea_grade": None}                    # 紅旗題的否認要有否定詞
    s4, _ = parse(answer_obj({"evidence": "兩年", "status": "answered", "value": 24}), "大概兩年。", QB["Q-PATTERN-01"])
    assert s4 == {"pattern_unchanged_duration_months": 24.0}


def test_opening_dense_with_evidence_guards():
    obj = opening_obj(evidence=[("symptom_character", "胸口悶"), ("syncope", "沒有昏倒"), ("cad_history", "我有冠心症")],
                      symptom_character="tightness", syncope=False, cad_history=True, dyspnea_grade="none",
                      last_episode_timing="ongoing")
    slots, diag = parse(obj, "我有冠心症，胸口悶，沒有昏倒。", None)
    # 沒提到喘卻寫 none（沒有否定詞證據）→ 丟；ongoing 沒有「現在」字眼的片段 → 丟
    assert slots == {"symptom_character": "tightness", "syncope": False, "cad_history": True}
    assert [g["slot"] for g in diag["guards"]] == ["dyspnea_grade", "last_episode_timing"]
    s2, _ = parse(opening_obj(evidence=[("last_episode_timing", "現在完全沒事")], last_episode_timing="ongoing"), "現在完全沒事。", None)
    assert s2 == {}                                         # 片段含否定詞 → 丟
    s3, _ = parse(opening_obj(evidence=[("ongoing_now", "從早上到現在都還在")], ongoing_now=True), "從早上到現在都還在。", None)
    assert s3 == {"ongoing_now": True}


def test_confirm_reply_agreement_and_restated():
    from acs_triage.prompter.confirm import confirm_prompt
    from sim.llm_extract_v2 import confirmed_value
    q, c = QB["Q-ONGOING-01"], QB["Q-DYSPNEA-GRADE-01"]
    p_no, p_ask = confirm_prompt(q, False), confirm_prompt(q, None)
    assert confirmed_value(q, p_no) == (True, False) and confirmed_value(q, p_ask) == (False, None)
    assert confirmed_value(c, confirm_prompt(c, "exertional_heavy")) == (True, "exertional_heavy")

    yn = {"yes": "有（情況成立）", "no": "沒有（情況不成立）", "none": "沒有重新回答", "stated": "重新回答了"}

    def conf(agreement, restated, value=None, prompt=p_no, qq=q, text="對。"):
        restated = yn[restated] if qq.answer_type == "yes_no" or restated == "stated" else "沒有重新回答"
        a = {"evidence": text, "agreement": agreement, "reply_answer": restated} | ({} if value is None else {"value": value})
        return parse({"asked": a, "mentions": [], "unclassified": []}, text, qq, confirm_prompt=prompt)[0][qq.slot_id]

    assert conf("agree", "none") is False                       # 「對。」→ 複誦的答案（沒有）
    assert conf("agree", "no", text="對，現在沒有了。") is False   # 句首「對」不套句首規則
    assert conf("disagree", "yes", text="不是，有啊。") is True
    assert conf("disagree", "none", text="不是。") is True        # 是非題只說「不是」→ 相反
    assert conf("unclear", "none", text="嗯…") is None
    assert conf("unclear", "yes", prompt=p_ask, text="有。") is True and conf("agree", "none", prompt=p_ask) is None
    pc = confirm_prompt(c, "none")
    assert conf("disagree", "none", "rest", prompt=pc, qq=c, text="不是。") is None           # 選擇題只說「不是」→ 未知
    assert conf("disagree", "stated", "exertional_daily", prompt=pc, qq=c, text="不是，走路就喘。") == "exertional_daily"
    assert conf("agree", "none", "rest", prompt=pc, qq=c) == "none"
    pa = confirm_prompt(c, None)                                 # 「我再跟您確認一次…」：病人說不清楚卻被讀成「沒有」→ 不採用
    assert conf("unclear", "stated", "none", prompt=pa, qq=c, text="喘的情況我不清楚，他沒跟我講。") is None


# ---------------------------------------------------------------- 抽取器
def test_extractor_cache_confirm_key_traditional_and_cost():
    obj = answer_obj({"evidence": "有", "stance": "yes"})
    c = FakeClient(obj)
    ex = LLMExtractorV2(c, name="fake", price=(2.0, 0.1, 10.0), to_traditional=lambda s: s.replace("没", "沒"))
    q = QB["Q-DIAPH-01"]
    assert ex("有，没事。", q) == {"diaphoresis": True}
    assert ex("有，没事。", q) == {"diaphoresis": True} and len(c.calls) == 1          # 快取
    assert "有，沒事。" in c.calls[0][1] and ex.n_tw_changed == 1                     # 送出前轉繁
    c.obj = {"asked": {"evidence": "對", "agreement": "agree", "reply_answer": "沒有重新回答"}, "mentions": [], "unclassified": []}
    assert ex("有，没事。", q, confirm_prompt="我跟您確認一下，剛剛問您『…』，您的回答是『有』，對嗎？") == {"diaphoresis": True}
    assert len(c.calls) == 2                                                          # 複誦句是快取鍵的一部分
    assert ex.spent == pytest.approx(2 * (1000 * 2 + 1000 * 0.1 + 300 * 10) / 1e6)


def test_extractor_failure_and_budget():
    ex = LLMExtractorV2(FakeClient(exc=RuntimeError("OpenAI HTTP 500 code=None type=None")), name="fake")
    assert ex("有。", QB["Q-DIAPH-01"]) == {"diaphoresis": None} and ex("胸口悶。", None) == {}
    assert not ex.record("有。", QB["Q-DIAPH-01"])["ok"]
    bad = LLMExtractorV2(FakeClient({"asked": {"stance": "yes"}}), name="fake")
    assert bad("有。", QB["Q-DIAPH-01"]) == {"diaphoresis": None}                     # schema 不合法 = 失敗
    c = FakeClient(answer_obj({"evidence": "有", "stance": "yes"}))
    b = LLMExtractorV2(c, name="fake", price=(2.0, 0.1, 10.0), budget_usd=0.001)
    b("有。", QB["Q-DIAPH-01"])
    assert b.record("有冒汗。", QB["Q-DIAPH-01"])["error"] == "budget_exceeded" and len(c.calls) == 1


# ---------------------------------------------------------------- 寫入方式（重放與閉環共用）
def test_mention_write_policy_fill_unknown_upgrade_or_conflict():
    st = SlotState({"symptom_character": "pressure", "dyspnea_grade": "exertional_daily", "nausea": True})
    st.set("diaphoresis", False, asked_by="Q-DIAPH-01", source="turn1")
    st.set("presyncope", None, asked_by="Q-SYNCOPE-01", source="turn2")          # 問過、答不知道
    cf = _write_mentions(st, {"symptom_character": "vague", "dyspnea_grade": "rest", "nausea": False, "diaphoresis": True,
                              "presyncope": True, "edema": True, "ongoing_now": None}, "cough_related", source="m")
    assert st.get("dyspnea_grade") == "rest"                        # confirm_back_severity 較嚴重 → 覆蓋
    assert st.get("diaphoresis") is True                            # 紅旗是非題「有」→ 覆蓋（即使問過）
    assert st.get("presyncope") is True and st.get("edema") is True  # 未知（含問過答不知道）→ 補上
    assert st.get("symptom_character") == "pressure" and st.get("nausea") is True   # 其他不同 → 保留已知值
    assert sorted(c["slot"] for c in cf) == ["nausea", "symptom_character"]
    assert {"kind": "conflict", "slot": "nausea", "known": True, "mention": False} in cf
    protect_asked_writer(st, {"cough_related": True, "orthopnea_pnd": True}, QB["Q-COUGH-01"], "turn3")
    assert st.get("cough_related") is True and st.get("orthopnea_pnd") is True


def test_report_and_adjudication_table_reproduce_from_repo_inputs(tmp_path, monkeypatch):
    """主報告與裁定表只靠 repo 內的程式與 reports/extractor_v2_2026-10-27_inputs/ 逐位重產（不讀 scratch）。"""
    import sys

    from acs_triage.loaders import REPO_ROOT
    from sim import extractor_v2_report as rep
    monkeypatch.setattr(sys, "argv", ["sim.extractor_v2_report", "--out", str(tmp_path)])
    rep.main()
    for name in ("extractor_v2_2026-10-27.md", "extractor_v2_2026-10-27.json",
                 "extractor_v2_ambiguous_2026-10-27.md", "extractor_v2_ambiguous_2026-10-27.xlsx"):
        assert (tmp_path / name).read_bytes() == (REPO_ROOT / "reports" / name).read_bytes(), name
