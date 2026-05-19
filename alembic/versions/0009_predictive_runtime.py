"""add predictive runtime simulation and chaos tables

Revision ID: 0009_predictive_runtime
Revises: 0008_adaptive_runtime
Create Date: 2026-05-17 02:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_predictive_runtime"
down_revision: Union[str, Sequence[str], None] = "0008_adaptive_runtime"
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
    if "predictivetelemetrysnapshot" not in tables:
        op.create_table(
            "predictivetelemetrysnapshot",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("workflow_version", sa.String(), nullable=True),
            sa.Column("window_seconds", sa.Integer(), nullable=False),
            sa.Column("queued_jobs", sa.Integer(), nullable=False),
            sa.Column("running_jobs", sa.Integer(), nullable=False),
            sa.Column("completed_jobs", sa.Integer(), nullable=False),
            sa.Column("failed_jobs", sa.Integer(), nullable=False),
            sa.Column("avg_latency_seconds", sa.Float(), nullable=False),
            sa.Column("p95_latency_seconds", sa.Float(), nullable=False),
            sa.Column("worker_count", sa.Integer(), nullable=False),
            sa.Column("active_task_count", sa.Integer(), nullable=False),
            sa.Column("ai_cost_usd", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("predictivetelemetrysnapshot", {
            "ix_predictivetelemetrysnapshot_owner_id": ["owner_id"],
            "ix_predictivetelemetrysnapshot_queue_name": ["queue_name"],
            "ix_predictivetelemetrysnapshot_workflow_version": ["workflow_version"],
            "ix_predictivetelemetrysnapshot_created_at": ["created_at"],
        })

    if "runtimeprediction" not in tables:
        op.create_table(
            "runtimeprediction",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("queue_name", sa.String(), nullable=True),
            sa.Column("prediction_type", sa.String(), nullable=False),
            sa.Column("horizon_seconds", sa.Integer(), nullable=False),
            sa.Column("predicted_value", sa.Float(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("model_version", sa.String(), nullable=False),
            sa.Column("features_json", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("runtimeprediction", {
            "ix_runtimeprediction_owner_id": ["owner_id"],
            "ix_runtimeprediction_queue_name": ["queue_name"],
            "ix_runtimeprediction_prediction_type": ["prediction_type"],
            "ix_runtimeprediction_model_version": ["model_version"],
            "ix_runtimeprediction_created_at": ["created_at"],
        })

    if "orchestrationrecommendation" not in tables:
        op.create_table(
            "orchestrationrecommendation",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("recommendation_type", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=True),
            sa.Column("workflow_version", sa.String(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("expected_impact_json", sa.String(), nullable=False),
            sa.Column("action_json", sa.String(), nullable=False),
            sa.Column("source_prediction_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["source_prediction_id"], ["runtimeprediction.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("orchestrationrecommendation", {
            "ix_orchestrationrecommendation_owner_id": ["owner_id"],
            "ix_orchestrationrecommendation_recommendation_type": ["recommendation_type"],
            "ix_orchestrationrecommendation_queue_name": ["queue_name"],
            "ix_orchestrationrecommendation_workflow_version": ["workflow_version"],
            "ix_orchestrationrecommendation_priority": ["priority"],
            "ix_orchestrationrecommendation_status": ["status"],
            "ix_orchestrationrecommendation_source_prediction_id": ["source_prediction_id"],
            "ix_orchestrationrecommendation_created_at": ["created_at"],
        })

    if "simulationscenario" not in tables:
        op.create_table(
            "simulationscenario",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("scenario_name", sa.String(), nullable=False),
            sa.Column("scenario_type", sa.String(), nullable=False),
            sa.Column("workload_json", sa.String(), nullable=False),
            sa.Column("failure_injection_json", sa.String(), nullable=True),
            sa.Column("expected_sla_seconds", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("simulationscenario", {
            "ix_simulationscenario_owner_id": ["owner_id"],
            "ix_simulationscenario_scenario_name": ["scenario_name"],
            "ix_simulationscenario_scenario_type": ["scenario_type"],
            "ix_simulationscenario_created_at": ["created_at"],
        })

    if "simulationrun" not in tables:
        op.create_table(
            "simulationrun",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scenario_id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("result_json", sa.String(), nullable=False),
            sa.Column("resilience_score", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["scenario_id"], ["simulationscenario.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("simulationrun", {
            "ix_simulationrun_scenario_id": ["scenario_id"],
            "ix_simulationrun_owner_id": ["owner_id"],
            "ix_simulationrun_status": ["status"],
            "ix_simulationrun_created_at": ["created_at"],
        })

    if "chaosexperiment" not in tables:
        op.create_table(
            "chaosexperiment",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("experiment_name", sa.String(), nullable=False),
            sa.Column("target_queue", sa.String(), nullable=False),
            sa.Column("failure_mode", sa.String(), nullable=False),
            sa.Column("blast_radius_percent", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("hypothesis", sa.String(), nullable=True),
            sa.Column("result_json", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("chaosexperiment", {
            "ix_chaosexperiment_owner_id": ["owner_id"],
            "ix_chaosexperiment_experiment_name": ["experiment_name"],
            "ix_chaosexperiment_target_queue": ["target_queue"],
            "ix_chaosexperiment_failure_mode": ["failure_mode"],
            "ix_chaosexperiment_status": ["status"],
            "ix_chaosexperiment_created_at": ["created_at"],
        })

    if "workerefficiencysnapshot" not in tables:
        op.create_table(
            "workerefficiencysnapshot",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("worker_name", sa.String(), nullable=False),
            sa.Column("queue_name", sa.String(), nullable=False),
            sa.Column("throughput_per_minute", sa.Float(), nullable=False),
            sa.Column("failure_rate", sa.Float(), nullable=False),
            sa.Column("avg_task_latency_seconds", sa.Float(), nullable=False),
            sa.Column("efficiency_score", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        _add_indexes("workerefficiencysnapshot", {
            "ix_workerefficiencysnapshot_worker_name": ["worker_name"],
            "ix_workerefficiencysnapshot_queue_name": ["queue_name"],
            "ix_workerefficiencysnapshot_created_at": ["created_at"],
        })


def downgrade() -> None:
    for table_name in [
        "workerefficiencysnapshot",
        "chaosexperiment",
        "simulationrun",
        "simulationscenario",
        "orchestrationrecommendation",
        "runtimeprediction",
        "predictivetelemetrysnapshot",
    ]:
        if table_name in _tables():
            for index_name in _indexes(table_name):
                op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)
