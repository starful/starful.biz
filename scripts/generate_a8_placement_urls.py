#!/usr/bin/env python3
"""starful.biz wrapper — hub A8 CSV generator (Neuro Dive)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parents[2] / "data" / "a8" / "generate_placement_urls.py"


def main() -> None:
    if not HUB.is_file():
        raise SystemExit(f"Hub generator not found: {HUB}")
    args = sys.argv[1:] or ["--program", "neuro_dive"]
    subprocess.check_call([sys.executable, str(HUB), *args])


if __name__ == "__main__":
    main()
