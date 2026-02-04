import os
import frontmatter
import markdown
import json 
import re 
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

app = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


# --- 서버 시작시에 JSON 파일을 미리 로드 ---
try:
    with open(STRUCTURE_FILE, 'r', encoding='utf-8') as f:
        SITE_DATA = json.load(f)
except FileNotFoundError:
    print(f"警告: '{STRUCTURE_FILE}' ファイルが見つかりません。メインページが空になる可能性があります。")
    SITE_DATA = {"categories": []}


# --- [수정] JSON Frontmatter를 직접 파싱하는 함수 ---
def parse_md_with_json_frontmatter(filepath):
    """
    MD ファイルから ---json...--- ブロックを探し、JSON Frontmatterと本文コンテンツをパースします。
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content_raw = f.read()

    # ---jsonで始まり ---で終わるJSON Frontmatterブロックを正規表現で探します。
    match = re.match(r'---json\s*(\{.*\})\s*---(.*)', content_raw, re.DOTALL)

    parsed_metadata = {}
    body_content = content_raw # 기본적으로 전체 내용을 본문으로 설정

    if match:
        json_str = match.group(1).strip()
        body_content = match.group(2).strip() # 본문은 --- 이후부터 시작
        try:
            parsed_metadata = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSONDecodeError parsing frontmatter for {filepath}: {e}\nProblematic JSON:\n{json_str}")
            # 파싱 실패 시, 메타데이터는 비어있고 본문은 원래 내용 그대로
            parsed_metadata = {}
    else:
        # ---json 블록이 없는 경우, 기존 frontmatter.load()를 시도하여 YAML 등을 처리 (Fallback)
        try:
            post_fallback = frontmatter.load(content_raw)
            if post_fallback and post_fallback.metadata:
                parsed_metadata = post_fallback.metadata
            body_content = post_fallback.content # fallback 시에는 본문도 다시 할당
        except Exception as e:
            print(f"ERROR: Failed to parse any frontmatter for {filepath} with default handler: {e}")
            parsed_metadata = {} # fallback 실패 시에도 빈 메타데이터

    # [최종 수정] frontmatter.Post 객체 생성 시 parsed_metadata를 직접 할당하여 중첩 방지
    # frontmatter.Post는 metadata 인자에 딕셔너리를 직접 받습니다.
    # 기존 코드에서 metadata=metadata 형태로 전달했는데, 로그에 중첩이 보인 것은 매우 특이합니다.
    # 명확하게 Post 객체의 .metadata 속성에 직접 딕셔너리를 할당하는 것으로 변경합니다.
    post_obj = frontmatter.Post(body_content, metadata=parsed_metadata)
    
    # 만약 어떤 이유로 post_obj.metadata가 중첩되어 있다면, 여기서 강제로 풀어줍니다.
    # 이는 방어적인 코드입니다.
    if post_obj.metadata and 'metadata' in post_obj.metadata and isinstance(post_obj.metadata['metadata'], dict):
        post_obj.metadata = post_obj.metadata['metadata']

    return post_obj


# --- 헬퍼 함수들에서 parse_md_with_json_frontmatter 사용 ---

def get_categories():
    """メモリにロードされたデータからカテゴリリストを返します。"""
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
    """メモリにロードされたデータから特定のカテゴリの詳細情報を見つけます。"""
    for cat in get_categories():
        if cat.get('slug') == slug:
            return cat
    return None

def get_item_metadata(item_id: str):
    """特定のアイテムのメタデータを取得します。"""
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if os.path.exists(filepath):
        post = parse_md_with_json_frontmatter(filepath)
        if post and post.metadata: 
            if 'thumbnail' not in post.metadata or not post.metadata['thumbnail']:
                post.metadata['thumbnail'] = '/static/img/placeholder.jpg'
            return post.metadata
    return None

def get_items_by_category(category_slug: str):
    """特定のカテゴリに属するコンテンツリストをファイルシステムから読み込みます。"""
    items = []
    # print(f"DEBUG: Attempting to load items for category: {category_slug} from {CONTENTS_DIR}")
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
                # else:
                #     print(f"DEBUG: {filename} has no valid metadata parsed.")
            except Exception as e:
                print(f"ERROR: Failed to load or parse frontmatter for {filename}: {e}")
    # print(f"DEBUG: Found {len(items)} items for category {category_slug}.")
    return items

def get_all_item_ids():
    """contents 디렉토리의 모든 마크다운 파일 ID 목록을 반환합니다."""
    ids = []
    if not os.path.exists(CONTENTS_DIR):
        return ids
    for filename in sorted(os.listdir(CONTENTS_DIR)):
        if filename.endswith(".md"):
            ids.append(filename.replace('.md', ''))
    return ids

@app.get("/")
async def home(request: Request):
    """メインページ: JSONファイルに定義されたカテゴリリストを表示します。"""
    categories_data = get_categories()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "categories": categories_data
    })

@app.get("/category/{category_slug}")
async def category_page(request: Request, category_slug: str):
    """カテゴリ別リストページ: そのカテゴリの職種リストを表示します。"""
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
    """詳細ページ: 特定の職種の詳細情報を表示します。"""
    filepath = os.path.join(CONTENTS_DIR, f"{item_id}.md")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Content not found")
        
    post = parse_md_with_json_frontmatter(filepath)
    if not post or not post.metadata:
        raise HTTPException(status_code=500, detail="Failed to parse content metadata for detail page")
    
    content_html = markdown.markdown(post.content, extensions=['tables'])

    category_slug = post.metadata.get('category')
    category_details = get_category_details(category_slug)
    if category_details:
        post.metadata['category_title'] = category_details.get('title', category_slug.capitalize())
    else:
        post.metadata['category_title'] = category_slug.capitalize()

    if 'hero_image' not in post.metadata or not post.metadata['hero_image']:
        if 'thumbnail' in post.metadata and post.metadata['thumbnail'] != '/static/img/placeholder.jpg':
            post.metadata['hero_image'] = post.metadata['thumbnail']
        else:
            post.metadata['hero_image'] = '/static/img/default_hero.jpg'
    
    related_jobs_data = []
    if 'related_jobs' in post.metadata and isinstance(post.metadata['related_jobs'], list):
        for related_job_id in post.metadata['related_jobs']:
            related_item_meta = get_item_metadata(related_job_id)
            if related_item_meta:
                related_jobs_data.append({
                    'id': related_job_id,
                    'title': related_item_meta.get('title', related_job_id.replace('_', ' ').title()),
                    "description": related_item_meta.get('meta_description', '詳細を見る'),
                    'thumbnail': related_item_meta.get('thumbnail', '/static/img/placeholder.jpg')
                })

    return templates.TemplateResponse("detail.html", {
        "request": request,
        "item": post.metadata,
        "content": content_html,
        "related_jobs_data": related_jobs_data
    })

@app.get("/about")
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/privacy")
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/sitemap.xml")
async def sitemap(request: Request):
    """동적으로 sitemap.xml을 생성합니다."""
    # 중요: 실제 서비스 도메인으로 변경해야 합니다.
    base_url = str(request.base_url)
    if base_url.endswith('/'):
        base_url = base_url[:-1]

    all_categories = get_categories()
    all_item_ids = get_all_item_ids()
    
    try:
        content = templates.get_template("sitemap.xml").render(
            request=request, 
            base_url=base_url,
            categories=all_categories,
            item_ids=all_item_ids
        )
        return Response(content=content, media_type="application/xml")
    except Exception as e:
        # 템플릿 렌더링 중 오류 발생 시 500 에러와 함께 로그를 남깁니다.
        print(f"Error rendering sitemap: {e}")
        raise HTTPException(status_code=500, detail="Error generating sitemap.")


@app.get('/ads.txt', response_class=FileResponse)
async def ads_txt():
    return os.path.join(STATIC_DIR, "ads.txt")

@app.get('/robots.txt', response_class=FileResponse)
async def robots_txt():
    return os.path.join(STATIC_DIR, "robots.txt")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # app/static/img/favicon.png 파일을 반환합니다.
    return FileResponse(os.path.join(STATIC_DIR, "img", "starful.biz_h.png"))