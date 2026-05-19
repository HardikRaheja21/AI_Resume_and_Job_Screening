from __future__ import annotations

import logging
import os
import re
from time import perf_counter
from typing import Any, Dict, List, Optional

import numpy as np
from sqlmodel import Session, select

from ..database import engine
from ..models import Resume, User
from ..services import embedding_cache
from ..services.embedding_service import encode_texts, get_model
from ..utils.config import settings

try:
    from chromadb import Client
    from chromadb.config import Settings as ChromaSettings
except ImportError:  # pragma: no cover
    Client = None  # type: ignore
    ChromaSettings = None  # type: ignore

logger = logging.getLogger("resume_parser.vector_service")
from ..utils import metrics

_COLLECTION_NAME = "resume_vectors"
_CHROMA_CLIENT: Optional[Client] = None


def _chroma_available() -> bool:
    return Client is not None


def _create_chroma_client() -> Client:
    global _CHROMA_CLIENT
    if _CHROMA_CLIENT is not None:
        return _CHROMA_CLIENT

    persist_dir = settings.VECTOR_DB_DIR or "./vector_store"
    os.makedirs(persist_dir, exist_ok=True)
    _CHROMA_CLIENT = Client(
        ChromaSettings(
            chroma_db_impl=settings.VECTOR_CHROMA_IMPL,
            persist_directory=persist_dir,
        )
    )
    return _CHROMA_CLIENT


def _get_collection() -> Any:
    client = _create_chroma_client()
    return client.get_or_create_collection(name=settings.VECTOR_COLLECTION_NAME)


def _to_similarity(distance: Optional[float]) -> float:
    if distance is None:
        return 0.0
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return 0.0
    similarity = 1.0 - value
    return max(0.0, min(1.0, similarity))


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _chunk_text(text: str, max_chars: int = 400) -> str:
    cleaned = _clean_text(text)
    return cleaned[:max_chars] if len(cleaned) > max_chars else cleaned


def _parse_skill_list(resume: Resume) -> List[str]:
    if resume.extracted_skills:
        return [skill.strip() for skill in resume.extracted_skills.split(",") if skill.strip()]
    return []


def _extract_project_snippets(text: str) -> List[str]:
    matches: List[str] = []
    if not text:
        return matches

    for pattern in [r"project[s]?:?\s*([^\n]+)", r"develop(ed|ing)\s+([^\n]+)", r"built\s+([^\n]+)"]:
        for match in re.finditer(pattern, text, flags=re.I):
            snippet = match.group(0).strip()
            if snippet and len(snippet) > 20:
                matches.append(_chunk_text(snippet, max_chars=300))
    if not matches:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if any(token in line.lower() for token in ("project", "built", "developed", "designed", "implemented")):
                matches.append(_chunk_text(line, max_chars=300))
                if len(matches) >= 3:
                    break
    return matches[:3]


def _extract_experience_snippets(resume: Resume, text: Optional[str] = None) -> List[str]:
    snippets: List[str] = []
    if resume.experience_years is not None:
        snippets.append(f"{resume.experience_years} years of experience")
    if text:
        for match in re.finditer(r"(\d+(?:\.\d+)?\+?\s+years?[^\n]*)", text, flags=re.I):
            snippet = match.group(0).strip()
            if snippet and snippet not in snippets:
                snippets.append(_chunk_text(snippet, max_chars=200))
    if not snippets and resume.parsed_text:
        lower = (resume.parsed_text or "").lower()
        if "experience" in lower:
            snippets.append(_chunk_text(resume.parsed_text[:300], max_chars=300))
    return snippets[:2]


def _extract_education_snippets(resume: Resume, text: Optional[str] = None) -> List[str]:
    snippets: List[str] = []
    if resume.education:
        snippets.append(_chunk_text(resume.education, max_chars=250))
    if text:
        for match in re.finditer(r"(b\.?tech[^\n]*|m\.?tech[^\n]*|bachelor[^\n]*|master[^\n]*|mba[^\n]*)", text, flags=re.I):
            snippet = match.group(0).strip()
            if snippet and snippet not in snippets:
                snippets.append(_chunk_text(snippet, max_chars=250))
    return snippets[:2]


def _build_resume_chunks(resume: Resume, parsed_text: Optional[str] = None) -> List[Dict[str, Any]]:
    text = parsed_text or resume.parsed_text or resume.feature_text or ""
    chunks: List[Dict[str, Any]] = []

    skills = _parse_skill_list(resume)
    if skills:
        chunks.append(
            {
                "chunk_type": "skills",
                "content": _chunk_text("Skills: " + ", ".join(skills), max_chars=350),
            }
        )

    for snippet in _extract_project_snippets(text):
        chunks.append({"chunk_type": "projects", "content": snippet})

    for snippet in _extract_experience_snippets(resume, text):
        chunks.append({"chunk_type": "experience", "content": snippet})

    for snippet in _extract_education_snippets(resume, text):
        chunks.append({"chunk_type": "education", "content": snippet})

    if not chunks and text:
        chunks.append({"chunk_type": "summary", "content": _chunk_text(text, max_chars=500)})

    seen = set()
    unique_chunks: List[Dict[str, Any]] = []
    for chunk in chunks:
        content = chunk["content"]
        if content in seen:
            continue
        seen.add(content)
        unique_chunks.append(chunk)
    return unique_chunks


