"""Job data JSON cache (mtime-based reload)."""
from __future__ import annotations

import json
import os
from datetime import date

from app.config import DATA_FILE

JOB_DATA: dict = {
    "jobs": [],
    "last_updated": date.today().isoformat(),
    "total_count": 0,
}
_JOB_CACHE_MTIME: float = 0.0


def _set_job_data(data: dict) -> None:
    """Update JOB_DATA in place so all importers keep the same object reference."""
    JOB_DATA.clear()
    JOB_DATA.update(data)


def ensure_jobs_cache() -> None:
    global _JOB_CACHE_MTIME
    if not os.path.exists(DATA_FILE):
        return
    try:
        mtime = os.path.getmtime(DATA_FILE)
    except OSError:
        return
    if mtime <= _JOB_CACHE_MTIME:
        return
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            _set_job_data(json.load(f))
        _JOB_CACHE_MTIME = mtime
    except Exception as e:
        print(f"❌ [Error] Failed to reload job JSON: {e}")


def load_jobs_on_startup() -> None:
    global _JOB_CACHE_MTIME
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                _set_job_data(json.load(f))
            _JOB_CACHE_MTIME = os.path.getmtime(DATA_FILE)
            print(f"✅ [Success] Loaded {JOB_DATA.get('total_count', 0)} jobs.")
        except Exception as e:
            print(f"❌ [Error] Failed to load JSON: {e}")


def related_careers_from_meta(meta: dict) -> list[dict]:
    """Resolve related_jobs IDs from job_data with titles."""
    ids = meta.get("related_jobs") or []
    if not ids:
        return []
    by_id = {j.get("id"): j for j in JOB_DATA.get("jobs", []) if j.get("id")}
    out: list[dict] = []
    for rid in ids:
        job = by_id.get(rid)
        if job:
            out.append({"id": rid, "title": job.get("title", rid)})
    return out
