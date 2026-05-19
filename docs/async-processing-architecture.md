# Async Processing Architecture

This phase moves the recruitment platform from request-bound AI processing toward a production ATS workflow engine.

## Runtime Topology

```text
Frontend
  -> FastAPI API
    -> Postgres: durable jobs, resumes, ATS data
    -> Redis: Celery broker/result backend
    -> Object/local storage: uploaded resumes
    -> Celery workers
      -> default/bulk: parse, extract, match orchestration
      -> ocr: scanned PDF OCR
      -> embedding/ai: chunk embedding, vector indexing, AI evaluation
    -> ChromaDB/vector store
```

## Queue Strategy

```text
critical   transactional notifications and urgent recruiter actions
default    normal resume processing orchestration
bulk       large upload fan-out and batch dispatch
ocr        CPU-heavy scanned document processing
embedding  sentence-transformer embedding and vector indexing
ai         LLM/RAG evaluation and candidate summaries
```

Workers should be scaled independently. OCR and embedding workers usually need lower concurrency because they are CPU and memory heavy.

## Processing Lifecycle

```text
queued
  -> running / parse_extract
  -> running / match
  -> running / embed_index
  -> completed

Failure path:
running
  -> retrying
  -> running
  -> failed
```

The durable source of truth is `processingjob`. The audit/progress stream is `processingevent`.

## API Contracts

```http
POST /processing/resumes/upload
GET  /processing/jobs
GET  /processing/jobs/{processing_job_id}
GET  /processing/jobs/{processing_job_id}/events
POST /processing/resumes/{resume_id}/enqueue
```

Frontend polling should call `GET /processing/jobs/{id}` every 1-2 seconds while the status is non-terminal, then load events for a detailed timeline. A WebSocket/SSE endpoint can later publish `processingevent` rows in real time.

## Production Rules

- API workers should only validate, persist metadata, enqueue, and return a job id.
- Long-running parsing, OCR, embedding, vector indexing, and AI evaluation must run in workers.
- Every task must update `processingjob.current_step`, `progress`, and append a `processingevent`.
- Store enough metadata to replay or debug a failed job without logging resume contents.
- Use content hashes before embedding to avoid recomputing unchanged chunks.
- Keep OCR, embedding, and AI tasks in separate queues to avoid starving normal API workflows.
- Treat AI outputs as versioned derived artifacts with prompt/model metadata.

## Pipeline Decomposition

The next-generation pipeline is a Celery DAG. The parent `processingjob` tracks the user-visible lifecycle, while `processingsubtask` tracks each distributed unit of work.

```text
dispatch_resume_pipeline
  -> parse_extract_resume       queue: default / ocr-aware parsing
  -> match_resume_to_job        queue: default
  -> embed_and_index_resume     queue: embedding
  -> generate_candidate_summary queue: ai
  -> finalize_resume_pipeline   queue: default
```

Each subtask has:

```text
processing_job_id
task_name
queue_name
celery_task_id
status
attempt
idempotency_key
input_hash
output_json
error_message
started_at / completed_at
```

The idempotency key is derived from:

```text
processing_job_id + task_name + sha256(input_payload)
```

This allows partial retries without duplicating downstream artifacts. For example, a failed `generate_summary` retry should not reparse or re-embed the resume.

## Celery DAG Examples

Single resume pipeline:

```python
chain(
    parse_extract_resume.s(context).set(queue="default"),
    match_resume_to_job.s().set(queue="default"),
    embed_and_index_resume.s().set(queue="embedding"),
    generate_candidate_summary.s().set(queue="ai"),
    finalize_resume_pipeline.s().set(queue="default"),
).apply_async()
```

Bulk upload pattern:

```python
group(dispatch_resume_pipeline.s(job_id) for job_id in processing_job_ids)
```

Batch completion pattern:

```python
chord(
    group(dispatch_resume_pipeline.s(job_id) for job_id in processing_job_ids),
    finalize_bulk_upload.s(batch_id),
)
```

The current implementation introduces the single-resume chain. Bulk chord finalization is the next natural extension for batch-level dashboards and SLA tracking.

## Realtime Event Architecture

Every durable `processingevent` is also published to Redis Pub/Sub:

```text
channel: ats:processing:job:{processing_job_id}
```

Frontend options:

```text
Preferred: GET /processing/jobs/{id}/stream  (SSE)
Fallback:  GET /processing/jobs/{id} every 1-2 seconds
Timeline:  GET /processing/jobs/{id}/events
DAG:       GET /processing/jobs/{id}/subtasks
```

SSE event example:

```text
event: processing.event
data: {
  "type": "processing.event",
  "processing_job_id": 42,
  "resume_id": 91,
  "event_type": "step_updated",
  "step": "embed_index",
  "status": "running",
  "message": "Embedding chunks and updating vector index",
  "detail": {},
  "created_at": "2026-05-17T12:00:00Z"
}
```

Heartbeat example:

```text
event: heartbeat
data: {"processing_job_id": 42, "ts": 1779028800.0}
```

## AI Auditability

AI outputs should be stored as derived artifacts, not hidden transient text:

```text
candidateaisummary
  resume_id
  processing_job_id
  prompt_version
  model_name
  summary_json
  evidence_json
  confidence

matchexplanation
  resume_id
  job_id
  processing_job_id
  explanation_version
  score
  explanation_json
  evidence_json
```

This makes recruiter-facing AI explainable, replayable, and debuggable.

## Embedding Cache

Embedding cache key:

```text
sha256(normalized_chunk_text) + model_name
```

Cache row:

```text
text_hash
model_name
vector_json
dimensions
usage_count
last_used_at
```

For larger production deployments, move vectors out of Postgres JSON into one of:

```text
pgvector
Redis vector cache
S3 object by hash
Qdrant/Pinecone payload metadata
```

## Duplicate Detection

Use layered duplicate detection:

