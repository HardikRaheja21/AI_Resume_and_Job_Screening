from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlmodel import Session

from ..models import SafetyVerification
from ..utils import metrics
from ..utils.config import settings


def verify_action(
    session: Session,
    *,
    action_type: str,
    proposal: Dict[str, Any],
    owner_id: Optional[int] = None,
    subject_ref: Optional[str] = None,
) -> SafetyVerification:
    checks = []
    risk = 0.0
    if action_type in {"scale_out", "prewarm_workers"}:
        checks.append({"check": "reversible_action", "passed": True})
        risk += 0.1
    if action_type in {"dag_mutation", "policy_evolution"}:
        checks.append({"check": "requires_simulation", "passed": bool(proposal.get("simulation_passed"))})
        risk += 0.35 if not proposal.get("simulation_passed") else 0.15
    if action_type in {"worker_quarantine"}:
        checks.append({"check": "blast_radius_limited", "passed": True})
        risk += 0.2
    if not proposal.get("rollback_plan"):
        checks.append({"check": "rollback_plan_present", "passed": False})
        risk += 0.25
    else:
        checks.append({"check": "rollback_plan_present", "passed": True})
    status = "passed" if risk <= settings.SAFETY_VERIFICATION_MAX_RISK and all(item["passed"] for item in checks if item["check"] == "rollback_plan_present") else "needs_review"
    row = SafetyVerification(
        owner_id=owner_id,
        action_type=action_type,
        subject_ref=subject_ref,
        status=status,
        risk_score=min(1.0, risk),
        checks_json=json.dumps(checks, default=str),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    metrics.inc_safety_verification(action_type, status)
    return row


def serialize_verification(row: SafetyVerification) -> Dict[str, Any]:
    return {
        "id": row.id,
        "action_type": row.action_type,
        "subject_ref": row.subject_ref,
        "status": row.status,
        "risk_score": row.risk_score,
        "checks": json.loads(row.checks_json or "[]"),
        "created_at": row.created_at,
    }
