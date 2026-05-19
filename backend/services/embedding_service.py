import logging
import threading
from functools import lru_cache
from time import perf_counter
from typing import Any, List, Optional, Tuple

from ..utils.config import settings
from ..utils import metrics

logger = logging.getLogger("resume_parser.embedding")

SentenceTransformer = None
sentence_transformers_util = None
_MODEL = None
_MODEL_LOCK = threading.Lock()
_EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def is_embedding_available() -> bool:
    """Check if embeddings can be used. Attempts to load model if not already loaded."""
    if settings.MATCHER_DISABLE_EMBEDDINGS:
        return False
    return _get_model() is not None


def is_embedding_enabled() -> bool:
    """Lightweight check if embeddings are enabled (without loading model)."""
    return not settings.MATCHER_DISABLE_EMBEDDINGS


def _load_sentence_transformers() -> Tuple[Any, Any]:
    global SentenceTransformer, sentence_transformers_util
    if SentenceTransformer is None or sentence_transformers_util is None:
        try:
            from sentence_transformers import SentenceTransformer as _SentenceTransformer, util as _util
        except Exception as exc:
            logger.warning("sentence_transformers_import_failed", extra={"error": str(exc)})
            raise
        SentenceTransformer = _SentenceTransformer
        sentence_transformers_util = _util
    return SentenceTransformer, sentence_transformers_util


def _get_model() -> Optional[Any]:
    if settings.MATCHER_DISABLE_EMBEDDINGS:
        logger.info("embeddings_disabled")
        try:
            metrics.inc_embedding_disabled()
        except Exception:
            pass
        return None
    if SentenceTransformer is None:
        try:
            _load_sentence_transformers()
        except Exception as exc:
            logger.warning("sentence_transformers_load_failed", extra={"error": str(exc)})
            return None
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                try:
                    _MODEL = SentenceTransformer(_EMBEDDING_MODEL_NAME)
                    logger.info(
                        "embedding_model_initialized",
                        extra={"model_name": _EMBEDDING_MODEL_NAME},
                    )
                except Exception as exc:
                    logger.warning("embedding_model_init_failed", extra={"error": str(exc)})
                    return None
    return _MODEL


def get_model() -> Any:
    model = _get_model()
    if model is None:
        raise RuntimeError("Embeddings disabled or model unavailable")
    return model


def get_sentence_transformers_utils() -> Any:
    if sentence_transformers_util is None:
        _load_sentence_transformers()
    return sentence_transformers_util


def encode_texts(
    texts: List[str], convert_to_numpy: bool = True, normalize_embeddings: bool = True
) -> Any:
    model = get_model()
    start = perf_counter()
    embeddings = model.encode(texts, convert_to_numpy=convert_to_numpy, normalize_embeddings=normalize_embeddings)
    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "embeddings_generated",
        extra={
            "text_count": len(texts),
            "duration_ms": duration_ms,
            "convert_to_numpy": convert_to_numpy,
            "normalize_embeddings": normalize_embeddings,
        },
    )
    try:
        metrics.observe_embedding_duration(duration_ms / 1000.0)
    except Exception:
        pass
    return embeddings


@lru_cache(maxsize=1024)
def cached_embedding(text: str) -> Any:
    return encode_texts([text])[0]
