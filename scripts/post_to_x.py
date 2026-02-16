import os
import random
import tweepy
import frontmatter
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

def get_random_job():
    """마크다운 파일에서 상세 데이터를 추출합니다."""
    if not os.path.exists(CONTENTS_DIR):
        raise FileNotFoundError(f"Directory not found: {CONTENTS_DIR}")
        
    files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    if not files:
        raise FileNotFoundError("No markdown files found.")
        
    target_file = random.choice(files)
    file_path = os.path.join(CONTENTS_DIR, target_file)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    
    slug = target_file.replace(".md", "")
    
    # 데이터 추출 및 가공
    job_title = post.get("title", slug.replace('_', ' ').title())
    job_desc = post.get("meta_description", "")
    tags = post.get("tags", [])
    
    # 상위 3개 태그만 추출하여 문자열로 변환
    tag_str = " / ".join(tags[:4]) if tags else "IT・Creative"
    
    return {
        "title": job_title,
        "desc": job_desc,
        "tags": tag_str,
        "url": f"{BASE_URL}{slug}"
    }

def post_tweet():
    """정보량이 풍부한 일본어 트윗을 게시합니다."""
    try:
        job = get_random_job()
        
        # 트윗 구성 (정보량 극대화 스타일)
        tweet_text = (
            f"＼今日の職種分析 🚀／\n\n"
            f"📌 【{job['title']}】\n\n"
            f"💡 どんな仕事？\n"
            f"{job['desc'][:60]}...\n\n"
            f"🛠 注目スキル\n"
            f"▸ {job['tags']}\n\n"
            f"🔗 キャリアの詳細はサイトでチェック！\n"
            f"{job['url']}\n\n"
            f"#キャリア #転職 #エンジニア #Starful"
        )

        # 280자(일본어 기준 140자) 제한 확인 (Tweepy가 자동으로 처리하지만 가독성 위해 조절)
        auth.create_tweet(text=tweet_text)
        print(f"✅ 게시 성공: {job['title']}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    post_tweet()