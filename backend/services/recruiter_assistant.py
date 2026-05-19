from __future__ import annotations

import json
import logging
from time import perf_counter
import re
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..models import Resume, User
from ..services import ai_assistant, vector_service
from ..utils.config import settings
from ..utils import metrics

logger = logging.getLogger("resume_parser.recruiter_assistant")


def _safe_json_dict(raw_text: str) -> Dict[str, Any]:
    if not raw_text:
        return {}
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(raw_text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return {}
    return {}


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _token_overlap_score(query: str, text: str) -> float:
    query_tokens = {token for token in re.findall(r"\w+", query.lower())}
    text_tokens = {token for token in re.findall(r"\w+", text.lower())}
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens.intersection(text_tokens))
    return max(0.0, min(1.0, overlap / len(query_tokens)))


def _serialize_candidate_reference(row: Resume, score: float = 0.0) -> Dict[str, Any]:
    return {
        "resume_id": int(row.id or 0),
        "name": row.name or row.filename,
        "filename": row.filename,
        "stage": row.stage,
        "score": round(max(0.0, min(1.0, score)), 4),
    }


def _serialize_supporting_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "resume_id": int(chunk.get("resume_id", 0)),
        "resume_name": chunk.get("filename"),
        "chunk_type": chunk.get("chunk_type", "summary"),
        "content_snippet": str(chunk.get("content_snippet") or chunk.get("document") or "")[:250],
    }


def _find_candidate_references(
    session: Session,
    current_user: User,
    query: str,
    limit: int,
) -> List[Dict[str, Any]]:
    if query and not settings.MATCHER_DISABLE_EMBEDDINGS:
        try:
            from . import vector_search

            return vector_search.semantic_search_resumes(
                session=session,
                current_user=current_user,
                query=query,
                limit=limit,
            )
        except Exception as exc:
            logger.debug("Semantic candidate search failed: %s", exc)

    rows = session.exec(select(Resume).where(Resume.owner_id == current_user.id)).all()
    scored: List[Dict[str, Any]] = []
    for row in rows:
        text = f"{row.parsed_text or ''} {row.name or ''} {row.tags or ''}"
        score = _token_overlap_score(query, text)
        scored.append({
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "filename": row.filename,
            "score": round(score, 4),
            "stage": row.stage,
            "top_chunks": [],
        })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


def _build_prompt(
    query: str,
    candidate_references: List[Dict[str, Any]],
    supporting_chunks: List[Dict[str, Any]],
) -> str:
    lines: List[str] = []
    lines.append("You are a recruiter AI assistant. Answer the user question by using the candidate context provided below.")
    lines.append("Return only valid JSON with keys: answer, supporting_chunks, candidate_references, confidence.")
    lines.append("Support the answer with resume chunk evidence and candidate references.")
    lines.append("Answer the question in a concise, recruiter-friendly way.")
    lines.append("If you cannot answer confidently, say so and use the available evidence.")
    lines.append("")
    lines.append(f"Question: {query}")
    lines.append("")
    if candidate_references:
        lines.append("Candidate references:")
        for reference in candidate_references:
            lines.append(
                f"- [{reference.get('resume_id')}] {reference.get('name')} (stage: {reference.get('stage') or 'unknown'}, score: {reference.get('score')})"
            )
        lines.append("")
    if supporting_chunks:
        lines.append("Relevant resume chunks:")
        for chunk in supporting_chunks[:6]:
            lines.append(
                f"- [{chunk.get('resume_id')}] {chunk.get('chunk_type')} : {chunk.get('content_snippet')}"
            )
        lines.append("")
    lines.append(
        "Return JSON only with these fields: answer (string), supporting_chunks (array), candidate_references (array), confidence (number 0.0-1.0)."
    )
    return "\n".join(lines)


