from __future__ import annotations

import json
from typing import Dict, List

import httpx

from ..utils.config import settings


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def is_ai_enabled() -> bool:
    return bool(settings.OPENAI_API_KEY.strip())


def _call_openai(prompt: str, max_output_tokens: int = 350) -> str:
    if not is_ai_enabled():
        raise RuntimeError("AI provider is not configured")

    payload = {
        "model": settings.OPENAI_MODEL,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=settings.OPENAI_TIMEOUT_SECONDS) as client:
        response = client.post(OPENAI_RESPONSES_URL, headers=headers, json=payload)
    response.raise_for_status()
    body = response.json()
    return (body.get("output_text") or "").strip()


def _safe_json_list(raw: str) -> List[str]:
    text = (raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        return []
    return []


def extract_jd_skills(jd_text: str) -> List[str]:
    prompt = (
        "Extract a JSON array of technical skills from the following job description. "
        "Return JSON list only with no explanation.\n\n"
        f"Job Description:\n{jd_text[:6000]}"
    )
    raw = _call_openai(prompt, max_output_tokens=300)
    return _safe_json_list(raw)


def build_candidate_summary(
    *,
    candidate_name: str,
    stage: str,
    score: float,
    tags: List[str],
    parsed_text: str,
    resume_context: str = "",
) -> Dict[str, object]:
    prompt = (
        "You are assisting a recruiter. Return compact JSON with keys: "
        "summary (string), strengths (array of strings), risks (array of strings). "
        f"Candidate: {candidate_name}\n"
        f"Stage: {stage}\n"
        f"Match score: {score}\n"
        f"Tags: {', '.join(tags) if tags else '(none)'}\n"
    )
    if resume_context:
        prompt += (
            "Relevant resume context:\n"
            f"{resume_context[:3000]}\n"
        )
    prompt += (
        "Resume text:\n"
        f"{parsed_text[:4000]}"
    )
    response = _call_openai(prompt)
    return {"raw": response}


def build_interview_questions(
    *,
    candidate_name: str,
    role_context: str,
    tags: List[str],
    parsed_text: str,
    resume_context: str = "",
) -> Dict[str, object]:
    prompt = (
        "You are assisting a recruiter. Return compact JSON with key 'questions' "
        "as an array of 5 to 8 interview questions tailored to the candidate.\n"
        f"Candidate: {candidate_name}\n"
        f"Role context: {role_context}\n"
        f"Tags: {', '.join(tags) if tags else '(none)'}\n"
    )
    if resume_context:
        prompt += (
            "Relevant resume context:\n"
            f"{resume_context[:3000]}\n"
        )
    prompt += (
        "Resume text:\n"
        f"{parsed_text[:4000]}"
    )
    response = _call_openai(prompt)
    return {"raw": response}


def generate_interview_questions_from_skills(candidate_skills: List[str]) -> Dict[str, object]:
    prompt = (
        "Generate exactly 5 technical interview questions for a candidate with these skills. "
        "Return plain numbered list only.\n\n"
        f"Skills: {', '.join(candidate_skills) if candidate_skills else '(none)'}"
    )
    response = _call_openai(prompt, max_output_tokens=350)
    return {"raw": response}
