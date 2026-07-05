"""GCS image asset helpers (gs://starful-biz-assets = source of truth)."""
from __future__ import annotations

import os
import subprocess

DEFAULT_BUCKET = os.getenv("STARFUL_GCS_BUCKET", "gs://starful-biz-assets")
DEFAULT_PUBLIC_BASE = os.getenv(
    "STARFUL_GCS_IMG_BASE", "https://storage.googleapis.com/starful-biz-assets"
).rstrip("/")

STAGING_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tmp",
    "image-staging",
)


def _run_gsutil(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["gsutil", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def blob_uri(name: str) -> str:
    base = DEFAULT_BUCKET.rstrip("/")
    return f"{base}/{name.lstrip('/')}"


def blob_exists(name: str) -> bool:
    proc = _run_gsutil(["stat", blob_uri(name)], check=False)
    return proc.returncode == 0


def upload_file(local_path: str, blob_name: str) -> None:
    _run_gsutil(["cp", local_path, blob_uri(blob_name)])


def download_file(blob_name: str, local_path: str) -> None:
    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
    _run_gsutil(["cp", blob_uri(blob_name), local_path])


def upload_staging_dir(staging_dir: str | None = None) -> int:
    """Upload all PNG/JPG files from staging to GCS. Returns count uploaded."""
    root = staging_dir or STAGING_DIR
    if not os.path.isdir(root):
        return 0
    uploaded = 0
    for name in sorted(os.listdir(root)):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        local = os.path.join(root, name)
        if not os.path.isfile(local):
            continue
        upload_file(local, name)
        uploaded += 1
    return uploaded


def list_career_pngs() -> set[str]:
    """Return set of blob basenames (e.g. data_scientist.png) in bucket root."""
    proc = _run_gsutil(["ls", DEFAULT_BUCKET], check=False)
    if proc.returncode != 0:
        return set()
    names: set[str] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or not line.endswith(".png"):
            continue
        names.add(line.rsplit("/", 1)[-1])
    return names


def ensure_default_local(dest_dir: str) -> str | None:
    """Download default.png from GCS into dest_dir. Returns local path or None."""
    os.makedirs(dest_dir, exist_ok=True)
    for name in ("default.png", "default.jpg"):
        local = os.path.join(dest_dir, name)
        if blob_exists(name):
            download_file(name, local)
            return local
    legacy = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app",
        "static",
        "img",
        "default.png",
    )
    if os.path.isfile(legacy):
        return legacy
    return None
