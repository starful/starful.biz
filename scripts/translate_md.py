import os
import google.generativeai as genai
import time
import re
from dotenv import load_dotenv

# --- 설정 ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# 경로 설정
CONTENTS_DIR = "app/contents"
BACKUP_DIR = "app/contents_backup" # 만약을 대비한 백업 폴더

# 프롬프트 정의
TRANSLATE_PROMPT = """
You are a professional translator and IT expert. 
Your task is to translate all Korean text in the provided Markdown content into natural, professional Japanese.

Rules:
1. Translate all Korean values in the JSON frontmatter (e.g., meta_description, keywords, title) into Japanese. 
   - DO NOT translate JSON keys (e.g., keep "category", "slug" as is).
2. Translate all Korean text in the body into natural Japanese.
3. Keep all Markdown syntax, HTML tags, and English technical terms exactly as they are.
4. Maintain the professional tone of a career guide.
5. Output ONLY the translated content, starting from the '---json' block.

Content to translate:
{content}
"""

def translate_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()

    # 한국어가 포함되어 있는지 체크 (한글 유니코드 범위: AC00-D7A3)
    if not re.search('[가-힣]', original_content):
        print(f"⏩ Skip (No Korean found): {filepath}")
        return False

    print(f"🔄 Translating: {filepath}...")
    
    try:
        response = model.generate_content(
            TRANSLATE_PROMPT.format(content=original_content),
            generation_config=genai.types.GenerationConfig(temperature=0.1) # 정확도를 위해 낮은 온도로 설정
        )
        
        translated_text = response.text.strip()
        
        # 번역 결과가 너무 짧거나 에러인 경우 방어 로직
        if len(translated_text) < 10:
            print(f"❌ Error: Translation result too short for {filepath}")
            return False

        # 번역본 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(translated_text)
        
        print(f"✅ Success: {filepath}")
        return True

    except Exception as e:
        print(f"❌ Error translating {filepath}: {e}")
        return False

def main():
    # 백업 폴더 생성
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"📁 Created backup directory: {BACKUP_DIR}")

    files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    
    for filename in files:
        filepath = os.path.join(CONTENTS_DIR, filename)
        
        # 1. 백업 복사본 생성 (안전을 위해)
        backup_path = os.path.join(BACKUP_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())

        # 2. 번역 수행
        success = translate_file(filepath)
        
        # API 할당량 초과 방지를 위한 쉼표 (Gemini Free Tier 기준)
        if success:
            time.sleep(5) 

if __name__ == "__main__":
    main()