```text
exact file hash
  -> exact email match
  -> normalized phone match
  -> resume text simhash/minhash
  -> embedding similarity above threshold
```

Recommended duplicate states:

```text
unique
exact_duplicate
probable_duplicate
same_candidate_new_resume
needs_reviewer_confirmation
```

## Vector Index Lifecycle

```text
parse/extract completed
  -> build semantic chunks
  -> hash chunks
  -> reuse cached embeddings where possible
  -> embed misses
  -> delete previous vectors for resume_id + owner_id
  -> upsert Chroma records
  -> emit indexed event
```

Production strategy:

- Include `chunk_hash`, `embedding_model`, `chunk_type`, `resume_id`, `owner_id`, and `source_page` in vector metadata.
- Reindex only changed chunks.
- Keep old vector versions until the new index write succeeds.
- Add a periodic reconciliation job that compares DB resume state with vector index metadata.

## Metrics

Prometheus examples:

```text
resume_parser_processing_jobs_total{job_type,status}
resume_parser_processing_events_total{step,status}
resume_parser_processing_step_duration_seconds{job_type,step}
resume_parser_embedding_cache_hits_total
resume_parser_embedding_cache_misses_total
resume_parser_ocr_duration_seconds
resume_parser_embedding_duration_seconds
resume_parser_chroma_fallbacks_total
```

Grafana dashboard ideas:

- Pipeline throughput by queue
- Queue latency and worker concurrency
- Job success/failure/retry rate
- p50/p95/p99 processing time by step
- OCR duration and failure rate
- Embedding cache hit ratio
- AI summary generation latency/cost
- Chroma indexing failures
- Jobs breaching SLA

## Retry And DLQ

Retry policy:

```text
parse_extract: 3 retries, exponential backoff
match:         2 retries
embed_index:   3 retries
summary:       2 retries
finalize:      no retry unless DB transient error
```

Dead-letter strategy:

```text
Celery task exhausted
  -> processingjob.status = failed
  -> processingsubtask.status = failed
  -> processingevent event_type = job_failed
  -> optional DLQ table/object file
  -> recruiter UI shows Retry from failed step
```

Future table:

```text
deadletterjob
  source_task
  processing_job_id
  payload_json
  exception_type
  exception_message
  traceback_ref
  retry_count
  created_at
```

## OpenTelemetry

Trace boundaries:

```text
HTTP request span
  -> enqueue span
    -> Celery dispatch span
      -> parse span
      -> match span
      -> embedding span
      -> vector index span
      -> AI summary span
```

Propagate:

```text
request_id
processing_job_id
resume_id
organization_id
celery_task_id
```

Export to:

```text
OTel Collector -> Tempo/Jaeger
Prometheus -> Grafana
Loki/Sentry -> logs/errors
```

## Autoscaling

Scale by queue depth and workload type:

```text
api pods:       CPU/RPS
default worker: default queue depth
ocr worker:     ocr queue depth + CPU
embedding:      embedding queue depth + RAM/GPU
ai worker:      ai queue depth + provider rate limits
```

GPU migration path:

```text
embedding queue
  -> CPU sentence-transformers worker today
  -> GPU worker pool later
  -> remote embedding service when scale grows
```

## Cloud Deployment

```text
Cloud Load Balancer
  -> FastAPI API service
  -> Redis/ElastiCache
  -> Celery worker services
  -> Postgres/RDS
  -> S3/Blob storage
  -> Chroma/Qdrant/Pinecone
  -> Prometheus/Grafana/Loki/Sentry
```

For Kubernetes:

```text
Deployment api
Deployment worker-default
Deployment worker-ocr
Deployment worker-embedding
Deployment worker-ai
HPA/KEDA scaled by Redis queue length
CronJob vector-reconciliation
CronJob failed-job-sweeper
```

## Parallel Distributed Orchestration

The platform now supports a parallel DAG mode. Sequential mode remains available through:

```text
WORKFLOW_ORCHESTRATION_MODE=sequential
```

Default mode:

```text
WORKFLOW_ORCHESTRATION_MODE=parallel
```

Parallel resume DAG:

```text
dispatch_parallel_resume_pipeline
  -> parse_extract_resume
  -> launch_parallel_post_parse
       -> chord header:
            match_resume_to_job        queue: default
            embed_and_index_resume     queue: embedding
       -> chord callback:
            merge_parallel_results     queue: default
            generate_candidate_summary queue: ai
            finalize_resume_pipeline   queue: default
```

Why this shape:

- parsing is a prerequisite for both matching and chunking
- matching and vector indexing can run independently
- AI summary should wait for structured fields, match output, and index status
- finalize should only mark the parent job complete after all required branches finish

Celery implementation pattern:

```python
chain(
    parse_extract_resume.s(context).set(queue="default"),
    launch_parallel_post_parse.s().set(queue="bulk"),
).apply_async()

chord(
    group(
        match_resume_to_job.s(context).set(queue="default"),
        embed_and_index_resume.s(context).set(queue="embedding"),
    )
)(
    chain(
        merge_parallel_results.s(processing_job_id).set(queue="default"),
        generate_candidate_summary.s().set(queue="ai"),
        finalize_resume_pipeline.s().set(queue="default"),
    )
)
```

## Trace Propagation

Trace correlation keys:

```text
request_id
traceparent
processing_job_id
processing_subtask_id
resume_id
job_id
celery_task_id
queue_name
worker_hostname
```

HTTP span example:

```json
{
  "span": "http.request",
  "attributes": {
    "http.method": "POST",
    "http.route": "/processing/resumes/upload",
    "request_id": "6ed4..."
  }
}
```

Worker span example:

```json
{
  "span": "resume.embed_index",
  "attributes": {
    "processing_job_id": 42,
    "resume_id": 91,
    "queue_name": "embedding",
    "celery_task_id": "a7c..."
  }
}
```

OpenTelemetry integration:

