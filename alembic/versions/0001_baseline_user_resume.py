"""baseline user and resume schema

Revision ID: 0001_baseline_user_resume
Revises:
Create Date: 2026-03-05 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_baseline_user_resume"
down_revision: Union[str, Sequence[str], None] = None
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

    if "user" not in table_names:
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.Column("full_name", sa.String(), nullable=True),
            sa.Column("role", sa.String(), nullable=False, server_default="recruiter"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_user_email", "user", ["email"], unique=True)

    inspector = sa.inspect(bind)
    table_names = _get_table_names(inspector)
    if "resume" not in table_names:
        op.create_table(
            "resume",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(), nullable=False),
            sa.Column("filepath", sa.String(), nullable=False),
            sa.Column("parsed_text", sa.String(), nullable=True),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("phone", sa.String(), nullable=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("education", sa.String(), nullable=True),
            sa.Column("experience_years", sa.Float(), nullable=True),
            sa.Column("extracted_skills", sa.String(), nullable=True),
            sa.Column("feature_text", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("matched_job", sa.String(), nullable=True),
            sa.Column("match_score", sa.Float(), nullable=True),
            sa.Column("interview_score", sa.Float(), nullable=True),
            sa.Column("final_score", sa.Float(), nullable=True),
            sa.Column("final_decision", sa.String(), nullable=True),
            sa.Column("stage", sa.String(), nullable=False, server_default="new"),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("tags", sa.String(), nullable=True),
            sa.Column("is_starred", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("assigned_to_email", sa.String(), nullable=True),
            sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_resume_owner_id", "resume", ["owner_id"], unique=False)
    else:
        resume_columns = _get_column_names(inspector, "resume")
        alter_map = {
            "owner_id": sa.Column("owner_id", sa.Integer(), nullable=True),
            "phone": sa.Column("phone", sa.String(), nullable=True),
            "education": sa.Column("education", sa.String(), nullable=True),
            "experience_years": sa.Column("experience_years", sa.Float(), nullable=True),
            "extracted_skills": sa.Column("extracted_skills", sa.String(), nullable=True),
            "feature_text": sa.Column("feature_text", sa.String(), nullable=True),
            "updated_at": sa.Column("updated_at", sa.DateTime(), nullable=True),
            "stage": sa.Column("stage", sa.String(), nullable=True, server_default="new"),
            "interview_score": sa.Column("interview_score", sa.Float(), nullable=True),
            "final_score": sa.Column("final_score", sa.Float(), nullable=True),
            "final_decision": sa.Column("final_decision", sa.String(), nullable=True),
            "notes": sa.Column("notes", sa.String(), nullable=True),
            "tags": sa.Column("tags", sa.String(), nullable=True),
            "is_starred": sa.Column("is_starred", sa.Boolean(), nullable=True, server_default=sa.false()),
            "assigned_to_email": sa.Column("assigned_to_email", sa.String(), nullable=True),
            "duplicate_of_id": sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
        }
        for name, col in alter_map.items():
            if name not in resume_columns:
                op.add_column("resume", col)
        indexes = {idx["name"] for idx in inspector.get_indexes("resume")}
        if "ix_resume_owner_id" not in indexes:
            op.create_index("ix_resume_owner_id", "resume", ["owner_id"], unique=False)

    inspector_after = sa.inspect(bind)
    if "jobtemplate" not in _get_table_names(inspector_after):
        op.create_table(
            "jobtemplate",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("required_skills", sa.String(), nullable=True),
            sa.Column("optional_skills", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_jobtemplate_owner_id", "jobtemplate", ["owner_id"], unique=False)

    if "activitylog" not in _get_table_names(inspector_after):
        op.create_table(
            "activitylog",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("details", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_activitylog_owner_id", "activitylog", ["owner_id"], unique=False)
        op.create_index("ix_activitylog_resume_id", "activitylog", ["resume_id"], unique=False)

    inspector_after = sa.inspect(bind)
    if "interviewsession" not in _get_table_names(inspector_after):
        op.create_table(
            "interviewsession",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=False),
            sa.Column("job_description", sa.String(), nullable=False),
            sa.Column("question_plan_json", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("current_question_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("difficulty_level", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_questions", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("total_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("average_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("recommended_decision", sa.String(), nullable=True),
            sa.Column("input_modes_used", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_interviewsession_owner_id", "interviewsession", ["owner_id"], unique=False)
        op.create_index("ix_interviewsession_resume_id", "interviewsession", ["resume_id"], unique=False)

    inspector_after = sa.inspect(bind)
    if "interviewanswer" not in _get_table_names(inspector_after):
        op.create_table(
            "interviewanswer",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=False),
            sa.Column("question_index", sa.Integer(), nullable=False),
            sa.Column("question_text", sa.String(), nullable=False),
            sa.Column("answer_text", sa.String(), nullable=False),
            sa.Column("input_type", sa.String(), nullable=False, server_default="text"),
            sa.Column("expected_keywords", sa.String(), nullable=True),
            sa.Column("matched_keywords", sa.String(), nullable=True),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("feedback", sa.String(), nullable=True),
            sa.Column("difficulty_before", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("difficulty_after", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["interviewsession.id"]),
            sa.ForeignKeyConstraint(["resume_id"], ["resume.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_interviewanswer_session_id", "interviewanswer", ["session_id"], unique=False)
        op.create_index("ix_interviewanswer_resume_id", "interviewanswer", ["resume_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = _get_table_names(inspector)
    if "resume" in table_names:
        resume_columns = _get_column_names(inspector, "resume")
        indexes = {idx["name"] for idx in inspector.get_indexes("resume")}
        if "ix_resume_owner_id" in indexes:
            op.drop_index("ix_resume_owner_id", table_name="resume")
        if "owner_id" in resume_columns:
            op.drop_column("resume", "owner_id")
    if "jobtemplate" in table_names:
        indexes = {idx["name"] for idx in inspector.get_indexes("jobtemplate")}
        if "ix_jobtemplate_owner_id" in indexes:
            op.drop_index("ix_jobtemplate_owner_id", table_name="jobtemplate")
        op.drop_table("jobtemplate")
    if "activitylog" in table_names:
        indexes = {idx["name"] for idx in inspector.get_indexes("activitylog")}
        if "ix_activitylog_owner_id" in indexes:
            op.drop_index("ix_activitylog_owner_id", table_name="activitylog")
        if "ix_activitylog_resume_id" in indexes:
            op.drop_index("ix_activitylog_resume_id", table_name="activitylog")
        op.drop_table("activitylog")
    if "interviewanswer" in table_names:
        indexes = {idx["name"] for idx in inspector.get_indexes("interviewanswer")}
        if "ix_interviewanswer_session_id" in indexes:
            op.drop_index("ix_interviewanswer_session_id", table_name="interviewanswer")
        if "ix_interviewanswer_resume_id" in indexes:
            op.drop_index("ix_interviewanswer_resume_id", table_name="interviewanswer")
        op.drop_table("interviewanswer")
    if "interviewsession" in table_names:
        indexes = {idx["name"] for idx in inspector.get_indexes("interviewsession")}
        if "ix_interviewsession_owner_id" in indexes:
            op.drop_index("ix_interviewsession_owner_id", table_name="interviewsession")
        if "ix_interviewsession_resume_id" in indexes:
            op.drop_index("ix_interviewsession_resume_id", table_name="interviewsession")
        op.drop_table("interviewsession")
