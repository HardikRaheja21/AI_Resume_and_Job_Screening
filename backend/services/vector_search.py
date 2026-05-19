from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlmodel import Session, select

from ..models import Resume, User
from ..services.embedding_service import encode_texts, get_model
from ..resume_parser_service.matcher import extract_tokens
from ..services import vector_store
from ..utils.config import settings
from ..utils import metrics

logger = logging.getLogger("resume_parser.vector_search")

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


@dataclass
class CachedIndex:
    owner_id: int
    signature: Tuple[Tuple[int, str], ...]
    ids: List[int]
    vectors: np.ndarray
    index: Optional[object] = None


_CACHE: Dict[int, CachedIndex] = {}


def _resume_signature(rows: List[Resume]) -> Tuple[Tuple[int, str], ...]:
    sig: List[Tuple[int, str]] = []
    for row in rows:
        updated = row.updated_at if isinstance(row.updated_at, datetime) else None
        sig.append((int(row.id or 0), (updated.isoformat() if updated else "")))
    sig.sort(key=lambda x: x[0])
    return tuple(sig)


def _build_vectors(texts: List[str]) -> np.ndarray:
    embeddings = encode_texts(texts, convert_to_numpy=True, normalize_embeddings=True)
    arr = np.asarray(embeddings, dtype="float32")
    return arr


def _build_faiss_index(vectors: np.ndarray):
    if faiss is None:
        return None
    dim = vectors.shape[1]
    # normalized vectors + IP ~= cosine similarity
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index


def _get_rows(session: Session, current_user: User) -> List[Resume]:
    return session.exec(select(Resume).where(Resume.owner_id == current_user.id)).all()


def _upsert_owner_index(session: Session, current_user: User) -> CachedIndex:
    rows = _get_rows(session, current_user)
    signature = _resume_signature(rows)
    cached = _CACHE.get(current_user.id)
    if cached and cached.signature == signature:
        return cached

    ids = [int(row.id) for row in rows if row.id is not None]
    texts = [row.feature_text or row.parsed_text or "" for row in rows]
    if not texts:
        new_cached = CachedIndex(
            owner_id=current_user.id,
            signature=signature,
            ids=[],
            vectors=np.empty((0, 384), dtype="float32"),
            index=None,
        )
        _CACHE[current_user.id] = new_cached
        return new_cached

    vectors = _build_vectors(texts)
    index = _build_faiss_index(vectors)
    cached = CachedIndex(
        owner_id=current_user.id,
        signature=signature,
        ids=ids,
        vectors=vectors,
        index=index,
    )
    _CACHE[current_user.id] = cached
    return cached


def _token_overlap_score(query: str, text: str) -> float:
    query_tokens = set(extract_tokens(query))
    text_tokens = set(extract_tokens(text))
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens.intersection(text_tokens))
    return max(0.0, min(1.0, overlap / len(query_tokens)))


