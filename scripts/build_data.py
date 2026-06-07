import os
import json
import re
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from slug_utils import normalize_slug

# 경로 설정
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'contents')
JSON_OUTPUT = os.path.join(BASE_DIR, 'app', 'static', 'json', 'job_data.json')
SITEMAP_OUTPUT = os.path.join(BASE_DIR, 'app', 'static', 'sitemap.xml')
BASE_URL = 'https://starful.biz'

def parse_starful_md(filepath):
    """Starful 특유의 ---json 형식을 해석합니다."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # ---json { ... } --- 패턴 추출
        match = re.match(r'---json\s*(\{.*?\})\s*---(.*)', raw_content, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            metadata = json.loads(json_str)
            return metadata
        return None
    except Exception as e:
        print(f"❌ 파싱 에러 ({os.path.basename(filepath)}): {e}")
        return None

def main():
    print(f"🔨 Starful 데이터 빌드 시작 (대상: {CONTENT_DIR})")
    jobs = []
    
    if not os.path.exists(CONTENT_DIR):
        print(f"❌ 폴더 없음: {CONTENT_DIR}")
        return

    for filename in os.listdir(CONTENT_DIR):
        if filename.endswith('.md'):
            filepath = os.path.join(CONTENT_DIR, filename)
            meta = parse_starful_md(filepath)
            
            if meta:
                job_id = normalize_slug(meta.get("slug") or filename.replace(".md", ""))
                jobs.append({
                    "id": job_id,
                    "title": meta.get('title', 'No Title'),
                    "category": meta.get('category', 'engineering'), # 기본값
                    "meta_description": meta.get('meta_description', '')[:160],
                    "tags": meta.get('tags', []),
                    "published": str(meta.get('published_at', datetime.now().strftime('%Y-%m-%d'))),
                    "link": f"/career/{job_id}"
                })

    # 최신순 정렬
    jobs.sort(key=lambda x: x['published'], reverse=True)
    
    final_data = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "total_count": len(jobs),
        "jobs": jobs
    }
    
    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"🎉 빌드 완료! 총 {len(jobs)}개 데이터를 {JSON_OUTPUT}에 저장했습니다.")

if __name__ == "__main__":
    main()