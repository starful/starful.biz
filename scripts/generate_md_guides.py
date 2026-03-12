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

# --- 본문(BODY) 프롬프트 ---
BODY_PROMPT = """
# 🎯 ポジション分析・ディープダイブプロンプト

あなたは**ITおよび技術職務の現役トップクラス・エキスパート兼、辛口だが愛情のあるキャリアコンサルタント**です。
今回は「{position_name}」という職種について、単なる辞書的な説明を脱却し、**「現場の泥臭いリアル」「未経験者が知るべき残酷な現実と希望」「プロフェッショナルとしての真の価値」**を、読者が引き込まれるような圧倒的な熱量で執筆してください。

【執筆の絶対ルール：SEO最適化と独自性】
1. **目標文字数**: **日本語で7,000字〜8,000字程度**の超特大ボリュームで執筆すること。AI特有の「薄っぺらい要約」は厳禁。各セクションで実際のプロジェクトにおける失敗談、チーム間の対立、深夜のトラブル対応など、**生々しいエピソード（架空の事例で可）を必ず交えて**文字数と内容の深さを担保してください。
2. 機械的に生成されたような「1. XXとは？ 2. 業務...」という箇条書きメインの構造は避け、**雑誌の特集記事のような読ませる文章**（見出しH2, H3を活用）を心がけてください。
3. はてなブログやZenn等でバズるような、視覚的要素（絵文字、太字、引用文 `> `）を積極的に活用してください。

---記事の構成ガイド（見出し名は指定通り、または更に魅力的に適宜変更すること）---

## 導入：{position_name}という職業の「光と影」
この職種が現代のIT業界でなぜこれほどまでに求められているのか。世間のキラキラしたイメージとは裏腹に、裏側ではどのような重圧や責任が伴うのかを、読者の心に刺さる言葉で語りかけてください。

## 💰 リアルな年収相場と、壁を越えるための「残酷な条件」
ただ年収を書くだけでなく、「なぜその年収で頭打ちになるのか」「シニアになるために乗り越えるべき壁は何か」を熱く解説してください。以下のMarkdownテーブル形式は必ず使用すること。
| キャリア段階 | 経験年数 | 推定年収 (万円) | 年収の壁を突破するための「リアルな必須条件」 |
| :--- | :--- | :--- | :--- |
| ジュニア | 1-3年 | [金額] | 言われたことをこなすだけでなく、[具体例]ができるか |
| ミドル | 3-7年 | [金額] | チームのボトルネックを特定し、[具体例]を主導できるか |
| シニア/リード | 7年以上 | [金額] | 経営層と技術の橋渡しを行い、[具体例]の責任を負えるか |

## ⏰ {position_name}の「生々しい1日」のスケジュール
出社から退勤までのタイムスケジュール（例：09:00〜19:00）を時系列で提示してください。
単なる「会議」「作業」ではなく、**「朝会で昨日のバグの原因を詰められる」「他部署からの無茶振り仕様変更にどう対応するか」「午後イチの集中タイムで発生した本番障害」**など、現場の空気が伝わるストーリー仕立てで詳細に記述してください。

## ⚖️ この仕事の「天国（やりがい）」と「地獄（きつい現実）」
読者が最も知りたいリアルな比較です。
- **【やりがい】**: 苦労が報われる瞬間、社会やユーザーに与えるインパクト。
- **【きつい部分・泥臭い現実】**: この職種を辞める人がよく挙げる理由、理不尽な板挟み、メンタルを削られる瞬間。
それぞれ3つずつ具体的なシチュエーションを挙げて、深くえぐり出すように解説してください。

## 🛠️ 現場で戦うための「ガチ」スキルマップと必須ツール
教科書通りのスキルではなく、**「実務で本当に差がつくスキル」**を解説してください。
以下の構成の【Markdownの表形式】を必ず使用すること。（※各セル内で絶対に改行を入れないこと）
| スキル・ツール名 | 現場での使われ方（「なぜ」必要なのか、具体的なシーン） |
| :--- | :--- |
| [具体例：Docker等] | 開発環境の差異による「私の環境では動きました」という不毛な争いを無くすため。 |
| [具体例：交渉力] | 無茶な納期要求に対し、技術的負債のリスクを説明しスコープを削るため。 |

## 🎤 激戦必至！{position_name}の「ガチ面接対策」と模範解答
実際の現場面接・技術面接で**「面接官が候補者の本質を見抜くために投げかける、意地悪だが重要な質問」**を5つ厳選してください。
各質問に対し、以下の形式で解説すること。
- **質問**: [具体的な質問内容]
- **面接官の意図**: [なぜこれを聞くのか、何を確認したいのか]
- **NGな回答例**: [落ちる候補者がやりがちな表面的な回答]
- **評価される模範解答の方向性**: [経験に基づいたSTAR法などを意識した回答の構成案]

## 💡 未経験・ジュニアからよくある質問（FAQ）
「プログラミングスクールを出ただけでなれますか？」「数学の知識はどこまで必要ですか？」など、初心者が抱きがちなリアルな疑問を5つ挙げ、それに対してコンサルタントとしての「本音（時には厳しい事実）」をQ&A形式で回答してください。

---
【出力条件（厳守事項）】
- 前置き、挨拶、「承知いたしました」等のAI的応答は一切不要。
- 必ずMarkdownのH1タグ `# [完全ガイド] {position_name}: {title_from_frontmatter}` から直接出力を開始すること。
- **途中で出力を中断せず、最後のFAQまで「必ず」完全な状態で出力しきること。**
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