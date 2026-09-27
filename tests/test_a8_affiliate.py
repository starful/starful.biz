"""A8 Neuro Dive affiliate banners (@PRO人 removed)."""

from app.a8_affiliate import (
    NEURO_DIVE_A8,
    a8_career_banners_context,
    a8_neuro_dive_context,
)


def test_career_page_shows_neuro_dive_only():
    ctx = a8_career_banners_context(page_kind="career")
    assert ctx["show_a8_banners"] is True
    assert [b["id"] for b in ctx["a8_banners"]] == ["neuro_dive"]
    assert ctx["a8_banners"][0]["click_url"] == NEURO_DIVE_A8["click_url"]
    assert "a8.net" in ctx["a8_banners"][0]["image_url"]
    assert ctx["a8_banners"][0]["pixel_url"].endswith("HVNAP")


def test_mbti_page_shows_banners():
    ctx = a8_neuro_dive_context(page_kind="mbti")
    assert ctx["show_a8_neuro_dive"] is True
    assert ctx["show_a8_banners"] is True
    assert ctx["a8_neuro_dive_banner"]["label"].startswith("Neuro Dive")
    assert [b["id"] for b in ctx["a8_banners"]] == ["neuro_dive"]


def test_disabled_via_env(monkeypatch):
    monkeypatch.setenv("A8_STARFUL_ENABLED", "0")
    ctx = a8_career_banners_context(page_kind="career")
    assert ctx["show_a8_banners"] is False
