"""sim/stt_eval.py 的純函式與計分流程測試（D-48）。不需音檔、不需 ASR 環境（mlx-whisper／opencc）。"""
from __future__ import annotations

import json

import pytest

from acs_triage.loaders import question_by_id
from sim import stt_eval as se


# ---------------------------------------------------------------- CER
def test_levenshtein_basics():
    assert se.levenshtein("", "") == 0
    assert se.levenshtein("abc", "abc") == 0
    assert se.levenshtein("", "abc") == 3
    assert se.levenshtein("abc", "") == 3
    assert se.levenshtein("kitten", "sitting") == 3
    assert se.levenshtein("沒有冒冷汗", "有冒冷汗") == 1          # 刪一字
    assert se.levenshtein("沒有冒冷汗", "沒有冒冷汗了") == 1       # 插一字
    assert se.levenshtein("沒有冒冷汗", "没有冒冷汗") == 1          # 換一字（未正規化時繁簡算錯）


def test_cer_values():
    assert se.cer("沒有冒冷汗", "沒有冒冷汗") == 0.0
    assert se.cer("沒有冒冷汗", "沒有冒冷旱") == pytest.approx(0.2)
    assert se.cer("abcd", "") == 1.0
    assert se.cer("ab", "abxxxx") == pytest.approx(2.0)            # 插入多時可超過 1
    assert se.cer("", "") == 0.0
    assert se.cer("", "x") == 1.0
    assert se.edit_stats("沒有", "有") == (1, 2)


def test_strip_punct():
    assert se.strip_punct("沒有，那時候 沒有冒冷汗。") == "沒有那時候沒有冒冷汗"
    assert se.strip_punct("沒有耶﹑不會…想?") == "沒有耶不會想"
    assert se.strip_punct("a, B-1") == "aB1"


# ---------------------------------------------------------------- 極性
@pytest.mark.parametrize("text,expect", [
    ("沒有，那時候沒有冒冷汗。", "neg"),
    ("沒有耶，不會想昏倒，眼前也沒有發黑。", "neg"),
    ("不會耶，我躺平睡都還好", "neg"),
    ("不是，是壓著的感覺", "neg"),
    ("還沒完全好", "neg"),
    ("沒什麼特別的", "neg"),
    ("嗯，沒有耶", "neg"),                                   # 句首語助詞
    ("喘的話倒是沒有，不管走路還是做家事都不會喘", "neg"),    # 否定詞不在句首
    ("有，現在胸口還是悶悶的", "pos"),
    ("會耶，躺平比較喘，要墊高枕頭", "pos"),
    ("是昨天，差不多昨天就好了", "pos"),
    ("還在悶", "pos"),
    ("對，休息的時候會悶是最近才開始的，以前不會這樣", "pos"),
    ("有，不過沒有冒汗", "pos"),                              # 肯定開頭優先，後面的否定不翻轉
    ("呃，有耶，最近有停過一陣子沒吃", "pos"),
    ("這個我不太確定耶，記不太清楚了", "unk"),                  # 非否定片語已遮罩
    ("我覺得胸口不太舒服", "unk"),
    ("其實現在坐著休息的時候也會喘耶", "unk"),
    ("", "unk"),
    ("，。…", "unk"),
])
def test_polarity(text, expect):
    assert se.polarity(text) == expect


def test_polarity_same_for_traditional_and_simplified():
    for trad, simp in [("沒有，不會", "没有，不会"), ("對，會悶", "对，会悶"),
                       ("還沒好", "还没好"), ("還在痛", "还在痛"), ("沒什麼症狀", "没什么症状")]:
        assert se.polarity(trad) == se.polarity(simp)


def test_polarity_does_not_depend_on_punctuation():
    """Whisper 有時完全不輸出標點；不能因此把同一句判成不同極性。"""
    ref = "嗯，現在胸口還是有一點壓壓的感覺，還沒完全好。"
    hyp = "现在胸口还是有一点压压的感觉还没完全好"
    assert se.polarity(ref) == se.polarity(hyp) == "neg"
    assert not se.polarity_flip(ref, hyp)


