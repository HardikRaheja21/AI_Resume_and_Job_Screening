from typing import Any, Dict, Optional

import httpx

from .reliability import retry_call, write_dead_letter
from ..utils.config import settings

def post_webhook(
    url: str,
    payload: Dict[str, Any],
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout_seconds: float = 8.0,
) -> Dict[str, Any]:
    if not url:
        return {"ok": False, "status_code": None, "error": "Webhook URL not configured"}

    def _send_once() -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=timeout_seconds or settings.WEBHOOK_TIMEOUT_SECONDS) as client:
                response = client.post(url, json=payload, headers=headers or {})
            if 200 <= response.status_code < 300:
                return {"ok": True, "status_code": response.status_code}
            return {
                "ok": False,
                "status_code": response.status_code,
                "error": f"Webhook rejected payload with status {response.status_code}",
                "body": response.text[:500],
            }
        except Exception as exc:
            return {"ok": False, "status_code": None, "error": str(exc)}

    result = retry_call(
        operation_name="webhook_post",
        fn=_send_once,
        attempts=settings.WEBHOOK_RETRY_ATTEMPTS,
        base_backoff_seconds=settings.WEBHOOK_RETRY_BACKOFF_SECONDS,
    )
    if not result.get("ok"):
        dead_letter_path = write_dead_letter(
            "webhook",
            {
                "url": url,
                "payload": payload,
                "headers": headers or {},
                "result": result,
            },
        )
        result["dead_letter"] = dead_letter_path
    return result