```text
FastAPI middleware starts request span
  -> inject trace context into workflow context
  -> Celery task starts child span
  -> DB/vector/AI steps add nested spans
  -> OTLP exporter sends spans to collector
```

Environment:

```text
OTEL_ENABLE=true
OTEL_SERVICE_NAME=resume-parser-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
```

## Governance Tables

Enterprise AI auditability is handled by:

```text
aiartifact
  artifact_type
  provider
  model_name
  prompt_version
  prompt_hash
  input_hash
  output_hash
  artifact_json
  evidence_json
  latency_ms
  token_count
  estimated_cost_usd
  governance_status

retrievalevidence
  query_hash
  retriever_version
  evidence_json
  artifact_id

vectorindexversion
  vector_store
  collection_name
  embedding_model
  schema_version
  chunk_count
  status

workflowreplay
  source_processing_job_id
  replay_processing_job_id
  replay_mode
  reason

deadletterjob
  source_task
  queue_name
  payload_json
  exception_type
  exception_message
  retry_count
  status
```

Governance statuses:

```text
approved
needs_review
blocked
expired
superseded
```

## DLQ And Replay

Dead-letter flow:

```text
task retries exhausted
  -> processingjob.status = failed
  -> deadletterjob.status = open
  -> processingevent.job_failed emitted
  -> recruiter/admin can inspect DLQ
  -> replay endpoint creates a new ProcessingJob
```

Replay endpoint:

```http
POST /processing/jobs/{processing_job_id}/replay
```

Payload:

```json
{
  "replay_mode": "from_failed_step",
  "reason": "Retry after embedding worker memory fix"
}
```

Response:

```json
{
  "source_job_id": 42,
  "replay_job": {
    "id": 51,
    "status": "queued",
    "current_step": "queued"
  }
}
```

DLQ endpoint:

```http
GET /processing/dead-letters?status=open
```

Replay safety rules:

- never mutate the old failed job into running again
- create a new job linked through `workflowreplay`
- preserve source job events for audit
- use subtask idempotency keys to prevent duplicate artifacts where possible
- mark old DLQ records as replayed only after the new job is queued

## SLA And Latency Analytics

SLA config:

```text
WORKFLOW_SLA_SECONDS=300
```

Recommended SLA checks:

```text
queued_latency = started_at - created_at
runtime_latency = completed_at - started_at
total_latency = completed_at - created_at
step_latency = processingsubtask.completed_at - started_at
```

SLA states:

```text
within_sla
at_risk
breached
unknown
```

Useful query dimensions:

```text
organization_id
job_type
queue_name
task_name
model_name
embedding_model
worker_hostname
status
```

## Cost Analytics

Track AI cost at artifact level:

```text
aiartifact.token_count
aiartifact.estimated_cost_usd
aiartifact.latency_ms
aiartifact.model_name
aiartifact.artifact_type
```

Cost dashboards:

- cost per candidate
- cost per job
- cost per organization
- cost by model
- summary generation cost
- recruiter assistant cost
- interview evaluation cost

Optimization strategies:

- cache embeddings by chunk hash
- skip AI summary regeneration if prompt/model/input hashes match
- batch embeddings
- use local models for low-risk summaries
- reserve premium LLMs for recruiter-visible final artifacts
- route large bulk jobs to lower-priority queues

## Prometheus Metrics

Implemented/target metrics:

```text
resume_parser_processing_jobs_total{job_type,status}
resume_parser_processing_events_total{step,status}
resume_parser_processing_step_duration_seconds{job_type,step}
resume_parser_queue_dispatch_total{queue_name,task_name}
resume_parser_dead_letter_jobs_total{source_task,status}
resume_parser_workflow_replays_total{mode}
resume_parser_ai_artifacts_total{artifact_type,model_name,governance_status}
resume_parser_ai_artifact_latency_seconds{artifact_type,model_name}
resume_parser_embedding_cache_hits_total
resume_parser_embedding_cache_misses_total
```

Additional recommended metrics:

```text
celery_queue_depth{queue_name}
celery_worker_concurrency{queue_name,worker}
celery_task_runtime_seconds{task_name,queue_name}
workflow_sla_breaches_total{job_type,queue_name}
ai_estimated_cost_usd_total{artifact_type,model_name}
vector_index_versions_total{schema_version,status}
```

## Grafana Architecture

Dashboards:

```text
ATS Executive Overview
  - resumes processed
  - success/failure rate
  - SLA breach count
  - AI cost trend

Workflow Orchestration
  - queue depth by queue
  - step latency p95/p99
  - retries by task
  - DLQ open count

AI Governance
  - artifacts by model/version
  - governance status distribution
  - prompt version adoption
  - cost by artifact type

Vector Platform
  - embedding cache hit ratio
  - vector index versions
  - Chroma fallback count
  - reindex throughput

Worker Fleet
  - worker concurrency
  - queue saturation
  - CPU/RAM/GPU
  - task failures by worker hostname
```

## Autoscaling Heuristics

Queue-based scaling:

```text
default workers:
  target queue depth per replica: 20

ocr workers:
  target queue depth per replica: 3
  max concurrency: 1-2

embedding workers:
  target queue depth per replica: 10 CPU / 50 GPU
  scale on RAM and queue age

ai workers:
  target queue depth per replica: provider rate-limit aware
  scale on queue age, not just depth

bulk workers:
  scale down aggressively
  avoid starving default queue
```

KEDA trigger example:

```text
redis list length for celery queue
  -> HPA worker deployment replicas
```

## Vector Migration Strategy

Embedding migration from `all-MiniLM-L6-v2` to a new model:

```text
1. add new VECTOR_SCHEMA_VERSION
2. create new vector collection
3. dual-write new resumes to old and new indexes
4. backfill old resumes in low-priority batch queue
5. shadow-read from new index and compare retrieval quality
6. switch read traffic to new collection
7. mark old vectorindexversion rows as superseded
8. delete old collection after retention window
```

