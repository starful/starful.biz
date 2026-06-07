import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from slug_utils import normalize_slug
CONTENTS_DIR = os.path.join(BASE_DIR, "app", "contents")
IMG_DIR = os.path.join(BASE_DIR, "app", "static", "img")

# 📂 기준이 되는 기본 이미지 (default.png 우선, legacy default.jpg fallback)
DEFAULT_CANDIDATES = ("default.png", "default.jpg")


def _default_source_path() -> str | None:
    for name in DEFAULT_CANDIDATES:
        path = os.path.join(IMG_DIR, name)
        if os.path.exists(path):
            return path
    return None

def generate_images_by_copy():
    """
    app/contents 폴더의 마크다운 파일을 스캔하여 
    이미지가 없는 항목에 대해 default.jpg를 복사하여 생성합니다.
    """
    
    # 1. 소스 이미지 존재 확인
    source_path = _default_source_path()
    if not source_path:
        print(f"❌ 기본 이미지 파일을 찾을 수 없습니다: {IMG_DIR}/default.png (또는 default.jpg)")
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
        slug = normalize_slug(filename.replace(".md", ""))
        
        # 생성될 이미지 경로 (기존 시스템과의 호환성을 위해 .png로 저장)
        target_path = os.path.join(IMG_DIR, f"{slug}.png")

        # 4. 이미 이미지가 존재하는지 확인
        if os.path.exists(target_path):
            skip_count += 1
            continue

        # 5. 이미지 복사 실행
        try:
            # copy2는 메타데이터(수정 시간 등)를 보존하며 파일을 복사합니다.
            shutil.copy2(source_path, target_path)
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