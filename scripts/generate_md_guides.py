import pandas as pd
import os
import google.generativeai as genai
import logging
import json
import re
from dotenv import load_dotenv
import concurrent.futures

# --- .env 파일 로드 ---
load_dotenv()

# --- 설정 ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEYが .env ファイルに設定されていません。")

genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-flash-latest" 
OUTPUT_DIR = "app/contents/"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE = os.path.join(BASE_DIR, "scripts", "data", "positions.csv")
LOG_FILE = os.path.join(BASE_DIR, "scripts", "log", "generation_log.txt")

# 🎯 [핵심 설정] 한 번 실행 시 최대로 생성할 파일 개수 (원하는 숫자로 변경하세요)
MAX_TO_GENERATE = 160

# 병렬 처리할 워커 개수 (유료 API이므로 5~10개 동시 실행 가능)
MAX_WORKERS = 8 

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CREATED: %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')]
)

model = genai.GenerativeModel(MODEL_NAME)

# --- Frontmatter 프롬프트 ---
FRONTMATTER_PROMPT = """
あなたは、ITおよび技術職務に関するブログ記事のMarkdown Frontmatter (JSON形式のメタデータ)を生成する専門家です。
「{position_name}」に関するFrontmatterを以下の構造を厳守し生成してください。
【重要】タイトルには職種名だけでなく「年収」「将来性」「未経験」「ロードマップ」などのキーワードを含めたクリックしたくなるロングテールタイトルを作成してください。

---json
{{
  "category": "{{engineering, ai-data, design, marketing, cloud-infra, product-management, cyber-security, sales-bizdev, customer-success, content-strategyから1つ選択}}",
  "keywords": [{{キーワードを5〜10個}}],
  "meta_description": "{{職務のリアルな現実とやりがいを含む魅力的な説明文（100字程度）}}",
  "related_jobs": [{{関連職務のslugを2〜3個。必ずスネークケース（_）を使用すること。例：["data_scientist", "backend_developer"]}}],
  "slug": "{{職務名を必ずスネークケース（_）に変換したID。例：crm_marketer}}",
  "tags": [{{関連タグを5〜10個}}],
  "thumbnail": "/static/img/{{slug}}.png",
  "hero_image": "/static/img/{{slug}}_hero.png",
  "title": "{{クリック率を高めるロングテールタイトル（日本語30字以内）}}"
}}
---
"""

BODY_PROMPT = """
# 🎯 職種別・ガチ面接対策プロンプト（完全版・圧倒的ボリューム）

あなたは**IT業界に精通した現役の採用担当責任者兼、凄腕の技術面接官**です。
今回は「{position_name}」の採用面接において、面接の最初から最後までを網羅した**【完全無欠の面接対策バイブル】**を執筆してください。

【執筆の絶対ルール】
1. **目標文字数**: **日本語で8,000字〜10,000字程度**。
2. **【超重要：Markdownの改行とフォーマット厳守】** 読者の可読性を最大化するため、各質問や解説の間に**必ず空白行（改行）**を入れ、指定されたMarkdownフォーマットを崩さずに記述してください。

---記事の構成とフォーマットガイド---

## 導入：{position_name}の面接官は「ここ」を見ている
面接官が最も警戒している地雷（NGな候補者）と、最も求めているコアスキルをリアルな本音ベースで暴露してください。

## 🗣️ {position_name}特化型：よくある「一般質問」の罠と模範解答
「自己紹介」「退職理由」に対し、「{position_name}として」どう答えるのが正解かを解説してください。（※具体的なNG例と模範解答を分けて改行して記述すること）

## ⚔️ 【経験年数別】容赦ない「技術・専門知識」質問リスト
実務経験がないと答えられない技術質問を、候補者のレベル別に出題・解説してください。
**【厳守フォーマット】各深掘り解説および一問一答は、以下のMarkdown構造と「改行」をそのままコピーして使用してください。**

### 🌱 ジュニア層（実務未経験〜3年）への質問
#### 【深掘り解説】
**Q1. [具体的な技術質問を入力]**

- **💡 面接官の意図**:
  [ここに意図を記述。改行を必ず入れること]
- **❌ NGな回答**:
  [ここにNG例を記述]
- **⭕ 模範解答**:
  [ここに模範解答を記述]

**Q2. [具体的な技術質問を入力]**
（Q1と同じフォーマット・改行で記述）

#### 【一問一答ドリル】（※最低5問以上。必ずQとAを改行して出力すること）
- **Q. [質問を入力]**
  - **A.** [1〜2行で回答の要点を記述]

- **Q. [質問を入力]**
  - **A.** [1〜2行で回答の要点を記述]

### 🌲 ミドル層（実務3年〜7年）への質問
（ジュニア層と全く同じ【厳守フォーマット】を用いて、Q1〜Q2の深掘り解説と、最低5問の一問一答ドリルを作成）

### 🌳 シニア・リード層（実務7年以上〜マネージャー）への質問
（ジュニア層と全く同じ【厳守フォーマット】を用いて、Q1〜Q2の深掘り解説と、最低5問の一問一答ドリルを作成）

## 🧠 思考力と修羅場経験を探る「行動・ソフトスキル質問」
チームの対立、理不尽な交渉など、問題解決能力を問うシチュエーション質問を厳選してください。
（これも技術質問と全く同じ【厳守フォーマット】を用いて、Q1〜Q2の深掘り解説と、最低5問の一問一答ドリルを作成）

## 📈 面接官を唸らせる{position_name}の「逆質問」戦略
面接の最後に必ず聞かれる「何か質問はありますか？」に対し、面接官を唸らせるキラー逆質問を**5つ**提案してください。
**【厳守フォーマット】逆質問のリストは、見出しタグ（#や###）を絶対に使用せず、以下のMarkdownの番号付きリスト（1. 2. 3.）をそのままコピーして記述してください。**

1. **[逆質問のキラーフレーズを具体的に入力]**
   - **💡 理由**: [なぜこの質問が面接官に刺さるのか、意図を記述]
2. **[逆質問のキラーフレーズを具体的に入力]**
   - **💡 理由**: [なぜこの質問が面接官に刺さるのか、意図を記述]
3. **[逆質問のキラーフレーズを具体的に入力]**
   - **💡 理由**: [なぜこの質問が面接官に刺さるのか、意図を記述]
4. **[逆質問のキラーフレーズを具体的に入力]**
   - **💡 理由**: [なぜこの質問が面接官に刺さるのか、意図を記述]
5. **[逆質問のキラーフレーズを具体的に入力]**
   - **💡 理由**: [なぜこの質問が面接官に刺さるのか、意図を記述]

## 結び：{position_name}面接を突破する極意
この記事の締めくくりとして、面接に臨む候補者に向けて、単なるスキルテストではない「面接の本質」と、自信を持って挑むための熱いエール（応援メッセージ）を簡潔に記述してください。
**【厳守】必ず `## 結び：{position_name}面接を突破する極意` というMarkdownのH2見出し（##）をつけて出力してください。**

---
【出力条件（厳守事項）】
- 前置き、挨拶等は一切不要。MarkdownのH1タグ `# [完全ガイド] {position_name}: {title_from_frontmatter}` から直接出力を開始すること。
- **一問一答ドリルにおいて、QとAは絶対に同じ行に繋げて書かないこと。必ずAの前に改行とインデント（箇条書き）を入れること。**
- **逆質問のリストや文末の締めくくりにおいて、指定した以外の見出しタグ（# や ###）を勝手に作成しないこと。**
- 途中で出力を中断せず、最後まで完全な状態で出力しきること。
"""

