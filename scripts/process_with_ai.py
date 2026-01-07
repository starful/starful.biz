import os
import re
import frontmatter
import shutil
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- 설정 ---
SOURCE_DIR = "1_source_files"
OUTPUT_MD_DIR = "2_processed_files"
OUTPUT_IMG_DIR = "3_processed_images"
LOG_FILE = "processed_log.txt"
BATCH_SIZE = 50

# --- AI 환경 설정 ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def call_gemini_for_metadata(content):
    """Gemini AI에게 콘텐츠를 보내고 풍부한 메타데이터를 JSON으로 요청합니다."""
    # [수정] 모델을 gemini-flash-latest로 변경
    model = genai.GenerativeModel('gemini-flash-latest')
    
    # [수정] AI에게 더 상세한 정보를 요청하는 프롬프트
    prompt = f"""
    당신은 일본 IT 커리어 콘텐츠를 분석하여 구조화된 메타데이터를 생성하는 전문가입니다.
    아래 마크다운 콘텐츠를 분석하여, 다음 규칙에 따라 JSON 형식으로만 응답해주세요.

    [규칙]
    1.  `title`: H1(#) 제목을 그대로 사용합니다.
    2.  `slug`: `title`을 기반으로, URL에 사용하기 좋은 짧고 간결한 영어(소문자) 또는 로마자 슬러그를 만듭니다. (예: 'APIエンジニアガイド' -> 'api_engineer')
    3.  `category`: 콘텐츠 전체를 파악하여 다음 중 가장 적합한 카테고리 하나를 선택합니다: [engineering, design, marketing, product, data, sales, technology]
    4.  `meta_description`: 콘텐츠 전체를 80자 내외의 자연스러운 일본어 문장으로 요약하여, 검색엔진 결과에 표시될 설명을 만듭니다.
    5.  `keywords`: 콘텐츠의 핵심 키워드를 5개 정도 쉼표로 구분하여 나열합니다.
    6.  `tags`: 콘텐츠에 언급된 주요 기술, 프레임워크, 개념 등을 추출하여 JSON 배열(리스트) 형식으로 만듭니다.
    7.  `related_jobs`: 이 직업과 연관성이 높은 다른 직업의 `slug`를 2개 정도 JSON 배열(리스트) 형식으로 제안합니다.

    [마크다운 콘텐츠]
    {content[:8000]} 

    [응답 형식]
    반드시 아래와 같은 JSON 형식으로만 응답해야 하며, 다른 설명은 포함하지 마세요.
    ```json
    {{
      "title": "APIエンジニアガイド",
      "slug": "api_engineer",
      "category": "engineering",
      "meta_description": "APIエンジニアの仕事内容、必要な技術スタック（Python, Java）、キャリアパス、将来性について解説する総合ガイドです。",
      "keywords": "APIエンジニア, バックエンド, REST, GraphQL, マイクロサービス",
      "tags": ["Python", "Java", "Go", "RESTful API", "GraphQL"],
      "related_jobs": ["backend_engineer", "cloud_engineer"]
    }}
    ```
    """
    
    try:
        response = model.generate_content(prompt)
        json_text = re.search(r'```json\s*([\s\S]+?)\s*```', response.text)
        if json_text:
            return json.loads(json_text.group(1))
        else:
            return json.loads(response.text)
    except Exception as e:
        print(f"    - ❗️ AI 호출 또는 JSON 파싱 오류: {e}")
        return None

def get_processed_files():
    if not os.path.exists(LOG_FILE): return set()
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def log_processed_file(filename):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(filename + '\n')

def process_files():
    if not os.path.exists(SOURCE_DIR):
        print(f"エラー: ソースフォルダ '{SOURCE_DIR}' が見つかりません。")
        return

    os.makedirs(OUTPUT_MD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)

    processed_files_log = get_processed_files()
    all_md_files = sorted([f for f in os.listdir(SOURCE_DIR) if f.endswith(".md")])
    files_to_process = [f for f in all_md_files if f not in processed_files_log]

    if not files_to_process:
        print("🎉 すべてのファイルの処理が完了しています！")
        return

    print(f"全 {len(all_md_files)} ファイル中 {len(processed_files_log)} 個処理済み。残り: {len(files_to_process)} 個")
    print(f"今回のバッチでは最大 {BATCH_SIZE} 個のファイルを処理します。")
    
    batch_counter = 0
    for filename in files_to_process:
        if batch_counter >= BATCH_SIZE:
            print(f"\n今回のバッチ処理数（{BATCH_SIZE}個）に達しました。スクリプトを終了します。")
            break

        print(f"\n[{batch_counter + 1}/{BATCH_SIZE}] '{filename}' を処理中...")
        try:
            source_path = os.path.join(SOURCE_DIR, filename)
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = re.sub(r'\[f:id:.*?\]\s*', '', content).strip()
            ai_metadata = call_gemini_for_metadata(original_content)
            
            if not ai_metadata:
                print(f"    - ❌ AIからメタデータを取得できなかったため、スキップします。")
                continue

            new_filename_base = ai_metadata['slug']
            new_md_filename = f"{new_filename_base}.md"
            
            # [수정] AI가 생성한 모든 메타데이터를 사용
            final_metadata = {
                'title': ai_metadata.get('title'),
                'slug': new_filename_base,
                'category': ai_metadata.get('category'),
                'thumbnail': f'/static/img/{new_filename_base}.png',
                'meta_description': ai_metadata.get('meta_description'),
                'keywords': ai_metadata.get('keywords'),
                'tags': ai_metadata.get('tags'),
                'related_jobs': ai_metadata.get('related_jobs')
            }

            new_post = frontmatter.Post(original_content, **final_metadata)
            output_md_path = os.path.join(OUTPUT_MD_DIR, new_md_filename)
            with open(output_md_path, 'w', encoding='utf-8') as f: f.write(frontmatter.dumps(new_post))
            print(f"    - ✅ [MD] -> '{new_md_filename}' の保存が完了しました。")

            original_base_name = filename.replace('.md', '')
            source_png_path = os.path.join(SOURCE_DIR, f"{original_base_name}.png")
            
            if os.path.exists(source_png_path):
                new_png_filename = f"{new_filename_base}.png"
                output_png_path = os.path.join(OUTPUT_IMG_DIR, new_png_filename)
                shutil.copy2(source_png_path, output_png_path)
                print(f"    - 🖼️  [PNG] -> '{new_png_filename}' のコピーが完了しました。")

            log_processed_file(filename)
            batch_counter += 1
            time.sleep(2)

        except Exception as e:
            print(f"❌ [エラー] '{filename}' の処理中に予期せぬ問題が発生しました: {e}")
            
    print("\n-------------------------------------------")
    remaining_files = len(files_to_process) - batch_counter
    if remaining_files > 0:
        print(f"今回のバッチで {batch_counter} 個のファイルを正常に処理しました。")
        print(f"再度スクリプトを実行して、残りの {remaining_files} 個のファイルを処理してください。")
    else:
        print("🎉 すべてのファイルの処理が正常に完了しました！")

if __name__ == '__main__':
    process_files()