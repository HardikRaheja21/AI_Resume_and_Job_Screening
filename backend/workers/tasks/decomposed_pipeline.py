from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any, Dict, Iterable, Optional

from celery import chain, chord, group
from sqlmodel import Session

from ...database import engine
from ...models import CandidateAISummary, Job, MatchExplanation, ProcessingJob, Resume, VectorIndexVersion
from ...resume_parser_service import matcher as resume_matcher
from ...resume_parser_service import parser as resume_parser
from ...services import ai_governance, event_sourcing, policy_engine, processing_service, vector_store, workflow_runtime
from ...utils import metrics
from ...utils.config import settings
from ...utils.logging import clear_request_context, set_request_context
from ...utils.tracing import inject_trace_context, start_span
from ..celery_app import celery_app

logger = logging.getLogger("resume_parser.workers.decomposed_pipeline")


PIPELINE_VERSION = "resume-dag-v1"


def _json_list(values: Iterable[Any]) -> str:
    return json.dumps([str(value) for value in values])


def _ctx(processing_job_id: int, **updates: Any) -> Dict[str, Any]:
    data = {
        "processing_job_id": processing_job_id,
        "pipeline_version": PIPELINE_VERSION,
        "trace_context": inject_trace_context({}),
    }
    data.update(updates)
    return data


def _load_job(session: Session, processing_job_id: int) -> ProcessingJob:
    job = session.get(ProcessingJob, processing_job_id)
    if not job:
        raise ValueError(f"ProcessingJob {processing_job_id} not found")
    if job.request_id:
        set_request_context(request_id=job.request_id)
    return job


def _subtask(session: Session, job: ProcessingJob, task_name: str, queue_name: str, context: Dict[str, Any]):
    return processing_service.get_or_create_subtask(
        session,
        job,
        task_name=task_name,
        queue_name=queue_name,
        input_payload=context,
    )


@celery_app.task(bind=True, name="resume.pipeline.dispatch", time_limit=60)
def dispatch_resume_pipeline(self, processing_job_id: int) -> Dict[str, Any]:
    signature = chain(
        parse_extract_resume.s(_ctx(processing_job_id)).set(queue="default"),
        match_resume_to_job.s().set(queue="default"),
        embed_and_index_resume.s().set(queue="embedding"),
        generate_candidate_summary.s().set(queue="ai"),
        finalize_resume_pipeline.s().set(queue="default"),
    )
    async_result = signature.apply_async()
    with Session(engine) as session:
        processing_service.attach_celery_task(session, processing_job_id, async_result.id)
    return {"processing_job_id": processing_job_id, "celery_task_id": async_result.id}


@celery_app.task(bind=True, name="resume.pipeline.dispatch_parallel", time_limit=60)
def dispatch_parallel_resume_pipeline(self, processing_job_id: int) -> Dict[str, Any]:
    with Session(engine) as session:
        job = session.get(ProcessingJob, processing_job_id)
        if job:
            workflow_runtime.check_queue_dispatch_allowed(session, queue_name="bulk", owner_id=job.owner_id)
    async_result = chain(
        parse_extract_resume.s(_ctx(processing_job_id)).set(queue="default"),
        launch_parallel_post_parse.s().set(queue="bulk"),
    ).apply_async()
    with Session(engine) as session:
        processing_service.attach_celery_task(session, processing_job_id, async_result.id)
    metrics.inc_queue_dispatch("bulk", "resume.pipeline.dispatch_parallel")
    return {"processing_job_id": processing_job_id, "celery_task_id": async_result.id, "mode": "parallel"}


