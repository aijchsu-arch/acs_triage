"""LLM 扮演病人（M2b，DECISIONS D-21／D-30／D-31）。

- 只看 hidden sheet（case.slots）；persona vague 時 sheet 只留紅旗題的事實，與 ScriptedPatient 的 vague 行為一致。
- 每題以 structured output 回傳 {utterance_zh, dont_know, answer}；answer 的型別／選項由題目的 answer_type 限定。
- 回傳的 value 直接進 runner（與 ScriptedPatient 同介面），不經 extractor：M2b 量的是「病人模型」的偏差，
  slot 抽取模型化是 M3。
- 每一題的答案都與 oracle（ScriptedPatient 無噪音時的答案）比對，偏差記在 self.deviations。
- 金鑰只讀 ACS_PATIENT_LLM_KEY，以 api_key= 明確傳入（D-31）；不讀 SDK 預設的金鑰環境變數。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from acs_triage.loaders import DATA_DIR, _load_yaml, questions, slot_defs
from acs_triage.schemas import Question

from .cases import Case
from .patient import _ZH_CHOICE, PatientReply, ScriptedPatient

KEY_ENV = "ACS_PATIENT_LLM_KEY"
DEFAULT_MODEL = "claude-opus-5-5"   # D-34：品質優先
DEFAULT_EFFORT = "medium"
_FALLBACK_BETA = "server-side-fallback-2026-07-01"   # Haiku 無 server-side fallback，只在其他模型帶


@dataclass
class Deviation:
    case_id: str
    question_id: str
    kind: str          # fabricated（sheet 不知道卻給答案）| contradicted（答案與 sheet 不同）| omitted（sheet 有答案卻說不知道）
    expected: Any
    got: Any
    utterance_zh: str
    confirm: bool = False   # D-50：複誦確認的回答（同樣與 sheet 比對，計入偏差與編造率）


def make_client() -> Any:
    import anthropic
    return anthropic.Anthropic(api_key=os.environ[KEY_ENV])


def _prompt_cfg() -> dict[str, Any]:
    return _load_yaml(DATA_DIR / "llm_patient.yaml")


def _render_value(v: Any) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str) and v in _ZH_CHOICE:
        return f"{v}（{_ZH_CHOICE[v]}）"
    return str(v)


def build_system(case: Case) -> str:
    cfg = _prompt_cfg()
    by_slot: dict[str, Question] = {}
    for q in questions():
        by_slot.setdefault(q.slot_id, q)
    lines = []
    for slot_id, v in sorted(case.slots.items()):
        if v is None:
            continue
        q = by_slot.get(slot_id)
        if case.persona == "vague" and q is not None and q.priority != "redflag":
            continue
        if q is None:
            lines.append(cfg["sheet_line_no_question_zh"].format(slot_id=slot_id, value=_render_value(v)))
        else:
            lines.append(cfg["sheet_line_zh"].format(slot_id=slot_id, script_zh=q.script_zh.strip(),
                                                     value=_render_value(v)))
    return cfg["system_zh"].format(opening_zh=case.opening_zh, sheet="\n".join(lines))


def answer_schema(q: Question) -> dict[str, Any]:
    if q.answer_type == "yes_no":
        ans: dict[str, Any] = {"type": "boolean"}
    elif q.answer_type == "choice":
        ans = {"type": "string", "enum": list(slot_defs()[q.slot_id]["choices"])}   # 用 slot 全集：題目 choices 可能是子集
    elif q.answer_type == "duration":
        ans = {"type": "number"}
    else:
        ans = {"type": "string"}
    return {"type": "object",
            "properties": {"utterance_zh": {"type": "string"}, "dont_know": {"type": "boolean"}, "answer": ans},
            "required": ["utterance_zh", "dont_know", "answer"],
            "additionalProperties": False}


def _norm(v: Any) -> Any:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v


class LLMPatientSimulator:
    def __init__(self, case: Case, *, client: Any = None, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT) -> None:
        self.case = case
        self.client = client if client is not None else make_client()
        self.model = model
        self.effort = effort
        self.system = build_system(case)
        self.messages: list[dict[str, Any]] = []
        self.oracle = ScriptedPatient(case)
        self.deviations: list[Deviation] = []
        self.model_versions: set[str] = set()
        self.usage = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,
                      "cache_read_input_tokens": 0, "calls": 0}

    def _parse(self, q: Question, data: dict[str, Any]) -> Any:
        if data["dont_know"]:
            if (self.case.persona != "vague" and q.answer_type == "choice"
                    and "unknown" in (slot_defs()[q.slot_id].get("choices") or [])):
                return "unknown"            # 與 ScriptedPatient 一致：選擇題的不知道 = 「不記得」（vague 除外）
            return None
        return data["answer"]

    def answer(self, q: Question, *, prompt_zh: str | None = None) -> PatientReply:
        self.messages.append({"role": "user", "content": prompt_zh or q.script_zh.strip()})
        resp = self.client.beta.messages.create(
            model=self.model,
            max_tokens=4000,
            system=self.system,
            messages=self.messages,
            cache_control={"type": "ephemeral"},
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": answer_schema(q)}},
            **({} if "haiku" in self.model else {"betas": [_FALLBACK_BETA], "fallbacks": "default"}),
        )
        if resp.stop_reason != "end_turn":
            raise RuntimeError(f"{self.case.id} {q.id}: stop_reason={resp.stop_reason}")
        self.model_versions.add(resp.model)
        self.usage["calls"] += 1
        for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
            self.usage[k] += getattr(resp.usage, k, None) or 0
        self.messages.append({"role": "assistant", "content": resp.content})
        data = json.loads(next(b.text for b in resp.content if b.type == "text"))
        value = self._parse(q, data)
        utt = data["utterance_zh"]

        expected = self.oracle.answer(q).value
        if _norm(value) != _norm(expected):                # 原題與複誦確認的回答都比對（confirm 欄位區分）
            kind = "fabricated" if expected is None or expected == "unknown" else \
                   "omitted" if value is None or value == "unknown" else "contradicted"
            self.deviations.append(Deviation(self.case.id, q.id, kind, expected, value, utt, confirm=prompt_zh is not None))
        return PatientReply(value=value, utterance_zh=utt, stt_confidence=1.0)

    def confirm(self, q: Question, prompt_zh: str) -> PatientReply:
        """D-50 複誦確認：同一段對話續問；answer 的 schema 與原題相同（填該題的實際值，不是「對／不對」）。"""
        return self.answer(q, prompt_zh=prompt_zh)

