import os
import random
import tweepy
import frontmatter
from dotenv import load_dotenv

load_dotenv()

# --- 설정 ---
CONTENTS_DIR = "app/contents"
BASE_URL = "https://starful.biz/career/" # 본인 도메인

# X API 인증
auth = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

def get_random_job():
    files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    target_file = random.choice(files)
    
    with open(os.path.join(CONTENTS_DIR, target_file), 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    
    slug = target_file.replace(".md", "")
    return {
        "title": post.get("title", "職業 가이드"),
        "desc": post.get("meta_description", ""),
        "url": f"{BASE_URL}{slug}"
    }

def post_tweet():
    job = get_random_job()
    
    # 트윗 문구 구성 (일본어 타겟)
    tweet_text = f"【今日のキャリアガイド 🚀】\n\n" \
                 f"📌 {job['title']}\n" \
                 f"{job['desc'][:80]}...\n\n" \
                 f"자세히 보기 👇\n" \
                 f"{job['url']}\n\n" \
                 f"#キャリア #転職 #エンジニア #Starful"

    try:
        auth.create_tweet(text=tweet_text)
        print(f"✅ Tweet Posted: {job['title']}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    post_tweet()