"""D-58（AI 代理裁定（Fable 5.2，2026-11-25，Clinical Owner 授權），未經 Clinical Owner 逐例審閱）：
#5 D-44 例外 A 縮小（同時符合 T2-DYSPNEA-DAILY／T2-POSTURAL-NEWMED 除「無胸部症狀」外全部條件 → T2）；
#7 Q-REPRO-01 只在 symptom_character == pain 時問；D-55 已知限制 (10) 抽取快取併發 single-flight。"""
import dataclasses
import itertools
import random
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest

from acs_triage.extract import extract
from acs_triage.loaders import load_clinical_rules, question_by_id, slot_defs
from acs_triage.prompter import Prompter
from acs_triage.rules import RulesEngine, SlotState, tiers
from sim.cases import all_cases
from sim.llm_extract_v2 import LLMExtractorV2, build_request, mention_slots
from sim.patient import ScriptedPatient
from sim.runner import run_case

E = RulesEngine()
QB = question_by_id()
CASES = {c.id: c for c in all_cases()}
FLAG = "reproducible_mechanical_mentioned"
REDFLAGS = {q.id for q in QB.values() if q.priority == "redflag"}

# 型態 24 個月、所有升級因子明確否認、gate 需要的欄位都已知（同 tests/test_d56.py 的 STABLE）
STABLE = dict(cad_history=True, onset_new=False, pattern_unchanged_duration_months=24, rest_symptom=False, threshold_decreased=False,
              dyspnea_acute=False, presyncope=False, syncope=False, ongoing_now=False, diaphoresis=False, ntg_use_increased=False,
              episode_frequency_increased=False, dyspnea_grade="none", orthopnea_pnd=False, cant_finish_sentence=False,
              antiplatelet_interrupted=False)
DAILY = dict(STABLE, dyspnea_grade="exertional_daily", dyspnea_complaint=True)
POSTURAL = dict(STABLE, postural_dizziness=True, new_medication_recent=True)


def _d(base, **slots):
    return E.decide(SlotState({**base, **slots}))


# ---------------------------------------------------------------- #5：裁定原例（delegate 在引擎上確認的三組）
@pytest.mark.parametrize("base,none_rule", [(DAILY, "T2-DYSPNEA-DAILY"), (POSTURAL, "T2-POSTURAL-NEWMED")])
def test_5_none_vague_tightness_all_t2(base, none_rule):
    """走路做家事就喘（或姿勢性頭暈＋新藥）、型態 24 個月：沒有胸部症狀 T2、悶 T2；說不上來 D-58 前 T3（例外 A）→ T2。"""
    d = _d(base, symptom_character="none")
    assert (d.provisional_tier, d.tier, d.gate_passed) == (2, 2, True) and d.evidence == [none_rule]
    d = _d(base, symptom_character="tightness")
    assert (d.provisional_tier, d.tier, d.gate_passed) == (2, 2, True) and d.evidence == ["T3-STABLE", "T2-CHEST-FLOOR"]
    d = _d(base, symptom_character="vague")
    assert (d.provisional_tier, d.tier, d.gate_passed) == (2, 2, True) and d.evidence == ["T3-STABLE", "T2-CHEST-FLOOR"]
    assert not tiers.d44_exception_a(SlotState({**base, "symptom_character": "vague"}))
    assert tiers.t2_conditions_except_chest(SlotState({**base, "symptom_character": "vague"}))


def test_5_exception_a_unchanged_otherwise():
    """不符合兩條 T2 條件者例外 A 照舊（S-INSUF-01#1 維持 T3）：沒喘、只有激烈運動才喘、姿勢性頭暈沒有新藥。"""
    for base in (STABLE, dict(STABLE, dyspnea_grade="exertional_heavy", dyspnea_complaint=True),
                 dict(STABLE, postural_dizziness=True, new_medication_recent=False)):
        d = _d(base, symptom_character="vague")
        assert (d.provisional_tier, d.tier) == (3, 3) and d.evidence == ["T3-STABLE"]
        assert tiers.d44_exception_a(SlotState({**base, "symptom_character": "vague"}))
    c = CASES["S-INSUF-01#1"]
    r = run_case(c)
    assert (r.final.tier, r.final.hard_stop) == (3, False) == (c.truth_tier, c.truth_hard_stop) and r.final.evidence == ["T3-STABLE"]


