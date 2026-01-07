# 1. 기본이 될 파이썬 환경을 선택합니다.
FROM python:3.11-slim

# 2. 컨테이너 안에서 작업할 폴더를 만듭니다.
WORKDIR /code

# 3. 환경변수를 설정하여 파이썬 로그가 바로 보이게 합니다.
ENV PYTHONUNBUFFERED=1

# 4. 필요한 파이썬 라이브러리를 먼저 설치합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 프로젝트의 모든 파일을 컨테이너 안으로 복사합니다.
COPY . .

# 6. 컨테이너가 시작될 때 실행할 명령어를 정의합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]