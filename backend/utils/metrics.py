try:
    from prometheus_client import Counter, Histogram
    _HAVE_PROM = True
except Exception:
    # prometheus_client may not be installed in some environments (tests)
    _HAVE_PROM = False


class _NoopMetric:
    def observe(self, *_, **__):
        return None

    def inc(self, *_, **__):
        return None


# Histograms (seconds)
if _HAVE_PROM:
    OCR_DURATION = Histogram(
        "resume_parser_ocr_duration_seconds",
        "OCR processing duration in seconds",
    )
    EMBEDDING_DURATION = Histogram(
        "resume_parser_embedding_duration_seconds",
        "Embedding generation duration in seconds",
    )
    SEMANTIC_RETRIEVAL_DURATION = Histogram(
        "resume_parser_semantic_retrieval_duration_seconds",
        "Semantic retrieval duration in seconds",
    )
    INTERVIEW_EVAL_DURATION = Histogram(
        "resume_parser_interview_evaluation_duration_seconds",
        "Interview evaluation duration in seconds",
    )
    RECRUITER_QUERY_DURATION = Histogram(
        "resume_parser_recruiter_query_duration_seconds",
        "Recruiter assistant query duration in seconds",
    )
    UPLOAD_PROCESSING_DURATION = Histogram(
        "resume_parser_upload_processing_duration_seconds",
        "Upload processing duration in seconds",
    )

    # Counters
    OCR_FALLBACKS = Counter(
        "resume_parser_ocr_fallbacks_total", "OCR fallbacks (not available or failed)"
    )
    EMBEDDING_DISABLED = Counter(
        "resume_parser_embedding_disabled_total", "Embeddings disabled fallbacks"
    )
    CHROMA_FALLBACKS = Counter(
        "resume_parser_chroma_fallbacks_total", "ChromaDB fallbacks or unavailable"
    )
    SPACY_FALLBACKS = Counter(
        "resume_parser_spacy_fallbacks_total", "spaCy fallbacks or unavailable"
    )
    BACKGROUND_TASKS_FAILED = Counter(
        "resume_parser_background_tasks_failed_total", "Background tasks failures"
    )
    PROCESSING_JOBS_TOTAL = Counter(
        "resume_parser_processing_jobs_total",
        "Processing jobs by type and status",
        ["job_type", "status"],
    )
    PROCESSING_STEP_DURATION = Histogram(
        "resume_parser_processing_step_duration_seconds",
        "Processing pipeline step duration in seconds",
        ["job_type", "step"],
    )
    PROCESSING_EVENTS_TOTAL = Counter(
        "resume_parser_processing_events_total",
        "Processing events emitted by step and status",
        ["step", "status"],
    )
    EMBEDDING_CACHE_HITS = Counter(
        "resume_parser_embedding_cache_hits_total",
        "Embedding cache hits",
    )
    EMBEDDING_CACHE_MISSES = Counter(
        "resume_parser_embedding_cache_misses_total",
        "Embedding cache misses",
    )
    WORKFLOW_REPLAYS_TOTAL = Counter(
        "resume_parser_workflow_replays_total",
        "Workflow replay requests by mode",
        ["mode"],
    )
    DLQ_EVENTS_TOTAL = Counter(
        "resume_parser_dead_letter_jobs_total",
        "Dead-letter jobs by source task and status",
        ["source_task", "status"],
    )
    AI_ARTIFACTS_TOTAL = Counter(
        "resume_parser_ai_artifacts_total",
        "AI artifacts by type, model, and governance status",
        ["artifact_type", "model_name", "governance_status"],
    )
    AI_ARTIFACT_LATENCY = Histogram(
        "resume_parser_ai_artifact_latency_seconds",
        "AI artifact generation latency",
        ["artifact_type", "model_name"],
    )
    QUEUE_DISPATCH_TOTAL = Counter(
        "resume_parser_queue_dispatch_total",
        "Tasks dispatched by queue and task name",
        ["queue_name", "task_name"],
    )
    FSM_TRANSITIONS_TOTAL = Counter(
        "resume_parser_fsm_transitions_total",
        "Workflow finite-state-machine transitions",
        ["from_state", "to_state", "valid"],
    )
    QUEUE_OVERLOAD_TOTAL = Counter(
        "resume_parser_queue_overload_total",
        "Queue overload protection events",
        ["queue_name", "action"],
    )
    AI_USAGE_COST = Counter(
        "resume_parser_ai_usage_cost_usd_total",
        "Estimated AI usage cost in USD",
        ["usage_type", "model_name"],
    )
    ORCHESTRATION_EVENTS_TOTAL = Counter(
        "resume_parser_orchestration_events_total",
        "Immutable orchestration events by type",
        ["event_type"],
    )
    POLICY_EVALUATIONS_TOTAL = Counter(
        "resume_parser_policy_evaluations_total",
        "Runtime policy evaluations",
        ["policy_type", "decision"],
    )
    ADAPTIVE_ROUTING_TOTAL = Counter(
        "resume_parser_adaptive_routing_total",
        "Adaptive queue routing decisions",
        ["from_queue", "to_queue", "reason"],
    )
    COMPLIANCE_ARTIFACTS_TOTAL = Counter(
        "resume_parser_compliance_artifacts_total",
        "AI compliance artifacts by type and status",
        ["artifact_type", "status"],
    )
    RUNTIME_PREDICTIONS_TOTAL = Counter(
        "resume_parser_runtime_predictions_total",
        "Runtime predictions by type and queue",
        ["prediction_type", "queue_name"],
    )
    ORCHESTRATION_RECOMMENDATIONS_TOTAL = Counter(
        "resume_parser_orchestration_recommendations_total",
        "Runtime recommendations by type and status",
        ["recommendation_type", "status"],
    )
    SIMULATION_RUNS_TOTAL = Counter(
        "resume_parser_simulation_runs_total",
        "Workflow simulation runs by scenario type and status",
        ["scenario_type", "status"],
    )
    AUTONOMOUS_ACTIONS_TOTAL = Counter(
        "resume_parser_autonomous_actions_total",
        "Autonomous runtime actions by type and status",
        ["action_type", "status"],
    )
    LEARNING_SIGNALS_TOTAL = Counter(
        "resume_parser_learning_signals_total",
        "Runtime learning signals by type",
        ["signal_type"],
    )
    WORKER_QUARANTINES_TOTAL = Counter(
        "resume_parser_worker_quarantines_total",
        "Worker quarantine events by queue and status",
        ["queue_name", "status"],
    )
    AGENT_MESSAGES_TOTAL = Counter(
        "resume_parser_agent_messages_total",
        "Runtime agent messages by type",
        ["message_type"],
    )
    CONSENSUS_DECISIONS_TOTAL = Counter(
        "resume_parser_consensus_decisions_total",
        "Agent consensus decisions by type and status",
        ["decision_type", "status"],
    )
    SAFETY_VERIFICATIONS_TOTAL = Counter(
        "resume_parser_safety_verifications_total",
        "Autonomous safety verifications by action type and status",
        ["action_type", "status"],
    )