Never overwrite the active vector collection in place during migration.

## Cloud-Scale Topology

```text
Frontend CDN
  -> API Gateway / Load Balancer
    -> FastAPI API pods
    -> Redis / ElastiCache
    -> Postgres / RDS
    -> Object Storage / S3
    -> Vector DB / Qdrant or Pinecone
    -> Celery workers
      -> default
      -> bulk
      -> ocr
      -> embedding-cpu
      -> embedding-gpu
      -> ai
    -> OTel Collector
    -> Prometheus
    -> Grafana
    -> Loki/Sentry
```

Kubernetes migration:

```text
Deployment api
Deployment worker-default
Deployment worker-bulk
Deployment worker-ocr
Deployment worker-embedding-cpu
Deployment worker-embedding-gpu
Deployment worker-ai
StatefulSet redis if self-hosted
Managed Postgres preferred
Managed object storage preferred
KEDA Redis scaler
OTel Collector DaemonSet/Deployment
Prometheus Operator
Grafana dashboards as ConfigMaps
```

ECS migration:

```text
Service api
Service worker-default
Service worker-ocr
Service worker-embedding
Service worker-ai
ElastiCache Redis
RDS Postgres
S3 uploads
CloudWatch logs
ADOT Collector for traces
Application Auto Scaling by Redis queue metrics
```

GPU future:

```text
embedding queue
  -> GPU worker deployment
  -> model warmed on startup
  -> batch encode chunks
  -> expose embedding microservice later
```

## Cloud-Native Workflow Runtime

The runtime now has explicit metadata for:

```text
workflowdefinition      versioned DAG + FSM definition
workflowcheckpoint      replay checkpoints and trace context
queuegovernancepolicy   tenant/global queue limits
workerheartbeat         worker fleet health snapshots
aiusageledger           token and cost accounting
```

### End-To-End Trace Propagation

Trace context should move with the workflow payload:

```json
{
  "processing_job_id": 42,
  "pipeline_version": "resume-dag-v1",
  "trace_context": {
    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
  }
}
```

HTTP request:

```text
FastAPI middleware
  -> starts span http.request
  -> injects W3C trace context
  -> stores request_id + trace context in workflow payload
```

Celery worker:

```text
task receives context.trace_context
  -> extracts parent context
  -> starts child span resume.parse_extract / resume.match / resume.embed_index
  -> tags span with processing_job_id, resume_id, queue_name, celery_task_id
```

Span payload example:

```json
{
  "name": "resume.match",
  "attributes": {
    "processing_job_id": 42,
    "resume_id": 91,
    "job_id": 7,
    "workflow_version": "resume-dag-v1",
    "queue_name": "default"
  }
}
```

### Workflow FSM

Legal parent-job transitions:

```text
queued
  -> running
  -> failed
  -> cancelled

running
  -> retrying
  -> completed
  -> failed
  -> cancelled

retrying
  -> running
  -> failed
  -> cancelled

failed
  -> queued       only through replay/new job semantics

completed/cancelled
  -> terminal
```

FSM enforcement happens before status mutation. Illegal transitions should emit:

```text
resume_parser_fsm_transitions_total{from_state,to_state,valid="false"}
```

State transition schema:

```json
{
  "from_state": "running",
  "to_state": "completed",
  "actor": "worker-default",
  "processing_job_id": 42,
  "reason": "finalize_resume_pipeline"
}
```

### Replay Checkpoints

Checkpoint example:

```json
{
  "checkpoint_name": "match_completed",
  "workflow_version": "resume-dag-v1",
  "state": {
    "resume_id": 91,
    "score": 0.82
  },
  "trace_context": {
    "traceparent": "00-..."
  }
}
```

Replay strategy:

```text
1. source job remains immutable
2. replay creates a new ProcessingJob
3. workflowreplay links source -> replay
4. latest checkpoint can seed replay context
5. idempotency keys prevent duplicate subtask artifacts
6. replay emits new event stream and trace
```

### Queue Governance

Queue policy:

```json
{
  "owner_id": null,
  "queue_name": "embedding",
  "max_depth": 1000,
  "max_concurrency": 2,
  "max_dispatch_per_minute": 120,
  "priority": 5,
  "is_active": true
}
```

Backpressure flow:

```text
API enqueue request
  -> resolve tenant queue policy
  -> estimate queue depth
  -> if below limit: dispatch
  -> if overloaded and reject=false: dispatch + overload metric
  -> if overloaded and reject=true: return 429/503 style failure
```

Queue overload metric:

```text
resume_parser_queue_overload_total{queue_name="embedding",action="reject"}
resume_parser_queue_overload_total{queue_name="embedding",action="allow_with_overload_event"}
```

Tenant queue isolation options:

```text
shared queues:
  default, embedding, ai

tenant-routed queues:
  default.tenant.{owner_id}
  embedding.tenant.{owner_id}
  ai.tenant.{owner_id}

hybrid:
  enterprise tenants get dedicated queues
  small tenants use shared fair queues
```

### AI Cost Accounting

Usage ledger:

```text
aiusageledger
  owner_id
  resume_id
  job_id
  processing_job_id
  artifact_id
  usage_type
  provider
  model_name
  input_tokens
  output_tokens
  total_tokens
  estimated_cost_usd
```

Cost model:

```text
estimated_cost =
  (input_tokens / 1000 * AI_INPUT_TOKEN_COST_PER_1K)
  + (output_tokens / 1000 * AI_OUTPUT_TOKEN_COST_PER_1K)
```

Dashboards:

- cost per organization
- cost per resume processed
- cost per job requisition
- cost by artifact type
- cost by model
- AI latency vs cost
- token spikes by tenant

### Worker Health

Worker heartbeat shape:

```json
{
  "worker_name": "worker-ai-7d9f",
  "queue_name": "ai",
  "status": "online",
  "active_tasks": 2,
  "max_concurrency": 4,
  "last_heartbeat_at": "2026-05-17T12:00:00Z"
}
```

