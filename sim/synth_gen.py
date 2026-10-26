"""實驗 1：獨立的合成病人驗證集——生成（OpenAI gpt-6.1-sol，與扮演病人的 Opus 不同家族）。

python -m sim.synth_gen [--out data/synth/scenarios_synth_v1.yaml] [--pilot N] [--workers 10]

- 每個 case：opening_zh（台灣口語開場白）、slots（病人知道的全部事實；不列 = 病人不知道）、persona_style、category、name_zh。
- slots 的 strict json_schema 由 acs_triage.loaders.slot_defs() 自動產生；consult_screen_positive 是合併篩檢題的答案，
  由 sim.cases._complete 從三個底層事實推得，不生成。
- 既有 119 個 case 的開場白交給生成器並要求不得改寫或複製；生成後以字元 3-gram 重疊係數檢查，
  與任一既有開場白 ≥ SIM_THRESHOLD 者重生（每例最多 MAX_REGEN 次），次數寫進檔頭。
- 檔頭寫明：LLM 生成、參考標註為暫定、非 Clinical Owner truth、不得用於規則調整或既有測試門檻。
- 金鑰只讀 ACS_OPENAI_API_KEY（D-31），以 api_key= 明確傳入；只用合成資料（D-10）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from acs_triage.decision.openai_adapter import KEY_ENV, OpenAIStructured, usage_cost
from acs_triage.loaders import DATA_DIR, _load_yaml, questions, rules_version, slot_defs

from .cases import Case, _complete, _decisive_fields, all_cases
from .openai_eval import PRICES
from .patient import _ZH_CHOICE

MODEL = "gpt-6.1-sol"
EFFORT = "medium"
SYNTH_DIR = DATA_DIR / "synth"
DEFAULT_OUT = SYNTH_DIR / "scenarios_synth_v1.yaml"
DERIVED_SLOTS = {"consult_screen_positive"}
SIM_THRESHOLD = 0.40     # 3-gram 重疊係數；既有開場白彼此的改寫版為 0.42–0.63，不同情境最高 0.28
MAX_REGEN = 3
BATCH = 5

HEADER = """\
# 合成病人驗證集 v1（實驗 1：獨立驗證集）
# - 本檔為 LLM 生成（OpenAI {model}），全為虛構合成資料（D-10、D-30、D-31）；生成器沒有看臨床規則。
# - 參考標註（data/synth/reference_synth_v1.json）為兩個 LLM 的暫定臨床判斷，**不是 Clinical Owner truth**；
#   不一致與系統低估的案例交 Clinical Owner 裁定（reports/synth_adjudication_*.xlsx／.md）。
# - **不得**用於規則、題庫、Prompter 的調整，也不得用於既有測試門檻；改規則時不得回頭看本檔的個案來調。
# - slots = 病人「知道」的全部事實（客服問到時會這樣答）；未列出的 slot = 病人不知道。
# - persona_style 只表現在開場白與哪些事實未知；LLM 病人（prompt 0.3）回答時不帶人物風格。
"""


def prompts() -> dict[str, Any]:
    return _load_yaml(SYNTH_DIR / "synth_prompts.yaml")


# ---------------------------------------------------------------- schema／驗證
def generated_slot_ids() -> list[str]:
    return [s for s in slot_defs() if s not in DERIVED_SLOTS]


def slot_schema() -> dict[str, Any]:
    props: dict[str, Any] = {}
    for sid in generated_slot_ids():
        d = slot_defs()[sid]
        if d["type"] == "yes_no":
            props[sid] = {"type": ["boolean", "null"]}
        elif d["type"] == "duration":
            props[sid] = {"type": ["number", "null"]}
        elif d["type"] == "choice":
            props[sid] = {"anyOf": [{"type": "string", "enum": list(d["choices"])}, {"type": "null"}]}
        else:
            raise ValueError(f"unsupported slot type: {sid} {d['type']}")
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def batch_schema() -> dict[str, Any]:
    case = {"type": "object",
            "properties": {"name_zh": {"type": "string"}, "opening_zh": {"type": "string"}, "slots": slot_schema()},
            "required": ["name_zh", "opening_zh", "slots"], "additionalProperties": False}
    return {"type": "object", "properties": {"cases": {"type": "array", "items": case}},
            "required": ["cases"], "additionalProperties": False}


def validate_slots(slots: dict[str, Any]) -> list[str]:
    """None 視為未知（合法）。回傳錯誤清單。"""
    errs = []
    for k, v in slots.items():
        d = slot_defs().get(k)
        if d is None or k in DERIVED_SLOTS:
            errs.append(f"{k}: 不是可生成的 slot")
        elif v is None:
            continue
        elif d["type"] == "yes_no" and not isinstance(v, bool):
            errs.append(f"{k}: 應為 bool，得到 {v!r}")
        elif d["type"] == "duration" and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0):
            errs.append(f"{k}: 應為非負數字，得到 {v!r}")
        elif d["type"] == "choice" and v not in d["choices"]:
            errs.append(f"{k}: {v!r} 不在選項 {d['choices']}")
    return errs


# ---------------------------------------------------------------- 相似度
def _norm(s: str) -> str:
    return re.sub(r"[\W_]+", "", s)


def trigrams(s: str) -> set[str]:
    t = _norm(s)
    return {t[i:i + 3] for i in range(len(t) - 2)} or {t}


def overlap(a: str, b: str) -> float:
    """字元 3-gram 重疊係數 |A∩B| / min(|A|,|B|)：短句被嵌進長句（加贅詞改寫）也抓得到。"""
    x, y = trigrams(a), trigrams(b)
    return len(x & y) / min(len(x), len(y))


def jaccard(a: str, b: str) -> float:
    x, y = trigrams(a), trigrams(b)
    return len(x & y) / len(x | y)


def most_similar(text: str, corpus: list[str]) -> tuple[float, str]:
    return max(((overlap(text, c), c) for c in corpus), default=(0.0, ""))


def existing_openings() -> list[str]:
    return sorted({c.opening_zh for c in all_cases()})


# ---------------------------------------------------------------- 提示詞
def glossary(cfg: dict[str, Any]) -> str:
    by_slot: dict[str, str] = {}
    for q in questions():
        by_slot.setdefault(q.slot_id, q.script_zh.strip())
    gloss = {**_ZH_CHOICE, **cfg["choice_gloss_extra_zh"]}
    lines = []
    for sid in generated_slot_ids():
        d = slot_defs()[sid]
        typ = {"yes_no": "是非", "duration": "數字", "choice": "選擇"}[d["type"]]
        ch = "、".join(f"{c}（{gloss[c]}）" if c in gloss else c for c in d.get("choices") or []) or "—"
        lines.append(f"- {sid}｜{typ}｜{ch}｜{by_slot.get(sid) or cfg['slot_gloss_zh'][sid]}")
    return "\n".join(lines)


def system_prompt(cfg: dict[str, Any], existing: list[str]) -> str:
    personas = "\n".join(f"- {k}：{v}" for k, v in cfg["personas"].items())
    return cfg["generator_system_zh"].format(personas=personas, existing="\n".join(f"- {o}" for o in existing),
                                             glossary=glossary(cfg))


def batch_user(cfg: dict[str, Any], category: str, items: list[dict[str, Any]], prior: list[str]) -> str:
    cat = cfg["categories"][category]
    lines = []
    for i, it in enumerate(items, 1):
        line = f"{i}. persona_style={it['persona_style']}；情境方向：{it['hint_zh']}"
        if it.get("regen_note"):
            line += "\n   " + it["regen_note"]
        lines.append(line)
    pr = cfg["generator_prior_zh"].format(openings="\n".join(f"- {o}" for o in prior)) if prior else ""
    return cfg["generator_batch_user_zh"].format(category=category, category_zh=cat["zh"], category_desc=cat["desc"],
                                                 n=len(items), items="\n".join(lines), prior=pr)


def build_plan(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """依涵蓋矩陣排定每個 case 的類別、人物風格與情境方向（確定性，不用亂數）。"""
    cycle = ["general", "elderly_slow", "minimizer", "anxious_exaggerating", "family_proxy", "unclear", "general"]
    plan, k = [], 0
    for cat, spec in cfg["categories"].items():
        for j in range(spec["n"]):
            if cat == "family_proxy":
                persona = "family_proxy"
            else:
                persona, k = cycle[k % len(cycle)], k + 1
            plan.append({"id": f"SYN-{len(plan) + 1:03d}", "category": cat, "persona_style": persona,
                         "hint_zh": spec["hints"][j % len(spec["hints"])]})
    return plan


# ---------------------------------------------------------------- 生成
class Generator:
    def __init__(self, client: Any, cfg: dict[str, Any], existing: list[str]) -> None:
        self.client = client
        self.cfg = cfg
        self.existing = existing
        self.system = system_prompt(cfg, existing)
        self.usage: list[dict[str, Any]] = []
        self.model_versions: set[str] = set()
        self.errors: list[str] = []

    def _ask(self, category: str, items: list[dict[str, Any]], prior: list[str]) -> list[dict[str, Any]]:
        user = batch_user(self.cfg, category, items, prior)
        last = ""
        for _ in range(3):
            data, usage, model = self.client.ask(self.system, user, batch_schema(), "synthetic_patients")
            self.usage.append(usage)
            self.model_versions.add(model)
            out = data["cases"]
            errs = [] if len(out) == len(items) else [f"數量 {len(out)} ≠ {len(items)}"]
            errs += [e for c in out for e in validate_slots(c["slots"])]
            errs += ["opening_zh 空白" for c in out if not c["opening_zh"].strip()]
            if not errs:
                return out
            last = "; ".join(errs[:5])
        raise RuntimeError(f"{category}：三次輸出都不合格（{last}）")

    def generate_category(self, category: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """同類別依序分批（後批看得到前批的開場白），再逐例檢查與既有開場白的相似度、太像就重生。"""
        done: list[dict[str, Any]] = []
        for i in range(0, len(items), BATCH):
            chunk = items[i:i + BATCH]
            out = self._ask(category, chunk, [d["opening_zh"] for d in done])
            for it, c in zip(chunk, out):
                done.append(self._finalize(category, it, c, [d["opening_zh"] for d in done]))
        return done

    def _finalize(self, category: str, it: dict[str, Any], c: dict[str, Any], prior: list[str]) -> dict[str, Any]:
        regen = 0
        score, sim = most_similar(c["opening_zh"], self.existing)
        first_score = score
        while score >= SIM_THRESHOLD and regen < MAX_REGEN:
            regen += 1
            note = self.cfg["generator_regen_note_zh"].format(old=c["opening_zh"], similar=sim)
            c = self._ask(category, [{**it, "regen_note": note}], prior)[0]
            score, sim = most_similar(c["opening_zh"], self.existing)
        return {"id": it["id"], "category": category, "persona_style": it["persona_style"], "hint_zh": it["hint_zh"],
                "name_zh": c["name_zh"].strip(), "opening_zh": c["opening_zh"].strip(),
                "slots": {k: v for k, v in c["slots"].items() if v is not None},
                "_sim": {"max_overlap_existing": round(score, 3), "first_overlap_existing": round(first_score, 3),
                         "most_similar_existing": sim, "regen": regen, "still_similar": score >= SIM_THRESHOLD}}

    def cost(self) -> float:
        return sum(usage_cost(u, *PRICES[MODEL]) for u in self.usage)


def generate(plan: list[dict[str, Any]], gen: Generator, workers: int) -> list[dict[str, Any]]:
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for it in plan:
        by_cat.setdefault(it["category"], []).append(it)

    def run(cat: str):
        try:
            return gen.generate_category(cat, by_cat[cat]), None
        except Exception as e:  # noqa: BLE001 — 單類別失敗要回報，不讓整批中斷
            return [], f"{cat}: {type(e).__name__}: {e}"

    with ThreadPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(run, by_cat))
    gen.errors += [e for _, e in res if e]
    order = {it["id"]: i for i, it in enumerate(plan)}
    return sorted((c for cs, _ in res for c in cs), key=lambda c: order[c["id"]])


# ---------------------------------------------------------------- 存檔／載入
def similarity_stats(scenarios: list[dict[str, Any]], existing: list[str]) -> dict[str, Any]:
    ov = [most_similar(s["opening_zh"], existing)[0] for s in scenarios]
    jac = [max(jaccard(s["opening_zh"], e) for e in existing) for s in scenarios]
    new_pairs = [(a["id"], b["id"], round(overlap(a["opening_zh"], b["opening_zh"]), 3))
                 for i, a in enumerate(scenarios) for b in scenarios[i + 1:]
                 if overlap(a["opening_zh"], b["opening_zh"]) >= SIM_THRESHOLD]
    return {"metric": "字元 3-gram 重疊係數（去標點）；另列 Jaccard", "threshold": SIM_THRESHOLD,
            "existing_openings": len(existing),
            "regenerated_cases": sum(1 for s in scenarios if s["_sim"]["regen"] > 0),
            "regen_attempts": sum(s["_sim"]["regen"] for s in scenarios),
            "still_similar_after_max_regen": [s["id"] for s in scenarios if s["_sim"]["still_similar"]],
            "max_overlap_vs_existing": round(max(ov, default=0), 3),
            "mean_max_overlap_vs_existing": round(sum(ov) / len(ov), 3) if ov else None,
            "max_jaccard_vs_existing": round(max(jac, default=0), 3),
            "new_vs_new_pairs_over_threshold": new_pairs}


def save(path: Path, scenarios: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    body = {**meta, "scenarios": [{k: v for k, v in s.items() if not k.startswith("_")}
                                  | {"similarity": s["_sim"]} for s in scenarios]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(model=MODEL) + "\n" + yaml.safe_dump(body, allow_unicode=True, sort_keys=False, width=1000),
                    encoding="utf-8")


def load_synth(path: Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def synth_case(sc: dict[str, Any]) -> Case:
    errs = validate_slots(sc["slots"])
    if errs:
        raise ValueError(f"{sc['id']}: {errs}")
    slots = _complete({k: v for k, v in sc["slots"].items() if v is not None})
    return Case(id=sc["id"], scenario_id=sc["id"], opening_zh=sc["opening_zh"], truth_tier=None, truth_hard_stop=False,
                truth_rf=None, slots=slots, persona="normal", module=sc["category"], note=sc.get("name_zh"),
                **_decisive_fields(slots))


def load_synth_cases(path: Path) -> list[Case]:
    """合成情境檔 → sim 的 Case（truth 一律 None：參考標註另存，不是 truth）。"""
    return [synth_case(sc) for sc in load_synth(path)["scenarios"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--pilot", type=int, default=None, help="只生成計畫中前 N 個 case（估算費用用）")
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()
    if not os.environ.get(KEY_ENV):
        print(f"{KEY_ENV}: MISSING")
        sys.exit(2)
    print(f"{KEY_ENV}: OK")
    cfg = prompts()
    plan = build_plan(cfg)
    if args.pilot:
        plan = plan[: args.pilot]
    existing = existing_openings()
    gen = Generator(OpenAIStructured(model=MODEL, effort=EFFORT, api_key=os.environ[KEY_ENV]), cfg, existing)
    scenarios = generate(plan, gen, args.workers)
    meta = {"synth_version": "1",
            "generated_by": {"model": MODEL, "model_versions": sorted(gen.model_versions), "reasoning_effort": EFFORT,
                             "prompt_version": cfg["prompt_version"], "date": date.today().isoformat(),
                             "rules_version_at_generation": rules_version()},
            "distribution": {"category": dict(Counter(s["category"] for s in scenarios)),
                             "persona_style": dict(Counter(s["persona_style"] for s in scenarios))},
            "similarity": similarity_stats(scenarios, existing),
            "cost": {"calls": len(gen.usage), "input_tokens": sum(u.get("input_tokens") or 0 for u in gen.usage),
                     "output_tokens": sum(u.get("output_tokens") or 0 for u in gen.usage),
                     "est_cost_usd": round(gen.cost(), 4)},
            "errors": gen.errors, "planned": len(plan), "generated": len(scenarios)}
    save(Path(args.out), scenarios, meta)
    for c in load_synth_cases(Path(args.out)):     # 存檔後能被 sim 載入
        assert c.slots is not None
    print(json.dumps({k: meta[k] for k in ("planned", "generated", "cost", "errors")}, ensure_ascii=False))
    print(json.dumps({k: v for k, v in meta["similarity"].items() if k != "new_vs_new_pairs_over_threshold"}, ensure_ascii=False))
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
