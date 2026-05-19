from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlmodel import Session

from ..models import ChaosExperiment
from ..utils.config import settings


def plan_chaos_experiment(
    session: Session,
    *,
    experiment_name: str,
    target_queue: str,
    failure_mode: str,
    owner_id: Optional[int] = None,
    blast_radius_percent: float = 5.0,
    hypothesis: Optional[str] = None,
) -> ChaosExperiment:
    status = "planned" if settings.CHAOS_EXPERIMENTS_ENABLE else "disabled"
    experiment = ChaosExperiment(
        owner_id=owner_id,
        experiment_name=experiment_name,
        target_queue=target_queue,
        failure_mode=failure_mode,
        blast_radius_percent=blast_radius_percent,
        status=status,
        hypothesis=hypothesis,
        result_json=json.dumps(
            {
                "enabled": settings.CHAOS_EXPERIMENTS_ENABLE,
                "safety_note": "Chaos execution is plan-only unless CHAOS_EXPERIMENTS_ENABLE=true",
            }
        ),
    )
    session.add(experiment)
    session.commit()
    session.refresh(experiment)
    return experiment


def serialize_experiment(experiment: ChaosExperiment) -> Dict[str, Any]:
    return {
        "id": experiment.id,
        "experiment_name": experiment.experiment_name,
        "target_queue": experiment.target_queue,
        "failure_mode": experiment.failure_mode,
        "blast_radius_percent": experiment.blast_radius_percent,
        "status": experiment.status,
        "hypothesis": experiment.hypothesis,
        "result": json.loads(experiment.result_json or "{}"),
        "created_at": experiment.created_at,
    }
