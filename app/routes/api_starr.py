"""STARR API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.dependencies import ai_client, db
from app.services.starr import (
    ShokumuBulletsResponse,
    StarrRequest,
    build_shokumu_bullets,
    build_starr_prompt,
    check_usage_limit,
    log_starr_feedback,
    parse_gemini_starr_response,
)

router = APIRouter()


@router.post("/analyze-starr")
async def analyze_starr(request: Request, starr_data: StarrRequest):
    if ai_client is None:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. Set GEMINI_API_KEY.",
        )

    client_ip, usage_doc_id, count = check_usage_limit(db, request)
    prompt = build_starr_prompt(starr_data)

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw_text = (response.text or "").strip()
        feedback = parse_gemini_starr_response(raw_text)
        log_starr_feedback(db, client_ip, usage_doc_id, count, starr_data, feedback)
        return feedback
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ STARR analyze error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze STARR response.",
        )


@router.post("/shokumu-bullets")
async def shokumu_bullets(starr_data: StarrRequest) -> ShokumuBulletsResponse:
    """Gemini なし。STARR＋職種から職務経歴書用箇条書き4行を生成。"""
    if not (starr_data.s or "").strip() or not (starr_data.a or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Situation(S) と Action(A) は必須です。",
        )
    if not (starr_data.job_title or "").strip():
        raise HTTPException(
            status_code=400,
            detail="職種・ポジションを選択または入力してください。",
        )
    bullets = build_shokumu_bullets(starr_data)
    return ShokumuBulletsResponse(
        bullets=bullets,
        job_title=starr_data.job_title.strip(),
    )