Health orchestration:

```text
worker startup -> heartbeat online
periodic beat  -> update active_tasks/concurrency
graceful stop  -> heartbeat draining
timeout        -> mark stale
autoscaler     -> use stale/active worker ratio
```

### KEDA ScaledObject Examples

Embedding workers:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: worker-embedding
spec:
  scaleTargetRef:
    name: worker-embedding
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
    - type: redis
      metadata:
        address: redis:6379
        listName: celery
        listLength: "25"
```

AI workers:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: worker-ai
spec:
  scaleTargetRef:
    name: worker-ai
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus:9090
        metricName: ai_queue_age_seconds
        threshold: "60"
        query: max(celery_queue_oldest_task_age_seconds{queue_name="ai"})
```

GPU embedding workers:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-embedding-gpu
spec:
  template:
    spec:
      nodeSelector:
        accelerator: nvidia
      containers:
        - name: worker
          image: ats-worker:latest
          args: ["celery", "-A", "backend.workers.celery_app.celery_app", "worker", "--queues=embedding", "--concurrency=1"]
          resources:
            limits:
              nvidia.com/gpu: 1
```

### Canary Workflow Rollout

Workflow rollout stages:

```text
resume-dag-v1 sequential
  -> resume-dag-v1 parallel shadow
  -> resume-dag-v2 5% tenants
  -> compare success rate, latency, AI cost, match score drift
  -> 25%
  -> 50%
  -> 100%
  -> mark previous workflow superseded
```

Canary guardrails:

```text
failure rate increase < 1%
p95 latency increase < 20%
AI cost increase < 15%
match score drift within expected bounds
DLQ rate stable
```

### Error Budget

Suggested SLOs:

```text
99% API enqueue requests succeed
95% resumes processed within 5 minutes
99% processing events delivered through polling/SSE fallback
99.5% worker tasks do not exhaust retries
AI artifact generation p95 under 60 seconds
```

Error budget burn:

```text
fast burn: 2% budget in 1 hour
slow burn: 10% budget in 3 days
```

Operational actions:

```text
fast burn -> freeze deploys, scale workers, inspect DLQ
slow burn -> tune queues, inspect model/provider latency, backfill failed jobs
```

### Distributed Logging

Every log line should include:

```text
request_id
trace_id
span_id
processing_job_id
processing_subtask_id
resume_id
owner_id
queue_name
celery_task_id
worker_name
workflow_version
```

Log routing:

```text
stdout JSON logs
  -> Fluent Bit / CloudWatch Agent
  -> Loki / CloudWatch Logs
  -> correlate with Tempo/Jaeger traces via trace_id
```

### Rolling Deployment Safety

Production deployment rules:

```text
1. deploy DB migrations first
2. deploy workers with support for old and new workflow versions
3. deploy API to start emitting new workflow version
4. drain old workers after queues empty
5. keep old task names registered until no old jobs remain
6. only then remove old workflow code
```

For Celery:

```text
worker_prefetch_multiplier=1
task_acks_late=True
graceful shutdown timeout > longest task soft limit
old workers drain before termination
```

## Adaptive Runtime Intelligence

This phase adds a self-optimizing orchestration layer on top of the fixed DAG runtime.

New runtime concepts:

```text
workflow_compiler       validates and compiles dynamic DAG JSON
policy_engine           evaluates runtime policy DSL
adaptive_scheduler      selects queues using SLA + tenant fairness
event_sourcing          writes immutable orchestration events
compliance artifacts    records AI safety and evidence checks
optimization signals    stores runtime learning/recommendations
```

### Dynamic DAG Definition

Example workflow JSON:

```json
{
  "workflow_name": "resume_intelligence",
  "workflow_version": "resume-dag-v2",
  "nodes": [
    {"id": "parse_extract", "task": "resume.pipeline.parse_extract", "queue": "default"},
    {"id": "match", "task": "resume.pipeline.match", "queue": "default", "depends_on": ["parse_extract"]},
    {"id": "embed_index", "task": "resume.pipeline.embed_index", "queue": "embedding", "depends_on": ["parse_extract"]},
    {"id": "summary", "task": "resume.pipeline.generate_summary", "queue": "ai", "depends_on": ["match", "embed_index"]},
    {"id": "finalize", "task": "resume.pipeline.finalize", "queue": "default", "depends_on": ["summary"]}
  ]
}
```

Compiled plan:

```json
{
  "valid": true,
  "execution_levels": [
    ["parse_extract"],
    ["embed_index", "match"],
    ["summary"],
    ["finalize"]
  ],
  "node_count": 5
}
```

Compile endpoint:

```http
POST /processing/workflows/compile
```

### Policy DSL

Runtime policy example:

```json
{
  "when": [
    {"field": "file_type", "op": "eq", "value": "exe"}
  ],
  "then": {
    "action": "deny",
    "reason": "unsupported_file_type"
  }
}
```

SLA routing policy:

```json
{
  "when": [
    {"field": "sla_seconds", "op": "lte", "value": 120}
  ],
  "then": {
    "action": "reroute",
    "queue": "critical"
  }
}
```

Policy trace:

```json
{
  "policy_type": "upload",
  "decision": "allow",
  "matched_policies": [
    {"policy_name": "block_executables", "action": "allow", "policy_version": "v1"}
  ]
}
```

### Tenant Fairness

Fairness score:

```text
score = priority_weight + burst_credits * 0.01 - active_jobs / max_active_jobs
```

Example:

```json
{
  "owner_id": 12,
  "active_jobs": 10,
  "max_active_jobs": 25,
  "priority_weight": 1.0,
  "burst_credits": 5,
  "fairness_score": 0.65
}
```

Scheduling decision:

```json
{
  "base_queue": "bulk",
  "selected_queue": "critical",
  "reason": "sla_priority",
  "fairness_score": 0.65
}
```

### Event Sourcing

Immutable orchestration event:

```json
{
  "event_id": "uuid",
  "stream_id": "processing_job:42",
  "event_type": "processing.step_updated",
  "event_version": "v1",
  "sequence_number": 7,
  "payload": {
    "step": "embed_index",
    "status": "running",
    "message": "Embedding chunks and updating vector index"
  },
  "metadata": {
    "request_id": "req-123",
    "traceparent": "00-..."
  }
}
```

Reconstruction:

```http
GET /processing/jobs/{processing_job_id}/reconstruct
```

Reconstructed state:

```json
{
  "stream_id": "processing_job:42",
  "status": "completed",
  "current_step": "finalize",
  "events": []
}
```

Deterministic replay rules:

- rebuild state from immutable events
- use checkpoints only as acceleration hints
- never edit historical events
- replay creates new events in a new stream
- duplicate side effects must be guarded by idempotency keys

### AI Safety And Compliance

Candidate summary compliance flow:

```text
generated summary
  -> count evidence chunks/signals
  -> compute evidence_sufficiency_score
  -> compute hallucination_risk_score
  -> record complianceartifact
  -> mark passed or needs_review
