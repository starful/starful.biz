"""Guards so GSC-retired careers are not regenerated.

Source of truth: app.seo_helpers.REMOVED_CAREER_SLUGS
"""
from __future__ import annotations

import os
import sys
from typing import Iterable

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
for _p in (SCRIPTS_DIR, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.seo_helpers import REMOVED_CAREER_SLUGS, is_removed_career  # noqa: E402
from slug_utils import normalize_slug, position_slug  # noqa: E402

__all__ = [
    "REMOVED_CAREER_SLUGS",
    "is_blocked_slug",
    "is_blocked_position",
    "filter_related_jobs",
    "existing_content_slugs",
]


def is_blocked_slug(slug: str | None) -> bool:
    return is_removed_career(normalize_slug(slug or ""))


def is_blocked_position(position_name: str | None) -> bool:
    return is_blocked_slug(position_slug(position_name or ""))


def existing_content_slugs(contents_dir: str) -> set[str]:
    out: set[str] = set()
    if not os.path.isdir(contents_dir):
        return out
    for name in os.listdir(contents_dir):
        if name.endswith(".md"):
            out.add(normalize_slug(name[:-3]))
    return out


def filter_related_jobs(
    related: Iterable[str] | None,
    *,
    contents_dir: str | None = None,
    allow: set[str] | None = None,
    limit: int = 3,
) -> list[str]:
    """Drop retired / unknown related_jobs; keep existing content slugs when possible."""
    allow_set = allow if allow is not None else (
        existing_content_slugs(contents_dir) if contents_dir else None
    )
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in related or []:
        slug = normalize_slug(str(raw))
        if not slug or slug in seen or is_blocked_slug(slug):
            continue
        if allow_set is not None and slug not in allow_set:
            continue
        seen.add(slug)
        cleaned.append(slug)
        if len(cleaned) >= limit:
            break
    return cleaned
