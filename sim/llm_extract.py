"""LLM slot 抽取器（實驗 2，`sim/e2e_llm.py`）：同一份提示給雲端 gpt-6.1-sol 與本機 LM Studio 模型。

- 有題目的輪：原封沿用 data/openai_prompts.yaml 的 slot 提示（prompts 0.3，D-39／D-40）與 sim/openai_slots.slot_schema()，
  只回被問那題的 slot。
- 開場白（沒有題目）：data/extractor_prompts.yaml 的 opening 提示，一次輸出全部欄位（沒提到填 null）。
- 兩種 client 介面相同：ask(system, user, schema, name) -> (obj, usage, model)。輸出一律再以 schema 驗證，
  不合法、逾時或 HTTP 錯誤 = 抽取失敗（回 {}，該句什麼都不寫入），並記錄在呼叫紀錄。
- 金鑰只由呼叫端以 api_key= 傳入（ACS_OPENAI_API_KEY，D-31）；錯誤只記狀態碼與錯誤代碼。只用合成資料（D-10）。
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any, Callable, Iterable

from acs_triage.decision.openai_adapter import Transport, usage_cost
from acs_triage.loaders import DATA_DIR, _load_yaml, question_by_id, slot_defs
from acs_triage.schemas import Question

from .openai_slots import choices_text, slot_schema
from .patient import _ZH_CHOICE

_TYPE = {"yes_no": "boolean", "duration": "number", "choice": "string"}


@lru_cache(maxsize=None)
def load_prompts() -> dict[str, Any]:
    """slot 提示（openai_prompts.yaml）＋開場白提示（extractor_prompts.yaml）。"""
    base = _load_yaml(DATA_DIR / "openai_prompts.yaml")
    ext = _load_yaml(DATA_DIR / "extractor_prompts.yaml")
    return {**ext, "slot_system_zh": base["slot_system_zh"], "slot_user_zh": base["slot_user_zh"],
            "slot_prompts_version": base["prompts_version"], "opening_prompts_version": ext["prompts_version"],
            "model": base["model"], "reasoning_effort": base["reasoning_effort"]}


def opening_slots() -> list[str]:
    excluded = set(load_prompts()["opening_excluded_slots"])
    return [s for s in slot_defs() if s not in excluded]


def opening_schema() -> dict[str, Any]:
    props: dict[str, Any] = {}
    for sid in opening_slots():
        d = slot_defs()[sid]
        props[sid] = {"type": [_TYPE[d["type"]], "null"]}
        if d["type"] == "choice":
            props[sid]["enum"] = [*d["choices"], None]
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def opening_fields_zh() -> str:
    first_q: dict[str, Question] = {}
    for q in question_by_id().values():
        first_q.setdefault(q.slot_id, q)
    desc = load_prompts()["opening_field_desc_zh"]
    labels = {**_ZH_CHOICE, **load_prompts()["opening_choice_labels_zh"]}
    lines = []
    for sid in opening_slots():
        d = slot_defs()[sid]
        text = first_q[sid].script_zh.strip() if sid in first_q else desc[sid]
        line = f"- {sid}（{d['type']}）：{text}"
        if d["type"] == "choice":
            line += "　選項：" + "、".join(f"{c}（{labels.get(c, c)}）" for c in d["choices"])
        lines.append(line)
    return "\n".join(lines)


def build_request(text: str, q: Question | None) -> tuple[str, str, dict[str, Any], str]:
    """(system, user, schema, schema_name)。q 為 None = 開場白。"""
    cfg = load_prompts()
    if q is None:
        return (cfg["opening_system_zh"].format(fields=opening_fields_zh()), cfg["opening_user_zh"].format(opening_zh=text),
                opening_schema(), "opening_slots")
    user = cfg["slot_user_zh"].format(slot_id=q.slot_id, answer_type=q.answer_type, choices=choices_text(q),
                                      question_zh=q.script_zh.strip(), utterance_zh=text)
    return cfg["slot_system_zh"], user, slot_schema(q), "slot_value"


def validate(obj: Any, schema: dict[str, Any]) -> None:
    """只支援本模組用到的 schema 子集（object／boolean／number／string／null、enum）；不合法 → ValueError。"""
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    props = schema["properties"]
    if set(obj) != set(props):
        raise ValueError(f"keys mismatch: missing={sorted(set(props) - set(obj))} extra={sorted(set(obj) - set(props))}")
    for k, spec in props.items():
        v = obj[k]
        types = spec["type"] if isinstance(spec["type"], list) else [spec["type"]]
        ok = ((v is None and "null" in types) or (isinstance(v, bool) and "boolean" in types)
              or (isinstance(v, (int, float)) and not isinstance(v, bool) and "number" in types)
              or (isinstance(v, str) and "string" in types))
        if not ok:
            raise ValueError(f"{k}: bad type")
        if "enum" in spec and v not in spec["enum"]:
            raise ValueError(f"{k}: not in enum")


def to_slots(obj: dict[str, Any], q: Question | None) -> dict[str, Any]:
    if q is None:
        return {k: v for k, v in obj.items() if v is not None}
    return {} if obj["dont_know"] else {q.slot_id: obj["answer"]}


def _urllib_transport(url: str, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, dict(r.headers), json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), None


class LMStudioStructured:
    """LM Studio 的 OpenAI 相容 /v1/chat/completions，response_format json_schema（strict）。不需金鑰。"""

    def __init__(self, *, model: str, base_url: str, temperature: float = 0.0, max_tokens: int = 2048,
                 transport: Transport | None = None) -> None:
        self.model, self.url = model, base_url.rstrip("/") + "/chat/completions"
        self.temperature, self.max_tokens = temperature, max_tokens
        self.transport = transport or _urllib_transport

    def ask(self, system: str, user: str, schema: dict[str, Any], name: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": self.temperature, "max_tokens": self.max_tokens,
            "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
        }, ensure_ascii=False).encode("utf-8")
        status, _, data = self.transport(self.url, {"Content-Type": "application/json"}, body)
        if status != 200:
            raise RuntimeError(f"LM Studio HTTP {status}")
        choice = data["choices"][0]
        if choice.get("finish_reason") not in (None, "stop"):
            raise RuntimeError(f"LM Studio finish_reason={choice.get('finish_reason')}")
        return json.loads(choice["message"]["content"]), data.get("usage") or {}, data.get("model", self.model)


def _err(e: Exception) -> str:
    # 只記類型與 adapter 自己組的訊息（狀態碼／錯誤代碼）；其他例外不記內容
    return f"{type(e).__name__}: {e}" if isinstance(e, (RuntimeError, ValueError)) else type(e).__name__


class LLMExtractor:
    """extract_fn(句子, 題目) → slot dict；同一 (題目, 句子) 只呼叫一次（快取）。

    price = (input, cached, output) USD/1M tokens（None = 不計費）；budget_usd：累計估算費用達上限後不再發出新呼叫，
    其後的句子記為失敗（budget_exceeded）。
    """

    def __init__(self, client: Any, *, name: str, price: tuple[float, float, float] | None = None,
                 budget_usd: float | None = None, clock: Callable[[], float] = time.perf_counter) -> None:
        self.client, self.name, self.price, self.budget = client, name, price, budget_usd
        self.clock = clock
        self.cache: dict[tuple[str | None, str], dict[str, Any]] = {}     # key → 呼叫紀錄
        self.spent = 0.0
        self._lock = threading.Lock()

    @staticmethod
    def key(text: str, q: Question | None) -> tuple[str | None, str]:
        return (q.id if q else None, text)

    def call(self, text: str, q: Question | None) -> dict[str, Any]:
        rec: dict[str, Any] = {"q": q.id if q else None, "text": text, "ok": False, "slots": {}, "error": None,
                               "latency_s": None, "usage": {}, "cost": 0.0, "model": None}
        if self.budget is not None and self.spent >= self.budget:
            rec["error"] = "budget_exceeded"
            return rec
        system, user, schema, name = build_request(text, q)
        t0 = self.clock()
        try:
            obj, usage, model = self.client.ask(system, user, schema, name)
            rec["usage"], rec["model"] = usage, model
            validate(obj, schema)
            rec.update(ok=True, slots=to_slots(obj, q), raw=obj)
        except Exception as e:  # noqa: BLE001
            rec["error"] = _err(e)
        rec["latency_s"] = self.clock() - t0
        if self.price and rec["usage"]:
            rec["cost"] = usage_cost(rec["usage"], *self.price)
        with self._lock:
            self.spent += rec["cost"]
        return rec

    def prefetch(self, items: Iterable[tuple[str, Question | None]], workers: int = 1) -> None:
        todo = list(dict.fromkeys(self.key(t, q) for t, q in items if self.key(t, q) not in self.cache))
        qb = question_by_id()

        def one(k: tuple[str | None, str]) -> None:
            rec = self.call(k[1], qb[k[0]] if k[0] else None)
            with self._lock:
                self.cache[k] = rec

        if workers <= 1:
            for k in todo:
                one(k)
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                list(ex.map(one, todo))

    def __call__(self, text: str, q: Question | None = None) -> dict[str, Any]:
        k = self.key(text, q)
        if k not in self.cache:
            rec = self.call(text, q)
            with self._lock:
                self.cache[k] = rec
        return dict(self.cache[k]["slots"])