else:
    OCR_DURATION = _NoopMetric()
    EMBEDDING_DURATION = _NoopMetric()
    SEMANTIC_RETRIEVAL_DURATION = _NoopMetric()
    INTERVIEW_EVAL_DURATION = _NoopMetric()
    RECRUITER_QUERY_DURATION = _NoopMetric()
    UPLOAD_PROCESSING_DURATION = _NoopMetric()

    OCR_FALLBACKS = _NoopMetric()
    EMBEDDING_DISABLED = _NoopMetric()
    CHROMA_FALLBACKS = _NoopMetric()
    SPACY_FALLBACKS = _NoopMetric()
    BACKGROUND_TASKS_FAILED = _NoopMetric()
    PROCESSING_JOBS_TOTAL = _NoopMetric()
    PROCESSING_STEP_DURATION = _NoopMetric()
    PROCESSING_EVENTS_TOTAL = _NoopMetric()
    EMBEDDING_CACHE_HITS = _NoopMetric()
    EMBEDDING_CACHE_MISSES = _NoopMetric()
    WORKFLOW_REPLAYS_TOTAL = _NoopMetric()
    DLQ_EVENTS_TOTAL = _NoopMetric()
    AI_ARTIFACTS_TOTAL = _NoopMetric()
    AI_ARTIFACT_LATENCY = _NoopMetric()
    QUEUE_DISPATCH_TOTAL = _NoopMetric()
    FSM_TRANSITIONS_TOTAL = _NoopMetric()
    QUEUE_OVERLOAD_TOTAL = _NoopMetric()
    AI_USAGE_COST = _NoopMetric()
    ORCHESTRATION_EVENTS_TOTAL = _NoopMetric()
    POLICY_EVALUATIONS_TOTAL = _NoopMetric()
    ADAPTIVE_ROUTING_TOTAL = _NoopMetric()
    COMPLIANCE_ARTIFACTS_TOTAL = _NoopMetric()
    RUNTIME_PREDICTIONS_TOTAL = _NoopMetric()
    ORCHESTRATION_RECOMMENDATIONS_TOTAL = _NoopMetric()
    SIMULATION_RUNS_TOTAL = _NoopMetric()
    AUTONOMOUS_ACTIONS_TOTAL = _NoopMetric()
    LEARNING_SIGNALS_TOTAL = _NoopMetric()
    WORKER_QUARANTINES_TOTAL = _NoopMetric()
    AGENT_MESSAGES_TOTAL = _NoopMetric()
    CONSENSUS_DECISIONS_TOTAL = _NoopMetric()
    SAFETY_VERIFICATIONS_TOTAL = _NoopMetric()

