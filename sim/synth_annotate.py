"""實驗 1：獨立參考標註——Opus 5.5 與 gpt-6.1-sol 各自標註，看不到彼此與系統結果。

python -m sim.synth_annotate [--scenarios data/synth/scenarios_synth_v1.yaml] [--out data/synth/reference_synth_v1.json]
                             [--limit N] [--workers 8]

- 輸入＝開場白＋完整事實清單（sim.llm_patient.render_sheet，與 LLM 病人看到的同一份渲染文字）＋ docs/CLINICAL_RULES.md §1–§3 原文
  （執行時從文件擷取）；不給 §4 之後的規則引擎細節 → 測規則的臨床效度，而不是請模型重新實作規則。不給類別、人物風格與系統結果。
- 輸出 {tier: T0–T4|T9, hard_stop, rf_ids, rationale_zh, confidence}。兩者 tier 與 hard_stop 都一致 → 參考標註；否則待裁定。
- 參考標註只是 LLM 臨床判斷，不是 truth（非 Clinical Owner 裁定）。
- 金鑰：Anthropic 只讀 ACS_PATIENT_LLM_KEY、OpenAI 只讀 ACS_OPENAI_API_KEY（D-31），以 api_key= 明確傳入；錯誤只記狀態碼／錯誤代碼。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

from acs_triage.decision.openai_adapter import KEY_ENV as OPENAI_KEY_ENV, OpenAIStructured, usage_cost
from acs_triage.loaders import DOCS_DIR, rules_version

from .cases import Case
from .llm_patient import _FALLBACK_BETA, KEY_ENV as ANTHROPIC_KEY_ENV, render_sheet
from .openai_eval import PRICES as OPENAI_PRICES
from .run_llm_eval import PRICES as ANTHROPIC_PRICES
from .synth_gen import DEFAULT_OUT as DEFAULT_SCENARIOS, SYNTH_DIR, load_synth_cases, prompts

DEFAULT_OUT = SYNTH_DIR / "reference_synth_v1.json"
TIERS = ["T0", "T1", "T2", "T3", "T4", "T9"]
RFS = ["RF-01", "RF-02", "RF-03", "RF-04", "RF-05", "RF-06"]
LABEL_SCHEMA = {
    "type": "object",
    "properties": {"tier": {"type": "string", "enum": TIERS}, "hard_stop": {"type": "boolean"},
                   "rf_ids": {"type": "array", "items": {"type": "string", "enum": RFS}},
                   "rationale_zh": {"type": "string"}, "confidence": {"type": "string", "enum": ["low", "medium", "high"]}},
    "required": ["tier", "hard_stop", "rf_ids", "rationale_zh", "confidence"],
    "additionalProperties": False,
}
ANNOTATORS = {"opus": {"model": "claude-opus-5-5", "effort": "medium"},
              "gpt": {"model": "gpt-6.1-sol", "effort": "medium"}}
DISCLAIMER = ("LLM 參考標註（暫定）：兩位 LLM 標註者各自依 CLINICAL_RULES §1–§3 與臨床判斷給的分級，"
              "不是 Clinical Owner truth；不得用於規則調整或既有測試門檻。")


def rules_excerpt() -> str:
    """docs/CLINICAL_RULES.md §1–§3 原文（『## 1. 分流等級』起、『## 4.』之前，去掉結尾分隔線）。"""
    text = (DOCS_DIR / "CLINICAL_RULES.md").read_text(encoding="utf-8")
    start = text.index("## 1. 分流等級")
    end = text.index("\n## 4. ", start)
    return text[start:end].rstrip().removesuffix("---").rstrip()


def system_prompt(cfg: dict[str, Any]) -> str:
    return cfg["annotator_system_zh"].format(rules=rules_excerpt())


def user_prompt(cfg: dict[str, Any], case: Case) -> str:
    return cfg["annotator_user_zh"].format(opening_zh=case.opening_zh, sheet=render_sheet(case))


