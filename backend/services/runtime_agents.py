from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlmodel import Session, select

from ..models import AgentConsensusDecision, AgentMessage, OrchestrationReasoningTrace, RuntimeAgent
from ..services import knowledge_graph, safety_verifier
from ..utils import metrics
from ..utils.config import settings

DEFAULT_AGENTS = [
    ("coordinator", "coordinator", ["consensus", "routing", "approval"]),
    ("scaling_agent", "scaling", ["autoscaling", "prewarming"]),
    ("retry_agent", "retry", ["retry_policy", "failure_analysis"]),
    ("dag_agent", "dag_optimization", ["dag_mutation", "workflow_compilation"]),
    ("sla_agent", "sla_protection", ["sla_risk", "degradation"]),
    ("cost_agent", "cost", ["cost_budget", "model_tier"]),
    ("safety_agent", "safety", ["compliance", "verification"]),
    ("resilience_agent", "resilience", ["chaos", "quarantine", "rollback"]),
]


def ensure_default_agents(session: Session) -> List[RuntimeAgent]:
    agents: List[RuntimeAgent] = []
    for name, agent_type, capabilities in DEFAULT_AGENTS:
        row = session.exec(select(RuntimeAgent).where(RuntimeAgent.agent_name == name)).first()
        if not row:
            row = RuntimeAgent(
                agent_name=name,
                agent_type=agent_type,
                capabilities_json=json.dumps(capabilities),
                policy_json=json.dumps({"autonomy": "guarded"}),
                confidence_score=0.6,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
        agents.append(row)
    return agents


def send_message(
    session: Session,
    *,
    conversation_id: str,
    sender_agent: str,
    message_type: str,
    payload: Dict[str, Any],
    receiver_agent: Optional[str] = None,
    confidence: float = 0.5,
) -> AgentMessage:
    row = AgentMessage(
        conversation_id=conversation_id,
        sender_agent=sender_agent,
        receiver_agent=receiver_agent,
        message_type=message_type,
        payload_json=json.dumps(payload, default=str),
        confidence=confidence,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    metrics.inc_agent_message(message_type)
    return row


def agent_vote(agent: RuntimeAgent, proposal: Dict[str, Any]) -> Dict[str, Any]:
    action_type = proposal.get("action_type", "")
    capabilities = json.loads(agent.capabilities_json or "[]")
    support = 0.45
    if action_type in {"scale_out", "prewarm_workers"} and "autoscaling" in capabilities:
        support = 0.82
    elif action_type in {"retry_adaptation"} and "retry_policy" in capabilities:
        support = 0.8
    elif action_type in {"dag_mutation"} and "dag_mutation" in capabilities:
        support = 0.78
    elif action_type in {"policy_evolution", "dag_mutation"} and "verification" in capabilities:
        support = 0.65 if proposal.get("simulation_passed") else 0.25
    elif "compliance" in capabilities:
        support = 0.7 if proposal.get("risk_score", 0.0) <= settings.SAFETY_VERIFICATION_MAX_RISK else 0.2
    return {
        "agent": agent.agent_name,
        "agent_type": agent.agent_type,
        "support": support,
        "rationale": "capability_match" if support >= 0.65 else "limited_or_risky_match",
    }


def coordinate_decision(
    session: Session,
    *,
    decision_type: str,
    proposal: Dict[str, Any],
    owner_id: Optional[int] = None,
) -> Dict[str, Any]:
    agents = ensure_default_agents(session)
    conversation_id = str(uuid4())
    send_message(
        session,
        conversation_id=conversation_id,
        sender_agent="coordinator",
        receiver_agent=None,
        message_type="proposal",
        payload=proposal,
        confidence=float(proposal.get("confidence", 0.5)),
    )
    votes = [agent_vote(agent, proposal) for agent in agents]
    consensus_score = sum(vote["support"] for vote in votes) / max(1, len(votes))
    safety = safety_verifier.verify_action(
        session,
        owner_id=owner_id,
        action_type=str(proposal.get("action_type", decision_type)),
        proposal=proposal,
        subject_ref=proposal.get("subject_ref"),
    )
    status = "approved" if consensus_score >= settings.AGENT_CONSENSUS_MIN_SCORE and safety.status == "passed" else "needs_review"
    decision = AgentConsensusDecision(
        decision_id=str(uuid4()),
        owner_id=owner_id,
        decision_type=decision_type,
        proposal_json=json.dumps(proposal, default=str),
        votes_json=json.dumps(votes, default=str),
        consensus_score=consensus_score,
        status=status,
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)
    metrics.inc_consensus_decision(decision_type, status)
    trace = OrchestrationReasoningTrace(
        trace_id=str(uuid4()),
        owner_id=owner_id,
        reasoning_type="agent_consensus",
        input_json=json.dumps(proposal, default=str),
        steps_json=json.dumps({"votes": votes, "safety_status": safety.status}, default=str),
        output_json=json.dumps({"decision_id": decision.decision_id, "status": status}, default=str),
        confidence=consensus_score,
    )
    session.add(trace)
    session.commit()
    knowledge_graph.upsert_node(
        session,
        node_key=f"decision:{decision.decision_id}",
        node_type="consensus_decision",
        label=decision_type,
        properties={"status": status, "consensus_score": consensus_score},
        confidence=consensus_score,
    )
    return {
        "decision_id": decision.decision_id,
        "status": status,
        "consensus_score": consensus_score,
        "votes": votes,
        "safety": safety_verifier.serialize_verification(safety),
        "reasoning_trace_id": trace.trace_id,
    }


def list_agents(session: Session) -> List[Dict[str, Any]]:
    return [
        {
            "agent_name": row.agent_name,
            "agent_type": row.agent_type,
            "status": row.status,
            "capabilities": json.loads(row.capabilities_json or "[]"),
            "confidence_score": row.confidence_score,
        }
        for row in ensure_default_agents(session)
    ]
