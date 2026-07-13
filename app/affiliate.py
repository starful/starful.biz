"""Amazon Associates + Rakuten Ichiba book CTAs for Starful.biz."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote, quote_plus

AMAZON_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "starful06-22")
RAKUTEN_HGC = os.getenv(
    "RAKUTEN_ICHIBA_HGC", "43cde6d2.98a376f7.43cde6d3.c7b92630"
)
_RAKUTEN_UT = "eyJwYWdlIjoidXJsIiwidHlwZSI6InRleHQiLCJjb2wiOjF9"

DEFAULT_KEYWORD = "転職 本"
MBTI_KEYWORD = "MBTI 本"

# Career category slug → book search keyword
CATEGORY_KEYWORDS: dict[str, str] = {
    "engineering": "ソフトウェアエンジニア 本",
    "ai-data": "データサイエンス 本",
    "design": "UI UX デザイン 本",
    "marketing": "マーケティング 本",
    "cloud-infra": "クラウド 本",
    "product-management": "プロダクトマネジメント 本",
    "cyber-security": "セキュリティ 本",
    "sales-bizdev": "営業 本",
    "customer-success": "カスタマーサクセス 本",
    "content-strategy": "コンテンツマーケティング 本",
}

# Specific career id overrides (more precise than category)
CAREER_OVERRIDES: dict[str, str] = {
    "devops_engineer": "DevOps 本",
    "seo_specialist": "SEO 本",
    "data_strategist": "データ分析 本",
    "data_visualization_engineer": "データ可視化 本",
    "growth_hacker": "グロースハック 本",
    "head_of_engineering": "エンジニアリングマネジメント 本",
    "head_of_design": "デザインマネジメント 本",
}


def amazon_search_url(keyword: str) -> str:
    return (
        "https://www.amazon.co.jp/s?k="
        + quote_plus(keyword)
        + "&tag="
        + quote_plus(AMAZON_TAG)
    )


def rakuten_search_url(keyword: str) -> str:
    dest = f"https://search.rakuten.co.jp/search/mall/{quote(keyword, safe='')}/"
    pc = quote(dest, safe="")
    return (
        f"https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_HGC}/"
        f"?pc={pc}&link_type=text&ut={_RAKUTEN_UT}"
    )


def resolve_career_keyword(
    career_id: str = "",
    *,
    category: str = "",
) -> str:
    cid = (career_id or "").strip().lower()
    if cid in CAREER_OVERRIDES:
        return CAREER_OVERRIDES[cid]
    cat = (category or "").strip().lower()
    return CATEGORY_KEYWORDS.get(cat, DEFAULT_KEYWORD)


def affiliate_context(
    *,
    keyword: str | None = None,
    career_id: str = "",
    category: str = "",
    page_kind: str = "career",
) -> dict[str, Any]:
    """Template vars for Amazon + Rakuten book CTA (always shown)."""
    if page_kind == "mbti":
        kw = MBTI_KEYWORD
        title = "関連書籍を Amazon / 楽天で探す"
        desc = (
            "このページはキャリアガイドです。ボタンを押すと新しいタブで"
            f"「{kw}」の検索結果が開きます（特定の商品ページではない場合があります）。"
        )
    else:
        kw = keyword or resolve_career_keyword(career_id, category=category)
        title = "関連する技術・転職の本を探す"
        desc = (
            "面接ガイドの参考書を Amazon / 楽天で検索できます。"
            f"「{kw}」の検索結果が新しいタブで開きます。"
        )

    return {
        "show_affiliate": True,
        "affiliate_keyword": kw,
        "affiliate_title": title,
        "affiliate_desc": desc,
        "affiliate_note": "アフィリエイトリンク · 新しいタブで開きます",
        "amazon_search_url": amazon_search_url(kw),
        "rakuten_search_url": rakuten_search_url(kw),
        "amazon_button_label": f"Amazonで {kw} を探す ↗",
        "rakuten_button_label": f"楽天で {kw} を探す ↗",
    }