# Helper aliases for readability
observe_ocr_duration = OCR_DURATION.observe
observe_embedding_duration = EMBEDDING_DURATION.observe
observe_semantic_retrieval_duration = SEMANTIC_RETRIEVAL_DURATION.observe
observe_interview_eval_duration = INTERVIEW_EVAL_DURATION.observe
observe_recruiter_query_duration = RECRUITER_QUERY_DURATION.observe
observe_upload_processing_duration = UPLOAD_PROCESSING_DURATION.observe

inc_ocr_fallback = OCR_FALLBACKS.inc
inc_embedding_disabled = EMBEDDING_DISABLED.inc
inc_chroma_fallback = CHROMA_FALLBACKS.inc
inc_spacy_fallback = SPACY_FALLBACKS.inc
inc_background_tasks_failed = BACKGROUND_TASKS_FAILED.inc


def inc_processing_job(job_type: str, status: str) -> None:
    try:
        PROCESSING_JOBS_TOTAL.labels(job_type=job_type, status=status).inc()
    except Exception:
        pass


def observe_processing_step(job_type: str, step: str, seconds: float) -> None:
    try:
        PROCESSING_STEP_DURATION.labels(job_type=job_type, step=step).observe(seconds)
    except Exception:
        pass


def inc_processing_event(step: str, status: str) -> None:
    try:
        PROCESSING_EVENTS_TOTAL.labels(step=step, status=status).inc()
    except Exception:
        pass


def inc_embedding_cache_hit() -> None:
    try:
        EMBEDDING_CACHE_HITS.inc()
    except Exception:
        pass


def inc_embedding_cache_miss() -> None:
    try:
        EMBEDDING_CACHE_MISSES.inc()
    except Exception:
        pass


def inc_workflow_replay(mode: str) -> None:
    try:
        WORKFLOW_REPLAYS_TOTAL.labels(mode=mode).inc()
    except Exception:
        pass


def inc_dlq_event(source_task: str, status: str) -> None:
    try:
        DLQ_EVENTS_TOTAL.labels(source_task=source_task, status=status).inc()
    except Exception:
        pass


def inc_ai_artifact(artifact_type: str, model_name: str, governance_status: str) -> None:
    try:
        AI_ARTIFACTS_TOTAL.labels(
            artifact_type=artifact_type,
            model_name=model_name,
            governance_status=governance_status,
        ).inc()
    except Exception:
        pass


