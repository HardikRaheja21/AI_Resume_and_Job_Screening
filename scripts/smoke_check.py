from pathlib import Path
from urllib.request import Request, urlopen
import json
import os
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import is_database_ready
from backend.utils.config import settings


def check_local_prereqs() -> list[str]:
    issues: list[str] = []
    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "please_change_me":
        issues.append("JWT_SECRET_KEY is not set to a secure value.")
    upload_path = Path(settings.UPLOAD_DIR)
    if not upload_path.exists():
        issues.append(f"UPLOAD_DIR does not exist: {upload_path}")
    elif not os.access(upload_path, os.W_OK):
        issues.append(f"UPLOAD_DIR is not writable: {upload_path}")
    dead_letter_path = Path(settings.DEAD_LETTER_DIR)
    dead_letter_path.mkdir(parents=True, exist_ok=True)
    if not os.access(dead_letter_path, os.W_OK):
        issues.append(f"DEAD_LETTER_DIR is not writable: {dead_letter_path}")
    if not is_database_ready():
        issues.append("Database connectivity check failed.")
    return issues


def check_http_health(base_url: str) -> list[str]:
    issues: list[str] = []
    for endpoint in ("/healthz", "/readyz"):
        url = f"{base_url.rstrip('/')}{endpoint}"
        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=6) as response:
                if response.status != 200:
                    issues.append(f"{endpoint} returned HTTP {response.status}")
                    continue
                payload = json.loads(response.read().decode("utf-8") or "{}")
                if endpoint == "/healthz" and payload.get("status") != "ok":
                    issues.append("/healthz response status is not ok")
                if endpoint == "/readyz" and payload.get("status") != "ready":
                    issues.append("/readyz response status is not ready")
        except Exception as exc:
            issues.append(f"{endpoint} failed: {exc}")
    return issues


def main() -> int:
    base_url = os.environ.get("SMOKE_BASE_URL", "").strip()
    issues = check_local_prereqs()
    if base_url:
        issues.extend(check_http_health(base_url))

    if issues:
        print("SMOKE CHECK FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("SMOKE CHECK PASSED")
    if base_url:
        print(f"- HTTP checks against {base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
