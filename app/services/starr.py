"""STARR interview feedback and shokumu bullet generation."""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from typing import List

from fastapi import HTTPException, Request
from firebase_admin import firestore
from pydantic import BaseModel

from app.config import FIRESTORE_STARR_FEEDBACK_LOGS, FIRESTORE_STARR_USAGE_LIMITS
from app.utils.http import get_client_ip

STARR_DAILY_LIMIT = 3


class StarrFeedback(BaseModel):
    score: int
    summary: str
    s_feedback: str
    t_feedback: str
    a_feedback: str
    r_feedback: str
    reflection_feedback: str
    improved_answer: str


class StarrRequest(BaseModel):
    s: str
    t: str
    a: str
    r: str
    reflection: str
    job_title: str


class ShokumuBulletsResponse(BaseModel):
    bullets: List[str]
    job_title: str


def pydantic_to_dict(model: BaseModel) -> dict:
    dump = getattr(model, "model_dump", None)
    if callable(dump):
        return dump()
    return model.dict()


def clip_shokumu_line(text: str, max_len: int = 130) -> str:
    t = unicodedata.normalize("NFKC", (text or "").strip())
    t = re.sub(r"[\r\n]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    if not t:
        return ""
    if len(t) > max_len:
        return t[: max_len - 1] + "…"
    return t


def build_shokumu_bullets(starr: StarrRequest) -> List[str]:
    """職務経歴書向け箇条書き4行（テンプレート・パターン3種＋学び）。"""
    job = clip_shokumu_line(starr.job_title, 70) or "職務"
    s = clip_shokumu_line(starr.s, 150)
    t = clip_shokumu_line(starr.t, 120)
    a = clip_shokumu_line(starr.a, 150)
    r = clip_shokumu_line(starr.r, 120)
    ref = clip_shokumu_line(starr.reflection, 120)
    task_phrase = t if t else "プロジェクト・事業上の課題"
    res_phrase = r if r else "業務・サービス上の改善につながる成果"
    refl_phrase = ref if ref else "再現性のある改善サイクルづくり"

    return [
        f"「{s}において、{task_phrase}に対し、{a}を実施し、{res_phrase}。」",
        f"「{job}として、課題設定から改善施策の実行までを担当。特に{a}を中心に推進。」",
        f"「関係者と連携し、進捗管理とリスク対応を含めて推進し、{res_phrase}。」",
        f"「本経験から{refl_phrase}について学び、以降の業務に反映。」",
    ]


def build_starr_prompt(starr_data: StarrRequest) -> str:
    return f"""
You are a senior IT interview coach.
Evaluate the candidate's STARR response for the job title: {starr_data.job_title}.

Candidate input:
- Situation: {starr_data.s}
- Task: {starr_data.t}
- Action: {starr_data.a}
- Result: {starr_data.r}
- Reflection: {starr_data.reflection}

Return ONLY valid JSON (no markdown, no extra text) using this exact schema:
{{
  "score": <integer 0-100>,
  "summary": "<short overall feedback>",
  "s_feedback": "<feedback for Situation>",
  "t_feedback": "<feedback for Task>",
  "a_feedback": "<feedback for Action>",
  "r_feedback": "<feedback for Result>",
  "reflection_feedback": "<feedback for Reflection>",
  "improved_answer": "<a polished improved STARR answer in Japanese>"
}}

Scoring rules:
- Prioritize clarity, impact, and measurable outcomes.
- Give practical, interview-ready feedback.
"""


def parse_gemini_starr_response(raw_text: str) -> StarrFeedback:
    if not raw_text:
        raise ValueError("Empty AI response")
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    parsed = json.loads(cleaned)
    feedback = StarrFeedback(**parsed)
    feedback.score = max(0, min(100, feedback.score))
    return feedback


def check_usage_limit(db, request: Request) -> tuple[str, str, int]:
    """Return (client_ip, usage_doc_id, current_count). Raises 429 if over limit."""
    client_ip = get_client_ip(request)
    safe_ip = client_ip.replace(".", "_").replace(":", "_")
    today = date.today().isoformat()
    usage_doc_id = f"{safe_ip}_{today}"
    count = 0

    if db:
        try:
            doc = db.collection(FIRESTORE_STARR_USAGE_LIMITS).document(usage_doc_id).get()
            if doc.exists:
                count = int(doc.to_dict().get("count", 0))
            if count >= STARR_DAILY_LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail="本日の利用制限（3回）に達しました。明日またお試しください。",
                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ Firestore {FIRESTORE_STARR_USAGE_LIMITS} read error: {e}")

    return client_ip, usage_doc_id, count


def log_starr_feedback(
    db,
    client_ip: str,
    usage_doc_id: str,
    count: int,
    starr_data: StarrRequest,
    feedback: StarrFeedback,
) -> None:
    if not db:
        return
    try:
        db.collection(FIRESTORE_STARR_FEEDBACK_LOGS).add(
            {
                "ip": client_ip,
                "job_title": starr_data.job_title,
                "user_input": pydantic_to_dict(starr_data),
                "ai_output": pydantic_to_dict(feedback),
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )
        db.collection(FIRESTORE_STARR_USAGE_LIMITS).document(usage_doc_id).set(
            {
                "count": count + 1,
                "last_access": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
    except Exception as e:
        print(
            f"⚠️ Firestore {FIRESTORE_STARR_FEEDBACK_LOGS} / "
            f"{FIRESTORE_STARR_USAGE_LIMITS} write error: {e}"
        )
