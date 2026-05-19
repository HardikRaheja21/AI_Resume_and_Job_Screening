from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlmodel import Session, select

from ..models import RuntimeKnowledgeEdge, RuntimeKnowledgeNode


def upsert_node(
    session: Session,
    *,
    node_key: str,
    node_type: str,
    label: str,
    properties: Dict[str, Any],
    confidence: float = 0.5,
) -> RuntimeKnowledgeNode:
    row = session.exec(select(RuntimeKnowledgeNode).where(RuntimeKnowledgeNode.node_key == node_key)).first()
    if row:
        row.properties_json = json.dumps(properties, default=str)
        row.confidence = confidence
    else:
        row = RuntimeKnowledgeNode(
            node_key=node_key,
            node_type=node_type,
            label=label,
            properties_json=json.dumps(properties, default=str),
            confidence=confidence,
        )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def add_edge(
    session: Session,
    *,
    source_node_key: str,
    target_node_key: str,
    edge_type: str,
    weight: float = 1.0,
    evidence: Dict[str, Any] | None = None,
) -> RuntimeKnowledgeEdge:
    row = RuntimeKnowledgeEdge(
        source_node_key=source_node_key,
        target_node_key=target_node_key,
        edge_type=edge_type,
        weight=weight,
        evidence_json=json.dumps(evidence or {}, default=str),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def graph_neighborhood(session: Session, node_key: str, limit: int = 25) -> Dict[str, Any]:
    edges = session.exec(
        select(RuntimeKnowledgeEdge)
        .where((RuntimeKnowledgeEdge.source_node_key == node_key) | (RuntimeKnowledgeEdge.target_node_key == node_key))
        .limit(limit)
    ).all()
    node_keys = {node_key}
    for edge in edges:
        node_keys.add(edge.source_node_key)
        node_keys.add(edge.target_node_key)
    nodes = session.exec(select(RuntimeKnowledgeNode).where(RuntimeKnowledgeNode.node_key.in_(node_keys))).all()
    return {
        "nodes": [
            {
                "node_key": node.node_key,
                "node_type": node.node_type,
                "label": node.label,
                "properties": json.loads(node.properties_json or "{}"),
                "confidence": node.confidence,
            }
            for node in nodes
        ],
        "edges": [
            {
                "source": edge.source_node_key,
                "target": edge.target_node_key,
                "edge_type": edge.edge_type,
                "weight": edge.weight,
                "evidence": json.loads(edge.evidence_json or "{}"),
            }
            for edge in edges
        ],
    }


def mine_pattern_from_event(session: Session, *, event_type: str, queue_name: str, outcome: str) -> None:
    event_node = upsert_node(
        session,
        node_key=f"event:{event_type}",
        node_type="event_type",
        label=event_type,
        properties={"event_type": event_type},
        confidence=0.7,
    )
    queue_node = upsert_node(
        session,
        node_key=f"queue:{queue_name}",
        node_type="queue",
        label=queue_name,
        properties={"queue_name": queue_name},
        confidence=0.7,
    )
    outcome_node = upsert_node(
        session,
        node_key=f"outcome:{outcome}",
        node_type="outcome",
        label=outcome,
        properties={"outcome": outcome},
        confidence=0.7,
    )
    add_edge(session, source_node_key=event_node.node_key, target_node_key=queue_node.node_key, edge_type="observed_on")
    add_edge(session, source_node_key=queue_node.node_key, target_node_key=outcome_node.node_key, edge_type="led_to")
