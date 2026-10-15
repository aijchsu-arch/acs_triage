"""Jev（TypeSafe AI）adapter（BLUEPRINT §5、M3a、D-36）。

- 直接 HTTP 呼叫 `POST https://api.typesafe.ai/v1/systemone`（不裝 SDK）；模型鎖定版本（`data/jev_questions.yaml`）。
- 只送英文 slot 結構（Q-02），不送中文逐字稿；只用合成資料（D-10）。
- 金鑰只讀 ACS_JEV_API_KEY，不印出（D-31）。
- choice 題的選項每次打亂順序（官方：jev-1.13 偏好第一個選項）；noul 的信心以 |2p−1| 計算（官方建議）。
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from ..loaders import DATA_DIR, _load_yaml, slot_defs
from ..schemas import Decision, TypedQuestion

KEY_ENV = "ACS_JEV_API_KEY"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
_RETRY_STATUS = {429, 529}

# transport(url, headers, body_bytes) -> (status, response_headers, response_json)
Transport = Callable[[str, dict[str, str], bytes], tuple[int, dict[str, str], Any]]


def load_config() -> dict[str, Any]:
    cfg = _load_yaml(DATA_DIR / "jev_questions.yaml")
    if cfg.get("status") != "approved":
        raise RuntimeError("data/jev_questions.yaml 尚未經 Clinical Owner 核可（status != approved）")
    return cfg


def _urllib_transport(url: str, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read())
        except Exception:  # noqa: BLE001 — 錯誤內容不是 JSON 時保留狀態碼即可
            payload = None
        return e.code, dict(e.headers or {}), payload


def slot_state(slots: dict[str, Any], preamble: str, mode: str = "all") -> dict[str, Any]:
    """英文 slot 結構。
    mode="all"：全部 slot 都列出，未知者為 "unknown"（M3a 基線）。
    mode="known"：只列已知 slot，未知者只列名稱於 not_yet_asked（M3a 對照實驗，減少無關內容）。
    """
    if mode == "known":
        return {"record": preamble,
                "findings": {k: slots[k] for k in sorted(slot_defs()) if slots.get(k) is not None},
                "not_yet_asked": [k for k in sorted(slot_defs()) if slots.get(k) is None]}
    findings = {k: ("unknown" if slots.get(k) is None else slots[k]) for k in sorted(slot_defs())}
    return {"record": preamble, "findings": findings}


def triage_questions(cfg: dict[str, Any], context: str) -> list[TypedQuestion]:
    p = cfg["principles"].strip()
    return [
        TypedQuestion(kind="choice", prompt=f"{cfg['tier']['instructions']}\n\n{p}",
                      choices=list(cfg["tier"]["criteria"]), criteria=dict(cfg["tier"]["criteria"]), context=context),
        TypedQuestion(kind="yes_no", prompt=f"{cfg['sufficient']['instructions'].strip()}\n\n{p}",
                      criteria=dict(cfg["sufficient"]["criteria"]), context=context),
    ]


class JevAdapter:
    def __init__(self, *, api_key: str | None = None, model: str | None = None, transport: Transport | None = None,
                 seed: int | str = 0, max_retries: int = 3) -> None:
        self.api_key = api_key if api_key is not None else os.environ[KEY_ENV]
        self.model_version = model or load_config()["model"]
        self.transport = transport or _urllib_transport
        self.rng = random.Random(seed)
        self.max_retries = max_retries
        self.last_model: str | None = None
        self.last_usage: dict[str, Any] = {}

    def _question(self, q: TypedQuestion) -> dict[str, Any]:
        if q.kind == "yes_no":
            out: dict[str, Any] = {"type": "noul", "instructions": q.prompt}
            if q.criteria:
                out["criteria"] = {"true": q.criteria["true"], "false": q.criteria["false"]}
            return out
        if q.kind == "choice":
            names = list(q.choices or (q.criteria or {}))
            self.rng.shuffle(names)
            crit = q.criteria or {n: n for n in names}
            return {"type": "choice", "instructions": q.prompt, "criteria": {n: crit[n] for n in names}}
        raise ValueError(f"unsupported kind: {q.kind}")

    def decide(self, q: TypedQuestion) -> Decision:
        return self.decide_many([q])[0]

    def decide_many(self, qs: list[TypedQuestion]) -> list[Decision]:
        if len({q.context for q in qs}) != 1:
            raise ValueError("decide_many：同一次呼叫的題目必須共用同一份 state")
        body = json.dumps({"model": self.model_version, "state": json.loads(qs[0].context),
                           "questions": {f"q{i}": self._question(q) for i, q in enumerate(qs)}},
                          ensure_ascii=False).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(self.max_retries + 1):
            status, rh, data = self.transport(ENDPOINT, headers, body)
            if status == 200:
                break
            if status in _RETRY_STATUS and attempt < self.max_retries:
                wait = float(rh.get("retry-after") or rh.get("Retry-After") or 2 ** attempt)
                time.sleep(min(wait, 30.0))
                continue
            raise RuntimeError(f"Jev HTTP {status}: {data}")
        self.last_model = data.get("model")
        self.last_usage = data.get("usage") or {}
        version = self.last_model or self.model_version
        out: list[Decision] = []
        for i, q in enumerate(qs):
            a = data["answers"][f"q{i}"]
            if q.kind == "yes_no":
                p = float(a["noul"])
                out.append(Decision(answer=p >= 0.5, confidence=abs(2 * p - 1), model_version=version,
                                    probabilities={"true": p}))
            else:
                out.append(Decision(answer=a["choice"], confidence=float(a["confidence"]), model_version=version,
                                    probabilities={k: float(v) for k, v in (a.get("probabilities") or {}).items()}))
        return out
