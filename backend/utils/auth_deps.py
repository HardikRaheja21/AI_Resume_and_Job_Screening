# backend/utils/auth_deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from jose.exceptions import ExpiredSignatureError
from typing import Optional

from ..utils.security import decode_token
from ..database import get_session
from sqlmodel import Session
from ..models import User

security = HTTPBearer(auto_error=False)

def _strip_bearer(token: str) -> str:
    if token.lower().startswith("bearer "):
        return token[7:]
    return token

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_session),
):
    """
    Dependency to protect routes. It accepts either:
     - token (paste the raw JWT in Swagger "Authorize" for HTTP Bearer), or
     - "Bearer <token>" (we strip the prefix).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = _strip_bearer(credentials.credentials)
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        # user_id may be str, convert safely
        try:
            uid = int(user_id)
        except Exception:
            # if sub contained something else, we try string lookup
            uid = user_id

        user = session.get(User, uid)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
