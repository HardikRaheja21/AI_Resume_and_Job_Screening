from __future__ import annotations

import logging
import re
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlmodel import Session

from . import vector_service
from ..models import User
from ..services.embedding_service import encode_texts, get_model
from ..utils.config import settings

logger = logging.getLogger("resume_parser.answer_evaluator")


def _concept_markers() -> List[str]:
    return [
        "because",
        "tradeoff",
        "example",
        "performance",
        "scal",
        "optimiz",
        "security",
        "testing",
        "debug",
        "approach",
        "strategy",
        "implement",
        "design",
        "architecture",
    ]


def _heuristic_score(
    answer_text: str,
    expected_keywords: List[str],
    difficulty_level: int,
) -> Tuple[float, List[str], float, float, float]:
    lowered = answer_text.lower()
    expected_lowered = [item.lower() for item in expected_keywords if item]
    matched = [item for item in expected_keywords if item.lower() in lowered]

    length_score = min(len(answer_text.split()) / 20.0, 1.0)
    keyword_score = (len(matched) / len(expected_lowered)) if expected_lowered else 0.5
    concept_hits = sum(1 for marker in _concept_markers() if marker in lowered)
    concept_score = min(concept_hits / 4.0, 1.0)

    # Compute base and keyword bonus per new heuristic
    base = (0.35 * keyword_score) + (0.25 * length_score) + (0.40 * concept_score)
    keyword_bonus_coef = 0.65
    keyword_bonus = (
        keyword_bonus_coef * (len(matched) / max(1, len(expected_lowered))) if expected_lowered else 0.0
    )

    heuristic = max(0.0, min(10.0, (base + keyword_bonus) * 10.0))

    return heuristic, matched, keyword_score, length_score, concept_score


