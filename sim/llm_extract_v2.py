"""抽取器 v2（D-52 第 3 項）：開場白、回答句、複誦回答都抽全部 slot；同一份提示給 gpt-6.1-sol 與本機 Gemma。

python -m sim.llm_extract_v2 replay [--extractors gpt,gemma] [--conditions ref,phone] [--limit N] [--workers 8]
                                    [--budget 6] --cache-dir DIR --out DIR [--tag NAME]

- 提示：data/extractor_prompts_v2.yaml（v1 的 data/openai_prompts.yaml、data/extractor_prompts.yaml 不動）。
- 每句一次呼叫，輸出稀疏：asked（被問那題：evidence 原句片段 → 是非題 stance yes／no／unclear，選擇題／時間題 value）、
  mentions（順口提到的其他 slot，各附 evidence）、unclassified（沒把握歸類的原話，交 Clinical Owner 裁定）。
  開場白沒有 asked。複誦回答：題目與複誦句一起當 context（confirm_prompt）。
- 極性保護（程式，不靠模型）：mentions 的是非題 true 若 evidence 含否定詞（先遮罩「不舒服」等非否定片語）→ 丟棄；
  D-50 範圍內（紅旗題＋stt_critical_questions）被問那題若 stance 與句首明確的肯定／否定詞（confirm.leading_yes_no）相反 → 視為未知
  （由 D-50 複誦追問）；複誦回答不套句首規則（「對」是對複誦的回答）。
- 送進模型的文字必須是繁體（D-49）：to_traditional 由呼叫端給（OpenCC s2twp ＋ stt_synth_asr.to_tw）。
- client 介面同 sim/llm_extract.py：ask(system, user, schema, name) -> (obj, usage, model)；輸出再以 schema 驗證，
  不合法、逾時或 HTTP 錯誤 = 抽取失敗（什麼都不寫入）。金鑰只由呼叫端以 api_key= 傳入（ACS_OPENAI_API_KEY）。只用合成資料。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable

from acs_triage.decision.openai_adapter import usage_cost
from acs_triage.loaders import DATA_DIR, REPO_ROOT, _load_yaml, load_extraction_patterns, question_by_id, slot_defs
from acs_triage.prompter.confirm import leading_yes_no
from acs_triage.schemas import Question

from .patient import _ZH_CHOICE

PROMPTS_FILE = DATA_DIR / "extractor_prompts_v2.yaml"
GPT_MODEL, GPT_EFFORT = "gpt-6.1-sol", "medium"         # 同 v1（data/openai_prompts.yaml）
_TYPE = {"yes_no": "boolean", "duration": "number", "choice": "string"}


# ---------------------------------------------------------------- 提示與 schema
@lru_cache(maxsize=None)
def load_prompts() -> dict[str, Any]:
    return _load_yaml(PROMPTS_FILE)


def prompt_file_sha256() -> str:
    return hashlib.sha256(PROMPTS_FILE.read_bytes()).hexdigest()


def code_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def choices(slot: str) -> list[str]:
    excl = set(load_prompts().get("excluded_choices", {}).get(slot, []))
    return [c for c in slot_defs()[slot]["choices"] if c not in excl]


def mention_slots() -> list[str]:
    excl = set(load_prompts()["mention_excluded_slots"])
    return [s for s in slot_defs() if s not in excl]


def _label(slot: str, c: str) -> str:
    return load_prompts()["choice_labels_zh"].get(slot, {}).get(c) or _ZH_CHOICE.get(c, c)


def choices_text(slot: str) -> str:
    return "　選項：" + "、".join(f"{c}（{_label(slot, c)}）" for c in choices(slot))


def fields_zh() -> str:
    first_q: dict[str, Question] = {}
    for q in question_by_id().values():
        first_q.setdefault(q.slot_id, q)
    desc = load_prompts()["field_desc_zh"]
    lines = []
    for sid, d in slot_defs().items():
        text = first_q[sid].script_zh.strip() if sid in first_q else desc[sid]
        lines.append(f"- {sid}（{d['type']}）：{text}" + (choices_text(sid) if d["type"] == "choice" else ""))
    return "\n".join(lines)


@lru_cache(maxsize=None)
def system_prompt(opening: bool = False) -> str:
    return load_prompts()["opening_system_zh" if opening else "answer_system_zh"].format(fields=fields_zh())


def rendered_sha256() -> str:
    """實際送出的提示全文（兩種 system＋三種 user 模板）的雜湊：凍結紀錄用；改任何一字都會變。"""
    cfg = load_prompts()
    blob = "\n".join([system_prompt(True), system_prompt(False), cfg["opening_user_zh"], cfg["answer_user_zh"],
                      cfg["confirm_user_zh"]])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _list_schema(item_props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": {"type": "object", "properties": item_props, "required": list(item_props),
                                       "additionalProperties": False}}


def _side_schemas() -> dict[str, Any]:
    return {"mentions": _list_schema({"slot": {"type": "string", "enum": mention_slots()}, "evidence": {"type": "string"},
                                      "value": {"type": "string"}}),
            "unclassified": _list_schema({"slot": {"type": "string", "enum": [k for k, d in slot_defs().items() if d["type"] == "choice"]},
                                          "phrase": {"type": "string"}})}


def asked_schema(q: Question) -> dict[str, Any]:
    props: dict[str, Any] = {"evidence": {"type": "string"}}
    if q.answer_type == "yes_no":
        props["stance"] = {"type": "string", "enum": ["yes", "no", "unclear"]}
    elif q.answer_type == "choice":
        props["status"] = {"type": "string", "enum": ["answered", "dont_know", "cannot_classify"]}
        props["value"] = {"type": "string", "enum": choices(q.slot_id)}
    else:
        props["status"] = {"type": "string", "enum": ["answered", "dont_know"]}
        props["value"] = {"type": "number"}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def opening_fields_schema() -> dict[str, Any]:
    """開場白：逐欄填寫（同 v1 開場白的稠密格式），沒說到填 null。"""
    props: dict[str, Any] = {}
    for sid in mention_slots():
        d = slot_defs()[sid]
        props[sid] = {"type": [_TYPE[d["type"]], "null"]}
        if d["type"] == "choice":
            props[sid]["enum"] = [*choices(sid), None]
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


CONFIRM_YN = {"有（情況成立）": True, "沒有（情況不成立）": False, "沒有重新回答": None}
CONFIRM_CHOICE = {"重新回答了": True, "沒有重新回答": False}


def confirm_schema(q: Question) -> dict[str, Any]:
    """複誦回答的 asked：agreement（同不同意複誦的答案）＋restated（病人自己重新回答原題）。值由 parse 依兩者決定。"""
    props: dict[str, Any] = {"evidence": {"type": "string"},
                             "agreement": {"type": "string", "enum": ["agree", "disagree", "unclear"]}}
    if q.answer_type == "yes_no":
        props["reply_answer"] = {"type": "string", "enum": [*CONFIRM_YN]}
    else:
        props["reply_answer"] = {"type": "string", "enum": [*CONFIRM_CHOICE]}
        props["value"] = {"type": "string", "enum": choices(q.slot_id)} if q.answer_type == "choice" else {"type": "number"}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def confirmed_value(q: Question, confirm_prompt: str) -> tuple[bool, Any]:
    """複誦句裡客服說的答案 X（S-CONFIRM-BACK：「您的回答是『X』」）→ (有沒有 X, 值)；以 data/scripts_zh.yaml 的值中文反查。"""
    from acs_triage.loaders import load_scripts
    m = re.search(r"您的回答是『(.+?)』", confirm_prompt)
    if not m:
        return False, None
    labels = load_scripts()["confirm_value_labels_zh"]
    table = labels["yes_no"] if q.answer_type == "yes_no" else labels.get(q.slot_id, {})
    rev = {v: k for k, v in table.items()}
    return (m.group(1) in rev), rev.get(m.group(1))


def request_schema(q: Question | None, confirm: bool = False) -> dict[str, Any]:
    side = _side_schemas()
    ev = _list_schema({"slot": {"type": "string", "enum": mention_slots()}, "quote": {"type": "string"}})
    props = ({"evidence": ev, **opening_fields_schema()["properties"], "unclassified": side["unclassified"]} if q is None
             else {"asked": confirm_schema(q) if confirm else asked_schema(q), **side})
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def build_request(text: str, q: Question | None, confirm_prompt: str | None = None) -> tuple[str, str, dict[str, Any], str]:
    """(system, user, schema, schema_name)。q 為 None = 開場白。"""
    cfg = load_prompts()
    if q is None:
        return system_prompt(True), cfg["opening_user_zh"].format(text=text), request_schema(None), "opening_v2"
    common = dict(slot_id=q.slot_id, answer_type=q.answer_type, question_zh=q.script_zh.strip(), text=text,
                  choices=choices_text(q.slot_id) if q.answer_type == "choice" else "")
    if confirm_prompt is None:
        return system_prompt(), cfg["answer_user_zh"].format(**common), request_schema(q), "answer_v2"
    return (system_prompt(), cfg["confirm_user_zh"].format(**common, confirm_prompt=confirm_prompt),
            request_schema(q, confirm=True), "confirm_v2")


def validate(obj: Any, schema: dict[str, Any], path: str = "$") -> None:
    """本模組用到的 schema 子集（object／array／string／number／boolean／null、enum）；不合法 → ValueError。"""
    types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    t = ("null" if obj is None else "boolean" if isinstance(obj, bool) else
         "number" if isinstance(obj, (int, float)) else "string" if isinstance(obj, str) else
         "array" if isinstance(obj, list) else "object" if isinstance(obj, dict) else "?")
    if t not in types:
        raise ValueError(f"{path}: bad type {t}")
    if "enum" in schema and obj not in schema["enum"]:
        raise ValueError(f"{path}: not in enum")
    if t == "object":
        props = schema["properties"]
        if set(obj) != set(props):
            raise ValueError(f"{path}: keys mismatch")
        for k, s in props.items():
            validate(obj[k], s, f"{path}.{k}")
    elif t == "array":
        for i, x in enumerate(obj):
            validate(x, schema["items"], f"{path}[{i}]")


# ---------------------------------------------------------------- 解析與極性保護
@lru_cache(maxsize=None)
def _negation() -> tuple[list[str], re.Pattern[str]]:
    lx = load_extraction_patterns()["leading_yes_no"]
    masks = sorted(set(lx["non_negation_phrases"]) | set(load_extraction_patterns()["non_negation_phrases"])
                   | set(load_prompts()["extra_non_negation_masks"]), key=len, reverse=True)
    return masks, re.compile("|".join(map(re.escape, sorted(lx["negative"], key=len, reverse=True))))


def negated(fragment: str) -> bool:
    """片段含否定詞（沒有、沒、不會、不是、不、沒什麼、還沒；先遮罩「不舒服」「不確定」等非否定片語）。"""
    masks, neg = _negation()
    s = fragment
    for m in masks:
        s = s.replace(m, "□" * len(m))
    return bool(neg.search(s))


def denial_ok(fragment: str) -> bool:
    """否認要有否定詞，且片段沒有表示不確定（「不清楚」「沒注意」「他沒跟我講」）。"""
    return negated(fragment) and not any(w in fragment for w in load_prompts()["uncertainty_markers"])


def _parse_value(slot: str, raw: str) -> tuple[bool, Any]:
    """mentions 的字串值 → (合法, 值)。"""
    d = slot_defs()[slot]
    s = raw.strip()
    if d["type"] == "yes_no":
        if s.lower() in ("true", "false"):
            return True, s.lower() == "true"
        return False, None
    if d["type"] == "choice":
        return (s in choices(slot)), (s if s in choices(slot) else None)
    try:
        return True, float(s)
    except ValueError:
        return False, None


def single_proposition(q: Question) -> bool:
    """是非題只問一件事（題目只有一個問號、不是「…還是…」的二選一）：句首「有／沒有」才等於答案，句首規則才適用。
    D-50 範圍內的題目都屬此類。"""
    t = q.script_zh.strip()
    return q.answer_type == "yes_no" and t.count("？") == 1 and "還是" not in t


def _polarity(slot: str, v: Any) -> str | None:
    """極性保護用：deny = false／none；affirm = 是非題 true，或會直接觸發紅旗的選項（dyspnea_grade＝rest、
    last_episode_timing＝ongoing）。symptom_character 的性質值不算 affirm（「現在不會悶了」仍說明了性質是悶）。"""
    if v is False or v == "none":
        return "deny"
    if v is True or (slot, v) in {("dyspnea_grade", "rest"), ("last_episode_timing", "ongoing")}:
        return "affirm"
    return None


def parse(obj: dict[str, Any], text: str, q: Question | None, confirm_prompt: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """模型輸出 → (slots, diag)。被問那題的 slot 一定在 slots 裡（未知 = None），其餘只放有值者。"""
    diag: dict[str, Any] = {"guards": [], "dropped": [], "unclassified": list(obj.get("unclassified", []))}
    slots: dict[str, Any] = {}
    conflict: set[str] = set()
    unsure = {u["slot"] for u in diag["unclassified"]}
    if q is None:
        quotes: dict[str, list[str]] = {}
        for e in obj["evidence"]:
            quotes.setdefault(e["slot"], []).append(e["quote"])
        mentions = [{"slot": k, "evidence": "／".join(quotes.get(k, [])), "value": v} for k, v in obj.items()
                    if k not in ("unclassified", "evidence") and v is not None]
    else:
        mentions = obj["mentions"]
    guarded = set(load_prompts()["polarity_guard_slots"])
    asked_in_mentions: list[Any] = []
    for m in mentions:
        slot = m["slot"]
        if q is not None and slot == q.slot_id:
            ok, v = _parse_value(slot, m["value"])
            if ok:
                asked_in_mentions.append(v)     # 被問那題以 asked 為準；asked 沒填時才用（模型把答案寫錯位置）
            continue
        ok, v = (True, float(m["value"]) if isinstance(m["value"], (int, float)) and not isinstance(m["value"], bool)
                 else m["value"]) if q is None else _parse_value(slot, m["value"])
        if not ok:
            diag["dropped"].append({**m, "why": "bad_value"})
            continue
        if slot in unsure:                                    # 模型自己把這欄列為沒把握歸類 → 不寫，讓系統追問
            diag["guards"].append({"slot": slot, "guard": "choice_listed_unclassified", "value": v})
            continue
        pol = _polarity(slot, v) if slot in guarded else None
        if pol == "deny" and q is not None:
            # 回答句順口提到的紅旗否認（含 symptom_character＝none）不採用：紅旗題一律直接問、照 D-50 複誦；
            # 開發集閉環中「現在不會悶了」「我不會喘」被抽成 symptom_character＝none，胸部紅旗題因此不問（under-triage）
            diag["guards"].append({"slot": slot, "guard": "mention_redflag_denial_not_used", "evidence": m["evidence"]})
            continue
        if pol == "affirm" and negated(m["evidence"]):
            diag["guards"].append({"slot": slot, "guard": "affirm_with_negated_evidence", "value": v, "evidence": m["evidence"]})
            continue
        if (((slot == "ongoing_now" and v is True) or (slot == "last_episode_timing" and v == "ongoing"))
                and not any(w in m["evidence"] for w in load_prompts()["present_markers"])):
            diag["guards"].append({"slot": slot, "guard": "ongoing_mention_without_present_marker", "evidence": m["evidence"]})
            continue
        if pol == "deny" and not denial_ok(m["evidence"]):
            diag["guards"].append({"slot": slot, "guard": "denial_without_negated_evidence", "evidence": m["evidence"]})
            continue
        if slot in slots and slots[slot] != v:
            conflict.add(slot)
        slots[slot] = v
    for slot in conflict:                                     # 同一句對同一欄給了兩種值 → 不寫
        diag["dropped"].append({"slot": slot, "why": "conflicting_mentions"})
        del slots[slot]
    if q is not None and confirm_prompt is not None:
        a = obj["asked"]
        has_x, x = confirmed_value(q, confirm_prompt)
        if q.answer_type == "yes_no":
            v = CONFIRM_YN[a["reply_answer"]]
        else:
            v = (float(a["value"]) if q.answer_type == "duration" else a["value"]) if CONFIRM_CHOICE[a["reply_answer"]] else None
        if v is None and has_x and a["agreement"] == "agree":
            v = x
        elif v is None and has_x and a["agreement"] == "disagree" and q.answer_type == "yes_no" and x is not None:
            v = not x                                   # 是非題只說「不是」→ X 的相反
        if (v == "none" and q.slot_id in guarded and CONFIRM_CHOICE[a["reply_answer"]] and not denial_ok(a["evidence"])):
            diag["guards"].append({"slot": q.slot_id, "guard": "denial_without_negated_evidence", "evidence": a["evidence"]})
            v = None                                    # 選擇題重新回答「沒有」卻沒有否定詞（例如「我不太清楚」）
        diag["confirm"] = {"agreement": a["agreement"], "reply_answer": a["reply_answer"], "x": x if has_x else "（無）"}
        slots[q.slot_id] = v
        diag["asked_evidence"] = a["evidence"]
    elif q is not None:
        a = obj["asked"]
        if q.answer_type == "yes_no":
            v = {"yes": True, "no": False}.get(a["stance"])
            if v is not None and single_proposition(q):
                lead = leading_yes_no(text)
                if lead is not None and lead != v:
                    diag["guards"].append({"slot": q.slot_id, "guard": "asked_stance_vs_leading_word",
                                           "stance": a["stance"], "leading": lead})
                    v = None
        else:
            v = a["value"] if a["status"] == "answered" else None
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                v = float(v)
            if a["status"] == "cannot_classify":
                diag["unclassified"].append({"slot": q.slot_id, "phrase": a["evidence"]})
            if v == "none" and q.slot_id in guarded and not denial_ok(a["evidence"]):
                diag["guards"].append({"slot": q.slot_id, "guard": "denial_without_negated_evidence", "evidence": a["evidence"]})
                v = None
        if v is None and len(set(map(repr, asked_in_mentions))) == 1:
            mv = asked_in_mentions[0]
            lead = leading_yes_no(text) if q.answer_type == "yes_no" and single_proposition(q) else None
            if lead is None or lead == mv:              # 同樣不得與句首明確的肯定／否定詞相反
                v = mv
                diag["guards"].append({"slot": q.slot_id, "guard": "asked_value_from_mentions", "value": v})
        slots[q.slot_id] = v
        diag["asked_evidence"] = a["evidence"]
    return slots, diag


# ---------------------------------------------------------------- 抽取器
def _err(e: Exception) -> str:
    return f"{type(e).__name__}: {e}" if isinstance(e, (RuntimeError, ValueError)) else type(e).__name__


Key = tuple[str | None, str | None, str]


class LLMExtractorV2:
    """extract_fn(text, q, confirm_prompt=None) → slot dict；同一 (題目, 複誦句, 句子) 只呼叫一次（快取）。

    price = (input, cached, output) USD/1M tokens（None = 不計費）；budget_usd 到了就不再發出新呼叫（之後記 budget_exceeded）。
    to_traditional：送進模型前的簡轉繁（必要前置，D-49）；None 時呼叫端須保證文字已是繁體。
    """

    def __init__(self, client: Any, *, name: str, price: tuple[float, float, float] | None = None,
                 budget_usd: float | None = None, to_traditional: Callable[[str], str] | None = None,
                 clock: Callable[[], float] = time.perf_counter) -> None:
        self.client, self.name, self.price, self.budget = client, name, price, budget_usd
        self.tw = to_traditional or (lambda s: s)
        self.clock = clock
        self.cache: dict[Key, dict[str, Any]] = {}
        self.spent = 0.0
        self.n_tw_changed = 0
        self._lock = threading.Lock()

    @staticmethod
    def key(text: str, q: Question | None, confirm_prompt: str | None = None) -> Key:
        return (q.id if q else None, confirm_prompt, text)

    def call(self, text: str, q: Question | None, confirm_prompt: str | None = None) -> dict[str, Any]:
        sent = self.tw(text)
        changed = sent != unicodedata.normalize("NFKC", text)        # 只算簡轉繁的改動（to_tw 會先 NFKC，全形標點變半形不算）
        rec: dict[str, Any] = {"q": q.id if q else None, "confirm_prompt": confirm_prompt, "text": text, "sent": sent,
                               "ok": False, "slots": {}, "diag": {}, "error": None, "latency_s": None, "usage": {},
                               "cost": 0.0, "model": None, "at": datetime.now().isoformat(timespec="seconds")}
        if changed:
            with self._lock:
                self.n_tw_changed += 1
        if self.budget is not None and self.spent >= self.budget:
            rec["error"] = "budget_exceeded"
            return rec
        system, user, schema, name = build_request(sent, q, confirm_prompt)
        t0 = self.clock()
        try:
            obj, usage, model = self.client.ask(system, user, schema, name)
            rec["usage"], rec["model"] = usage, model
            validate(obj, schema)
            slots, diag = parse(obj, sent, q, confirm_prompt)
            rec.update(ok=True, slots=slots, diag=diag, raw=obj)
        except Exception as e:  # noqa: BLE001
            rec["error"] = _err(e)
        rec["latency_s"] = self.clock() - t0
        if self.price and rec["usage"]:
            rec["cost"] = usage_cost(rec["usage"], *self.price)
        with self._lock:
            self.spent += rec["cost"]
        return rec

    def record(self, text: str, q: Question | None, confirm_prompt: str | None = None) -> dict[str, Any]:
        k = self.key(text, q, confirm_prompt)
        if k not in self.cache:
            rec = self.call(text, q, confirm_prompt)
            with self._lock:
                self.cache[k] = rec
        return self.cache[k]

    def __call__(self, text: str, q: Question | None = None, confirm_prompt: str | None = None) -> dict[str, Any]:
        rec = self.record(text, q, confirm_prompt)
        out = dict(rec["slots"])
        if q is not None:
            out.setdefault(q.slot_id, None)
        return out

    def prefetch(self, items: Iterable[tuple[str, Question | None, str | None]], workers: int = 1) -> None:
        todo = list(dict.fromkeys(self.key(*it) for it in items if self.key(*it) not in self.cache))
        qb = question_by_id()

        def one(k: Key) -> None:
            self.record(k[2], qb[k[0]] if k[0] else None, k[1])

        if workers <= 1:
            for k in todo:
                one(k)
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                list(ex.map(one, todo))

    # ---- 快取檔（可續跑、不重複付費；失敗的不沿用但費用照計）
    def load(self, path: Path, meta: dict[str, Any], reparse: bool = False) -> list[dict[str, Any]]:
        """reparse=True：快取的模型、effort 與送出提示全文（rendered_sha256）都相同、只有程式保護或檔案註解改過時，
        沿用模型原始輸出（raw），以目前的 parse() 重算 slots（不重新呼叫）。"""
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        same_model = {k: v for k, v in data.get("meta", {}).items() if k not in ("prompts_version", "prompt_file_sha256", "code_sha256")} == \
            {k: v for k, v in meta.items() if k not in ("prompts_version", "prompt_file_sha256", "code_sha256")}
        if data.get("meta") != meta and not (reparse and same_model):
            raise SystemExit(f"{path}：快取設定與本次不同，請換 --cache-dir")
        qb = question_by_id()
        for r in data["records"]:
            if r["ok"]:
                if data.get("meta") != meta:
                    q = qb[r["q"]] if r["q"] else None
                    r = {**r, "reparsed_from": data["meta"]}
                    r["slots"], r["diag"] = parse(r["raw"], r["sent"], q, r["confirm_prompt"])
                self.cache[(r["q"], r["confirm_prompt"], r["text"])] = r
        self.spent = sum(r["cost"] for r in data["records"])
        return [r for r in data["records"] if not r["ok"]]

    def save(self, path: Path, meta: dict[str, Any], history: list[dict[str, Any]]) -> None:
        with self._lock:
            recs = history + list(self.cache.values())
        path.write_text(json.dumps({"meta": meta, "records": recs}, ensure_ascii=False, indent=1), encoding="utf-8")


def meta_for(extractor: str) -> dict[str, Any]:
    cfg = load_prompts()
    base = {"prompts_version": cfg["prompts_version"], "prompt_file_sha256": prompt_file_sha256(),
            "rendered_sha256": rendered_sha256(), "code_sha256": code_sha256()}
    if extractor == "gpt":
        return {"extractor": GPT_MODEL, "effort": GPT_EFFORT, **base}
    return {"extractor": cfg["local_model"], "temperature": cfg["local_temperature"], **base}


def load_to_tw() -> Callable[[str], str]:
    """OpenCC s2twp ＋ stt_synth_asr.to_tw()（先在「是」「只」之間切開）。專案 .venv 沒有 opencc：
    以 PYTHONPATH 指向本機已有的 opencc-python-reimplemented（D-49 ASR 環境用的同一版），不下載。缺少就停（不得送簡體）。"""
    try:
        import opencc
    except ImportError:
        raise SystemExit("opencc 無法 import：送進抽取器的文字必須先轉繁體（D-49），請以 PYTHONPATH 指向本機 opencc 後重跑")
    from .stt_synth_asr import to_tw
    s2tw = opencc.OpenCC("s2twp")
    return lambda s: to_tw(s, s2tw)


def make_extractor(name: str, *, budget: float | None = None, to_traditional: Callable[[str], str] | None = None) -> LLMExtractorV2:
    cfg = load_prompts()
    if name == "gpt":
        from acs_triage.decision.openai_adapter import KEY_ENV, OpenAIStructured

        from .openai_eval import PRICES
        if not os.environ.get(KEY_ENV):
            print(f"{KEY_ENV}: MISSING")
            sys.exit(2)
        client = OpenAIStructured(model=GPT_MODEL, effort=GPT_EFFORT, api_key=os.environ[KEY_ENV])
        return LLMExtractorV2(client, name=GPT_MODEL, price=PRICES[GPT_MODEL], budget_usd=budget, to_traditional=to_traditional)
    from .llm_extract import LMStudioStructured
    client = LMStudioStructured(model=cfg["local_model"], base_url=cfg["local_base_url"],
                                temperature=cfg["local_temperature"], max_tokens=cfg["local_max_tokens"])
    return LLMExtractorV2(client, name=cfg["local_model"], to_traditional=to_traditional)


# ---------------------------------------------------------------- 重放（階段 A）
def protect_asked_writer(ext, found: dict[str, Any], q: Question, source: str) -> None:
    """重放的寫入方式：順口提到的 slot 套用與閉環 runner 相同的 _write_mentions（補未知；已知值只在紅旗是非題「有」或
    confirm_back_severity 較嚴重時覆蓋，其餘保留已知值）。被問那題只有抽到值才寫入（asked_by）；閉環 runner 則照既有 runner
    寫入未知並標記已問——兩者在這一點不同。"""
    from .runner import _write_mentions
    _write_mentions(ext, found, q.slot_id, source=source + "_mention")
    if found.get(q.slot_id) is not None:
        ext.set(q.slot_id, found[q.slot_id], asked_by=q.id, source=source)


def confirm_rows(transcripts: list[dict], fn: Callable[..., dict[str, Any]]) -> list[dict[str, Any]]:
    """開發集 10-23 逐字稿的複誦回答：題目＋複誦句當 context，抽出的值 vs 逐字稿的確認值。"""
    from .openai_slots import grade
    qb = question_by_id()
    rows = []
    for t in transcripts:
        for i, x in enumerate(t["turns"], 1):
            if "confirm" not in x:
                continue
            q, c = qb[x["q"]], x["confirm"]
            pred = fn(c["utterance_zh"], q, confirm_prompt=c["prompt_zh"]).get(q.slot_id)
            rows.append({"case_id": t["case_id"], "turn": i, "q": q.id, "truth": c["value"], "pred": pred,
                         "grade": grade(c["value"], pred, q.slot_id), "prompt_zh": c["prompt_zh"], "text": c["utterance_zh"]})
    return rows


CONFIRM_DEV = REPO_ROOT / "reports" / "eval_2026-10-23_llm_opus-5-5_medium_transcripts.json"
# 複誦回答探針：開發集複誦句（10-23）＋人工寫的「更正」回答；只測解讀，不是臨床資料（題目原文、複誦模板取自 repo）
CONFIRM_PROBES = [
    ("Q-ONGOING-01", False, "不是，有啊，現在還是悶悶的。", True),
    ("Q-ONGOING-01", False, "不是不是，還在不舒服。", True),
    ("Q-ONGOING-01", False, "不是。", True),
    ("Q-ONGOING-01", False, "對。", False),
    ("Q-ONGOING-01", False, "對啦，現在沒有了。", False),
    ("Q-DIAPH-01", False, "不對，有冒冷汗。", True),
    ("Q-DIAPH-01", None, "有，那時候有冒冷汗。", True),
    ("Q-DIAPH-01", None, "沒有，沒有冒汗。", False),
    ("Q-SYNCOPE-01", False, "嗯，對，沒有。", False),
    ("Q-SYNCOPE-01", None, "這個我不太確定耶。", None),
    ("Q-DYSPNEA-GRADE-01", "none", "不是，我走路做家事就會喘。", "exertional_daily"),
    ("Q-DYSPNEA-GRADE-01", "exertional_heavy", "對，只有激烈運動才會。", "exertional_heavy"),
    ("Q-DYSPNEA-GRADE-01", "none", "不是。", None),
    ("Q-CHARACTER-01", "vague", "不是，比較像被壓住。", "pressure"),
    ("Q-CHARACTER-01", "vague", "對，就說不上來。", "vague"),
]


def probe_rows(fn: Callable[..., dict[str, Any]]) -> list[dict[str, Any]]:
    from acs_triage.prompter.confirm import confirm_prompt
    qb = question_by_id()
    rows = []
    for qid, said, reply, truth in CONFIRM_PROBES:
        q = qb[qid]
        prompt = confirm_prompt(q, said)
        pred = fn(reply, q, confirm_prompt=prompt).get(q.slot_id)
        rows.append({"q": qid, "confirmed_value": said, "text": reply, "truth": truth, "pred": pred, "ok": pred == truth})
    return rows


def _cell_summary(c: dict[str, Any]) -> dict[str, Any]:
    m = c["_m"]
    return {"hs_miss": len(m.hard_stop_miss), "hs_truth": m.hard_stop_truth, "premature": len(c["premature"]),
            "false_hs": len(m.hard_stop_false_alarm), "under": len(m.under_triage), "over": len(m.over_triage),
            "exact": round(m.exact_rate, 4), "abstain_fp": len(m.abstain_fp), "rf_yes_missed": len(c["rf_yes_missed"]),
            "slot_all": c["slot_by_priority"]["all"], "slot_redflag": c["slot_by_priority"].get("redflag", {}),
            "hs_miss_cases": m.hard_stop_miss, "false_hs_cases": m.hard_stop_false_alarm, "premature_cases": c["premature"]}


def replay_main(argv: list[str]) -> None:
    from .e2e_llm import DEFAULT_STT, DEFAULT_TRANSCRIPTS, latency_stats, phone_texts, run_cell, utterances
    from .metrics import compute  # noqa: F401  (run_cell 內用)
    ap = argparse.ArgumentParser(prog="sim.llm_extract_v2 replay")
    ap.add_argument("--extractors", default="gpt,gemma")
    ap.add_argument("--conditions", default="ref,phone")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--local-workers", type=int, default=1, help="本機模型並行數（1 = 一次一句，延遲才有意義）")
    ap.add_argument("--budget", type=float, default=6.0, help="gpt 累計估算費用上限（USD；快取檔累計）")
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--no-confirm", action="store_true", help="不跑複誦回答（10-23 逐字稿與探針）")
    ap.add_argument("--reparse", action="store_true", help="快取的送出提示全文相同時，以目前程式重算 slots（不重新呼叫）")
    args = ap.parse_args(argv)
    to_tw = load_to_tw()
    transcripts = json.loads(Path(DEFAULT_TRANSCRIPTS).read_text(encoding="utf-8"))
    confirm_tr = json.loads(CONFIRM_DEV.read_text(encoding="utf-8"))
    if args.limit:
        transcripts, confirm_tr = transcripts[: args.limit], confirm_tr[: args.limit]
    stt_rows = json.loads(Path(DEFAULT_STT).read_text(encoding="utf-8"))["rows"]
    ptexts, unmatched = phone_texts(transcripts, stt_rows)
    texts = {"ref": {}, "phone": ptexts}
    all_text = [s for t in transcripts for _, s, _ in utterances(t)] + list(ptexts.values())
    tw_changed = sorted({s for s in all_text if to_tw(s) != unicodedata.normalize("NFKC", s)})
    qb = question_by_id()
    cache_dir, out = Path(args.cache_dir), Path(args.out)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    rep: dict[str, Any] = {"meta": {"date": date.today().isoformat(), "started_at": datetime.now().isoformat(timespec="seconds"),
                                    "tag": args.tag, "limit": args.limit, "prompts_version": load_prompts()["prompts_version"],
                                    "prompt_file_sha256": prompt_file_sha256(), "rendered_sha256": rendered_sha256(),
                                    "code_sha256": code_sha256(), "transcripts": Path(DEFAULT_TRANSCRIPTS).name,
                                    "phone_unmatched": len(unmatched), "texts_not_traditional": tw_changed},
                           "cells": {}, "llm": {}, "confirm": {}}
    for e in [x for x in args.extractors.split(",") if x]:
        ex = make_extractor(e, budget=args.budget, to_traditional=to_tw)
        meta = meta_for(e)
        path = cache_dir / f"v2_cache_{e}.json"
        history = ex.load(path, meta, reparse=args.reparse)
        todo = [(texts[c].get((t["case_id"], i), s), qb[qid] if qid else None, None)
                for c in args.conditions.split(",") for t in transcripts for i, s, qid in utterances(t)]
        if not args.no_confirm:
            todo += [(x["confirm"]["utterance_zh"], qb[x["q"]], x["confirm"]["prompt_zh"])
                     for t in confirm_tr for x in t["turns"] if "confirm" in x]
        print(f"{ex.name}：{len(dict.fromkeys(ex.key(*it) for it in todo))} 個不同呼叫", flush=True)
        w = args.workers if e == "gpt" else args.local_workers
        for a in range(0, len(todo), 100):
            ex.prefetch(todo[a:a + 100], workers=w)
            ex.save(path, meta, history)
            print(f"  {ex.name}: {len(ex.cache)} 筆，累計估算 US${ex.spent:.4f}", flush=True)
        for c in args.conditions.split(","):
            cell = run_cell(transcripts, ex, texts[c], writer=protect_asked_writer)
            rep["cells"][f"{e}/{c}"] = {**_cell_summary(cell), "rows": cell["rows"], "opening": cell["opening"],
                                        "hs_trigger": cell["hs_trigger"], "abstain_diag": cell["abstain_diag"]}
        if not args.no_confirm:
            cr, pr = confirm_rows(confirm_tr, ex), probe_rows(ex)
            ex.save(path, meta, history)                 # 探針是逐句呼叫的，也存進快取（重跑不再付費）
            rep["confirm"][e] = {"dev_rows": cr, "dev_grades": dict(Counter(r["grade"] for r in cr)),
                                 "probe_rows": pr, "probe_ok": sum(r["ok"] for r in pr), "probe_n": len(pr)}
        recs = list(ex.cache.values())
        rep["llm"][e] = {"n_calls": len(recs), "n_failed": sum(not r["ok"] for r in recs),
                         "errors": dict(Counter(r["error"] for r in recs if not r["ok"])), "latency": latency_stats(recs),
                         "cost_total": ex.spent, "workers": w,
                         "guards": dict(Counter(g["guard"] for r in recs for g in r["diag"].get("guards", []))),
                         "unclassified": [{"q": r["q"], "text": r["text"], **u} for r in recs for u in r["diag"].get("unclassified", [])]}
    rep["meta"]["finished_at"] = datetime.now().isoformat(timespec="seconds")
    stem = f"v2_replay{'_' + args.tag if args.tag else ''}"
    (out / f"{stem}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: {kk: v[kk] for kk in ("hs_miss", "premature", "false_hs", "under", "over", "exact", "abstain_fp", "rf_yes_missed")}
                      for k, v in rep["cells"].items()}, ensure_ascii=False))
    print(json.dumps({e: {"probe": f"{v['probe_ok']}/{v['probe_n']}", "dev": v["dev_grades"]} for e, v in rep["confirm"].items()},
                     ensure_ascii=False))
    print(json.dumps({e: {"cost": round(v["cost_total"], 4), "guards": v["guards"], "fail": v["n_failed"]} for e, v in rep["llm"].items()},
                     ensure_ascii=False))
    print(f"→ {out / (stem + '.json')}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "replay":
        replay_main(sys.argv[2:])
    else:
        print(__doc__)
