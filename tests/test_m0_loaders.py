"""M0：YAML 與文件一致性、loader 可用。"""
from acs_triage import loaders
from acs_triage.schemas import Question


def test_rules_version_matches_doc():
    assert loaders.rules_version() == loaders.doc_rules_version()


def test_red_flag_count_matches_doc():
    yaml_ids = sorted(rf["id"] for rf in loaders.load_clinical_rules()["red_flags"])
    assert yaml_ids == loaders.doc_red_flag_ids()
    assert len(yaml_ids) == 6


def test_question_bank_loads_and_is_consistent():
    qs = loaders.questions()
    assert all(isinstance(q, Question) for q in qs)
    slots = loaders.slot_defs()
    for q in qs:
        assert q.slot_id in slots, q.id
        if q.choices:
            assert set(q.choices) <= set(slots[q.slot_id]["choices"]), q.id
    assert loaders.load_question_bank()["rules_version_required"] <= loaders.rules_version()


def test_scenarios_reference_known_questions_and_slots():
    qids = set(loaders.question_by_id())
    slots = loaders.slot_defs()
    scs = loaders.all_scenarios()
    assert len(scs) == 38
    for sc in scs:
        assert sc["truth_tier"] in (0, 1, 2, 3, 4, 9)
        for qid in sc.get("decisive_questions", []):
            assert qid in qids, (sc["id"], qid)
        for k, v in sc.get("hidden_slots", {}).items():
            assert k in slots, (sc["id"], k)
            ch = slots[k].get("choices")
            if ch and v is not None:
                assert v in ch, (sc["id"], k, v)
        for var in sc.get("boundary_variants", []):
            for k, v in var["override"].items():
                assert k in slots, (sc["id"], k)
                ch = slots[k].get("choices")
                if ch and v is not None:
                    assert v in ch, (sc["id"], k, v)


def test_scripts_cover_all_pathway_ids():
    rules = loaders.load_clinical_rules()
    scripts = loaders.load_scripts()["scripts"]
    for key, pw in rules["pathways"].items():
        assert pw["script"] in scripts, (key, pw["script"])
        if pw.get("safety_net"):
            assert pw["safety_net"] in scripts


def test_derived_values_cleared_when_source_changes():
    """D-40：來源 slot 改變（含變體 reset）時，由它衍生的值一併清除；明確回答過的值不受影響。"""
    from acs_triage.rules import SlotState
    s = SlotState({"symptom_character": "none"})
    assert s.get("ongoing_now") is False                     # 否認胸部症狀 → 衍生「現在沒在發作」
    s.set("symptom_character", None, source="reset_for_variant")
    assert s.get("ongoing_now") is None                      # 來源清掉 → 衍生值一併清掉，必須再問
    s = SlotState({"symptom_character": "none"})
    s.set("ongoing_now", False, source="turn1", asked_by="Q-ONGOING-01")
    s.set("symptom_character", "pressure", source="turn2")
    assert s.get("ongoing_now") is False                     # 明確回答過的不清
