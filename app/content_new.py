"""Homepage NEW badge helpers (published date vs rolling cutoff)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

NEW_CONTENT_DAYS = 14


def new_content_cutoff(days: int | None = None) -> str:
    span = NEW_CONTENT_DAYS if days is None else days
    return (date.today() - timedelta(days=span)).isoformat()


def is_content_new(published: str | None, *, days: int | None = None) -> bool:
    if not published:
        return False
    pub = str(published).strip()[:10]
    if len(pub) < 10:
        return False
    return pub >= new_content_cutoff(days)


def enrich_item(item: dict[str, Any], *, days: int | None = None) -> dict[str, Any]:
    out = dict(item)
    pub = out.get("published") or out.get("date") or ""
    if pub:
        out["published"] = str(pub)[:10]
    out["is_new"] = is_content_new(out.get("published"), days=days)
    return out


def enrich_items(items: list[dict[str, Any]], *, days: int | None = None) -> list[dict[str, Any]]:
    return [enrich_item(i, days=days) for i in items]
