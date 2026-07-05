"""Image URL helpers and static img serving."""
from __future__ import annotations

import os
from urllib.parse import urljoin

from fastapi import Request
from fastapi.responses import FileResponse, RedirectResponse

from app.config import (
    BASE_URL,
    BRAND_LOGO_FILE,
    GCS_IMG_BASE,
    LOCAL_IMG_NAMES,
    STATIC_DIR,
)
from app.services.jobs_cache import JOB_DATA, ensure_jobs_cache


def career_img_url(slug: str) -> str:
    """커리어 카드 썸네일 — GCS 직접 참조 (okadmin 업로드 즉시 반영)."""
    ensure_jobs_cache()
    published = ""
    for job in JOB_DATA.get("jobs", []):
        if job.get("id") == slug:
            published = str(job.get("published") or "")
            break
    base = f"{GCS_IMG_BASE}/{slug}.png"
    v = str(published).strip()[:10]
    if len(v) >= 8:
        return f"{base}?v={v}"
    return base


def gcs_or_static_img(filename: str, cache_v: str | None = None) -> str:
    if filename in LOCAL_IMG_NAMES or filename.startswith(("favicon", "apple-touch")):
        return f"/static/img/{filename}"
    url = f"{GCS_IMG_BASE}/{filename}"
    v = str(cache_v or "").strip()[:10]
    if len(v) >= 8:
        return f"{url}?v={v}"
    return url


async def serve_img(filename: str, request: Request):
    """이미지는 GCS가 기준 — okadmin 업로드 즉시 반영."""
    local_path = os.path.join(STATIC_DIR, "img", filename)
    if filename in LOCAL_IMG_NAMES or filename.startswith(("favicon", "apple-touch")):
        if os.path.isfile(local_path):
            return FileResponse(local_path)
    url = f"{GCS_IMG_BASE}/{filename}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers = {"Cache-Control": "no-cache, must-revalidate"}
    return RedirectResponse(url, status_code=302, headers=headers)


def absolute_static_url(path: str) -> str:
    if not path:
        return f"{GCS_IMG_BASE}/{BRAND_LOGO_FILE}"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("/static/img/"):
        fname = path.rsplit("/", 1)[-1]
        if fname in LOCAL_IMG_NAMES or fname.startswith(("favicon", "apple-touch")):
            return urljoin(f"{BASE_URL}/", path.lstrip("/"))
        return f"{GCS_IMG_BASE}/{fname}"
    return urljoin(f"{BASE_URL}/", path.lstrip("/"))