def _semantic_score(
    question: str,
    answer_text: str,
    expected_concepts: List[str],
) -> Tuple[float, float]:
    try:
        if settings.MATCHER_DISABLE_EMBEDDINGS:
            raise RuntimeError("Embeddings disabled")

        question_embedding = encode_texts([question], convert_to_numpy=True, normalize_embeddings=True)
        answer_embedding = encode_texts([answer_text], convert_to_numpy=True, normalize_embeddings=True)

        q_to_a_sim = float(np.dot(question_embedding[0], answer_embedding[0]))
        q_to_a_sim = max(0.0, min(1.0, (q_to_a_sim + 1.0) / 2.0))

        relevance_score = q_to_a_sim
        if expected_concepts:
            concept_embeddings = encode_texts(
                expected_concepts,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            similarities = np.dot(answer_embedding[0], concept_embeddings.T)
            avg_concept_sim = float(np.mean(similarities))
            relevance_score = max(0.0, min(1.0, (avg_concept_sim + 1.0) / 2.0))

        return q_to_a_sim * 10.0, relevance_score * 10.0
    except Exception as exc:
        logger.debug("semantic_scoring_failed", extra={"error": str(exc)})
        return 0.0, 0.0


def _retrieve_resume_chunks(
    *,
    session: Optional[Session],
    current_user: Optional[User],
    resume_id: Optional[int],
    query: str,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    if not session or not current_user or resume_id is None:
        return []
    try:
        return vector_service.retrieve_resume_chunks(
            session=session,
            current_user=current_user,
            resume_id=resume_id,
            query=query,
            limit=limit,
        )
    except Exception as exc:
        logger.debug("Resume retrieval failed: %s", exc)
        return []


def _extract_concept_candidates_from_chunks(
    chunks: List[Dict[str, Any]], max_concepts: int = 6
) -> List[str]:
    concepts: List[str] = []
    for chunk in chunks:
        content = str(chunk.get("content_snippet") or chunk.get("document", "") or "").strip()
        if content and content not in concepts:
            concepts.append(content)
        if len(concepts) >= max_concepts:
            break
    return concepts


def _derive_expected_concepts(
    question: str,
    expected_concepts: Optional[List[str]],
    resume_chunks: List[Dict[str, Any]],
    max_concepts: int = 8,
) -> List[str]:
    concepts: List[str] = []
    if expected_concepts:
        for item in expected_concepts:
            if item and item.strip():
                text = item.strip()
                if text not in concepts:
                    concepts.append(text)
    for content in _extract_concept_candidates_from_chunks(resume_chunks, max_concepts=max_concepts):
        if content not in concepts:
            concepts.append(content)
    if not concepts:
        parts = [part.strip() for part in re.split(r"[,:;\\-\\.?]", question) if part.strip()]
        for part in parts:
            if part not in concepts:
                concepts.append(part)
            if len(concepts) >= max_concepts:
                break
    return concepts[:max_concepts]


def _semantic_concept_alignment(
    answer_text: str,
    expected_concepts: List[str],
) -> Tuple[List[float], List[str], float]:
    if not expected_concepts:
        return [], [], 0.0
    try:
        if settings.MATCHER_DISABLE_EMBEDDINGS:
            raise RuntimeError("Embeddings disabled")

        answer_embedding = encode_texts([answer_text], convert_to_numpy=True, normalize_embeddings=True)[0]
        concept_embeddings = encode_texts(
            expected_concepts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        similarities = np.dot(answer_embedding, concept_embeddings.T)
        normalized = [max(0.0, min(1.0, (float(sim) + 1.0) / 2.0)) for sim in similarities.tolist()]
        coverage = float(sum(1 for sim in normalized if sim >= 0.55)) / len(normalized)
        missing = [concept for concept, sim in zip(expected_concepts, normalized) if sim < 0.55]
        return normalized, missing, coverage
    except Exception as exc:
        logger.debug("Semantic concept alignment failed: %s", exc)
        return [], expected_concepts, 0.0


def _build_structured_feedback(
    answer_text: str,
    score: float,
    heuristic: float,
    semantic_q_score: float,
    semantic_rel_score: float,
    matched_keywords: List[str],
    concept_coverage: float,
    missing_concepts: List[str],
    retrieval_used: bool,
    input_type: str,
) -> str:
    lines: List[str] = []
    if len(answer_text.split()) < 5:
        lines.append("Answer is too short. Add more detail and practical reasoning.")
    elif score >= 8:
        lines.append("Strong answer with good technical depth and relevance.")
    elif score >= 6:
        lines.append("Good answer with solid reasoning. Could use more examples or depth.")
    elif score >= 4:
        lines.append("Partial answer with some relevant concepts. Strengthen with clearer structure.")
    else:
        lines.append("Weak answer. Revisit core concepts and provide structured reasoning.")

    if matched_keywords:
        keywords_str = ", ".join(matched_keywords)
        lines.append(f"Key concepts identified: {keywords_str}.")

    if retrieval_used:
        lines.append("Evaluation used candidate-specific resume context to judge relevance.")

    if missing_concepts:
        missing = ", ".join(missing_concepts[:3])
        lines.append(f"Missing concepts: {missing}.")
    elif concept_coverage >= 0.7:
        lines.append("Concept coverage is strong and aligned with expectations.")
    elif concept_coverage >= 0.4:
        lines.append("Concept coverage is moderate. Expand on the remaining topics.")
    elif concept_coverage > 0:
        lines.append("Concept coverage is limited. Address the missing concepts more directly.")

    if semantic_rel_score >= 7:
        lines.append("Semantic understanding is well aligned with expected concepts.")
    elif semantic_rel_score >= 4:
        lines.append("Semantic understanding is partial. Add more concept depth.")
    elif semantic_rel_score > 0:
        lines.append("Semantic alignment is weak. Focus on core concepts.")

    if input_type == "voice":
        lines.append("Voice transcript processed successfully.")

    return " ".join(lines)


def _combine_scores(
    heuristic: float,
    semantic_q_score: float,
    semantic_rel_score: float,
    difficulty_level: int,
) -> float:
    weights = {
        1: {"heuristic": 0.8, "semantic": 0.2},
        2: {"heuristic": 0.7, "semantic": 0.3},
        3: {"heuristic": 0.6, "semantic": 0.4},
    }
    level = max(1, min(3, difficulty_level))
    w = weights.get(level, weights[1])

    semantic_avg = (semantic_q_score + semantic_rel_score) / 2.0
    combined = (w["heuristic"] * heuristic) + (w["semantic"] * semantic_avg)
    return max(0.0, min(10.0, combined))


def _next_difficulty(score: float, difficulty_level: int) -> int:
    if score >= 8:
        return min(3, difficulty_level + 1)
    elif score < 4:
        return max(1, difficulty_level - 1)
    else:
        return difficulty_level


def _recommendation_from_score(score: float) -> str:
    if score >= 8:
        return "select"
    elif score >= 5:
        return "hold"
    else:
        return "reject"


def _build_feedback(
    answer_text: str,
    score: float,
    heuristic: float,
    semantic_q_score: float,
    semantic_rel_score: float,
    matched_keywords: List[str],
    input_type: str,
) -> str:
    lines: List[str] = []

    if len(answer_text.split()) < 5:
        lines.append("Answer is too short. Add more detail and practical reasoning.")
    elif score >= 8:
        lines.append("Strong answer with good technical depth and relevance.")
    elif score >= 6:
        lines.append("Good answer with solid reasoning. Could use more examples or depth.")
    elif score >= 4:
        lines.append("Partial answer with some relevant concepts. Strengthen with clearer structure.")
    else:
        lines.append("Weak answer. Revisit core concepts and provide structured reasoning.")

    if matched_keywords:
        keywords_str = ", ".join(matched_keywords)
        lines.append(f"Key concepts identified: {keywords_str}.")

    if semantic_rel_score >= 7:
        lines.append("Semantic understanding: Well-aligned with expected concepts.")
    elif semantic_rel_score >= 4:
        lines.append("Semantic understanding: Partially aligned. Consider expanding topic coverage.")
    elif semantic_rel_score > 0:
        lines.append("Semantic understanding: Limited alignment. Review core concepts.")

    if input_type == "voice":
        lines.append("Voice transcript processed successfully.")

    return " ".join(lines)


def evaluate_answer_semantic(
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
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate a candidate's interview answer using both heuristic and semantic scoring.

    Args:
        question: The interview question asked.
        answer: The candidate's answer.
        expected_keywords: Keywords expected in the answer.
        expected_concepts: Semantic concepts the answer should cover.
        difficulty_level: Current difficulty level (1-3).
        input_type: Type of input ('text' or 'voice').

    Returns:
        Dictionary with score, feedback, recommendation, and scoring details.
    """
    start = perf_counter()
    # Safely derive owner id for logging (tests may pass dummy current_user)
    owner_id = None
    try:
        if current_user is not None and hasattr(current_user, "id"):
            owner_id = int(getattr(current_user, "id"))
        elif isinstance(current_user, int):
            owner_id = int(current_user)
    except Exception:
        owner_id = None

    logger.info(
        "interview_evaluation_started",
        extra={
            "resume_id": resume_id,
            "owner_id": owner_id,
            "question_length": len(question or ""),
            "input_type": input_type,
        },
    )
    answer_text = (answer or "").strip()
    expected_keywords_clean = [kw for kw in expected_keywords if kw and kw.strip()]
    expected_concepts_clean = [c for c in (expected_concepts or []) if c and c.strip()]

    retrieval_query = query or question or ""
    retrieved_chunks = _retrieve_resume_chunks(
        session=session,
        current_user=current_user,
        resume_id=resume_id,
        query=retrieval_query,
        limit=4,
    )
    derived_concepts = _derive_expected_concepts(
        question,
        expected_concepts_clean,
        retrieved_chunks,
    )
    semantic_targets = derived_concepts or expected_keywords_clean

    heuristic, matched_keywords, keyword_score, length_score, concept_score = _heuristic_score(
        answer_text,
        expected_keywords_clean,
        difficulty_level,
    )

    semantic_q_score, semantic_rel_score = _semantic_score(
        question,
        answer_text,
        semantic_targets,
    )
    concept_similarities, missing_concepts, concept_coverage = _semantic_concept_alignment(
        answer_text,
        semantic_targets,
    )

    final_score = _combine_scores(
        heuristic,
        semantic_q_score,
        semantic_rel_score,
        difficulty_level,
    )

    next_difficulty = _next_difficulty(final_score, difficulty_level)
    recommendation = _recommendation_from_score(final_score)
    retrieval_used = bool(retrieved_chunks)

    technical_depth = min(
        10.0,
        (semantic_rel_score * 0.55)
        + (concept_score * 10.0 * 0.25)
        + (length_score * 10.0 * 0.20),
    )
    confidence_score = min(
        1.0,
        max(0.0, ((semantic_rel_score + semantic_q_score) / 20.0) * 0.5 + (heuristic / 10.0) * 0.5),
    )

    feedback = _build_structured_feedback(
        answer_text,
        final_score,
        heuristic,
        semantic_q_score,
        semantic_rel_score,
        matched_keywords,
        concept_coverage,
        missing_concepts,
        retrieval_used,
        input_type,
    )

    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "interview_evaluation_completed",
        extra={
            "resume_id": resume_id,
            "owner_id": owner_id,
            "score": round(final_score, 2),
            "retrieval_used": retrieval_used,
            "retrieved_chunk_count": len(retrieved_chunks),
            "duration_ms": duration_ms,
        },
    )

    return {
        "score": round(final_score, 2),
        "feedback": feedback,
        "matched_keywords": matched_keywords,
        "next_difficulty": next_difficulty,
        "recommendation": recommendation,
        "question": question,
        "technical_depth": round(technical_depth, 2),
        "concept_coverage": round(concept_coverage * 10.0, 2),
        "missing_concepts": missing_concepts[:5],
        "confidence_score": round(confidence_score, 2),
        "retrieval_used": retrieval_used,
        "scoring_details": {
            "heuristic_score": round(heuristic, 2),
            "semantic_question_score": round(semantic_q_score, 2),
            "semantic_relevance_score": round(semantic_rel_score, 2),
            "keyword_coverage": round(keyword_score, 4),
            "answer_length_score": round(length_score, 4),
            "concept_score": round(concept_score, 4),
            "concept_coverage_score": round(concept_coverage * 10.0, 2),
            "confidence_score": round(confidence_score, 2),
            "retrieval_used": retrieval_used,
            "retrieved_chunk_count": len(retrieved_chunks),
            "difficulty_level": difficulty_level,
            "next_difficulty": next_difficulty,
        },
    }


def evaluate_answer_heuristic(
    *,
    question: str,
    answer: str,
    expected_keywords: List[str],
    difficulty_level: int = 1,
    input_type: str = "text",
) -> Dict[str, Any]:
    """
    Fallback heuristic-only evaluation when semantic scoring is unavailable.
    Preserves existing behavior for backward compatibility.

    Args:
        question: The interview question asked.
        answer: The candidate's answer.
        expected_keywords: Keywords expected in the answer.
        difficulty_level: Current difficulty level (1-3).
        input_type: Type of input ('text' or 'voice').

    Returns:
        Dictionary with score, feedback, recommendation, and scoring details.
    """
    answer_text = (answer or "").strip()
    lowered = answer_text.lower()
    expected_keywords_clean = [kw for kw in expected_keywords if kw and kw.strip()]

    heuristic, matched_keywords, keyword_score, length_score, concept_score = _heuristic_score(
        answer_text,
        expected_keywords_clean,
        difficulty_level,
    )

    next_difficulty = _next_difficulty(heuristic, difficulty_level)
    recommendation = _recommendation_from_score(heuristic)

    if len(answer_text.split()) < 5:
        feedback = "Answer is too short. Add more detail and practical reasoning."
    elif heuristic >= 8:
        feedback = "Strong answer with good technical depth."
    elif heuristic >= 6:
        feedback = "Good answer, but it could use more depth or examples."
    elif heuristic >= 4:
        feedback = "Partial answer. Include clearer concepts, keywords, and examples."
    else:
        feedback = "Weak answer. Revisit the core concept and answer with more structure."

    if input_type == "voice":
        feedback += " Voice transcript accepted successfully."

    missing_concepts = [kw for kw in expected_keywords_clean if kw.lower() not in lowered]
    confidence_score = min(1.0, max(0.0, ((heuristic / 10.0) + keyword_score + length_score) / 3.0))

    return {
        "score": round(heuristic, 2),
        "feedback": feedback,
        "matched_keywords": matched_keywords,
        "next_difficulty": next_difficulty,
        "recommendation": recommendation,
        "question": question,
        "technical_depth": round(min(10.0, heuristic), 2),
        "concept_coverage": round(keyword_score * 10.0, 2),
        "missing_concepts": missing_concepts,
        "confidence_score": round(confidence_score, 2),
        "retrieval_used": False,
        "scoring_details": {
            "heuristic_score": round(heuristic, 2),
            "semantic_question_score": 0.0,
            "semantic_relevance_score": 0.0,
            "keyword_coverage": round(keyword_score, 4),
            "answer_length_score": round(length_score, 4),
            "concept_score": round(concept_score, 4),
            "concept_coverage_score": round(keyword_score * 10.0, 2),
            "confidence_score": round(confidence_score, 2),
            "retrieval_used": False,
            "retrieved_chunk_count": 0,
            "difficulty_level": difficulty_level,
            "next_difficulty": next_difficulty,
        },
    }
