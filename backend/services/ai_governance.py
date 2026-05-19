from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from sqlmodel import Session

from ..models import AIArtifact, AIUsageLedger, RetrievalEvidence
from ..utils import metrics
from ..utils.config import settings


def _hash_json(value: Dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_ai_artifact(
    session: Session,
    *,
    owner_id: int,
    artifact_type: str,
    artifact: Dict[str, Any],
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
    processing_job_id: Optional[int] = None,
    provider: str = "local",
    model_name: Optional[str] = None,
    prompt_version: Optional[str] = None,
    prompt: Optional[Dict[str, Any]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    latency_ms: Optional[float] = None,
    token_count: Optional[int] = None,
    estimated_cost_usd: Optional[float] = None,
    governance_status: str = "approved",
) -> AIArtifact:
    selected_model = model_name or settings.OPENAI_MODEL
    selected_prompt_version = prompt_version or settings.AI_PROMPT_VERSION
    row = AIArtifact(
        owner_id=owner_id,
        resume_id=resume_id,
        job_id=job_id,
        processing_job_id=processing_job_id,
        artifact_type=artifact_type,
        provider=provider,
        model_name=selected_model,
        prompt_version=selected_prompt_version,
        prompt_hash=_hash_json(prompt or {"prompt_version": selected_prompt_version}),
        input_hash=_hash_json({"resume_id": resume_id, "job_id": job_id, "evidence": evidence or {}}),
        output_hash=_hash_json(artifact),
        artifact_json=json.dumps(artifact, default=str),
        evidence_json=json.dumps(evidence or {}, default=str),
        latency_ms=latency_ms,
        token_count=token_count,
        estimated_cost_usd=estimated_cost_usd,
        governance_status=governance_status,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    metrics.inc_ai_artifact(artifact_type, selected_model, governance_status)
    if latency_ms is not None:
        metrics.observe_ai_artifact_latency(artifact_type, selected_model, latency_ms / 1000.0)
    total_tokens = int(token_count or 0)
    estimated_cost = float(estimated_cost_usd or 0.0)
    session.add(
        AIUsageLedger(
            owner_id=owner_id,
            resume_id=resume_id,
            job_id=job_id,
            processing_job_id=processing_job_id,
            artifact_id=int(row.id or 0),
            usage_type=artifact_type,
            provider=provider,
            model_name=selected_model,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
        )
    )
    session.commit()
    metrics.inc_ai_usage_cost(artifact_type, selected_model, estimated_cost)
    return row


def record_retrieval_evidence(
    session: Session,
    *,
    owner_id: int,
    query: str,
    retriever_version: str,
    evidence: Dict[str, Any],
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
    processing_job_id: Optional[int] = None,
    artifact_id: Optional[int] = None,
) -> RetrievalEvidence:
    row = RetrievalEvidence(
        owner_id=owner_id,
        resume_id=resume_id,
        job_id=job_id,
        processing_job_id=processing_job_id,
        artifact_id=artifact_id,
        query_hash=hashlib.sha256((query or "").encode("utf-8")).hexdigest(),
        retriever_version=retriever_version,
        evidence_json=json.dumps(evidence, default=str),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