```

Compliance artifact:

```json
{
  "artifact_type": "candidate_summary_safety",
  "status": "needs_review",
  "risk_score": 0.42,
  "details": {
    "evidence_sufficiency_score": 0.33,
    "hallucination_risk_score": 0.42,
    "claim_count": 7
  }
}
```

PII governance should add:

```text
pii_detected
pii_redacted
pii_policy_violation
retention_policy_applied
candidate_consent_verified
```

### Runtime Optimization

Optimization signal examples:

```json
{
  "signal_type": "queue_saturation",
  "queue_name": "embedding",
  "severity": "warning",
  "score": 0.82,
  "recommendation": {
    "action": "scale_out",
    "target_replicas": 4,
    "reason": "p95 queue age above SLA"
  }
}
```

```json
{
  "signal_type": "low_evidence_ai_summary",
  "workflow_version": "resume-dag-v2",
  "severity": "info",
  "recommendation": {
    "action": "increase_retrieval_k",
    "from": 4,
    "to": 8
  }
}
```

Dashboards:

- queue saturation signals
- fairness score by tenant
- policy decisions over time
- compliance artifacts by status
- hallucination risk trend
- evidence sufficiency trend
- workflow version comparison
- experiment control vs treatment latency/cost

### Workflow Experiments

A/B orchestration testing:

```json
{
  "experiment_name": "summary_after_index_v2",
  "workflow_name": "resume_intelligence",
  "control_version": "resume-dag-v1",
  "treatment_version": "resume-dag-v2",
  "traffic_percent": 10,
  "success_metric": "summary_passed_compliance",
  "guardrails": {
    "max_cost_increase_percent": 15,
    "max_latency_increase_percent": 20,
    "max_dlq_rate_percent": 2
  }
}
```

### Self-Healing Logic

Self-healing playbook:

```text
worker unhealthy
  -> stop routing new work to worker queue shard
  -> emit optimization signal
  -> scale replacement worker
  -> replay failed jobs from latest checkpoint

queue overloaded
  -> reroute SLA-sensitive jobs to critical
  -> throttle low-priority tenants
  -> allow existing jobs to drain
  -> emit queue_overload metric

AI compliance degraded
  -> mark artifacts needs_review
  -> increase retrieval evidence requirement
  -> switch prompt version
  -> canary safer workflow
```

### Multi-Region Strategy

Recommended topology:

```text
Region A primary:
  API, workers, Redis, Postgres writer, vector writer

Region B standby/active-read:
  API read path, workers disabled or limited, Postgres replica, vector replica

Global:
  object storage replication
  event stream replication
  tenant-region routing
```

Rules:

- keep a workflow stream pinned to one region
- replicate immutable orchestration events
- replay in another region only after fencing old region
- use globally unique event IDs
- store vector index version per region if vector DB is regional

### Enterprise SaaS Isolation

Isolation levels:

```text
basic:
  shared queues, row-level tenant filtering

premium:
  tenant queue shards, tenant quotas, dedicated concurrency caps

enterprise:
  dedicated workers, isolated vector collection, dedicated object prefix/KMS key

regulated:
  region pinning, stricter AI governance, extended audit retention
```

Runtime feature flags:

```text
ADAPTIVE_RUNTIME_ENABLE
POLICY_ENGINE_ENABLE
TENANT_FAIRNESS_ENABLE
TENANT_QUEUE_ISOLATION_ENABLE
WORKFLOW_ORCHESTRATION_MODE
```

## Predictive Runtime Intelligence

This phase adds predictive orchestration, simulation, chaos planning, and optimization recommendations.

New runtime services:

```text
predictive_runtime    queue forecasting, SLA risk, autoscaling recommendations
simulation_engine     synthetic workload simulation and resilience scoring
chaos_engine          safe chaos experiment planning
```

New tables:

```text
predictivetelemetrysnapshot
runtimeprediction
orchestrationrecommendation
simulationscenario
simulationrun
chaosexperiment
workerefficiencysnapshot
```

### Predictive Telemetry

Telemetry snapshot example:

```json
{
  "queue_name": "embedding",
  "window_seconds": 300,
  "queued_jobs": 84,
  "running_jobs": 12,
  "completed_jobs": 260,
  "failed_jobs": 3,
  "avg_latency_seconds": 41.2,
  "p95_latency_seconds": 112.5,
  "worker_count": 3,
  "active_task_count": 9
}
```

Congestion prediction:

```json
{
  "prediction_type": "queue_congestion",
  "queue_name": "embedding",
  "horizon_seconds": 300,
  "predicted_value": 0.81,
  "confidence": 0.65,
  "features": {
    "queued_jobs": 84,
    "running_jobs": 12,
    "worker_count": 3,
    "p95_latency_seconds": 112.5,
    "failure_pressure": 0.01
  }
}
```

Forecast endpoint:

```http
GET /processing/runtime/forecast?queue_name=embedding
```

### Recommendation Engine

Recommendation payload:

```json
{
  "recommendation_type": "autoscaling",
  "priority": 2,
  "action": {
    "action": "scale_out",
    "queue_name": "embedding",
    "target_replicas_delta": 2,
    "reason": "predicted_queue_congestion"
  },
  "expected_impact": {
    "predicted_value": 0.81,
    "confidence": 0.65,
    "horizon_seconds": 300
  }
}
```

Heuristic model today:

```text
congestion =
  queue_load * 0.50
  + latency_pressure * 0.35
  + failure_pressure * 0.15
