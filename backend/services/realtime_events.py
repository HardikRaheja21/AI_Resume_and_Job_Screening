from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from ..utils.config import settings

logger = logging.getLogger("resume_parser.realtime_events")

try:
    import redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore


_CLIENT: Optional[Any] = None


def _client() -> Optional[Any]:
    global _CLIENT
    if not settings.PROCESSING_EVENT_REDIS_ENABLED or redis is None:
        return None
    if _CLIENT is None:
        try:
            _CLIENT = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as exc:
            logger.warning("redis_event_client_unavailable", extra={"error": str(exc)})
            return None
    return _CLIENT


def channel_for_job(processing_job_id: int) -> str:
    return f"{settings.PROCESSING_EVENT_CHANNEL_PREFIX}:job:{processing_job_id}"


def publish_job_event(processing_job_id: int, payload: Dict[str, Any]) -> None:
    client = _client()
    if client is None:
        return
    try:
        client.publish(channel_for_job(processing_job_id), json.dumps(payload, default=str))
    except Exception as exc:
        logger.warning(
            "redis_event_publish_failed",
            extra={"processing_job_id": processing_job_id, "error": str(exc)},
        )


def subscribe_to_job(processing_job_id: int) -> Optional[Any]:
    client = _client()
    if client is None:
        return None
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel_for_job(processing_job_id))
    return pubsub
