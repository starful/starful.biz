import os
import json
import re
from datetime import date
from typing import List, Optional
from urllib.parse import urljoin

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import markdown
from google import genai

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

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

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

# --- 5. 라우팅 (TypeError 해결: 인자 명시) ---

@app.get("/")
async def home(request: Request):
    category_list = [
        {"slug": "engineering", "title": "Engineering"},
        {"slug": "ai-data", "title": "AI & Data"},
        {"slug": "design", "title": "Design"},
        {"slug": "marketing", "title": "Marketing"},
        {"slug": "cloud-infra", "title": "Cloud & Infra"},
        {"slug": "product-management", "title": "Product"},
        {"slug": "cyber-security", "title": "Security"},
        {"slug": "sales-bizdev", "title": "Business Development"},
        {"slug": "customer-success", "title": "Customer Success"},
        {"slug": "content-strategy", "title": "Content Strategy"}
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
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "grouped_items": grouped_items,
            "total_count": JOB_DATA.get('total_count', 0),
            "last_updated": JOB_DATA.get('last_updated', date.today().isoformat())
        }
    )

@app.get("/career/{item_id}")
async def career_detail(request: Request, item_id: str):
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if not os.path.exists(filepath): raise HTTPException(status_code=404)
    meta, body = parse_starful_md(filepath)
    content_html = markdown.markdown(body, extensions=['tables'])
    
    return templates.TemplateResponse(
        request=request, 
        name="detail.html", 
        context={
            "item": meta, 
            "content": content_html,
            "category_title": meta.get('category', 'Career')
        }
    )

@app.get("/practice")
async def practice_page(request: Request):
    return templates.TemplateResponse(request=request, name="practice.html")

@app.get("/search")
async def search(request: Request, q: str = ""):
    query = q.lower()
    results = [j for j in JOB_DATA.get('jobs', []) if query in j.get('title', '').lower()]
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
        return feedback
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ STARR analyze error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze STARR response."
        )

@app.get("/sitemap.xml")
async def sitemap():
    static_paths = ["/", "/practice", "/about", "/privacy"]
    urls = []

    for path in static_paths:
        loc = BASE_URL if path == "/" else urljoin(f"{BASE_URL}/", path.lstrip("/"))
        urls.append(
            f"<url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )

    for job in JOB_DATA.get("jobs", []):
        career_path = f"/career/{job.get('id', '')}"
        loc = urljoin(f"{BASE_URL}/", career_path.lstrip("/"))
        urls.append(
            f"<url><loc>{loc}</loc><lastmod>{job.get('published', date.today().isoformat())}</lastmod>"
            "<changefreq>monthly</changefreq><priority>0.7</priority></url>"
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
@app.get('/robots.txt')
async def robots(): 
    return PlainTextResponse(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml"
    )