class OpusAnnotator:
    def __init__(self, client: Any = None, *, model: str = ANNOTATORS["opus"]["model"],
                 effort: str = ANNOTATORS["opus"]["effort"]) -> None:
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ[ANTHROPIC_KEY_ENV])
        self.client, self.model, self.effort = client, model, effort

    def label(self, system: str, user: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        resp = self.client.beta.messages.create(
            model=self.model, max_tokens=8000,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],   # 共用的規則前綴才快取
            messages=[{"role": "user", "content": user}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": LABEL_SCHEMA}},
            betas=[_FALLBACK_BETA], fallbacks="default",
        )
        if resp.stop_reason != "end_turn":
            raise RuntimeError(f"stop_reason={resp.stop_reason}")
        usage = {k: getattr(resp.usage, k, None) or 0 for k in
                 ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
        return json.loads(next(b.text for b in resp.content if b.type == "text")), usage, resp.model

    def cost(self, u: dict[str, Any]) -> float:
        pin, pout = ANTHROPIC_PRICES[self.model]
        return (u["input_tokens"] * pin + u["output_tokens"] * pout + u["cache_creation_input_tokens"] * pin * 1.25
                + u["cache_read_input_tokens"] * pin * 0.1) / 1e6


class GptAnnotator:
    def __init__(self, client: Any = None, *, model: str = ANNOTATORS["gpt"]["model"],
                 effort: str = ANNOTATORS["gpt"]["effort"]) -> None:
        self.client = client or OpenAIStructured(model=model, effort=effort, api_key=os.environ[OPENAI_KEY_ENV])
        self.model = model

    def label(self, system: str, user: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        return self.client.ask(system, user, LABEL_SCHEMA, "reference_label")

    def cost(self, u: dict[str, Any]) -> float:
        return usage_cost(u, *OPENAI_PRICES[self.model])


def tier_num(label: dict[str, Any]) -> int:
    return int(label["tier"].removeprefix("T"))


def normalized(label: dict[str, Any]) -> tuple[int, bool]:
    """(tier, hard_stop)；hard_stop=true 一律視為 T0（Hard stop 一定是 T0，CLINICAL_RULES §1）。"""
    return (0 if label["hard_stop"] else tier_num(label)), bool(label["hard_stop"])


def agree(a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    return a is not None and b is not None and normalized(a) == normalized(b)


def safe_error(e: Exception) -> str:
    """只留例外型別與狀態碼；OpenAI adapter 與本模組自己丟的 RuntimeError 已只含狀態碼／錯誤代碼，可保留訊息。"""
    if type(e) is RuntimeError:
        return f"RuntimeError: {str(e)[:200]}"
    code = getattr(e, "status_code", None)
    return type(e).__name__ + (f" HTTP {code}" if code is not None else "")


def annotate(cases: list[Case], annotators: dict[str, Any], cfg: dict[str, Any], workers: int = 8) -> list[dict[str, Any]]:
    system = system_prompt(cfg)
    jobs = [(c, name) for c in cases for name in annotators]

    def one(job):
        c, name = job
        ann = annotators[name]
        try:
            lab, usage, model = ann.label(system, user_prompt(cfg, c))
            return c.id, name, {**lab, "model_version": model, "usage": usage, "est_cost_usd": round(ann.cost(usage), 6)}, None
        except Exception as e:  # noqa: BLE001 — 單筆失敗要記錄
            return c.id, name, None, safe_error(e)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(one, jobs))
    rows = {c.id: {"case_id": c.id, "labels": {}, "errors": {}} for c in cases}
    for cid, name, lab, err in out:
        if lab is not None:
            rows[cid]["labels"][name] = lab
        else:
            rows[cid]["errors"][name] = err
    for r in rows.values():
        r["agree"] = agree(r["labels"].get("opus"), r["labels"].get("gpt"))
    return list(rows.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    missing = [k for k in (ANTHROPIC_KEY_ENV, OPENAI_KEY_ENV) if not os.environ.get(k)]
    for k in (ANTHROPIC_KEY_ENV, OPENAI_KEY_ENV):
        print(f"{k}: {'MISSING' if k in missing else 'OK'}")
    if missing:
        sys.exit(2)
    cfg = prompts()
    cases = load_synth_cases(Path(args.scenarios))
    cases = cases[: args.limit] if args.limit else cases
    rows = annotate(cases, {"opus": OpusAnnotator(), "gpt": GptAnnotator()}, cfg, args.workers)
    cost = {n: round(sum(r["labels"][n]["est_cost_usd"] for r in rows if n in r["labels"]), 4) for n in ANNOTATORS}
    excerpt = rules_excerpt()
    meta = {"disclaimer": DISCLAIMER, "date": date.today().isoformat(), "scenarios": str(args.scenarios),
            "annotators": {n: {**a, "model_versions": sorted({r["labels"][n]["model_version"] for r in rows if n in r["labels"]})}
                           for n, a in ANNOTATORS.items()},
            "prompt_version": cfg["prompt_version"], "rules_version": rules_version(),
            "rules_excerpt": "docs/CLINICAL_RULES.md §1–§3", "rules_excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
            "n_cases": len(rows), "n_agree": sum(r["agree"] for r in rows),
            "n_errors": sum(len(r["errors"]) for r in rows), "est_cost_usd": cost}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"_meta": meta, "cases": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("n_cases", "n_agree", "n_errors", "est_cost_usd")}, ensure_ascii=False))
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
