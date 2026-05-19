from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..models import WorkflowDefinition
from ..utils.config import settings


DEFAULT_RESUME_WORKFLOW = {
    "workflow_name": "resume_intelligence",
    "workflow_version": "resume-dag-v1",
    "nodes": [
        {"id": "parse_extract", "task": "resume.pipeline.parse_extract", "queue": "default"},
        {"id": "match", "task": "resume.pipeline.match", "queue": "default", "depends_on": ["parse_extract"]},
        {"id": "embed_index", "task": "resume.pipeline.embed_index", "queue": "embedding", "depends_on": ["parse_extract"]},
        {"id": "merge_parallel", "task": "resume.pipeline.merge_parallel", "queue": "default", "depends_on": ["match", "embed_index"]},
        {"id": "generate_summary", "task": "resume.pipeline.generate_summary", "queue": "ai", "depends_on": ["merge_parallel"]},
        {"id": "finalize", "task": "resume.pipeline.finalize", "queue": "default", "depends_on": ["generate_summary"]},
    ],
}


def active_workflow_definition(
    session: Session,
    *,
    workflow_name: Optional[str] = None,
    workflow_version: Optional[str] = None,
) -> Dict[str, Any]:
    name = workflow_name or settings.DEFAULT_WORKFLOW_NAME
    version = workflow_version or settings.DEFAULT_WORKFLOW_VERSION
    row = session.exec(
        select(WorkflowDefinition)
        .where(WorkflowDefinition.workflow_name == name)
        .where(WorkflowDefinition.workflow_version == version)
        .where(WorkflowDefinition.is_active == True)  # noqa: E712
    ).first()
    if not row:
        return DEFAULT_RESUME_WORKFLOW
    try:
        return json.loads(row.dag_json)
    except Exception:
        return DEFAULT_RESUME_WORKFLOW


def compile_workflow(dag: Dict[str, Any], *, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = dag.get("nodes") or []
    node_ids = {node["id"] for node in nodes if node.get("id")}
    errors: List[str] = []
    levels: List[List[str]] = []
    remaining = {node["id"]: set(node.get("depends_on") or []) for node in nodes if node.get("id")}
    for node_id, deps in remaining.items():
        missing = deps - node_ids
        if missing:
            errors.append(f"{node_id} depends on unknown nodes: {sorted(missing)}")
    resolved: set[str] = set()
    while remaining and not errors:
        ready = sorted([node_id for node_id, deps in remaining.items() if deps.issubset(resolved)])
        if not ready:
            errors.append("Workflow DAG contains a cycle or unsatisfied dependency")
            break
        levels.append(ready)
        resolved.update(ready)
        for node_id in ready:
            remaining.pop(node_id, None)
    return {
        "workflow_name": dag.get("workflow_name", settings.DEFAULT_WORKFLOW_NAME),
        "workflow_version": dag.get("workflow_version", settings.DEFAULT_WORKFLOW_VERSION),
        "valid": not errors,
        "errors": errors,
        "execution_levels": levels,
        "node_count": len(nodes),
        "context": context or {},
    }
