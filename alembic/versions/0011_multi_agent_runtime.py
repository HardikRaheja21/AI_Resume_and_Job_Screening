"""add multi-agent runtime intelligence tables

Revision ID: 0011_multi_agent_runtime
Revises: 0010_autonomous_runtime
Create Date: 2026-05-17 03:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_multi_agent_runtime"
down_revision: Union[str, Sequence[str], None] = "0010_autonomous_runtime"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _add_indexes(table_name: str, indexes: dict[str, list[str]]) -> None:
    existing = _indexes(table_name)
    for name, columns in indexes.items():
        if name not in existing:
            op.create_index(name, table_name, columns, unique=False)


def upgrade() -> None:
    tables = _tables()
    if "runtimeagent" not in tables:
        op.create_table(
            "runtimeagent",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("agent_name", sa.String(), nullable=False),
            sa.Column("agent_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("capabilities_json", sa.String(), nullable=False),
            sa.Column("policy_json", sa.String(), nullable=True),
            sa.Column("confidence_score", sa.Float(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_runtimeagent_agent_name", "runtimeagent", ["agent_name"], unique=True)
        _add_indexes("runtimeagent", {
            "ix_runtimeagent_agent_type": ["agent_type"],
            "ix_runtimeagent_status": ["status"],
            "ix_runtimeagent_last_seen_at": ["last_seen_at"],
            "ix_runtimeagent_created_at": ["created_at"],
        })

    if "agentmessage" not in tables:
        op.create_table(
            "agentmessage",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("conversation_id", sa.String(), nullable=False),
            sa.Column("sender_agent", sa.String(), nullable=False),
            sa.Column("receiver_agent", sa.String(), nullable=True),
            sa.Column("message_type", sa.String(), nullable=False),
            sa.Column("payload_json", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("agentmessage", {
            "ix_agentmessage_conversation_id": ["conversation_id"],
            "ix_agentmessage_sender_agent": ["sender_agent"],
            "ix_agentmessage_receiver_agent": ["receiver_agent"],
            "ix_agentmessage_message_type": ["message_type"],
            "ix_agentmessage_created_at": ["created_at"],
        })

    if "runtimeknowledgenode" not in tables:
        op.create_table(
            "runtimeknowledgenode",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("node_key", sa.String(), nullable=False),
            sa.Column("node_type", sa.String(), nullable=False),
            sa.Column("label", sa.String(), nullable=False),
            sa.Column("properties_json", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_runtimeknowledgenode_node_key", "runtimeknowledgenode", ["node_key"], unique=True)
        _add_indexes("runtimeknowledgenode", {
            "ix_runtimeknowledgenode_node_type": ["node_type"],
            "ix_runtimeknowledgenode_created_at": ["created_at"],
        })

    if "runtimeknowledgeedge" not in tables:
        op.create_table(
            "runtimeknowledgeedge",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_node_key", sa.String(), nullable=False),
            sa.Column("target_node_key", sa.String(), nullable=False),
            sa.Column("edge_type", sa.String(), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False),
            sa.Column("evidence_json", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("runtimeknowledgeedge", {
            "ix_runtimeknowledgeedge_source_node_key": ["source_node_key"],
            "ix_runtimeknowledgeedge_target_node_key": ["target_node_key"],
            "ix_runtimeknowledgeedge_edge_type": ["edge_type"],
            "ix_runtimeknowledgeedge_created_at": ["created_at"],
        })

    if "orchestrationreasoningtrace" not in tables:
        op.create_table(
            "orchestrationreasoningtrace",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("trace_id", sa.String(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("reasoning_type", sa.String(), nullable=False),
            sa.Column("input_json", sa.String(), nullable=False),
            sa.Column("steps_json", sa.String(), nullable=False),
            sa.Column("output_json", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_orchestrationreasoningtrace_trace_id", "orchestrationreasoningtrace", ["trace_id"], unique=True)
        _add_indexes("orchestrationreasoningtrace", {
            "ix_orchestrationreasoningtrace_owner_id": ["owner_id"],
            "ix_orchestrationreasoningtrace_reasoning_type": ["reasoning_type"],
            "ix_orchestrationreasoningtrace_created_at": ["created_at"],
        })

    if "agentconsensusdecision" not in tables:
        op.create_table(
            "agentconsensusdecision",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("decision_id", sa.String(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("decision_type", sa.String(), nullable=False),
            sa.Column("proposal_json", sa.String(), nullable=False),
            sa.Column("votes_json", sa.String(), nullable=False),
            sa.Column("consensus_score", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_agentconsensusdecision_decision_id", "agentconsensusdecision", ["decision_id"], unique=True)
        _add_indexes("agentconsensusdecision", {
            "ix_agentconsensusdecision_owner_id": ["owner_id"],
            "ix_agentconsensusdecision_decision_type": ["decision_type"],
            "ix_agentconsensusdecision_status": ["status"],
            "ix_agentconsensusdecision_created_at": ["created_at"],
        })

    if "safetyverification" not in tables:
        op.create_table(
            "safetyverification",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("action_type", sa.String(), nullable=False),
            sa.Column("subject_ref", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("risk_score", sa.Float(), nullable=False),
            sa.Column("checks_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("safetyverification", {
            "ix_safetyverification_owner_id": ["owner_id"],
            "ix_safetyverification_action_type": ["action_type"],
            "ix_safetyverification_subject_ref": ["subject_ref"],
            "ix_safetyverification_status": ["status"],
            "ix_safetyverification_created_at": ["created_at"],
        })

    if "experimentassignment" not in tables:
        op.create_table(
            "experimentassignment",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("experiment_name", sa.String(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("subject_key", sa.String(), nullable=False),
            sa.Column("variant", sa.String(), nullable=False),
            sa.Column("assignment_hash", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("experimentassignment", {
            "ix_experimentassignment_experiment_name": ["experiment_name"],
            "ix_experimentassignment_owner_id": ["owner_id"],
            "ix_experimentassignment_subject_key": ["subject_key"],
            "ix_experimentassignment_variant": ["variant"],
            "ix_experimentassignment_assignment_hash": ["assignment_hash"],
            "ix_experimentassignment_created_at": ["created_at"],
        })

    if "strategytournament" not in tables:
        op.create_table(
            "strategytournament",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tournament_name", sa.String(), nullable=False),
            sa.Column("strategy_type", sa.String(), nullable=False),
            sa.Column("candidates_json", sa.String(), nullable=False),
            sa.Column("winner_strategy", sa.String(), nullable=True),
            sa.Column("scorecard_json", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("strategytournament", {
            "ix_strategytournament_tournament_name": ["tournament_name"],
            "ix_strategytournament_strategy_type": ["strategy_type"],
            "ix_strategytournament_winner_strategy": ["winner_strategy"],
            "ix_strategytournament_status": ["status"],
            "ix_strategytournament_created_at": ["created_at"],
        })

    if "policyevolutionproposal" not in tables:
        op.create_table(
            "policyevolutionproposal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("policy_name", sa.String(), nullable=False),
            sa.Column("source_version", sa.String(), nullable=False),
            sa.Column("proposed_version", sa.String(), nullable=False),
            sa.Column("proposal_json", sa.String(), nullable=False),
            sa.Column("safety_status", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("policyevolutionproposal", {
            "ix_policyevolutionproposal_policy_name": ["policy_name"],
            "ix_policyevolutionproposal_source_version": ["source_version"],
            "ix_policyevolutionproposal_proposed_version": ["proposed_version"],
            "ix_policyevolutionproposal_safety_status": ["safety_status"],
            "ix_policyevolutionproposal_created_at": ["created_at"],
        })


def downgrade() -> None:
    for table_name in [
        "policyevolutionproposal",
        "strategytournament",
        "experimentassignment",
        "safetyverification",
        "agentconsensusdecision",
        "orchestrationreasoningtrace",
        "runtimeknowledgeedge",
        "runtimeknowledgenode",
        "agentmessage",
        "runtimeagent",
    ]:
        if table_name in _tables():
            for index_name in _indexes(table_name):
                op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)