def test_polarity_flip_and_direction():
    # 紅旗題「有」被聽成「沒有」：非否定 → 否定
    assert se.polarity_flip("有，現在胸口還是悶悶的", "沒有，現在胸口還是悶悶的")
    assert se.flip_direction("有，現在胸口還是悶悶的", "沒有，現在胸口還是悶悶的") == "neg_gained"
    # 「沒有」被聽成「有」：否定 → 非否定
    assert se.polarity_flip("沒有冒冷汗", "有冒冷汗")
    assert se.flip_direction("沒有冒冷汗", "有冒冷汗") == "neg_lost"
    # 否定詞被聽成其他字（沒有 → 沒來）仍含「沒」，不算翻轉；繁簡差異不算翻轉
    assert not se.polarity_flip("沒有冒冷汗", "沒來冒冷汗")
    assert not se.polarity_flip("沒有冒冷汗", "没有冒冷汗")
    assert se.flip_direction("沒有冒冷汗", "没有冒冷汗") is None
    # 肯定 → 無法判定（「有」被吞掉）不算翻轉
    assert not se.polarity_flip("有，悶悶的", "悶悶的")


def test_lead_polarity_and_flip_kind():
    assert se.lead_polarity("呃，有耶") == "pos"
    assert se.lead_polarity("沒有，那時候") == "neg"
    assert se.lead_polarity("現在胸口還是悶悶的，還沒好") is None            # 否定詞不在句首
    k = lambda a, b: se.flip_kind(se.lead_polarity(a), se.lead_polarity(b))
    assert k("有，現在胸口還是悶悶的", "沒有，現在胸口還是悶悶的") == "inversion"        # 明確 yes/no 互換
    assert k("沒有冒冷汗", "有冒冷汗") == "inversion"
    # 句首「有」被吞掉、剩下的句子含「還沒」：整句否定判定翻轉，但不是明確互換
    ref, hyp = "有，現在胸口還是悶悶的，還沒好。", "現在胸口還是悶悶的,還沒好。"
    assert se.polarity_flip(ref, hyp) and k(ref, hyp) == "lead_lost"
    # 「這個…沒有特別去算」被聽成「有個…沒有特別去算」：句首多出肯定詞
    ref, hyp = "這個我也說不準耶，沒有特別去算多久了。", "有個我也說不准你,沒有特別去算多久了。"
    assert se.polarity_flip(ref, hyp) and k(ref, hyp) == "lead_gained"
    # 句中否定詞被聽成別的字
    ref, hyp = "現在沒有在痛，現在沒咳就還好。", "現在的有贊通,現在的科技還好。"
    assert se.polarity_flip(ref, hyp) and k(ref, hyp) == "inner"


# 詞表（繁體）與對應的簡體寫法：Whisper 不加提示時常輸出簡體，遮罩與詞表必須兩種字形都命中
_NON_NEG_SIMPLIFIED = ["不舒服", "不太舒服", "不适", "说不上来", "不知道", "不确定", "不太确定", "不清楚", "不太清楚", "记不清楚",
                       "记不太清楚", "不太对", "不一样", "不规则", "不正常", "不动", "不过", "不管", "不然", "没关系"]


def test_non_negation_phrases_masked_in_both_scripts():
    assert len(_NON_NEG_SIMPLIFIED) == len(se.NON_NEGATION)
    for trad, simp in zip(se.NON_NEGATION, _NON_NEG_SIMPLIFIED):
        assert se.polarity("我覺得" + trad + "耶") == "unk", trad
        assert se.polarity("我觉得" + simp + "耶") == "unk", simp


