"""閉環模擬（D-52 第 3 項階段 B）：Opus LLM 病人 → 抽取器 v2 → 規則 → 下一題（sim/runner.py 的 extractor 選項）。

python -m sim.closed_loop run --set dev|holdout --arm gpt|gemma|structured --cache-dir DIR --out DIR
                              [--limit N（只限開發集）] [--workers 8] [--opus-budget X] [--gpt-budget Y] [--seed-extract FILE]
python -m sim.closed_loop freeze          # 凍結紀錄寫到 reports/extractor_v2_freeze.json（固定位置、只能寫一次）

- 病人：LLMPatientSimulator（claude-opus-5-5、effort medium、prompt 0.3），以「對話前綴快取」包一層：同一 case、
  同一串客服問句（含複誦句）→ 重用已取得的病人回答。快取種子＝同一份情境的結構化值閉環逐字稿（開發集 10-23、
  保留集 10-26）；兩種抽取器的閉環共用同一份快取。問句序列相同時，病人看到的對話與當時完全相同，重用即是同一個樣本
  （配對比較；不是新的獨立樣本）。序列一旦分岔，之後都是新呼叫（API）。
- structured arm：只用快取、不准新呼叫，重跑結構化值閉環；必須逐例重現逐字稿的最終結果（自我檢查）。
- 抽取器：sim/llm_extract_v2.py（gpt-6.1-sol 或本機 Gemma）；送進抽取器與句首判斷的文字一律先轉繁體（OpenCC s2twp＋to_tw）。
- premature：Hard stop 若只靠抽錯的值成立（把觸發時已知的 slot 換回病人真正知道的事實後不再是 Hard stop）→ 不算命中
  （truth／參考為 Hard stop 者計為 miss；同 sim.extractor_e2e 的慣例，保留 tier 0、去掉 hard_stop）。
- 保留集（gpt、gemma、structured 三個 arm 都一樣）：固定位置的凍結紀錄必須存在，全部凍結檔（FROZEN_FILES）與提示全文的 sha256
  須相符；不得 --limit；開跑前先登記到固定位置的 reports/extractor_v2_holdout_runs.json，同一 arm 已登記或 --out 已有輸出就拒跑。
- 金鑰只讀環境變數（ACS_PATIENT_LLM_KEY、ACS_OPENAI_API_KEY），以 api_key= 傳入；錯誤只記類型與狀態碼。只用合成資料（D-10）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

from acs_triage.loaders import DATA_DIR, REPO_ROOT, question_by_id, rules_version
from acs_triage.rules import RulesEngine, SlotState

from .cases import Case, all_cases
from .llm_patient import DEFAULT_EFFORT, DEFAULT_MODEL, KEY_ENV, LLMPatientSimulator, _prompt_cfg, make_client
from .patient import PatientReply
from .runner import RunResult, run_case

DEV_STRUCTURED = REPO_ROOT / "reports" / "eval_2026-10-23_llm_opus-5-5_medium_transcripts.json"
HOLDOUT_SCENARIOS = DATA_DIR / "synth" / "scenarios_synth_v1.yaml"
HOLDOUT_STRUCTURED = REPO_ROOT / "reports" / "eval_2026-10-26_llm_scenarios_synth_v1_opus-5-5_medium_transcripts.json"
HOLDOUT_REFERENCE = DATA_DIR / "synth" / "reference_synth_v1.json"
# 凍結範圍：提示、抽取器、閉環 runner、閉環指標（premature 定義）與簡轉繁（to_tw）。保留集的三個 arm 都要比對全部 sha256。
FROZEN_FILES = ["data/extractor_prompts_v2.yaml", "sim/llm_extract_v2.py", "sim/runner.py", "sim/closed_loop.py", "sim/stt_synth_asr.py"]
# 固定位置（不隨 --out 改變）：凍結紀錄只能寫一次；保留集每個 arm 開跑前先登記，已登記就拒跑。
FREEZE_PATH = REPO_ROOT / "reports" / "extractor_v2_freeze.json"
HOLDOUT_REGISTRY = REPO_ROOT / "reports" / "extractor_v2_holdout_runs.json"
_ENGINE = RulesEngine()


def _price(model: str) -> tuple[float, float]:
    from .run_llm_eval import PRICES
    return PRICES[model]


def call_cost(u: dict[str, int], model: str = DEFAULT_MODEL) -> float:
    """同 run_llm_eval.usage_summary：cache 寫入 1.25×input、讀取 0.1×input。"""
    pin, pout = _price(model)
    return (u.get("input_tokens", 0) * pin + u.get("output_tokens", 0) * pout + u.get("cache_creation_input_tokens", 0) * pin * 1.25
            + u.get("cache_read_input_tokens", 0) * pin * 0.1) / 1e6


def _err(e: Exception) -> str:
    return f"{type(e).__name__}: {str(e)[:200]}" if isinstance(e, (RuntimeError, ValueError, KeyError)) else type(e).__name__


# ---------------------------------------------------------------- 病人對話前綴快取
class PatientCache:
    """對話前綴快取。鍵含病人模型、effort 與 llm_patient prompt_version：任何一個改了，舊回答都不會被沿用。"""

    def __init__(self, model: str = DEFAULT_MODEL, effort: str = DEFAULT_EFFORT, prompt_version: str | None = None) -> None:
        self.meta = {"model": model, "effort": effort,
                     "prompt_version": prompt_version if prompt_version is not None else _prompt_cfg()["prompt_version"]}
        self.store: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def key(self, case_id: str, path: list[str]) -> str:
        m = self.meta
        return json.dumps([m["model"], m["effort"], m["prompt_version"], case_id, path], ensure_ascii=False)

    def get(self, k: str) -> dict[str, Any] | None:
        with self._lock:
            return self.store.get(k)

    def put(self, k: str, rec: dict[str, Any]) -> None:
        with self._lock:
            self.store.setdefault(k, rec)

    def seed(self, transcripts: list[dict[str, Any]], source: str) -> int:
        """結構化值閉環逐字稿 → 前綴快取（問句＝題目原文；複誦句＝逐字稿記下的 prompt_zh）。
        呼叫端須確認逐字稿是同一個病人模型／effort／prompt_version 產生的（10-23、10-26 皆為 claude-opus-5-5、medium、0.3）。"""
        qb = question_by_id()
        n = 0
        for t in transcripts:
            path: list[str] = []
            for x in t["turns"]:
                path.append(qb[x["q"]].script_zh.strip())
                self.put(self.key(t["case_id"], path), {**reconstruct(x["value"], x["utterance_zh"]), "source": source})
                n += 1
                if "confirm" in x:
                    c = x["confirm"]
                    path.append(c["prompt_zh"])
                    self.put(self.key(t["case_id"], path), {**reconstruct(c["value"], c["utterance_zh"]), "source": source})
                    n += 1
        return n

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("meta") != self.meta:
            raise SystemExit(f"{path}：病人快取的模型／effort／prompt_version（{data.get('meta')}）與本次（{self.meta}）不同，不能沿用")
        self.store.update(data["store"])

    def save(self, path: Path) -> None:
        with self._lock:
            data = {"meta": self.meta, "store": dict(self.store)}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")


def reconstruct(value: Any, utterance_zh: str) -> dict[str, Any]:
    """逐字稿的值 → 病人當時的 structured output（dont_know／answer）。不知道（None）與選擇題「不記得」都是 dont_know。"""
    dk = value is None or value == "unknown"
    return {"utterance_zh": utterance_zh, "dont_know": dk, "answer": value if not dk else False}


class Budget:
    def __init__(self, limit: float | None) -> None:
        self.limit, self.spent, self.calls = limit, 0.0, 0
        self._lock = threading.Lock()

    def check(self) -> None:
        with self._lock:
            if self.limit is not None and self.spent >= self.limit:
                raise RuntimeError("opus_budget_exceeded")

    def add(self, usd: float) -> None:
        with self._lock:
            self.spent += usd
            self.calls += 1


class _NoClient:
    class beta:  # noqa: N801
        class messages:  # noqa: N801
            @staticmethod
            def create(**kw: Any) -> Any:
                raise RuntimeError("patient_cache_miss")


class CachedLLMPatient(LLMPatientSimulator):
    """LLMPatientSimulator＋對話前綴快取。live=False 時快取沒有就丟 patient_cache_miss（structured arm 的自我檢查）。"""

    def __init__(self, case: Case, *, cache: PatientCache, client: Any = None, live: bool = True,
                 budget: Budget | None = None, **kw: Any) -> None:
        super().__init__(case, client=client if (client is not None and live) else _NoClient(), **kw)
        if cache.meta != {"model": self.model, "effort": self.effort, "prompt_version": _prompt_cfg()["prompt_version"]}:
            raise ValueError("病人快取的設定與病人模擬不同")
        self.cache, self.live, self.budget = cache, live, budget
        self.path: list[str] = []
        self.n_live = self.n_cached = 0
        self.cost = 0.0
        self.sources: Counter = Counter()

    def answer(self, q, *, prompt_zh: str | None = None) -> PatientReply:  # type: ignore[override]
        user = prompt_zh or q.script_zh.strip()
        k = self.cache.key(self.case.id, self.path + [user])
        rec = self.cache.get(k)
        if rec is None:
            if not self.live:
                raise RuntimeError("patient_cache_miss")
            if self.budget is not None:
                self.budget.check()
            before = dict(self.usage)
            reply = super().answer(q, prompt_zh=prompt_zh)
            delta = {kk: self.usage[kk] - before[kk] for kk in self.usage if kk != "calls"}
            usd = call_cost(delta, self.model)
            self.cost += usd
            if self.budget is not None:
                self.budget.add(usd)
            data = json.loads(next(b.text for b in self.messages[-1]["content"] if b.type == "text"))
            self.cache.put(k, {**data, "source": "live", "model": sorted(self.model_versions)[-1] if self.model_versions else None,
                               "at": datetime.now().isoformat(timespec="seconds")})
            self.path.append(user)
            self.n_live += 1
            self.sources["live"] += 1
            return reply
        data = {kk: rec[kk] for kk in ("utterance_zh", "dont_know", "answer")}
        self.messages.append({"role": "user", "content": user})
        self.messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
        value = self._parse(q, data)
        expected = self.oracle.answer(q).value                     # 偏差紀錄同 LLMPatientSimulator.answer
        from .llm_patient import Deviation, _norm
        if _norm(value) != _norm(expected):
            kind = "fabricated" if expected is None or expected == "unknown" else \
                   "omitted" if value is None or value == "unknown" else "contradicted"
            self.deviations.append(Deviation(self.case.id, q.id, kind, expected, value, data["utterance_zh"], confirm=prompt_zh is not None))
        self.path.append(user)
        self.n_cached += 1
        self.sources["live_reused" if rec.get("source") == "live" else "seed"] += 1
        return PatientReply(value=value, utterance_zh=data["utterance_zh"], stt_confidence=1.0)


# ---------------------------------------------------------------- 資料
def load_set(name: str) -> tuple[list[Case], list[dict[str, Any]]]:
    if name == "dev":
        return all_cases(), json.loads(DEV_STRUCTURED.read_text(encoding="utf-8"))
    from .synth_gen import load_synth_cases
    return load_synth_cases(HOLDOUT_SCENARIOS), json.loads(HOLDOUT_STRUCTURED.read_text(encoding="utf-8"))


def file_hashes() -> dict[str, str]:
    return {f: hashlib.sha256((REPO_ROOT / f).read_bytes()).hexdigest() for f in FROZEN_FILES}


def freeze_record() -> dict[str, Any]:
    from .llm_extract_v2 import load_prompts, prompt_file_sha256, rendered_sha256
    return {"prompts_version": load_prompts()["prompts_version"], "prompt_file_sha256": prompt_file_sha256(),
            "rendered_sha256": rendered_sha256(), "files": file_hashes()}


def check_holdout_allowed(arm: str, limit: int | None, out_dir: Path) -> dict[str, Any]:
    """保留集防護（三個 arm 都套）：要有固定位置的凍結紀錄、全部凍結檔與提示全文的 sha256 相符、不得 --limit、
    同一 arm 沒有登記過也沒有任何既有輸出。通過才回傳凍結紀錄。"""
    if limit:
        raise SystemExit("保留集不得用 --limit（只能完整跑一次）")
    if not FREEZE_PATH.exists():
        raise SystemExit(f"保留集必須先凍結（{FREEZE_PATH} 不存在；python -m sim.closed_loop freeze）")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    now = freeze_record()
    bad = [f for f in FROZEN_FILES if freeze.get("files", {}).get(f) != now["files"][f]]
    bad += [k for k in ("prompt_file_sha256", "rendered_sha256") if freeze.get(k) != now[k]]
    if bad:
        raise SystemExit(f"凍結後有改動：{bad}（保留集只能用凍結版跑）")
    runs = json.loads(HOLDOUT_REGISTRY.read_text(encoding="utf-8")) if HOLDOUT_REGISTRY.exists() else []
    if any(r["arm"] == arm for r in runs) or list(out_dir.glob(f"closed_holdout_{arm}*.json")):
        raise SystemExit(f"保留集 {arm} arm 已經跑過（{HOLDOUT_REGISTRY} 或 {out_dir}）：每個 arm 只跑一次")
    return freeze


def check_lmstudio(base_url: str, model: str) -> None:
    """LM Studio 伺服器連得上、模型已載入（/api/v0/models 的 state＝loaded；舊版沒有該端點時只查 /v1/models）。不送推論請求。"""
    import urllib.error
    import urllib.request

    def get(url: str) -> Any:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read())
    try:
        ids = [m["id"] for m in get(base_url.rstrip("/") + "/models").get("data", [])]
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise SystemExit(f"LM Studio 連不上（{type(e).__name__}）：先開伺服器並 lms load {model}")
    if model not in ids:
        raise SystemExit(f"LM Studio 沒有模型 {model}：先 lms load {model} -c 8192")
    try:
        v0 = get(base_url.rstrip("/").removesuffix("/v1") + "/api/v0/models").get("data", [])
    except (urllib.error.URLError, OSError, ValueError):
        return
    state = next((m.get("state") for m in v0 if m.get("id") == model), None)
    if state is not None and state != "loaded":
        raise SystemExit(f"LM Studio 模型 {model} 未載入（state={state}）：先 lms load {model} -c 8192")


def register_holdout_run(arm: str, **info: Any) -> None:
    runs = json.loads(HOLDOUT_REGISTRY.read_text(encoding="utf-8")) if HOLDOUT_REGISTRY.exists() else []
    hit = next((r for r in runs if r["arm"] == arm), None)
    if hit is None:
        runs.append({"arm": arm, **info})
    else:
        hit.update(info)
    HOLDOUT_REGISTRY.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")


def seed_extractor(ex: Any, path: Path, meta: dict[str, Any]) -> int:
    """階段 A 重放的抽取快取 → 閉環抽取快取：模型、effort／temperature 與送出提示全文（rendered_sha256）都相同才可。
    閉環傳給抽取器的是轉繁後的句子，所以以重放紀錄的 sent 當鍵；以目前程式重算 slots；費用記 0（已在階段 A 計過）。"""
    from .llm_extract_v2 import parse
    data = json.loads(path.read_text(encoding="utf-8"))
    for k in ("extractor", "effort", "temperature", "rendered_sha256"):
        if data["meta"].get(k) != meta.get(k):
            raise SystemExit(f"{path}：{k} 與本次不同，不能當抽取種子")
    qb = question_by_id()
    n = 0
    for r in data["records"]:
        key = (r["q"], r["confirm_prompt"], r["sent"])
        if not r["ok"] or key in ex.cache:
            continue
        slots, diag = parse(r["raw"], r["sent"], qb[r["q"]] if r["q"] else None, r["confirm_prompt"])
        ex.cache[key] = {**r, "text": r["sent"], "slots": slots, "diag": diag, "cost": 0.0, "orig_cost": r["cost"],
                         "seeded_from": path.name}
        n += 1
    return n


def hs_supported(case: Case, state: SlotState) -> bool:
    """觸發 Hard stop 時已知的 slot（推導值除外）換回病人真正知道的事實（不知道 → 未知），是否仍為 Hard stop。"""
    facts = {k: case.slots.get(k) for k in state.as_dict() if not state.is_derived(k) and case.slots.get(k) is not None}
    return _ENGINE.decide(SlotState(facts)).hard_stop


# ---------------------------------------------------------------- 一個 arm
def run_arm(cases: list[Case], *, arm: str, cache: PatientCache, client: Any, extractor: Any, tw: Any,
            budget: Budget | None, workers: int) -> list[dict[str, Any]]:
    def one(case: Case) -> dict[str, Any]:
        p = CachedLLMPatient(case, cache=cache, client=client, live=arm != "structured", budget=budget)
        t0 = time.monotonic()
        try:
            r = run_case(case, patient=p, extractor=extractor, to_traditional=tw)
            err = None
        except Exception as e:  # noqa: BLE001 — 單案失敗要記錄、不中斷整批
            r, err = None, _err(e)
        return {"case": case, "result": r, "patient": p, "error": err, "wall_s": time.monotonic() - t0}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, cases))


def case_record(o: dict[str, Any]) -> dict[str, Any]:
    case, r, p = o["case"], o["result"], o["patient"]
    rec: dict[str, Any] = {"case_id": case.id, "error": o["error"], "wall_s": round(o["wall_s"], 2),
                           "patient": {"live": p.n_live, "cached": p.n_cached, "sources": dict(p.sources), "cost": p.cost,
                                       "deviations": [d.__dict__ for d in p.deviations]}}
    if r is None:
        return rec
    sup = hs_supported(case, r.final_state) if r.final.hard_stop else None
    rec.update(final={"tier": r.final.tier, "hs": r.final.hard_stop, "rf": list(r.final.rf_hits), "missing": list(r.final.missing)},
               hs_supported=sup, stop=r.stop_reason, n_q=r.n_questions, n_confirms=r.n_confirms,
               n_confirm_changed=r.n_confirm_changed, hard_stop_turn=r.hard_stop_turn,
               opening_extracted=r.opening_extracted, final_slots=r.final_slots, mention_conflicts=r.mention_conflicts,
               mention_confirms=r.mention_confirms,
               turns=[{"q": t.question_id, "utt": t.utterance_zh, "value": t.answer, "structured": t.structured_answer,
                       "pre_confirm": t.pre_confirm_answer, "extracted": t.extracted, "confirm_prompt": t.confirm_prompt_zh,
                       "confirm_utt": t.confirm_utterance_zh, "confirm_value": t.confirm_answer,
                       "confirm_structured": t.confirm_structured} for t in r.turns])
    return rec


def adjusted(o: dict[str, Any], truth_hs: bool) -> RunResult:
    """premature（Hard stop 只靠抽錯的值）且 truth／參考為 Hard stop → 去掉 hard_stop（保留 tier 0），計為 miss。"""
    r = o["result"]
    if truth_hs and r.final.hard_stop and not hs_supported(o["case"], r.final_state):
        r.final = r.final.model_copy(update={"hard_stop": False, "rf_hits": []})
        r.stop_reason = "premature_hard_stop"
    return r


def dev_metrics(outs: list[dict[str, Any]]) -> dict[str, Any]:
    from .metrics import compute
    ok = [o for o in outs if o["result"] is not None]
    unsupported = [o["case"].id for o in ok if o["result"].final.hard_stop and not hs_supported(o["case"], o["result"].final_state)]
    premature = [cid for cid in unsupported if next(x for x in ok if x["case"].id == cid)["case"].truth_hard_stop]
    res = [adjusted(o, o["case"].truth_hard_stop) for o in ok]
    m = compute(res)
    t9 = sum(1 for r in res if r.final.tier == 9)
    return {"n": len(res), "errors": [(o["case"].id, o["error"]) for o in outs if o["result"] is None],
            "hs_truth": m.hard_stop_truth, "hs_hit": m.hard_stop_hit, "hs_sensitivity": m.hard_stop_hit / m.hard_stop_truth if m.hard_stop_truth else None,
            "hs_miss": m.hard_stop_miss, "premature": premature, "hs_unsupported": unsupported,
            "false_hs": m.hard_stop_false_alarm, "under": m.under_triage, "over": m.over_triage, "exact": m.exact_rate,
            "abstain_fp": m.abstain_fp, "abstain_fn": m.abstain_fn, "t9": t9, "mean_questions": m.mean_questions,
            "confirms": m.confirms, "confirms_per_call": m.mean_confirms, "confirm_changed": m.confirm_changed,
            "escalating_recall": m.escalating_recall, "stop_reasons": dict(m.stop_reasons),
            "finals": {r.case_id: f"{'HS' if r.final.hard_stop else 'T' + str(r.final.tier)}" for r in res}}


def holdout_rows(outs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    from .synth_eval import _outcome
    rows = {}
    for o in outs:
        if o["result"] is None:
            continue
        r = o["result"]
        out = _outcome(r.final, r.final_state, r.n_questions, r.stop_reason)
        out["hs_supported"] = hs_supported(o["case"], r.final_state) if r.final.hard_stop else None
        out["n_confirms"] = r.n_confirms
        rows[o["case"].id] = out
    return rows


def holdout_metrics(rows: dict[str, dict[str, Any]], cases: list[Case]) -> dict[str, Any]:
    """與 sim.synth_eval 同一套（參考一致子集為主；全部＝較急者）。premature：參考為 Hard stop、系統 Hard stop 只靠抽錯的值 → 計 miss。"""
    from .synth_eval import conservative, metrics, ref_outcome, urgency
    ref = {r["case_id"]: r for r in json.loads(HOLDOUT_REFERENCE.read_text(encoding="utf-8"))["cases"]}
    by_id = {c.id: c for c in cases}
    table = []
    for cid, out in rows.items():
        case = by_id[cid]
        labels = ref.get(cid, {}).get("labels", {})
        ro = ref_outcome(labels["opus"], case) if "opus" in labels else None
        rg = ref_outcome(labels["gpt"], case) if "gpt" in labels else None
        agree = ro if (ro and rg and (ro["tier"], ro["hs"]) == (rg["tier"], rg["hs"])) else None
        table.append({"id": cid, "ref_agree": agree, "ref_cons": conservative(ro, rg), "sys": dict(out)})
    res = {}
    for rk in ("ref_agree", "ref_cons"):
        tb = []
        for row in table:
            sys_out = dict(row["sys"])
            if row[rk] is not None and row[rk]["hs"] and sys_out["hs"] and not sys_out["hs_supported"]:
                sys_out.update(hs=False, rf=[], urg=urgency(sys_out["tier"], False, SlotState()), premature=True)
            tb.append({**row, "sys": sys_out})
        m = metrics(tb, "sys", rk)
        hs_ref = [r for r in tb if r[rk] is not None and r[rk]["hs"]]
        m["premature"] = [r["id"] for r in hs_ref if r["sys"].get("premature")]
        m["false_hs"] = [r["id"] for r in tb if r[rk] is not None and not r[rk]["hs"] and r["sys"]["hs"]]
        m["hs_unsupported"] = [r["id"] for r in tb if r["sys"]["hs"] and r["sys"]["hs_supported"] is False]
        m["confirms"] = sum(r["sys"]["n_confirms"] for r in tb if r[rk] is not None)
        res[rk] = m
    return res


def extraction_stats(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """閉環中被問那題的抽取（確認前）vs 病人模擬的結構化值；複誦回答的抽取 vs 結構化值。"""
    from .openai_slots import grade
    qb = question_by_id()
    g, gc, rf_yes_missed = Counter(), Counter(), []
    for r in recs:
        for t in r.get("turns", []):
            q = qb[t["q"]]
            pre = t["pre_confirm"] if t["confirm_prompt"] is not None else t["value"]
            gr = grade(t["structured"], pre, q.slot_id)
            g[gr] += 1
            if q.priority == "redflag" and t["structured"] is True and pre is not True:
                rf_yes_missed.append({"case_id": r["case_id"], "q": t["q"], "utt": t["utt"], "pred": pre})
            if t["confirm_prompt"] is not None:
                gc[grade(t["confirm_structured"], t["confirm_value"], q.slot_id)] += 1
    return {"asked": dict(g), "confirm_reply": dict(gc), "rf_yes_missed": rf_yes_missed}


# ---------------------------------------------------------------- CLI：run
def run_main(argv: list[str]) -> None:
    from .llm_extract_v2 import load_prompts, load_to_tw, make_extractor, meta_for
    ap = argparse.ArgumentParser(prog="sim.closed_loop run")
    ap.add_argument("--set", choices=["dev", "holdout"], required=True)
    ap.add_argument("--arm", choices=["gpt", "gemma", "structured"], required=True)
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--opus-budget", type=float, default=None, help="Opus 病人新呼叫的估算費用上限（USD，本次執行）")
    ap.add_argument("--gpt-budget", type=float, default=None, help="gpt 抽取累計估算費用上限（USD，快取檔累計）")
    ap.add_argument("--seed-extract", action="append", default=[],
                    help="抽取快取種子（sim.llm_extract_v2 重放的快取檔）：同模型、同送出提示全文時，同一句（轉繁後）直接沿用原始輸出、以目前程式重算")
    args = ap.parse_args(argv)
    out_dir, cache_dir = Path(args.out), Path(args.cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    stem = f"closed_{args.set}_{args.arm}{'_limit' + str(args.limit) if args.limit else ''}"
    freeze = None
    if args.set == "holdout":
        freeze = check_holdout_allowed(args.arm, args.limit, out_dir)
    # ---- 前置檢查（全部在登記保留集 arm 之前；任何一項失敗都不留下登記，可修好後重試）
    inputs = [DEV_STRUCTURED] if args.set == "dev" else [HOLDOUT_SCENARIOS, HOLDOUT_STRUCTURED, HOLDOUT_REFERENCE]
    missing = [str(f) for f in [*inputs, *map(Path, args.seed_extract)] if not Path(f).exists()]
    if missing:
        raise SystemExit(f"輸入檔不存在：{missing}")
    cache = PatientCache(DEFAULT_MODEL, DEFAULT_EFFORT, _prompt_cfg()["prompt_version"])
    cpath = cache_dir / f"patient_cache_{args.set}.json"
    cache.load(cpath)
    tw = extractor = client = None
    ex_meta: dict[str, Any] = {}
    n_seed_extract: dict[str, int] = {}
    if args.arm != "structured":
        if not os.environ.get(KEY_ENV):
            print(f"{KEY_ENV}: MISSING")
            sys.exit(2)
        client = make_client()
        tw = load_to_tw()
        extractor = make_extractor(args.arm, budget=args.gpt_budget, to_traditional=tw)   # gpt：金鑰缺少即 exit 2
        if args.arm == "gemma":
            cfg = load_prompts()
            check_lmstudio(cfg["local_base_url"], cfg["local_model"])
        ex_meta = meta_for(args.arm)
        epath = cache_dir / f"extract_cache_{args.set}_{args.arm}.json"
        history = extractor.load(epath, ex_meta, reparse=True)
        n_seed_extract = {Path(f).name: seed_extractor(extractor, Path(f), ex_meta) for f in args.seed_extract}
    if args.set == "holdout":
        register_holdout_run(args.arm, started_at=datetime.now().isoformat(timespec="seconds"), out=str(out_dir),
                             cache_dir=str(cache_dir), freeze_sha256=freeze["files"])
    cases, structured = load_set(args.set)
    if args.limit:
        cases = cases[: args.limit]
    n_seed = cache.seed(structured, source=("seed:" + (DEV_STRUCTURED if args.set == "dev" else HOLDOUT_STRUCTURED).name))
    budget = Budget(args.opus_budget)
    tracker = None if extractor is None else UsedKeys(extractor)
    keys_before, spent_before = (set(extractor.cache), extractor.spent) if extractor is not None else (set(), 0.0)
    started = datetime.now().isoformat(timespec="seconds")
    t0 = time.monotonic()
    try:
        outs = run_arm(cases, arm=args.arm, cache=cache, client=client, extractor=tracker, tw=tw, budget=budget,
                       workers=args.workers if args.arm != "gemma" else min(args.workers, 4))
    finally:
        cache.save(cpath)
        if extractor is not None:
            extractor.save(epath, ex_meta, history)
    finished = datetime.now().isoformat(timespec="seconds")
    recs = [case_record(o) for o in outs]
    rep: dict[str, Any] = {"meta": {"set": args.set, "arm": args.arm, "limit": args.limit, "started_at": started, "finished_at": finished,
                                    "wall_s": round(time.monotonic() - t0, 1), "rules_version": rules_version(),
                                    "patient": {"model": DEFAULT_MODEL, "effort": DEFAULT_EFFORT, "prompt_version": _prompt_cfg()["prompt_version"]},
                                    "extractor": ex_meta, "prompts_version": load_prompts()["prompts_version"],
                                    "file_sha256": file_hashes(), "freeze": freeze, "n_seed_entries": n_seed,
                                    "n_seed_extract": n_seed_extract if args.arm != "structured" else None,
                                    "structured_source": (DEV_STRUCTURED if args.set == "dev" else HOLDOUT_STRUCTURED).name},
                           "patient_usage": {"live_calls": sum(o["patient"].n_live for o in outs),
                                             "cached_calls": sum(o["patient"].n_cached for o in outs),
                                             "sources": dict(sum((o["patient"].sources for o in outs), Counter())),
                                             "opus_cost_usd": round(budget.spent, 4)},
                           "extractor_usage": None if extractor is None else _ex_usage(extractor, tracker.used, keys_before, spent_before),
                           "cases": recs}
    if args.set == "dev":
        rep["metrics"] = dev_metrics(outs)
    else:
        rep["metrics"] = holdout_metrics(holdout_rows(outs), cases)
    rep["extraction"] = extraction_stats(recs) if args.arm != "structured" else None
    rep["mention_conflicts"] = [c for o in outs if o["result"] is not None for c in o["result"].mention_conflicts]
    rep["mention_confirms"] = [c for o in outs if o["result"] is not None for c in o["result"].mention_confirms]
    if args.arm == "structured":
        fin = {t["case_id"]: t["final"] for t in structured}
        rep["self_check"] = {"reproduced": sum(1 for o in outs if o["result"] is not None and
                                                f"{o['result'].final.tier}{'Y' if o['result'].final.hard_stop else ''}" == fin[o["case"].id]),
                             "n": len(outs)}
    (out_dir / f"{stem}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if args.set == "holdout":
        register_holdout_run(args.arm, finished_at=finished, output=str(out_dir / f"{stem}.json"))
    summ = rep["metrics"] if args.set == "dev" else rep["metrics"]["ref_agree"]
    print(json.dumps({k: summ.get(k) for k in ("hs_sensitivity", "hs_miss", "premature", "false_hs", "under", "t9", "mean_questions",
                                                "confirms", "exact")}, ensure_ascii=False, default=str))
    print(json.dumps({"patient": rep["patient_usage"], "extractor_cost": (rep["extractor_usage"] or {}).get("cost_total_usd"),
                      "mention_conflicts": len(rep["mention_conflicts"]),
                      "errors": [r["case_id"] for r in recs if r["error"]], "self_check": rep.get("self_check")}, ensure_ascii=False))
    print(f"→ {out_dir / (stem + '.json')}")


class UsedKeys:
    """包住抽取器，記下本次執行用到的（題目, 複誦句, 句子）鍵，費用與延遲只統計這些。"""

    def __init__(self, ex: Any) -> None:
        self.ex, self.used = ex, set()
        self._lock = threading.Lock()

    def __call__(self, text: str, q: Any = None, confirm_prompt: str | None = None) -> dict[str, Any]:
        with self._lock:
            self.used.add(self.ex.key(text, q, confirm_prompt))
        return self.ex(text, q, confirm_prompt)


def _ex_usage(ex: Any, used: set, before: set, spent_before: float) -> dict[str, Any]:
    recs = [ex.cache[k] for k in used if k in ex.cache]
    new = [ex.cache[k] for k in used - before if k in ex.cache]
    return {"calls_used": len(recs), "new_calls": len(new), "reused_seed": sum(1 for r in recs if r.get("seeded_from")),
            "reused_earlier_run": len(recs) - len(new) - sum(1 for r in recs if r.get("seeded_from")),
            "cost_this_run_usd": round(ex.spent - spent_before, 4), "cost_total_usd": round(ex.spent, 4),
            "failed": sum(not r["ok"] for r in recs), "tw_changed": ex.n_tw_changed,
            "latency_new_calls": _lat([r for r in new if r["ok"] and r["latency_s"] is not None]),
            "guards": dict(Counter(g["guard"] for r in recs for g in r["diag"].get("guards", []))),
            "unclassified": [{"q": r["q"], "text": r["text"], **u} for r in recs for u in r["diag"].get("unclassified", [])]}


def _lat(recs: list[dict[str, Any]]) -> dict[str, Any]:
    xs = sorted(r["latency_s"] for r in recs)
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "median_s": round(median(xs), 3), "p95_s": round(xs[max(0, int(len(xs) * 0.95 + 0.999) - 1)], 3),
            "mean_s": round(mean(xs), 3)}


def freeze_main(argv: list[str]) -> None:
    """凍結紀錄寫在固定位置 FREEZE_PATH，已存在就拒絕（凍結只做一次）。內容：全部凍結檔與提示全文的 sha256＋時間戳。"""
    argparse.ArgumentParser(prog="sim.closed_loop freeze").parse_args(argv)
    if FREEZE_PATH.exists():
        raise SystemExit(f"{FREEZE_PATH} 已存在（凍結只做一次）")
    rec = {**freeze_record(), "frozen_at": datetime.now().isoformat(timespec="seconds")}
    FREEZE_PATH.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "run":
        run_main(sys.argv[2:])
    elif cmd == "freeze":
        freeze_main(sys.argv[2:])
    else:
        print(__doc__)