def semantic_search_resumes(
    *,
    session: Session,
    current_user: User,
    query: str,
    limit: int,
) -> List[Dict[str, object]]:
    if settings.MATCHER_DISABLE_EMBEDDINGS:
        logger.info("semantic_search_disabled")
        raise RuntimeError("Embeddings disabled by configuration")

    start = perf_counter()
    logger.info(
        "semantic_search_started",
        extra={"owner_id": int(current_user.id), "query_length": len(query), "limit": limit},
    )
    try:
        result = vector_store.semantic_search_resumes(
            session=session,
            current_user=current_user,
            query=query,
            limit=limit,
        )
        duration_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "semantic_search_completed",
            extra={"owner_id": int(current_user.id), "result_count": len(result), "duration_ms": duration_ms},
        )
        try:
            metrics.observe_semantic_retrieval_duration(duration_ms / 1000.0)
        except Exception:
            pass
        return result
    except Exception as exc:
        logger.warning("semantic_search_fallback", extra={"error": str(exc), "owner_id": int(current_user.id)})
        try:
            metrics.inc_chroma_fallback()
        except Exception:
            pass
        cached = _upsert_owner_index(session, current_user)
        if not cached.ids:
            return []

        query_vec = encode_texts([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        top_k = max(1, min(limit, len(cached.ids)))

        scored: List[Tuple[int, float]] = []
        if cached.index is not None and faiss is not None:
            similarities, indices = cached.index.search(query_vec, top_k)
            for sim, idx in zip(similarities[0], indices[0]):
                if idx < 0 or idx >= len(cached.ids):
                    continue
                scored.append((cached.ids[idx], float(sim)))
        else:
            sims = np.dot(cached.vectors, query_vec[0])
            ranked = np.argsort(-sims)[:top_k]
            for idx in ranked:
                scored.append((cached.ids[int(idx)], float(sims[int(idx)])))

        rows = session.exec(
            select(Resume)
            .where(Resume.owner_id == current_user.id)
            .where(Resume.id.in_([rid for rid, _ in scored]))
        ).all()
        by_id = {int(row.id): row for row in rows if row.id is not None}

        results: List[Dict[str, object]] = []
        for rid, sim in scored:
            row = by_id.get(rid)
            if not row:
                continue
            score = max(0.0, min(1.0, (sim + 1.0) / 2.0))
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
            "semantic_search_fallback_completed",
            extra={"owner_id": int(current_user.id), "result_count": len(results), "duration_ms": duration_ms},
        )
        try:
            metrics.observe_semantic_retrieval_duration(duration_ms / 1000.0)
        except Exception:
            pass
        return results


def semantic_retrieve_chunks(
    *,
    session: Session,
    current_user: User,
    query: str,
    limit: int,
    max_chunks: int = 3,
) -> List[Dict[str, object]]:
    if settings.MATCHER_DISABLE_EMBEDDINGS:
        logger.info("semantic_retrieve_disabled")
        raise RuntimeError("Embeddings disabled by configuration")

    start = perf_counter()
    logger.info(
        "semantic_retrieve_started",
        extra={"owner_id": int(current_user.id), "query_length": len(query), "limit": limit, "max_chunks": max_chunks},
    )
    try:
        result = vector_store.semantic_retrieve_chunks(
            session=session,
            current_user=current_user,
            query=query,
            limit=limit,
            max_chunks=max_chunks,
        )
        duration_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "semantic_retrieve_completed",
            extra={"owner_id": int(current_user.id), "result_count": len(result), "duration_ms": duration_ms},
        )
        try:
            metrics.observe_semantic_retrieval_duration(duration_ms / 1000.0)
        except Exception:
            pass
        return result
    except Exception as exc:
        logger.warning("semantic_retrieve_fallback", extra={"error": str(exc), "owner_id": int(current_user.id)})
        try:
            metrics.inc_chroma_fallback()
        except Exception:
            pass
        rows = session.exec(select(Resume).where(Resume.owner_id == current_user.id)).all()
        scored = []
        for row in rows:
            text = f"{row.parsed_text or ''} {row.name or ''} {row.tags or ''}"
            score = _token_overlap_score(query, text)
            scored.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "email": row.email,
                    "filename": row.filename,
                    "score": round(score, 4),
                    "stage": row.stage,
                    "top_chunks": [],
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        duration_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "semantic_retrieve_fallback_completed",
            extra={"owner_id": int(current_user.id), "result_count": len(scored), "duration_ms": duration_ms},
        )
        try:
            metrics.observe_semantic_retrieval_duration(duration_ms / 1000.0)
        except Exception:
            pass
        return scored[:limit]


def get_resume_chunks(*, current_user: User, resume_id: int) -> List[Dict[str, object]]:
    if settings.MATCHER_DISABLE_EMBEDDINGS:
        raise RuntimeError("Embeddings disabled by configuration")
    return vector_store.get_resume_chunks(current_user=current_user, resume_id=resume_id)
