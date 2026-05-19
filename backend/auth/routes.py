from collections import defaultdict, deque
from time import time
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from pydantic import EmailStr
from sqlmodel import Session
from ..database import get_session
from .schemas import LoginRequest, UserCreate, Token, UserRead
from . import crud
from ..utils.security import create_access_token
from ..utils.config import settings
from ..utils.auth_deps import get_current_user
from ..models import User

router = APIRouter(prefix="/auth", tags=["auth"])
_LOGIN_FAILURES: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit_key(email: str, request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{email.lower()}|{client_ip}"


def _is_rate_limited(key: str) -> bool:
    now = time()
    window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    attempts = settings.LOGIN_RATE_LIMIT_ATTEMPTS
    failures = _LOGIN_FAILURES[key]
    while failures and (now - failures[0]) > window:
        failures.popleft()
    return len(failures) >= attempts


def _record_login_failure(key: str) -> None:
    _LOGIN_FAILURES[key].append(time())


def _clear_login_failures(key: str) -> None:
    _LOGIN_FAILURES.pop(key, None)

@router.post("/signup", response_model=UserRead)
@router.post("/register", response_model=UserRead)
def signup(payload: UserCreate, session: Session = Depends(get_session)):
    existing = crud.get_user_by_email(session, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(session, payload.email, payload.password, payload.full_name)
    return user


async def get_login_request(
    request: Request,
    # Form fields to make Swagger UI show email/password inputs in docs
    email: Optional[EmailStr] = Form(default=None),
    password: Optional[str] = Form(default=None),
) -> LoginRequest:
    if email and password:
        return LoginRequest(email=email, password=password)
    try:
        body = await request.json()
    except Exception:
        body = None
    if isinstance(body, dict):
        try:
            return LoginRequest.model_validate(body)
        except Exception:
            pass
    raise HTTPException(status_code=400, detail="Email and password are required")


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    payload: LoginRequest = Depends(get_login_request),
    session: Session = Depends(get_session),
):
    key = _rate_limit_key(str(payload.email), request)
    if _is_rate_limited(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please retry later.",
        )
    user = crud.authenticate_user(session, str(payload.email), str(payload.password))
    if not user:
        _record_login_failure(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    _clear_login_failures(key)
    token = create_access_token(subject=str(user.id))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
