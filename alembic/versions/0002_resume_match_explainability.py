"""add resume explainability persistence fields

Revision ID: 0002_resume_match_explainability
Revises: 0001_baseline_user_resume
Create Date: 2026-05-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_resume_match_explainability"
down_revision: Union[str, Sequence[str], None] = "0001_baseline_user_resume"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "resume" not in table_names:
        return

    resume_columns = _get_column_names(inspector, "resume")
    alter_map = {
        "role": sa.Column("role", sa.String(), nullable=True),
        "role_category": sa.Column("role_category", sa.String(), nullable=True),
        "required_skills_json": sa.Column("required_skills_json", sa.String(), nullable=True),
        "optional_skills_json": sa.Column("optional_skills_json", sa.String(), nullable=True),
        "matched_skills_json": sa.Column("matched_skills_json", sa.String(), nullable=True),
        "related_skills_json": sa.Column("related_skills_json", sa.String(), nullable=True),
        "missing_skills_json": sa.Column("missing_skills_json", sa.String(), nullable=True),
        "jd_keywords_json": sa.Column("jd_keywords_json", sa.String(), nullable=True),
        "score_breakdown_json": sa.Column("score_breakdown_json", sa.String(), nullable=True),
        "jd_analysis_json": sa.Column("jd_analysis_json", sa.String(), nullable=True),
        "ai_evaluation_text": sa.Column("ai_evaluation_text", sa.String(), nullable=True),
    }
    for name, col in alter_map.items():
        if name not in resume_columns:
            op.add_column("resume", col)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "resume" not in table_names:
        return

    resume_columns = _get_column_names(inspector, "resume")
    for column_name in [
        "ai_evaluation_text",
        "jd_analysis_json",
        "score_breakdown_json",
        "jd_keywords_json",
        "missing_skills_json",
        "related_skills_json",
        "matched_skills_json",
        "optional_skills_json",
        "required_skills_json",
        "role_category",
        "role",
    ]:
        if column_name in resume_columns:
            op.drop_column("resume", column_name)
