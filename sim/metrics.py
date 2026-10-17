"""指標（BLUEPRINT §6.3）。Tier 9 的處理：9 不是「更不急」，單獨計 abstention。"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .runner import RunResult


@dataclass
class Metrics:
    n_cases: int = 0
    n_scored: int = 0                      # truth_tier 非 None
    hard_stop_truth: int = 0
    hard_stop_hit: int = 0
    hard_stop_miss: list[str] = field(default_factory=list)
    hard_stop_false_alarm: list[str] = field(default_factory=list)
    hard_stop_latency_max: int = 0
    exact: int = 0
    under_triage: list[tuple[str, int, int]] = field(default_factory=list)   # (case, truth, pred)
    over_triage: list[tuple[str, int, int]] = field(default_factory=list)
    abstain_tp: int = 0   # truth 9, pred 9
    abstain_fp: list[tuple[str, int]] = field(default_factory=list)   # truth 0-4, pred 9
    abstain_fn: list[tuple[str, int]] = field(default_factory=list)   # truth 9, pred 0-4
    decisive_hit: int = 0
    decisive_total: int = 0
    escalating_hit: int = 0
    escalating_total: int = 0
    escalating_missed: list[tuple[str, str, int, str]] = field(default_factory=list)  # (case, qid, final tier, stop)
    escalating_missed_strict: list[tuple[str, str, int, str]] = field(default_factory=list)  # D-42：推導值不算已知
    questions: list[int] = field(default_factory=list)
    repeats: int = 0
    stop_reasons: Counter = field(default_factory=Counter)
    confusion: Counter = field(default_factory=Counter)   # (truth, pred)
    by_module: dict[str, Counter] = field(default_factory=dict)
    rf_mismatch: list[tuple[str, str, list[str]]] = field(default_factory=list)

    # ---- 衍生 ----
    @property
    def under_triage_rate(self) -> float:
        return len(self.under_triage) / self.n_scored if self.n_scored else 0.0

    @property
    def over_triage_rate(self) -> float:
        return len(self.over_triage) / self.n_scored if self.n_scored else 0.0

    @property
    def exact_rate(self) -> float:
        return self.exact / self.n_scored if self.n_scored else 0.0

    @property
    def hard_stop_miss_rate(self) -> float:
        return len(self.hard_stop_miss) / self.hard_stop_truth if self.hard_stop_truth else 0.0

    @property
    def decisive_recall(self) -> float:
        return self.decisive_hit / self.decisive_total if self.decisive_total else 1.0

    @property
    def escalating_recall(self) -> float:
        return self.escalating_hit / self.escalating_total if self.escalating_total else 1.0

    @property
    def escalating_recall_strict(self) -> float:
        return (self.escalating_total - len(self.escalating_missed_strict)) / self.escalating_total if self.escalating_total else 1.0

    @property
    def abstention_precision(self) -> float:
        d = self.abstain_tp + len(self.abstain_fp)
        return self.abstain_tp / d if d else 1.0

    @property
    def abstention_recall(self) -> float:
        d = self.abstain_tp + len(self.abstain_fn)
        return self.abstain_tp / d if d else 1.0

    @property
    def mean_questions(self) -> float:
        return sum(self.questions) / len(self.questions) if self.questions else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_cases": self.n_cases, "n_scored": self.n_scored,
            "hard_stop": {"truth": self.hard_stop_truth, "hit": self.hard_stop_hit, "miss": self.hard_stop_miss,
                          "miss_rate": self.hard_stop_miss_rate, "false_alarm": self.hard_stop_false_alarm,
                          "latency_max": self.hard_stop_latency_max},
            "exact_rate": self.exact_rate,
            "under_triage": {"rate": self.under_triage_rate, "cases": self.under_triage},
            "over_triage": {"rate": self.over_triage_rate, "cases": self.over_triage},
            "abstention": {"tp": self.abstain_tp, "fp": self.abstain_fp, "fn": self.abstain_fn,
                           "precision": self.abstention_precision, "recall": self.abstention_recall},
            "escalating_recall": self.escalating_recall,
            "escalating": {"hit": self.escalating_hit, "total": self.escalating_total, "missed": self.escalating_missed},
            "escalating_recall_strict": self.escalating_recall_strict,
            "escalating_missed_strict": self.escalating_missed_strict,
            "decisive_recall": self.decisive_recall,
            "questions_to_decision_mean": self.mean_questions,
            "gate_repeats": self.repeats,
            "stop_reasons": dict(self.stop_reasons),
            "confusion": {f"{t}->{p}": n for (t, p), n in sorted(self.confusion.items())},
            "rf_mismatch": self.rf_mismatch,
        }


def compute(results: list[RunResult]) -> Metrics:
    m = Metrics()
    for r in results:
        m.n_cases += 1
        m.stop_reasons[r.stop_reason] += 1
        m.questions.append(r.n_questions)
        m.repeats += r.n_repeats
        m.decisive_hit += r.decisive_asked_or_known
        m.decisive_total += r.decisive_total
        m.escalating_hit += r.escalating_asked_or_known
        m.escalating_total += r.escalating_total
        m.escalating_missed += [(r.case_id, q, r.final.tier, r.stop_reason) for q in r.escalating_missed]
        m.escalating_missed_strict += [(r.case_id, q, r.final.tier, r.stop_reason) for q in r.escalating_missed_strict]
        if r.truth_tier is None:
            continue
        m.n_scored += 1
        pred = r.final.tier
        truth = r.truth_tier
        m.confusion[(truth, pred)] += 1
        mod = m.by_module.setdefault(r.module, Counter())
        mod["n"] += 1
        if r.truth_hard_stop:
            m.hard_stop_truth += 1
            if r.final.hard_stop:
                m.hard_stop_hit += 1
                lat = r.hard_stop_latency or 0
                m.hard_stop_latency_max = max(m.hard_stop_latency_max, lat)
                # 開場白即 Hard stop 時，變體預期的 RF 可能尚未被問到（例如 RF-01 已停、RF-05 未問）→ 不算不一致
                if r.truth_rf and r.truth_rf not in r.final.rf_hits and (r.hard_stop_turn or 0) > 0:
                    m.rf_mismatch.append((r.case_id, r.truth_rf, r.final.rf_hits))
            else:
                m.hard_stop_miss.append(r.case_id)
        elif r.final.hard_stop:
            m.hard_stop_false_alarm.append(r.case_id)
        if pred == truth:
            m.exact += 1
            mod["exact"] += 1
        if truth == 9 and pred == 9:
            m.abstain_tp += 1
        elif truth != 9 and pred == 9:
            m.abstain_fp.append((r.case_id, truth))
            mod["abstain_fp"] += 1
        elif truth == 9 and pred != 9:
            m.abstain_fn.append((r.case_id, pred))
            mod["abstain_fn"] += 1
        elif pred > truth:
            m.under_triage.append((r.case_id, truth, pred))
            mod["under"] += 1
        elif pred < truth:
            m.over_triage.append((r.case_id, truth, pred))
            mod["over"] += 1
    return m
