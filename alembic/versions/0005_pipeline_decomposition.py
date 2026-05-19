"""add pipeline decomposition and AI audit tables

Revision ID: 0005_pipeline_decomposition
Revises: 0004_processing_jobs
Create Date: 2026-05-17 00:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_pipeline_decomposition"
down_revision: Union[str, Sequence[str], None] = "0004_processing_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _create_indexes(table_name: str, indexes: dict[str, list[str]]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    for name, columns in indexes.items():
        if name not in existing:
            op.create_index(name, table_name, columns, unique=False)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = _tables(inspector)

    if "processingsubtask" not in table_names:
        op.create_table(
            "processingsubtask",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("processing_job_id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("task_name", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("celery_task_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("attempt", sa.Integer(), nullable=False),
            sa.Column("idempotency_key", sa.String(), nullable=False),
            sa.Column("input_hash", sa.String(), nullable=True),
            sa.Column("output_json", sa.String(), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_indexes(
            "processingsubtask",
            {
                "ix_processingsubtask_processing_job_id": ["processing_job_id"],
                "ix_processingsubtask_owner_id": ["owner_id"],
                "ix_processingsubtask_resume_id": ["resume_id"],
                "ix_processingsubtask_task_name": ["task_name"],
                "ix_processingsubtask_queue_name": ["queue_name"],
                "ix_processingsubtask_celery_task_id": ["celery_task_id"],
                "ix_processingsubtask_status": ["status"],
                "ix_processingsubtask_idempotency_key": ["idempotency_key"],
                "ix_processingsubtask_input_hash": ["input_hash"],
                "ix_processingsubtask_created_at": ["created_at"],
            },
        )

    if "embeddingcache" not in table_names:
        op.create_table(
            "embeddingcache",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("text_hash", sa.String(), nullable=False),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("vector_json", sa.String(), nullable=False),
            sa.Column("dimensions", sa.Integer(), nullable=False),
            sa.Column("usage_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_indexes(
            "embeddingcache",
            {
                "ix_embeddingcache_text_hash": ["text_hash"],
                "ix_embeddingcache_model_name": ["model_name"],
                "ix_embeddingcache_created_at": ["created_at"],
            },
        )

    if "candidateaisummary" not in table_names:
        op.create_table(
            "candidateaisummary",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=False),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("prompt_version", sa.String(), nullable=False),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("summary_json", sa.String(), nullable=False),
            sa.Column("evidence_json", sa.String(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_indexes(
            "candidateaisummary",
            {
                "ix_candidateaisummary_owner_id": ["owner_id"],
                "ix_candidateaisummary_resume_id": ["resume_id"],
                "ix_candidateaisummary_processing_job_id": ["processing_job_id"],
                "ix_candidateaisummary_prompt_version": ["prompt_version"],
                "ix_candidateaisummary_model_name": ["model_name"],
                "ix_candidateaisummary_created_at": ["created_at"],
            },
        )

    if "matchexplanation" not in table_names:
        op.create_table(
            "matchexplanation",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=True),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("explanation_version", sa.String(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("explanation_json", sa.String(), nullable=False),
            sa.Column("evidence_json", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_indexes(
            "matchexplanation",
            {
                "ix_matchexplanation_owner_id": ["owner_id"],
                "ix_matchexplanation_resume_id": ["resume_id"],
                "ix_matchexplanation_job_id": ["job_id"],
                "ix_matchexplanation_processing_job_id": ["processing_job_id"],
                "ix_matchexplanation_explanation_version": ["explanation_version"],
                "ix_matchexplanation_created_at": ["created_at"],
            },
        )


def downgrade() -> None:
    for table_name in ["matchexplanation", "candidateaisummary", "embeddingcache", "processingsubtask"]:
        inspector = sa.inspect(op.get_bind())
        if table_name in _tables(inspector):
            for index in inspector.get_indexes(table_name):
                op.drop_index(index["name"], table_name=table_name)
            op.drop_table(table_name)
