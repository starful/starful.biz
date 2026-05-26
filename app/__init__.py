import os
import json
import re
import unicodedata
from datetime import date
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, PlainTextResponse, RedirectResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

import markdown
from google import genai

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

# Firebase 관련 라이브러리
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. 경로 설정 ---
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CONTENTS_DIR = os.path.join(BASE_DIR, "contents")   
DATA_FILE = os.path.join(STATIC_DIR, "json", "job_data.json")
BASE_URL = os.getenv("SITE_URL", "https://starful.biz").rstrip("/")

# Firestore: サイト名 starful × 機能名 starr
FIRESTORE_STARR_FEEDBACK_LOGS = "starful_starr_feedback_logs"
FIRESTORE_STARR_USAGE_LIMITS = "starful_starr_usage_limits"

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)
templates.env.globals["site_url"] = BASE_URL

_CATEGORY_LABELS_JA: Dict[str, str] = {
    "engineering": "エンジニアリング",
    "ai-data": "AI・データ",
    "design": "デザイン",
    "marketing": "マーケティング",
    "cloud-infra": "クラウド・インフラ",
    "product-management": "プロダクト",
    "cyber-security": "セキュリティ",
    "sales-bizdev": "ビジネス開発",
    "customer-success": "カスタマーサクセス",
    "content-strategy": "コンテンツ",
}


def category_label_ja(slug: Optional[str]) -> str:
    if not slug:
        return ""
    return _CATEGORY_LABELS_JA.get(str(slug).lower(), slug)


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

# --- 2. 데이터 캐시 초기화 ---
JOB_DATA = {"jobs": [], "last_updated": date.today().isoformat(), "total_count": 0}

@app.on_event("startup")
async def startup_event():
    global JOB_DATA
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                JOB_DATA = json.load(f)
                print(f"✅ [Success] Loaded {JOB_DATA.get('total_count', 0)} jobs.")
        except Exception as e:
            print(f"❌ [Error] Failed to load JSON: {e}")

