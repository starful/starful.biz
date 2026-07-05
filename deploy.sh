#!/bin/bash
# Starful deployment helper — images on GCS, code on Cloud Run

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMMIT_MSG="update: auto-generated career guides, images & data $(date '+%Y-%m-%d %H:%M') (Admin Sync)"
BUCKET_URL="${BUCKET_URL:-gs://starful-biz-assets}"
STAGING_DIR="tmp/image-staging"
CONTENT_DIR="app/contents"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-starful-258005}"
MODE="full"
DO_GIT=false
DO_CLOUD_DEPLOY=false
NEW_COUNT=0

print_step() { echo ""; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
print_err()  { echo -e "${RED}  ❌ $1${NC}"; }

usage() {
    cat <<'EOF'
Usage: ./deploy.sh [MODE] [OPTIONS]

Modes (default: full)
  --full           Generate content + GCS image stubs + build job_data.json
  --content-only   Generate career guides + build_data only
  --images-only    generate_images + resize_images (upload to GCS)
  --deploy-only    Cloud Build deploy only (fast — no local images)

Options
  --with-git       Commit and push generated changes
  --with-deploy    Trigger Cloud Run deploy after selected mode
  --help           Show this help

Career PNGs live on GCS (gs://starful-biz-assets). okadmin uploads go
directly to the bucket — no Cloud Run redeploy needed for image changes.
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        print_err "Missing required command: $1"
        exit 1
    fi
}

check_env() {
    print_step "STEP 0  |  환경 체크"
    [ ! -f ".env" ] && { print_err ".env 파일이 없습니다."; exit 1; }
    print_ok ".env 확인"
}

generate_content() {
    print_step "STEP A  |  커리어 가이드 생성"
    local before_count=0
    [ -d "$CONTENT_DIR" ] && before_count=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
    python3 scripts/generate_md_guides.py
    local after_count
    after_count=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
    NEW_COUNT=$(( after_count - before_count ))
    print_ok "가이드 생성 완료 (신규 ${NEW_COUNT}개)"
}

process_images() {
    print_step "STEP B  |  GCS 이미지 (missing slug → default.png upload)"
    mkdir -p "$STAGING_DIR"
    python3 scripts/generate_images.py
    python3 scripts/resize_images.py
    print_ok "GCS 이미지 처리 완료"
}

build_data() {
    print_step "STEP C  |  데이터 인덱스 빌드"
    python3 scripts/build_data.py
    print_ok "job_data.json 갱신 완료"
}

git_push_changes() {
    print_step "STEP D  |  GitHub Push"
    git add .
    if ! git diff-index --quiet HEAD --; then
        git commit -m "$COMMIT_MSG"
        git push origin main
        print_ok "GitHub push 완료"
    else
        print_warn "GitHub 변경 사항 없음"
    fi
}

deploy_cloud_run() {
    print_step "STEP E  |  Cloud Build 배포 (코드만 — 경량)"
    gcloud builds submit --config cloudbuild.yaml --project "$GCP_PROJECT_ID"
    print_ok "사이트 배포 완료"
}

for arg in "$@"; do
    case "$arg" in
        --full) MODE="full" ;;
        --content-only) MODE="content-only" ;;
        --images-only) MODE="images-only" ;;
        --deploy-only) MODE="deploy-only" ;;
        --with-git) DO_GIT=true ;;
        --with-deploy) DO_CLOUD_DEPLOY=true ;;
        --help|-h) usage; exit 0 ;;
        *)
            print_err "Unknown argument: $arg"
            usage
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"
check_env
require_cmd python3
require_cmd gcloud

case "$MODE" in
    full)
        require_cmd gsutil
        generate_content
        process_images
        build_data
        ;;
    content-only)
        generate_content
        build_data
        ;;
    images-only)
        require_cmd gsutil
        process_images
        ;;
    deploy-only)
        DO_CLOUD_DEPLOY=true
        ;;
esac

if [ "$DO_GIT" = true ]; then
    require_cmd git
    git_push_changes
fi

if [ "$DO_CLOUD_DEPLOY" = true ]; then
    deploy_cloud_run
fi

echo -e "${GREEN}완료: ${MODE}${NC}"