def _serialize_metadata(resume: Resume, chunk_type: str, content: str) -> Dict[str, Any]:
    return {
        "resume_id": int(resume.id or 0),
        "owner_id": int(resume.owner_id),
        "chunk_type": chunk_type,
        "filename": resume.filename,
        "resume_name": resume.name or "",
        "stage": resume.stage or "new",
        "content_snippet": content[:120],
    }


def _embed_texts(texts: List[str], session: Optional[Session] = None) -> np.ndarray:
    if session is not None and settings.EMBEDDING_CACHE_ENABLE:
        return embedding_cache.get_or_create_embeddings(session, texts)
    embeddings = encode_texts(texts, convert_to_numpy=True, normalize_embeddings=True)
    return np.asarray(embeddings, dtype="float32")


def index_resume_chunks(resume: Resume, parsed_text: Optional[str] = None) -> None:
    if not _chroma_available():
        logger.warning("chroma_unavailable", extra={"resume_id": int(resume.id or 0)})
        try:
            metrics.inc_chroma_fallback()
        except Exception:
            pass
        return
    if resume.id is None:
        raise ValueError("Resume must have an id before indexing")

    start = perf_counter()
    logger.info(
        "index_resume_chunks_started",
        extra={"resume_id": int(resume.id), "owner_id": int(resume.owner_id)},
    )
    collection = _get_collection()
    try:
        collection.delete(where={"resume_id": int(resume.id), "owner_id": int(resume.owner_id)})
    except Exception:
        pass

    chunks = _build_resume_chunks(resume, parsed_text=parsed_text)
    if not chunks:
        logger.info(
            "index_resume_chunks_skipped",
            extra={"resume_id": int(resume.id), "chunk_count": 0},
        )
        return

    ids: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    documents: List[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        chunk_id = f"{resume.id}:{chunk['chunk_type']}:{idx}"
        ids.append(chunk_id)
        documents.append(chunk["content"])
        metadatas.append(_serialize_metadata(resume, chunk["chunk_type"], chunk["content"]))

    with Session(engine) as session:
        embeddings = _embed_texts(documents, session=session).tolist()
    collection.add(
        ids=ids,
        metadatas=metadatas,
        documents=documents,
        embeddings=embeddings,
    )
    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "index_resume_chunks_completed",
        extra={
            "resume_id": int(resume.id),
            "chunk_count": len(chunks),
            "duration_ms": duration_ms,
        },
    )


def delete_resume_chunks(resume: Resume) -> None:
    if not _chroma_available() or resume.id is None:
        return
    collection = _get_collection()
    try:
        collection.delete(where={"resume_id": int(resume.id), "owner_id": int(resume.owner_id)})
    except Exception:
        logger.warning("Failed to delete chunks for resume %s", resume.id)


def rebuild_owner_resume_index(session: Session, owner_id: int) -> None:
    if not _chroma_available():
        raise RuntimeError("ChromaDB is not installed")

    collection = _get_collection()
    try:
        collection.delete(where={"owner_id": owner_id})
    except Exception:
        pass

    rows = session.exec(select(Resume).where(Resume.owner_id == owner_id)).all()
    for resume in rows:
        try:
            index_resume_chunks(resume)
        except Exception as exc:
            logger.warning("Failed to index resume %s: %s", resume.id, exc)