def _ai_recruiter_response(
    query: str,
    candidate_references: List[Dict[str, Any]],
    supporting_chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    prompt = _build_prompt(query, candidate_references, supporting_chunks)
    raw = ai_assistant._call_openai(prompt, max_output_tokens=450)
    parsed = _safe_json_dict(raw)
    if not parsed:
        raise RuntimeError("AI response could not be parsed")
    return parsed


def _fallback_recruiter_response(
    query: str,
    candidate_references: List[Dict[str, Any]],
    supporting_chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not supporting_chunks and not candidate_references:
        answer = "No candidate context is available for this question. Please upload or index candidate resumes."
    else:
        if candidate_references and len(candidate_references) == 1:
            ref = candidate_references[0]
            answer = (
                f"Candidate {ref.get('name')} appears to match the query based on their resume context. "
                f"Review the highlighted chunks for details."
            )
        elif candidate_references:
            names = [str(item.get("name")) for item in candidate_references[:3] if item.get("name")]
            answer = (
                f"The most relevant candidates are {', '.join(names)}. "
                f"Use the supporting chunks to compare their strengths and shortlist recommendations."
            )
        else:
            answer = "The query could not be matched to any candidate context." 
        if supporting_chunks:
            answer += " I highlighted the most relevant resume snippets below."
    return {
        "answer": _clean_text(answer),
        "supporting_chunks": supporting_chunks,
        "candidate_references": candidate_references,
        "confidence": 0.35 if supporting_chunks or candidate_references else 0.0,
    }


def answer_question(
    *,
    session: Session,
    current_user: User,
    query: str,
    resume_id: Optional[int] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    query = str(query or "").strip()
    if not query:
        raise ValueError("Query must not be empty")

    start = perf_counter()
    logger.info(
        "recruiter_assistant_query_started",
        extra={
            "owner_id": int(current_user.id),
            "resume_id": resume_id,
            "query_length": len(query),
            "limit": limit,
        },
    )

    candidate_references: List[Dict[str, Any]] = []
    supporting_chunks: List[Dict[str, Any]] = []

    if resume_id is not None:
        row = session.get(Resume, resume_id)
        if not row or row.owner_id != current_user.id:
            raise ValueError("Resume not found")
        candidate_references = [
            _serialize_candidate_reference(row, score=1.0),
        ]
        chunks = vector_service.retrieve_resume_chunks(
            session=session,
            current_user=current_user,
            resume_id=resume_id,
            query=query,
            limit=limit,
        )
        supporting_chunks = [_serialize_supporting_chunk(chunk) for chunk in chunks]
    else:
        references = _find_candidate_references(session, current_user, query, limit)
        candidate_references = [
            {
                "resume_id": int(item.get("id") or 0),
                "name": item.get("name") or item.get("filename", "unknown"),
                "filename": item.get("filename"),
                "stage": item.get("stage"),
                "score": float(item.get("score") or 0.0),
            }
            for item in references
        ]
        for item in references[:limit]:
            if item.get("id") is None:
                continue
            chunks = vector_service.retrieve_resume_chunks(
                session=session,
                current_user=current_user,
                resume_id=int(item["id"]),
                query=query,
                limit=2,
            )
            supporting_chunks.extend([_serialize_supporting_chunk(chunk) for chunk in chunks])
        if len(supporting_chunks) > limit * 3:
            supporting_chunks = supporting_chunks[: limit * 3]

    answer_data: Dict[str, Any] = {}
    try:
        if ai_assistant.is_ai_enabled():
            answer_data = _ai_recruiter_response(query, candidate_references, supporting_chunks)
    except Exception as exc:
        logger.debug("AI recruiter response failed", extra={"error": str(exc), "owner_id": int(current_user.id)})

    if not answer_data:
        answer_data = _fallback_recruiter_response(query, candidate_references, supporting_chunks)

    answer_data["supporting_chunks"] = answer_data.get("supporting_chunks") or supporting_chunks
    answer_data["candidate_references"] = answer_data.get("candidate_references") or candidate_references
    answer_data["confidence"] = float(answer_data.get("confidence") or 0.0)
    answer_data["answer"] = str(answer_data.get("answer") or "")
    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "recruiter_assistant_query_completed",
        extra={
            "owner_id": int(current_user.id),
            "resume_id": resume_id,
            "reference_count": len(candidate_references),
            "supporting_chunk_count": len(supporting_chunks),
            "confidence": answer_data["confidence"],
            "duration_ms": duration_ms,
        },
    )
    try:
        metrics.observe_recruiter_query_duration(duration_ms / 1000.0)
    except Exception:
        pass
    return answer_data
