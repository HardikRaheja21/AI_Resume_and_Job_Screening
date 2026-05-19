"""add jobs table and link resumes to jobs

Revision ID: 0003_jobs_module
Revises: 0002_resume_match_explainability
Create Date: 2026-05-15 00:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_jobs_module"
down_revision: Union[str, Sequence[str], None] = "0002_resume_match_explainability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _get_column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = _get_table_names(inspector)

    if "job" not in table_names:
        op.create_table(
            "job",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=True),
            sa.Column("role_category", sa.String(), nullable=True),
            sa.Column("required_skills_json", sa.String(), nullable=True),
            sa.Column("optional_skills_json", sa.String(), nullable=True),
            sa.Column("keywords_json", sa.String(), nullable=True),
            sa.Column("education_requirements_json", sa.String(), nullable=True),
            sa.Column("minimum_experience_years", sa.Float(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_job_owner_id", "job", ["owner_id"], unique=False)

    inspector = sa.inspect(bind)
    if "resume" in _get_table_names(inspector):
        resume_columns = _get_column_names(inspector, "resume")
        if "job_id" not in resume_columns:
            op.add_column("resume", sa.Column("job_id", sa.Integer(), nullable=True))
            try:
                op.create_foreign_key("fk_resume_job_id_job", "resume", "job", ["job_id"], ["id"])
            except Exception:
                pass
            indexes = {idx["name"] for idx in inspector.get_indexes("resume")}
            if "ix_resume_job_id" not in indexes:
                op.create_index("ix_resume_job_id", "resume", ["job_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = _get_table_names(inspector)

    if "resume" in table_names:
        resume_columns = _get_column_names(inspector, "resume")
        indexes = {idx["name"] for idx in inspector.get_indexes("resume")}
        if "ix_resume_job_id" in indexes:
            op.drop_index("ix_resume_job_id", table_name="resume")
        if "job_id" in resume_columns:
            try:
                op.drop_constraint("fk_resume_job_id_job", "resume", type_="foreignkey")
            except Exception:
                pass
            op.drop_column("resume", "job_id")

    inspector = sa.inspect(bind)
    if "job" in _get_table_names(inspector):
        indexes = {idx["name"] for idx in inspector.get_indexes("job")}
        if "ix_job_owner_id" in indexes:
            op.drop_index("ix_job_owner_id", table_name="job")
        op.drop_table("job")
