"""add processing job and event tables

Revision ID: 0004_processing_jobs
Revises: 0003_jobs_module
Create Date: 2026-05-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_processing_jobs"
down_revision: Union[str, Sequence[str], None] = "0003_jobs_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _indexes(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = _tables(inspector)

    if "processingjob" not in table_names:
        op.create_table(
            "processingjob",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("job_id", sa.Integer(), nullable=True),
            sa.Column("celery_task_id", sa.String(), nullable=True),
            sa.Column("job_type", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("current_step", sa.String(), nullable=False),
            sa.Column("progress", sa.Integer(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_retries", sa.Integer(), nullable=False),
            sa.Column("error_code", sa.String(), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.Column("result_json", sa.String(), nullable=True),
            sa.Column("input_json", sa.String(), nullable=True),
            sa.Column("request_id", sa.String(), nullable=True),
            sa.Column("locked_by", sa.String(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("failed_at", sa.DateTime(), nullable=True),
            sa.Column("next_retry_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for name, columns in {
            "ix_processingjob_owner_id": ["owner_id"],
            "ix_processingjob_resume_id": ["resume_id"],
            "ix_processingjob_job_id": ["job_id"],
            "ix_processingjob_celery_task_id": ["celery_task_id"],
            "ix_processingjob_job_type": ["job_type"],
            "ix_processingjob_queue_name": ["queue_name"],
            "ix_processingjob_status": ["status"],
            "ix_processingjob_priority": ["priority"],
            "ix_processingjob_request_id": ["request_id"],
            "ix_processingjob_created_at": ["created_at"],
        }.items():
            op.create_index(name, "processingjob", columns, unique=False)

    inspector = sa.inspect(bind)
    if "processingevent" not in _tables(inspector):
        op.create_table(
            "processingevent",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("processing_job_id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("step", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("message", sa.String(), nullable=True),
            sa.Column("detail_json", sa.String(), nullable=True),
            sa.Column("request_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for name, columns in {
            "ix_processingevent_processing_job_id": ["processing_job_id"],
            "ix_processingevent_owner_id": ["owner_id"],
            "ix_processingevent_resume_id": ["resume_id"],
            "ix_processingevent_event_type": ["event_type"],
            "ix_processingevent_step": ["step"],
            "ix_processingevent_status": ["status"],
            "ix_processingevent_request_id": ["request_id"],
            "ix_processingevent_created_at": ["created_at"],
        }.items():
            op.create_index(name, "processingevent", columns, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = _tables(inspector)

    if "processingevent" in table_names:
        for index_name in _indexes(inspector, "processingevent"):
            op.drop_index(index_name, table_name="processingevent")
        op.drop_table("processingevent")

    inspector = sa.inspect(bind)
    if "processingjob" in _tables(inspector):
        for index_name in _indexes(inspector, "processingjob"):
            op.drop_index(index_name, table_name="processingjob")
        op.drop_table("processingjob")
