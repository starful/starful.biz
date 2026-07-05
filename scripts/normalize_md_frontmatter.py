#!/usr/bin/env python3
"""Normalize ---json career MD to canonical fields (slug, category, meta_description)."""
from __future__ import annotations

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from md_metadata import ensure_published_at, read_starful_md, write_starful_md
from slug_utils import normalize_slug

CONTENTS_DIR = os.path.join(BASE_DIR, "app", "contents")
DEFAULT_CATEGORY = "engineering"


def normalize_meta(meta: dict, slug: str, filepath: str) -> tuple[dict, bool]:
    out = dict(meta)
    changed = False

    if not out.get("slug"):
        out["slug"] = slug
        changed = True

    if not out.get("category"):
        out["category"] = DEFAULT_CATEGORY
        changed = True

    desc = out.get("meta_description") or out.get("description") or out.get("seo_description")
    if desc and out.get("meta_description") != desc:
        out["meta_description"] = str(desc).strip()[:160]
        changed = True

    if not out.get("title"):
        out["title"] = slug.replace("_", " ").title()
        changed = True

    out2, date, pub_changed = ensure_published_at(out, filepath)
    if pub_changed:
        out2["published_at"] = date
        changed = True
    elif out2.get("published_at") and out2.get("published_at") != out.get("published_at"):
        changed = True

    return out2, changed


def main() -> None:
    updated = 0
    for filename in sorted(os.listdir(CONTENTS_DIR)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(CONTENTS_DIR, filename)
        parsed = read_starful_md(filepath)
        if not parsed:
            continue
        meta, body = parsed
        slug = normalize_slug(meta.get("slug") or filename[:-3])
        meta, changed = normalize_meta(meta, slug, filepath)
        if changed:
            write_starful_md(filepath, meta, body)
            updated += 1
    print(f"Normalized {updated} markdown file(s) in {CONTENTS_DIR}")


if __name__ == "__main__":
    main()
