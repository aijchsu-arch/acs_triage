"""OpenAI adapter（M3b，D-36、D-38）：Responses API ＋ strict JSON schema。

- 直接 HTTP 呼叫 `POST https://api.openai.com/v1/responses`（不裝 SDK）。
- 金鑰只讀 ACS_OPENAI_API_KEY（D-31 修訂），不印出；錯誤時只回報狀態碼與錯誤代碼，不回報可能含遮罩金鑰的訊息。
- 只用合成資料（D-10）。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable

KEY_ENV = "ACS_OPENAI_API_KEY"
ENDPOINT = "https://api.openai.com/v1/responses"
_RETRY_STATUS = {429, 500, 502, 503}

Transport = Callable[[str, dict[str, str], bytes], tuple[int, dict[str, str], Any]]


def _urllib_transport(url: str, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, dict(r.headers), json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read())
        except Exception:  # noqa: BLE001
            payload = None
        return e.code, dict(e.headers or {}), payload


class OpenAIStructured:
    def __init__(self, *, model: str, effort: str, api_key: str | None = None, transport: Transport | None = None,
                 max_retries: int = 3) -> None:
        self.model = model
        self.effort = effort
        self.api_key = api_key if api_key is not None else os.environ[KEY_ENV]
        self.transport = transport or _urllib_transport
        self.max_retries = max_retries

    def ask(self, system: str, user: str, schema: dict[str, Any], name: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        """回傳 (parsed_json, usage, response_model)。"""
        body = json.dumps({
            "model": self.model,
            "input": [{"role": "developer", "content": system}, {"role": "user", "content": user}],
            "reasoning": {"effort": self.effort},
            "text": {"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}},
            "store": False,
        }, ensure_ascii=False).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(self.max_retries + 1):
            status, rh, data = self.transport(ENDPOINT, headers, body)
            if status == 200:
                break
            if status in _RETRY_STATUS and attempt < self.max_retries:
                time.sleep(min(float(rh.get("retry-after") or rh.get("Retry-After") or 2 ** attempt), 30.0))
                continue
            err = (data or {}).get("error") or {}
            raise RuntimeError(f"OpenAI HTTP {status} code={err.get('code')} type={err.get('type')}")
        if data.get("status") != "completed":
            raise RuntimeError(f"OpenAI response status={data.get('status')} "
                               f"reason={(data.get('incomplete_details') or {}).get('reason')}")
        texts = [c["text"] for item in data.get("output", []) if item.get("type") == "message"
                 for c in item.get("content", []) if c.get("type") == "output_text"]
        if not texts:
            raise RuntimeError(f"OpenAI response 無 output_text（output types={[i.get('type') for i in data.get('output', [])]}）")
        return json.loads(texts[-1]), data.get("usage") or {}, data.get("model", self.model)


def usage_cost(usage: dict[str, Any], price_in: float, price_cached: float, price_out: float) -> float:
    """USD；input_tokens 含 cached_tokens。output_tokens 含 reasoning tokens。"""
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0
    inp = (usage.get("input_tokens") or 0) - cached
    return (inp * price_in + cached * price_cached + (usage.get("output_tokens") or 0) * price_out) / 1e6
