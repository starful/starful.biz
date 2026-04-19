import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 환경 변수 로드
load_dotenv()

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENTS_DIR = os.path.join(BASE_DIR, "app", "contents")
IMG_DIR = os.path.join(BASE_DIR, "app", "static", "img")

# 클라이언트 설정 (Gemini API 키 사용)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 🎨 사용자가 제공한 프롬프트 템플릿
PROMPT_TEMPLATE = """
An isometric 3D render representing the workspace and core responsibilities of a [{job_title}], 
featuring abstract stylized elements, tools, and data flows related to the profession. 
Luxurious Apple-style technical aesthetic, high-end product design, minimalist workspace. 
Beautiful combination of smooth matte clay and translucent frosted glass textures. 
Soft pastel colors featuring mint green, baby blue, soft lavender, and warm white. 
Clean background, soft bright studio lighting, tilt-shift effect, highly detailed, 8k resolution, 
octane render, photorealistic
"""

def generate_images():
    if not os.path.exists(CONTENTS_DIR):
        print("❌ 콘텐츠 디렉토리가 없습니다.")
        return

    os.makedirs(IMG_DIR, exist_ok=True)

    # 1. 마크다운 파일 목록 가져오기
    md_files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    print(f"📂 총 {len(md_files)}개의 마크다운 파일을 찾았습니다.")

    for filename in md_files:
        slug = filename.replace(".md", "")
        # 직업 이름은 파일명에서 언더바를 공백으로 바꾼 것 (예: service_planner -> Service Planner)
        job_title = slug.replace("_", " ").title()
        
        target_path = os.path.join(IMG_DIR, f"{slug}.png")

        # 2. 이미 이미지가 있는지 확인 (중복 생성 방지)
        if os.path.exists(target_path):
            # print(f"✅ 스킵: {slug}.png (이미 존재함)")
            continue

        print(f"🚀 이미지 생성 중: {job_title}...")

        try:
            # 3. Imagen 3를 사용하여 이미지 생성
            prompt = PROMPT_TEMPLATE.format(job_title=job_title)
            
            response = client.models.generate_image(
                model='imagen-4.0-fast-generate-001',
                prompt=prompt,
                config=types.GenerateImageConfig(
                    aspect_ratio="3:2",
                    output_mime_type="image/png"
                )
            )

            # 4. 이미지 저장
            # response.generated_images[0].image.save(target_path) # SDK 버전에 따라 다를 수 있음
            # 최신 SDK 방식:
            for i, generated_image in enumerate(response.generated_images):
                generated_image.image.save(target_path)
            
            print(f"✨ 저장 완료: {target_path}")
            
            # API 할당량 제한을 위해 잠시 대기 (Free Tier일 경우)
            time.sleep(2) 

        except Exception as e:
            print(f"❌ {job_title} 생성 실패: {e}")

if __name__ == "__main__":
    generate_images()