def test_5_pending_test_floor_still_t1_and_expedite_kept():
    """待追蹤檢查的 T1 下限照舊（T2 再提高到 T1）；抗血小板中斷：D-58 前 T3＋expedite，現在 T2＋expedite（D-56 裁定 2）。"""
    d = _d(DAILY, symptom_character="vague", pending_abnormal_test=True)
    assert d.provisional_tier == 1 and d.evidence == ["T3-STABLE", "T2-CHEST-FLOOR", "T1-PENDING-TEST"]
    d = _d(DAILY, symptom_character="vague", antiplatelet_interrupted=True)
    assert d.provisional_tier == 2 and "expedite" in d.pathway_actions


def test_5_condition_mirrors_t2_rules():
    """t2_conditions_except_chest 與 t2_rules 的兩條在「沒有胸部症狀」時逐組一致（隨機 6,000 組，性質改成 none 比對）。"""
    rng = random.Random(58)
    defs = slot_defs()
    hits = 0
    for _ in range(6000):
        s = {}
        for sid, d in defs.items():
            if rng.random() < 0.5:
                continue
            s[sid] = (rng.choice([True, False]) if d["type"] == "yes_no" else rng.choice(d["choices"]) if d["type"] == "choice"
                      else rng.choice([0.0, 1.0, 3.0, 24.0]))
        st = SlotState(s)
        none = SlotState({**s, "symptom_character": "none"})
        expect = bool({"T2-DYSPNEA-DAILY", "T2-POSTURAL-NEWMED"} & set(tiers.t2_rules(none)))
        assert tiers.t2_conditions_except_chest(st) is expect
        hits += expect
    assert hits > 0


def _vague_states():
    """vague 狀態窮舉：#5 讀到的欄位（兩條 T2 條件、例外 A 的新發／型態、紅旗 presyncope、待追蹤檢查）全部組合，其他升級因子明確否認。"""
    grid = dict(dyspnea_grade=[None, "none", "exertional_heavy", "exertional_daily", "rest"],
                dyspnea_acute=[None, False, True], orthopnea_pnd=[None, False, True],
                postural_dizziness=[None, False, True], new_medication_recent=[None, False, True], presyncope=[None, False, True],
                onset_new=[None, False, True], pattern_unchanged_duration_months=[None, 3, 24], pending_abnormal_test=[None, True])
    fixed = {k: v for k, v in STABLE.items() if k not in grid}
    for combo in itertools.product(*grid.values()):
        yield {**fixed, "symptom_character": "vague", **{k: v for k, v in zip(grid, combo) if v is not None}}
    rng = random.Random(5858)                                     # 另加 4,000 組全欄位隨機的 vague 狀態
    defs = slot_defs()
    for _ in range(4000):
        s = {sid: (rng.choice([True, False]) if d["type"] == "yes_no" else rng.choice(d["choices"]) if d["type"] == "choice"
                   else rng.choice([0.0, 0.3, 2.0, 6.0, 24.0])) for sid, d in defs.items() if rng.random() < 0.5}
        yield {**s, "symptom_character": "vague"}


def test_5_exhaustive_vague_never_less_urgent_than_head(monkeypatch):
    """vague 狀態（窮舉 21,870 組＋隨機 4,000 組）：與 HEAD（不縮小例外 A）相比，只有暫判 T3 → T2（定案 T3 → T2 或 T9 不變）、
    或待追蹤檢查下限後同為 T1 而多一個 T2-CHEST-FLOOR；Hard stop、缺項、動作與其他結果逐組相同。"""
    states = list(_vague_states())
    new = [E.decide(SlotState(s)) for s in states]
    cond = [tiers.t2_conditions_except_chest(SlotState(s)) for s in states]
    monkeypatch.setattr(tiers, "t2_conditions_except_chest", lambda s: False)       # = HEAD 的 d44_exception_a
    old = [E.decide(SlotState(s)) for s in states]
    changed = Counter()
    for a, b, c in zip(new, old, cond):
        if a == b:
            continue
        assert c and not a.hard_stop and not b.hard_stop
        assert (a.missing, a.gate_passed, a.pathway_actions) == (b.missing, b.gate_passed, b.pathway_actions)
        assert (b.provisional_tier, a.provisional_tier) in ((3, 2), (1, 1))
        assert (b.tier, a.tier) in ((3, 2), (9, 9), (1, 1))
        assert b.evidence[0] == "T3-STABLE" and a.evidence == b.evidence[:1] + ["T2-CHEST-FLOOR"] + b.evidence[1:]
        changed[(b.tier, a.tier)] += 1
    assert changed[(3, 2)] > 0 and changed[(1, 1)] > 0


