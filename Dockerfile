# 1. 기본이 될 파이썬 환경을 선택합니다.
FROM python:3.11-slim

# 2. 컨테이너 안에서 작업할 폴더를 만듭니다.
WORKDIR /code

# 3. 환경변수를 설정하여 파이썬 로그가 바로 보이게 합니다.
ENV PYTHONUNBUFFERED=1

# --- [최적화 1] 라이브러리 설치 레이어를 분리하여 캐싱합니다 ---
# 4. requirements.txt 파일만 먼저 복사합니다.
COPY requirements.txt .

# 5. 라이브러리를 설치합니다. requirements.txt가 변경되지 않으면 이 단계는 캐시를 사용해 즉시 완료됩니다.
RUN pip install --no-cache-dir -r requirements.txt

# --- [최적화 2] 애플리케이션 소스 코드 복사 ---
# 6. 나머지 모든 소스 코드를 컨테이너 안으로 복사합니다.
COPY . .

# 7. 컨테이너가 시작될 때 실행할 명령어를 정의합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]