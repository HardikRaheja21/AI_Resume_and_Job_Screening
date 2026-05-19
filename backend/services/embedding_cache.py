from __future__ import annotations

import hashlib
import json
from typing import List, Optional

import numpy as np
from sqlmodel import Session, select

from ..models import EmbeddingCache
from ..services import embedding_service
from ..utils import metrics
from ..utils.config import settings


def hash_text(text: str) -> str:
    normalized = " ".join((text or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_or_create_embeddings(session: Session, texts: List[str], *, model_name: Optional[str] = None) -> np.ndarray:
    if not texts:
        return np.asarray([], dtype="float32")
    if not settings.EMBEDDING_CACHE_ENABLE:
        return np.asarray(
            embedding_service.encode_texts(texts, convert_to_numpy=True, normalize_embeddings=True),
            dtype="float32",
        )

    selected_model = model_name or settings.EMBEDDING_CACHE_MODEL_NAME
    ordered_vectors: list[Optional[list[float]]] = []
    misses: list[tuple[int, str, str]] = []

    for idx, text in enumerate(texts):
        text_hash = hash_text(text)
        row = session.exec(
            select(EmbeddingCache)
            .where(EmbeddingCache.text_hash == text_hash)
            .where(EmbeddingCache.model_name == selected_model)
        ).first()
        if row:
            row.usage_count += 1
            session.add(row)
            ordered_vectors.append(json.loads(row.vector_json))
            metrics.inc_embedding_cache_hit()
        else:
            ordered_vectors.append(None)
            misses.append((idx, text, text_hash))
            metrics.inc_embedding_cache_miss()

    if misses:
        new_embeddings = np.asarray(
            embedding_service.encode_texts([item[1] for item in misses], convert_to_numpy=True, normalize_embeddings=True),
            dtype="float32",
        )
        for miss_idx, (_, _, text_hash) in enumerate(misses):
            vector = [float(value) for value in new_embeddings[miss_idx].tolist()]
            ordered_vectors[misses[miss_idx][0]] = vector
            session.add(
                EmbeddingCache(
                    text_hash=text_hash,
                    model_name=selected_model,
                    vector_json=json.dumps(vector),
                    dimensions=len(vector),
                )
            )
        session.commit()
    else:
        session.commit()

    return np.asarray([vector or [] for vector in ordered_vectors], dtype="float32")
