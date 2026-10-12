"""把情境檔展開成 hidden case sheets（BLUEPRINT §6.1）。

每個 case：
- id、scenario_id、opening_zh
- truth: {tier, hard_stop, rf}  —— e2e 的期望（base 用 truth_*；變體用 expect）
- slots: 病人「知道」的全部事實 = extract(opening) ∪ hidden_slots ∪ override
- reset_slots: 變體 override 的 key —— runner 初始狀態要把它們設回未知，讓資訊只能靠問出來
- persona: normal | vague
- decisive_questions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acs_triage import loaders
from acs_triage.extract import extract


@dataclass
class Case:
    id: str
    scenario_id: str
    opening_zh: str
    truth_tier: int | None
    truth_hard_stop: bool
    truth_rf: str | None
    slots: dict[str, Any]
    reset_slots: list[str] = field(default_factory=list)
    persona: str = "normal"
    decisive_questions: list[str] = field(default_factory=list)
    is_variant: bool = False
    note: str | None = None
    module: str = ""


def expand_scenario(sc: dict[str, Any]) -> list[Case]:
    base = extract(sc["opening_zh"])
    for k, v in sc.get("hidden_slots", {}).items():
        if v is not None:
            base[k] = v
    persona = sc.get("persona", "normal")
    module = sc.get("module", sc.get("_file", ""))
    cases = [Case(id=sc["id"], scenario_id=sc["id"], opening_zh=sc["opening_zh"],
                  truth_tier=sc["truth_tier"], truth_hard_stop=sc["truth_hard_stop"],
                  truth_rf=sc.get("reviewer_rf"), slots=dict(base), persona=persona,
                  decisive_questions=list(sc.get("decisive_questions", [])), module=module)]
    for i, var in enumerate(sc.get("boundary_variants", [])):
        exp = var["expect"]
        slots = dict(base)
        slots.update(var["override"])
        cases.append(Case(id=f"{sc['id']}#{i}", scenario_id=sc["id"], opening_zh=sc["opening_zh"],
                          truth_tier=exp.get("tier"), truth_hard_stop=bool(exp.get("hard_stop", False)),
                          truth_rf=exp.get("rf"), slots=slots, reset_slots=list(var["override"].keys()),
                          persona="normal", decisive_questions=list(sc.get("decisive_questions", [])),
                          is_variant=True, note=var.get("note"), module=module))
    return cases


def all_cases() -> list[Case]:
    out: list[Case] = []
    for sc in loaders.all_scenarios():
        out.extend(expand_scenario(sc))
    return out
