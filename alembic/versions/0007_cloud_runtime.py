"""add cloud workflow runtime tables

Revision ID: 0007_cloud_runtime
Revises: 0006_observability_governance
Create Date: 2026-05-17 01:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_cloud_runtime"
down_revision: Union[str, Sequence[str], None] = "0006_observability_governance"
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

    if "workflowdefinition" not in tables:
        op.create_table(
            "workflowdefinition",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workflow_name", sa.String(), nullable=False),
            sa.Column("workflow_version", sa.String(), nullable=False),
            sa.Column("dag_json", sa.String(), nullable=False),
            sa.Column("state_machine_json", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "workflowdefinition",
            {
                "ix_workflowdefinition_workflow_name": ["workflow_name"],
                "ix_workflowdefinition_workflow_version": ["workflow_version"],
                "ix_workflowdefinition_is_active": ["is_active"],
                "ix_workflowdefinition_created_at": ["created_at"],
            },
        )

    if "workflowcheckpoint" not in tables:
        op.create_table(
            "workflowcheckpoint",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("processing_job_id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("checkpoint_name", sa.String(), nullable=False),
            sa.Column("workflow_version", sa.String(), nullable=False),
            sa.Column("state_json", sa.String(), nullable=False),
            sa.Column("trace_context_json", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "workflowcheckpoint",
            {
                "ix_workflowcheckpoint_processing_job_id": ["processing_job_id"],
                "ix_workflowcheckpoint_owner_id": ["owner_id"],
                "ix_workflowcheckpoint_resume_id": ["resume_id"],
                "ix_workflowcheckpoint_checkpoint_name": ["checkpoint_name"],
                "ix_workflowcheckpoint_workflow_version": ["workflow_version"],
                "ix_workflowcheckpoint_created_at": ["created_at"],
            },
        )

    if "queuegovernancepolicy" not in tables:
        op.create_table(
            "queuegovernancepolicy",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("max_depth", sa.Integer(), nullable=False),
            sa.Column("max_concurrency", sa.Integer(), nullable=False),
            sa.Column("max_dispatch_per_minute", sa.Integer(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "queuegovernancepolicy",
            {
                "ix_queuegovernancepolicy_owner_id": ["owner_id"],
                "ix_queuegovernancepolicy_queue_name": ["queue_name"],
                "ix_queuegovernancepolicy_is_active": ["is_active"],
                "ix_queuegovernancepolicy_created_at": ["created_at"],
            },
        )

    if "workerheartbeat" not in tables:
        op.create_table(
            "workerheartbeat",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("worker_name", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("active_tasks", sa.Integer(), nullable=False),
            sa.Column("max_concurrency", sa.Integer(), nullable=False),
            sa.Column("last_heartbeat_at", sa.DateTime(), nullable=False),
            sa.Column("detail_json", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "workerheartbeat",
            {
                "ix_workerheartbeat_worker_name": ["worker_name"],
                "ix_workerheartbeat_queue_name": ["queue_name"],
                "ix_workerheartbeat_status": ["status"],
                "ix_workerheartbeat_last_heartbeat_at": ["last_heartbeat_at"],
            },
        )

    if "aiusageledger" not in tables:
        op.create_table(
            "aiusageledger",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("job_id", sa.Integer(), nullable=True),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("artifact_id", sa.Integer(), nullable=True),
            sa.Column("usage_type", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("input_tokens", sa.Integer(), nullable=False),
            sa.Column("output_tokens", sa.Integer(), nullable=False),
            sa.Column("total_tokens", sa.Integer(), nullable=False),
            sa.Column("estimated_cost_usd", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["artifact_id"], ["aiartifact.id"]),
            sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "aiusageledger",
            {
                "ix_aiusageledger_owner_id": ["owner_id"],
                "ix_aiusageledger_resume_id": ["resume_id"],
                "ix_aiusageledger_job_id": ["job_id"],
                "ix_aiusageledger_processing_job_id": ["processing_job_id"],
                "ix_aiusageledger_artifact_id": ["artifact_id"],
                "ix_aiusageledger_usage_type": ["usage_type"],
                "ix_aiusageledger_provider": ["provider"],
                "ix_aiusageledger_model_name": ["model_name"],
                "ix_aiusageledger_created_at": ["created_at"],
            },
        )


def downgrade() -> None:
    for table_name in ["aiusageledger", "workerheartbeat", "queuegovernancepolicy", "workflowcheckpoint", "workflowdefinition"]:
        if table_name in _tables():
            for index_name in _indexes(table_name):
                op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)
