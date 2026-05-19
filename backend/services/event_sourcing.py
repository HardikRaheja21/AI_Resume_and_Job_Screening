from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlmodel import Session, func, select

from ..models import OrchestrationEvent
from ..utils import metrics


def append_event(
    session: Session,
    *,
    stream_id: str,
    event_type: str,
    payload: Dict[str, Any],
    owner_id: Optional[int] = None,
    processing_job_id: Optional[int] = None,
    resume_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    event_version: str = "v1",
) -> OrchestrationEvent:
    max_sequence = session.exec(
        select(func.max(OrchestrationEvent.sequence_number)).where(OrchestrationEvent.stream_id == stream_id)
    ).one()
    next_sequence = int(max_sequence or 0) + 1
    event = OrchestrationEvent(
        event_id=str(uuid4()),
        stream_id=stream_id,
        owner_id=owner_id,
        processing_job_id=processing_job_id,
        resume_id=resume_id,
        event_type=event_type,
        event_version=event_version,
        sequence_number=next_sequence,
        payload_json=json.dumps(payload, default=str),
        metadata_json=json.dumps(metadata or {}, default=str),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    metrics.inc_orchestration_event(event_type)
    return event


def load_stream(session: Session, stream_id: str) -> List[Dict[str, Any]]:
    rows = session.exec(
        select(OrchestrationEvent)
        .where(OrchestrationEvent.stream_id == stream_id)
        .order_by(OrchestrationEvent.sequence_number.asc())
    ).all()
    return [serialize_event(row) for row in rows]


def serialize_event(event: OrchestrationEvent) -> Dict[str, Any]:
    return {
        "id": event.id,
        "event_id": event.event_id,
        "stream_id": event.stream_id,
        "owner_id": event.owner_id,
        "processing_job_id": event.processing_job_id,
        "resume_id": event.resume_id,
        "event_type": event.event_type,
        "event_version": event.event_version,
        "sequence_number": event.sequence_number,
        "payload": json.loads(event.payload_json or "{}"),
        "metadata": json.loads(event.metadata_json or "{}"),
        "created_at": event.created_at,
    }


def reconstruct_workflow_state(session: Session, stream_id: str) -> Dict[str, Any]:
    state: Dict[str, Any] = {"stream_id": stream_id, "events": [], "current_step": None, "status": "unknown"}
    for event in load_stream(session, stream_id):
        state["events"].append(event)
        payload = event.get("payload", {})
        if payload.get("status"):
            state["status"] = payload["status"]
        if payload.get("step"):
            state["current_step"] = payload["step"]
        if event["event_type"] == "workflow.completed":
            state["status"] = "completed"
        elif event["event_type"] == "workflow.failed":
            state["status"] = "failed"
    return state
