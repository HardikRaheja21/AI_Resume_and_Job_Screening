import pytest

prom = pytest.importorskip("prometheus_client")
from prometheus_client import generate_latest
from backend.utils import metrics


def test_metrics_exposed():
    # Increment counters and observe histograms
    metrics.inc_ocr_fallback()
    metrics.inc_embedding_disabled()
    metrics.inc_chroma_fallback()
    metrics.inc_spacy_fallback()
    metrics.inc_background_tasks_failed()
    metrics.observe_ocr_duration(0.1)
    metrics.observe_embedding_duration(0.05)
    metrics.observe_semantic_retrieval_duration(0.02)
    metrics.observe_interview_eval_duration(0.2)
    metrics.observe_recruiter_query_duration(0.1)
    metrics.observe_upload_processing_duration(0.3)

    text = generate_latest()
    decoded = text.decode("utf-8")
    # Ensure key metric names are present
    assert "resume_parser_ocr_fallbacks_total" in decoded
    assert "resume_parser_embedding_disabled_total" in decoded
    assert "resume_parser_chroma_fallbacks_total" in decoded
    assert "resume_parser_spacy_fallbacks_total" in decoded
    assert "resume_parser_background_tasks_failed_total" in decoded
    assert "resume_parser_ocr_duration_seconds" in decoded
    assert "resume_parser_embedding_duration_seconds" in decoded
    assert "resume_parser_semantic_retrieval_duration_seconds" in decoded
    assert "resume_parser_interview_evaluation_duration_seconds" in decoded
    assert "resume_parser_recruiter_query_duration_seconds" in decoded
    assert "resume_parser_upload_processing_duration_seconds" in decoded
