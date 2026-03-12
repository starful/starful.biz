import os
import json
import re

# 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENTS_DIR = os.path.join(BASE_DIR, "app", "contents")

def clean_broken_links():
    if not os.path.exists(CONTENTS_DIR):
        print(f"❌ 폴더를 찾을 수 없습니다: {CONTENTS_DIR}")
        return

    files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    # 실제로 존재하는 파일들의 slug 목록
    valid_slugs = set([f.replace(".md", "") for f in files])
    
    fixed_count = 0
    
    for filename in files:
        filepath = os.path.join(CONTENTS_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        match = re.match(r'---json\s*(\{.*?\})\s*---(.*)', content, re.DOTALL)
        if not match:
            continue
            
        metadata = json.loads(match.group(1))
        body = match.group(2)
        
        related_jobs = metadata.get("related_jobs", [])
        if not related_jobs:
            continue
            
        # 🎯 AI가 실수로 만든 하이픈(-)을 언더스코어(_)로 자동 교정하며 체크
        valid_related = []
        for job in related_jobs:
            # 혹시 모를 하이픈(-)이나 공백을 언더스코어(_)로 통일
            safe_job = job.replace("-", "_").replace(" ", "_").lower()
            
            # 교정한 이름이 실제 파일 목록에 있으면 살려둠
            if safe_job in valid_slugs:
                valid_related.append(safe_job)
        
        # 목록이 변경되었거나 교정이 일어났다면 파일 덮어쓰기
        if related_jobs != valid_related:
            metadata["related_jobs"] = valid_related
            new_content = f"---json\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n---{body}"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            fixed_count += 1
            print(f"✅ 링크 자동 교정 및 정리 완료: {filename}")

    print(f"\n🎉 총 {fixed_count}개의 파일에서 관련 직무 링크를 정상화했습니다.")

if __name__ == "__main__":
    clean_broken_links()