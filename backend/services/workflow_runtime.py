from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from ..models import ProcessingJob, QueueGovernancePolicy, WorkflowCheckpoint
from ..utils import metrics
from ..utils.config import settings

LEGAL_JOB_TRANSITIONS = {
    "queued": {"running", "cancelled", "failed"},
    "running": {"retrying", "completed", "failed", "cancelled"},
    "retrying": {"running", "failed", "cancelled"},
    "completed": set(),
    "failed": {"queued"},
    "cancelled": set(),
}


def validate_transition(from_state: str, to_state: str) -> None:
    valid = to_state in LEGAL_JOB_TRANSITIONS.get(from_state, set()) or from_state == to_state
    metrics.inc_fsm_transition(from_state, to_state, valid)
    if not valid:
        raise ValueError(f"Illegal workflow transition: {from_state} -> {to_state}")


def transition_job(record: ProcessingJob, to_state: str) -> None:
    validate_transition(record.status, to_state)
    record.status = to_state


def create_checkpoint(
    session: Session,
    job: ProcessingJob,
    *,
    checkpoint_name: str,
    workflow_version: str,
    state: Dict[str, Any],
    trace_context: Optional[Dict[str, Any]] = None,
) -> WorkflowCheckpoint:
    checkpoint = WorkflowCheckpoint(
        processing_job_id=int(job.id or 0),
        owner_id=job.owner_id,
        resume_id=job.resume_id,
        checkpoint_name=checkpoint_name,
        workflow_version=workflow_version,
        state_json=json.dumps(state, default=str),
        trace_context_json=json.dumps(trace_context or {}, default=str),
    )
    session.add(checkpoint)
    session.commit()
    session.refresh(checkpoint)
    return checkpoint


def latest_checkpoint(session: Session, processing_job_id: int) -> Optional[WorkflowCheckpoint]:
    return session.exec(
        select(WorkflowCheckpoint)
        .where(WorkflowCheckpoint.processing_job_id == processing_job_id)
        .order_by(WorkflowCheckpoint.created_at.desc())
    ).first()


def queue_name_for_owner(base_queue: str, owner_id: int) -> str:
    if not settings.TENANT_QUEUE_ISOLATION_ENABLE:
        return base_queue
    return f"{base_queue}.tenant.{owner_id}"


def queue_policy(session: Session, queue_name: str, owner_id: Optional[int] = None) -> QueueGovernancePolicy:
    row = None
    if owner_id is not None:
        row = session.exec(
            select(QueueGovernancePolicy)
            .where(QueueGovernancePolicy.queue_name == queue_name)
            .where(QueueGovernancePolicy.owner_id == owner_id)
            .where(QueueGovernancePolicy.is_active == True)  # noqa: E712
        ).first()
    if row is None:
        row = session.exec(
            select(QueueGovernancePolicy)
            .where(QueueGovernancePolicy.queue_name == queue_name)
            .where(QueueGovernancePolicy.owner_id == None)  # noqa: E711
            .where(QueueGovernancePolicy.is_active == True)  # noqa: E712
        ).first()
    return row or QueueGovernancePolicy(queue_name=queue_name, max_depth=settings.QUEUE_MAX_DEPTH_DEFAULT)


def check_queue_dispatch_allowed(
    session: Session,
    *,
    queue_name: str,
    owner_id: Optional[int] = None,
    estimated_depth: int = 0,
) -> None:
    if not settings.QUEUE_GOVERNANCE_ENABLE:
        return
    policy = queue_policy(session, queue_name, owner_id)
    if estimated_depth >= policy.max_depth:
        action = "reject" if settings.QUEUE_OVERLOAD_REJECT else "allow_with_overload_event"
        metrics.inc_queue_overload(queue_name, action)
        if settings.QUEUE_OVERLOAD_REJECT:
            raise RuntimeError(f"Queue {queue_name} is overloaded")


def utcnow() -> datetime:
    return datetime.utcnow()
