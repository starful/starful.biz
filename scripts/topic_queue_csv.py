"""Resolve CSV path from okadmin topic bank / pipeline queue (TOPIC_* env)."""
from __future__ import annotations

import os


def resolve(bank_id: str, default_path: str, *, source: str = "queue") -> str:
    """source: 'queue' (generators) or 'bank' (metadata / fetch_images)."""
    norm = bank_id.upper().replace("-", "_")
    if source == "bank":
        keys = (f"TOPIC_BANK_{norm}", f"TOPIC_QUEUE_{norm}", "TOPIC_QUEUE_CSV")
    else:
        keys = (f"TOPIC_QUEUE_{norm}", "TOPIC_QUEUE_CSV", f"TOPIC_BANK_{norm}")
    for key in keys:
        path = (os.environ.get(key) or "").strip()
        if path and os.path.isfile(path):
            return path
    return default_path
