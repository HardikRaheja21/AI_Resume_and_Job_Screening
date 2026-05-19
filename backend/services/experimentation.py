from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from ..models import ExperimentAssignment, PolicyEvolutionProposal, StrategyTournament


def assign_variant(
    session: Session,
    *,
    experiment_name: str,
    subject_key: str,
    variants: List[str],
    traffic_percent: float,
    owner_id: Optional[int] = None,
) -> ExperimentAssignment:
    digest = hashlib.sha256(f"{experiment_name}:{subject_key}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    variant = variants[1] if len(variants) > 1 and bucket < traffic_percent else variants[0]
    row = ExperimentAssignment(
        experiment_name=experiment_name,
        owner_id=owner_id,
        subject_key=subject_key,
        variant=variant,
        assignment_hash=digest,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def run_strategy_tournament(
    session: Session,
    *,
    tournament_name: str,
    strategy_type: str,
    candidates: List[Dict[str, Any]],
) -> StrategyTournament:
    scorecard = []
    for candidate in candidates:
        score = (
            float(candidate.get("reliability", 0.5)) * 0.4
            + float(candidate.get("latency_score", 0.5)) * 0.25
            + float(candidate.get("cost_score", 0.5)) * 0.2
            + float(candidate.get("safety_score", 0.5)) * 0.15
        )
        scorecard.append({"strategy": candidate.get("strategy"), "score": score})
    winner = max(scorecard, key=lambda item: item["score"])["strategy"] if scorecard else None
    row = StrategyTournament(
        tournament_name=tournament_name,
        strategy_type=strategy_type,
        candidates_json=json.dumps(candidates, default=str),
        winner_strategy=winner,
        scorecard_json=json.dumps(scorecard, default=str),
        status="completed",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def propose_policy_evolution(
    session: Session,
    *,
    policy_name: str,
    source_version: str,
    proposed_version: str,
    proposal: Dict[str, Any],
    confidence: float,
) -> PolicyEvolutionProposal:
    row = PolicyEvolutionProposal(
        policy_name=policy_name,
        source_version=source_version,
        proposed_version=proposed_version,
        proposal_json=json.dumps(proposal, default=str),
        confidence=confidence,
        safety_status="pending",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