def observe_ai_artifact_latency(artifact_type: str, model_name: str, seconds: float) -> None:
    try:
        AI_ARTIFACT_LATENCY.labels(artifact_type=artifact_type, model_name=model_name).observe(seconds)
    except Exception:
        pass


def inc_queue_dispatch(queue_name: str, task_name: str) -> None:
    try:
        QUEUE_DISPATCH_TOTAL.labels(queue_name=queue_name, task_name=task_name).inc()
    except Exception:
        pass


def inc_fsm_transition(from_state: str, to_state: str, valid: bool) -> None:
    try:
        FSM_TRANSITIONS_TOTAL.labels(from_state=from_state, to_state=to_state, valid=str(valid).lower()).inc()
    except Exception:
        pass


def inc_queue_overload(queue_name: str, action: str) -> None:
    try:
        QUEUE_OVERLOAD_TOTAL.labels(queue_name=queue_name, action=action).inc()
    except Exception:
        pass


def inc_ai_usage_cost(usage_type: str, model_name: str, cost_usd: float) -> None:
    try:
        AI_USAGE_COST.labels(usage_type=usage_type, model_name=model_name).inc(max(0.0, cost_usd))
    except Exception:
        pass


def inc_orchestration_event(event_type: str) -> None:
    try:
        ORCHESTRATION_EVENTS_TOTAL.labels(event_type=event_type).inc()
    except Exception:
        pass


def inc_policy_evaluation(policy_type: str, decision: str) -> None:
    try:
        POLICY_EVALUATIONS_TOTAL.labels(policy_type=policy_type, decision=decision).inc()
    except Exception:
        pass


def inc_adaptive_routing(from_queue: str, to_queue: str, reason: str) -> None:
    try:
        ADAPTIVE_ROUTING_TOTAL.labels(from_queue=from_queue, to_queue=to_queue, reason=reason).inc()
    except Exception:
        pass


def inc_compliance_artifact(artifact_type: str, status: str) -> None:
    try:
        COMPLIANCE_ARTIFACTS_TOTAL.labels(artifact_type=artifact_type, status=status).inc()
    except Exception:
        pass


def inc_runtime_prediction(prediction_type: str, queue_name: str) -> None:
    try:
        RUNTIME_PREDICTIONS_TOTAL.labels(prediction_type=prediction_type, queue_name=queue_name).inc()
    except Exception:
        pass


def inc_orchestration_recommendation(recommendation_type: str, status: str) -> None:
    try:
        ORCHESTRATION_RECOMMENDATIONS_TOTAL.labels(
            recommendation_type=recommendation_type,
            status=status,
        ).inc()
    except Exception:
        pass


def inc_simulation_run(scenario_type: str, status: str) -> None:
    try:
        SIMULATION_RUNS_TOTAL.labels(scenario_type=scenario_type, status=status).inc()
    except Exception:
        pass


def inc_autonomous_action(action_type: str, status: str) -> None:
    try:
        AUTONOMOUS_ACTIONS_TOTAL.labels(action_type=action_type, status=status).inc()
    except Exception:
        pass


def inc_learning_signal(signal_type: str) -> None:
    try:
        LEARNING_SIGNALS_TOTAL.labels(signal_type=signal_type).inc()
    except Exception:
        pass


def inc_worker_quarantine(queue_name: str, status: str) -> None:
    try:
        WORKER_QUARANTINES_TOTAL.labels(queue_name=queue_name, status=status).inc()
    except Exception:
        pass


def inc_agent_message(message_type: str) -> None:
    try:
        AGENT_MESSAGES_TOTAL.labels(message_type=message_type).inc()
    except Exception:
        pass


def inc_consensus_decision(decision_type: str, status: str) -> None:
    try:
        CONSENSUS_DECISIONS_TOTAL.labels(decision_type=decision_type, status=status).inc()
    except Exception:
        pass


def inc_safety_verification(action_type: str, status: str) -> None:
    try:
        SAFETY_VERIFICATIONS_TOTAL.labels(action_type=action_type, status=status).inc()
    except Exception:
        pass
