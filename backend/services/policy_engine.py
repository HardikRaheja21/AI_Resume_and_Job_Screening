from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..models import ComplianceArtifact, RuntimePolicy
from ..utils import metrics
from ..utils.config import settings


def _matches_condition(context: Dict[str, Any], condition: Dict[str, Any]) -> bool:
    field = str(condition.get("field") or "")
    op = str(condition.get("op") or "eq")
    expected = condition.get("value")
    actual = context.get(field)
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "gte":
        return float(actual or 0) >= float(expected or 0)
    if op == "lte":
        return float(actual or 0) <= float(expected or 0)
    if op == "in":
        return actual in (expected or [])
    if op == "contains":
        return str(expected).lower() in str(actual or "").lower()
    return False


def evaluate_policies(
    session: Session,
    *,
    policy_type: str,
    context: Dict[str, Any],
    owner_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not settings.POLICY_ENGINE_ENABLE:
        return {"decision": "allow", "matched_policies": []}
    query = select(RuntimePolicy).where(RuntimePolicy.policy_type == policy_type).where(RuntimePolicy.is_active == True)  # noqa: E712
    rows = session.exec(query.order_by(RuntimePolicy.priority.asc())).all()
    matched: List[Dict[str, Any]] = []
    decision = "allow"
    for policy in rows:
        if policy.owner_id is not None and owner_id is not None and policy.owner_id != owner_id:
            continue
        try:
            rule = json.loads(policy.rule_json or "{}")
        except Exception:
            continue
        conditions = rule.get("when") or []
        if conditions and not all(_matches_condition(context, cond) for cond in conditions):
            continue
        action = rule.get("then", {}).get("action", "allow")
        matched.append({"policy_name": policy.policy_name, "action": action, "policy_version": policy.policy_version})
        if action in {"deny", "review", "throttle", "reroute"}:
            decision = action
            break
    metrics.inc_policy_evaluation(policy_type, decision)
    return {"decision": decision, "matched_policies": matched}


def record_compliance_artifact(
    session: Session,
    *,
    owner_id: int,
    artifact_type: str,
    status: str,
    details: Dict[str, Any],
    resume_id: Optional[int] = None,
    processing_job_id: Optional[int] = None,
    policy_version: str = "v1",
    risk_score: float = 0.0,
) -> ComplianceArtifact:
    artifact = ComplianceArtifact(
        owner_id=owner_id,
        resume_id=resume_id,
        processing_job_id=processing_job_id,
        artifact_type=artifact_type,
        policy_version=policy_version,
        status=status,
        risk_score=risk_score,
        details_json=json.dumps(details, default=str),
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    metrics.inc_compliance_artifact(artifact_type, status)
    return artifact


def evidence_sufficiency_score(evidence_count: int, required_count: int = 3) -> float:
    if required_count <= 0:
        return 1.0
    return max(0.0, min(1.0, evidence_count / required_count))


def hallucination_risk_score(*, evidence_score: float, generated_claim_count: int = 1) -> float:
    claim_factor = min(1.0, max(0.1, generated_claim_count / 10))
    return max(0.0, min(1.0, (1.0 - evidence_score) * claim_factor))
