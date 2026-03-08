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
QUALITY = 82       # 이미지 품질 (1~100, 보통 80~85가 용량 대비 화질이 좋음)

def resize_images():
    if not os.path.exists(IMG_DIR):
        print(f"❌ 이미지 디렉토리를 찾을 수 없습니다: {IMG_DIR}")
        return

    # 백업 폴더 생성 (.gitignore에 추가하는 것을 권장)
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"📁 백업 디렉토리 생성: {BACKUP_DIR}")

    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    files =[f for f in os.listdir(IMG_DIR) if f.lower().endswith(valid_extensions)]

    if not files:
        print("📭 처리할 이미지 ファイルが 없습니다.")
        return

    print(f"🚀 {len(files)}개의 이미지 최적화 및 리사이징 작업을 시작します...")

    total_saved_space = 0

    for filename in files:
        filepath = os.path.join(IMG_DIR, filename)
        backup_filepath = os.path.join(BACKUP_DIR, filename)

        # 원본 백업 (이미 백업된 파일이 없으면 복사)
        if not os.path.exists(backup_filepath):
            shutil.copy2(filepath, backup_filepath)

        original_size = os.path.getsize(filepath)

        try:
            with Image.open(filepath) as img:
                fmt = img.format if img.format else 'JPEG'
                
                # 리사이징 (비율을 유지하면서 MAX_WIDTH, MAX_HEIGHT 안에 맞춤)
                img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
                
                # PNG 등을 JPEG로 변환 저장할 경우를 대비하여 투명도(Alpha) 채널 처리
                if fmt in ('JPEG', 'JPG') and img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # 덮어쓰기 저장 (최적화 옵션 활성화)
                # PNG는 quality 파라미터가 크게 영향이 없지만 optimize=True가 용량을 줄여줍니다.
                if fmt == 'PNG':
                    img.save(filepath, format=fmt, optimize=True)
                else:
                    img.save(filepath, format=fmt, optimize=True, quality=QUALITY)

            new_size = os.path.getsize(filepath)
            diff = original_size - new_size
            
            if diff > 0:
                total_saved_space += diff
                print(f"✅ {filename}: {original_size / 1024:.1f}KB -> {new_size / 1024:.1f}KB ({(diff/original_size)*100:.1f}% 감소)")
            else:
                # 용량이 오히려 늘어났거나 변동이 없는 경우 원본 복구
                shutil.copy2(backup_filepath, filepath)
                print(f"⏩ {filename}: 이미 최적화되어 있어 건너뜁니다.")

        except Exception as e:
            print(f"❌ {filename} 처리 중 오류 발생: {e}")

    saved_mb = total_saved_space / (1024 * 1024)
    print(f"\n🎉 작업 완료! 총 {saved_mb:.2f}MB의 용량을 절약했습니다.")

if __name__ == "__main__":
    resize_images()