# --- 3. 외부 서비스 (Firebase & Gemini) ---
db = None
try:
    if not firebase_admin._apps:
        sm_key_path = "/secrets/FIREBASE_KEY"
        if os.path.exists(sm_key_path):
            cred = credentials.Certificate(sm_key_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    db = firestore.client()
except Exception as e:
    print(f"⚠️ Firebase Warning: {e}")

ai_client = None
if os.getenv("GEMINI_API_KEY"):
    ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class StarrFeedback(BaseModel):
    score: int; summary: str; s_feedback: str; t_feedback: str; a_feedback: str; r_feedback: str; reflection_feedback: str; improved_answer: str

class StarrRequest(BaseModel):
    s: str; t: str; a: str; r: str; reflection: str; job_title: str

# --- 4. 유틸리티 ---
def parse_starful_md(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content_raw = f.read()
        match = re.match(r'---json\s*(\{.*?\})\s*---(.*)', content_raw, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip()), match.group(2).strip()
        return {}, content_raw
    except Exception as e:
        return {}, ""

SEARCH_SYNONYMS: Dict[str, Set[str]] = {
    "backend": {"backend", "バックエンド", "server", "api"},
    "frontend": {"frontend", "フロントエンド", "ui", "web"},
    "fullstack": {"fullstack", "full stack", "フルスタック"},
    "ai": {"ai", "ml", "machine learning", "人工知能", "機械学習"},
    "data": {"data", "データ", "analytics", "分析"},
    "cloud": {"cloud", "クラウド", "aws", "gcp", "azure"},
    "security": {"security", "セキュリティ", "appsec", "cybersecurity"},
    "devops": {"devops", "sre", "platform", "インフラ"},
    "product": {"product", "pm", "プロダクト", "企画"},
    "design": {"design", "デザイン", "ux", "ui"},
    "marketing": {"marketing", "マーケティング", "growth", "seo"},
}


def normalize_search_text(text: str) -> str:
    """Normalize case, width, and whitespace for robust matching."""
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def expand_query_terms(query: str) -> Set[str]:
    base = normalize_search_text(query)
    if not base:
        return set()

    terms: Set[str] = {base}
    split_terms = {t for t in re.split(r"[\s/,_-]+", base) if t}
    terms.update(split_terms)

    for token in list(terms):
        for group in SEARCH_SYNONYMS.values():
            if token in group:
                terms.update(group)
    return terms


def related_careers_from_meta(meta: dict) -> List[dict]:
    """related_jobs ID を job_data からタイトル付きで解決。"""
    ids = meta.get("related_jobs") or []
    if not ids:
        return []
    by_id = {j.get("id"): j for j in JOB_DATA.get("jobs", []) if j.get("id")}
    out: List[dict] = []
    for rid in ids:
        job = by_id.get(rid)
        if job:
            out.append({"id": rid, "title": job.get("title", rid)})
    return out


def absolute_static_url(path: str) -> str:
    if not path:
        return BASE_URL + "/static/img/logo.png"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(f"{BASE_URL}/", path.lstrip("/"))


def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _pydantic_to_dict(model: BaseModel) -> dict:
    dump = getattr(model, "model_dump", None)
    if callable(dump):
        return dump()
    return model.dict()


def _clip_shokumu_line(text: str, max_len: int = 130) -> str:
    t = unicodedata.normalize("NFKC", (text or "").strip())
    t = re.sub(r"[\r\n]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    if not t:
        return ""
    if len(t) > max_len:
        return t[: max_len - 1] + "…"
    return t


def build_shokumu_bullets(starr: StarrRequest) -> List[str]:
    """職務経歴書向け箇条書き4行（テンプレート・パターン3種＋学び）。"""
    job = _clip_shokumu_line(starr.job_title, 70) or "職務"
    s = _clip_shokumu_line(starr.s, 150)
    t = _clip_shokumu_line(starr.t, 120)
    a = _clip_shokumu_line(starr.a, 150)
    r = _clip_shokumu_line(starr.r, 120)
    ref = _clip_shokumu_line(starr.reflection, 120)
    task_phrase = t if t else "プロジェクト・事業上の課題"
    res_phrase = r if r else "業務・サービス上の改善につながる成果"
    refl_phrase = ref if ref else "再現性のある改善サイクルづくり"

    return [
        f"「{s}において、{task_phrase}に対し、{a}を実施し、{res_phrase}。」",
        f"「{job}として、課題設定から改善施策の実行までを担当。特に{a}を中心に推進。」",
        f"「関係者と連携し、進捗管理とリスク対応を含めて推進し、{res_phrase}。」",
        f"「本経験から{refl_phrase}について学び、以降の業務に反映。」",
    ]


class ShokumuBulletsResponse(BaseModel):
    bullets: List[str]
    job_title: str


def score_job_for_terms(job: dict, terms: Set[str]) -> int:
    title = normalize_search_text(job.get("title", ""))
    category = normalize_search_text(job.get("category", ""))
    tags = " ".join(job.get("tags", []) or [])
    tags_text = normalize_search_text(tags)
    desc = normalize_search_text(job.get("meta_description", ""))

    score = 0
    for term in terms:
        if not term:
            continue
        if term == title:
            score += 120
        elif term in title:
            score += 60

        if term == category:
            score += 50
        elif term in category:
            score += 30

        if term in tags_text:
            score += 35

        if term in desc:
            score += 10
    return score

# --- 5. 라우팅 (TypeError 해결: 인자 명시) ---

@app.get("/favicon.ico")
async def favicon_root():
    """検索エンジン・ブラウザがドメイン直下の /favicon.ico を参照する場合用。"""
    path = os.path.join(STATIC_DIR, "img", "favicon.ico")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/vnd.microsoft.icon")


@app.get("/")
async def home(request: Request):
    category_list = [
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
    
    grouped_items = []
    all_jobs = JOB_DATA.get('jobs', [])
    for cat in category_list:
        items = [j for j in all_jobs if j.get('category', '').lower() == cat['slug'].lower()]
        if items:
            cat_copy = cat.copy()
            cat_copy['job_items'] = items
            grouped_items.append(cat_copy)

    # 💡 핵심 수정: 인자를 명시적으로 전달 (request=request, name=..., context={...})
    featured_jobs = featured_jobs_from_data(all_jobs)

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "grouped_items": grouped_items,
            "total_count": JOB_DATA.get('total_count', 0),
            "last_updated": JOB_DATA.get('last_updated', date.today().isoformat()),
            "featured_jobs": featured_jobs,
        }
    )

@app.get("/career/{item_id}")
async def career_detail(request: Request, item_id: str):
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
    content_html = markdown.markdown(body, extensions=['tables'])
    canonical = canonical_career_url(BASE_URL, resolved_id)
    share_image = absolute_static_url(
        meta.get("thumbnail") or f"/static/img/{resolved_id}.png"
    )
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta.get("title", ""),
        "description": (meta.get("meta_description") or "")[:300],
        "image": [share_image],
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "author": {"@type": "Organization", "name": "Starful"},
        "publisher": {
            "@type": "Organization",
            "name": "Starful",
            "url": BASE_URL,
            "logo": {
                "@type": "ImageObject",
                "url": f"{BASE_URL}/static/img/logo.png?v=5",
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
            "share_image": share_image,
            "related_careers": related_careers_from_meta(meta),
            "featured_careers": featured_others,
            "json_ld_career": json_ld_career,
        },
    )

@app.get("/practice")
async def practice_page(request: Request):
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

@app.get("/search")
async def search(request: Request, q: str = ""):
    terms = expand_query_terms(q)
    if not terms:
        results = []
    else:
        scored = []
        for job in JOB_DATA.get("jobs", []):
            score = score_job_for_terms(job, terms)
            if score > 0:
                scored.append((score, job))

        # Higher score first, then title for stable ordering.
        scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
        results = [job for _, job in scored]

    return templates.TemplateResponse(
        request=request, 
        name="search_results.html", 
        context={"items": results, "query": q, "results_count": len(results)}
    )

# --- 6. 기타 엔드포인트 ---
@app.post("/api/analyze-starr")
async def analyze_starr(request: Request, starr_data: StarrRequest):
    if ai_client is None:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. Set GEMINI_API_KEY."
        )

    client_ip = get_client_ip(request)
    safe_ip = client_ip.replace(".", "_").replace(":", "_")
    today = date.today().isoformat()
    usage_doc_id = f"{safe_ip}_{today}"
    count = 0

    if db:
        try:
            doc = db.collection(FIRESTORE_STARR_USAGE_LIMITS).document(usage_doc_id).get()
            if doc.exists:
                count = int(doc.to_dict().get("count", 0))
            if count >= 3:
                raise HTTPException(
                    status_code=429,
                    detail="本日の利用制限（3回）に達しました。明日またお試しください。",
                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ Firestore {FIRESTORE_STARR_USAGE_LIMITS} read error: {e}")

    prompt = f"""
You are a senior IT interview coach.
Evaluate the candidate's STARR response for the job title: {starr_data.job_title}.

Candidate input:
- Situation: {starr_data.s}
- Task: {starr_data.t}
- Action: {starr_data.a}
- Result: {starr_data.r}
- Reflection: {starr_data.reflection}

Return ONLY valid JSON (no markdown, no extra text) using this exact schema:
{{
  "score": <integer 0-100>,
  "summary": "<short overall feedback>",
  "s_feedback": "<feedback for Situation>",
  "t_feedback": "<feedback for Task>",
  "a_feedback": "<feedback for Action>",
  "r_feedback": "<feedback for Result>",
  "reflection_feedback": "<feedback for Reflection>",
  "improved_answer": "<a polished improved STARR answer in Japanese>"
}}

Scoring rules:
- Prioritize clarity, impact, and measurable outcomes.
- Give practical, interview-ready feedback.
"""

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        raw_text = (response.text or "").strip()
        if not raw_text:
            raise ValueError("Empty AI response")

        # Handle responses wrapped in markdown fences.
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        parsed = json.loads(cleaned)
        feedback = StarrFeedback(**parsed)

        # Clamp score to a valid range to keep UI consistent.
        feedback.score = max(0, min(100, feedback.score))

        if db:
            try:
                db.collection(FIRESTORE_STARR_FEEDBACK_LOGS).add(
                    {
                        "ip": client_ip,
                        "job_title": starr_data.job_title,
                        "user_input": _pydantic_to_dict(starr_data),
                        "ai_output": _pydantic_to_dict(feedback),
                        "created_at": firestore.SERVER_TIMESTAMP,
                    }
                )
                db.collection(FIRESTORE_STARR_USAGE_LIMITS).document(usage_doc_id).set(
                    {
                        "count": count + 1,
                        "last_access": firestore.SERVER_TIMESTAMP,
                    },
                    merge=True,
                )
            except Exception as e:
                print(
                    f"⚠️ Firestore {FIRESTORE_STARR_FEEDBACK_LOGS} / "
                    f"{FIRESTORE_STARR_USAGE_LIMITS} write error: {e}"
                )

        return feedback
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ STARR analyze error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze STARR response."
        )


@app.post("/api/shokumu-bullets")
async def shokumu_bullets(starr_data: StarrRequest) -> ShokumuBulletsResponse:
    """Gemini なし。STARR＋職種から職務経歴書用箇条書き4行を生成。"""
    if not (starr_data.s or "").strip() or not (starr_data.a or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Situation(S) と Action(A) は必須です。",
        )
    if not (starr_data.job_title or "").strip():
        raise HTTPException(status_code=400, detail="職種・ポジションを選択または入力してください。")
    bullets = build_shokumu_bullets(starr_data)
    return ShokumuBulletsResponse(
        bullets=bullets,
        job_title=starr_data.job_title.strip(),
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
        + "".join(urls) +
        "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")

@app.get("/about")
async def about_page(request: Request): 
    return templates.TemplateResponse(request=request, name="about.html")

@app.get("/privacy")
async def privacy_page(request: Request): 
    return templates.TemplateResponse(request=request, name="privacy.html")

@app.get("/ads.txt")
async def ads_txt():
    path = os.path.join(STATIC_DIR, "ads.txt")
    return FileResponse(path) if os.path.exists(path) else Response(status_code=404)

# 기존에 있던 robots.txt 코드
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