# ---------------------------------------------------------------- #7：Q-REPRO-01 只在 pain 時問
_RF_DONE = {FLAG: True, "ongoing_now": False, "presyncope": False, "diaphoresis": False, "dyspnea_grade": "none"}


@pytest.mark.parametrize("character", [None, *slot_defs()["symptom_character"]["choices"]])
def test_7_prompter_only_when_pain(character):
    st = SlotState({**_RF_DONE, **({"symptom_character": character} if character else {})})
    q = Prompter().repro_confirm_question(st, E.decide(st), set())
    assert q == (QB["Q-REPRO-01"] if character == "pain" else None)
    if character == "pain":
        assert Prompter().repro_confirm_question(st, E.decide(st), {"Q-REPRO-01"}) is None     # 只問一次


def test_7_rest_of_d56_d57_unchanged_for_pain():
    """pain 時其他條件照舊：Hard stop 不問；T0 由 T0-NEW-TODAY 以外的規則成立不問；只靠 T0-NEW-TODAY 要問。"""
    p = Prompter()
    base = {**_RF_DONE, "symptom_character": "pain", "onset_new": True, "last_episode_timing": "today"}
    st = SlotState(base)
    assert p.repro_confirm_question(st, E.decide(st), set()) == QB["Q-REPRO-01"]
    st = SlotState({**base, "rest_symptom": True})
    assert p.repro_confirm_question(st, E.decide(st), set()) is None
    st = SlotState({**base, "diaphoresis": True})
    assert E.decide(st).hard_stop and p.repro_confirm_question(st, E.decide(st), set()) is None


def _without_flag(case):
    """對照：同一開場白但抽取結果拿掉旗標（回答用結構化事實，同 Scripted）。"""
    def ex(text, q, confirm_prompt=None):
        if q is None:
            return {k: v for k, v in extract(text).items() if v is not None and k != FLAG}
        return {q.slot_id: ScriptedPatient(case).answer(q).value}
    return ex


@pytest.mark.parametrize("character", ["none", "pressure", "tightness", "vague", "other", "epigastric"])
def test_7_flag_opening_without_pain_flag_has_no_effect(character):
    """開場白只說「按下去不會痛」（旗標、性質未知）：D-58 前確認題 Q-REPRO-01 排在第 2 題（D-57 觀察）；現在性質不是 pain 時
    旗標不起作用——問題序列與結果等於沒有旗標的同一通。vague 落 T9 後一般選題仍可能問到 Q-REPRO-01（D-56 前就有的路徑），其他性質不問。"""
    base = CASES["S-MID-14"]
    c = dataclasses.replace(base, id="D58-X", opening_zh="按下去不會痛", slots={**base.slots, "symptom_character": character})
    assert extract(c.opening_zh)[FLAG] is True
    r, ref = run_case(c), run_case(c, extractor=_without_flag(c))
    qs = [t.question_id for t in r.turns]
    assert qs == [t.question_id for t in ref.turns] and (r.final.tier, r.final.evidence) == (ref.final.tier, ref.final.evidence)
    assert ("Q-REPRO-01" in qs) == (character == "vague")