def semantic_search_resumes(
    *,
    session: Session,
    current_user: User,
    query: str,
    limit: int,
) -> List[Dict[str, Any]]:
    if not _chroma_available():
        logger.warning("semantic_search_chroma_unavailable", extra={"owner_id": int(current_user.id)})
        try:
            metrics.inc_chroma_fallback()
        except Exception:
            pass
        raise RuntimeError("ChromaDB is not installed")
    if not query or not query.strip():
        return []

    start = perf_counter()
    logger.info(
        "semantic_search_started",
        extra={
            "owner_id": int(current_user.id),
            "query_length": len(query),
            "limit": limit,
        },
    )
    collection = _get_collection()
    try:
        count = collection.count(where={"owner_id": int(current_user.id)})
    except Exception:
        count = 0
    if count == 0:
        rebuild_owner_resume_index(session, int(current_user.id))

    query_embedding = _embed_texts([query])[0].tolist()
    response = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        where={"owner_id": int(current_user.id)},
        include=["metadatas", "distances"],
    )

    candidates: Dict[int, float] = {}
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]
    for metadata, distance in zip(metadatas, distances):
        resume_id = int(metadata.get("resume_id", 0))
        if resume_id <= 0:
            continue
        similarity = _to_similarity(distance)
        candidates[resume_id] = max(candidates.get(resume_id, 0.0), similarity)

    if not candidates:
        logger.info(
            "semantic_search_no_candidates",
            extra={"owner_id": int(current_user.id), "query_length": len(query)},
        )
        return []

    ranked = sorted(candidates.items(), key=lambda item: item[1], reverse=True)[:limit]
    rows = session.exec(
        select(Resume)
        .where(Resume.owner_id == int(current_user.id))
        .where(Resume.id.in_([rid for rid, _ in ranked]))
    ).all()
    rows_by_id = {int(row.id or 0): row for row in rows}

    results: List[Dict[str, Any]] = []
    for resume_id, score in ranked:
        row = rows_by_id.get(resume_id)
        if not row:
            continue
        results.append(
            {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "filename": row.filename,
                "score": round(score, 4),
                "stage": row.stage,
            }
        )
    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "semantic_search_completed",
        extra={
            "owner_id": int(current_user.id),
            "result_count": len(results),
            "duration_ms": duration_ms,
        },
    )
    return results


def semantic_retrieve_chunks(
    *,
    session: Session,
    current_user: User,
    query: str,
    limit: int,
    max_chunks: int = 3,
) -> List[Dict[str, Any]]:
    if not _chroma_available():
        logger.warning("semantic_retrieve_chroma_unavailable", extra={"owner_id": int(current_user.id)})
        try:
            metrics.inc_chroma_fallback()
        except Exception:
            pass
        raise RuntimeError("ChromaDB is not installed")
    if not query or not query.strip():
        return []

    start = perf_counter()
    logger.info(
        "semantic_retrieve_started",
        extra={
            "owner_id": int(current_user.id),
            "query_length": len(query),
            "limit": limit,
            "max_chunks": max_chunks,
        },
    )
    collection = _get_collection()
    try:
        count = collection.count(where={"owner_id": int(current_user.id)})
    except Exception:
        count = 0
    if count == 0:
        rebuild_owner_resume_index(session, int(current_user.id))

    query_embedding = _embed_texts([query])[0].tolist()
    response = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(limit * max_chunks, 10),
        where={"owner_id": int(current_user.id)},
        include=["metadatas", "documents", "distances"],
    )

    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]
    documents = response.get("documents", [[]])[0]

    grouped: Dict[int, Dict[str, Any]] = {}
    for metadata, distance, document in zip(metadatas, distances, documents):
        resume_id = int(metadata.get("resume_id", 0))
        if resume_id <= 0:
            continue

        similarity = _to_similarity(distance)
        chunk = {
            "chunk_type": metadata.get("chunk_type", "summary"),
            "content_snippet": metadata.get("content_snippet") or (document or "")[:200],
            "score": round(similarity, 4),
        }
        current = grouped.setdefault(resume_id, {"score": 0.0, "chunks": []})
        current["score"] = max(current["score"], similarity)
        current["chunks"].append(chunk)

    for entry in grouped.values():
        entry["chunks"].sort(key=lambda item: item["score"], reverse=True)
        entry["chunks"] = entry["chunks"][:max_chunks]

    ranked = sorted(grouped.items(), key=lambda item: item[1]["score"], reverse=True)[:limit]
    rows = session.exec(
        select(Resume)
        .where(Resume.owner_id == int(current_user.id))
        .where(Resume.id.in_([rid for rid, _ in ranked]))
    ).all()
    rows_by_id = {int(row.id or 0): row for row in rows}

    results: List[Dict[str, Any]] = []
    for resume_id, details in ranked:
        row = rows_by_id.get(resume_id)
        if not row:
            continue
        results.append(
            {
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "filename": row.filename,
                "stage": row.stage,
                "score": round(details["score"], 4),
                "top_chunks": details["chunks"],
            }
        )
    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "semantic_retrieve_completed",
        extra={
            "owner_id": int(current_user.id),
            "result_count": len(results),
            "duration_ms": duration_ms,
        },
    )
    return results


