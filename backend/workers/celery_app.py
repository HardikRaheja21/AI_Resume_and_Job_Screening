from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from ..utils.config import settings


broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "resume_parser",
    broker=broker_url,
    backend=result_backend,
    include=[
        "backend.workers.tasks.resume_pipeline",
        "backend.workers.tasks.decomposed_pipeline",
        "backend.workers.tasks.ai_pipeline",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_routes={
        "resume.process": {"queue": "default", "routing_key": "default"},
        "resume.pipeline.dispatch": {"queue": "bulk", "routing_key": "bulk"},
        "resume.pipeline.dispatch_parallel": {"queue": "bulk", "routing_key": "bulk"},
        "resume.pipeline.launch_parallel": {"queue": "bulk", "routing_key": "bulk"},
        "resume.pipeline.merge_parallel": {"queue": "default", "routing_key": "default"},
        "resume.pipeline.parse_extract": {"queue": "default", "routing_key": "default"},
        "resume.pipeline.match": {"queue": "default", "routing_key": "default"},
        "resume.pipeline.embed_index": {"queue": "embedding", "routing_key": "embedding"},
        "resume.pipeline.generate_summary": {"queue": "ai", "routing_key": "ai"},
        "resume.pipeline.finalize": {"queue": "default", "routing_key": "default"},
        "resume.parse_extract": {"queue": "default", "routing_key": "default"},
        "resume.ocr": {"queue": "ocr", "routing_key": "ocr"},
        "resume.embed_index": {"queue": "embedding", "routing_key": "embedding"},
        "resume.bulk_dispatch": {"queue": "bulk", "routing_key": "bulk"},
        "ai.evaluate_answer": {"queue": "ai", "routing_key": "ai"},
        "ai.generate_candidate_summary": {"queue": "ai", "routing_key": "ai"},
    },
    task_queues=(
        Queue("critical", Exchange("critical"), routing_key="critical"),
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("bulk", Exchange("bulk"), routing_key="bulk"),
        Queue("ocr", Exchange("ocr"), routing_key="ocr"),
        Queue("embedding", Exchange("embedding"), routing_key="embedding"),
        Queue("ai", Exchange("ai"), routing_key="ai"),
    ),
)