@celery_app.task(bind=True, name="resume.pipeline.launch_parallel", time_limit=60)
def launch_parallel_post_parse(self, context: Dict[str, Any]) -> Dict[str, Any]:
    processing_job_id = int(context["processing_job_id"])
    with Session(engine) as session:
        job = session.get(ProcessingJob, processing_job_id)
        if job:
            workflow_runtime.check_queue_dispatch_allowed(session, queue_name="default", owner_id=job.owner_id)
            workflow_runtime.check_queue_dispatch_allowed(session, queue_name="embedding", owner_id=job.owner_id)
    callback = chain(
        merge_parallel_results.s(processing_job_id).set(queue="default"),
        generate_candidate_summary.s().set(queue="ai"),
        finalize_resume_pipeline.s().set(queue="default"),
    )
    async_result = chord(
        group(
            match_resume_to_job.s(context).set(queue="default"),
            embed_and_index_resume.s(context).set(queue="embedding"),
        )
    )(callback)
    metrics.inc_queue_dispatch("default", "resume.pipeline.match")
    metrics.inc_queue_dispatch("embedding", "resume.pipeline.embed_index")
    with Session(engine) as session:
        job = session.get(ProcessingJob, processing_job_id)
        if job:
            event_sourcing.append_event(
                session,
                stream_id=f"processing_job:{processing_job_id}",
                event_type="workflow.parallel_dispatched",
                owner_id=job.owner_id,
                processing_job_id=processing_job_id,
                resume_id=job.resume_id,
                payload={"workflow_version": PIPELINE_VERSION, "mode": "parallel"},
            )
            workflow_runtime.create_checkpoint(
                session,
                job,
                checkpoint_name="parallel_dispatched",
                workflow_version=PIPELINE_VERSION,
                state=context,
                trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else {},
            )
            processing_service.add_processing_event(
                session,
                job,
                event_type="parallel_tasks_dispatched",
                step="parallel_match_index",
                status="running",
                message="Match and vector indexing dispatched in parallel",
                detail={"celery_task_id": async_result.id},
            )
    return {**context, "parallel_celery_task_id": async_result.id}


@celery_app.task(bind=True, name="resume.pipeline.merge_parallel", time_limit=120)
def merge_parallel_results(self, results: list[Dict[str, Any]], processing_job_id: int) -> Dict[str, Any]:
    merged = _ctx(processing_job_id)
    for result in results or []:
        if isinstance(result, dict):
            merged.update(result)
    with Session(engine) as session:
        job = _load_job(session, processing_job_id)
        subtask = _subtask(session, job, "merge_parallel", "default", merged)
        processing_service.mark_subtask_started(session, int(subtask.id or 0), getattr(self.request, "id", None))
        processing_service.update_job_step(
            session,
            processing_job_id,
            step="merge_parallel",
            progress=82,
            message="Merged parallel match and indexing results",
            detail={"result_count": len(results or [])},
        )
        workflow_runtime.create_checkpoint(
            session,
            job,
            checkpoint_name="parallel_merged",
            workflow_version=PIPELINE_VERSION,
            state=merged,
            trace_context=merged.get("trace_context") if isinstance(merged.get("trace_context"), dict) else {},
        )
        processing_service.mark_subtask_completed(session, int(subtask.id or 0), {"merged": True})
    return merged


@celery_app.task(
    bind=True,
    name="resume.pipeline.parse_extract",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    time_limit=600,
)
def parse_extract_resume(self, context: Dict[str, Any]) -> Dict[str, Any]:
    processing_job_id = int(context["processing_job_id"])
    with Session(engine) as session:
        job = _load_job(session, processing_job_id)
        processing_service.mark_job_started(session, processing_job_id, locked_by=getattr(self.request, "hostname", None))
        subtask = _subtask(session, job, "parse_extract", "default", context)
        processing_service.mark_subtask_started(session, int(subtask.id or 0), getattr(self.request, "id", None))
        try:
            with start_span(
                "resume.parse_extract",
                {"processing_job_id": processing_job_id, "resume_id": job.resume_id or 0},
                trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else None,
            ):
                if job.resume_id is None:
                    raise ValueError("Processing job has no resume_id")
                resume = session.get(Resume, job.resume_id)
                if not resume:
                    raise ValueError(f"Resume {job.resume_id} not found")
                if resume.parsed_text and resume.feature_text:
                    processing_service.update_job_step(
                        session,
                        processing_job_id,
                        step="parse_extract",
                        progress=25,
                        message="Parse/extract skipped; resume already has structured text",
                        detail={"idempotent_skip": True},
                    )
                    processing_service.mark_subtask_completed(session, int(subtask.id or 0), {"skipped": True})
                    return {**context, "resume_id": resume.id, "parsed": True, "idempotent_skip": True}

                processing_service.update_job_step(
                    session,
                    processing_job_id,
                    step="parse_extract",
                    progress=20,
                    message="Parsing resume and extracting structured fields",
                )
                parsed_text = resume_parser.parse_resume(resume.filepath, resume.filename)
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
                workflow_runtime.create_checkpoint(
                    session,
                    job,
                    checkpoint_name="parse_extract_completed",
                    workflow_version=PIPELINE_VERSION,
                    state={"resume_id": resume.id, "skill_count": len(skills)},
                    trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else {},
                )
                processing_service.mark_subtask_completed(
                    session,
                    int(subtask.id or 0),
                    {"resume_id": resume.id, "skill_count": len(skills), "text_length": len(parsed_text or "")},
                )
                return {**context, "resume_id": resume.id, "parsed": True, "skill_count": len(skills)}
        except Exception as exc:
            processing_service.mark_subtask_failed(session, int(subtask.id or 0), str(exc))
            processing_service.fail_job(session, processing_job_id, error_message=str(exc), retryable=True)
            raise
        finally:
            clear_request_context()


