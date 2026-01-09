import os
import frontmatter
import markdown
import json 
import re 
from datetime import datetime, date # date 추가
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response # Response 추가

# --- 설정 및 경로 정의 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CONTENTS_DIR = os.path.join(BASE_DIR, "contents")
STRUCTURE_FILE = os.path.join(BASE_DIR, "site_structure.json")

# [중요] 실제 운영 도메인 주소를 입력하세요.
BASE_URL = "https://www.starful.biz" 

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


# --- 서버 시작 시 JSON 파일 사전 로드 ---
try:
    with open(STRUCTURE_FILE, 'r', encoding='utf-8') as f:
        SITE_DATA = json.load(f)
except FileNotFoundError:
    print(f"경고: '{STRUCTURE_FILE}' 파일이 없습니다. 메인 페이지가 비어 있을 수 있습니다.")
    SITE_DATA = {"categories": []}


# --- JSON Frontmatter 파싱 함수 ---
def parse_md_with_json_frontmatter(filepath):
    # (이 함수 내용은 변경 없음)
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
        except json.JSONDecodeError:
            parsed_metadata = {}
    else:
        try:
            post_fallback = frontmatter.loads(content_raw)
            if post_fallback and post_fallback.metadata:
                parsed_metadata = post_fallback.metadata
            body_content = post_fallback.content
        except Exception:
            parsed_metadata = {}
    post_obj = frontmatter.Post(body_content, metadata=parsed_metadata)
    if post_obj.metadata and 'metadata' in post_obj.metadata and isinstance(post_obj.metadata['metadata'], dict):
        post_obj.metadata = post_obj.metadata['metadata']
    return post_obj


# --- 헬퍼 함수들 ---
# (get_categories, get_category_details, get_item_metadata, get_items_by_category, get_site_stats 함수 변경 없음)

def get_categories():
    categories_with_image_status = []
    for cat in SITE_DATA.get("categories", []):
        cat_copy = cat.copy()
        if cat_copy.get('image') and cat_copy['image'] != '/static/img/placeholder.jpg':
            cat_copy['has_image'] = True
        else:
            cat_copy['has_image'] = False
            cat_copy['image'] = '/static/img/placeholder.jpg'
        categories_with_image_status.append(cat_copy)
    return categories_with_image_status

def get_category_details(slug: str):
    for cat in get_categories():
        if cat.get('slug') == slug:
            return cat
    return None

def get_item_metadata(item_id: str):
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if os.path.exists(filepath):
        post = parse_md_with_json_frontmatter(filepath)
        if post and post.metadata: 
            if 'thumbnail' not in post.metadata or not post.metadata['thumbnail']:
                post.metadata['thumbnail'] = '/static/img/placeholder.jpg'
            return post.metadata
    return None

def get_items_by_category(category_slug: str):
    items = []
    for filename in sorted(os.listdir(CONTENTS_DIR)):
        if filename.endswith(".md"):
            filepath = os.path.join(CONTENTS_DIR, filename)
            try:
                post = parse_md_with_json_frontmatter(filepath)
                if post and post.metadata: 
                    item_category = post.metadata.get('category') 
                    if item_category == category_slug: 
                        item_data = post.metadata
                        item_data['id'] = filename.replace('.md', '')
                        if 'thumbnail' not in item_data or not item_data['thumbnail']:
                            item_data['thumbnail'] = '/static/img/placeholder.jpg'
                        items.append(item_data)
            except Exception as e:
                print(f"ERROR: Failed to load or parse frontmatter for {filename}: {e}")
    return items

def get_site_stats():
    total_guides = 0
    latest_timestamp = 0
    if os.path.exists(CONTENTS_DIR):
        md_files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
        total_guides = len(md_files)
        if md_files:
            timestamps = [os.path.getmtime(os.path.join(CONTENTS_DIR, f)) for f in md_files]
            latest_timestamp = max(timestamps)
    if latest_timestamp > 0:
        last_updated = datetime.fromtimestamp(latest_timestamp).strftime("%Y.%m.%d")
    else:
        last_updated = datetime.now().strftime("%Y.%m.%d")
    return {"total_guides": total_guides, "last_updated": last_updated}

# --- 라우트 (Routes) ---
# (home, category_page, career_detail, about_page, privacy_page 등 기존 라우트는 변경 없음)

