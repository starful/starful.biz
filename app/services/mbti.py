"""MBTI type → IT career mapping helpers."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from app.config import STATIC_DIR
from app.services.jobs_cache import JOB_DATA, ensure_jobs_cache

MBTI_DATA_FILE = os.path.join(STATIC_DIR, "json", "mbti_careers.json")
MBTI_TYPE_ORDER: tuple[str, ...] = (
    "INTJ",
    "INTP",
    "ENTJ",
    "ENTP",
    "INFJ",
    "INFP",
    "ENFJ",
    "ENFP",
    "ISTJ",
    "ISFJ",
    "ESTJ",
    "ESFJ",
    "ISTP",
    "ISFP",
    "ESTP",
    "ESFP",
)
VALID_TYPES = frozenset(MBTI_TYPE_ORDER)


@lru_cache(maxsize=1)
def _load_raw() -> dict[str, Any]:
    with open(MBTI_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def normalize_mbti_type(raw: str) -> str | None:
    code = (raw or "").strip().upper()
    return code if code in VALID_TYPES else None


def list_mbti_types() -> list[dict[str, Any]]:
    """Ordered list of all types for the index page."""
    data = _load_raw().get("types", {})
    items = []
    for code in MBTI_TYPE_ORDER:
        entry = data.get(code) or {}
        items.append(
            {
                "code": code,
                "label": entry.get("label", ""),
                "summary": entry.get("summary", ""),
            }
        )
    return items


def get_mbti_type(code: str) -> dict[str, Any] | None:
    """Hydrated type payload with career links from JOB_DATA."""
    normalized = normalize_mbti_type(code)
    if not normalized:
        return None

    ensure_jobs_cache()
    entry = (_load_raw().get("types") or {}).get(normalized)
    if not entry:
        return None

    jobs_by_id = {j.get("id"): j for j in JOB_DATA.get("jobs", []) if j.get("id")}
    careers = []
    for c in entry.get("careers") or []:
        jid = c.get("id", "")
        job = jobs_by_id.get(jid)
        if not job:
            continue
        careers.append(
            {
                "id": jid,
                "name": c.get("name") or job.get("title", jid),
                "reason": c.get("reason", ""),
                "detail": c.get("detail", ""),
                "title": job.get("title", ""),
                "meta_description": job.get("meta_description", ""),
                "category": job.get("category", ""),
                "link": job.get("link") or f"/career/{jid}",
            }
        )

    related = []
    for rel in entry.get("related") or []:
        rel_code = normalize_mbti_type(rel)
        if not rel_code:
            continue
        rel_entry = (_load_raw().get("types") or {}).get(rel_code) or {}
        related.append({"code": rel_code, "label": rel_entry.get("label", "")})

    faqs = [
        {"question": f.get("q", ""), "answer": f.get("a", "")}
        for f in (entry.get("faqs") or [])
        if f.get("q") and f.get("a")
    ]

    return {
        "code": normalized,
        "label": entry.get("label", ""),
        "summary": entry.get("summary", ""),
        "intro": entry.get("intro", ""),
        "work_style": entry.get("work_style", ""),
        "avoid_env": entry.get("avoid_env", ""),
        "closing": entry.get("closing", ""),
        "strengths": list(entry.get("strengths") or []),
        "watchouts": list(entry.get("watchouts") or []),
        "careers": careers,
        "related": related,
        "faqs": faqs,
    }


def types_for_career(career_id: str, *, limit: int = 4) -> list[dict[str, str]]:
    """Reverse lookup: which MBTI types recommend this career."""
    if not career_id:
        return []
    out: list[dict[str, str]] = []
    data = _load_raw().get("types") or {}
    for code in MBTI_TYPE_ORDER:
        entry = data.get(code) or {}
        ids = {c.get("id") for c in (entry.get("careers") or [])}
        if career_id in ids:
            out.append({"code": code, "label": entry.get("label", "")})
            if len(out) >= limit:
                break
    return out


def all_mbti_type_codes() -> list[str]:
    return list(MBTI_TYPE_ORDER)
