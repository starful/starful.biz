import os
import frontmatter
import markdown
import json 
import re 
from datetime import datetime, date
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
BASE_URL = "https://www.starful.biz" # 실제 운영 도메인 주소

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


# --- [수정된 부분] 누락되었던 JSON 파일 로드 코드를 다시 추가합니다 ---
try:
    with open(STRUCTURE_FILE, 'r', encoding='utf-8') as f:
        SITE_DATA = json.load(f)
except FileNotFoundError:
    print(f"경고: '{STRUCTURE_FILE}' 파일이 없습니다. 메인 페이지가 비어 있을 수 있습니다.")
    SITE_DATA = {"categories": []}
except json.JSONDecodeError:
    print(f"경고: '{STRUCTURE_FILE}' 파일의 JSON 형식이 올바르지 않습니다.")
    SITE_DATA = {"categories": []}


# --- JSON Frontmatter 파싱 함수 ---
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
    if 'metadata' in post_obj.metadata and isinstance(post_obj.metadata['metadata'], dict):
        post_obj.metadata = post_obj.metadata['metadata']
    return post_obj


# --- 헬퍼 함수들 ---

def get_categories():
    categories_with_image_status = []
    for cat in SITE_DATA.get("categories", []):
        cat_copy = cat.copy()
        cat_copy['has_image'] = bool(cat_copy.get('image') and cat_copy['image'] != '/static/img/placeholder.jpg')
        if not cat_copy['has_image']:
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
            post.metadata.setdefault('thumbnail', '/static/img/placeholder.jpg')
            return post.metadata
    return None

def get_items_by_category(category_slug: str):
    items = []
    if not os.path.exists(CONTENTS_DIR): return items
    for filename in sorted(os.listdir(CONTENTS_DIR)):
        if filename.endswith(".md"):
            filepath = os.path.join(CONTENTS_DIR, filename)
            try:
                post = parse_md_with_json_frontmatter(filepath)
                if post and post.metadata and post.metadata.get('category') == category_slug:
                    item_data = post.metadata
                    item_data['id'] = filename.replace('.md', '')
                    item_data.setdefault('thumbnail', '/static/img/placeholder.jpg')
                    items.append(item_data)
            except Exception as e:
                print(f"ERROR: {filename} 처리 중 오류 발생: {e}")
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
    last_updated = datetime.fromtimestamp(latest_timestamp).strftime("%Y.%m.%d") if latest_timestamp > 0 else datetime.now().strftime("%Y.%m.%d")
    return {"total_guides": total_guides, "last_updated": last_updated}

def search_items(query: str):
    if not query or not os.path.exists(CONTENTS_DIR): return []
    
    found_items, added_ids = [], set()
    query_lower = query.lower()

    for filename in os.listdir(CONTENTS_DIR):
        if filename.endswith(".md"):
            item_id = filename.replace('.md', '')
            if item_id in added_ids: continue

            post = parse_md_with_json_frontmatter(os.path.join(CONTENTS_DIR, filename))
            if not (post and post.metadata): continue

            title = post.metadata.get("title", "").lower()
            keywords = [k.lower() for k in post.metadata.get("keywords", [])]
            
            is_match = query_lower in title or any(query_lower in k for k in keywords)
            
            if is_match:
                item_data = post.metadata
                item_data['id'] = item_id
                found_items.append(item_data)
                added_ids.add(item_id)
                        
    return found_items


# --- 라우트 (Routes) ---

@app.get("/")
async def home(request: Request):
    categories_data = get_categories()
    site_stats = get_site_stats()
    return templates.TemplateResponse("index.html", {
        "request": request, "categories": categories_data, "stats": site_stats
    })

@app.get("/search")
async def search_page(request: Request, q: str = ""):
    search_results = search_items(q)
    return templates.TemplateResponse("search_results.html", {
        "request": request, "query": q, "items": search_results, "results_count": len(search_results)
    })

@app.get("/category/{category_slug}")
async def category_page(request: Request, category_slug: str):
    category_details = get_category_details(category_slug)
    if not category_details: raise HTTPException(status_code=404, detail="Category not found")
    items_in_category = get_items_by_category(category_slug)
    return templates.TemplateResponse("category.html", {
        "request": request, "category": category_details, "items": items_in_category
    })

@app.get("/career/{item_id}")
async def career_detail(request: Request, item_id: str):
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if not os.path.exists(filepath): raise HTTPException(status_code=404, detail="Content not found")
    
    post = parse_md_with_json_frontmatter(filepath)
    if not (post and post.metadata): raise HTTPException(status_code=500, detail="Failed to parse content")
    
    content_html = markdown.markdown(post.content, extensions=['tables'])
    
    category_slug = post.metadata.get('category')
    category_details = get_category_details(category_slug) if category_slug else None
    post.metadata['category_title'] = category_details.get('title', category_slug.capitalize()) if category_details else (category_slug.capitalize() if category_slug else "Uncategorized")
    
    post.metadata.setdefault('hero_image', post.metadata.get('thumbnail', '/static/img/default_hero.jpg'))
    if post.metadata['hero_image'] == '/static/img/placeholder.jpg':
        post.metadata['hero_image'] = '/static/img/default_hero.jpg'

    related_jobs_data = []
    if 'related_jobs' in post.metadata and isinstance(post.metadata['related_jobs'], list):
        for job_id in post.metadata['related_jobs']:
            meta = get_item_metadata(job_id)
            if meta:
                related_jobs_data.append({
                    'id': job_id,
                    'title': meta.get('title', '관련 직업'),
                    "description": meta.get('meta_description', '상세 보기'),
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

@app.get("/sitemap.xml")
async def sitemap(request: Request):
    url_data = []
    today = date.today().isoformat()
    # 고정 페이지
    for page in ["", "/about", "/privacy"]:
        url_data.append({"loc": f"{BASE_URL}{page}", "lastmod": today, "changefreq": "weekly", "priority": "0.8" if page == "" else "0.5"})
    # 카테고리 페이지
    for cat in get_categories():
        url_data.append({"loc": f"{BASE_URL}/category/{cat['slug']}", "lastmod": today, "changefreq": "daily", "priority": "0.9"})
    # 상세 페이지
    if os.path.exists(CONTENTS_DIR):
        for filename in os.listdir(CONTENTS_DIR):
            if filename.endswith(".md"):
                filepath = os.path.join(CONTENTS_DIR, filename)
                url_data.append({
                    "loc": f"{BASE_URL}/career/{filename.replace('.md', '')}",
                    "lastmod": datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d'),
                    "changefreq": "monthly",
                    "priority": "1.0"
                })
    return templates.TemplateResponse("sitemap.xml", {"request": request, "url_data": url_data}, media_type="application/xml")

@app.get('/ads.txt', response_class=FileResponse)
async def ads_txt():
    return os.path.join(STATIC_DIR, "ads.txt")

@app.get('/robots.txt', response_class=FileResponse)
async def robots_txt():
    return os.path.join(STATIC_DIR, "robots.txt")