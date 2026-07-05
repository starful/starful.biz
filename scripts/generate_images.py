"""Create missing career thumbnails on GCS (from default.png)."""
from __future__ import annotations

import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from gcs_assets import STAGING_DIR, blob_exists, ensure_default_local
from slug_utils import normalize_slug

CONTENTS_DIR = os.path.join(BASE_DIR, "app", "contents")


def generate_images_by_copy() -> None:
    """For each career slug missing on GCS, copy default.png and upload."""
    source_path = ensure_default_local(STAGING_DIR)
    if not source_path:
        print("❌ default.png not found on GCS or locally")
        return

    if not os.path.isdir(CONTENTS_DIR):
        print(f"❌ 콘텐츠 디렉토리가 없습니다: {CONTENTS_DIR}")
        return

    os.makedirs(STAGING_DIR, exist_ok=True)
    md_files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    print(f"📂 {len(md_files)} contents — GCS bucket is source of truth")

    copy_count = 0
    skip_count = 0

    for filename in md_files:
        slug = normalize_slug(filename.replace(".md", ""))
        blob_name = f"{slug}.png"

        if blob_exists(blob_name):
            skip_count += 1
            continue

        target_path = os.path.join(STAGING_DIR, blob_name)
        try:
            shutil.copy2(source_path, target_path)
            copy_count += 1
            print(f"✅ staged ({copy_count}): {blob_name}")
        except OSError as e:
            print(f"❌ {slug} copy failed: {e}")

    print("\n" + "=" * 40)
    print("✨ Staging complete (run resize_images.py to optimize + upload)")
    print(f"   - newly staged: {copy_count}")
    print(f"   - already on GCS: {skip_count}")
    print("=" * 40)


if __name__ == "__main__":
    generate_images_by_copy()
