"""Resize images in staging and upload optimized PNGs to GCS."""
from __future__ import annotations

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from gcs_assets import STAGING_DIR, upload_staging_dir
from slug_utils import is_protected_asset

try:
    from PIL import Image
except ImportError:
    print("❌ Install Pillow: pip install Pillow")
    raise SystemExit(1)

MAX_WIDTH = 1200
MAX_HEIGHT = 1200


def resize_staging_images() -> None:
    if not os.path.isdir(STAGING_DIR):
        os.makedirs(STAGING_DIR, exist_ok=True)
        print(f"📭 No staging dir yet: {STAGING_DIR}")
        print("   Put raw PNGs here or run generate_images.py first.")
        return

    valid = (".png", ".jpg", ".jpeg", ".webp")
    files = [f for f in os.listdir(STAGING_DIR) if f.lower().endswith(valid)]
    if not files:
        print("📭 No images in staging — run generate_images.py first or add PNGs to staging.")
        return

    print(f"🚀 Resizing {len(files)} staging image(s) → upload to GCS...")

    for filename in files:
        name_only, ext = os.path.splitext(filename)
        if is_protected_asset(name_only):
            continue

        filepath = os.path.join(STAGING_DIR, filename)
        out_path = os.path.join(STAGING_DIR, f"{name_only}.png")

        try:
            with Image.open(filepath) as img:
                img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                img.save(out_path, format="PNG", optimize=True)

            if ext.lower() != ".png" and filepath != out_path:
                os.remove(filepath)
            print(f"✅ {name_only}.png")
        except OSError as e:
            print(f"❌ {filename}: {e}")

    uploaded = upload_staging_dir()
    for name in list(os.listdir(STAGING_DIR)):
        path = os.path.join(STAGING_DIR, name)
        if os.path.isfile(path):
            os.remove(path)

    print(f"\n🎉 Done — {uploaded} file(s) uploaded to GCS")


if __name__ == "__main__":
    resize_staging_images()
