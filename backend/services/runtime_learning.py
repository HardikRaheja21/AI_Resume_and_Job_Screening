from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from ..models import (
    OrchestrationStrategy,
    RuntimeLearningSignal,
    StrategyOutcome,
)
from ..utils import metrics
from ..utils.config import settings


def reward_score(
    *,
    latency_delta_seconds: float = 0.0,
    cost_delta_usd: float = 0.0,
    reliability_delta: float = 0.0,
    sla_met: bool = True,
) -> float:
    reward = 0.0
    reward += max(-1.0, min(1.0, -latency_delta_seconds / 300.0)) * 0.35
    reward += max(-1.0, min(1.0, -cost_delta_usd)) * 0.2
    reward += max(-1.0, min(1.0, reliability_delta)) * 0.3
    reward += 0.15 if sla_met else -0.15
    return max(-1.0, min(1.0, reward))


def record_learning_signal(
    session: Session,
    *,
    signal_type: str,
    features: Dict[str, Any],
    outcome: Dict[str, Any],
    reward: float,
    owner_id: Optional[int] = None,
    strategy_name: Optional[str] = None,
    workflow_version: Optional[str] = None,
    queue_name: Optional[str] = None,
) -> RuntimeLearningSignal:
    row = RuntimeLearningSignal(
        owner_id=owner_id,
        signal_type=signal_type,
        strategy_name=strategy_name,
        workflow_version=workflow_version,
        queue_name=queue_name,
        reward=reward,
        features_json=json.dumps(features, default=str),
        outcome_json=json.dumps(outcome, default=str),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    metrics.inc_learning_signal(signal_type)
    return row


def get_or_create_strategy(
    session: Session,
    *,
    strategy_name: str,
    strategy_type: str,
    config: Dict[str, Any],
    workflow_version: Optional[str] = None,
) -> OrchestrationStrategy:
    row = session.exec(
        select(OrchestrationStrategy)
        .where(OrchestrationStrategy.strategy_name == strategy_name)
        .where(OrchestrationStrategy.strategy_type == strategy_type)
    ).first()
    if row:
        return row
    row = OrchestrationStrategy(
        strategy_name=strategy_name,
        strategy_type=strategy_type,
        workflow_version=workflow_version,
        config_json=json.dumps(config, default=str),
        score=0.0,
        confidence=0.1,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def record_strategy_outcome(
    session: Session,
    *,
    strategy: OrchestrationStrategy,
    outcome: Dict[str, Any],
    reward: float,
    owner_id: Optional[int] = None,
    processing_job_id: Optional[int] = None,
    latency_delta_seconds: float = 0.0,
    cost_delta_usd: float = 0.0,
    reliability_delta: float = 0.0,
) -> StrategyOutcome:
    row = StrategyOutcome(
        strategy_id=int(strategy.id or 0),
        owner_id=owner_id,
        processing_job_id=processing_job_id,
        reward=reward,
        latency_delta_seconds=latency_delta_seconds,
        cost_delta_usd=cost_delta_usd,
        reliability_delta=reliability_delta,
        outcome_json=json.dumps(outcome, default=str),
    )
    strategy.score = (strategy.score * (1 - settings.STRATEGY_LEARNING_RATE)) + (reward * settings.STRATEGY_LEARNING_RATE)
    strategy.confidence = min(1.0, strategy.confidence + 0.03)
    session.add(strategy)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def strategy_confidence(strategy: OrchestrationStrategy) -> float:
    return max(0.0, min(1.0, (strategy.confidence * 0.7) + (max(0.0, strategy.score) * 0.3)))
