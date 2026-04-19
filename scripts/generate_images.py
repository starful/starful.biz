import os
import shutil

# --- 경로 설정 ---
# 스크립트 위치 기준으로 프로젝트 루트 경로를 계산합니다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENTS_DIR = os.path.join(BASE_DIR, "app", "contents")
IMG_DIR = os.path.join(BASE_DIR, "app", "static", "img")

# 📂 기준이 되는 기본 이미지 파일명
# 이 파일이 app/static/img/ 폴더 안에 실제로 존재해야 합니다.
DEFAULT_IMAGE_NAME = "default.jpg"
SOURCE_PATH = os.path.join(IMG_DIR, DEFAULT_IMAGE_NAME)

def generate_images_by_copy():
    """
    app/contents 폴더의 마크다운 파일을 스캔하여 
    이미지가 없는 항목에 대해 default.jpg를 복사하여 생성합니다.
    """
    
    # 1. 소스 이미지 존재 확인
    if not os.path.exists(SOURCE_PATH):
        print(f"❌ 기본 이미지 파일을 찾을 수 없습니다: {SOURCE_PATH}")
        print(f"💡 {IMG_DIR} 폴더 안에 {DEFAULT_IMAGE_NAME} 파일을 먼저 준비해주세요.")
        return

    # 2. 콘텐츠 디렉토리 존재 확인
    if not os.path.exists(CONTENTS_DIR):
        print(f"❌ 콘텐츠 디렉토리가 없습니다: {CONTENTS_DIR}")
        return

    # 이미지 저장 폴더가 없으면 생성
    os.makedirs(IMG_DIR, exist_ok=True)

    # 3. 마크다운 파일 목록 가져오기
    md_files = [f for f in os.listdir(CONTENTS_DIR) if f.endswith(".md")]
    print(f"📂 총 {len(md_files)}개의 콘텐츠 파일을 스캔합니다.")

    copy_count = 0
    skip_count = 0

    for filename in md_files:
        # 파일명에서 확장자 제거하여 slug 추출 (예: service_planner)
        slug = filename.replace(".md", "")
        
        # 생성될 이미지 경로 (기존 시스템과의 호환성을 위해 .png로 저장)
        target_path = os.path.join(IMG_DIR, f"{slug}.png")

        # 4. 이미 이미지가 존재하는지 확인
        if os.path.exists(target_path):
            skip_count += 1
            continue

        # 5. 이미지 복사 실행
        try:
            # copy2는 메타데이터(수정 시간 등)를 보존하며 파일을 복사합니다.
            shutil.copy2(SOURCE_PATH, target_path)
            copy_count += 1
            print(f"✅ 생성 완료 ({copy_count}): {slug}.png")
        except Exception as e:
            print(f"❌ {slug} 복사 중 오류 발생: {e}")

    # 6. 결과 보고
    print("\n" + "="*40)
    print(f"✨ 작업이 완료되었습니다.")
    print(f"   - 새로 생성됨: {copy_count}개")
    print(f"   - 이미 존재함: {skip_count}개")
    print("="*40)

if __name__ == "__main__":
    generate_images_by_copy()