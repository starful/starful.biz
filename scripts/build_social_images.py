#!/usr/bin/env python3
"""Optional: pre-generate career social JPEGs (runtime /social/ also works from GCS).

Not run during Docker build — images are served from GCS at deploy time.
Usage: python scripts/build_social_images.py
"""
from __future__ import annotations

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import GCS_IMG_BASE, parse_starful_md
from app.social_share import (
    career_thumbnail_url,
    fetch_social_jpeg,
    load_career_meta,
    static_social_image_key,
)

CONTENTS_DIR = os.path.join(BASE_DIR, "app", "contents")
OUTPUT_DIR = os.path.join(BASE_DIR, "app", "static", "social")


def career_slugs() -> list[str]:
    return sorted(
        filename[:-3]
        for filename in os.listdir(CONTENTS_DIR)
        if filename.endswith(".md")
    )


def build_career_images() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ok = 0
    failed: list[str] = []
    for slug in career_slugs():
        image_key = static_social_image_key(slug)
        output_path = os.path.join(OUTPUT_DIR, f"{image_key}.jpg")
        try:
            load_career_meta(slug, parse_starful_md)
            source = career_thumbnail_url(GCS_IMG_BASE, slug)
            data = fetch_social_jpeg(source)
            with open(output_path, "wb") as handle:
                handle.write(data)
            ok += 1
        except Exception as exc:
            failed.append(f"{slug}: {exc}")
    print(f"Built {ok} career social images in {OUTPUT_DIR}")
    if failed:
        print(f"Skipped {len(failed)} careers:")
        for line in failed[:10]:
            print(f"  - {line}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")


if __name__ == "__main__":
    build_career_images()
