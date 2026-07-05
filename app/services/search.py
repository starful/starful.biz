"""Career search scoring and query expansion."""
from __future__ import annotations

import re
import unicodedata
from typing import Set

SEARCH_SYNONYMS: dict[str, set[str]] = {
    "backend": {"backend", "バックエンド", "server", "api"},
    "frontend": {"frontend", "フロントエンド", "ui", "web"},
    "fullstack": {"fullstack", "full stack", "フルスタック"},
    "ai": {"ai", "ml", "machine learning", "人工知能", "機械学習"},
    "data": {"data", "データ", "analytics", "分析"},
    "cloud": {"cloud", "クラウド", "aws", "gcp", "azure"},
    "security": {"security", "セキュリティ", "appsec", "cybersecurity"},
    "devops": {"devops", "sre", "platform", "インフラ"},
    "product": {"product", "pm", "プロダクト", "企画"},
    "design": {"design", "デザイン", "ux", "ui"},
    "marketing": {"marketing", "マーケティング", "growth", "seo"},
}


def normalize_search_text(text: str) -> str:
    """Normalize case, width, and whitespace for robust matching."""
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def expand_query_terms(query: str) -> Set[str]:
    base = normalize_search_text(query)
    if not base:
        return set()

    terms: Set[str] = {base}
    split_terms = {t for t in re.split(r"[\s/,_-]+", base) if t}
    terms.update(split_terms)

    for token in list(terms):
        for group in SEARCH_SYNONYMS.values():
            if token in group:
                terms.update(group)
    return terms


def score_job_for_terms(job: dict, terms: Set[str]) -> int:
    title = normalize_search_text(job.get("title", ""))
    category = normalize_search_text(job.get("category", ""))
    tags = " ".join(job.get("tags", []) or [])
    tags_text = normalize_search_text(tags)
    desc = normalize_search_text(job.get("meta_description", ""))

    score = 0
    for term in terms:
        if not term:
            continue
        if term == title:
            score += 120
        elif term in title:
            score += 60

        if term == category:
            score += 50
        elif term in category:
            score += 30

        if term in tags_text:
            score += 35

        if term in desc:
            score += 10
    return score


def search_jobs(jobs: list[dict], query: str) -> list[dict]:
    terms = expand_query_terms(query)
    if not terms:
        return []

    scored = []
    for job in jobs:
        score = score_job_for_terms(job, terms)
        if score > 0:
            scored.append((score, job))

    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    return [job for _, job in scored]
