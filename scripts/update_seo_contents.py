import os
import json
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- 설정 ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

CONTENTS_DIR = "app/contents"
BACKUP_DIR = "app/contents_seo_backup" # 만약을 대비한 백업

# --- AI 프롬프트 정의 ---
SEO_UPDATE_PROMPT = """
You are an SEO expert and Japanese career consultant. 
Based on the job title "{position_name}", please provide the following in Japanese:

1. Long-tail Title: Create a catchy, SEO-optimized title (within 50 chars) that includes keywords like "年収" (Salary), "将来性" (Future), "未経験" (Inexperienced), or "ロードマップ" (Roadmap).
2. Salary Table: Create a Markdown table for estimated annual salaries in Japan based on data from doda and OpenWork.
   Columns: [経験年数, 年収範囲 (万円), 特徴]
   Rows: [ジュニア (0-3年), ミドル (3-7年), シニア (7年以上/리드)]

Format:
---TITLE---
[Generated Long-tail Title]
---TABLE---
[Generated Markdown Table]
"""

def parse_markdown_json(raw_content):
    """기존 파일의 JSON 메타데이터와 본문을 분리합니다."""
    match = re.match(r'---json\s*(\{.*?\})\s*---(.*)', raw_content, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip()), match.group(2).strip()
    return None, raw_content

def update_file(filename):
    file_path = os.path.join(CONTENTS_DIR, filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    metadata, body = parse_markdown_json(raw_content)
    if not metadata:
        print(f"⏩ Skip (No JSON found): {filename}")
        return

    position_name = metadata.get('slug', filename.replace('.md', '')).replace('_', ' ')
    print(f"🔄 SEO Updating: {position_name}...")

    try:
        response = model.generate_content(
            SEO_UPDATE_PROMPT.format(position_name=position_name),
            generation_config=genai.types.GenerationConfig(temperature=0.2)
        )
        ai_output = response.text

        # AI 결과에서 타이틀과 표 추출
        new_title = re.search(r'---TITLE---\n(.*?)\n', ai_output).group(1).strip()
        salary_table = re.search(r'---TABLE---\n(.*)', ai_output, re.DOTALL).group(1).strip()

        # 1. 메타데이터 업데이트 (롱테일 제목 반영)
        metadata['title'] = new_title
        
        # 2. 본문 업데이트 (기존 본문의 맨 앞 혹은 적절한 위치에 연봉 표 삽입)
        # 이미 표가 있는지 체크 (중복 방지)
        if "年収範囲" not in body:
            salary_section = f"\n\n## 💰 日本での推定年収（doda・OpenWork参照）\n\n{salary_table}\n\n"
            # 1번 섹션(### 1.) 뒤에 삽입하거나 맨 위에 삽입
            body = salary_section + body

        # 3. 파일 저장
        new_content = f"---json\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n---\n{body}"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"✅ Updated: {filename} -> {new_title}")
        return True

    except Exception as e:
        print(f"❌ Error updating {filename}: {e}")
        return False

def main():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    print(f"🚀 Found {len(files)} files to SEO optimize.")

    for filename in files:
        # 백업 생성
        with open(os.path.join(CONTENTS_DIR, filename), 'r', encoding='utf-8') as src:
            with open(os.path.join(BACKUP_DIR, filename), 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        success = update_file(filename)
        if success:
            time.sleep(3) # API 할당량 조절

if __name__ == "__main__":
    main()