from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from ..models import (
    AutonomousRollback,
    ConcurrencyTuningDecision,
    DagMutationProposal,
    OrchestrationRecommendation,
    RetryPolicyAdaptation,
    RuntimeAction,
    RuntimeControlLoop,
    WorkerEfficiencySnapshot,
    WorkerQuarantine,
)
from ..services import predictive_runtime, runtime_learning
from ..utils import metrics
from ..utils.config import settings


def confidence_for_recommendation(recommendation: OrchestrationRecommendation) -> float:
    try:
        impact = json.loads(recommendation.expected_impact_json or "{}")
    except Exception:
        impact = {}
    confidence = float(impact.get("confidence") or 0.0)
    predicted_value = float(impact.get("predicted_value") or 0.0)
    return max(0.0, min(1.0, (confidence * 0.6) + (predicted_value * 0.4)))


def propose_action_from_recommendation(
    session: Session,
    recommendation: OrchestrationRecommendation,
    *,
    control_loop_id: Optional[int] = None,
) -> RuntimeAction:
    try:
        action_payload = json.loads(recommendation.action_json or "{}")
    except Exception:
        action_payload = {"action": "manual_review"}
    action_type = str(action_payload.get("action") or recommendation.recommendation_type)
    confidence = confidence_for_recommendation(recommendation)
    status = "approved" if settings.AUTONOMOUS_RUNTIME_ENABLE and confidence >= settings.AUTONOMOUS_ACTION_MIN_CONFIDENCE else "proposed"
    guardrails = {
        "min_confidence": settings.AUTONOMOUS_ACTION_MIN_CONFIDENCE,
        "autonomous_enabled": settings.AUTONOMOUS_RUNTIME_ENABLE,
        "requires_guardrails": settings.AUTONOMOUS_REQUIRE_GUARDRAILS,
    }
    row = RuntimeAction(
        control_loop_id=control_loop_id,
        owner_id=recommendation.owner_id,
        action_type=action_type,
        queue_name=recommendation.queue_name,
        status=status,
        confidence=confidence,
        action_json=json.dumps(action_payload, default=str),
        guardrail_json=json.dumps(guardrails),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    metrics.inc_autonomous_action(action_type, status)
    return row


def execute_action(session: Session, action: RuntimeAction) -> RuntimeAction:
    if action.status not in {"approved", "proposed"}:
        return action
    if not settings.AUTONOMOUS_RUNTIME_ENABLE or action.confidence < settings.AUTONOMOUS_ACTION_MIN_CONFIDENCE:
        action.status = "requires_approval"
        session.add(action)
        session.commit()
        metrics.inc_autonomous_action(action.action_type, action.status)
        return action
    action.status = "executed"
    action.executed_at = datetime.utcnow()
    action.result_json = json.dumps({"executed": True, "mode": "recorded_control_action"})
    session.add(action)
    session.commit()
    metrics.inc_autonomous_action(action.action_type, action.status)
    return action


def run_control_loop(
    session: Session,
    *,
    queue_name: str = "default",
    owner_id: Optional[int] = None,
    loop_name: str = "queue_congestion_controller",
) -> Dict[str, Any]:
    loop = session.exec(select(RuntimeControlLoop).where(RuntimeControlLoop.loop_name == loop_name)).first()
    if not loop:
        loop = RuntimeControlLoop(
            loop_name=loop_name,
            loop_type="predictive_queue_control",
            policy_json=json.dumps({"queue_name": queue_name, "mode": "guarded"}),
        )
        session.add(loop)
        session.commit()
        session.refresh(loop)
    report = predictive_runtime.queue_forecast_report(session, queue_name=queue_name, owner_id=owner_id)
    recommendation = session.get(OrchestrationRecommendation, report["recommendation"]["id"])
    action = propose_action_from_recommendation(session, recommendation, control_loop_id=int(loop.id or 0))
    executed = execute_action(session, action)
    loop.last_run_at = datetime.utcnow()
    session.add(loop)
    session.commit()
    reward = runtime_learning.reward_score(
        latency_delta_seconds=-10 if executed.status == "executed" else 0,
        reliability_delta=0.05 if executed.status == "executed" else 0,
        sla_met=True,
    )
    runtime_learning.record_learning_signal(
        session,
        signal_type="control_loop_action",
        owner_id=owner_id,
        queue_name=queue_name,
        features=report["prediction"],
        outcome={"action_status": executed.status, "action_type": executed.action_type},
        reward=reward,
    )
    return {
        "control_loop_id": loop.id,
        "forecast": report,
        "action": serialize_action(executed),
        "reward": reward,
    }


def propose_concurrency_tuning(
    session: Session,
    *,
    queue_name: str,
    current_concurrency: int,
    congestion_score: float,
) -> ConcurrencyTuningDecision:
    delta = 1 if congestion_score >= settings.QUEUE_CONGESTION_RISK_THRESHOLD else -1 if congestion_score < 0.25 else 0
    delta = max(-settings.MAX_AUTONOMOUS_CONCURRENCY_DELTA, min(settings.MAX_AUTONOMOUS_CONCURRENCY_DELTA, delta))
    recommended = max(1, current_concurrency + delta)
    row = ConcurrencyTuningDecision(
        queue_name=queue_name,
        current_concurrency=current_concurrency,
        recommended_concurrency=recommended,
        confidence=min(1.0, abs(congestion_score - 0.5) + 0.4),
        reason="congestion_score_above_threshold" if delta > 0 else "low_utilization" if delta < 0 else "hold",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def quarantine_unhealthy_workers(session: Session, *, queue_name: Optional[str] = None) -> list[Dict[str, Any]]:
    query = select(WorkerEfficiencySnapshot)
    if queue_name:
        query = query.where(WorkerEfficiencySnapshot.queue_name == queue_name)
    snapshots = session.exec(query.order_by(WorkerEfficiencySnapshot.created_at.desc()).limit(50)).all()
    quarantines: list[Dict[str, Any]] = []
    seen = set()
    for snapshot in snapshots:
        if snapshot.worker_name in seen:
            continue
        seen.add(snapshot.worker_name)
        if snapshot.failure_rate >= settings.WORKER_QUARANTINE_FAILURE_RATE_THRESHOLD:
            row = WorkerQuarantine(
                worker_name=snapshot.worker_name,
                queue_name=snapshot.queue_name,
                reason="failure_rate_above_threshold",
                confidence=min(1.0, snapshot.failure_rate),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            metrics.inc_worker_quarantine(row.queue_name, row.status)
            quarantines.append({"worker_name": row.worker_name, "queue_name": row.queue_name, "status": row.status})
    return quarantines


def propose_dag_mutation(
    session: Session,
    *,
    workflow_name: str,
    source_version: str,
    mutation_type: str,
    proposal: Dict[str, Any],
    confidence: float,
) -> DagMutationProposal:
    row = DagMutationProposal(
        workflow_name=workflow_name,
        source_version=source_version,
        proposed_version=f"{source_version}-{mutation_type}",
        mutation_type=mutation_type,
        proposal_json=json.dumps(proposal, default=str),
        confidence=confidence,
        status="proposed",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def propose_retry_adaptation(
    session: Session,
    *,
    task_name: str,
    exception_type: str,
    current_policy: Dict[str, Any],
    proposed_policy: Dict[str, Any],
    confidence: float,
) -> RetryPolicyAdaptation:
    row = RetryPolicyAdaptation(
        task_name=task_name,
        exception_type=exception_type,
        current_policy_json=json.dumps(current_policy, default=str),
        proposed_policy_json=json.dumps(proposed_policy, default=str),
        confidence=confidence,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def plan_rollback(session: Session, *, action: RuntimeAction, reason: str) -> AutonomousRollback:
    row = AutonomousRollback(
        action_id=action.id,
        rollback_type=f"rollback_{action.action_type}",
        reason=reason,
        rollback_json=json.dumps({"action_id": action.id, "action_type": action.action_type}),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def serialize_action(action: RuntimeAction) -> Dict[str, Any]:
    return {
        "id": action.id,
        "action_type": action.action_type,
        "queue_name": action.queue_name,
        "status": action.status,
        "confidence": action.confidence,
        "action": json.loads(action.action_json or "{}"),
        "guardrails": json.loads(action.guardrail_json or "{}"),
        "result": json.loads(action.result_json or "{}") if action.result_json else {},
        "created_at": action.created_at,
        "executed_at": action.executed_at,
    }
