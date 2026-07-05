"""Starful FastAPI application entrypoint."""
from __future__ import annotations

import os
import re
from datetime import date
from urllib.parse import urljoin

import markdown
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import (
    BASE_URL,
    BRAND_LOGO_FILE,
    CONTENTS_DIR,
    GCS_IMG_BASE,
    STATIC_DIR,
    category_label_ja,
)
from .dependencies import db  # noqa: F401 — init Firebase on import
from .md_parser import parse_starful_md
from .reactions import router as reactions_router
from .routes.api_starr import router as starr_router
from .routes.pages import router as pages_router
from .seo_helpers import (
    FEATURED_CAREER_SLUGS,
    canonical_career_url,
    extract_faq_from_markdown,
    faq_page_json_ld,
    featured_jobs_from_data,
    legacy_redirect_target,
    merge_career_json_ld,
    resolve_career_id,
)
from .services.jobs_cache import JOB_DATA, ensure_jobs_cache, load_jobs_on_startup, related_careers_from_meta
from .services.media import career_img_url, gcs_or_static_img, serve_img
from .social_share import (
    card_page_path,
    career_thumbnail_url,
    detail_page_path,
    fetch_social_jpeg,
    share_context,
)
from .templating import templates

load_dotenv()

app = FastAPI()

app.add_api_route("/static/img/{filename:path}", serve_img, methods=["GET"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates.env.globals["site_url"] = BASE_URL
templates.env.globals["brand_logo_file"] = BRAND_LOGO_FILE
templates.env.globals["career_img_url"] = career_img_url
templates.env.globals["gcs_or_static_img"] = gcs_or_static_img
templates.env.globals["category_label_ja"] = category_label_ja


@app.middleware("http")
async def seo_request_middleware(request: Request, call_next):
    """www/http 統一、レガシー URL の 301、HTTPS 応答に HSTS。"""
    host_header = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or ""
    ).split(",")[0].strip()
    host_lower = host_header.lower()

    if host_lower.startswith("www."):
        apex = host_lower[4:]
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
        return RedirectResponse(f"https://{apex}{path}", status_code=301)

    legacy_target = legacy_redirect_target(request.url.path)
    if legacy_target is not None:
        loc = BASE_URL if legacy_target == "/" else urljoin(f"{BASE_URL}/", legacy_target.lstrip("/"))
        if request.url.query:
            loc = f"{loc}?{request.url.query}"
        return RedirectResponse(loc, status_code=301)

    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if not proto and request.url.scheme:
        proto = request.url.scheme.lower()
    if proto == "http" and host_header:
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
        return RedirectResponse(f"https://{host_header}{path}", status_code=301)

    response = await call_next(request)
    if proto == "https" or (not proto and BASE_URL.startswith("https")):
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={
                "featured_jobs": featured_jobs_from_data(JOB_DATA.get("jobs", [])),
            },
            status_code=404,
        )
    return await http_exception_handler(request, exc)


@app.on_event("startup")
async def startup_event():
    load_jobs_on_startup()


app.include_router(pages_router)
app.include_router(starr_router, prefix="/api")
app.include_router(reactions_router, prefix="/api")


# --- SEO-frozen routes (do not refactor without SEO review) ---

@app.get("/favicon.ico")
async def favicon_root():
    """検索エンジン・ブラウザがドメイン直下の /favicon.ico を参照する場合用。"""
    path = os.path.join(STATIC_DIR, "img", "favicon.ico")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/vnd.microsoft.icon")


@app.get("/career/{item_id}")
async def career_detail(request: Request, item_id: str):
    ensure_jobs_cache()
    resolved_id = resolve_career_id(item_id)
    if resolved_id != item_id:
        target = canonical_career_url(BASE_URL, resolved_id)
        if request.url.query:
            target = f"{target}?{request.url.query}"
        return RedirectResponse(target, status_code=301)

    filepath = os.path.join(CONTENTS_DIR, f"{resolved_id}.md")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404)
    meta, body = parse_starful_md(filepath)
    content_html = markdown.markdown(body, extensions=["tables"])
    cache_v = str(meta.get("published_at") or "")[:10]
    if len(cache_v) >= 8:
        content_html = re.sub(
            r'(/static/img/[^"\'?\s>]+)',
            lambda m: m.group(1) if "?v=" in m.group(1) else f"{m.group(1)}?v={cache_v}",
            content_html,
        )
    canonical = canonical_career_url(BASE_URL, resolved_id)
    title = meta.get("title", "面接ガイド")
    ctx = share_context(BASE_URL, resolved_id, title)
    social_image = ctx["og_image_abs"]
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta.get("title", ""),
        "description": (meta.get("meta_description") or "")[:300],
        "image": [social_image],
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "author": {"@type": "Organization", "name": "Starful"},
        "publisher": {
            "@type": "Organization",
            "name": "Starful",
            "url": BASE_URL,
            "logo": {
                "@type": "ImageObject",
                "url": f"{BASE_URL}/static/img/{BRAND_LOGO_FILE}",
            },
        },
    }
    pub = meta.get("published_at")
    if pub:
        article_ld["datePublished"] = str(pub)
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "ホーム",
                "item": f"{BASE_URL}/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": meta.get("title", "面接ガイド")[:80],
                "item": canonical,
            },
        ],
    }
    faq_items = extract_faq_from_markdown(body)
    faq_ld = faq_page_json_ld(faq_items, canonical)
    json_ld_career = merge_career_json_ld([article_ld, breadcrumb_ld], faq_ld)

    all_featured = featured_jobs_from_data(JOB_DATA.get("jobs", []))
    featured_others = [j for j in all_featured if j.get("id") != resolved_id][:8]

    return templates.TemplateResponse(
        request=request,
        name="detail.html",
        context={
            "item": meta,
            "content": content_html,
            "category_title": meta.get("category", "Career"),
            "career_id": resolved_id,
            "canonical_url": canonical,
            "related_careers": related_careers_from_meta(meta),
            "featured_careers": featured_others,
            "json_ld_career": json_ld_career,
            **ctx,
        },
    )


