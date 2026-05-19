from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database import get_session
from ..models import Job, ProcessingJob, Resume, User
from ..resume_parser_service import parser as resume_parser
from ..services import (
    adaptive_scheduler,
    autonomous_controller,
    chaos_engine,
    event_sourcing,
    experimentation,
    knowledge_graph,
    policy_engine,
    predictive_runtime,
    processing_service,
    realtime_events,
    runtime_agents,
    simulation_engine,
    workflow_compiler,
)
from ..utils.auth_deps import get_current_user
from ..utils.config import settings
from ..workers.tasks.decomposed_pipeline import dispatch_parallel_resume_pipeline, dispatch_resume_pipeline

router = APIRouter(prefix="/processing", tags=["processing"])

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt"}
ALLOWED_MIME_TYPES_BY_EXTENSION = {
    "pdf": {"application/pdf"},
    "doc": {"application/msword", "application/octet-stream"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    "txt": {"text/plain", "application/octet-stream"},
}


class ProcessingJobRead(BaseModel):
    id: int
    owner_id: int
    resume_id: Optional[int] = None
    job_id: Optional[int] = None
    celery_task_id: Optional[str] = None
    job_type: str
    queue_name: str
    status: str
    current_step: str
    progress: int
    priority: int
    attempts: int
    max_retries: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
    started_at: Optional[Any] = None
    completed_at: Optional[Any] = None
    failed_at: Optional[Any] = None
    created_at: Any
    updated_at: Any


class ProcessingEventRead(BaseModel):
    id: int
    processing_job_id: int
    event_type: str
    step: str
    status: str
    message: Optional[str] = None
    detail: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
    created_at: Any


class ProcessingSubtaskRead(BaseModel):
    id: int
    processing_job_id: int
    resume_id: Optional[int] = None
    task_name: str
    queue_name: str
    celery_task_id: Optional[str] = None
    status: str
    attempt: int
    idempotency_key: str
    input_hash: Optional[str] = None
    output: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[Any] = None
    completed_at: Optional[Any] = None
    created_at: Any
    updated_at: Any


class AsyncUploadResponse(BaseModel):
    batch_job_id: Optional[str] = None
    total_resumes: int
    jobs: List[ProcessingJobRead]


class EnqueueResumeResponse(BaseModel):
    processing_job: ProcessingJobRead


class ReplayJobRequest(BaseModel):
    replay_mode: str = "from_failed_step"
    reason: Optional[str] = None


class ReplayJobResponse(BaseModel):
    source_job_id: int
    replay_job: ProcessingJobRead


class SimulationScenarioRequest(BaseModel):
    scenario_name: str
    workload_size: Optional[int] = None
    queue_mix: Optional[Dict[str, float]] = None
    failure_rate: float = 0.0
    expected_sla_seconds: Optional[int] = None


class ChaosExperimentRequest(BaseModel):
    experiment_name: str
    target_queue: str
    failure_mode: str
    blast_radius_percent: float = 5.0
    hypothesis: Optional[str] = None


class ControlLoopRunRequest(BaseModel):
    queue_name: str = "default"
    loop_name: str = "queue_congestion_controller"


class ConcurrencyTuneRequest(BaseModel):
    queue_name: str
    current_concurrency: int
    congestion_score: float


class DagMutationRequest(BaseModel):
    workflow_name: str
    source_version: str
    mutation_type: str
    proposal: Dict[str, Any]
    confidence: float = 0.5


class RetryAdaptationRequest(BaseModel):
    task_name: str
    exception_type: str
    current_policy: Dict[str, Any]
    proposed_policy: Dict[str, Any]
    confidence: float = 0.5


class ConsensusRequest(BaseModel):
    decision_type: str
    proposal: Dict[str, Any]


class ExperimentAssignRequest(BaseModel):
    experiment_name: str
    subject_key: str
    variants: List[str]
    traffic_percent: float = 10.0


class StrategyTournamentRequest(BaseModel):
    tournament_name: str
    strategy_type: str
    candidates: List[Dict[str, Any]]


class PolicyEvolutionRequest(BaseModel):
    policy_name: str
    source_version: str
    proposed_version: str
    proposal: Dict[str, Any]
    confidence: float = 0.5


def _normalize_filename(filename: str) -> str:
    return os.path.basename((filename or "").replace(" ", "_"))


def _file_extension(filename: str) -> str:
    return filename.lower().rsplit(".", 1)[-1] if "." in filename else ""


def _assert_allowed_extension(filename: str) -> None:
    ext = _file_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type for '{filename}'")


def _assert_allowed_mime_type(upload: UploadFile, filename: str) -> None:
    ext = _file_extension(filename)
    allowed_mimes = ALLOWED_MIME_TYPES_BY_EXTENSION.get(ext, set())
    content_type = (upload.content_type or "").lower().strip()
    if allowed_mimes and content_type and content_type not in allowed_mimes:
        raise HTTPException(status_code=400, detail=f"Unsupported MIME type '{content_type}' for '{filename}'")


def _assert_max_file_size(upload: UploadFile, filename: str) -> None:
    limit_bytes = settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024
    current_pos = upload.file.tell()
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > limit_bytes:
        raise HTTPException(status_code=400, detail=f"File '{filename}' exceeds {settings.MAX_UPLOAD_FILE_SIZE_MB}MB limit")
    if current_pos:
        upload.file.seek(0)


def _build_unique_storage_path(filename: str) -> str:
    from uuid import uuid4

    return os.path.join(settings.UPLOAD_DIR, f"{uuid4().hex}_{filename}")


def _route_queue_for_resume(filename: str) -> str:
    return "ocr" if _file_extension(filename) == "pdf" else "default"


def _serialize_job(job: ProcessingJob) -> Dict[str, Any]:
    return processing_service.serialize_job(job)


def _dispatch_job(processing_job_id: int):
    if settings.WORKFLOW_ORCHESTRATION_MODE == "sequential":
        return dispatch_resume_pipeline.apply_async(args=[processing_job_id], queue="bulk")
    return dispatch_parallel_resume_pipeline.apply_async(args=[processing_job_id], queue="bulk")


def _dispatch_job_for_owner(session: Session, processing_job_id: int, owner_id: int):
    routing = adaptive_scheduler.route_queue(
        session,
        base_queue="bulk",
        owner_id=owner_id,
        sla_seconds=settings.WORKFLOW_SLA_SECONDS,
    )
    queue_name = routing["queue_name"]
    if settings.WORKFLOW_ORCHESTRATION_MODE == "sequential":
        return dispatch_resume_pipeline.apply_async(args=[processing_job_id], queue=queue_name)
    return dispatch_parallel_resume_pipeline.apply_async(args=[processing_job_id], queue=queue_name)


@router.post("/resumes/upload", response_model=AsyncUploadResponse, summary="Upload resumes and process asynchronously")
async def upload_resumes_async(
    request: Request,
    files: List[UploadFile] = File(...),
    job_id: Optional[int] = Form(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="Please provide at least one resume file")
    if len(files) > settings.BULK_UPLOAD_MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Bulk uploads are limited to {settings.BULK_UPLOAD_MAX_FILES} files")

    selected_job = None
    if job_id is not None:
        selected_job = session.get(Job, job_id)
        if not selected_job or selected_job.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Job not found")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    request_id = getattr(request.state, "request_id", None)
    created_jobs: List[ProcessingJob] = []

    for upload in files:
        filename = _normalize_filename(upload.filename)
        _assert_allowed_extension(filename)
        _assert_allowed_mime_type(upload, filename)
        _assert_max_file_size(upload, filename)
        stored_path = _build_unique_storage_path(filename)
        resume_parser.save_upload_file(upload, stored_path)

        resume = Resume(
            owner_id=int(current_user.id),
            job_id=selected_job.id if selected_job else None,
            filename=filename,
            filepath=stored_path,
            matched_job=selected_job.title if selected_job else None,
            stage="new",
        )
        session.add(resume)
        session.commit()
        session.refresh(resume)

        queue_name = _route_queue_for_resume(filename)
        policy = policy_engine.evaluate_policies(
            session,
            policy_type="upload",
            owner_id=int(current_user.id),
            context={"filename": filename, "queue_name": queue_name, "file_type": _file_extension(filename)},
        )
        if policy["decision"] == "deny":
            raise HTTPException(status_code=403, detail="Upload blocked by runtime policy")
        processing_job = processing_service.create_processing_job(
            session,
            owner_id=int(current_user.id),
            resume_id=int(resume.id or 0),
            job_id=selected_job.id if selected_job else None,
            job_type="resume_processing",
            queue_name=queue_name,
            input_payload={"filename": filename, "job_id": selected_job.id if selected_job else None},
            request_id=request_id,
        )
        async_result = _dispatch_job_for_owner(session, int(processing_job.id or 0), int(current_user.id))
        processing_service.attach_celery_task(session, int(processing_job.id or 0), async_result.id)
        session.refresh(processing_job)
        created_jobs.append(processing_job)

    return {
        "batch_job_id": None,
        "total_resumes": len(created_jobs),
        "jobs": [_serialize_job(job) for job in created_jobs],
    }


@router.post("/resumes/{resume_id}/enqueue", response_model=EnqueueResumeResponse, summary="Reprocess an existing resume asynchronously")
def enqueue_existing_resume(
    resume_id: int,
    request: Request,
    job_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    resume = session.get(Resume, resume_id)
    if not resume or resume.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    selected_job_id = job_id if job_id is not None else resume.job_id
    if selected_job_id is not None:
        selected_job = session.get(Job, selected_job_id)
        if not selected_job or selected_job.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Job not found")

    queue_name = _route_queue_for_resume(resume.filename)
    processing_job = processing_service.create_processing_job(
        session,
        owner_id=int(current_user.id),
        resume_id=resume_id,
        job_id=selected_job_id,
        job_type="resume_processing",
        queue_name=queue_name,
        input_payload={"resume_id": resume_id, "job_id": selected_job_id},
        request_id=getattr(request.state, "request_id", None),
    )
    async_result = _dispatch_job_for_owner(session, int(processing_job.id or 0), int(current_user.id))
    processing_service.attach_celery_task(session, int(processing_job.id or 0), async_result.id)
    session.refresh(processing_job)
    return {"processing_job": _serialize_job(processing_job)}


@router.get("/jobs", response_model=List[ProcessingJobRead], summary="List processing jobs")
def list_processing_jobs(
    status: Optional[str] = None,
    resume_id: Optional[int] = None,
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    limit = max(1, min(limit, 200))
    query = select(ProcessingJob).where(ProcessingJob.owner_id == current_user.id)
    if status:
        query = query.where(ProcessingJob.status == status)
    if resume_id is not None:
        query = query.where(ProcessingJob.resume_id == resume_id)
    rows = session.exec(query.order_by(ProcessingJob.created_at.desc()).limit(limit)).all()
    return [_serialize_job(row) for row in rows]


@router.get("/jobs/{processing_job_id}", response_model=ProcessingJobRead, summary="Get processing job status")
def get_processing_job(
    processing_job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = session.get(ProcessingJob, processing_job_id)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Processing job not found")
    existing_events = processing_service.list_job_events(session, processing_job_id, int(current_user.id))
    return _serialize_job(record)


@router.get("/jobs/{processing_job_id}/events", response_model=List[ProcessingEventRead], summary="Get processing job events")
def get_processing_job_events(
    processing_job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = session.get(ProcessingJob, processing_job_id)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return processing_service.list_job_events(session, processing_job_id, int(current_user.id))


@router.post("/jobs/{processing_job_id}/replay", response_model=ReplayJobResponse, summary="Replay a failed or completed workflow")
def replay_processing_job(
    processing_job_id: int,
    payload: ReplayJobRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    source = session.get(ProcessingJob, processing_job_id)
    if not source or source.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Processing job not found")
    if source.resume_id is None:
        raise HTTPException(status_code=400, detail="Only resume processing jobs can be replayed")

    replay_job = processing_service.create_processing_job(
        session,
        owner_id=int(current_user.id),
        resume_id=source.resume_id,
        job_id=source.job_id,
        job_type=source.job_type,
        queue_name=source.queue_name,
        priority=source.priority,
        input_payload={
            "source_processing_job_id": source.id,
            "replay_mode": payload.replay_mode,
            "reason": payload.reason,
        },
        request_id=getattr(request.state, "request_id", None),
    )
    processing_service.create_workflow_replay(
        session,
        source_job=source,
        replay_job=replay_job,
        replay_mode=payload.replay_mode,
        reason=payload.reason,
    )
    async_result = _dispatch_job_for_owner(session, int(replay_job.id or 0), int(current_user.id))
    processing_service.attach_celery_task(session, int(replay_job.id or 0), async_result.id)
    session.refresh(replay_job)
    return {"source_job_id": processing_job_id, "replay_job": _serialize_job(replay_job)}


@router.get("/dead-letters", summary="List dead-lettered processing jobs")
def list_dead_letters(
    status: Optional[str] = "open",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return processing_service.list_dead_letters(session, int(current_user.id), status=status)


@router.get("/jobs/{processing_job_id}/reconstruct", summary="Reconstruct workflow state from immutable events")
def reconstruct_processing_job(
    processing_job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = session.get(ProcessingJob, processing_job_id)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return event_sourcing.reconstruct_workflow_state(session, f"processing_job:{processing_job_id}")


@router.post("/workflows/compile", summary="Compile a dynamic workflow DAG")
def compile_dynamic_workflow(
    payload: Dict[str, Any],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    policy = policy_engine.evaluate_policies(
        session,
        policy_type="workflow_compile",
        owner_id=int(current_user.id),
        context={"workflow_name": payload.get("workflow_name"), "node_count": len(payload.get("nodes") or [])},
    )
    if policy["decision"] == "deny":
        raise HTTPException(status_code=403, detail="Workflow compilation blocked by runtime policy")
    return workflow_compiler.compile_workflow(payload, context={"owner_id": current_user.id})


@router.get("/runtime/forecast", summary="Predict queue congestion and recommend runtime action")
def forecast_runtime(
    queue_name: str = "default",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return predictive_runtime.queue_forecast_report(session, queue_name=queue_name, owner_id=int(current_user.id))


@router.get("/runtime/workload-patterns", summary="Summarize workload patterns")
def workload_patterns(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return predictive_runtime.workload_pattern_summary(session, owner_id=int(current_user.id))


@router.post("/simulations/synthetic", summary="Create and run a synthetic workflow simulation")
def run_synthetic_simulation(
    payload: SimulationScenarioRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    scenario = simulation_engine.create_synthetic_scenario(
        session,
        owner_id=int(current_user.id),
        scenario_name=payload.scenario_name,
        workload_size=payload.workload_size,
        queue_mix=payload.queue_mix,
        failure_rate=payload.failure_rate,
        expected_sla_seconds=payload.expected_sla_seconds,
    )
    run = simulation_engine.run_simulation(session, scenario)
    return {"scenario_id": scenario.id, "run": simulation_engine.serialize_run(run)}


@router.post("/chaos/experiments", summary="Plan a chaos experiment")
def plan_chaos_experiment(
    payload: ChaosExperimentRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    experiment = chaos_engine.plan_chaos_experiment(
        session,
        owner_id=int(current_user.id),
        experiment_name=payload.experiment_name,
        target_queue=payload.target_queue,
        failure_mode=payload.failure_mode,
        blast_radius_percent=payload.blast_radius_percent,
        hypothesis=payload.hypothesis,
    )
    return chaos_engine.serialize_experiment(experiment)


@router.post("/runtime/control-loop/run", summary="Run a guarded autonomous control loop")
def run_control_loop(
    payload: ControlLoopRunRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return autonomous_controller.run_control_loop(
        session,
        queue_name=payload.queue_name,
        owner_id=int(current_user.id),
        loop_name=payload.loop_name,
    )


@router.post("/runtime/concurrency/tune", summary="Propose a concurrency tuning decision")
def tune_concurrency(
    payload: ConcurrencyTuneRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    decision = autonomous_controller.propose_concurrency_tuning(
        session,
        queue_name=payload.queue_name,
        current_concurrency=payload.current_concurrency,
        congestion_score=payload.congestion_score,
    )
    return {
        "id": decision.id,
        "queue_name": decision.queue_name,
        "current_concurrency": decision.current_concurrency,
        "recommended_concurrency": decision.recommended_concurrency,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "status": decision.status,
    }


@router.post("/runtime/workers/quarantine", summary="Propose quarantines for unhealthy workers")
def quarantine_workers(
    queue_name: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return {"quarantines": autonomous_controller.quarantine_unhealthy_workers(session, queue_name=queue_name)}


@router.post("/runtime/dag-mutations", summary="Propose a guarded DAG mutation")
def propose_dag_mutation(
    payload: DagMutationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    proposal = autonomous_controller.propose_dag_mutation(
        session,
        workflow_name=payload.workflow_name,
        source_version=payload.source_version,
        mutation_type=payload.mutation_type,
        proposal=payload.proposal,
        confidence=payload.confidence,
    )
    return {
        "id": proposal.id,
        "workflow_name": proposal.workflow_name,
        "source_version": proposal.source_version,
        "proposed_version": proposal.proposed_version,
        "mutation_type": proposal.mutation_type,
        "confidence": proposal.confidence,
        "status": proposal.status,
    }


@router.post("/runtime/retry-adaptations", summary="Propose adaptive retry policy")
def propose_retry_adaptation(
    payload: RetryAdaptationRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    row = autonomous_controller.propose_retry_adaptation(
        session,
        task_name=payload.task_name,
        exception_type=payload.exception_type,
        current_policy=payload.current_policy,
        proposed_policy=payload.proposed_policy,
        confidence=payload.confidence,
    )
    return {
        "id": row.id,
        "task_name": row.task_name,
        "exception_type": row.exception_type,
        "confidence": row.confidence,
        "status": row.status,
    }


@router.get("/runtime/agents", summary="List runtime orchestration agents")
def list_runtime_agents(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return {"agents": runtime_agents.list_agents(session)}


@router.post("/runtime/agents/consensus", summary="Run cross-agent consensus for a proposal")
def run_agent_consensus(
    payload: ConsensusRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return runtime_agents.coordinate_decision(
        session,
        owner_id=int(current_user.id),
        decision_type=payload.decision_type,
        proposal=payload.proposal,
    )


@router.get("/runtime/graph/{node_key}", summary="Inspect runtime knowledge graph neighborhood")
def inspect_runtime_graph(
    node_key: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return knowledge_graph.graph_neighborhood(session, node_key=node_key)


@router.post("/runtime/experiments/assign", summary="Assign a workflow experiment variant")
def assign_experiment_variant(
    payload: ExperimentAssignRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    row = experimentation.assign_variant(
        session,
        owner_id=int(current_user.id),
        experiment_name=payload.experiment_name,
        subject_key=payload.subject_key,
        variants=payload.variants,
        traffic_percent=payload.traffic_percent,
    )
    return {
        "id": row.id,
        "experiment_name": row.experiment_name,
        "subject_key": row.subject_key,
        "variant": row.variant,
    }


@router.post("/runtime/experiments/tournament", summary="Evaluate strategy tournament")
def run_strategy_tournament(
    payload: StrategyTournamentRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    row = experimentation.run_strategy_tournament(
        session,
        tournament_name=payload.tournament_name,
        strategy_type=payload.strategy_type,
        candidates=payload.candidates,
    )
    return {
        "id": row.id,
        "winner_strategy": row.winner_strategy,
        "scorecard": json.loads(row.scorecard_json or "[]"),
        "status": row.status,
    }


@router.post("/runtime/policies/evolve", summary="Propose runtime policy evolution")
def propose_policy_evolution(
    payload: PolicyEvolutionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    row = experimentation.propose_policy_evolution(
        session,
        policy_name=payload.policy_name,
        source_version=payload.source_version,
        proposed_version=payload.proposed_version,
        proposal=payload.proposal,
        confidence=payload.confidence,
    )
    return {
        "id": row.id,
        "policy_name": row.policy_name,
        "source_version": row.source_version,
        "proposed_version": row.proposed_version,
        "confidence": row.confidence,
        "safety_status": row.safety_status,
    }


@router.get("/jobs/{processing_job_id}/subtasks", response_model=List[ProcessingSubtaskRead], summary="Get processing DAG subtasks")
def get_processing_job_subtasks(
    processing_job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = session.get(ProcessingJob, processing_job_id)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return processing_service.list_job_subtasks(session, processing_job_id, int(current_user.id))


@router.get("/jobs/{processing_job_id}/stream", summary="Stream processing job events")
def stream_processing_job_events(
    processing_job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = session.get(ProcessingJob, processing_job_id)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Processing job not found")

    def _format_sse(event: str, payload: Dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"

    def _event_stream():
        for event in existing_events[-25:]:
            yield _format_sse("processing.event", event)

        pubsub = realtime_events.subscribe_to_job(processing_job_id)
        if pubsub is None:
            while True:
                yield _format_sse("heartbeat", {"processing_job_id": processing_job_id, "ts": time.time()})
                time.sleep(settings.PROCESSING_STREAM_HEARTBEAT_SECONDS)

        last_heartbeat = time.time()
        try:
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message.get("data"):
                    try:
                        payload = json.loads(message["data"])
                    except Exception:
                        payload = {"raw": message["data"]}
                    yield _format_sse("processing.event", payload)
                if time.time() - last_heartbeat >= settings.PROCESSING_STREAM_HEARTBEAT_SECONDS:
                    last_heartbeat = time.time()
                    yield _format_sse("heartbeat", {"processing_job_id": processing_job_id, "ts": last_heartbeat})
        finally:
            try:
                pubsub.close()
            except Exception:
                pass

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
