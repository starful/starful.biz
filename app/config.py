"""Application configuration and constants."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CONTENTS_DIR = os.path.join(BASE_DIR, "contents")
DATA_FILE = os.path.join(STATIC_DIR, "json", "job_data.json")

BASE_URL = os.getenv("SITE_URL", "https://starful.biz").rstrip("/")
BRAND_LOGO_FILE = "brand_biz_mark.png"

FIRESTORE_STARR_FEEDBACK_LOGS = "starful_starr_feedback_logs"
FIRESTORE_STARR_USAGE_LIMITS = "starful_starr_usage_limits"

GCS_IMG_BASE = os.getenv(
    "STARFUL_GCS_IMG_BASE", "https://storage.googleapis.com/starful-biz-assets"
).rstrip("/")

LOCAL_IMG_NAMES = frozenset(
    {
        BRAND_LOGO_FILE,
        "favicon.ico",
        "favicon-16x16.png",
        "favicon-32x32.png",
        "favicon-48x48.png",
        "apple-touch-icon.png",
    }
)

CAREER_CATEGORIES: list[dict[str, str]] = [
    {"slug": "engineering", "title": "エンジニアリング"},
    {"slug": "ai-data", "title": "AI・データ"},
    {"slug": "design", "title": "デザイン"},
    {"slug": "marketing", "title": "マーケティング"},
    {"slug": "cloud-infra", "title": "クラウド・インフラ"},
    {"slug": "product-management", "title": "プロダクト"},
    {"slug": "cyber-security", "title": "セキュリティ"},
    {"slug": "sales-bizdev", "title": "ビジネス開発"},
    {"slug": "customer-success", "title": "カスタマーサクセス"},
    {"slug": "content-strategy", "title": "コンテンツ"},
]

_CATEGORY_LABELS_JA = {c["slug"]: c["title"] for c in CAREER_CATEGORIES}


def category_label_ja(slug: str | None) -> str:
    if not slug:
        return ""
    return _CATEGORY_LABELS_JA.get(str(slug).lower(), slug)