@celery_app.task(bind=True, name="resume.pipeline.match", autoretry_for=(RuntimeError,), retry_backoff=True, retry_jitter=True, max_retries=2, time_limit=300)
def match_resume_to_job(self, context: Dict[str, Any]) -> Dict[str, Any]:
    processing_job_id = int(context["processing_job_id"])
    with Session(engine) as session:
        job = _load_job(session, processing_job_id)
        subtask = _subtask(session, job, "match", "default", context)
        processing_service.mark_subtask_started(session, int(subtask.id or 0), getattr(self.request, "id", None))
        try:
            resume = session.get(Resume, job.resume_id) if job.resume_id else None
            selected_job = session.get(Job, job.job_id) if job.job_id else None
            if not resume:
                raise ValueError("Resume not found for matching")
            if not selected_job:
                processing_service.update_job_step(
                    session,
                    processing_job_id,
                    step="match",
                    progress=45,
                    message="Match skipped; no job description attached",
                    detail={"idempotent_skip": True},
                )
                processing_service.mark_subtask_completed(session, int(subtask.id or 0), {"skipped": True})
                return {**context, "matched": False}

            processing_service.update_job_step(
                session,
                processing_job_id,
                step="match",
                progress=45,
                message="Generating explainable job fit score",
            )
            with start_span(
                "resume.match",
                {"processing_job_id": processing_job_id, "resume_id": resume.id or 0, "job_id": selected_job.id or 0},
                trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else None,
            ):
                match_result = resume_matcher.compare_resume_to_jd(selected_job.description, resume.parsed_text or "")
            score = float(match_result["score"])
            jd_analysis = dict(match_result.get("jd_analysis") or {})
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

            explanation = {
                "score": score,
                "decision": resume.final_decision,
                "score_breakdown": match_result.get("score_breakdown") or {},
                "matched_skills": match_result.get("matched_skills") or [],
                "related_skills": match_result.get("related_skills") or [],
                "missing_skills": match_result.get("missing_skills") or [],
                "summary": match_result.get("summary"),
            }
            session.add(
                MatchExplanation(
                    owner_id=job.owner_id,
                    resume_id=int(resume.id or 0),
                    job_id=selected_job.id,
                    processing_job_id=processing_job_id,
                    explanation_version=settings.MATCH_EXPLANATION_VERSION,
                    score=score,
                    explanation_json=json.dumps(explanation),
                    evidence_json=json.dumps({"source": "matcher_score_breakdown"}),
                )
            )
            ai_governance.record_ai_artifact(
                session,
                owner_id=job.owner_id,
                resume_id=int(resume.id or 0),
                job_id=selected_job.id,
                processing_job_id=processing_job_id,
                artifact_type="match_explanation",
                artifact=explanation,
                model_name="rules+embeddings",
                prompt_version=settings.MATCH_EXPLANATION_VERSION,
                evidence={"source": "matcher_score_breakdown"},
            )
            session.commit()
            workflow_runtime.create_checkpoint(
                session,
                job,
                checkpoint_name="match_completed",
                workflow_version=PIPELINE_VERSION,
                state={"resume_id": resume.id, "score": score},
                trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else {},
            )
            processing_service.mark_subtask_completed(session, int(subtask.id or 0), {"score": score})
            return {**context, "matched": True, "match_score": score}
        except Exception as exc:
            processing_service.mark_subtask_failed(session, int(subtask.id or 0), str(exc))
            processing_service.fail_job(session, processing_job_id, error_message=str(exc), retryable=True)
            raise
        finally:
            clear_request_context()