```

Future ML-assisted model:

```text
features:
  queue depth
  queue age
  worker count
  active task count
  p50/p95/p99 latency
  retry rate
  DLQ rate
  tenant priority
  hour/day seasonality
  model/provider latency

models:
  gradient boosted trees for SLA breach risk
  online regression for latency prediction
  anomaly detector for failure spikes
  contextual bandit for routing strategy
```

### Concurrency Auto-Tuning

Auto-tuning loop:

```text
observe queue telemetry
  -> predict congestion/SLA risk
  -> estimate worker efficiency
  -> recommend concurrency delta
  -> apply through KEDA/HPA or worker config
  -> observe impact
  -> store optimization signal
```

Concurrency recommendation example:

```json
{
  "queue_name": "ai",
  "current_concurrency": 2,
  "recommended_concurrency": 4,
  "reason": "p95 latency above SLA and failure rate stable",
  "guardrails": {
    "provider_rate_limit_remaining": true,
    "cost_budget_available": true
  }
}
```

### Intelligent Retry Optimization

Retry policy learning signals:

```text
task_name
exception_type
attempt_number
retry_delay
eventual_success
runtime_after_retry
provider_status
queue_depth_at_failure
```

Adaptive retry strategy:

```text
transient provider error -> exponential backoff + jitter
OCR memory failure       -> route to low-concurrency OCR worker
vector DB timeout        -> retry after queue cool-down
policy/compliance fail   -> no retry, route to review
bad input/document       -> no retry, DLQ with user-facing reason
```

### Workflow Simulation

Synthetic simulation request:

```http
POST /processing/simulations/synthetic
```

Payload:

```json
{
  "scenario_name": "monday_bulk_upload",
  "workload_size": 500,
  "queue_mix": {
    "default": 0.45,
    "embedding": 0.3,
    "ai": 0.2,
    "ocr": 0.05
  },
  "failure_rate": 0.02,
  "expected_sla_seconds": 300
}
```

Simulation result:

```json
{
  "resilience_score": 0.78,
  "result": {
    "bottleneck_queue": "default",
    "estimated_latency_seconds": 337.5,
    "sla_risk": 1.0,
    "recommendations": [
      {"action": "scale_out", "queue_name": "default"},
      {"action": "prewarm_cache", "target": "embeddings"}
    ]
  }
}
```

### Chaos Engineering

Chaos planning endpoint:

```http
POST /processing/chaos/experiments
```

Payload:

```json
{
  "experiment_name": "embedding_worker_loss",
  "target_queue": "embedding",
  "failure_mode": "worker_termination",
  "blast_radius_percent": 10,
  "hypothesis": "KEDA replaces failed workers before SLA breach"
}
```

Safety:

```text
CHAOS_EXPERIMENTS_ENABLE=false by default
```

Chaos experiments should begin as plan-only, then evolve into controlled execution with:

```text
blast radius caps
tenant allowlists
time windows
automatic rollback
SLO/error budget guardrails
```

### Digital Twin Runtime

Digital twin topology:

```text
production event stream
  -> telemetry snapshots
  -> simulation scenarios
  -> predicted queue states
  -> recommendation engine
  -> canary strategy
  -> production rollout
```

Uses:

- compare workflow versions before rollout
- test queue policies
- estimate cost/performance tradeoffs
- predict GPU worker demand
- stress test tenant fairness rules
- replay incidents safely

### GPU Forecasting

GPU workload forecast:

```text
embedding_queue_depth
chunk_count_per_resume
cache_miss_rate
embedding_model_latency
GPU_batch_capacity
```

Decision:

```text
if cache_miss_rate high and queue_age rising:
  prewarm GPU workers
  batch embeddings
  defer low-priority tenants
```

### Resilience Dashboards

Dashboard panels:

- predicted queue congestion by queue
- SLA breach probability
- recommendation backlog
- simulation resilience scores
- chaos experiment status
- retry success by exception type
- worker efficiency score
- cache hit ratio vs latency
- GPU forecasted demand
- cost per completed workflow

### Enterprise Reliability Strategy

Reliability maturity path:

```text
Level 1: observe
  metrics, logs, traces, events

Level 2: recommend
  forecasts, optimization signals, dashboards

Level 3: simulate
  digital twin, synthetic workloads, chaos plans

Level 4: assist
  operator-approved scale/routing/retry changes

Level 5: autonomic
  policy-bounded self-healing and self-tuning
```

## Autonomous Runtime Control Loops

This phase turns recommendations into guarded, auditable control actions. The runtime remains safety-first:

```text
AUTONOMOUS_RUNTIME_ENABLE=false by default
```

When autonomy is disabled, the system still proposes actions and records learning signals, but actions remain approval-gated.

New services:

```text
autonomous_controller   converts predictions/recommendations into guarded actions
runtime_learning        records rewards, strategy outcomes, and confidence scores
```

New tables:

```text
runtimecontrolloop
runtimeaction
runtimelearningsignal
orchestrationstrategy
strategyoutcome
concurrencytuningdecision
workerquarantine
dagmutationproposal
retrypolicyadaptation
autonomousrollback
```

### Closed-Loop Control

Control loop:

```text
observe telemetry
  -> predict congestion / SLA risk
  -> recommend action
  -> validate guardrails
  -> execute or require approval
  -> observe outcome
  -> compute reward
  -> update strategy memory
