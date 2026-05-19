from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    role: str = Field(default="recruiter")
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Resume(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id", index=True)
    filename: str
    filepath: str
    parsed_text: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    education: Optional[str] = None
    experience_years: Optional[float] = None
    extracted_skills: Optional[str] = None
    feature_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    matched_job: Optional[str] = None
    match_score: Optional[float] = None
    role: Optional[str] = None
    role_category: Optional[str] = None
    required_skills_json: Optional[str] = None
    optional_skills_json: Optional[str] = None
    matched_skills_json: Optional[str] = None
    related_skills_json: Optional[str] = None
    missing_skills_json: Optional[str] = None
    jd_keywords_json: Optional[str] = None
    score_breakdown_json: Optional[str] = None
    jd_analysis_json: Optional[str] = None
    ai_evaluation_text: Optional[str] = None
    interview_score: Optional[float] = None
    final_score: Optional[float] = None
    final_decision: Optional[str] = None
    stage: str = Field(default="new")
    notes: Optional[str] = None
    tags: Optional[str] = None
    is_starred: bool = False
    assigned_to_email: Optional[str] = None
    duplicate_of_id: Optional[int] = None


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    title: str
    description: str
    role: Optional[str] = None
    role_category: Optional[str] = None
    required_skills_json: Optional[str] = None
    optional_skills_json: Optional[str] = None
    keywords_json: Optional[str] = None
    education_requirements_json: Optional[str] = None
    minimum_experience_years: Optional[float] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    title: str
    description: str
    required_skills: Optional[str] = None
    optional_skills: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ActivityLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, index=True)
    action: str
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: int = Field(foreign_key="resume.id", index=True)
    job_description: str
    question_plan_json: Optional[str] = None
    status: str = Field(default="active")
    current_question_index: int = 0
    difficulty_level: int = 1
    question_count: int = 0
    max_questions: int = 5
    total_score: float = 0.0
    average_score: float = 0.0
    recommended_decision: Optional[str] = None
    input_modes_used: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewAnswer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="interviewsession.id", index=True)
    resume_id: int = Field(foreign_key="resume.id", index=True)
    question_index: int
    question_text: str
    answer_text: str
    input_type: str = Field(default="text")
    expected_keywords: Optional[str] = None
    matched_keywords: Optional[str] = None
    score: float = 0.0
    feedback: Optional[str] = None
    difficulty_before: int = 1
    difficulty_after: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessingJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id", index=True)
    celery_task_id: Optional[str] = Field(default=None, index=True)
    job_type: str = Field(index=True)
    queue_name: str = Field(default="default", index=True)
    status: str = Field(default="queued", index=True)
    current_step: str = Field(default="queued")
    progress: int = Field(default=0)
    priority: int = Field(default=5, index=True)
    attempts: int = Field(default=0)
    max_retries: int = Field(default=3)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    result_json: Optional[str] = None
    input_json: Optional[str] = None
    request_id: Optional[str] = Field(default=None, index=True)
    locked_by: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessingEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    processing_job_id: int = Field(foreign_key="processingjob.id", index=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    event_type: str = Field(index=True)
    step: str = Field(index=True)
    status: str = Field(index=True)
    message: Optional[str] = None
    detail_json: Optional[str] = None
    request_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ProcessingSubtask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    processing_job_id: int = Field(foreign_key="processingjob.id", index=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    task_name: str = Field(index=True)
    queue_name: str = Field(index=True)
    celery_task_id: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="queued", index=True)
    attempt: int = Field(default=0)
    idempotency_key: str = Field(index=True)
    input_hash: Optional[str] = Field(default=None, index=True)
    output_json: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text_hash: str = Field(index=True)
    model_name: str = Field(index=True)
    vector_json: str
    dimensions: int
    usage_count: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)