def test_7_flag_opening_with_pain_asks_once_after_character_and_redflags():
    base = CASES["S-MID-14"]
    c = dataclasses.replace(base, id="D58-Y", opening_zh="按下去不會痛", slots=dict(base.slots))
    r = run_case(c)
    qs = [t.question_id for t in r.turns]
    i = qs.index("Q-REPRO-01")
    assert qs.count("Q-REPRO-01") == 1 and i > qs.index("Q-CHARACTER-01")
    assert {"Q-ONGOING-01", "Q-SYNCOPE-01", "Q-DIAPH-01"} <= set(qs[:i])          # 胸部紅旗題都在它之前
    assert r.final_state._values["reproducible_mechanical"].asked_by_question_id == "Q-REPRO-01"
    assert (r.final.tier, r.final.evidence) == (3, ["T3-MECHANICAL"])


def test_7_s_mid_14_still_t3():
    c = CASES["S-MID-14"]
    r = run_case(c)
    qs = [t.question_id for t in r.turns]
    assert qs.count("Q-REPRO-01") == 1 and qs.index("Q-REPRO-01") == 4 and set(qs[:4]) <= REDFLAGS
    assert (r.final.tier, r.final.hard_stop, r.final.evidence) == (3, False, ["T3-MECHANICAL"]) == (c.truth_tier, False, ["T3-MECHANICAL"])


# ---------------------------------------------------------------- 抽取快取 single-flight（D-55 已知限制 (10)）
OK_OBJ = {"asked": {"evidence": "有", "stance": "yes"}, "mentions": [], "unclassified": []}
OPENING_OBJ = {"evidence": [], **{k: None for k in mention_slots()}, "unclassified": []}
USAGE = {"input_tokens": 100, "output_tokens": 10}


class GatedClient:
    """block_on 裡的 user 文字要等 release 才回；記下每次收到的 (system, user)。"""

    def __init__(self, block_on=None):
        self.block_on, self.calls = block_on, []
        self.entered, self.release = threading.Event(), threading.Event()
        self._lock = threading.Lock()

    def ask(self, system, user, schema, name):
        with self._lock:
            self.calls.append((system, user))
        if self.block_on is None or self.block_on in user:
            self.entered.set()
            assert self.release.wait(10)
        return (OPENING_OBJ if name == "opening_v2" else OK_OBJ), USAGE, "fake"


def test_cache_single_flight_identical_concurrent_requests():
    """同一句併發 8 次：模型只被呼叫一次，8 個呼叫端拿到同一筆紀錄；送出的文字與 build_request 逐字相同。"""
    c = GatedClient()
    ex = LLMExtractorV2(c, name="fake", sleep=lambda s: None)
    q = QB["Q-DIAPH-01"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(ex.record, "有。", q) for _ in range(8)]
        assert c.entered.wait(10)
        time.sleep(0.2)                       # 其他 7 個已經在等同一把鎖（沒有 single-flight 時這裡已是 8 次呼叫）
        assert len(c.calls) == 1
        c.release.set()
        recs = [f.result() for f in futs]
    assert len(c.calls) == 1 and all(r is recs[0] for r in recs) and recs[0]["ok"]
    assert c.calls[0] == build_request("有。", q)[:2]
    assert ex("有。", q) == {"diaphoresis": True} and len(c.calls) == 1


def test_cache_single_flight_s_mid_12_openings_and_other_keys_not_blocked():
    """S-MID-12 三個變體開場白相同：併發只呼叫一次；不同句子不被這把鎖擋住。"""
    ids = ["S-MID-12", "S-MID-12#0", "S-MID-12#1"]
    assert len({CASES[i].opening_zh for i in ids}) == 1
    text = CASES["S-MID-12"].opening_zh
    c = GatedClient(block_on=text)
    ex = LLMExtractorV2(c, name="fake", sleep=lambda s: None)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(ex, CASES[i].opening_zh, None) for i in ids]
        assert c.entered.wait(10)
        other = pool.submit(ex.record, "沒有。", QB["Q-DIAPH-01"]).result(timeout=10)   # 另一個鍵：不必等
        assert other["ok"] and not c.release.is_set()
        c.release.set()
        outs = [f.result() for f in futs]
    assert sum(1 for _, u in c.calls if text in u) == 1 and len(c.calls) == 2
    assert outs[0] == outs[1] == outs[2]
    assert c.calls[[text in u for _, u in c.calls].index(True)] == build_request(text, None)[:2]


def test_rules_version_bumped():
    assert load_clinical_rules()["rules_version"] == "0.12.0"
