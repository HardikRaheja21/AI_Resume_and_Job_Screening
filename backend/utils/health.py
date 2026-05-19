from typing import Dict

from ..services import embedding_service, vector_service
from ..resume_parser_service import ocr as resume_ocr
from ..services import nlp_extractor


def embedding_ready() -> bool:
    try:
        return embedding_service.is_embedding_available()
    except Exception:
        return False


def vector_db_ready() -> bool:
    try:
        if not vector_service._chroma_available():
            return False
        # attempt to create client (may be cached)
        try:
            vector_service._create_chroma_client()
            return True
        except Exception:
            return False
    except Exception:
        return False


def ocr_ready() -> bool:
    try:
        return resume_ocr.is_ocr_available()
    except Exception:
        return False


def spacy_ready() -> bool:
    try:
        return nlp_extractor.is_nlp_available()
    except Exception:
        return False


def readiness_summary() -> Dict[str, bool]:
    return {
        "embedding_model": embedding_ready(),
        "vector_db": vector_db_ready(),
        "ocr": ocr_ready(),
        "spacy": spacy_ready(),
    }
