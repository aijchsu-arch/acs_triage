"""把情境檔展開成 hidden case sheets（BLUEPRINT §6.1）。

每個 case：
- id、scenario_id、opening_zh
- truth: {tier, hard_stop, rf}  —— e2e 的期望（base 用 truth_*；變體用 expect）
- slots: 病人「知道」的全部事實 = extract(opening) ∪ hidden_slots ∪ override
- reset_slots: 變體 override 的 key —— runner 初始狀態要把它們設回未知，讓資訊只能靠問出來
- 變體可帶自己的 opening_zh（D-35）：開場白與變體事實矛盾時使用；該變體的事實改由 extract(變體開場白) 起算
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


def _complete(slots: dict[str, Any]) -> dict[str, Any]:
    """Sheet 補全：合併篩檢題（Q-14f）的答案由三個底層事實推得；D-54：新欄位 episode_frequency_increased 情境檔沒寫 → 沒有
    （舊情境都是在這個欄位存在前寫的；不補的話模擬病人答不知道，gate 卡住變 T9）。"""
    slots.setdefault("episode_frequency_increased", False)
    if slots.get("consult_screen_positive") is None:
        vals = [slots.get(k) for k in ("palpitations", "postural_dizziness", "pending_abnormal_test")]
        if any(v is True for v in vals):
            slots["consult_screen_positive"] = True
        elif all(v is False for v in vals):
            slots["consult_screen_positive"] = False
    return slots


def _decisive_fields(slots: dict[str, Any]) -> dict[str, list[str]]:
    c = classify(slots)
    return {"decisive_questions": list(c), "escalating_questions": [q for q, d in c.items() if "up" in d]}


def _base_slots(sc: dict[str, Any], opening: str) -> dict[str, Any]:
    base = extract(opening)
    if base.pop("reproducible_mechanical_mentioned", None):     # D-57：開場白說的胸壁痛仍是病人知道的事實（truth 不變），通話中靠 Q-REPRO-01 問出
        base["reproducible_mechanical"] = True
    for k, v in sc.get("hidden_slots", {}).items():
        if v is not None:
            base[k] = v
    return _complete(base)


def expand_scenario(sc: dict[str, Any]) -> list[Case]:
    base = _base_slots(sc, sc["opening_zh"])
    persona = sc.get("persona", "normal")
    module = sc.get("module", sc.get("_file", ""))
    cases = [Case(id=sc["id"], scenario_id=sc["id"], opening_zh=sc["opening_zh"],
                  truth_tier=sc["truth_tier"], truth_hard_stop=sc["truth_hard_stop"],
                  truth_rf=sc.get("reviewer_rf"), slots=dict(base), persona=persona, module=module,
                  **_decisive_fields(base))]
    for i, var in enumerate(sc.get("boundary_variants", [])):
        exp = var["expect"]
        opening = var.get("opening_zh", sc["opening_zh"])
        slots = dict(base) if opening == sc["opening_zh"] else _base_slots(sc, opening)
        slots.update(var["override"])
        if any(k in var["override"] for k in ("palpitations", "postural_dizziness", "pending_abnormal_test")):
            slots.pop("consult_screen_positive", None)
        slots = _complete(slots)
        cases.append(Case(id=f"{sc['id']}#{i}", scenario_id=sc["id"], opening_zh=opening,
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
