#!/bin/bash
# 🌟 Starful Career Grid 통합 자동 배포 파이프라인 (Safe Sync & AI Generation)
# 실행: ./deploy.sh

set -e

# --- 색상 설정 ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# --- 경로 및 설정 (본인 환경에 맞게 자동 감지) ---
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMMIT_MSG="update: auto-generated career guides, images & data $(date '+%Y-%m-%d %H:%M') (Admin Sync)"
BUCKET_URL="gs://starful-biz-assets" 
IMAGES_DIR="app/static/img"
CONTENT_DIR="app/contents"

print_step() { echo ""; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
print_err()  { echo -e "${RED}  ❌ $1${NC}"; }
print_info() { echo -e "  ℹ️  $1"; }

clear
echo ""
echo -e "${BOLD}${CYAN}  🌟 Starful 통합 자동 배포 파이프라인${NC}"
echo -e "  $(date '+%Y년 %m월 %d일 %H:%M:%S') 시작"
echo ""
START_TIME=$SECONDS

# ── STEP 0: 환경 체크 ──────────────────────
print_step "STEP 0 / 8  |  환경 체크"
cd "$PROJECT_ROOT"

[ ! -f ".env" ] && { print_err ".env 파일이 없습니다."; exit 1; }
print_ok ".env 확인"

command -v gsutil &>/dev/null || { print_err "gsutil이 설치되지 않았습니다."; exit 1; }
command -v gcloud &>/dev/null || { print_err "gcloud가 설치되지 않았습니다."; exit 1; }
print_ok "Cloud SDK 확인 완료"

# ── STEP 1: 클라우드 이미지 동기화 (기존 이미지 보호) ──
print_step "STEP 1 / 8  |  GCS 최신 이미지 가져오기 (Safe Sync)"
mkdir -p "$IMAGES_DIR"
print_info "클라우드($BUCKET_URL) -> 로컬($IMAGES_DIR) 동기화..."
# GCS에 있는 이미지를 먼저 가져와서 로컬에 누락된 이미지가 없도록 합니다.
gsutil -m rsync -r "$BUCKET_URL" "$IMAGES_DIR"
print_ok "동기화 완료 (기존 이미지 보호됨)"

# ── STEP 2: 커리어 가이드 생성 (Gemini) ──────────
print_step "STEP 2 / 8  |  커리어 가이드 생성 (AI)"
BEFORE_COUNT=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
print_info "현재 가이드 개수: ${BEFORE_COUNT}개"

python3 scripts/generate_md_guides.py

AFTER_COUNT=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
NEW_COUNT=$(( AFTER_COUNT - BEFORE_COUNT ))
print_ok "가이드 생성 완료 (신규: ${NEW_COUNT}개)"

# ── STEP 3: 누락된 AI 이미지 생성 (Imagen 4.0) ──
print_step "STEP 3 / 8  |  누락된 이미지 자동 생성"
# STEP 2에서 새로 생긴 가이드에 대한 이미지를 생성합니다. (imagen-4.0-fast-generate-001 사용)
python3 scripts/generate_images.py
print_ok "이미지 생성 프로세스 완료"

# ── STEP 4: 이미지 리사이징 및 최적화 ────────────
print_step "STEP 4 / 8  |  이미지 최적화 (Resizing & PNG)"
python3 scripts/resize_images.py
print_ok "이미지 최적화 완료"

# ── STEP 5: 데이터 빌드 (job_data.json) ──────────
print_step "STEP 5 / 8  |  데이터 인덱스 빌드"
python3 scripts/build_data.py
print_ok "job_data.json 및 sitemap.xml 갱신 완료"

# ── STEP 6: GitHub 업데이트 ────────────────────
print_step "STEP 6 / 8  |  GitHub Push (백업)"
GIT_STATUS=$(git status --porcelain)
if [ -z "$GIT_STATUS" ]; then
    print_warn "GitHub 변경 사항 없음"
else
    git add .
    git commit -m "$COMMIT_MSG"
    git push origin main
    print_ok "GitHub 업데이트 완료"
fi

# ── STEP 7: GCS 이미지 최종 동기화 (업로드) ──────
print_step "STEP 7 / 8  |  GCS 자산 최종 업로드"
print_info "로컬 -> 클라우드($BUCKET_URL) 업로드 중..."
# 새로 생성되고 최적화된 이미지들을 GCS 버킷에 최종 저장합니다.
gsutil -m rsync -r "$IMAGES_DIR" "$BUCKET_URL"
print_ok "GCS 업로드 완료"

# ── STEP 8: 배포 (Cloud Run) ──────────────────
print_step "STEP 8 / 8  |  Cloud Run 최종 배포"
print_info "Cloud Build & Deploy 시작..."
gcloud builds submit --config cloudbuild.yaml
print_ok "사이트 배포 완료!"

# ── 최종 요약 ───────────────────────────────
print_step "배포 완료 요약"
ELAPSED=$(( SECONDS - START_TIME ))
echo ""
echo -e "${BOLD}${GREEN}  🎉 Starful 프로젝트가 성공적으로 라이브에 적용되었습니다!${NC}"
echo ""
echo -e "  ⏱️  총 소요 시간 : $(( ELAPSED / 60 ))분 $(( ELAPSED % 60 ))초"
echo -e "  📝 가이드 현황   : 총 ${AFTER_COUNT}개 (신규 ${NEW_COUNT}개)"
echo -e "  🖼️  이미지 저장소 : ${BUCKET_URL}"
echo -e "  🌐 서비스 주소   : https://starful.biz"
echo ""

# Mac 알림 (지원되는 경우)
osascript -e 'display notification "Starful 배포가 완료되었습니다!" with title "Deploy Success"' 2>/dev/null || true
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""