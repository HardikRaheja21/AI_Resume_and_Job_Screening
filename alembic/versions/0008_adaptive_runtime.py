"""add adaptive runtime intelligence tables

Revision ID: 0008_adaptive_runtime
Revises: 0007_cloud_runtime
Create Date: 2026-05-17 02:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_adaptive_runtime"
down_revision: Union[str, Sequence[str], None] = "0007_cloud_runtime"
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

    if "orchestrationevent" not in tables:
        op.create_table(
            "orchestrationevent",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_id", sa.String(), nullable=False),
            sa.Column("stream_id", sa.String(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("event_version", sa.String(), nullable=False),
            sa.Column("sequence_number", sa.Integer(), nullable=False),
            sa.Column("payload_json", sa.String(), nullable=False),
            sa.Column("metadata_json", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_orchestrationevent_event_id", "orchestrationevent", ["event_id"], unique=True)
        _add_indexes(
            "orchestrationevent",
            {
                "ix_orchestrationevent_stream_id": ["stream_id"],
                "ix_orchestrationevent_owner_id": ["owner_id"],
                "ix_orchestrationevent_processing_job_id": ["processing_job_id"],
                "ix_orchestrationevent_resume_id": ["resume_id"],
                "ix_orchestrationevent_event_type": ["event_type"],
                "ix_orchestrationevent_event_version": ["event_version"],
                "ix_orchestrationevent_sequence_number": ["sequence_number"],
                "ix_orchestrationevent_created_at": ["created_at"],
            },
        )

    if "runtimepolicy" not in tables:
        op.create_table(
            "runtimepolicy",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("policy_name", sa.String(), nullable=False),
            sa.Column("policy_type", sa.String(), nullable=False),
            sa.Column("policy_version", sa.String(), nullable=False),
            sa.Column("rule_json", sa.String(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("runtimepolicy", {
            "ix_runtimepolicy_owner_id": ["owner_id"],
            "ix_runtimepolicy_policy_name": ["policy_name"],
            "ix_runtimepolicy_policy_type": ["policy_type"],
            "ix_runtimepolicy_policy_version": ["policy_version"],
            "ix_runtimepolicy_priority": ["priority"],
            "ix_runtimepolicy_is_active": ["is_active"],
            "ix_runtimepolicy_created_at": ["created_at"],
        })

    if "tenantquota" not in tables:
        op.create_table(
            "tenantquota",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("max_active_jobs", sa.Integer(), nullable=False),
            sa.Column("max_daily_jobs", sa.Integer(), nullable=False),
            sa.Column("max_ai_cost_usd_daily", sa.Float(), nullable=False),
            sa.Column("priority_weight", sa.Float(), nullable=False),
            sa.Column("burst_credits", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("tenantquota", {
            "ix_tenantquota_owner_id": ["owner_id"],
            "ix_tenantquota_is_active": ["is_active"],
            "ix_tenantquota_created_at": ["created_at"],
        })

    if "workflowexperiment" not in tables:
        op.create_table(
            "workflowexperiment",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("experiment_name", sa.String(), nullable=False),
            sa.Column("workflow_name", sa.String(), nullable=False),
            sa.Column("control_version", sa.String(), nullable=False),
            sa.Column("treatment_version", sa.String(), nullable=False),
            sa.Column("traffic_percent", sa.Float(), nullable=False),
            sa.Column("success_metric", sa.String(), nullable=False),
            sa.Column("guardrail_json", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("workflowexperiment", {
            "ix_workflowexperiment_owner_id": ["owner_id"],
            "ix_workflowexperiment_experiment_name": ["experiment_name"],
            "ix_workflowexperiment_workflow_name": ["workflow_name"],
            "ix_workflowexperiment_is_active": ["is_active"],
            "ix_workflowexperiment_created_at": ["created_at"],
        })

    if "complianceartifact" not in tables:
        op.create_table(
            "complianceartifact",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("artifact_type", sa.String(), nullable=False),
            sa.Column("policy_version", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("risk_score", sa.Float(), nullable=False),
            sa.Column("details_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("complianceartifact", {
            "ix_complianceartifact_owner_id": ["owner_id"],
            "ix_complianceartifact_resume_id": ["resume_id"],
            "ix_complianceartifact_processing_job_id": ["processing_job_id"],
            "ix_complianceartifact_artifact_type": ["artifact_type"],
            "ix_complianceartifact_policy_version": ["policy_version"],
            "ix_complianceartifact_status": ["status"],
            "ix_complianceartifact_created_at": ["created_at"],
        })

    if "runtimeoptimizationsignal" not in tables:
        op.create_table(
            "runtimeoptimizationsignal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("signal_type", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=True),
            sa.Column("workflow_version", sa.String(), nullable=True),
            sa.Column("severity", sa.String(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("recommendation_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("runtimeoptimizationsignal", {
            "ix_runtimeoptimizationsignal_owner_id": ["owner_id"],
            "ix_runtimeoptimizationsignal_signal_type": ["signal_type"],
            "ix_runtimeoptimizationsignal_queue_name": ["queue_name"],
            "ix_runtimeoptimizationsignal_workflow_version": ["workflow_version"],
            "ix_runtimeoptimizationsignal_severity": ["severity"],
            "ix_runtimeoptimizationsignal_created_at": ["created_at"],
        })


def downgrade() -> None:
    for table_name in [
        "runtimeoptimizationsignal",
        "complianceartifact",
        "workflowexperiment",
        "tenantquota",
        "runtimepolicy",
        "orchestrationevent",
    ]:
        if table_name in _tables():
            for index_name in _indexes(table_name):
                op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)
