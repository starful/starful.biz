import os
import frontmatter
import markdown
import json 
import re 
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

# --- 설정 및 경로 정의 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CONTENTS_DIR = os.path.join(BASE_DIR, "contents")
STRUCTURE_FILE = os.path.join(BASE_DIR, "site_structure.json")
DEFAULT_PLACEHOLDER = "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?q=80&w=800&auto=format&fit=crop"

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --- 서버 시작시에 JSON 데이터 로드 ---
try:
    with open(STRUCTURE_FILE, 'r', encoding='utf-8') as f:
        SITE_DATA = json.load(f)
except Exception:
    SITE_DATA = {"categories": []}

# --- 마크다운 파서 (JSON Frontmatter 대응 및 중첩 방지) ---
def parse_md_with_json_frontmatter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content_raw = f.read()
    match = re.match(r'---json\s*(\{.*\})\s*---(.*)', content_raw, re.DOTALL)
    parsed_metadata = {}
    body_content = content_raw
    if match:
        json_str = match.group(1).strip()
        body_content = match.group(2).strip()
        try:
            parsed_metadata = json.loads(json_str)
        except: parsed_metadata = {}
    
    post_obj = frontmatter.Post(body_content, metadata=parsed_metadata)
    # 중첩된 metadata 구조 방어 로직
    if post_obj.metadata and 'metadata' in post_obj.metadata and isinstance(post_obj.metadata['metadata'], dict):
        post_obj.metadata = post_obj.metadata['metadata']
    return post_obj

# --- 데이터 헬퍼 함수들 ---
def get_categories():
    return SITE_DATA.get("categories", [])

def get_item_metadata(item_id: str):
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if os.path.exists(filepath):
        return parse_md_with_json_frontmatter(filepath).metadata
    return None


def get_items_by_category(category_slug: str):
    items = []
    if not os.path.exists(CONTENTS_DIR): return items
    for filename in sorted(os.listdir(CONTENTS_DIR)):
        if filename.endswith(".md"):
            post = parse_md_with_json_frontmatter(os.path.join(CONTENTS_DIR, filename))
            if post.metadata.get('category') == category_slug:
                item_data = post.metadata
                item_data['id'] = filename.replace('.md', '')
                # 이미지가 없거나 placeholder.jpg인 경우 교체
                if not item_data.get('thumbnail') or 'placeholder.jpg' in item_data.get('thumbnail'):
                    item_data['thumbnail'] = DEFAULT_PLACEHOLDER
                items.append(item_data)
    return items

def get_all_item_ids():
    if not os.path.exists(CONTENTS_DIR): return []
    return [f.replace('.md', '') for f in os.listdir(CONTENTS_DIR) if f.endswith('.md')]

# --- 메인 라우팅 섹션 ---

@app.get("/")
async def home(request: Request):
    """메인 페이지: 카테고리별 그룹화 리스트 + 자동 통계"""
    categories_data = get_categories()
    grouped_items = []
    total_count = 0
    
    for cat in categories_data:
        cat_copy = cat.copy()
        items = get_items_by_category(cat_copy['slug'])
        if items:
            cat_copy['job_items'] = items # 템플릿 예약어 충돌 방지
            grouped_items.append(cat_copy)
            total_count += len(items)

    # 날짜 및 통계 계산
    last_updated = datetime.now().strftime('%Y-%m-%d')
    all_ids = get_all_item_ids()
    if all_ids:
        latest_time = 0
        for iid in all_ids:
            p = os.path.join(CONTENTS_DIR, f"{iid}.md")
            if os.path.exists(p):
                mt = os.path.getmtime(p)
                if mt > latest_time: latest_time = mt
        if latest_time > 0:
            last_updated = datetime.fromtimestamp(latest_time).strftime('%Y-%m-%d')

    return templates.TemplateResponse("index.html", {
        "request": request,
        "grouped_items": grouped_items,
        "total_count": total_count,
        "last_updated": last_updated
    })

@app.get("/career/{item_id}")
async def career_detail(request: Request, item_id: str):
    """상세 가이드 페이지"""
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if not os.path.exists(filepath): raise HTTPException(status_code=404)
    
    post = parse_md_with_json_frontmatter(filepath)
    content_html = markdown.markdown(post.content, extensions=['tables'])
    
    # 카테고리 타이틀 찾기
    cat_title = "Career Guide"
    for c in get_categories():
        if c['slug'] == post.metadata.get('category'):
            cat_title = c['title']
            break

    related_jobs = []
    for rid in post.metadata.get('related_jobs', []):
        rmeta = get_item_metadata(rid)
        if rmeta:
            rmeta['id'] = rid
            related_jobs.append(rmeta)

    return templates.TemplateResponse("detail.html", {
        "request": request,
        "item": post.metadata,
        "content": content_html,
        "related_jobs_data": related_jobs,
        "category_title": cat_title
    })

@app.get("/search")
async def search(request: Request, q: str = ""):
    """검색 결과 페이지"""
    results = []
    if q:
        for iid in get_all_item_ids():
            meta = get_item_metadata(iid)
            if meta and (q.lower() in meta.get('title','').lower() or q.lower() in meta.get('meta_description','').lower()):
                meta['id'] = iid
                results.append(meta)
    return templates.TemplateResponse("search_results.html", {
        "request": request, 
        "query": q, 
        "items": results,
        "results_count": len(results)
    })

@app.get("/about")
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/privacy")
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

# --- 시스템 파일 및 SEO 라우팅 ---

@app.get("/sitemap.xml")
async def sitemap(request: Request):
    """동적 sitemap.xml 생성"""
    base_url = str(request.base_url).rstrip('/')
    item_ids = get_all_item_ids()
    
    # sitemap 템플릿이 없을 경우를 대비한 문자열 생성 방식
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    # 메인 페이지
    xml_content += f'  <url><loc>{base_url}/</loc><priority>1.0</priority></url>\n'
    # 상세 페이지들
    for iid in item_ids:
        xml_content += f'  <url><loc>{base_url}/career/{iid}</loc><priority>0.8</priority></url>\n'
    xml_content += '</urlset>'
    
    return Response(content=xml_content, media_type="application/xml")

@app.get('/ads.txt', response_class=FileResponse)
async def ads_txt():
    return os.path.join(STATIC_DIR, "ads.txt")

@app.get('/robots.txt', response_class=FileResponse)
async def robots_txt():
    return os.path.join(STATIC_DIR, "robots.txt")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # 로고를 파비콘으로 사용
    return FileResponse(os.path.join(STATIC_DIR, "img", "logo.png"))