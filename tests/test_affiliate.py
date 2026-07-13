"""Affiliate book keyword mapping for Starful.biz."""

from app.affiliate import (
    DEFAULT_KEYWORD,
    MBTI_KEYWORD,
    affiliate_context,
    resolve_career_keyword,
)


def test_category_keyword():
    assert resolve_career_keyword("foo", category="ai-data") == "データサイエンス 本"


def test_career_override():
    assert resolve_career_keyword("devops_engineer", category="engineering") == "DevOps 本"


def test_default_keyword():
    assert resolve_career_keyword("unknown_role", category="") == DEFAULT_KEYWORD


def test_career_context():
    ctx = affiliate_context(career_id="seo_specialist", category="engineering")
    assert ctx["show_affiliate"] is True
    assert ctx["affiliate_keyword"] == "SEO 本"
    assert "starful06-22" in ctx["amazon_search_url"]
    assert "hb.afl.rakuten.co.jp/hgc/" in ctx["rakuten_search_url"]


def test_mbti_context():
    ctx = affiliate_context(page_kind="mbti")
    assert ctx["affiliate_keyword"] == MBTI_KEYWORD
    assert "MBTI" in ctx["amazon_button_label"]
