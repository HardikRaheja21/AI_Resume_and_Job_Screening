from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlmodel import Session, func, select

from ..models import (
    OrchestrationRecommendation,
    PredictiveTelemetrySnapshot,
    ProcessingJob,
    RuntimePrediction,
    WorkerHeartbeat,
)
from ..utils import metrics
from ..utils.config import settings


def collect_queue_snapshot(
    session: Session,
    *,
    queue_name: str,
    owner_id: Optional[int] = None,
    window_seconds: int = 300,
) -> PredictiveTelemetrySnapshot:
    since = datetime.utcnow() - timedelta(seconds=window_seconds)
    query = select(ProcessingJob).where(ProcessingJob.queue_name == queue_name)
    if owner_id is not None:
        query = query.where(ProcessingJob.owner_id == owner_id)
    rows = session.exec(query.where(ProcessingJob.created_at >= since)).all()
    queued = len([row for row in rows if row.status == "queued"])
    running = len([row for row in rows if row.status == "running"])
    completed_rows = [row for row in rows if row.status == "completed" and row.completed_at]
    failed = len([row for row in rows if row.status == "failed"])
    latencies = [
        max(0.0, (row.completed_at - row.created_at).total_seconds())
        for row in completed_rows
        if row.completed_at
    ]
    sorted_latencies = sorted(latencies)
    p95 = sorted_latencies[int(max(0, len(sorted_latencies) - 1) * 0.95)] if sorted_latencies else 0.0
    avg = sum(latencies) / len(latencies) if latencies else 0.0
    workers = session.exec(select(WorkerHeartbeat).where(WorkerHeartbeat.queue_name == queue_name)).all()
    snapshot = PredictiveTelemetrySnapshot(
        owner_id=owner_id,
        queue_name=queue_name,
        window_seconds=window_seconds,
        queued_jobs=queued,
        running_jobs=running,
        completed_jobs=len(completed_rows),
        failed_jobs=failed,
        avg_latency_seconds=avg,
        p95_latency_seconds=p95,
        worker_count=len(workers),
        active_task_count=sum(int(worker.active_tasks or 0) for worker in workers),
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def predict_queue_congestion(
    session: Session,
    *,
    queue_name: str,
    owner_id: Optional[int] = None,
    horizon_seconds: Optional[int] = None,
) -> RuntimePrediction:
    horizon = horizon_seconds or settings.PREDICTION_HORIZON_SECONDS
    snapshot = collect_queue_snapshot(session, queue_name=queue_name, owner_id=owner_id, window_seconds=horizon)
    worker_capacity = max(1, snapshot.worker_count * 4)
    load = (snapshot.queued_jobs + snapshot.running_jobs) / worker_capacity
    failure_pressure = snapshot.failed_jobs / max(1, snapshot.completed_jobs + snapshot.failed_jobs)
    latency_pressure = snapshot.p95_latency_seconds / max(1, settings.WORKFLOW_SLA_SECONDS)
    predicted = max(0.0, min(1.0, (load * 0.5) + (latency_pressure * 0.35) + (failure_pressure * 0.15)))
    prediction = RuntimePrediction(
        owner_id=owner_id,
        queue_name=queue_name,
        prediction_type="queue_congestion",
        horizon_seconds=horizon,
        predicted_value=predicted,
        confidence=0.65,
        features_json=json.dumps(
            {
                "queued_jobs": snapshot.queued_jobs,
                "running_jobs": snapshot.running_jobs,
                "worker_count": snapshot.worker_count,
                "p95_latency_seconds": snapshot.p95_latency_seconds,
                "failure_pressure": failure_pressure,
            }
        ),
    )
    session.add(prediction)
    session.commit()
    session.refresh(prediction)
    metrics.inc_runtime_prediction("queue_congestion", queue_name)
    return prediction


def recommend_for_prediction(session: Session, prediction: RuntimePrediction) -> OrchestrationRecommendation:
    if prediction.predicted_value >= settings.QUEUE_CONGESTION_RISK_THRESHOLD:
        action = {
            "action": "scale_out",
            "queue_name": prediction.queue_name,
            "target_replicas_delta": 2,
            "reason": "predicted_queue_congestion",
        }
        recommendation_type = "autoscaling"
        priority = 2
    elif prediction.predicted_value >= 0.5:
        action = {
            "action": "prewarm_workers",
            "queue_name": prediction.queue_name,
            "reason": "moderate_congestion_risk",
        }
        recommendation_type = "prewarm"
        priority = 4
    else:
        action = {
            "action": "hold",
            "queue_name": prediction.queue_name,
            "reason": "risk_within_budget",
        }
        recommendation_type = "no_op"
        priority = 9
    recommendation = OrchestrationRecommendation(
        owner_id=prediction.owner_id,
        recommendation_type=recommendation_type,
        queue_name=prediction.queue_name,
        priority=priority,
        expected_impact_json=json.dumps(
            {
                "predicted_value": prediction.predicted_value,
                "confidence": prediction.confidence,
                "horizon_seconds": prediction.horizon_seconds,
            }
        ),
        action_json=json.dumps(action),
        source_prediction_id=prediction.id,
    )
    session.add(recommendation)
    session.commit()
    session.refresh(recommendation)
    metrics.inc_orchestration_recommendation(recommendation_type, recommendation.status)
    return recommendation


def queue_forecast_report(session: Session, *, queue_name: str, owner_id: Optional[int] = None) -> Dict[str, Any]:
    prediction = predict_queue_congestion(session, queue_name=queue_name, owner_id=owner_id)
    recommendation = recommend_for_prediction(session, prediction)
    return {
        "prediction": {
            "id": prediction.id,
            "queue_name": prediction.queue_name,
            "prediction_type": prediction.prediction_type,
            "predicted_value": prediction.predicted_value,
            "confidence": prediction.confidence,
            "horizon_seconds": prediction.horizon_seconds,
            "features": json.loads(prediction.features_json or "{}"),
        },
        "recommendation": {
            "id": recommendation.id,
            "recommendation_type": recommendation.recommendation_type,
            "priority": recommendation.priority,
            "action": json.loads(recommendation.action_json or "{}"),
            "expected_impact": json.loads(recommendation.expected_impact_json or "{}"),
        },
    }


def workload_pattern_summary(session: Session, *, owner_id: Optional[int] = None) -> Dict[str, Any]:
    query = select(ProcessingJob.queue_name, func.count(ProcessingJob.id)).group_by(ProcessingJob.queue_name)
    if owner_id is not None:
        query = query.where(ProcessingJob.owner_id == owner_id)
    rows = session.exec(query).all()
    return {"queues": [{"queue_name": row[0], "job_count": row[1]} for row in rows]}