@app.get("/")
async def home(request: Request):
    categories_data = get_categories()
    site_stats = get_site_stats()
    return templates.TemplateResponse("index.html", {
        "request": request, "categories": categories_data, "stats": site_stats
    })

@app.get("/category/{category_slug}")
async def category_page(request: Request, category_slug: str):
    category_details = get_category_details(category_slug)
    if not category_details:
        raise HTTPException(status_code=404, detail="Category not found")
    items_in_category = get_items_by_category(category_slug)
    return templates.TemplateResponse("category.html", {
        "request": request, "category": category_details, "items": items_in_category
    })

@app.get("/career/{item_id}")
async def career_detail(request: Request, item_id: str):
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Content not found")
    post = parse_md_with_json_frontmatter(filepath)
    if not post or not post.metadata:
        raise HTTPException(status_code=500, detail="Failed to parse content metadata")
    content_html = markdown.markdown(post.content, extensions=['tables'])
    category_slug = post.metadata.get('category')
    category_details = get_category_details(category_slug)
    post.metadata['category_title'] = category_details.get('title', category_slug.capitalize()) if category_details else category_slug.capitalize()
    if 'hero_image' not in post.metadata or not post.metadata['hero_image']:
        post.metadata['hero_image'] = post.metadata.get('thumbnail', '/static/img/default_hero.jpg') if post.metadata.get('thumbnail') != '/static/img/placeholder.jpg' else '/static/img/default_hero.jpg'
    related_jobs_data = []
    if 'related_jobs' in post.metadata and isinstance(post.metadata['related_jobs'], list):
        for related_job_id in post.metadata['related_jobs']:
            related_item_meta = get_item_metadata(related_job_id)
            if related_item_meta:
                related_jobs_data.append({
                    'id': related_job_id,
                    'title': related_item_meta.get('title', '관련 직업'),
                    "description": related_item_meta.get('meta_description', '상세 보기'),
                })
    return templates.TemplateResponse("detail.html", {
        "request": request, "item": post.metadata, "content": content_html, "related_jobs_data": related_jobs_data
    })

@app.get("/about")
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/privacy")
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

# --- [새로 추가된 사이트맵 라우트] ---
@app.get("/sitemap.xml")
async def sitemap(request: Request):
    """동적으로 sitemap.xml을 생성합니다."""
    url_data = []
    
    # 오늘 날짜 (YYYY-MM-DD 형식)
    today = date.today().isoformat()

    # 1. 고정 페이지 추가 (메인, about, privacy)
    static_pages = ["", "/about", "/privacy"]
    for page in static_pages:
        url_data.append({
            "loc": f"{BASE_URL}{page}",
            "lastmod": today,
            "changefreq": "weekly",
            "priority": "0.8" if page == "" else "0.5"
        })

    # 2. 카테고리 페이지 추가
    categories = get_categories()
    for cat in categories:
        url_data.append({
            "loc": f"{BASE_URL}/category/{cat['slug']}",
            "lastmod": today, # 최신 글 날짜로 대체 가능
            "changefreq": "daily",
            "priority": "0.9"
        })

    # 3. 직무 상세 페이지 추가
    if os.path.exists(CONTENTS_DIR):
        for filename in os.listdir(CONTENTS_DIR):
            if filename.endswith(".md"):
                item_id = filename.replace('.md', '')
                filepath = os.path.join(CONTENTS_DIR, filename)
                last_mod_timestamp = os.path.getmtime(filepath)
                last_mod_date = datetime.fromtimestamp(last_mod_timestamp).strftime('%Y-%m-%d')
                
                url_data.append({
                    "loc": f"{BASE_URL}/career/{item_id}",
                    "lastmod": last_mod_date,
                    "changefreq": "monthly",
                    "priority": "1.0"
                })

    # 템플릿을 사용하여 XML 응답 생성
    response = templates.TemplateResponse(
        "sitemap.xml", 
        {"request": request, "url_data": url_data},
        media_type="application/xml"
    )
    return response

# --- 기존 정적 파일 라우트 ---
@app.get('/ads.txt', response_class=FileResponse)
async def ads_txt():
    return os.path.join(STATIC_DIR, "ads.txt")

@app.get('/robots.txt', response_class=FileResponse)
async def robots_txt():
    return os.path.join(STATIC_DIR, "robots.txt")