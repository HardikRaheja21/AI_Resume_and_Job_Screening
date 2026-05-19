from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any, Dict, Iterable, Optional

from sqlmodel import Session

from ...database import engine
from ...models import Job, Resume
from ...resume_parser_service import matcher as resume_matcher
from ...resume_parser_service import parser as resume_parser
from ...services import processing_service, vector_store
from ...utils import metrics
from ...utils.logging import clear_request_context, set_request_context
from ..celery_app import celery_app

logger = logging.getLogger("resume_parser.workers.resume_pipeline")


def _json_list(values: Iterable[Any]) -> str:
    return json.dumps([str(value) for value in values])


def _run_step(processing_job_id: int, step: str, fn, *args, **kwargs):
    start = perf_counter()
    try:
        return fn(*args, **kwargs)
    finally:
        duration = perf_counter() - start
        try:
            metrics.observe_processing_step("resume_processing", step, duration)
        except Exception:
            pass


@celery_app.task(
    bind=True,
    name="resume.process",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    time_limit=900,
)
def process_resume(self, processing_job_id: int) -> Dict[str, Any]:
    worker_name = getattr(getattr(self, "request", None), "hostname", None)
    with Session(engine) as session:
        job = processing_service.mark_job_started(session, processing_job_id, locked_by=worker_name)
        if not job:
            return {"status": "missing_job", "processing_job_id": processing_job_id}
        if job.request_id:
            set_request_context(request_id=job.request_id)

        try:
            if job.resume_id is None:
                raise ValueError("Processing job has no resume_id")
            resume = session.get(Resume, job.resume_id)
            if not resume:
                raise ValueError(f"Resume {job.resume_id} not found")

            processing_service.update_job_step(
                session,
                processing_job_id,
                step="parse_extract",
                progress=20,
                message="Parsing resume and extracting structured fields",
            )
            parsed_text = _run_step(
                processing_job_id,
                "parse_extract",
                resume_parser.parse_resume,
                resume.filepath,
                resume.filename,
            )
            structured = resume_parser.extract_structured_resume_data(parsed_text)
            resume.parsed_text = parsed_text
            resume.email = str(structured.get("email")) if structured.get("email") else resume.email
            resume.phone = str(structured.get("phone")) if structured.get("phone") else resume.phone
            resume.name = str(structured.get("name")) if structured.get("name") else resume.name
            resume.education = str(structured.get("education")) if structured.get("education") else resume.education
            experience_years = structured.get("experience_years")
            resume.experience_years = float(experience_years) if experience_years is not None else resume.experience_years
            skills = [str(skill) for skill in (structured.get("skills") or [])]
            resume.extracted_skills = ",".join(skills) if skills else resume.extracted_skills
            resume.feature_text = str(structured.get("feature_text") or parsed_text)
            session.add(resume)
            session.commit()
            session.refresh(resume)

            match_result: Optional[Dict[str, Any]] = None
            if job.job_id is not None:
                selected_job = session.get(Job, job.job_id)
                if selected_job:
                    processing_service.update_job_step(
                        session,
                        processing_job_id,
                        step="match",
                        progress=50,
                        message="Matching resume against job description",
                    )
                    match_result = _run_step(
                        processing_job_id,
                        "match",
                        resume_matcher.compare_resume_to_jd,
                        selected_job.description,
                        parsed_text,
                    )
                    score = float(match_result["score"])
                    jd_analysis = dict(match_result.get("jd_analysis") or {})
                    resume.job_id = selected_job.id
                    resume.matched_job = selected_job.title
                    resume.match_score = score
                    resume.final_score = score
                    resume.final_decision = "selected" if match_result.get("selected", score >= 0.6) else "rejected"
                    resume.role = str(jd_analysis.get("role")) if jd_analysis.get("role") else None
                    resume.role_category = str(jd_analysis.get("role_category")) if jd_analysis.get("role_category") else None
                    resume.required_skills_json = _json_list(match_result.get("required_skills") or [])
                    resume.optional_skills_json = _json_list(match_result.get("optional_skills") or [])
                    resume.matched_skills_json = _json_list(match_result.get("matched_skills") or [])
                    resume.related_skills_json = _json_list(match_result.get("related_skills") or [])
                    resume.missing_skills_json = _json_list(match_result.get("missing_skills") or [])
                    resume.jd_keywords_json = _json_list(jd_analysis.get("keywords") or [])
                    resume.score_breakdown_json = json.dumps(match_result.get("score_breakdown") or {})
                    resume.jd_analysis_json = json.dumps(jd_analysis)
                    resume.ai_evaluation_text = str(match_result.get("ai_evaluation") or "") or None
                    session.add(resume)
                    session.commit()
                    session.refresh(resume)

            processing_service.update_job_step(
                session,
                processing_job_id,
                step="embed_index",
                progress=75,
                message="Embedding resume chunks and updating vector index",
            )
            _run_step(processing_job_id, "embed_index", vector_store.index_resume_chunks, resume, parsed_text)

            result = {
                "resume_id": resume.id,
                "match_score": resume.match_score,
                "final_decision": resume.final_decision,
                "matched": bool(match_result),
            }
            processing_service.complete_job(session, processing_job_id, result=result)
            return result
        except Exception as exc:
            logger.exception("resume_processing_failed", extra={"processing_job_id": processing_job_id})
            processing_service.fail_job(
                session,
                processing_job_id,
                error_message=str(exc),
                retryable=True,
            )
            raise
        finally:
            clear_request_context()


@celery_app.task(bind=True, name="resume.bulk_dispatch", time_limit=300)
def bulk_dispatch(self, processing_job_ids: list[int]) -> Dict[str, Any]:
    dispatched = 0
    for processing_job_id in processing_job_ids:
        async_result = process_resume.apply_async(args=[processing_job_id], queue="default")
        with Session(engine) as session:
            processing_service.attach_celery_task(session, processing_job_id, async_result.id)
        dispatched += 1
    return {"dispatched": dispatched}
