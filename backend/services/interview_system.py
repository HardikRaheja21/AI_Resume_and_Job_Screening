from __future__ import annotations

from typing import Dict, List, Optional

from sqlmodel import Session

from . import ai_assistant
from . import answer_evaluator
from ..models import User


QUESTION_BANK = {
    "python": [
        "Explain the difference between a list and a tuple in Python.",
        "How would you debug a slow Python API endpoint in production?",
        "What are generators in Python, and when would you use them?",
    ],
    "fastapi": [
        "How does dependency injection work in FastAPI?",
        "How would you structure request validation and error handling in FastAPI?",
        "What steps would you take to secure a FastAPI service?",
    ],
    "sql": [
        "What is the difference between INNER JOIN and LEFT JOIN?",
        "How would you optimize a slow SQL query?",
        "How do indexes improve query performance, and when can they hurt?",
    ],
    "machine learning": [
        "How do you detect overfitting in a machine learning model?",
        "What is the bias-variance tradeoff?",
        "How would you evaluate a classification model beyond accuracy?",
    ],
    "docker": [
        "Why would you use multi-stage Docker builds?",
        "How do you reduce Docker image size for production?",
        "How do containers differ from virtual machines?",
    ],
    "default": [
        "Walk me through a project that best matches this role.",
        "How do you prioritize work when deadlines shift unexpectedly?",
        "Describe a difficult technical problem you solved and how you approached it.",
    ],
}


def _normalize(skills: List[str]) -> List[str]:
    return [skill.strip().lower() for skill in skills if skill and skill.strip()]


def generate_question_plan(
    *,
    candidate_name: str,
    skills: List[str],
    job_description: str,
    max_questions: int,
) -> List[Dict[str, object]]:
    normalized = _normalize(skills)
    ordered_topics = normalized[:]
    if not ordered_topics:
        ordered_topics = ["default"]
    while len(ordered_topics) < max_questions:
        ordered_topics.append("default")

    plan: List[Dict[str, object]] = []
    used_questions: set[str] = set()
    for idx in range(max_questions):
        topic = ordered_topics[idx] if idx < len(ordered_topics) else "default"
        question = None
        for candidate in QUESTION_BANK.get(topic, QUESTION_BANK["default"]):
            if candidate not in used_questions:
                question = candidate
                break
        if question is None:
            question = QUESTION_BANK["default"][idx % len(QUESTION_BANK["default"])]
        used_questions.add(question)
        expected_keywords = [topic] if topic != "default" else normalized[:2]
        plan.append(
            {
                "question_index": idx + 1,
                "topic": topic,
                "difficulty": min(3, 1 + (idx // 2)),
                "question": question,
                "expected_keywords": [kw for kw in expected_keywords if kw],
            }
        )

    if ai_assistant.is_ai_enabled():
        try:
            ai_result = ai_assistant.build_interview_questions(
                candidate_name=candidate_name,
                role_context=job_description[:300] or "General hiring",
                tags=skills[:5],
                parsed_text=job_description[:2000],
            )
            raw = str(ai_result.get("raw", "")).strip()
            ai_questions = [line.strip("0123456789). ").strip() for line in raw.splitlines() if line.strip()]
            for idx, question in enumerate(ai_questions[: len(plan)]):
                if question:
                    plan[idx]["question"] = question
        except Exception:
            pass

    return plan


def evaluate_answer(
    *,
    question: str,
    answer: str,
    expected_keywords: List[str],
    difficulty_level: int,
    input_type: str,
) -> Dict[str, object]:
    answer_text = (answer or "").strip()
    lowered = answer_text.lower()
    expected = [item.lower() for item in expected_keywords if item]
    matched = [item for item in expected if item in lowered]

    length_score = min(len(answer_text.split()) / 40.0, 1.0)
    keyword_score = (len(matched) / len(expected)) if expected else 0.5
    concept_markers = [
        "because",
        "tradeoff",
        "example",
        "performance",
        "scal",
        "optimiz",
        "security",
        "testing",
        "debug",
    ]
    concept_hits = sum(1 for marker in concept_markers if marker in lowered)
    concept_score = min(concept_hits / 4.0, 1.0)
    score = max(0.0, min(10.0, ((0.35 * keyword_score) + (0.25 * length_score) + (0.40 * concept_score)) * 10))

    if len(answer_text.split()) < 5:
        feedback = "Answer is too short. Add more detail and practical reasoning."
    elif score >= 8:
        feedback = "Strong answer with good technical depth."
    elif score >= 6:
        feedback = "Good answer, but it could use more depth or examples."
    elif score >= 4:
        feedback = "Partial answer. Include clearer concepts, keywords, and examples."
    else:
        feedback = "Weak answer. Revisit the core concept and answer with more structure."

    if input_type == "voice":
        feedback += " Voice transcript accepted successfully."

    if score >= 8:
        next_difficulty = min(3, difficulty_level + 1)
    elif score < 4:
        next_difficulty = max(1, difficulty_level - 1)
    else:
        next_difficulty = difficulty_level

    recommendation = "select" if score >= 8 else "hold" if score >= 5 else "reject"
    return {
        "score": round(score, 2),
        "feedback": feedback,
        "matched_keywords": matched,
        "next_difficulty": next_difficulty,
        "recommendation": recommendation,
        "question": question,
    }


def combine_final_scores(match_score: float, interview_score: float) -> Dict[str, object]:
    final_score = max(0.0, min(1.0, (0.6 * match_score) + (0.4 * interview_score)))
    if final_score >= 0.75:
        decision = "selected"
    elif final_score >= 0.5:
        decision = "hold"
    else:
        decision = "rejected"
    return {
        "final_score": round(final_score, 4),
        "decision": decision,
    }


def evaluate_answer_advanced(
    *,
    question: str,
    answer: str,
    expected_keywords: List[str],
    expected_concepts: Optional[List[str]] = None,
    difficulty_level: int = 1,
    input_type: str = "text",
    session: Optional[Session] = None,
    current_user: Optional[User] = None,
    resume_id: Optional[int] = None,
) -> Dict[str, object]:
    """
    Evaluate answer with semantic scoring when available, heuristic fallback.

    This is the recommended evaluation method for advanced interview assessment.
    """
    return answer_evaluator.evaluate_answer_semantic(
        question=question,
        answer=answer,
        expected_keywords=expected_keywords,
        expected_concepts=expected_concepts or expected_keywords,
        difficulty_level=difficulty_level,
        input_type=input_type,
        session=session,
        current_user=current_user,
        resume_id=resume_id,
        query=question,
    )