@celery_app.task(bind=True, name="resume.pipeline.embed_index", autoretry_for=(RuntimeError,), retry_backoff=True, retry_jitter=True, max_retries=3, time_limit=400)
def embed_and_index_resume(self, context: Dict[str, Any]) -> Dict[str, Any]:
    processing_job_id = int(context["processing_job_id"])
    with Session(engine) as session:
        job = _load_job(session, processing_job_id)
        subtask = _subtask(session, job, "embed_index", "embedding", context)
        processing_service.mark_subtask_started(session, int(subtask.id or 0), getattr(self.request, "id", None))
        try:
            resume = session.get(Resume, job.resume_id) if job.resume_id else None
            if not resume:
                raise ValueError("Resume not found for vector indexing")
            processing_service.update_job_step(
                session,
                processing_job_id,
                step="embed_index",
                progress=70,
                message="Embedding chunks and updating vector index",
            )
            with start_span(
                "resume.embed_index",
                {"processing_job_id": processing_job_id, "resume_id": resume.id or 0},
                trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else None,
            ):
                vector_store.index_resume_chunks(resume, resume.parsed_text)
            session.add(
                VectorIndexVersion(
                    owner_id=job.owner_id,
                    resume_id=int(resume.id or 0),
                    processing_job_id=processing_job_id,
                    collection_name=settings.VECTOR_COLLECTION_NAME,
                    embedding_model=settings.EMBEDDING_CACHE_MODEL_NAME,
                    schema_version=settings.VECTOR_SCHEMA_VERSION,
                    chunk_count=0,
                    status="active",
                )
            )
            session.commit()
            workflow_runtime.create_checkpoint(
                session,
                job,
                checkpoint_name="embed_index_completed",
                workflow_version=PIPELINE_VERSION,
                state={"resume_id": resume.id, "indexed": True},
                trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else {},
            )
            processing_service.mark_subtask_completed(session, int(subtask.id or 0), {"indexed": True})
            return {**context, "indexed": True}
        except Exception as exc:
            processing_service.mark_subtask_failed(session, int(subtask.id or 0), str(exc))
            processing_service.fail_job(session, processing_job_id, error_message=str(exc), retryable=True)
            raise
        finally:
            clear_request_context()


