"""A8.net banners for Starful.biz (Neuro Dive + @PRO人)."""

from __future__ import annotations

import os
from typing import Any, Literal

A8PageKind = Literal["career", "mbti"]

NEURO_DIVE_A8 = {
    "id": "neuro_dive",
    "click_url": os.getenv(
        "A8_NEURO_DIVE_CLICK_URL",
        "https://px.a8.net/svt/ejp?a8mat=4BACLI+2KVNX6+47GS+HVNAP",
    ),
    "image_url": os.getenv(
        "A8_NEURO_DIVE_BANNER_URL",
        "https://www23.a8.net/svt/bgt?aid=260823366156&wid=002&eno=01&mid=s00000019630003003000&mc=1",
    ),
    "pixel_url": os.getenv(
        "A8_NEURO_DIVE_PIXEL_URL",
        "https://www14.a8.net/0.gif?a8mat=4BACLI+2KVNX6+47GS+HVNAP",
    ),
    "label": "Neuro Dive — IT特化型 就労移行支援",
    "desc": "AI・データサイエンスを学べる就労移行支援事業所（パーソルダイバース）",
    "alt": "Neuro Dive 就労移行支援 — アフィリエイト",
}

PRO_JIN_A8 = {
    "id": "pro_jin",
    "click_url": os.getenv(
        "A8_PRO_JIN_CLICK_URL",
        "https://px.a8.net/svt/ejp?a8mat=4BACLI+2IHXI2+4GWI+BZVU9",
    ),
    "image_url": os.getenv(
        "A8_PRO_JIN_BANNER_URL",
        "https://www23.a8.net/svt/bgt?aid=260823366152&wid=002&eno=01&mid=s00000020853002015000&mc=1",
    ),
    "pixel_url": os.getenv(
        "A8_PRO_JIN_PIXEL_URL",
        "https://www13.a8.net/0.gif?a8mat=4BACLI+2IHXI2+4GWI+BZVU9",
    ),
    "label": "IT転職エージェント @PRO人",
    "desc": "IT職種・業界特化。キャリア相談の質にこだわった転職エージェント",
    "alt": "IT転職エージェント @PRO人 — アフィリエイト",
}


def _banner_dict(src: dict[str, str]) -> dict[str, str]:
    return {
        "id": src["id"],
        "click_url": src["click_url"],
        "image_url": src["image_url"],
        "pixel_url": src["pixel_url"],
        "alt": src["alt"],
        "label": src["label"],
        "desc": src["desc"],
    }


def a8_neuro_dive_context(*, page_kind: A8PageKind) -> dict[str, Any]:
    """Back-compat wrapper — returns combined A8 banner context."""
    return a8_career_banners_context(page_kind=page_kind)


def a8_career_banners_context(*, page_kind: A8PageKind) -> dict[str, Any]:
    """Neuro Dive + @PRO人 on career / MBTI pages."""
    enabled = os.getenv("A8_STARFUL_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if not enabled or page_kind not in ("career", "mbti"):
        return {
            "show_a8_neuro_dive": False,
            "show_a8_banners": False,
            "a8_banners": [],
        }

    banners = [_banner_dict(NEURO_DIVE_A8), _banner_dict(PRO_JIN_A8)]
    first = banners[0]
    return {
        "show_a8_neuro_dive": True,
        "a8_neuro_dive_banner": first,
        "a8_neuro_dive_title": "就労移行支援（IT・データサイエンス）",
        "a8_neuro_dive_note": "アフィリエイト広告 · 新しいタブで開きます",
        "show_a8_banners": True,
        "a8_banners": banners,
        "a8_banners_title": "キャリア支援（アフィリエイト）",
        "a8_banners_note": "アフィリエイト広告 · 新しいタブで開きます",
    }