class CandidateAISummary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: int = Field(foreign_key="resume.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    prompt_version: str = Field(index=True)
    model_name: str = Field(index=True)
    summary_json: str
    evidence_json: Optional[str] = None
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class MatchExplanation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: int = Field(foreign_key="resume.id", index=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    explanation_version: str = Field(index=True)
    score: float = 0.0
    explanation_json: str
    evidence_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class DeadLetterJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    source_task: str = Field(index=True)
    queue_name: str = Field(default="default", index=True)
    payload_json: Optional[str] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    traceback_ref: Optional[str] = None
    retry_count: int = 0
    status: str = Field(default="open", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    replayed_at: Optional[datetime] = None


class WorkflowReplay(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_processing_job_id: int = Field(foreign_key="processingjob.id", index=True)
    replay_processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    replay_mode: str = Field(default="from_failed_step", index=True)
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class AIArtifact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    artifact_type: str = Field(index=True)
    provider: str = Field(default="local", index=True)
    model_name: str = Field(index=True)
    prompt_version: str = Field(index=True)
    prompt_hash: Optional[str] = Field(default=None, index=True)
    input_hash: Optional[str] = Field(default=None, index=True)
    output_hash: Optional[str] = Field(default=None, index=True)
    artifact_json: str
    evidence_json: Optional[str] = None
    latency_ms: Optional[float] = None
    token_count: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    governance_status: str = Field(default="approved", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RetrievalEvidence(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    artifact_id: Optional[int] = Field(default=None, foreign_key="aiartifact.id", index=True)
    query_hash: str = Field(index=True)
    retriever_version: str = Field(index=True)
    evidence_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class VectorIndexVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: int = Field(foreign_key="resume.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    vector_store: str = Field(default="chroma", index=True)
    collection_name: str = Field(index=True)
    embedding_model: str = Field(index=True)
    schema_version: str = Field(index=True)
    chunk_count: int = 0
    status: str = Field(default="active", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class WorkflowDefinition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_name: str = Field(index=True)
    workflow_version: str = Field(index=True)
    dag_json: str
    state_machine_json: str
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class WorkflowCheckpoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    processing_job_id: int = Field(foreign_key="processingjob.id", index=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    checkpoint_name: str = Field(index=True)
    workflow_version: str = Field(index=True)
    state_json: str
    trace_context_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class QueueGovernancePolicy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    queue_name: str = Field(index=True)
    max_depth: int = 1000
    max_concurrency: int = 4
    max_dispatch_per_minute: int = 120
    priority: int = 5
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class WorkerHeartbeat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    worker_name: str = Field(index=True)
    queue_name: str = Field(index=True)
    status: str = Field(default="online", index=True)
    active_tasks: int = 0
    max_concurrency: int = 1
    last_heartbeat_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    detail_json: Optional[str] = None


class AIUsageLedger(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    artifact_id: Optional[int] = Field(default=None, foreign_key="aiartifact.id", index=True)
    usage_type: str = Field(index=True)
    provider: str = Field(default="local", index=True)
    model_name: str = Field(index=True)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class OrchestrationEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(index=True, unique=True)
    stream_id: str = Field(index=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    event_type: str = Field(index=True)
    event_version: str = Field(default="v1", index=True)
    sequence_number: int = Field(index=True)
    payload_json: str
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RuntimePolicy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    policy_name: str = Field(index=True)
    policy_type: str = Field(index=True)
    policy_version: str = Field(default="v1", index=True)
    rule_json: str
    priority: int = Field(default=100, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class TenantQuota(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    max_active_jobs: int = 25
    max_daily_jobs: int = 500
    max_ai_cost_usd_daily: float = 10.0
    priority_weight: float = 1.0
    burst_credits: int = 0
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class WorkflowExperiment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    experiment_name: str = Field(index=True)
    workflow_name: str = Field(index=True)
    control_version: str
    treatment_version: str
    traffic_percent: float = 0.0
    success_metric: str = "workflow_completed"
    guardrail_json: Optional[str] = None
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ComplianceArtifact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    resume_id: Optional[int] = Field(default=None, foreign_key="resume.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    artifact_type: str = Field(index=True)
    policy_version: str = Field(index=True)
    status: str = Field(default="passed", index=True)
    risk_score: float = 0.0
    details_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RuntimeOptimizationSignal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    signal_type: str = Field(index=True)
    queue_name: Optional[str] = Field(default=None, index=True)
    workflow_version: Optional[str] = Field(default=None, index=True)
    severity: str = Field(default="info", index=True)
    score: float = 0.0
    recommendation_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class PredictiveTelemetrySnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    queue_name: str = Field(index=True)
    workflow_version: Optional[str] = Field(default=None, index=True)
    window_seconds: int = 300
    queued_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    avg_latency_seconds: float = 0.0
    p95_latency_seconds: float = 0.0
    worker_count: int = 0
    active_task_count: int = 0
    ai_cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RuntimePrediction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    queue_name: Optional[str] = Field(default=None, index=True)
    prediction_type: str = Field(index=True)
    horizon_seconds: int = 300
    predicted_value: float
    confidence: float = 0.0
    model_version: str = Field(default="heuristic-v1", index=True)
    features_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class OrchestrationRecommendation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    recommendation_type: str = Field(index=True)
    queue_name: Optional[str] = Field(default=None, index=True)
    workflow_version: Optional[str] = Field(default=None, index=True)
    priority: int = Field(default=5, index=True)
    status: str = Field(default="open", index=True)
    expected_impact_json: str
    action_json: str
    source_prediction_id: Optional[int] = Field(default=None, foreign_key="runtimeprediction.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SimulationScenario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    scenario_name: str = Field(index=True)
    scenario_type: str = Field(default="synthetic_load", index=True)
    workload_json: str
    failure_injection_json: Optional[str] = None
    expected_sla_seconds: int = 300
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SimulationRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="simulationscenario.id", index=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    status: str = Field(default="completed", index=True)
    result_json: str
    resilience_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ChaosExperiment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    experiment_name: str = Field(index=True)
    target_queue: str = Field(index=True)
    failure_mode: str = Field(index=True)
    blast_radius_percent: float = 0.0
    status: str = Field(default="planned", index=True)
    hypothesis: Optional[str] = None
    result_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class WorkerEfficiencySnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    worker_name: str = Field(index=True)
    queue_name: str = Field(index=True)
    throughput_per_minute: float = 0.0
    failure_rate: float = 0.0
    avg_task_latency_seconds: float = 0.0
    efficiency_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RuntimeControlLoop(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    loop_name: str = Field(index=True)
    loop_type: str = Field(index=True)
    status: str = Field(default="active", index=True)
    policy_json: str
    last_run_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RuntimeAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    control_loop_id: Optional[int] = Field(default=None, foreign_key="runtimecontrolloop.id", index=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    action_type: str = Field(index=True)
    queue_name: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="proposed", index=True)
    confidence: float = 0.0
    action_json: str
    guardrail_json: Optional[str] = None
    result_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    executed_at: Optional[datetime] = None


class RuntimeLearningSignal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    signal_type: str = Field(index=True)
    strategy_name: Optional[str] = Field(default=None, index=True)
    workflow_version: Optional[str] = Field(default=None, index=True)
    queue_name: Optional[str] = Field(default=None, index=True)
    reward: float = 0.0
    features_json: str
    outcome_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class OrchestrationStrategy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_name: str = Field(index=True)
    strategy_type: str = Field(index=True)
    workflow_version: Optional[str] = Field(default=None, index=True)
    config_json: str
    score: float = 0.0
    confidence: float = 0.0
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class StrategyOutcome(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key="orchestrationstrategy.id", index=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    processing_job_id: Optional[int] = Field(default=None, foreign_key="processingjob.id", index=True)
    reward: float = 0.0
    latency_delta_seconds: float = 0.0
    cost_delta_usd: float = 0.0
    reliability_delta: float = 0.0
    outcome_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ConcurrencyTuningDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    queue_name: str = Field(index=True)
    current_concurrency: int
    recommended_concurrency: int
    confidence: float = 0.0
    reason: str
    status: str = Field(default="proposed", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class WorkerQuarantine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    worker_name: str = Field(index=True)
    queue_name: str = Field(index=True)
    reason: str
    status: str = Field(default="quarantined", index=True)
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    released_at: Optional[datetime] = None


class DagMutationProposal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_name: str = Field(index=True)
    source_version: str = Field(index=True)
    proposed_version: str = Field(index=True)
    mutation_type: str = Field(index=True)
    proposal_json: str
    confidence: float = 0.0
    status: str = Field(default="proposed", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RetryPolicyAdaptation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_name: str = Field(index=True)
    exception_type: str = Field(index=True)
    current_policy_json: str
    proposed_policy_json: str
    confidence: float = 0.0
    status: str = Field(default="proposed", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class AutonomousRollback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action_id: Optional[int] = Field(default=None, foreign_key="runtimeaction.id", index=True)
    rollback_type: str = Field(index=True)
    reason: str
    status: str = Field(default="planned", index=True)
    rollback_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    executed_at: Optional[datetime] = None


class RuntimeAgent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_name: str = Field(index=True, unique=True)
    agent_type: str = Field(index=True)
    status: str = Field(default="active", index=True)
    capabilities_json: str
    policy_json: Optional[str] = None
    confidence_score: float = 0.0
    last_seen_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class AgentMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: str = Field(index=True)
    sender_agent: str = Field(index=True)
    receiver_agent: Optional[str] = Field(default=None, index=True)
    message_type: str = Field(index=True)
    payload_json: str
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class RuntimeKnowledgeNode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    node_key: str = Field(index=True, unique=True)
    node_type: str = Field(index=True)
    label: str
    properties_json: str
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RuntimeKnowledgeEdge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_node_key: str = Field(index=True)
    target_node_key: str = Field(index=True)
    edge_type: str = Field(index=True)
    weight: float = 1.0
    evidence_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class OrchestrationReasoningTrace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trace_id: str = Field(index=True, unique=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    reasoning_type: str = Field(index=True)
    input_json: str
    steps_json: str
    output_json: str
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class AgentConsensusDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    decision_id: str = Field(index=True, unique=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    decision_type: str = Field(index=True)
    proposal_json: str
    votes_json: str
    consensus_score: float = 0.0
    status: str = Field(default="proposed", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SafetyVerification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    action_type: str = Field(index=True)
    subject_ref: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="passed", index=True)
    risk_score: float = 0.0
    checks_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ExperimentAssignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_name: str = Field(index=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    subject_key: str = Field(index=True)
    variant: str = Field(index=True)
    assignment_hash: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class StrategyTournament(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tournament_name: str = Field(index=True)
    strategy_type: str = Field(index=True)
    candidates_json: str
    winner_strategy: Optional[str] = Field(default=None, index=True)
    scorecard_json: Optional[str] = None
    status: str = Field(default="running", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class PolicyEvolutionProposal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    policy_name: str = Field(index=True)
    source_version: str = Field(index=True)
    proposed_version: str = Field(index=True)
    proposal_json: str
    safety_status: str = Field(default="pending", index=True)
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
