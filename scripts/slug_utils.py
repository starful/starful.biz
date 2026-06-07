"""Starful slug / image filename rules (snake_case, no hyphens in assets)."""
from __future__ import annotations

import re

# favicon-32x32, apple-touch-icon 등 표준 웹 아이콘은 하이픈 유지
PROTECTED_ASSET_PREFIXES = ("favicon", "apple-touch")
PROTECTED_ASSET_NAMES = frozenset({"default", "default_og", "logo"})


def is_protected_asset(stem: str) -> bool:
    s = (stem or "").lower()
    if s in PROTECTED_ASSET_NAMES:
        return True
    return any(s.startswith(p) for p in PROTECTED_ASSET_PREFIXES)


def position_slug(name: str) -> str:
    """position_name → snake_case id."""
    s = (name or "").strip().lower()
    for src, dst in (
        ("/", "_"),
        (" ", "_"),
        ("-", "_"),
        ("(", ""),
        (")", ""),
        (",", ""),
        ('"', ""),
    ):
        s = s.replace(src, dst)
    return normalize_slug(s)


def normalize_slug(slug: str) -> str:
    """Career / image stem: lowercase snake_case only."""
    s = (slug or "").strip().lower().replace("-", "_")
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def normalize_image_filename(filename: str) -> str:
    """Normalize asset filename; preserve favicon / apple-touch names."""
    if not filename or "." not in filename:
        stem = normalize_slug(filename)
        return f"{stem}.png" if stem else filename
    stem, ext = filename.rsplit(".", 1)
    if is_protected_asset(stem):
        return filename
    norm = normalize_slug(stem)
    return f"{norm}.{ext.lower()}" if norm else filename


def canonical_starful_filename(slug: str) -> str:
    return f"{normalize_slug(slug)}.png"


def legacy_hyphen_filename(filename: str) -> str | None:
    """Underscore canonical name → legacy hyphen variant (for cleanup)."""
    if not filename or "." not in filename:
        return None
    stem, ext = filename.rsplit(".", 1)
    if is_protected_asset(stem) or "-" in stem:
        return None
    if "_" not in stem:
        return None
    return f"{stem.replace('_', '-')}.{ext.lower()}"
