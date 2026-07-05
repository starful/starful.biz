"""Starful FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import BASE_URL, BRAND_LOGO_FILE, GCS_IMG_BASE, STATIC_DIR, category_label_ja
from .dependencies import db  # noqa: F401 — init Firebase on import
from .md_parser import parse_starful_md
from .reactions import router as reactions_router
from .routes.api_starr import router as starr_router
from .routes.pages import router as pages_router
from .routes.seo import register_seo
from .services.jobs_cache import JOB_DATA, load_jobs_on_startup
from .services.media import career_img_url, gcs_or_static_img, serve_img
from .templating import templates

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_jobs_on_startup()
    yield


app = FastAPI(lifespan=lifespan)

app.add_api_route("/static/img/{filename:path}", serve_img, methods=["GET"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates.env.globals["site_url"] = BASE_URL
templates.env.globals["brand_logo_file"] = BRAND_LOGO_FILE
templates.env.globals["career_img_url"] = career_img_url
templates.env.globals["gcs_or_static_img"] = gcs_or_static_img
templates.env.globals["category_label_ja"] = category_label_ja

register_seo(app)

app.include_router(pages_router)
app.include_router(starr_router, prefix="/api")
app.include_router(reactions_router, prefix="/api")

__all__ = [
    "app",
    "BASE_URL",
    "GCS_IMG_BASE",
    "parse_starful_md",
    "JOB_DATA",
]