def get_resume_chunks(*, current_user: User, resume_id: int) -> List[Dict[str, Any]]:
    if not _chroma_available():
        raise RuntimeError("ChromaDB is not installed")
    collection = _get_collection()
    response = collection.get(where={"resume_id": resume_id, "owner_id": int(current_user.id)}, include=["metadatas", "documents"])
    metadatas = response.get("metadatas", [])
    documents = response.get("documents", [])
    if metadatas and isinstance(metadatas[0], list):
        metadatas = metadatas[0]
    if documents and isinstance(documents[0], list):
        documents = documents[0]

    results: List[Dict[str, Any]] = []
    for metadata, document in zip(metadatas, documents):
        if not isinstance(metadata, dict):
            continue
        results.append(
            {
                "chunk_type": metadata.get("chunk_type", "summary"),
                "content_snippet": metadata.get("content_snippet") or (document or "")[:200],
                "filename": metadata.get("filename"),
                "resume_id": int(metadata.get("resume_id", 0)),
                "stage": metadata.get("stage"),
                "document": document,
            }
        )
    return results


def _build_resume_context(chunks: List[Dict[str, Any]], max_chars: int = 1200) -> str:
    parts: List[str] = []
    total_chars = 0
    for chunk in chunks:
        snippet = str(chunk.get("content_snippet", "") or "").strip()
        if not snippet:
            continue
        part = f"{str(chunk.get('chunk_type', 'summary')).title()}: {snippet}"
        if total_chars + len(part) > max_chars:
            break
        parts.append(part)
        total_chars += len(part)
    return "\n".join(parts)


def retrieve_resume_chunks(
    *,
    session: Session,
    current_user: User,
    resume_id: int,
    query: str,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    logger.info(
        "resume_chunk_retrieval_started",
        extra={
            "resume_id": resume_id,
            "owner_id": int(current_user.id),
            "query_length": len(query or ""),
            "limit": limit,
        },
    )
    if not query or not query.strip():
        if not _chroma_available():
            row = session.exec(
                select(Resume)
                .where(Resume.owner_id == int(current_user.id))
                .where(Resume.id == resume_id)
            ).first()
            if not row:
                return []
            return [
                {
                    "chunk_type": chunk.get("chunk_type", "summary"),
                    "content_snippet": str(chunk.get("content", ""))[:200],
                    "filename": row.filename,
                    "resume_id": int(row.id or 0),
                    "stage": row.stage or "new",
                    "document": chunk.get("content", ""),
                }
                for chunk in _build_resume_chunks(row)[:limit]
            ]
        return get_resume_chunks(current_user=current_user, resume_id=resume_id)[:limit]

    if not _chroma_available():
        logger.warning(
            "resume_chunk_retrieval_fallback_no_chroma",
            extra={"resume_id": resume_id, "owner_id": int(current_user.id)},
        )
        row = session.exec(
            select(Resume)
            .where(Resume.owner_id == int(current_user.id))
            .where(Resume.id == resume_id)
        ).first()
        if not row:
            return []
        return [
            {
                "chunk_type": chunk.get("chunk_type", "summary"),
                "content_snippet": str(chunk.get("content", ""))[:200],
                "filename": row.filename,
                "resume_id": int(row.id or 0),
                "stage": row.stage or "new",
                "document": chunk.get("content", ""),
            }
            for chunk in _build_resume_chunks(row)[:limit]
        ]

    try:
        query_embedding = _embed_texts([query])[0].tolist()
        collection = _get_collection()
        response = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where={"resume_id": resume_id, "owner_id": int(current_user.id)},
            include=["metadatas", "documents", "distances"],
        )
        metadatas = response.get("metadatas", [])
        documents = response.get("documents", [])
        distances = response.get("distances", [])
        if metadatas and isinstance(metadatas[0], list):
            metadatas = metadatas[0]
        if documents and isinstance(documents[0], list):
            documents = documents[0]
        if distances and isinstance(distances[0], list):
            distances = distances[0]

        results: List[Dict[str, Any]] = []
        for metadata, document, distance in zip(metadatas, documents, distances):
            if not isinstance(metadata, dict):
                continue
            results.append(
                {
                    "chunk_type": metadata.get("chunk_type", "summary"),
                    "content_snippet": metadata.get("content_snippet") or (document or "")[:200],
                    "filename": metadata.get("filename"),
                    "resume_id": int(metadata.get("resume_id", 0)),
                    "stage": metadata.get("stage"),
                    "document": document,
                    "distance": distance,
                }
            )
        if results:
            return results
    except Exception:
        pass

    row = session.exec(
        select(Resume)
        .where(Resume.owner_id == int(current_user.id))
        .where(Resume.id == resume_id)
    ).first()
    if not row:
        return []
    return [
        {
            "chunk_type": chunk.get("chunk_type", "summary"),
            "content_snippet": str(chunk.get("content", ""))[:200],
            "filename": row.filename,
            "resume_id": int(row.id or 0),
            "stage": row.stage or "new",
            "document": chunk.get("content", ""),
        }
        for chunk in _build_resume_chunks(row)[:limit]
    ]


def build_resume_context(chunks: List[Dict[str, Any]]) -> str:
    return _build_resume_context(chunks)
