import json
import logging

from backend.utils.logging import (
    JsonLogFormatter,
    get_request_context,
    set_request_context,
    clear_request_context,
    _safe_json_value,
)


def test_request_context_set_get_clear():
    clear_request_context()
    assert get_request_context() == {}
    set_request_context(request_id="abc123", user_id=42)
    ctx = get_request_context()
    assert ctx.get("request_id") == "abc123"
    assert ctx.get("user_id") == 42
    clear_request_context()
    assert get_request_context() == {}


def test_safe_json_value_non_serializable():
    # sets are not JSON serializable; should return a string
    val = {1, 2, 3}
    safe = _safe_json_value(val)
    assert isinstance(safe, str)


def test_json_log_formatter_includes_context():
    clear_request_context()
    set_request_context(request_id="req-xyz", method="POST")
    formatter = JsonLogFormatter()
    logger = logging.getLogger("test_logger")
    record = logger.makeRecord(name=logger.name, level=logging.INFO, fn="", lno=0, msg="hello", args=(), exc_info=None)
    formatted = formatter.format(record)
    data = json.loads(formatted)
    assert data.get("message") == "hello"
    assert data.get("request_id") == "req-xyz"
    assert data.get("method") == "POST"