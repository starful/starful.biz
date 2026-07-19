"""Starful career MD ---json frontmatter helpers."""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# Load app/md_parser.py directly so build_data does not import app/__init__.py
# (that pulls dotenv/FastAPI and breaks hub deploy on system Python).
_MD_PARSER_PATH = Path(__file__).resolve().parents[1] / "app" / "md_parser.py"
_spec = importlib.util.spec_from_file_location("starful_md_parser_standalone", _MD_PARSER_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load md_parser from {_MD_PARSER_PATH}")
_md_parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_md_parser)
parse_starful_md_raw = _md_parser.parse_starful_md_raw


def parse_starful_md(raw: str) -> tuple[dict[str, Any], str] | None:
    return parse_starful_md_raw(raw)


def read_starful_md(filepath: str) -> tuple[dict[str, Any], str] | None:
    if not os.path.isfile(filepath):
        return None
    with open(filepath, encoding="utf-8") as f:
        return parse_starful_md(f.read())


def write_starful_md(filepath: str, meta: dict[str, Any], body: str) -> None:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    front = f"---json\n{json.dumps(meta, ensure_ascii=False, indent=2)}\n---\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front + body.lstrip("\n"))


def file_mtime_date(filepath: str) -> str:
    return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")


def published_date(meta: dict[str, Any], filepath: str) -> str:
    pub = meta.get("published_at") or meta.get("published")
    if pub:
        return str(pub).strip()[:10]
    return file_mtime_date(filepath)


def ensure_published_at(meta: dict[str, Any], filepath: str) -> tuple[dict[str, Any], str, bool]:
    """Return (meta, YYYY-MM-DD, whether meta was updated)."""
    pub = meta.get("published_at") or meta.get("published")
    if pub:
        return meta, str(pub).strip()[:10], False
    out = dict(meta)
    date = file_mtime_date(filepath)
    out["published_at"] = date
    return out, date, True


def backfill_published_at_file(filepath: str) -> str | None:
    """Persist published_at from mtime when missing. Returns date or None if not ---json."""
    parsed = read_starful_md(filepath)
    if not parsed:
        return None
    meta, body = parsed
    meta, date, changed = ensure_published_at(meta, filepath)
    if changed:
        write_starful_md(filepath, meta, body)
    return date
