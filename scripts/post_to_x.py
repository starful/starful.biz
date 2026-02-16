import os
import random
import tweepy
import json
import re
from dotenv import load_dotenv

# 로컬 환경용 .env 로드
load_dotenv()

# --- 경로 설정 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENTS_DIR = os.path.join(BASE_DIR, "app", "contents")
BASE_URL = "https://starful.biz/career/"

# --- X API 인증 설정 ---
auth = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

def parse_markdown_json(file_path):
    """---json 형식을 포함한 마크다운을 파싱합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    
    # ---json { ... } --- 패턴 추출
    match = re.match(r'---json\s*(\{.*?\})\s*---(.*)', raw_content, re.DOTALL)
    
    metadata = {}
    body_content = raw_content
    
    if match:
        json_str = match.group(1).strip()
        body_content = match.group(2).strip()
        try:
            metadata = json.loads(json_str)
        except:
            metadata = {}
            
    return metadata, body_content

def get_random_job():
    """마크다운 파일에서 상세 데이터를 추출합니다."""
    if not os.path.exists(CONTENTS_DIR):
        raise FileNotFoundError(f"Directory not found: {CONTENTS_DIR}")
        
    files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    if not files:
        raise FileNotFoundError("No markdown files found.")
        
    target_file = random.choice(files)
    file_path = os.path.join(CONTENTS_DIR, target_file)
    
    # 특수 파서 사용
    metadata, body = parse_markdown_json(file_path)
    
    slug = target_file.replace(".md", "")
    
    # 1. 제목 결정
    job_title = metadata.get("title") or slug.replace('_', ' ').title()
    
    # 2. 설명 결정 (meta_description이 없으면 본문에서 추출)
    job_desc = metadata.get("meta_description", "")
    if not job_desc or len(job_desc) < 5:
        # 마크다운 기호 제거 후 순수 텍스트만 추출
        clean_body = re.sub(r'[#*`>-]', '', body).strip()
        job_desc = clean_body[:100]
        
    # 3. 태그 결정
    tags = metadata.get("tags", [])
    tag_str = " / ".join(tags[:4]) if tags else "IT・Creative"
    
    return {
        "title": job_title,
        "desc": job_desc.replace('\n', ' '),
        "tags": tag_str,
        "url": f"{BASE_URL}{slug}"
    }

def post_tweet():
    """100% 일본어 정보 트윗을 게시합니다."""
    try:
        job = get_random_job()
        
        # 트윗 구성 (모든 문구 일본어 확인 완료)
        tweet_text = (
            f"＼今日の職種分析 🚀／\n\n"
            f"📌 【{job['title']}】\n\n"
            f"💡 どんな仕事？\n"
            f"{job['desc'][:85]}...\n\n"
            f"🛠 注目スキル\n"
            f"▸ {job['tags']}\n\n"
            f"🔗 キャリアの詳細はサイトでチェック！\n"
            f"{job['url']}\n\n"
            f"#キャリア #転職 #エンジニア #Starful"
        )

        auth.create_tweet(text=tweet_text)
        print(f"✅ 投稿成功: {job['title']}")
    except Exception as e:
        print(f"❌ エラー発生: {e}")

if __name__ == "__main__":
    post_tweet()