def test_negation_and_positive_tokens_same_in_both_scripts():
    pairs = [("沒有", "没有"), ("沒什麼", "没什么"), ("還沒", "还没"), ("不會", "不会"), ("不是", "不是"), ("不", "不")]
    for trad, simp in pairs:
        assert se.polarity(trad + "症狀") == se.polarity(simp + "症状") == "neg"
    for trad, simp in [("有", "有"), ("會", "会"), ("是", "是"), ("還在", "还在"), ("對", "对")]:
        assert se.polarity(trad + "，不過沒有冒汗") == se.polarity(simp + "，不过没有冒汗") == "pos"


# ---------------------------------------------------------------- AUC
def test_auc_known_values():
    assert se.auc([0.1, 0.4, 0.35, 0.8], [False, False, True, True]) == pytest.approx(0.75)   # 經典範例
    assert se.auc([1, 2, 3, 4], [False, False, True, True]) == 1.0
    assert se.auc([4, 3, 2, 1], [False, False, True, True]) == 0.0
    assert se.auc([1, 1, 1, 1], [False, True, False, True]) == 0.5
    assert se.auc([1, 1, 2], [False, True, True]) == pytest.approx(0.75)                     # 同分算 0.5
    assert se.auc([1, 2, 3], [True, True, True]) is None
    assert se.auc([1, 2, 3], [False, False, False]) is None
    assert se.auc([], []) is None


def test_auc_matches_bruteforce():
    import random
    rng = random.Random(7)
    scores = [round(rng.random(), 1) for _ in range(40)]          # 故意讓同分很多
    labels = [rng.random() < 0.4 for _ in scores]
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    brute = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))
    assert se.auc(scores, labels) == pytest.approx(brute)


def test_low_confidence_auc_direction():
    # 錯誤的句子信心較低 → 越低越可能錯 → AUC 接近 1
    assert se.low_confidence_auc([0.4, 0.5, 0.9, 0.95], [True, True, False, False]) == 1.0
    assert se.low_confidence_auc([0.9, 0.95, 0.4, 0.5], [True, True, False, False]) == 0.0


# ---------------------------------------------------------------- 門檻
def test_threshold_stats():
    vals = [0.5, 0.8, 0.95, 0.99]
    err = [True, True, False, False]
    flip = [True, False, False, False]
    s = se.threshold_stats(vals, [0.9] * 4, err, flip)
    assert (s["n_reask"], s["reask_rate"]) == (2, 0.5)
    assert (s["n_error_caught"], s["error_caught"], s["n_flip_caught"], s["flip_caught"]) == (2, 1.0, 1, 1.0)
    assert s["precision"] == 1.0
    s = se.threshold_stats(vals, [0.6] * 4, err, flip)
    assert s["error_caught"] == 0.5 and s["flip_caught"] == 1.0
    # 嚴格小於：剛好等於門檻不重問（同 runner 的 conf < thr）
    assert se.threshold_stats([0.9], [0.9], [True], [True])["n_reask"] == 0
    # 逐句不同門檻（系統政策：關鍵題 0.9、其他 0.75）
    s = se.threshold_stats([0.8, 0.8], [0.9, 0.75], [True, True], [False, False])
    assert s["n_reask"] == 1 and s["n_error_caught"] == 1
    # 沒有錯誤／沒有翻轉時比例為 None，不除以零
    s = se.threshold_stats([0.5], [0.9], [False], [False])
    assert s["error_caught"] is None and s["flip_caught"] is None and s["precision"] == 0.0


