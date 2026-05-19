"""add autonomous runtime control loop tables

Revision ID: 0010_autonomous_runtime
Revises: 0009_predictive_runtime
Create Date: 2026-05-17 03:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_autonomous_runtime"
down_revision: Union[str, Sequence[str], None] = "0009_predictive_runtime"
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

    if "runtimecontrolloop" not in tables:
        op.create_table(
            "runtimecontrolloop",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("loop_name", sa.String(), nullable=False),
            sa.Column("loop_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("policy_json", sa.String(), nullable=False),
            sa.Column("last_run_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("runtimecontrolloop", {
            "ix_runtimecontrolloop_loop_name": ["loop_name"],
            "ix_runtimecontrolloop_loop_type": ["loop_type"],
            "ix_runtimecontrolloop_status": ["status"],
            "ix_runtimecontrolloop_last_run_at": ["last_run_at"],
            "ix_runtimecontrolloop_created_at": ["created_at"],
        })

    if "runtimeaction" not in tables:
        op.create_table(
            "runtimeaction",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("control_loop_id", sa.Integer(), nullable=True),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("action_type", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("action_json", sa.String(), nullable=False),
            sa.Column("guardrail_json", sa.String(), nullable=True),
            sa.Column("result_json", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["control_loop_id"], ["runtimecontrolloop.id"]),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("runtimeaction", {
            "ix_runtimeaction_control_loop_id": ["control_loop_id"],
            "ix_runtimeaction_owner_id": ["owner_id"],
            "ix_runtimeaction_action_type": ["action_type"],
            "ix_runtimeaction_queue_name": ["queue_name"],
            "ix_runtimeaction_status": ["status"],
            "ix_runtimeaction_created_at": ["created_at"],
        })

    if "runtimelearningsignal" not in tables:
        op.create_table(
            "runtimelearningsignal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("signal_type", sa.String(), nullable=False),
            sa.Column("strategy_name", sa.String(), nullable=True),
            sa.Column("workflow_version", sa.String(), nullable=True),
            sa.Column("queue_name", sa.String(), nullable=True),
            sa.Column("reward", sa.Float(), nullable=False),
            sa.Column("features_json", sa.String(), nullable=False),
            sa.Column("outcome_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("runtimelearningsignal", {
            "ix_runtimelearningsignal_owner_id": ["owner_id"],
            "ix_runtimelearningsignal_signal_type": ["signal_type"],
            "ix_runtimelearningsignal_strategy_name": ["strategy_name"],
            "ix_runtimelearningsignal_workflow_version": ["workflow_version"],
            "ix_runtimelearningsignal_queue_name": ["queue_name"],
            "ix_runtimelearningsignal_created_at": ["created_at"],
        })

    if "orchestrationstrategy" not in tables:
        op.create_table(
            "orchestrationstrategy",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("strategy_name", sa.String(), nullable=False),
            sa.Column("strategy_type", sa.String(), nullable=False),
            sa.Column("workflow_version", sa.String(), nullable=True),
            sa.Column("config_json", sa.String(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("orchestrationstrategy", {
            "ix_orchestrationstrategy_strategy_name": ["strategy_name"],
            "ix_orchestrationstrategy_strategy_type": ["strategy_type"],
            "ix_orchestrationstrategy_workflow_version": ["workflow_version"],
            "ix_orchestrationstrategy_is_active": ["is_active"],
            "ix_orchestrationstrategy_created_at": ["created_at"],
        })

    if "strategyoutcome" not in tables:
        op.create_table(
            "strategyoutcome",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("strategy_id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("processing_job_id", sa.Integer(), nullable=True),
            sa.Column("reward", sa.Float(), nullable=False),
            sa.Column("latency_delta_seconds", sa.Float(), nullable=False),
            sa.Column("cost_delta_usd", sa.Float(), nullable=False),
            sa.Column("reliability_delta", sa.Float(), nullable=False),
            sa.Column("outcome_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["processing_job_id"], ["processingjob.id"]),
            sa.ForeignKeyConstraint(["strategy_id"], ["orchestrationstrategy.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("strategyoutcome", {
            "ix_strategyoutcome_strategy_id": ["strategy_id"],
            "ix_strategyoutcome_owner_id": ["owner_id"],
            "ix_strategyoutcome_processing_job_id": ["processing_job_id"],
            "ix_strategyoutcome_created_at": ["created_at"],
        })

    if "concurrencytuningdecision" not in tables:
        op.create_table(
            "concurrencytuningdecision",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("current_concurrency", sa.Integer(), nullable=False),
            sa.Column("recommended_concurrency", sa.Integer(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("reason", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("concurrencytuningdecision", {
            "ix_concurrencytuningdecision_queue_name": ["queue_name"],
            "ix_concurrencytuningdecision_status": ["status"],
            "ix_concurrencytuningdecision_created_at": ["created_at"],
        })

    if "workerquarantine" not in tables:
        op.create_table(
            "workerquarantine",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("worker_name", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("reason", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("released_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("workerquarantine", {
            "ix_workerquarantine_worker_name": ["worker_name"],
            "ix_workerquarantine_queue_name": ["queue_name"],
            "ix_workerquarantine_status": ["status"],
            "ix_workerquarantine_created_at": ["created_at"],
        })

    if "dagmutationproposal" not in tables:
        op.create_table(
            "dagmutationproposal",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("workflow_name", sa.String(), nullable=False),
            sa.Column("source_version", sa.String(), nullable=False),
            sa.Column("proposed_version", sa.String(), nullable=False),
            sa.Column("mutation_type", sa.String(), nullable=False),
            sa.Column("proposal_json", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("dagmutationproposal", {
            "ix_dagmutationproposal_workflow_name": ["workflow_name"],
            "ix_dagmutationproposal_source_version": ["source_version"],
            "ix_dagmutationproposal_proposed_version": ["proposed_version"],
            "ix_dagmutationproposal_mutation_type": ["mutation_type"],
            "ix_dagmutationproposal_status": ["status"],
            "ix_dagmutationproposal_created_at": ["created_at"],
        })

    if "retrypolicyadaptation" not in tables:
        op.create_table(
            "retrypolicyadaptation",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("task_name", sa.String(), nullable=False),
            sa.Column("exception_type", sa.String(), nullable=False),
            sa.Column("current_policy_json", sa.String(), nullable=False),
            sa.Column("proposed_policy_json", sa.String(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("retrypolicyadaptation", {
            "ix_retrypolicyadaptation_task_name": ["task_name"],
            "ix_retrypolicyadaptation_exception_type": ["exception_type"],
            "ix_retrypolicyadaptation_status": ["status"],
            "ix_retrypolicyadaptation_created_at": ["created_at"],
        })

    if "autonomousrollback" not in tables:
        op.create_table(
            "autonomousrollback",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("action_id", sa.Integer(), nullable=True),
            sa.Column("rollback_type", sa.String(), nullable=False),
            sa.Column("reason", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("rollback_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["action_id"], ["runtimeaction.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("autonomousrollback", {
            "ix_autonomousrollback_action_id": ["action_id"],
            "ix_autonomousrollback_rollback_type": ["rollback_type"],
            "ix_autonomousrollback_status": ["status"],
            "ix_autonomousrollback_created_at": ["created_at"],
        })


def downgrade() -> None:
    for table_name in [
        "autonomousrollback",
        "retrypolicyadaptation",
        "dagmutationproposal",
        "workerquarantine",
        "concurrencytuningdecision",
        "strategyoutcome",
        "orchestrationstrategy",
        "runtimelearningsignal",
        "runtimeaction",
        "runtimecontrolloop",
    ]:
        if table_name in _tables():
            for index_name in _indexes(table_name):
                op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)
