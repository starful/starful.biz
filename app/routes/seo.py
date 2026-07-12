"""SEO-frozen routes (do not refactor without SEO review)."""
from __future__ import annotations

import os
import re
from datetime import date
from urllib.parse import urljoin

import markdown
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import BASE_URL, BRAND_LOGO_FILE, CONTENTS_DIR, GCS_IMG_BASE, STATIC_DIR
from app.md_parser import parse_starful_md
from app.seo_helpers import (
    FEATURED_CAREER_SLUGS,
    canonical_career_url,
    extract_faq_from_markdown,
    faq_page_json_ld,
    featured_jobs_from_data,
    legacy_redirect_target,
    merge_career_json_ld,
    resolve_career_id,
)
from app.services.jobs_cache import JOB_DATA, ensure_jobs_cache, related_careers_from_meta
from app.services.mbti import all_mbti_type_codes, types_for_career
from app.services.media import career_img_url, gcs_or_static_img
from app.social_share import (
    card_page_path,
    career_thumbnail_url,
    detail_page_path,
    fetch_social_jpeg,
    share_context,
)
from app.templating import templates

router = APIRouter()


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
    host_name = host_lower.split(":")[0]
    is_local = host_name in {"localhost", "127.0.0.1", "::1"}
    if proto == "http" and host_header and not is_local:
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"
        return RedirectResponse(f"https://{host_header}{path}", status_code=301)

    response = await call_next(request)
    if not is_local and (proto == "https" or (not proto and BASE_URL.startswith("https"))):
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
    return response


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


def register_seo(app: FastAPI) -> None:
    app.middleware("http")(seo_request_middleware)
    app.exception_handler(StarletteHTTPException)(starlette_http_exception_handler)
    app.include_router(router)


@router.get("/favicon.ico")
async def favicon_root():
    """検索エンジン・ブラウザがドメイン直下の /favicon.ico を参照する場合用。"""
    path = os.path.join(STATIC_DIR, "img", "favicon.ico")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/vnd.microsoft.icon")


@router.get("/career/{item_id}")
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
    mbti_types = types_for_career(resolved_id)

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
            "mbti_types": mbti_types,
            "json_ld_career": json_ld_career,
            **ctx,
        },
    )


@router.get("/sitemap.xml")
async def sitemap():
    static_paths = [
        ("/", "daily", "1.0"),
        ("/practice", "weekly", "0.85"),
        ("/mbti", "weekly", "0.8"),
        ("/about", "monthly", "0.5"),
        ("/contact", "monthly", "0.4"),
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

    today = date.today().isoformat()
    for code in all_mbti_type_codes():
        loc = urljoin(f"{BASE_URL}/", f"mbti/{code}")
        urls.append(
            f"<url><loc>{loc}</loc><lastmod>{today}</lastmod>"
            f"<changefreq>monthly</changefreq><priority>0.75</priority></url>"
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


@router.get("/ads.txt")
async def ads_txt():
    path = os.path.join(STATIC_DIR, "ads.txt")
    return FileResponse(path) if os.path.exists(path) else Response(status_code=404)


@router.get("/robots.txt")
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


@router.api_route("/social/{image_key}.jpg", methods=["GET", "HEAD"])
async def social_image(image_key: str):
    static_path = _static_social_path(image_key)
    if static_path:
        return FileResponse(static_path, media_type="image/jpeg", headers=_social_image_headers())
    return _render_social_image(image_key)


@router.api_route("/card/career/{career_id}", methods=["GET", "HEAD"])
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