```

Endpoint:

```http
POST /processing/runtime/control-loop/run
```

Payload:

```json
{
  "queue_name": "embedding",
  "loop_name": "queue_congestion_controller"
}
```

Action payload:

```json
{
  "action_type": "scale_out",
  "queue_name": "embedding",
  "status": "requires_approval",
  "confidence": 0.74,
  "action": {
    "action": "scale_out",
    "queue_name": "embedding",
    "target_replicas_delta": 2,
    "reason": "predicted_queue_congestion"
  },
  "guardrails": {
    "min_confidence": 0.8,
    "autonomous_enabled": false,
    "requires_guardrails": true
  }
}
```

### Runtime Learning

Learning signal:

```json
{
  "signal_type": "control_loop_action",
  "queue_name": "embedding",
  "reward": 0.19,
  "features": {
    "predicted_value": 0.81,
    "confidence": 0.65,
    "queued_jobs": 84
  },
  "outcome": {
    "action_status": "executed",
    "action_type": "scale_out"
  }
}
```

Reward function:

```text
reward =
  latency_improvement * 0.35
  + cost_improvement * 0.20
  + reliability_delta * 0.30
  + SLA_bonus_or_penalty * 0.15
```

Strategy confidence:

```text
confidence = observed_confidence * 0.70 + positive_score * 0.30
```

### Self-Tuning Concurrency

Endpoint:

```http
POST /processing/runtime/concurrency/tune
```

Payload:

```json
{
  "queue_name": "ai",
  "current_concurrency": 2,
  "congestion_score": 0.86
}
```

Decision:

```json
{
  "queue_name": "ai",
  "current_concurrency": 2,
  "recommended_concurrency": 3,
  "confidence": 0.76,
  "reason": "congestion_score_above_threshold",
  "status": "proposed"
}
```

Guardrails:

```text
MAX_AUTONOMOUS_CONCURRENCY_DELTA=2
provider rate limits must be respected
cost budgets must be checked before scaling AI workers
GPU nodes require capacity-aware scheduling
```

### Worker Quarantine

Endpoint:

```http
POST /processing/runtime/workers/quarantine?queue_name=embedding
```

Quarantine rule:

```text
if worker failure_rate >= WORKER_QUARANTINE_FAILURE_RATE_THRESHOLD:
  create workerquarantine record
  stop routing new shard work to worker
  allow in-flight tasks to finish or retry elsewhere
```

Recovery trace:

```json
{
  "worker_name": "worker-embedding-7d9f",
  "queue_name": "embedding",
  "reason": "failure_rate_above_threshold",
  "status": "quarantined",
  "confidence": 0.72
}
```

### DAG Mutation

Endpoint:

```http
POST /processing/runtime/dag-mutations
```

Example:

```json
{
  "workflow_name": "resume_intelligence",
  "source_version": "resume-dag-v1",
  "mutation_type": "prune_optional_summary",
  "proposal": {
    "condition": "low_sla_remaining",
    "remove_node": "generate_summary",
    "fallback": "summary_async_later"
  },
  "confidence": 0.68
}
```

Allowed mutation classes:

```text
prune_optional_step
parallelize_independent_steps
defer_ai_artifact_generation
increase_retrieval_k
switch_model_tier
route_to_gpu_embedding
```

Mutation safety:

- never mutate active workflow in place
- create proposed version
- run simulation
- canary experiment
- monitor guardrails
- rollback if error budget burns

### Adaptive Retry Policy

Endpoint:

```http
POST /processing/runtime/retry-adaptations
```

Example:

```json
{
  "task_name": "resume.pipeline.embed_index",
  "exception_type": "VectorStoreTimeout",
  "current_policy": {
    "max_retries": 3,
    "backoff": "exponential",
    "base_delay": 30
  },
  "proposed_policy": {
    "max_retries": 5,
    "backoff": "exponential_jitter",
    "base_delay": 60,
    "reroute_after_attempt": 3
  },
  "confidence": 0.73
}
```

Retry learning signals:

```text
eventual_success_rate
attempt_count_distribution
time_to_recovery
queue_depth_at_failure
exception_type
provider_status
cost_of_retry
```

### Autonomous Rollback

Every executed action should have a rollback plan:

```json
{
  "rollback_type": "rollback_scale_out",
  "reason": "p95 latency worsened after action",
  "rollback": {
    "action_id": 31,
    "action_type": "scale_out"
  }
}
```

Rollback triggers:

```text
latency regression
cost budget breach
DLQ spike
compliance failure spike
worker crash loop
model/provider degradation
```

### AI-Agent Orchestration Controller

Future AI controller role:

```text
read:
  telemetry snapshots
  predictions
  recommendations
  event streams
  simulation runs
  chaos outcomes

reason:
  propose control actions
  explain expected impact
  identify guardrails
  recommend rollback plan

act:
  only through RuntimeAction records
  only if policy allows
  only if confidence threshold passes
```

Agent safety:

```text
no direct infrastructure mutation
all actions are typed
all actions are event-sourced
all actions have rollback plans
all actions are policy checked
high-risk actions require human approval
```

### Autonomous Runtime State

```text
observe
  -> predict
  -> recommend
  -> propose_action
  -> guardrail_check
  -> execute_or_wait
  -> measure
  -> learn
  -> adapt_policy_or_strategy
```

### Enterprise Governance

Autonomy levels:

```text
level_0: observe only
level_1: recommend only
level_2: propose typed actions
level_3: execute low-risk actions
level_4: execute reversible actions with rollback
level_5: full policy-bounded autonomy
```

Recommended production default:

```text
level_2 for most tenants
level_3 for internal/staging workloads
level_4 only after proven guardrails
level_5 not recommended for regulated hiring workflows
```
