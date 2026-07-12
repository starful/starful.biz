"""Non-SEO page routes: home, search, practice, about, privacy, mbti."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import BASE_URL, CAREER_CATEGORIES
from app.content_new import enrich_items
from app.seo_helpers import faq_page_json_ld, featured_jobs_from_data, merge_career_json_ld
from app.services.jobs_cache import JOB_DATA, ensure_jobs_cache
from app.services.mbti import get_mbti_type, list_mbti_types, normalize_mbti_type
from app.services.search import search_jobs
from app.templating import templates

router = APIRouter()


@router.get("/")
async def home(request: Request):
    ensure_jobs_cache()
    grouped_items = []
    all_jobs = JOB_DATA.get("jobs", [])
    for cat in CAREER_CATEGORIES:
        items = enrich_items(
            [j for j in all_jobs if j.get("category", "").lower() == cat["slug"].lower()]
        )
        items.sort(key=lambda x: (x.get("published", ""), x.get("id", "")), reverse=True)
        if items:
            cat_copy = cat.copy()
            cat_copy["job_items"] = items
            grouped_items.append(cat_copy)

    featured_jobs = enrich_items(featured_jobs_from_data(all_jobs))

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "grouped_items": grouped_items,
            "total_count": JOB_DATA.get("total_count", 0),
            "last_updated": JOB_DATA.get("last_updated", date.today().isoformat()),
            "featured_jobs": featured_jobs,
        },
    )


@router.get("/practice")
async def practice_page(request: Request):
    ensure_jobs_cache()
    career_opts = [
        {"id": j.get("id", ""), "title": j.get("title", "")}
        for j in JOB_DATA.get("jobs", [])
        if j.get("title")
    ]
    career_opts.sort(key=lambda x: x["title"])
    return templates.TemplateResponse(
        request=request,
        name="practice.html",
        context={"career_options": career_opts},
    )


@router.get("/search")
async def search(request: Request, q: str = ""):
    ensure_jobs_cache()
    results = search_jobs(JOB_DATA.get("jobs", []), q)
    return templates.TemplateResponse(
        request=request,
        name="search_results.html",
        context={"items": results, "query": q, "results_count": len(results)},
    )


@router.get("/about")
async def about_page(request: Request):
    return templates.TemplateResponse(request=request, name="about.html")


@router.get("/privacy")
async def privacy_page(request: Request):
    return templates.TemplateResponse(request=request, name="privacy.html")


@router.get("/mbti")
async def mbti_index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="mbti_index.html",
        context={"mbti_types": list_mbti_types()},
    )


@router.get("/mbti/{type_code}")
async def mbti_type_page(request: Request, type_code: str):
    normalized = normalize_mbti_type(type_code)
    if not normalized:
        raise HTTPException(status_code=404)
    if type_code != normalized:
        return RedirectResponse(f"{BASE_URL}/mbti/{normalized}", status_code=301)

    payload = get_mbti_type(normalized)
    if not payload:
        raise HTTPException(status_code=404)

    canonical = f"{BASE_URL}/mbti/{normalized}"
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "MBTIから探す", "item": f"{BASE_URL}/mbti"},
            {"@type": "ListItem", "position": 3, "name": normalized, "item": canonical},
        ],
    }
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{normalized}に向いているIT職種｜{payload.get('label', '')}",
        "description": (payload.get("summary") or "")[:300],
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "author": {"@type": "Organization", "name": "Starful"},
        "publisher": {
            "@type": "Organization",
            "name": "Starful",
            "url": BASE_URL,
        },
    }
    item_list_ld = None
    if payload.get("careers"):
        item_list_ld = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"{normalized}におすすめのIT職種",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": c.get("name", ""),
                    "url": f"{BASE_URL}{c.get('link', '')}",
                }
                for i, c in enumerate(payload["careers"])
            ],
        }
    faq_ld = faq_page_json_ld(payload.get("faqs") or [], canonical)
    graph = [article_ld, breadcrumb_ld]
    if item_list_ld:
        graph.append(item_list_ld)
    json_ld_mbti = merge_career_json_ld(graph, faq_ld)

    return templates.TemplateResponse(
        request=request,
        name="mbti_type.html",
        context={"mbti": payload, "json_ld_mbti": json_ld_mbti},
    )
