"""add observability governance and replay tables

Revision ID: 0006_observability_governance
Revises: 0005_pipeline_decomposition
Create Date: 2026-05-17 01:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_observability_governance"
down_revision: Union[str, Sequence[str], None] = "0005_pipeline_decomposition"
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

    if "deadletterjob" not in tables:
        op.create_table(
            "deadletterjob",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("source_task", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("payload_json", sa.String(), nullable=True),
            sa.Column("exception_type", sa.String(), nullable=True),
            sa.Column("exception_message", sa.String(), nullable=True),
            sa.Column("traceback_ref", sa.String(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("replayed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "deadletterjob",
            {
                "ix_deadletterjob_processing_job_id": ["processing_job_id"],
                "ix_deadletterjob_owner_id": ["owner_id"],
                "ix_deadletterjob_resume_id": ["resume_id"],
                "ix_deadletterjob_source_task": ["source_task"],
                "ix_deadletterjob_queue_name": ["queue_name"],
                "ix_deadletterjob_status": ["status"],
                "ix_deadletterjob_created_at": ["created_at"],
            },
        )

    if "workflowreplay" not in tables:
        op.create_table(
            "workflowreplay",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_processing_job_id", sa.Integer(), nullable=False),
            sa.Column("replay_processing_job_id", sa.Integer(), nullable=True),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("replay_mode", sa.String(), nullable=False),
            sa.Column("reason", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["replay_processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["source_processing_job_id"], ["processingjob.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "workflowreplay",
            {
                "ix_workflowreplay_source_processing_job_id": ["source_processing_job_id"],
                "ix_workflowreplay_replay_processing_job_id": ["replay_processing_job_id"],
                "ix_workflowreplay_owner_id": ["owner_id"],
                "ix_workflowreplay_replay_mode": ["replay_mode"],
                "ix_workflowreplay_created_at": ["created_at"],
            },
        )

    if "aiartifact" not in tables:
        op.create_table(
            "aiartifact",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("job_id", sa.Integer(), nullable=True),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("artifact_type", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("prompt_version", sa.String(), nullable=False),
            sa.Column("prompt_hash", sa.String(), nullable=True),
            sa.Column("input_hash", sa.String(), nullable=True),
            sa.Column("output_hash", sa.String(), nullable=True),
            sa.Column("artifact_json", sa.String(), nullable=False),
            sa.Column("evidence_json", sa.String(), nullable=True),
            sa.Column("latency_ms", sa.Float(), nullable=True),
            sa.Column("token_count", sa.Integer(), nullable=True),
            sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
            sa.Column("governance_status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "aiartifact",
            {
                "ix_aiartifact_owner_id": ["owner_id"],
                "ix_aiartifact_resume_id": ["resume_id"],
                "ix_aiartifact_job_id": ["job_id"],
                "ix_aiartifact_processing_job_id": ["processing_job_id"],
                "ix_aiartifact_artifact_type": ["artifact_type"],
                "ix_aiartifact_provider": ["provider"],
                "ix_aiartifact_model_name": ["model_name"],
                "ix_aiartifact_prompt_version": ["prompt_version"],
                "ix_aiartifact_prompt_hash": ["prompt_hash"],
                "ix_aiartifact_input_hash": ["input_hash"],
                "ix_aiartifact_output_hash": ["output_hash"],
                "ix_aiartifact_governance_status": ["governance_status"],
                "ix_aiartifact_created_at": ["created_at"],
            },
        )

    if "retrievalevidence" not in tables:
        op.create_table(
            "retrievalevidence",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("job_id", sa.Integer(), nullable=True),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("artifact_id", sa.Integer(), nullable=True),
            sa.Column("query_hash", sa.String(), nullable=False),
            sa.Column("retriever_version", sa.String(), nullable=False),
            sa.Column("evidence_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["artifact_id"], ["aiartifact.id"]),
            sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "retrievalevidence",
            {
                "ix_retrievalevidence_owner_id": ["owner_id"],
                "ix_retrievalevidence_resume_id": ["resume_id"],
                "ix_retrievalevidence_job_id": ["job_id"],
                "ix_retrievalevidence_processing_job_id": ["processing_job_id"],
                "ix_retrievalevidence_artifact_id": ["artifact_id"],
                "ix_retrievalevidence_query_hash": ["query_hash"],
                "ix_retrievalevidence_retriever_version": ["retriever_version"],
                "ix_retrievalevidence_created_at": ["created_at"],
            },
        )

    if "vectorindexversion" not in tables:
        op.create_table(
            "vectorindexversion",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=False),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("vector_store", sa.String(), nullable=False),
            sa.Column("collection_name", sa.String(), nullable=False),
            sa.Column("embedding_model", sa.String(), nullable=False),
            sa.Column("schema_version", sa.String(), nullable=False),
            sa.Column("chunk_count", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes(
            "vectorindexversion",
            {
                "ix_vectorindexversion_owner_id": ["owner_id"],
                "ix_vectorindexversion_resume_id": ["resume_id"],
                "ix_vectorindexversion_processing_job_id": ["processing_job_id"],
                "ix_vectorindexversion_vector_store": ["vector_store"],
                "ix_vectorindexversion_collection_name": ["collection_name"],
                "ix_vectorindexversion_embedding_model": ["embedding_model"],
                "ix_vectorindexversion_schema_version": ["schema_version"],
                "ix_vectorindexversion_status": ["status"],
                "ix_vectorindexversion_created_at": ["created_at"],
            },
        )


def downgrade() -> None:
    for table_name in ["vectorindexversion", "retrievalevidence", "aiartifact", "workflowreplay", "deadletterjob"]:
        if table_name in _tables():
            for index_name in _indexes(table_name):
                op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)
