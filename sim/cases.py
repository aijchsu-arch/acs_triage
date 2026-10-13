"""把情境檔展開成 hidden case sheets（BLUEPRINT §6.1）。

每個 case：
- id、scenario_id、opening_zh
- truth: {tier, hard_stop, rf}  —— e2e 的期望（base 用 truth_*；變體用 expect）
- slots: 病人「知道」的全部事實 = extract(opening) ∪ hidden_slots ∪ override
- reset_slots: 變體 override 的 key —— runner 初始狀態要把它們設回未知，讓資訊只能靠問出來
- persona: normal | vague
- decisive_questions：由 sim/decisive.py 依 case 的完整事實計算（答案會改變分流結果的題目），
  base 與每個變體各自計算；情境檔 YAML 的同名欄位只是 base 的紀錄，由 tests/test_decisive.py 確保一致。
- escalating_questions：decisive 中「某個答案會使結果更急」的子集（安全指標用，D-27）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acs_triage import loaders
from acs_triage.extract import extract

from .decisive import classify


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
    escalating_questions: list[str] = field(default_factory=list)
    is_variant: bool = False
    note: str | None = None
    module: str = ""


def _decisive_fields(slots: dict[str, Any]) -> dict[str, list[str]]:
    c = classify(slots)
    return {"decisive_questions": list(c), "escalating_questions": [q for q, d in c.items() if "up" in d]}


def expand_scenario(sc: dict[str, Any]) -> list[Case]:
    base = extract(sc["opening_zh"])
    for k, v in sc.get("hidden_slots", {}).items():
        if v is not None:
            base[k] = v
    persona = sc.get("persona", "normal")
    module = sc.get("module", sc.get("_file", ""))
    cases = [Case(id=sc["id"], scenario_id=sc["id"], opening_zh=sc["opening_zh"],
                  truth_tier=sc["truth_tier"], truth_hard_stop=sc["truth_hard_stop"],
                  truth_rf=sc.get("reviewer_rf"), slots=dict(base), persona=persona, module=module,
                  **_decisive_fields(base))]
    for i, var in enumerate(sc.get("boundary_variants", [])):
        exp = var["expect"]
        slots = dict(base)
        slots.update(var["override"])
        cases.append(Case(id=f"{sc['id']}#{i}", scenario_id=sc["id"], opening_zh=sc["opening_zh"],
                          truth_tier=exp.get("tier"), truth_hard_stop=bool(exp.get("hard_stop", False)),
                          truth_rf=exp.get("rf"), slots=slots, reset_slots=list(var["override"].keys()),
                          persona="normal", **_decisive_fields(slots),
                          is_variant=True, note=var.get("note"), module=module))
    return cases


def all_cases() -> list[Case]:
    out: list[Case] = []
    for sc in loaders.all_scenarios():
        out.extend(expand_scenario(sc))
    return out
