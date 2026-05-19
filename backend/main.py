import os
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List
from uuid import uuid4
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.database import init_db, is_database_ready
from backend.utils.config import settings
from backend.utils.logging import clear_request_context, configure_logging, set_request_context
from backend.utils.tracing import configure_tracing, inject_trace_context, start_span
from backend.auth import routes as auth_routes
from backend.routers import resumes as resume_routes
from backend.routers import features as feature_routes
from backend.routers import processing as processing_routes
from backend.resume_parser_service import matcher as resume_matcher

logger = logging.getLogger("resume_parser.api")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# create upload dir
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

configure_logging()
configure_tracing()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    resume_matcher.warmup_model()
    yield


app = FastAPI(title="Resume Parser & Job Matching API", version="1.0", lifespan=lifespan)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

default_origins: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]
allow_origins = settings.CORS_ORIGINS or default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_payload(
    request_id: str,
    code: str,
    message: str,
    detail: Any = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        },
        # Backward compatibility for existing clients that read `detail`.
        "detail": message if detail is None else detail,
    }
    if detail is not None:
        payload["error"]["details"] = detail
    return payload


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    set_request_context(request_id=request_id, method=request.method, path=request.url.path)
    start = perf_counter()
    response = None
    trace_headers = inject_trace_context({})
    if trace_headers:
        request.state.trace_context = trace_headers
    try:
        with start_span(
            "http.request",
            {
                "http.method": request.method,
                "http.route": request.url.path,
                "request_id": request_id,
            },
        ):
            response = await call_next(request)
        duration_ms = round((perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    except Exception:
        duration_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise
    finally:
        clear_request_context()


@app.exception_handler(HTTPException)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    if exc.status_code == 401:
        code = "unauthorized"
    elif exc.status_code == 403:
        code = "forbidden"
    elif exc.status_code == 404:
        code = "not_found"
    elif exc.status_code == 422:
        code = "validation_error"
    else:
        code = "http_error"
    payload = _error_payload(request_id, code, message, exc.detail if not isinstance(exc.detail, str) else None)
    response = JSONResponse(status_code=exc.status_code, content=payload)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    detail = jsonable_encoder(exc.errors())
    payload = _error_payload(
        request_id=request_id,
        code="validation_error",
        message="Validation failed",
        detail=detail,
    )
    response = JSONResponse(status_code=422, content=payload)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    logger.exception("unhandled_exception id=%s path=%s", request_id, request.url.path, exc_info=exc)
    payload = _error_payload(
        request_id=request_id,
        code="internal_server_error",
        message="Internal server error",
    )
    response = JSONResponse(status_code=500, content=payload)
    response.headers["X-Request-ID"] = request_id
    return response

app.include_router(auth_routes.router)
app.include_router(resume_routes.router)
app.include_router(feature_routes.router)
app.include_router(processing_routes.router)
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "resume_parser"}


@app.get("/readyz")
def readyz():
    db_ok = is_database_ready()
    upload_dir_ok = os.path.isdir(settings.UPLOAD_DIR) and os.access(settings.UPLOAD_DIR, os.W_OK)

    # health of dependent subsystems
    from backend.utils import health

    health_summary = health.readiness_summary()

    all_ok = db_ok and upload_dir_ok and all(health_summary.values())
    if not all_ok:
        detail = {"database": db_ok, "upload_dir": upload_dir_ok}
        detail.update(health_summary)
        raise HTTPException(status_code=503, detail=detail)
    resp = {"status": "ready", "database": True, "upload_dir": True}
    resp.update(health_summary)
    return resp


@app.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse(
        "signup.html",
        {
            "request": request,
            "title": "Create account",
            "login_url": "/login",
            "api_client_src": "/frontend/assets/apiClient.js",
        },
    )


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "title": "Log in",
            "signup_url": "/signup",
            "api_client_src": "/frontend/assets/apiClient.js",
        },
    )