@app.get("/sitemap.xml")
async def sitemap():
    static_paths = [
        ("/", "daily", "1.0"),
        ("/practice", "weekly", "0.85"),
        ("/about", "monthly", "0.5"),
        ("/privacy", "yearly", "0.3"),
    ]
    urls = []
    featured_set = set(FEATURED_CAREER_SLUGS)

    for path, changefreq, priority in static_paths:
        loc = BASE_URL if path == "/" else urljoin(f"{BASE_URL}/", path.lstrip("/"))
        urls.append(
            f"<url><loc>{loc}</loc><changefreq>{changefreq}</changefreq>"
            f"<priority>{priority}</priority></url>"
        )

    for job in JOB_DATA.get("jobs", []):
        jid = job.get("id", "")
        if not jid:
            continue
        career_path = f"/career/{jid}"
        loc = urljoin(f"{BASE_URL}/", career_path.lstrip("/"))
        priority = "0.9" if jid in featured_set else "0.7"
        urls.append(
            f"<url><loc>{loc}</loc><lastmod>{job.get('published', date.today().isoformat())}</lastmod>"
            f"<changefreq>monthly</changefreq><priority>{priority}</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls)
        + "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


@app.get("/ads.txt")
async def ads_txt():
    path = os.path.join(STATIC_DIR, "ads.txt")
    return FileResponse(path) if os.path.exists(path) else Response(status_code=404)


@app.get("/robots.txt")
async def robots():
    return PlainTextResponse(
        "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                f"Sitemap: {BASE_URL}/sitemap.xml",
            ]
        )
        + "\n"
    )


def _static_social_path(image_key: str) -> str | None:
    path = os.path.join(STATIC_DIR, "social", f"{image_key}.jpg")
    return path if os.path.isfile(path) else None


def _social_image_headers() -> dict[str, str]:
    return {"Cache-Control": "public, max-age=604800"}


def _render_social_image(career_id: str) -> Response:
    source = career_thumbnail_url(GCS_IMG_BASE, career_id)
    data = fetch_social_jpeg(source)
    return Response(content=data, media_type="image/jpeg", headers=_social_image_headers())


@app.api_route("/social/{image_key}.jpg", methods=["GET", "HEAD"])
async def social_image(image_key: str):
    static_path = _static_social_path(image_key)
    if static_path:
        return FileResponse(static_path, media_type="image/jpeg", headers=_social_image_headers())
    return _render_social_image(image_key)


@app.api_route("/card/career/{career_id}", methods=["GET", "HEAD"])
async def career_social_card(request: Request, career_id: str):
    resolved_id = resolve_career_id(career_id)
    if resolved_id != career_id:
        target = f"{BASE_URL}{card_page_path(resolved_id)}"
        if request.url.query:
            target = f"{target}&{request.url.query}" if "?" in target else f"{target}?{request.url.query}"
        return RedirectResponse(target, status_code=301)

    filepath = os.path.join(CONTENTS_DIR, f"{resolved_id}.md")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404)
    meta, _ = parse_starful_md(filepath)
    title = meta.get("title", "面接ガイド")
    ctx = share_context(BASE_URL, resolved_id, title)
    page = f"{BASE_URL}{detail_page_path(resolved_id)}"
    card = f"{BASE_URL}{card_page_path(resolved_id)}"
    seo_title = f"{title}｜面接Q&A【Starful】"
    seo_desc = meta.get("meta_description") or ""
    return templates.TemplateResponse(
        request=request,
        name="social_card.html",
        context={
            "title": title,
            "seo_title": seo_title,
            "seo_desc": seo_desc,
            "page_url": page,
            "card_url": card,
            **ctx,
        },
    )


__all__ = [
    "app",
    "BASE_URL",
    "GCS_IMG_BASE",
    "parse_starful_md",
    "JOB_DATA",
]
