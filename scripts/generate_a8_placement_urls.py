#!/usr/bin/env python3
"""Build A8 広告掲載URL CSV for Neuro Dive (program ID + URL, no header)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOB_DATA = ROOT / "app" / "static" / "json" / "job_data.json"
OUT_DIR = ROOT / "data" / "a8"
BASE = "https://starful.biz"

NEURO_DIVE_PROGRAM_ID = "s00000019630003"

MBTI_TYPE_CODES = (
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
)


def _write_csv(path: Path, program_id: str, urls: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    unique = sorted(dict.fromkeys(urls))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        for url in unique:
            writer.writerow([program_id, url])


def main() -> None:
    jobs = json.loads(JOB_DATA.read_text(encoding="utf-8")).get("jobs", [])

    urls: list[str] = []
    for job in jobs:
        jid = job.get("id", "").strip()
        if jid:
            urls.append(f"{BASE}/career/{jid}")

    for code in MBTI_TYPE_CODES:
        urls.append(f"{BASE}/mbti/{code}")

    out_path = OUT_DIR / "a8-neuro-dive-placement-urls.csv"
    _write_csv(out_path, NEURO_DIVE_PROGRAM_ID, urls)
    print(f"Wrote {out_path} ({len(set(urls))} rows, program={NEURO_DIVE_PROGRAM_ID})")


if __name__ == "__main__":
    main()
