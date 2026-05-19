from __future__ import annotations

import logging
from typing import Any, Dict

from sqlmodel import Session

from ...database import engine
from ...models import InterviewAnswer, ProcessingJob, Resume
from ...services import answer_evaluator, processing_service, vector_service
from ...utils.logging import clear_request_context, set_request_context
from ..celery_app import celery_app

logger = logging.getLogger("resume_parser.workers.ai_pipeline")


@celery_app.task(bind=True, name="ai.evaluate_answer", retry_backoff=True, retry_jitter=True, max_retries=2, time_limit=300)
def evaluate_interview_answer(self, processing_job_id: int, interview_answer_id: int) -> Dict[str, Any]:
    with Session(engine) as session:
        job = processing_service.mark_job_started(session, processing_job_id, locked_by=getattr(self.request, "hostname", None))
        if not job:
            return {"status": "missing_job", "processing_job_id": processing_job_id}
        if job.request_id:
            set_request_context(request_id=job.request_id)
        try:
            answer = session.get(InterviewAnswer, interview_answer_id)
            if not answer:
                raise ValueError(f"InterviewAnswer {interview_answer_id} not found")
            processing_service.update_job_step(
                session,
                processing_job_id,
                step="ai_evaluation",
                progress=50,
                message="Evaluating interview answer with isolated AI worker",
            )
            worker_user = type("WorkerUser", (), {"id": job.owner_id})()
            result = answer_evaluator.evaluate_answer_semantic(
                question=answer.question_text,
                answer=answer.answer_text,
                expected_keywords=(answer.expected_keywords or "").split(",") if answer.expected_keywords else [],
                difficulty_level=answer.difficulty_before,
                input_type=answer.input_type,
                resume_id=answer.resume_id,
                session=session,
                current_user=worker_user,
            )
            answer.score = float(result.get("score", answer.score) or 0.0)
            answer.feedback = str(result.get("feedback") or result.get("summary") or "")
            session.add(answer)
            session.commit()
            processing_service.complete_job(session, processing_job_id, result=result)
            return result
        except Exception as exc:
            logger.exception("ai_answer_evaluation_failed", extra={"processing_job_id": processing_job_id})
            processing_service.fail_job(session, processing_job_id, error_message=str(exc), retryable=True)
            raise
        finally:
            clear_request_context()


@celery_app.task(bind=True, name="ai.generate_candidate_summary", retry_backoff=True, retry_jitter=True, max_retries=2, time_limit=300)
def generate_candidate_summary(self, processing_job_id: int, resume_id: int) -> Dict[str, Any]:
    with Session(engine) as session:
        job: ProcessingJob | None = processing_service.mark_job_started(
            session,
            processing_job_id,
            locked_by=getattr(self.request, "hostname", None),
        )
        if not job:
            return {"status": "missing_job", "processing_job_id": processing_job_id}
        if job.request_id:
            set_request_context(request_id=job.request_id)
        try:
            resume = session.get(Resume, resume_id)
            if not resume:
                raise ValueError(f"Resume {resume_id} not found")
            processing_service.update_job_step(
                session,
                processing_job_id,
                step="summary_retrieval",
                progress=40,
                message="Retrieving evidence chunks for candidate summary",
            )
            chunks = vector_service.retrieve_resume_chunks(
                current_user=type("WorkerUser", (), {"id": job.owner_id})(),
                resume_id=resume_id,
                query="candidate strengths weaknesses role fit skills projects experience",
                limit=6,
            )
            summary = {
                "resume_id": resume_id,
                "candidate_name": resume.name,
                "headline": f"{resume.name or resume.filename} has {resume.experience_years or 'unknown'} years of experience.",
                "evidence_chunks": chunks[:6],
                "match_score": resume.match_score,
                "recommended_focus": ["technical depth", "project ownership", "role-specific missing skills"],
            }
            processing_service.complete_job(session, processing_job_id, result=summary)
            return summary
        except Exception as exc:
            logger.exception("candidate_summary_failed", extra={"processing_job_id": processing_job_id})
            processing_service.fail_job(session, processing_job_id, error_message=str(exc), retryable=True)
            raise
        finally:
            clear_request_context()
