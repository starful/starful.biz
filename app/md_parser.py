"""Starful career Markdown frontmatter parsing (---json and YAML ---)."""
from __future__ import annotations

import json
import re
from typing import Any

_JSON_BLOCK = re.compile(r"\A---json\s*(\{.*?\})\s*---(.*)", re.DOTALL)
_YAML_BLOCK = re.compile(r"\A---\n(?!json)(.*?)\n---\n(.*)", re.DOTALL)


def _parse_yaml_block(block: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        meta[key.strip()] = value.strip()
    return _normalize_yaml_meta(meta)


def _normalize_yaml_meta(raw: dict[str, Any]) -> dict[str, Any]:
    """Map YAML frontmatter keys to Starful metadata shape."""
    meta = dict(raw)
    if raw.get("description"):
        meta["meta_description"] = raw["description"]
    elif raw.get("seo_description"):
        meta["meta_description"] = raw["seo_description"]
    return meta


def parse_starful_md_raw(raw: str) -> tuple[dict[str, Any], str] | None:
    """Parse raw markdown content. Returns None if no recognized frontmatter."""
    text = raw.lstrip("\ufeff")

    match = _JSON_BLOCK.match(text)
    if match:
        try:
            meta = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
        return meta, match.group(2)

    match = _YAML_BLOCK.match(text)
    if match:
        meta = _parse_yaml_block(match.group(1))
        if meta:
            return meta, match.group(2)

    return None


def parse_starful_md(filepath: str) -> tuple[dict[str, Any], str]:
    """Parse a career markdown file (app runtime behavior).

    Returns ({}, \"\") on missing file or parse failure.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content_raw = f.read()
        parsed = parse_starful_md_raw(content_raw)
        if parsed:
            return parsed
        return {}, content_raw
    except Exception:
        return {}, ""
