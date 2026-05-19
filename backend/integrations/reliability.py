from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import time
from typing import Any, Callable, Dict
from uuid import uuid4

from ..utils.config import settings

logger = logging.getLogger("resume_parser.integrations")


def _ensure_dead_letter_dir() -> str:
    path = settings.DEAD_LETTER_DIR
    os.makedirs(path, exist_ok=True)
    return path


def write_dead_letter(kind: str, payload: Dict[str, Any]) -> str:
    directory = _ensure_dead_letter_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"{kind}_{timestamp}.jsonl"
    destination = os.path.join(directory, filename)
    envelope = {
        "id": str(uuid4()),
        "kind": kind,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    with open(destination, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(envelope, ensure_ascii=True) + "\n")
    return destination


def retry_call(
    operation_name: str,
    fn: Callable[[], Dict[str, Any]],
    attempts: int,
    base_backoff_seconds: float,
) -> Dict[str, Any]:
    capped_attempts = max(1, attempts)
    wait = max(0.0, base_backoff_seconds)
    last_result: Dict[str, Any] = {"ok": False, "error": "operation_not_run"}
    started = time.perf_counter()

    for attempt in range(1, capped_attempts + 1):
        current = fn()
        current["attempt"] = attempt
        if current.get("ok"):
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            current["elapsed_ms"] = elapsed_ms
            logger.info(
                "%s succeeded attempt=%s elapsed_ms=%s",
                operation_name,
                attempt,
                elapsed_ms,
            )
            return current

        last_result = current
        logger.warning(
            "%s failed attempt=%s error=%s",
            operation_name,
            attempt,
            str(current.get("error", "unknown_error"))[:240],
        )
        if attempt < capped_attempts and wait > 0:
            time.sleep(wait)
            wait *= 2

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    last_result["elapsed_ms"] = elapsed_ms
    last_result["attempt"] = capped_attempts
    return last_result
