#!/usr/bin/env python3
"""Rename/consolidate starful image assets (local + GCS). One slug = one .png."""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from slug_utils import (  # noqa: E402
    canonical_starful_filename,
    is_protected_asset,
    legacy_hyphen_filename,
    normalize_image_filename,
    normalize_slug,
)

IMG_DIR = os.path.join(BASE_DIR, "app", "static", "img")
DEFAULT_BUCKET = "gs://starful-biz-assets"
VALID_EXT = (".png", ".jpg", ".jpeg", ".webp")


def _file_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _consolidate_stem_local(img_dir: str, stem: str, files: list[str]) -> int:
    """Keep newest variant as {stem}.png; remove siblings."""
    if is_protected_asset(stem):
        return 0
    canonical = canonical_starful_filename(stem)
    canon_path = os.path.join(img_dir, canonical)
    best_path = max(files, key=_file_mtime)
    best_mtime = _file_mtime(best_path)
    changed = 0

    if best_path != canon_path:
        if os.path.isfile(canon_path) and _file_mtime(canon_path) >= best_mtime:
            pass
        else:
            if best_path.lower().endswith(".png"):
                os.replace(best_path, canon_path)
            else:
                try:
                    from PIL import Image

                    with Image.open(best_path) as img:
                        if img.mode not in ("RGB", "RGBA"):
                            img = img.convert("RGBA")
                        img.save(canon_path, format="PNG", optimize=True)
                except Exception as exc:
                    print(f"skip convert {best_path}: {exc}")
                    return 0
            changed += 1
            print(f"local canonical: {os.path.basename(best_path)} -> {canonical}")

    for path in files:
        if path != canon_path and os.path.isfile(path):
            os.remove(path)
            changed += 1
            print(f"local removed duplicate: {os.path.basename(path)}")
    return changed


def migrate_local(img_dir: str) -> int:
    if not os.path.isdir(img_dir):
        print(f"skip: missing {img_dir}")
        return 0
    by_stem: dict[str, list[str]] = defaultdict(list)
    changed = 0
    for name in sorted(os.listdir(img_dir)):
        if not name.lower().endswith(VALID_EXT):
            continue
        stem = os.path.splitext(name)[0]
        if is_protected_asset(stem):
            continue
        norm_stem = normalize_slug(stem)
        by_stem[norm_stem].append(os.path.join(img_dir, name))

    for stem, paths in by_stem.items():
        # hyphen legacy names → same stem bucket
        changed += _consolidate_stem_local(img_dir, stem, paths)

    # hyphen-only renames without duplicates
    for name in sorted(os.listdir(img_dir)):
        if not name.lower().endswith(VALID_EXT):
            continue
        stem = os.path.splitext(name)[0]
        if is_protected_asset(stem):
            continue
        canonical = normalize_image_filename(name)
        if canonical == name:
            continue
        src = os.path.join(img_dir, name)
        dst = os.path.join(img_dir, canonical)
        if os.path.isfile(dst):
            os.remove(src)
            print(f"removed duplicate legacy: {name}")
        else:
            os.rename(src, dst)
            print(f"renamed: {name} -> {canonical}")
        changed += 1
    return changed


def _gcloud_ls_l(bucket: str) -> list[tuple[str, float, int]]:
    proc = subprocess.run(
        ["gcloud", "storage", "ls", "-l", bucket],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(f"GCS list failed: {proc.stderr or proc.stdout}")
        return []
    rows: list[tuple[str, float, int]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("TOTAL") or not line.startswith("gs://"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            size = int(parts[0])
        except ValueError:
            continue
        uri = parts[1]
        ts_str = parts[2]
        from datetime import datetime, timezone

        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            ts = 0.0
        rows.append((uri, ts, size))
    return rows


def cleanup_gcs(bucket: str) -> int:
    prefix = bucket.rstrip("/") + "/"
    rows = _gcloud_ls_l(bucket)
    if not rows:
        return 0

    by_stem: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
    changed = 0
    for uri, ts, _size in rows:
        fname = uri.split("/")[-1]
        if not fname.lower().endswith(VALID_EXT):
            continue
        stem = os.path.splitext(fname)[0]
        if is_protected_asset(stem):
            continue
        by_stem[normalize_slug(stem)].append((uri, ts, fname))

    for stem, items in by_stem.items():
        canonical = canonical_starful_filename(stem)
        canon_uri = prefix + canonical
        best_uri, best_ts, best_name = max(items, key=lambda x: x[1])
        # remove non-canonical siblings
        for uri, _ts, fname in items:
            if fname == canonical:
                continue
            if uri == best_uri and not fname.lower().endswith(".png"):
                # promote best jpg → png
                tmp = f"/tmp/starful_gcs_{stem}.bin"
                subprocess.run(["gcloud", "storage", "cp", uri, tmp], check=False)
                try:
                    from PIL import Image

                    with Image.open(tmp) as img:
                        if img.mode not in ("RGB", "RGBA"):
                            img = img.convert("RGBA")
                        out = io.BytesIO()
                        img.save(out, format="PNG", optimize=True)
                    out_tmp = tmp + ".png"
                    with open(out_tmp, "wb") as f:
                        f.write(out.getvalue())
                    subprocess.run(
                        [
                            "gcloud",
                            "storage",
                            "cp",
                            out_tmp,
                            canon_uri,
                            "--cache-control=no-cache, max-age=0, must-revalidate",
                        ],
                        check=False,
                    )
                    os.remove(out_tmp)
                    print(f"GCS promoted {fname} -> {canonical}")
                    changed += 1
                except Exception as exc:
                    print(f"GCS promote failed {fname}: {exc}")
                finally:
                    if os.path.isfile(tmp):
                        os.remove(tmp)
            subprocess.run(["gcloud", "storage", "rm", uri], check=False)
            if fname != canonical:
                print(f"GCS removed duplicate: {fname}")
                changed += 1

        # legacy hyphen blob
        legacy = legacy_hyphen_filename(canonical)
        if legacy:
            leg_uri = prefix + legacy
            check = subprocess.run(["gcloud", "storage", "ls", leg_uri], capture_output=True, check=False)
            if check.returncode == 0:
                subprocess.run(["gcloud", "storage", "rm", leg_uri], check=False)
                print(f"GCS removed hyphen legacy: {legacy}")
                changed += 1

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize starful image filenames")
    parser.add_argument("--gcs", action="store_true", help="Also clean gs://starful-biz-assets")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    args = parser.parse_args()

    n_local = migrate_local(IMG_DIR)
    print(f"local: {n_local} file(s) adjusted")
    if args.gcs:
        n_gcs = cleanup_gcs(args.bucket)
        print(f"GCS: {n_gcs} blob(s) adjusted")


if __name__ == "__main__":
    main()
