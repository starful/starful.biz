import os
import json
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from slug_utils import normalize_slug
from md_metadata import parse_starful_md, published_date, ensure_published_at, write_starful_md

# 경로 설정
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'contents')
JSON_OUTPUT = os.path.join(BASE_DIR, 'app/static/json/job_data.json')
SITEMAP_OUTPUT = os.path.join(BASE_DIR, 'app/static/sitemap.xml')
BASE_URL = 'https://starful.biz'


def parse_starful_md_file(filepath):
    """Starful ---json MD → metadata dict."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        parsed = parse_starful_md(raw_content)
        if not parsed:
            return None
        meta, body = parsed
        meta, date, changed = ensure_published_at(meta, filepath)
        if changed:
            write_starful_md(filepath, meta, body)
        meta["published_at"] = date
        return meta
    except Exception as e:
        print(f"❌ 파싱 에러 ({os.path.basename(filepath)}): {e}")
        return None


def main():
    print(f"🔨 Starful 데이터 빌드 시작 (대상: {CONTENT_DIR})")
    jobs = []
    backfilled = 0

    if not os.path.exists(CONTENT_DIR):
        print(f"❌ 폴더 없음: {CONTENT_DIR}")
        return

    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(CONTENT_DIR, filename)
        with open(filepath, encoding='utf-8') as f:
            raw = f.read()
        parsed = parse_starful_md(raw)
        if not parsed:
            continue
        meta, body = parsed
        meta, date, changed = ensure_published_at(meta, filepath)
        if changed:
            write_starful_md(filepath, meta, body)
            backfilled += 1

        job_id = normalize_slug(meta.get("slug") or filename.replace(".md", ""))
        jobs.append({
            "id": job_id,
            "title": meta.get('title', 'No Title'),
            "category": meta.get('category', 'engineering'),
            "meta_description": meta.get('meta_description', '')[:160],
            "tags": meta.get('tags', []),
            "published": published_date(meta, filepath),
            "link": f"/career/{job_id}",
        })

    jobs.sort(key=lambda x: (x['published'], x['id']), reverse=True)

    final_data = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "total_count": len(jobs),
        "jobs": jobs,
    }

    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    if backfilled:
        print(f"📅 published_at 백필: {backfilled}개 MD")
    print(f"🎉 빌드 완료! 총 {len(jobs)}개 데이터를 {JSON_OUTPUT}에 저장했습니다.")


if __name__ == "__main__":
    main()
