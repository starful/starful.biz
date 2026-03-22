# scripts/resize_images.py
import os
import shutil
try:
    from PIL import Image
except ImportError:
    print("❌ Pillow 라이브러리가 설치되어 있지 않습니다. 'pip install Pillow'를 실행해주세요.")
    exit(1)

# --- 경로 설정 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE_DIR, "app", "static", "img")
BACKUP_DIR = os.path.join(BASE_DIR, "app", "static", "img_backup")

# --- 최적화 설정 ---
MAX_WIDTH = 1200   # 최대 가로 길이 (픽셀)
MAX_HEIGHT = 1200  # 최대 세로 길이 (픽셀)

def resize_images():
    if not os.path.exists(IMG_DIR):
        print(f"❌ 이미지 디렉토리를 찾을 수 없습니다: {IMG_DIR}")
        return

    # 백업 폴더 생성
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"📁 백업 디렉토리 생성: {BACKUP_DIR}")

    # 변환 대상 확장자들 (webp, jpg, jpeg 등을 모두 읽어옴)
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(valid_extensions)]

    if not files:
        print("📭 처리할 이미지 파일이 없습니다.")
        return

    print(f"🚀 {len(files)}개의 이미지 리사이징 및 PNG 강제 변환을 시작합니다...")

    total_saved_space = 0

    for filename in files:
        filepath = os.path.join(IMG_DIR, filename)
        backup_filepath = os.path.join(BACKUP_DIR, filename)
        
        # 파일명(확장자 제외) 추출
        name_only, ext = os.path.splitext(filename)
        # 새로 저장될 PNG 파일 경로 (기존 확장자가 뭐든 무조건 .png로 저장)
        new_png_filepath = os.path.join(IMG_DIR, f"{name_only}.png")

        # 원본 백업 (이미 백업된 파일이 없으면 복사)
        if not os.path.exists(backup_filepath):
            shutil.copy2(filepath, backup_filepath)

        original_size = os.path.getsize(filepath)

        try:
            with Image.open(filepath) as img:
                # 1. 리사이징 (비율을 유지하면서 MAX_WIDTH, MAX_HEIGHT 안에 맞춤)
                img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
                
                # 2. 투명도(Alpha) 채널이 없는 이미지를 PNG로 변환할 때 색상 모드 변환 방지
                # 만약 CMYK 등 웹에 부적합한 포맷이면 RGB/RGBA로 강제 변환
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGBA')

                # 3. 무조건 PNG 포맷으로 저장 (최적화 옵션 활성화)
                img.save(new_png_filepath, format='PNG', optimize=True)

            new_size = os.path.getsize(new_png_filepath)
            diff = original_size - new_size
            
            # 원본이 PNG가 아니었다면, 원본 파일(JPG 등) 삭제
            if ext.lower() != '.png':
                os.remove(filepath)
                print(f"🔄 {filename} -> {name_only}.png 로 변환 완료!")
            
            if diff > 0:
                total_saved_space += diff
                print(f"✅ {name_only}.png: {original_size / 1024:.1f}KB -> {new_size / 1024:.1f}KB ({(diff/original_size)*100:.1f}% 감소)")
            else:
                # 용량이 늘어난 경우 (JPG -> PNG 변환 시 종종 발생) 백업 복구 안함.
                # (웹사이트 코드가 .png를 요구하므로 무조건 변환 유지)
                print(f"⚠️ {name_only}.png: 최적화 완료 (PNG 변환으로 용량 소폭 증가/유지됨)")

        except Exception as e:
            print(f"❌ {filename} 처리 중 오류 발생: {e}")

    saved_mb = total_saved_space / (1024 * 1024)
    print(f"\n🎉 작업 완료! (총 {saved_mb:.2f}MB의 용량 절약 및 PNG 통일 완료)")

if __name__ == "__main__":
    resize_images()