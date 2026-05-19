from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..models import DeadLetterJob, ProcessingEvent, ProcessingJob, ProcessingSubtask, WorkflowReplay
from ..services import event_sourcing, realtime_events, workflow_runtime
from ..utils.config import settings
from ..utils import metrics


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def _now() -> datetime:
    return datetime.utcnow()


def _json_dumps(value: Optional[Dict[str, Any]]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, default=str)


def _json_loads(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def hash_payload(value: Dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_processing_job(
    session: Session,
    *,
    owner_id: int,
    job_type: str,
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
    queue_name: str = "default",
    priority: int = 5,
    input_payload: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ProcessingJob:
    record = ProcessingJob(
        owner_id=owner_id,
        resume_id=resume_id,
        job_id=job_id,
        job_type=job_type,
        queue_name=queue_name,
        priority=priority,
        status="queued",
        current_step="queued",
        progress=0,
        max_retries=settings.PROCESSING_JOB_MAX_RETRIES,
        input_json=_json_dumps(input_payload),
        request_id=request_id,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    add_processing_event(
        session,
        record,
        event_type="job_created",
        step="queued",
        status="queued",
        message="Processing job queued",
        detail=input_payload,
    )
    try:
        metrics.inc_processing_job(job_type, "queued")
    except Exception:
        pass
    return record


def attach_celery_task(session: Session, processing_job_id: int, celery_task_id: str) -> None:
    record = session.get(ProcessingJob, processing_job_id)
    if not record:
        return
    record.celery_task_id = celery_task_id
    record.updated_at = _now()
    session.add(record)
    session.commit()


def add_processing_event(
    session: Session,
    job: ProcessingJob,
    *,
    event_type: str,
    step: str,
    status: str,
    message: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> ProcessingEvent:
    event = ProcessingEvent(
        processing_job_id=int(job.id or 0),
        owner_id=job.owner_id,
        resume_id=job.resume_id,
        event_type=event_type,
        step=step,
        status=status,
        message=message,
        detail_json=_json_dumps(detail),
        request_id=job.request_id,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    metrics.inc_processing_event(step, status)
    event_sourcing.append_event(
        session,
        stream_id=f"processing_job:{job.id}",
        event_type=f"processing.{event_type}",
        owner_id=job.owner_id,
        processing_job_id=int(job.id or 0),
        resume_id=job.resume_id,
        payload={
            "step": step,
            "status": status,
            "message": message,
            "detail": detail or {},
        },
        metadata={"request_id": job.request_id},
    )
    realtime_events.publish_job_event(
        int(job.id or 0),
        {
            "type": "processing.event",
            "event_id": event.id,
            "processing_job_id": job.id,
            "resume_id": job.resume_id,
            "event_type": event.event_type,
            "step": event.step,
            "status": event.status,
            "message": event.message,
            "detail": _json_loads(event.detail_json),
            "request_id": event.request_id,
            "created_at": event.created_at,
        },
    )
    return event


def get_or_create_subtask(
    session: Session,
    job: ProcessingJob,
    *,
    task_name: str,
    queue_name: str,
    input_payload: Dict[str, Any],
) -> ProcessingSubtask:
    idempotency_key = f"{job.id}:{task_name}:{hash_payload(input_payload)}"
    existing = session.exec(
        select(ProcessingSubtask)
        .where(ProcessingSubtask.processing_job_id == job.id)
        .where(ProcessingSubtask.idempotency_key == idempotency_key)
    ).first()
    if existing:
        return existing
    subtask = ProcessingSubtask(
        processing_job_id=int(job.id or 0),
        owner_id=job.owner_id,
        resume_id=job.resume_id,
        task_name=task_name,
        queue_name=queue_name,
        idempotency_key=idempotency_key,
        input_hash=hash_payload(input_payload),
    )
    session.add(subtask)
    session.commit()
    session.refresh(subtask)
    return subtask


def mark_subtask_started(session: Session, subtask_id: int, celery_task_id: Optional[str] = None) -> None:
    row = session.get(ProcessingSubtask, subtask_id)
    if not row:
        return
    row.status = "running"
    row.attempt += 1
    row.celery_task_id = celery_task_id or row.celery_task_id
    row.started_at = row.started_at or _now()
    row.updated_at = _now()
    session.add(row)
    session.commit()


def mark_subtask_completed(session: Session, subtask_id: int, output: Optional[Dict[str, Any]] = None) -> None:
    row = session.get(ProcessingSubtask, subtask_id)
    if not row:
        return
    row.status = "completed"
    row.output_json = _json_dumps(output)
    row.completed_at = _now()
    row.updated_at = _now()
    session.add(row)
    session.commit()


def mark_subtask_failed(session: Session, subtask_id: int, error: str) -> None:
    row = session.get(ProcessingSubtask, subtask_id)
    if not row:
        return
    row.status = "failed"
    row.error_message = error[:1000]
    row.updated_at = _now()
    session.add(row)
    session.commit()


def mark_job_started(session: Session, processing_job_id: int, *, locked_by: Optional[str] = None) -> Optional[ProcessingJob]:
    record = session.get(ProcessingJob, processing_job_id)
    if not record:
        return None
    workflow_runtime.transition_job(record, "running")
    record.current_step = "started"
    record.progress = max(record.progress, 5)
    record.attempts += 1
    record.locked_by = locked_by
    record.started_at = record.started_at or _now()
    record.updated_at = _now()
    session.add(record)
    session.commit()
    session.refresh(record)
    add_processing_event(session, record, event_type="job_started", step="started", status="running")
    metrics.inc_processing_job(record.job_type, "running")
    return record


def update_job_step(
    session: Session,
    processing_job_id: int,
    *,
    step: str,
    progress: int,
    message: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> Optional[ProcessingJob]:
    record = session.get(ProcessingJob, processing_job_id)
    if not record:
        return None
    workflow_runtime.transition_job(record, "running")
    record.current_step = step
    record.progress = max(0, min(100, progress))
    record.updated_at = _now()
    session.add(record)
    session.commit()
    session.refresh(record)
    add_processing_event(
        session,
        record,
        event_type="step_updated",
        step=step,
        status="running",
        message=message,
        detail=detail,
    )
    return record


def complete_job(
    session: Session,
    processing_job_id: int,
    *,
    result: Optional[Dict[str, Any]] = None,
) -> Optional[ProcessingJob]:
    record = session.get(ProcessingJob, processing_job_id)
    if not record:
        return None
    workflow_runtime.transition_job(record, "completed")
    record.current_step = "completed"
    record.progress = 100
    record.result_json = _json_dumps(result)
    record.completed_at = _now()
    record.updated_at = _now()
    session.add(record)
    session.commit()
    session.refresh(record)
    add_processing_event(
        session,
        record,
        event_type="job_completed",
        step="completed",
        status="completed",
        message="Processing job completed",
        detail=result,
    )
    metrics.inc_processing_job(record.job_type, "completed")
    return record


def fail_job(
    session: Session,
    processing_job_id: int,
    *,
    error_message: str,
    error_code: str = "processing_failed",
    retryable: bool = True,
) -> Optional[ProcessingJob]:
    record = session.get(ProcessingJob, processing_job_id)
    if not record:
        return None
    should_retry = retryable and record.attempts < record.max_retries
    workflow_runtime.transition_job(record, "retrying" if should_retry else "failed")
    record.current_step = "retry_wait" if should_retry else "failed"
    record.error_code = error_code
    record.error_message = error_message[:1000]
    record.failed_at = None if should_retry else _now()
    record.updated_at = _now()
    session.add(record)
    session.commit()
    session.refresh(record)
    add_processing_event(
        session,
        record,
        event_type="job_retrying" if should_retry else "job_failed",
        step=record.current_step,
        status=record.status,
        message=record.error_message,
        detail={"retryable": should_retry, "attempts": record.attempts, "max_retries": record.max_retries},
    )
    if not should_retry:
        existing_dlq = session.exec(
            select(DeadLetterJob)
            .where(DeadLetterJob.processing_job_id == processing_job_id)
            .where(DeadLetterJob.status == "open")
        ).first()
        if not existing_dlq:
            dlq = DeadLetterJob(
                processing_job_id=processing_job_id,
                owner_id=record.owner_id,
                resume_id=record.resume_id,
                source_task=record.current_step or record.job_type,
                queue_name=record.queue_name,
                payload_json=record.input_json,
                exception_type=error_code,
                exception_message=record.error_message,
                retry_count=record.attempts,
            )
            session.add(dlq)
            session.commit()
            metrics.inc_dlq_event(dlq.source_task, "open")
    metrics.inc_processing_job(record.job_type, record.status)
    return record


def serialize_job(record: ProcessingJob, include_input: bool = False) -> Dict[str, Any]:
    result = {
        "id": record.id,
        "owner_id": record.owner_id,
        "resume_id": record.resume_id,
        "job_id": record.job_id,
        "celery_task_id": record.celery_task_id,
        "job_type": record.job_type,
        "queue_name": record.queue_name,
        "status": record.status,
        "current_step": record.current_step,
        "progress": record.progress,
        "priority": record.priority,
        "attempts": record.attempts,
        "max_retries": record.max_retries,
        "error_code": record.error_code,
        "error_message": record.error_message,
        "result": _json_loads(record.result_json),
        "request_id": record.request_id,
        "started_at": record.started_at,
        "completed_at": record.completed_at,
        "failed_at": record.failed_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    if include_input:
        result["input"] = _json_loads(record.input_json)
    return result


def list_job_subtasks(session: Session, processing_job_id: int, owner_id: int) -> List[Dict[str, Any]]:
    rows = session.exec(
        select(ProcessingSubtask)
        .where(ProcessingSubtask.processing_job_id == processing_job_id)
        .where(ProcessingSubtask.owner_id == owner_id)
        .order_by(ProcessingSubtask.created_at.asc())
    ).all()
    return [
        {
            "id": row.id,
            "processing_job_id": row.processing_job_id,
            "resume_id": row.resume_id,
            "task_name": row.task_name,
            "queue_name": row.queue_name,
            "celery_task_id": row.celery_task_id,
            "status": row.status,
            "attempt": row.attempt,
            "idempotency_key": row.idempotency_key,
            "input_hash": row.input_hash,
            "output": _json_loads(row.output_json),
            "error_message": row.error_message,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


def list_job_events(session: Session, processing_job_id: int, owner_id: int) -> List[Dict[str, Any]]:
    rows = session.exec(
        select(ProcessingEvent)
        .where(ProcessingEvent.processing_job_id == processing_job_id)
        .where(ProcessingEvent.owner_id == owner_id)
        .order_by(ProcessingEvent.created_at.asc())
    ).all()
    return [
        {
            "id": row.id,
            "processing_job_id": row.processing_job_id,
            "event_type": row.event_type,
            "step": row.step,
            "status": row.status,
            "message": row.message,
            "detail": _json_loads(row.detail_json),
            "request_id": row.request_id,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def create_workflow_replay(
    session: Session,
    *,
    source_job: ProcessingJob,
    replay_job: ProcessingJob,
    replay_mode: str,
    reason: Optional[str] = None,
) -> WorkflowReplay:
    replay = WorkflowReplay(
        source_processing_job_id=int(source_job.id or 0),
        replay_processing_job_id=int(replay_job.id or 0),
        owner_id=source_job.owner_id,
        replay_mode=replay_mode,
        reason=reason,
    )
    session.add(replay)
    session.commit()
    session.refresh(replay)
    metrics.inc_workflow_replay(replay_mode)
    return replay


def list_dead_letters(session: Session, owner_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    query = select(DeadLetterJob).where(DeadLetterJob.owner_id == owner_id)
    if status:
        query = query.where(DeadLetterJob.status == status)
    rows = session.exec(query.order_by(DeadLetterJob.created_at.desc()).limit(100)).all()
    return [
        {
            "id": row.id,
            "processing_job_id": row.processing_job_id,
            "resume_id": row.resume_id,
            "source_task": row.source_task,
            "queue_name": row.queue_name,
            "exception_type": row.exception_type,
            "exception_message": row.exception_message,
            "retry_count": row.retry_count,
            "status": row.status,
            "created_at": row.created_at,
            "replayed_at": row.replayed_at,
        }
        for row in rows
    ]


def mark_dead_letter_replayed(session: Session, dead_letter_id: int) -> None:
    row = session.get(DeadLetterJob, dead_letter_id)
    if not row:
        return
    row.status = "replayed"
    row.replayed_at = _now()
    session.add(row)
    session.commit()
    metrics.inc_dlq_event(row.source_task, "replayed")