def generate_frontmatter(position_name):
    try:
        response = model.generate_content(
            FRONTMATTER_PROMPT.format(position_name=position_name),
            generation_config=genai.types.GenerationConfig(temperature=0.4)
        )
        json_match = re.search(r'(\{.*\})', response.text, re.DOTALL)
        if not json_match: return None
        return json.loads(json_match.group(0).strip())
    except Exception as e:
        print(f"[{position_name}] Frontmatter Error: {e}")
        return None

def generate_body(position_name, frontmatter_data):
    title = frontmatter_data.get('title', "詳細ガイド")
    try:
        response = model.generate_content(
            BODY_PROMPT.format(position_name=position_name, title_from_frontmatter=title),
            generation_config=genai.types.GenerationConfig(
                temperature=0.6,
                max_output_tokens=8192
            )
        )
        return response.text
    except Exception as e:
        print(f"[{position_name}] Body Error: {e}")
        return None

def process_single_position(position):
    """개별 직무에 대한 생성 작업을 수행하는 워커 함수"""
    print(f"⏳ 開始: {position}")
    
    frontmatter = generate_frontmatter(position)
    if not frontmatter:
        print(f"❌ 失敗 (Frontmatter): {position}")
        return False
        
    slug = frontmatter.get('slug', position.lower().replace(' ', '_'))
    output_filepath = os.path.join(OUTPUT_DIR, f"{slug}.md")

    body = generate_body(position, frontmatter)
    if not body:
        print(f"❌ 失敗 (本文): {position}")
        return False

    frontmatter_str = f"---json\n{json.dumps(frontmatter, ensure_ascii=False, indent=2)}\n---\n"
    
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter_str + body)
        print(f"✅ 完了: {position}")
        logging.info(output_filepath)
        return True
    except IOError as e:
        print(f"❌ 失敗 (保存エラー): {position} - {e}")
        return False

def main():
    if not os.path.exists(CSV_FILE):
        print(f"エラー: CSVファイル '{CSV_FILE}' が見つかりません。")
        return

    df = pd.read_csv(CSV_FILE)
    positions = df['position_name'].tolist()
    
    # 생성되지 않은 파일 목록 필터링
    positions_to_generate = []
    for pos in positions:
        slug = pos.replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '').replace(',', '').replace('"', '').lower()
        filepath = os.path.join(OUTPUT_DIR, f"{slug}.md")
        if not os.path.exists(filepath):
            positions_to_generate.append(pos)
    
    # 🎯 [핵심 변경사항] 남은 파일 개수와 설정한 최대 건수(MAX_TO_GENERATE) 중 작은 값만큼만 자르기
    target_positions = positions_to_generate[:MAX_TO_GENERATE]
    
    if not target_positions:
        print("🎉 すべてのファイルが生成済みです。")
        return

    print(f"🚀 超高速生成を開始します。ターゲット: {len(target_positions)}件 (同時実行: {MAX_WORKERS}件)")
    
    success_count = 0
    
    # ThreadPoolExecutor를 사용한 병렬 처리
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(process_single_position, target_positions)
        
        for result in results:
            if result:
                success_count += 1

    print(f"\n🎉 すべてのプロセスが完了しました。{success_count}件のファイルが新しく作成されました。")
    if len(positions_to_generate) > MAX_TO_GENERATE:
        remaining = len(positions_to_generate) - MAX_TO_GENERATE
        print(f"📌 残りの生成待ちジョブ数: {remaining}件 (再度スクリプトを実行してください)")

if __name__ == "__main__":
    main()