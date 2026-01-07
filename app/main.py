import os
import frontmatter
import markdown
import json # json 라이브러리 추가
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# --- 설정 및 경로 정의 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
CONTENTS_DIR = os.path.join(BASE_DIR, "contents")
STRUCTURE_FILE = os.path.join(BASE_DIR, "site_structure.json") # [신규] JSON 파일 경로

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


# --- [신규] 서버 시작 시 JSON 파일을 미리 로드 ---
try:
    with open(STRUCTURE_FILE, 'r', encoding='utf-8') as f:
        SITE_DATA = json.load(f)
except FileNotFoundError:
    print(f"경고: '{STRUCTURE_FILE}' 파일을 찾을 수 없습니다. 메인 페이지가 비어있을 수 있습니다.")
    SITE_DATA = {"categories": []}


# --- [수정됨] Helper 함수들 ---

def get_categories():
    """메모리에 로드된 데이터에서 카테고리 목록을 반환합니다."""
    return SITE_DATA.get("categories", [])

def get_category_details(slug: str):
    """메모리에 로드된 데이터에서 특정 카테고리의 상세 정보를 찾습니다."""
    for cat in get_categories():
        if cat.get('slug') == slug:
            return cat
    return None

def get_items_by_category(category_slug: str):
    """(변경 없음) 특정 카테고리에 속한 콘텐츠 목록을 파일 시스템에서 읽어옵니다."""
    items = []
    for filename in sorted(os.listdir(CONTENTS_DIR)):
        if filename.endswith(".md"):
            filepath = os.path.join(CONTENTS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                if post.metadata.get('category') == category_slug:
                    item_data = post.metadata
                    item_data['id'] = filename.replace('.md', '')
                    items.append(item_data)
    return items

# --- 라우트 (변경 없음) ---

@app.get("/")
async def home(request: Request):
    """메인 페이지: JSON 파일에 정의된 카테고리 목록을 보여줍니다."""
    categories_data = get_categories()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "categories": categories_data
    })

@app.get("/category/{category_slug}")
async def category_page(request: Request, category_slug: str):
    """카테고리별 목록 페이지: 해당 카테고리의 직업 목록을 보여줍니다."""
    category_details = get_category_details(category_slug)
    if not category_details:
        raise HTTPException(status_code=404, detail="Category not found")
        
    items_in_category = get_items_by_category(category_slug)
    
    return templates.TemplateResponse("category.html", {
        "request": request,
        "category": category_details,
        "items": items_in_category
    })

@app.get("/career/{item_id}")
async def career_detail(request: Request, item_id: str):
    """상세 페이지: 특정 직업의 상세 정보를 보여줍니다."""
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Content not found")
        
    with open(filepath, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
        content_html = markdown.markdown(post.content)
        
    return templates.TemplateResponse("detail.html", {
        "request": request,
        "item": post.metadata,
        "content": content_html
    })