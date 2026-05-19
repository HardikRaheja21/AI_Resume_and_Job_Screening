import json
import logging
import os
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

from .config import settings

_LOG_CONTEXT: ContextVar[Dict[str, Any]] = ContextVar("_log_context", default={})


def _safe_json_value(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def get_request_context() -> Dict[str, Any]:
    context = _LOG_CONTEXT.get() or {}
    return {k: _safe_json_value(v) for k, v in context.items()}


def set_request_context(**kwargs: Any) -> None:
    current = get_request_context()
    current.update({k: _safe_json_value(v) for k, v in kwargs.items() if v is not None})
    _LOG_CONTEXT.set(current)


def clear_request_context() -> None:
    _LOG_CONTEXT.set({})


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        payload.update(get_request_context())

        extra = {
            key: _safe_json_value(value)
            for key, value in record.__dict__.items()
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            }
        }

        payload.update(extra)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)
    formatter = JsonLogFormatter()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    log_file = settings.LOG_FILE or os.environ.get("LOG_FILE")
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
