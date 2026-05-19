import logging
from ..utils.logging import set_request_context, clear_request_context
from ..utils import metrics
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from fastapi import BackgroundTasks

logger = logging.getLogger("resume_parser.background_tasks")

_TASK_STATUS: Dict[str, Dict[str, Any]] = {}
_RESUME_TASK_STATUS: Dict[int, str] = {}
_STATUS_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _update_status(task_id: str, updates: Dict[str, Any]) -> None:
    with _STATUS_LOCK:
        if task_id not in _TASK_STATUS:
            return
        _TASK_STATUS[task_id].update(updates)
        _TASK_STATUS[task_id]["updated_at"] = _now_iso()


def get_task_status(task_id: str) -> Dict[str, Any]:
    with _STATUS_LOCK:
        return _TASK_STATUS.get(task_id, {}).copy()


def get_resume_task_status(resume_id: int) -> Dict[str, Any]:
    with _STATUS_LOCK:
        task_id = _RESUME_TASK_STATUS.get(resume_id)
        if not task_id:
            return {"status": "idle"}
        return _TASK_STATUS.get(task_id, {}).copy()


def schedule_task(
    background_tasks: Optional[BackgroundTasks],
    task_name: str,
    fn: Callable[..., Any],
    *args: Any,
    track_resume_id: Optional[int] = None,
    request_id: Optional[str] = None,
    **kwargs: Any,
) -> str:
    task_id = f"{task_name}:{uuid.uuid4().hex}"
    task_record = {
        "task_id": task_id,
        "task_name": task_name,
        "status": "queued",
        "created_at": _now_iso(),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "request_id": request_id,
    }

    with _STATUS_LOCK:
        _TASK_STATUS[task_id] = task_record
        if track_resume_id is not None:
            _RESUME_TASK_STATUS[track_resume_id] = task_id

    logger.info(
        "scheduled_background_task",
        extra={
            "task_id": task_id,
            "task_name": task_name,
            "resume_id": track_resume_id,
            "request_id": request_id,
        },
    )
    if background_tasks is None:
        _update_status(task_id, {"status": "failed", "completed_at": _now_iso(), "error": "BackgroundTasks unavailable"})
        return task_id

    background_tasks.add_task(_run_task, task_id, fn, *args, **kwargs)
    return task_id


def _run_task(task_id: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    _update_status(task_id, {"status": "running", "started_at": _now_iso()})
    task_request_id = _TASK_STATUS.get(task_id, {}).get("request_id")
    logger.info(
        "background_task_start",
        extra={"task_id": task_id, "request_id": task_request_id},
    )
    try:
        # Propagate request id into structured logging context for this task
        if task_request_id:
            set_request_context(request_id=task_request_id)
        result = fn(*args, **kwargs)
        _update_status(task_id, {"status": "completed", "completed_at": _now_iso()})
        logger.info(
            "background_task_completed",
            extra={"task_id": task_id, "request_id": task_request_id},
        )
        return result
    except Exception as exc:
        logger.exception(
            "background_task_failed",
            extra={"task_id": task_id, "request_id": task_request_id},
        )
        try:
            metrics.inc_background_tasks_failed()
        except Exception:
            pass
        _update_status(task_id, {"status": "failed", "completed_at": _now_iso(), "error": str(exc)})
        return None
    finally:
        # Clear any request-specific context to avoid leaking between tasks
        try:
            clear_request_context()
        except Exception:
            pass
