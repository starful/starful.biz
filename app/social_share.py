"""SNS share bar + X/OG card helpers (same-domain social JPEGs)."""
from __future__ import annotations

import io
import os
import re
import urllib.request
from urllib.parse import quote

SOCIAL_CARD_VERSION = "1"
_FETCH_UA = "Starful/1.0 (+https://starful.biz)"
CONTENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contents")


def social_image_path(career_id: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]", "", career_id.lower())
    return f"/social/{safe}.jpg"


def social_image_url(domain: str, career_id: str) -> str:
    return f"{domain.rstrip('/')}{social_image_path(career_id)}"


def detail_page_path(career_id: str) -> str:
    return f"/career/{career_id}"


def card_page_path(career_id: str) -> str:
    return f"/card/career/{career_id}?sc={SOCIAL_CARD_VERSION}"


def share_context(domain: str, career_id: str, title: str) -> dict:
    page = detail_page_path(career_id)
    share_url = f"{domain.rstrip('/')}{page}"
    share_tweet = f"{title} — Starful 面接対策"
    return {
        "share_id": career_id,
        "share_url": share_url,
        "share_url_x": f"{domain.rstrip('/')}{card_page_path(career_id)}",
        "share_tweet": share_tweet,
        "share_lang": "ja",
        "og_page_url": share_url,
        "og_image_abs": social_image_url(domain, career_id),
        "og_image_width": 1200,
        "og_image_height": 630,
        "share_label": "このページを共有",
        "share_copy": "リンクをコピー",
        "share_copied": "コピーしました",
        "share_hint": "X共有は /card/ プレビューURLを使います。画像が表示されない場合は ",
        "share_hint_link": "カードページ",
        "share_hint_tail": "を開いてからXボタンで共有してください。",
        "linkedin_inspector_url": (
            f"https://www.linkedin.com/post-inspector/inspect/{quote(share_url, safe='')}"
        ),
    }


def career_thumbnail_url(gcs_base: str, career_id: str) -> str:
    return f"{gcs_base.rstrip('/')}/{career_id}.png"


def load_career_meta(career_id: str, parse_md) -> dict:
    filepath = os.path.join(CONTENTS_DIR, f"{career_id}.md")
    if not os.path.exists(filepath):
        raise FileNotFoundError(career_id)
    meta, _ = parse_md(filepath)
    return meta


def jpeg_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def fetch_social_jpeg(source_url: str) -> bytes:
    req = urllib.request.Request(source_url, headers={"User-Agent": _FETCH_UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        if not raw:
            raise ValueError("empty image")
    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        return jpeg_bytes(ImageOps.fit(img, (1200, 630), Image.Resampling.LANCZOS))
    except Exception:
        return raw


def static_social_image_key(career_id: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", career_id.lower())
