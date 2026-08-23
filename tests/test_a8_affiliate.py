"""A8 Neuro Dive affiliate banner."""

from app.a8_affiliate import NEURO_DIVE_A8, a8_neuro_dive_context


def test_career_page_shows_banner():
    ctx = a8_neuro_dive_context(page_kind="career")
    assert ctx["show_a8_neuro_dive"] is True
    banner = ctx["a8_neuro_dive_banner"]
    assert banner["id"] == "neuro_dive"
    assert banner["click_url"] == NEURO_DIVE_A8["click_url"]
    assert "a8.net" in banner["image_url"]
    assert banner["pixel_url"].endswith("HVNAP")


def test_mbti_page_shows_banner():
    ctx = a8_neuro_dive_context(page_kind="mbti")
    assert ctx["show_a8_neuro_dive"] is True
    assert ctx["a8_neuro_dive_banner"]["label"].startswith("Neuro Dive")


def test_disabled_via_env(monkeypatch):
    monkeypatch.setenv("A8_NEURO_DIVE_ENABLED", "0")
    ctx = a8_neuro_dive_context(page_kind="career")
    assert ctx["show_a8_neuro_dive"] is False