@celery_app.task(bind=True, name="resume.pipeline.generate_summary", autoretry_for=(RuntimeError,), retry_backoff=True, retry_jitter=True, max_retries=2, time_limit=300)
def generate_candidate_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
    processing_job_id = int(context["processing_job_id"])
    with Session(engine) as session:
        job = _load_job(session, processing_job_id)
        subtask = _subtask(session, job, "generate_summary", "ai", context)
        processing_service.mark_subtask_started(session, int(subtask.id or 0), getattr(self.request, "id", None))
        try:
            resume = session.get(Resume, job.resume_id) if job.resume_id else None
            if not resume:
                raise ValueError("Resume not found for AI summary")
            processing_service.update_job_step(
                session,
                processing_job_id,
                step="generate_summary",
                progress=88,
                message="Generating evidence-backed candidate summary",
            )
            skills = [item.strip() for item in (resume.extracted_skills or "").split(",") if item.strip()]
            start = perf_counter()
            summary = {
                "headline": f"{resume.name or resume.filename} is a candidate with {resume.experience_years or 'unknown'} years of experience.",
                "strengths": skills[:8],
                "risks": json.loads(resume.missing_skills_json or "[]")[:6] if resume.missing_skills_json else [],
                "recommended_interview_focus": ["project ownership", "production depth", "missing role requirements"],
                "match_score": resume.match_score,
                "prompt_version": settings.AI_PROMPT_VERSION,
            }
            session.add(
                CandidateAISummary(
                    owner_id=job.owner_id,
                    resume_id=int(resume.id or 0),
                    processing_job_id=processing_job_id,
                    prompt_version=settings.AI_PROMPT_VERSION,
                    model_name=settings.OPENAI_MODEL,
                    summary_json=json.dumps(summary),
                    evidence_json=json.dumps({"resume_id": resume.id, "source": "structured_resume_fields"}),
                    confidence=0.75 if skills else 0.45,
                )
            )
            artifact = ai_governance.record_ai_artifact(
                session,
                owner_id=job.owner_id,
                resume_id=int(resume.id or 0),
                job_id=job.job_id,
                processing_job_id=processing_job_id,
                artifact_type="candidate_summary",
                artifact=summary,
                model_name=settings.OPENAI_MODEL,
                prompt_version=settings.AI_PROMPT_VERSION,
                evidence={"resume_id": resume.id, "source": "structured_resume_fields"},
                latency_ms=round((perf_counter() - start) * 1000, 2),
                token_count=len(json.dumps(summary).split()),
                estimated_cost_usd=0.0,
            )
            ai_governance.record_retrieval_evidence(
                session,
                owner_id=job.owner_id,
                resume_id=int(resume.id or 0),
                job_id=job.job_id,
                processing_job_id=processing_job_id,
                artifact_id=int(artifact.id or 0),
                query="candidate summary structured resume fields",
                retriever_version=settings.VECTOR_SCHEMA_VERSION,
                evidence={"source": "structured_resume_fields", "skills": skills[:8]},
            )
            evidence_score = policy_engine.evidence_sufficiency_score(len(skills[:8]), required_count=3)
            risk_score = policy_engine.hallucination_risk_score(
                evidence_score=evidence_score,
                generated_claim_count=len(summary.get("strengths") or []),
            )
            status = "passed"
            if evidence_score < settings.MIN_EVIDENCE_SUFFICIENCY_SCORE or risk_score > settings.MAX_HALLUCINATION_RISK_SCORE:
                status = "needs_review"
            policy_engine.record_compliance_artifact(
                session,
                owner_id=job.owner_id,
                resume_id=int(resume.id or 0),
                processing_job_id=processing_job_id,
                artifact_type="candidate_summary_safety",
                policy_version=settings.AI_PROMPT_VERSION,
                status=status,
                risk_score=risk_score,
                details={
                    "evidence_sufficiency_score": evidence_score,
                    "hallucination_risk_score": risk_score,
                    "claim_count": len(summary.get("strengths") or []),
                },
            )
            session.commit()
            workflow_runtime.create_checkpoint(
                session,
                job,
                checkpoint_name="summary_completed",
                workflow_version=PIPELINE_VERSION,
                state={"resume_id": resume.id, "summary_created": True},
                trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else {},
            )
            processing_service.mark_subtask_completed(session, int(subtask.id or 0), {"summary_created": True})
            return {**context, "summary_created": True}
        except Exception as exc:
            processing_service.mark_subtask_failed(session, int(subtask.id or 0), str(exc))
            processing_service.fail_job(session, processing_job_id, error_message=str(exc), retryable=True)
            raise
        finally:
            clear_request_context()


@celery_app.task(bind=True, name="resume.pipeline.finalize", time_limit=120)
def finalize_resume_pipeline(self, context: Dict[str, Any]) -> Dict[str, Any]:
    processing_job_id = int(context["processing_job_id"])
    with Session(engine) as session:
        job = _load_job(session, processing_job_id)
        subtask = _subtask(session, job, "finalize", "default", context)
        processing_service.mark_subtask_started(session, int(subtask.id or 0), getattr(self.request, "id", None))
        result = {
            "resume_id": job.resume_id,
            "job_id": job.job_id,
            "pipeline_version": PIPELINE_VERSION,
            "matched": context.get("matched", False),
            "indexed": context.get("indexed", False),
            "summary_created": context.get("summary_created", False),
        }
        processing_service.mark_subtask_completed(session, int(subtask.id or 0), result)
        workflow_runtime.create_checkpoint(
            session,
            job,
            checkpoint_name="workflow_finalized",
            workflow_version=PIPELINE_VERSION,
            state=result,
            trace_context=context.get("trace_context") if isinstance(context.get("trace_context"), dict) else {},
        )
        event_sourcing.append_event(
            session,
            stream_id=f"processing_job:{processing_job_id}",
            event_type="workflow.completed",
            owner_id=job.owner_id,
            processing_job_id=processing_job_id,
            resume_id=job.resume_id,
            payload={**result, "status": "completed", "step": "finalize"},
        )
        processing_service.complete_job(session, processing_job_id, result=result)
        clear_request_context()
        return result
