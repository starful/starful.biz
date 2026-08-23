"""A8.net Neuro Dive (就労移行支援) banner for Starful.biz."""

from __future__ import annotations

import os
from typing import Any, Literal

A8PageKind = Literal["career", "mbti"]

NEURO_DIVE_PROGRAM_ID = "s00000019630003"

NEURO_DIVE_A8 = {
    "id": "neuro_dive",
    "click_url": os.getenv(
        "A8_NEURO_DIVE_CLICK_URL",
        "https://px.a8.net/svt/ejp?a8mat=4BACLI+2KVNX6+47GS+HVNAP",
    ),
    "image_url": os.getenv(
        "A8_NEURO_DIVE_BANNER_URL",
        "https://www29.a8.net/svt/bgt?aid=260823366156&wid=002&eno=01&mid=s00000019630003003000&mc=1",
    ),
    "pixel_url": os.getenv(
        "A8_NEURO_DIVE_PIXEL_URL",
        "https://www10.a8.net/0.gif?a8mat=4BACLI+2KVNX6+47GS+HVNAP",
    ),
    "label": "Neuro Dive — IT特化型 就労移行支援",
    "desc": "AI・データサイエンスを学べる就労移行支援事業所（パーソルダイバース）",
    "alt": "Neuro Dive 就労移行支援 — アフィリエイト",
}


def a8_neuro_dive_context(*, page_kind: A8PageKind) -> dict[str, Any]:
    """Template context for Neuro Dive A8 banner on career / MBTI pages."""
    enabled = os.getenv("A8_NEURO_DIVE_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if not enabled or page_kind not in ("career", "mbti"):
        return {"show_a8_neuro_dive": False}

    banner = {
        "id": NEURO_DIVE_A8["id"],
        "click_url": NEURO_DIVE_A8["click_url"],
        "image_url": NEURO_DIVE_A8["image_url"],
        "pixel_url": NEURO_DIVE_A8["pixel_url"],
        "alt": NEURO_DIVE_A8["alt"],
        "label": NEURO_DIVE_A8["label"],
        "desc": NEURO_DIVE_A8["desc"],
    }
    return {
        "show_a8_neuro_dive": True,
        "a8_neuro_dive_banner": banner,
        "a8_neuro_dive_title": "就労移行支援（IT・データサイエンス）",
        "a8_neuro_dive_note": "アフィリエイト広告 · 新しいタブで開きます",
    }
