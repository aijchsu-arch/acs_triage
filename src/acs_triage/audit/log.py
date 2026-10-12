"""Append-only audit log（JSONL）。dev 用檔案；prod 候選 PostgreSQL。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..loaders import rules_version
from ..schemas import AuditEvent


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.events: list[AuditEvent] = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, call_id: str, kind: str, payload: dict[str, Any] | None = None,
             model_version: str | None = None) -> AuditEvent:
        ev = AuditEvent(ts=datetime.now(timezone.utc), call_id=call_id, kind=kind,
                        payload=payload or {}, rules_version=rules_version(), model_version=model_version)
        self.events.append(ev)
        if self.path is not None:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(ev.model_dump_json() + "\n")
        return ev
