"""規則路徑 Slot Extractor（Phase 0）：關鍵詞 + 否定詞處理，從一段中文 utterance 抽出 slot 值。

設計原則
- 永遠保守：抽不出就留 None，交給 Prompter 去問；不自行補完。
- 否定詞處理：正向命中前方（同子句、6 字內）出現否定詞 → 丟棄；另有各 slot 的明確否定樣式。
- 只在 38 個 benchmark 開場白與紅旗測試句上驗證；M3 起由模型路徑補強。
"""
from __future__ import annotations

import re
from typing import Any

from ..loaders import load_extraction_patterns

_NEG_WINDOW = 6


class RuleExtractor:
    def __init__(self) -> None:
        self.p = load_extraction_patterns()
        self.slots: dict[str, Any] = self.p["slots"]
        self._split = re.compile(self.p["clause_splitters"])
        self._neg_tokens = sorted(self.p["negation_tokens"], key=len, reverse=True)
        self._neg_re = re.compile("|".join(re.escape(t) for t in self._neg_tokens))
        self._mask_phrases = sorted(self.p["non_negation_phrases"], key=len, reverse=True)

    # ------------------------------------------------------------------ utils
    def _mask(self, text: str) -> str:
        for ph in self._mask_phrases:
            text = text.replace(ph, "□" * len(ph))
        return text

    def _clauses(self, text: str) -> list[tuple[int, int]]:
        spans, start = [], 0
        for m in self._split.finditer(text):
            if m.start() > start:
                spans.append((start, m.start()))
            start = m.end()
        if start < len(text):
            spans.append((start, len(text)))
        return spans

    def _clause_start(self, text: str, pos: int) -> int:
        for a, b in self._clauses(text):
            if a <= pos < b:
                return a
        return 0

    def _negated_before(self, masked: str, start: int) -> bool:
        cs = self._clause_start(masked, start)
        window = masked[max(cs, start - _NEG_WINDOW):start]
        return bool(self._neg_re.search(window))

    def _find_positive(self, text: str, masked: str, patterns: list[str]) -> bool:
        for pat in patterns:
            for m in re.finditer(pat, text):
                if not self._negated_before(masked, m.start()):
                    return True
        return False

    @staticmethod
    def _any(text: str, patterns: list[str]) -> bool:
        return any(re.search(p, text) for p in patterns)

    # ------------------------------------------------------------------ main
    def extract(self, text: str) -> dict[str, Any]:
        text = text.strip()
        masked = self._mask(text)
        out: dict[str, Any] = {}

        # --- 單純 positive/negative 型 slot ---
        for slot_id in ["presyncope", "syncope", "ongoing_now", "diaphoresis", "cant_finish_sentence",
                        "dyspnea_acute", "orthopnea_pnd", "edema", "onset_new", "rest_symptom",
                        "rest_symptom_first_time", "threshold_decreased", "ntg_use_increased",
                        "recurrence", "cad_history", "pci_history", "antiplatelet_interrupted",
                        "third_party_call", "patient_reachable", "palpitations", "postural_dizziness",
                        "new_medication_recent", "reproducible_mechanical", "cough_related",
                        "postprandial_relieved", "pending_abnormal_test", "drug_time_correlation"]:
            spec = self.slots.get(slot_id)
            if not spec:
                continue
            pos = self._find_positive(text, masked, spec.get("positive", []))
            neg = self._any(text, spec.get("negative", []))
            if slot_id in ("onset_new",):
                # 慢性標記優先於「開始」類弱標記；明確新發標記（第一次／以前沒有）優先於慢性
                strong_new = self._find_positive(text, masked, [p for p in spec["positive"]
                                                                if "開始" not in p])
                if strong_new:
                    out[slot_id] = True
                elif neg:
                    out[slot_id] = False
                elif pos:
                    out[slot_id] = True
                continue
            if neg and not pos:
                out[slot_id] = False
            elif pos and not neg:
                out[slot_id] = True
            elif pos and neg:
                # 兩者皆有：對紅旗類 slot 以正向為準（敏感度優先），其餘留 None
                if slot_id in ("presyncope", "syncope", "diaphoresis", "cant_finish_sentence"):
                    out[slot_id] = True
                elif slot_id in ("ongoing_now",):
                    out[slot_id] = None
                else:
                    out[slot_id] = None

        # syncope 與 presyncope 互斥修正：差點昏倒 ≠ 昏倒
        if out.get("presyncope") is True and out.get("syncope") is True:
            if not self._any(text, ["昏過去", "失去意識", "昏迷", "倒下去"]):
                out["syncope"] = None

        # --- symptom_character ---
        sc = self.slots["symptom_character"]
        char = None
        for item in sc["ordered_values"]:
            if self._find_positive(text, masked, item["patterns"]):
                char = item["value"]
                break
        if char is None and self._any(text, sc["none_patterns"]):
            char = "none"
        if char is not None:
            out["symptom_character"] = char
        chest_present = char not in (None, "none")

        # --- dyspnea_grade ---
        dg = self.slots["dyspnea_grade"]
        grade = None
        not_rest = self._any(text, dg.get("explicit_not_rest", []))
        for item in dg["ordered_values"]:
            if item["value"] == "rest" and not_rest:
                continue
            if self._find_positive(text, masked, item["patterns"]):
                grade = item["value"]
                break
        if grade is None and self._any(text, dg["none_patterns"]) and not re.search(r"(?<!不會)(?<!沒有)(?<!沒)喘", masked):
            grade = "none"
        if grade is not None:
            out["dyspnea_grade"] = grade
        if grade not in ("none",) and re.search(r"喘|呼吸困難|呼吸不順|吸不到氣", masked) and not self._any(text, dg["none_patterns"]):
            # 有提到喘但未分級 → 標記主訴，讓呼吸類題目進入提問
            out["dyspnea_complaint"] = True

        # --- threshold_decrease_timescale（僅 threshold_decreased 為 True 時） ---
        if out.get("threshold_decreased") is True:
            ts = self.slots["threshold_decrease_timescale"]
            for item in ts["ordered_values"]:
                if self._any(text, item["patterns"]):
                    out["threshold_decrease_timescale"] = item["value"]
                    break

        # --- pattern_unchanged_duration_months ---
        pu = self.slots["pattern_unchanged_duration_months"]
        if self._any(text, pu["uncertainty_phrases"]):
            pass  # 明確不確定 → 留 None
        else:
            stab_pos = None
            for ph in pu["stability_phrases"]:
                m = re.search(ph, text)
                if m:
                    stab_pos = m.start()
                    break
            if stab_pos is not None:
                months = None
                cs = self._clause_start(text, stab_pos)
                clause = text[cs:]
                clause = clause[: self._split.search(clause).start()] if self._split.search(clause) else clause
                for d in pu["duration_patterns"]:
                    if re.search(d["pattern"], clause):
                        months = d["months"]
                        break
                if months is None:
                    for d in pu["duration_patterns"]:
                        if re.search(d["pattern"], text):
                            months = d["months"]
                            break
                out["pattern_unchanged_duration_months"] = months if months is not None else 6
                if out.get("threshold_decreased") is None:
                    out["threshold_decreased"] = False

        # --- onset_weeks_ago（僅 onset_new True） ---
        if out.get("onset_new") is True:
            for d in self.slots["onset_weeks_ago"]["patterns"]:
                if re.search(d["pattern"], text):
                    out["onset_weeks_ago"] = d["weeks"]
                    break

        # --- last_episode_timing（僅胸部症狀存在） ---
        if chest_present:
            lt = self.slots["last_episode_timing"]
            today_hit = self._any(text, lt["today_markers"]) and not self._any(text, lt["today_negated"])
            if today_hit:
                out["last_episode_timing"] = "today"
            elif self._any(text, lt["yesterday_markers"]):
                out["last_episode_timing"] = "yesterday_within_24h"
            elif self._any(text, lt["over_24h_markers"]):
                out["last_episode_timing"] = "over_24h"

        # --- episode_duration_min ---
        for d in self.slots["episode_duration_min"]["patterns"]:
            if re.search(d["pattern"], text):
                out["episode_duration_min"] = d["minutes"]
                break

        # --- exertion_relation ---
        ex = self.slots["exertion_relation"]
        if chest_present:
            ex_neg = self._any(text, ex["exertion_negated"])
            ex_pos = self._find_positive(text, masked, ex["exertion_markers"]) and not ex_neg
            if ex_neg:
                out["exertion_relation"] = "unclear"
            elif ex_pos and out.get("rest_symptom") is True:
                out["exertion_relation"] = "both"
            elif ex_pos:
                out["exertion_relation"] = "exertion_only"
            elif out.get("rest_symptom") is True:
                out["exertion_relation"] = "rest_only"

        # --- recent_pci_months ---
        if out.get("pci_history") is True:
            for d in self.slots["recent_pci_months"]["patterns"]:
                if re.search(d["pattern"], text):
                    out["recent_pci_months"] = d["months"]
                    break

        # --- symptom_vs_pre_pci ---
        for item in self.slots["symptom_vs_pre_pci"]["ordered_values"]:
            if self._any(text, item["patterns"]):
                out["symptom_vs_pre_pci"] = item["value"]
                break

        # --- consult_topic（僅無症狀時） ---
        symptomatic = chest_present or (grade not in (None, "none")) or any(
            out.get(k) is True for k in ("palpitations", "presyncope", "syncope", "orthopnea_pnd",
                                         "postural_dizziness", "edema", "reproducible_mechanical",
                                         "cough_related", "postprandial_relieved", "dyspnea_acute",
                                         "ntg_use_increased", "ongoing_now"))
        if symptomatic:
            out["consult_topic"] = "symptom"
        else:
            for item in self.slots["consult_topic"]["ordered_values"]:
                if self._any(text, item["patterns"]):
                    out["consult_topic"] = item["value"]
                    break

        return out


_default: RuleExtractor | None = None


def extract(text: str) -> dict[str, Any]:
    global _default
    if _default is None:
        _default = RuleExtractor()
    return _default.extract(text)
