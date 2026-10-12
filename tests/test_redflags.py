"""RF-01～RF-06：每條至少 3 個正例、3 個含否定詞的反例（文字 → extractor → engine）。"""
import pytest

from helpers import decide_text

POS = {
    "RF-01": ["胸口一陣壓迫感，站起來時差點昏倒。", "胸口悶悶的，而且眼前發黑快要暈倒。", "下顎和左肩沉重，剛才差點昏過去。"],
    "RF-02": ["我現在坐著也會喘。", "什麼都沒做就很喘，休息也喘。", "坐著不動也喘，可能是太緊張。"],
    "RF-03": ["胸口現在還在痛。", "胸口壓迫感從剛才到現在都還沒好。", "下顎沉重不適一直持續到現在。"],
    "RF-04": ["喘到一句話講不完。", "我先生喘到說不完一句話。", "嘴唇發紫而且很喘。"],
    "RF-05": ["剛才胸口悶然後昏倒了。", "他失去意識大概一分鐘。", "胸口痛完就昏過去了。"],
    "RF-06": ["胸口被壓住的感覺，而且冒冷汗。", "胸悶合併全身冒汗。", "上腹悶痛又流冷汗。"],
}
NEG = {
    "RF-01": ["胸口一陣壓迫感，但沒有昏倒也沒有頭暈。", "胸悶，沒有快昏倒的感覺。", "胸口悶，不會暈。"],
    "RF-02": ["走路會喘，坐著不會喘。", "做家事比較會喘，休息時不會。", "坐著不喘，只有爬樓梯才喘。"],
    "RF-03": ["胸口剛才悶了十分鐘，現在已經好了。", "胸口壓迫感休息後就好了，現在沒事。", "下顎沉重感自己好了。"],
    "RF-04": ["有點喘，但講話還可以。", "走路會喘，不會喘到講不完話。", "喘，可是可以講完一句話。"],
    "RF-05": ["差點昏倒，但沒有真的昏倒。", "有點頭暈，沒有昏過去。", "快要暈倒的感覺，沒有失去意識。"],
    "RF-06": ["胸口悶，沒有冒汗。", "胸口壓迫感，也沒有冷汗。", "胸悶但沒冒汗。"],
}


@pytest.mark.parametrize("rf", sorted(POS))
def test_positive_examples_trigger_hard_stop(engine, rf):
    assert len(POS[rf]) >= 3
    for text in POS[rf]:
        d = decide_text(engine, text)
        assert d.hard_stop and rf in d.rf_hits, (rf, text, d.rf_hits)


@pytest.mark.parametrize("rf", sorted(NEG))
def test_negated_examples_do_not_trigger(engine, rf):
    assert len(NEG[rf]) >= 3
    for text in NEG[rf]:
        d = decide_text(engine, text)
        assert rf not in d.rf_hits, (rf, text, d.rf_hits)


def test_rf02_anxiety_attribution_does_not_downgrade(engine):
    d = decide_text(engine, "坐著也會喘，不過我想可能是我太焦慮了。")
    assert d.hard_stop and "RF-02" in d.rf_hits
