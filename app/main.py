import os
import json
import re
import time
from datetime import datetime, date
from typing import List, Optional

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import frontmatter
import markdown
from google import genai

# Firebase 관련 라이브러리
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. 경로 설정 및 환경 변수 로드 ---
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CONTENTS_DIR = os.path.join(BASE_DIR, "contents")
STRUCTURE_FILE = os.path.join(BASE_DIR, "site_structure.json")
DEFAULT_PLACEHOLDER = "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?q=80&w=800&auto=format&fit=crop"

app = FastAPI()

# 정적 파일 마운트
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- 2. Firebase 초기화 (Secret Manager 볼륨 대응) ---
db = None
try:
    if not firebase_admin._apps:
        # Secret Manager에서 볼륨 마운트 시 기본 경로는 /secrets/FIREBASE_KEY 입니다.
        sm_key_path = "/secrets/FIREBASE_KEY"
        local_key_path = os.path.join(os.path.dirname(BASE_DIR), "firebase-key.json")
        
        if os.path.exists(sm_key_path):
            cred = credentials.Certificate(sm_key_path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase initialized via Secret Manager: {sm_key_path}")
        elif os.path.exists(local_key_path):
            cred = credentials.Certificate(local_key_path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase initialized via Local Key: {local_key_path}")
        else:
            # 키 파일이 전혀 없는 경우 구글 클라우드 환경 기본 권한 사용
            firebase_admin.initialize_app()
            print("✅ Firebase initialized via Application Default Credentials")
            
    db = firestore.client()
except Exception as e:
    print(f"⚠️ Firebase Initialization Warning: {e}")

# --- 3. Gemini AI 클라이언트 설정 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ai_client = None
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)

# --- 4. 데이터 모델 정의 ---
class StarrFeedback(BaseModel):
    score: int
    summary: str
    s_feedback: str
    t_feedback: str
    a_feedback: str
    r_feedback: str
    reflection_feedback: str
    improved_answer: str

class StarrRequest(BaseModel):
    s: str
    t: str
    a: str
    r: str
    reflection: str
    job_title: str

# --- 5. 유틸리티 함수 ---
def get_client_ip(request: Request):
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def parse_md_with_json_frontmatter(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content_raw = f.read()
        match = re.match(r'---json\s*(\{.*\})\s*---(.*)', content_raw, re.DOTALL)
        parsed_metadata = {}
        body_content = content_raw
        if match:
            json_str = match.group(1).strip()
            body_content = match.group(2).strip()
            parsed_metadata = json.loads(json_str)
        
        post_obj = frontmatter.Post(body_content, metadata=parsed_metadata)
        if post_obj.metadata and 'metadata' in post_obj.metadata and isinstance(post_obj.metadata['metadata'], dict):
            post_obj.metadata = post_obj.metadata['metadata']
        return post_obj
    except Exception as e:
        print(f"❌ Markdown Parse Error ({filepath}): {e}")
        return None

def get_categories():
    if not os.path.exists(STRUCTURE_FILE): return []
    try:
        with open(STRUCTURE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("categories", [])
    except: return []

def get_items_by_category(category_slug: str):
    items = []
    if not os.path.exists(CONTENTS_DIR): return items
    for filename in sorted(os.listdir(CONTENTS_DIR)):
        if filename.endswith(".md"):
            post = parse_md_with_json_frontmatter(os.path.join(CONTENTS_DIR, filename))
            if post and post.metadata.get('category') == category_slug:
                item_data = post.metadata
                item_data['id'] = filename.replace('.md', '')
                if not item_data.get('thumbnail') or 'placeholder.jpg' in item_data.get('thumbnail'):
                    item_data['thumbnail'] = DEFAULT_PLACEHOLDER
                items.append(item_data)
    return items

# --- 6. 페이지 라우팅 ---

@app.get("/")
async def home(request: Request):
    categories_data = get_categories()
    grouped_items = []
    total_count = 0
    for cat in categories_data:
        items = get_items_by_category(cat['slug'])
        if items:
            cat_copy = cat.copy()
            cat_copy['job_items'] = items
            grouped_items.append(cat_copy)
            total_count += len(items)

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"grouped_items": grouped_items, "total_count": total_count, "last_updated": date.today().isoformat()}
    )

@app.get("/practice")
async def practice_page(request: Request):
    return templates.TemplateResponse(request=request, name="practice.html", context={})

@app.get("/career/{item_id}")
async def career_detail(request: Request, item_id: str):
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if not os.path.exists(filepath): raise HTTPException(status_code=404)
    post = parse_md_with_json_frontmatter(filepath)
    content_html = markdown.markdown(post.content, extensions=['tables'])
    return templates.TemplateResponse(
        request=request, name="detail.html",
        context={"item": post.metadata, "content": content_html}
    )

# --- 7. API 라우팅 (AI 분석 및 재시도 로직) ---

@app.post("/api/analyze-starr")
async def analyze_starr(request: Request, starr_data: StarrRequest):
    if not ai_client: raise HTTPException(status_code=503, detail="AI Service setup pending")

    # [1] IP 기반 제한 체크 (Firebase 이용)
    client_ip = get_client_ip(request)
    safe_ip = client_ip.replace(".", "_").replace(":", "_")
    today = date.today().isoformat()
    limit_path = f"usage_limits/{safe_ip}_{today}"
    count = 0

    if db:
        try:
            doc = db.document(limit_path).get()
            if doc.exists:
                count = doc.to_dict().get("count", 0)
            if count >= 3:
                raise HTTPException(status_code=429, detail="本日の利用制限（3回）に達しました。明日またお試しください。")
        except HTTPException: raise
        except Exception as e: print(f"DB Error: {e}")

    # [2] AI 분석 수행 (503/429 대응 재시도 로직)
    prompt = f"당신은 전문 면접관입니다. 다음 STARR 답변을 분석하고 일본어로 피드백하세요: {starr_data.dict()}"
    target_models = ["gemini-2.0-flash", "gemini-flash-latest"]
    feedback_result = None

    for model_name in target_models:
        for attempt in range(2): # 모델당 2회 시도
            try:
                response = ai_client.models.generate_content(
                    model=model_name, contents=prompt,
                    config={"response_mime_type": "application/json", "response_schema": StarrFeedback}
                )
                feedback_result = response.parsed
                break
            except Exception as e:
                print(f"⚠️ AI Attempt {attempt+1} ({model_name}) failed: {e}")
                time.sleep(2)
        if feedback_result: break

    if not feedback_result:
        raise HTTPException(status_code=500, detail="AI 서버가 혼잡합니다. 잠시 후 다시 시도해 주세요.")

    # [3] 성공 시 결과 저장
    if db:
        db.collection("interview_logs").add({
            "ip": client_ip, "input": starr_data.dict(),
            "output": feedback_result.dict(), "created_at": firestore.SERVER_TIMESTAMP
        })
        db.document(limit_path).set({"count": count + 1, "last_access": firestore.SERVER_TIMESTAMP}, merge=True)

    return feedback_result

# --- 8. 시스템 엔드포인트 ---

@app.get("/sitemap.xml")
async def sitemap(request: Request):
    base_url = str(request.base_url).rstrip('/')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += f'<url><loc>{base_url}/</loc><priority>1.0</priority></url>\n'
    xml += f'<url><loc>{base_url}/practice</loc><priority>0.9</priority></url>\n'
    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")

@app.get('/robots.txt', response_class=PlainTextResponse)
async def robots(): return "User-agent: *\nAllow: /"

@app.get('/ads.txt', response_class=FileResponse)
async def ads_txt():
    # static 폴더 안에 ads.txt 파일이 있어야 합니다.
    ads_path = os.path.join(STATIC_DIR, "ads.txt")
    if os.path.exists(ads_path):
        return ads_path
    return Response(status_code=404)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(STATIC_DIR, "img", "logo.png"))