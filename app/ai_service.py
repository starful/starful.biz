import os
from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# 클라이언트 초기화 (API 키 자동 로드)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# AI가 응답할 JSON 구조 정의 (매우 중요: 에러 방지)
class StarrFeedback(BaseModel):
    score: int
    summary: str
    s_feedback: str
    t_feedback: str
    a_feedback: str
    r_feedback: str
    reflection_feedback: str
    best_practice: str

def get_starr_feedback(s, t, a, r, reflection, job_title):
    prompt = f"""
    당신은 IT 전문 면접관입니다. '{job_title}' 직무 지원자의 STARR 방식 답변을 채점하세요.
    
    [답변 내용]
    - 상황(S): {s}
    - 과제(T): {t}
    - 행동(A): {a}
    - 결과(R): {r}
    - 성찰(Reflection): {reflection}
    
    [채점 가이드라인]
    1. 각 항목이 구체적이고 논리적인가? (수치적 성과 우대)
    2. 점수는 100점 만점으로 계산.
    3. 'best_practice' 항목에는 이 답변을 훨씬 매끄럽고 설득력 있게 다듬은 모범 답안을 작성.
    """

    # Gemini 2.0 Flash 호출
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": StarrFeedback,
        }
    )
    return response.parsed