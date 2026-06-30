"""Starful career MD ---json frontmatter helpers."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

_JSON_BLOCK = re.compile(r"---json\s*(\{.*?\})\s*---(.*)", re.DOTALL)


def parse_starful_md(raw: str) -> tuple[dict[str, Any], str] | None:
    match = _JSON_BLOCK.match(raw)
    if not match:
        return None
    try:
        meta = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None
    return meta, match.group(2)


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
