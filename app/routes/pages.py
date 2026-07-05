"""Non-SEO page routes: home, search, practice, about, privacy."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request

from app.config import CAREER_CATEGORIES
from app.content_new import enrich_items
from app.seo_helpers import featured_jobs_from_data
from app.services.jobs_cache import JOB_DATA, ensure_jobs_cache
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
