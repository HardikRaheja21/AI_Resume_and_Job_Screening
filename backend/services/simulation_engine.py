from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlmodel import Session

from ..models import SimulationRun, SimulationScenario
from ..utils import metrics
from ..utils.config import settings


def create_synthetic_scenario(
    session: Session,
    *,
    scenario_name: str,
    owner_id: Optional[int] = None,
    workload_size: Optional[int] = None,
    queue_mix: Optional[Dict[str, float]] = None,
    failure_rate: float = 0.0,
    expected_sla_seconds: Optional[int] = None,
) -> SimulationScenario:
    workload = {
        "workload_size": workload_size or settings.SIMULATION_DEFAULT_WORKLOAD_SIZE,
        "queue_mix": queue_mix or {"default": 0.5, "embedding": 0.25, "ai": 0.2, "ocr": 0.05},
        "arrival_pattern": "burst",
    }
    scenario = SimulationScenario(
        owner_id=owner_id,
        scenario_name=scenario_name,
        scenario_type="synthetic_load",
        workload_json=json.dumps(workload),
        failure_injection_json=json.dumps({"failure_rate": failure_rate}),
        expected_sla_seconds=expected_sla_seconds or settings.WORKFLOW_SLA_SECONDS,
    )
    session.add(scenario)
    session.commit()
    session.refresh(scenario)
    return scenario


def run_simulation(session: Session, scenario: SimulationScenario) -> SimulationRun:
    workload = json.loads(scenario.workload_json or "{}")
    failure = json.loads(scenario.failure_injection_json or "{}")
    workload_size = int(workload.get("workload_size") or 0)
    failure_rate = float(failure.get("failure_rate") or 0.0)
    queue_mix = workload.get("queue_mix") or {}
    bottleneck_queue = max(queue_mix.items(), key=lambda item: item[1])[0] if queue_mix else "default"
    estimated_latency = workload_size * max(queue_mix.values() or [1.0]) * 1.5
    sla_risk = min(1.0, estimated_latency / max(1, scenario.expected_sla_seconds))
    resilience_score = max(0.0, min(1.0, 1.0 - ((failure_rate * 0.6) + (sla_risk * 0.4))))
    result = {
        "workload_size": workload_size,
        "bottleneck_queue": bottleneck_queue,
        "estimated_latency_seconds": round(estimated_latency, 2),
        "sla_risk": round(sla_risk, 3),
        "failure_rate": failure_rate,
        "recommendations": [
            {"action": "scale_out", "queue_name": bottleneck_queue, "reason": "simulation_bottleneck"},
            {"action": "prewarm_cache", "target": "embeddings", "reason": "bulk_workload"},
        ],
    }
    run = SimulationRun(
        scenario_id=int(scenario.id or 0),
        owner_id=scenario.owner_id,
        status="completed",
        result_json=json.dumps(result),
        resilience_score=resilience_score,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    metrics.inc_simulation_run(scenario.scenario_type, run.status)
    return run


def serialize_run(run: SimulationRun) -> Dict[str, Any]:
    return {
        "id": run.id,
        "scenario_id": run.scenario_id,
        "status": run.status,
        "resilience_score": run.resilience_score,
        "result": json.loads(run.result_json or "{}"),
        "created_at": run.created_at,
    }
