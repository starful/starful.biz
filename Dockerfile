# 1. 파이썬 3.11 환경
FROM python:3.11-slim

# 2. 작업 디렉토리 생성
WORKDIR /code

# 3. 환경 변수 설정
ENV PYTHONUNBUFFERED=1

# 4. 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 복사
COPY . .

# 6. [중요] 빌드 시점에 데이터 통합 스크립트 실행 (OKOnsen 스타일)
# 이 과정에서 app/static/json/job_data.json과 sitemap.xml이 자동 생성됩니다.
RUN python scripts/build_data.py

# 7. 포트 설정 및 실행 (app 패키지의 app 객체 실행)
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]