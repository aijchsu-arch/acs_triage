"""YAML 載入器：clinical_rules、question bank、scenarios、scripts、extraction patterns。"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .schemas import Question

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=None)
def load_clinical_rules() -> dict[str, Any]:
    return _load_yaml(DATA_DIR / "clinical_rules.yaml")


def rules_version() -> str:
    return str(load_clinical_rules()["rules_version"])


def doc_rules_version() -> str:
    """從 docs/CLINICAL_RULES.md 頂部讀 rules_version，供一致性測試。"""
    text = (DOCS_DIR / "CLINICAL_RULES.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*rules_version\*\*:\s*([0-9]+\.[0-9]+\.[0-9]+)", text)
    if not m:
        raise ValueError("docs/CLINICAL_RULES.md 找不到 rules_version")
    return m.group(1)


def doc_red_flag_ids() -> list[str]:
    text = (DOCS_DIR / "CLINICAL_RULES.md").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^\| (RF-\d{2}) \|", text, flags=re.M)))


@lru_cache(maxsize=None)
def load_question_bank() -> dict[str, Any]:
    return _load_yaml(DATA_DIR / "question_bank_seed.yaml")


@lru_cache(maxsize=None)
def questions() -> list[Question]:
    return [Question(**q) for q in load_question_bank()["questions"]]


@lru_cache(maxsize=None)
def question_by_id() -> dict[str, Question]:
    return {q.id: q for q in questions()}


@lru_cache(maxsize=None)
def slot_defs() -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in load_question_bank()["slots"]}


@lru_cache(maxsize=None)
def load_scripts() -> dict[str, Any]:
    return _load_yaml(DATA_DIR / "scripts_zh.yaml")


@lru_cache(maxsize=None)
def load_extraction_patterns() -> dict[str, Any]:
    return _load_yaml(DATA_DIR / "extraction_patterns.yaml")


def load_scenarios(name: str) -> dict[str, Any]:
    """name ∈ {"v0.2", "midband"}。"""
    fname = {"v0.2": "scenarios_v0.2.yaml", "midband": "scenarios_midband_v0.1.yaml"}[name]
    return _load_yaml(DATA_DIR / fname)


def all_scenarios() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name in ("v0.2", "midband"):
        d = load_scenarios(name)
        for sc in d["scenarios"]:
            sc = dict(sc)
            sc["_file"] = name
            out.append(sc)
    return out
