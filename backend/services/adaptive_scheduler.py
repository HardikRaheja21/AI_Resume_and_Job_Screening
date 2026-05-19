from __future__ import annotations

from typing import Any, Dict, Optional

from sqlmodel import Session, func, select

from ..models import ProcessingJob, RuntimeOptimizationSignal, TenantQuota
from ..services import workflow_runtime
from ..utils import metrics
from ..utils.config import settings


def tenant_quota(session: Session, owner_id: int) -> TenantQuota:
    row = session.exec(
        select(TenantQuota).where(TenantQuota.owner_id == owner_id).where(TenantQuota.is_active == True)  # noqa: E712
    ).first()
    return row or TenantQuota(owner_id=owner_id)


def tenant_active_jobs(session: Session, owner_id: int) -> int:
    return int(
        session.exec(
            select(func.count(ProcessingJob.id))
            .where(ProcessingJob.owner_id == owner_id)
            .where(ProcessingJob.status.in_(["queued", "running", "retrying"]))
        ).one()
        or 0
    )


def fairness_score(session: Session, owner_id: int) -> float:
    quota = tenant_quota(session, owner_id)
    active = tenant_active_jobs(session, owner_id)
    utilization = active / max(1, quota.max_active_jobs)
    return max(0.0, quota.priority_weight + (quota.burst_credits * 0.01) - utilization)


def route_queue(
    session: Session,
    *,
    base_queue: str,
    owner_id: int,
    sla_seconds: Optional[int] = None,
    estimated_depth: int = 0,
) -> Dict[str, Any]:
    selected = workflow_runtime.queue_name_for_owner(base_queue, owner_id)
    score = fairness_score(session, owner_id) if settings.TENANT_FAIRNESS_ENABLE else 1.0
    reason = "default"
    if sla_seconds is not None and sla_seconds < settings.WORKFLOW_SLA_SECONDS / 2 and base_queue != "critical":
        selected = workflow_runtime.queue_name_for_owner("critical", owner_id)
        reason = "sla_priority"
    elif score <= 0.0:
        reason = "fairness_throttle"
    workflow_runtime.check_queue_dispatch_allowed(
        session,
        queue_name=selected,
        owner_id=owner_id,
        estimated_depth=estimated_depth,
    )
    if selected != base_queue:
        metrics.inc_adaptive_routing(base_queue, selected, reason)
    return {"queue_name": selected, "fairness_score": score, "reason": reason}


def record_optimization_signal(
    session: Session,
    *,
    signal_type: str,
    recommendation: Dict[str, Any],
    owner_id: Optional[int] = None,
    queue_name: Optional[str] = None,
    workflow_version: Optional[str] = None,
    severity: str = "info",
    score: float = 0.0,
) -> RuntimeOptimizationSignal:
    import json

    row = RuntimeOptimizationSignal(
        owner_id=owner_id,
        signal_type=signal_type,
        queue_name=queue_name,
        workflow_version=workflow_version,
        severity=severity,
        score=score,
        recommendation_json=json.dumps(recommendation, default=str),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