def test_threshold_table_has_required_thresholds():
    t = se.threshold_table([0.5, 0.99], [True, False], [False, False])
    assert [r["threshold"] for r in t] == [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
    assert t[0]["n_reask"] == 0 and t[-1]["n_reask"] == 1


def test_confidence_features_skip_punctuation_tokens():
    f = se.confidence_features([{"avg_logprob": -0.2}, {"avg_logprob": -0.4}],
                               [["沒有", 0.9], ["耶,", 0.7], ["﹑", 0.1], ["。", 0.2]])
    assert f["min_word_prob"] == 0.7                       # 純標點 token 不納入
    assert f["mean_word_prob"] == pytest.approx(0.8)
    assert f["mean_avg_logprob"] == pytest.approx(-0.3)
    empty = se.confidence_features([], [])
    assert empty["min_word_prob"] == 0.0 and empty["mean_avg_logprob"] == se.MISSING_LOGPROB


# ---------------------------------------------------------------- utterance 清單與計分流程
def _transcripts():
    return [
        {"case_id": "C1", "opening_zh": "胸口悶。", "turns": [
            {"q": "Q-DIAPH-01", "value": False, "utterance_zh": "沒有冒冷汗。"},
            {"q": "Q-CHARACTER-01", "value": "pressure", "utterance_zh": "像被壓住。"},
            {"q": "Q-NTG-01", "value": False, "utterance_zh": "沒有。"}]},
        {"case_id": "C2", "opening_zh": "胸口悶。", "turns": [
            {"q": "Q-NTG-01", "value": False, "utterance_zh": "沒有冒冷汗。"},      # 與 C1 紅旗題同字句
            {"q": "Q-DIAPH-01", "value": True, "utterance_zh": "有，冒冷汗。"}]},
    ]


def test_build_utterances_dedupes_and_keeps_sources():
    utts = se.build_utterances(_transcripts(), question_by_id(), {"Q-CHARACTER-01", "Q-REST-02"})
    assert [u["text"] for u in utts] == ["胸口悶。", "沒有冒冷汗。", "像被壓住。", "沒有。", "有，冒冷汗。"]
    assert [u["id"] for u in utts] == ["u0001", "u0002", "u0003", "u0004", "u0005"]
    by = {u["text"]: u for u in utts}
    assert len(by["胸口悶。"]["sources"]) == 2 and by["胸口悶。"]["qtype"] == "opening"
    assert len(by["沒有冒冷汗。"]["sources"]) == 2
    assert by["沒有冒冷汗。"]["qtype"] == "redflag"           # 同句出現在紅旗題與其他題 → 取最嚴重
    assert by["像被壓住。"]["qtype"] == "critical"
    assert by["像被壓住。"]["sources"][0] == {"case_id": "C1", "kind": "answer", "turn": 2, "q": "Q-CHARACTER-01",
                                                  "slot_id": "symptom_character", "redflag": False, "critical": True,
                                                  "value": "pressure"}
    assert by["沒有。"]["qtype"] == "other"
    assert by["有，冒冷汗。"]["qtype"] == "redflag"


def test_critical_questions_come_from_rules_config():
    assert {"Q-CHARACTER-01", "Q-REST-02"} <= se.critical_question_ids()


def _rec(u, cond, hyp, probs, lp=-0.2, hyp_tw=None):
    norm = lambda t: "".join(ch for ch in t if ch.isalnum())
    return {"id": u["id"], "voice": "Meijia", "condition": cond, "ref": u["text"], "hyp": hyp,
            "hyp_tw": hyp if hyp_tw is None else hyp_tw,
            "ref_norm": norm(u["text"]), "hyp_norm": norm(hyp),
            "segments": [{"avg_logprob": lp, "no_speech_prob": 0.0, "compression_ratio": 1.0}],
            "words": [[ch, p] for ch, p in zip(norm(hyp), probs)], "elapsed_s": 1.0}


def _asr_doc(utts):
    out = []
    for u in utts:
        out.append(_rec(u, "clean", u["text"], [0.99] * 40))
    # phone：紅旗題「有，冒冷汗。」被聽成「沒有冒冷汗。」（翻轉），且最低字機率低；其餘照舊
    for u in utts:
        if u["text"] == "有，冒冷汗。":
            out.append(_rec(u, "phone", "沒有冒冷汗。", [0.6] + [0.95] * 40, lp=-0.8))
        else:
            out.append(_rec(u, "phone", u["text"], [0.99] * 40))
    return {"meta": {"model": "fake", "language": "zh", "source": "test", "sessions": []}, "results": out}


def _utt(uid, text, qtype="redflag", q="Q-DIAPH-01", slot="diaphoresis"):
    return {"id": uid, "text": text, "qtype": qtype,
            "sources": [{"case_id": "C", "kind": "answer", "turn": 1, "q": q, "slot_id": slot,
                         "redflag": qtype == "redflag", "critical": qtype == "critical", "value": None}]}


def _row(utt, hyp, hyp_tw=None, probs=None):
    asr = {"meta": {}, "results": [_rec(utt, "phone", hyp, probs or [0.99] * 40, hyp_tw=hyp_tw)]}
    return se.make_rows(asr, [utt])[0]


def test_make_rows_and_analyze_end_to_end():
    utts = se.build_utterances(_transcripts(), question_by_id(), {"Q-CHARACTER-01", "Q-REST-02"})
    rows = se.make_rows(_asr_doc(utts), utts)
    assert len(rows) == 10
    s = se.analyze(rows, 0.9, 0.75)
    assert s["conditions"] == ["clean", "phone"] and s["n_utterances"] == 5
    assert s["cer"]["by_condition"]["clean"]["cer"] == 0.0
    # phone：只有一句有字錯：ref「有冒冷汗」4 字、hyp「沒有冒冷汗」5 字，編輯距離 1
    ph = s["cer"]["by_condition"]["phone"]
    assert ph["edits"] == 1 and ph["ref_chars"] == sum(len(r["ref_norm"]) for r in rows if r["condition"] == "phone")
    # 極性：phone 一句翻轉，屬紅旗題，方向 neg_gained；clean 無翻轉
    assert s["polarity"]["by_condition"]["clean"]["n_flip"] == 0
    assert s["polarity"]["by_condition"]["phone"]["n_flip"] == 1
    assert s["polarity"]["by_condition_qtype"]["phone"]["redflag"]["n_flip"] == 1
    assert [(f["condition"], f["flip_dir"], f["qtype"]) for f in s["polarity"]["flips"]] == [("phone", "neg_gained", "redflag")]
    assert s["polarity"]["by_condition"]["phone"]["n_inversion"] == 1
    assert s["polarity"]["by_condition"]["phone"]["flip_kinds"] == {"inversion": 1, "lead_lost": 0, "lead_gained": 0, "inner": 0}
    assert s["polarity"]["flips"][0]["flip_kind"] == "inversion"
    assert s["polarity"]["by_condition"]["clean"]["n_lead_ref_pos"] == 1
    # 抽取器：「有，冒冷汗。」→「沒有冒冷汗。」diaphoresis 由 True 變 False
    assert s["extractor"]["by_condition"]["clean"]["n_diff"] == 0
    assert s["extractor"]["by_condition"]["phone"]["n_diff"] == 1
    # 校準：phone 的翻轉句 min_word_prob=0.6，被 0.75／0.9 門檻抓到；其餘句 0.99 不重問
    tab = {t["threshold"]: t for t in s["calibration"]["by_condition"]["phone"]["threshold_table"]["min_word_prob"]}
    assert tab[0.75]["n_reask"] == 1 and tab[0.75]["flip_caught"] == 1.0
    assert tab[0.5]["n_reask"] == 0 and tab[0.5]["flip_caught"] == 0.0
    pol = s["calibration"]["policy"]["phone"]["min_word_prob"]
    assert pol["n_reask"] == 1 and pol["n_flip_caught"] == 1 and pol["subgroups"]["gated"]["n_reask"] == 1
    assert s["calibration"]["by_condition"]["phone"]["auc_flip"]["min_word_prob"] == 1.0
    assert s["calibration"]["by_condition"]["ALL"]["n_flip"] == 1


def test_cer_capped_and_loop_detection():
    rows = [{"edits": 5, "ref_len": 10, "cer": 0.5, "max_compression_ratio": 1.0},
            {"edits": 300, "ref_len": 20, "cer": 15.0, "max_compression_ratio": 36.8}]      # 重複迴圈：插入遠超參考長度
    c = se.cer_summary(rows)
    assert c["cer"] == pytest.approx(305 / 30)
    assert c["cer_capped"] == pytest.approx(25 / 30)
    assert c["n_loops"] == 1


def test_report_numbers_reproducible_from_rows_json():
    """報告 JSON 內含 rows；經 JSON 往返後重算的彙總與原值逐項相同。"""
    utts = se.build_utterances(_transcripts(), question_by_id(), {"Q-CHARACTER-01", "Q-REST-02"})
    rows = se.make_rows(_asr_doc(utts), utts)
    s1 = se.analyze(rows, 0.9, 0.75)
    s2 = se.analyze(json.loads(json.dumps(rows, ensure_ascii=False)), 0.9, 0.75)
    assert json.dumps(s1, sort_keys=True) == json.dumps(s2, sort_keys=True)


def test_render_md_has_all_sections():
    utts = se.build_utterances(_transcripts(), question_by_id(), {"Q-CHARACTER-01", "Q-REST-02"})
    s = se.analyze(se.make_rows(_asr_doc(utts), utts), 0.9, 0.75)
    md = se.render_md(s, {"model": "fake", "language": "zh", "source": "test", "sessions": [{"wall_s": 3.0}]}, "stt_whisper_x")
    assert "樂觀上限" in md.split("## 0.")[0]               # 限制寫在最前面
    for head in ("## 1. 字錯率", "## 2. 極性翻轉", "## 3. 抽取器受 ASR 影響", "## 4. 信心校準"):
        assert head in md
    assert "★ 0.75" in md and "★ 0.90" in md


def test_make_rows_rejects_changed_utterance_list():
    utts = se.build_utterances(_transcripts(), question_by_id(), {"Q-CHARACTER-01"})
    asr = _asr_doc(utts)
    utts[0]["text"] = "被改過"
    with pytest.raises(ValueError):
        se.make_rows(asr, utts)


# ---------------------------------------------------------------- 變異測試補強（獨立驗收指出的存活變異）
def test_polarity_and_extractor_read_hyp_tw_not_raw_hyp():
    """hyp = Whisper 原文，hyp_tw = 繁體化後的轉寫（STT adapter 的輸出）。極性與抽取必須看 hyp_tw；原文只用在「未轉換」對照欄。"""
    u = _utt("u0001", "沒有冒冷汗。")
    # 原文缺否定詞、hyp_tw 正確：不該判成翻轉或抽取差異；原文版的差異只出現在對照欄 ext_diff_raw
    row = _row(u, hyp="有冒冷汗。", hyp_tw="沒有冒冷汗。")
    assert row["pol_hyp"] == "neg" and row["lead_hyp"] == "neg"
    assert not row["flip"] and row["flip_kind"] is None and row["flip_dir"] is None
    assert not row["ext_diff"] and not row["ext_asked_diff"] and row["ext_diff_slots"] == []
    assert row["ext_diff_raw"]
    # 反向：原文正確、hyp_tw 缺否定詞 → 以 hyp_tw 為準
    row = _row(u, hyp="沒有冒冷汗。", hyp_tw="有冒冷汗。")
    assert row["pol_hyp"] == "pos" and row["flip"] and row["flip_kind"] == "inversion" and row["flip_dir"] == "neg_lost"
    assert row["ext_diff"] and row["ext_asked_diff"] and row["ext_diff_slots"] == ["diaphoresis"]
    assert not row["ext_diff_raw"]


def _prow(qtype, min_word_prob, mean_word_prob=0.95):
    return {"qtype": qtype, "min_word_prob": min_word_prob, "mean_word_prob": mean_word_prob, "error": True, "flip": False}


def test_policy_uses_critical_threshold_only_for_redflag_and_critical_questions():
    # 信心 0.8 介於 0.75 與 0.9 之間：紅旗題與關鍵題（門檻 0.9）要重問，其他與開場白（門檻 0.75）不重問
    p = se.policy_for([_prow("redflag", 0.8), _prow("critical", 0.8), _prow("other", 0.8), _prow("opening", 0.8)], 0.9, 0.75)["min_word_prob"]
    assert p["n_reask"] == 2
    assert (p["subgroups"]["gated"]["n"], p["subgroups"]["gated"]["n_reask"]) == (2, 2)
    assert (p["subgroups"]["other"]["n"], p["subgroups"]["other"]["n_reask"]) == (2, 0)
    # 高於 0.9 的紅旗題不重問；低於 0.75 的其他題重問
    p = se.policy_for([_prow("redflag", 0.95), _prow("critical", 0.95), _prow("other", 0.7), _prow("opening", 0.7)], 0.9, 0.75)["min_word_prob"]
    assert (p["subgroups"]["gated"]["n_reask"], p["subgroups"]["other"]["n_reask"]) == (0, 2)
    # mean_word_prob 用同一套分題型門檻
    p = se.policy_for([_prow("redflag", 0.99, 0.8), _prow("other", 0.99, 0.8)], 0.9, 0.75)["mean_word_prob"]
    assert (p["subgroups"]["gated"]["n_reask"], p["subgroups"]["other"]["n_reask"]) == (1, 0)


def test_score_passes_config_thresholds_to_policy(tmp_path):
    """score 子命令把 clinical_rules 的 0.9（critical）／0.75（其他）傳進政策模擬，且不能對調。"""
    import argparse
    from acs_triage.loaders import load_clinical_rules
    utts = se.build_utterances(_transcripts(), question_by_id(), {"Q-CHARACTER-01", "Q-REST-02"})
    (tmp_path / "asr.json").write_text(json.dumps(_asr_doc(utts), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "utts.json").write_text(json.dumps(utts, ensure_ascii=False), encoding="utf-8")
    se.cmd_score(argparse.Namespace(asr=str(tmp_path / "asr.json"), utterances=str(tmp_path / "utts.json"),
                                    out_dir=str(tmp_path), stem="t"))
    th = load_clinical_rules()["thresholds"]
    out = json.loads((tmp_path / "t.json").read_text(encoding="utf-8"))
    assert out["summary"]["calibration"]["policy_thresholds"] == {"critical": th["stt_min_confidence_critical"],
                                                                   "other": th["stt_min_confidence"]}
    assert th["stt_min_confidence_critical"] > th["stt_min_confidence"]
    assert (tmp_path / "t.md").read_text(encoding="utf-8").startswith("# STT 評估")


def test_error_label_includes_polarity_flip_even_when_cer_is_small():
    u = _utt("u0001", "有，現在胸口還是悶悶的，還沒好。", q="Q-ONGOING-01", slot="ongoing_now")
    # 只少了句首的「有」：CER 1/13 < 0.1，但整句否定判定翻轉 → 仍是錯誤
    row = _row(u, hyp="現在胸口還是悶悶的，還沒好。")
    assert row["cer"] <= se.CER_ERROR_THRESHOLD and row["flip"] and row["error"]
    # 字錯多、沒有翻轉 → 錯誤
    row = _row(u, hyp="有，現在胸口還是能懵著，已經好了。")
    assert row["cer"] > se.CER_ERROR_THRESHOLD and not row["flip"] and row["error"]
    # 完全正確 → 不是錯誤
    row = _row(u, hyp=u["text"])
    assert row["cer"] == 0.0 and not row["flip"] and not row["error"]
    # 字錯少、沒有翻轉 → 不是錯誤
    row = _row(u, hyp="有，現在胸口還是悶悶的，還沒壞。")
    assert 0 < row["cer"] <= se.CER_ERROR_THRESHOLD and not row["flip"] and not row["error"]
