<<<<<<< HEAD
# backend/utils/auth_deps.py
=======
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from typing import Optional
<<<<<<< HEAD

=======
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
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
<<<<<<< HEAD
    """
    Dependency to protect routes. It accepts either:
     - token (paste the raw JWT in Swagger "Authorize" for HTTP Bearer), or
     - "Bearer <token>" (we strip the prefix).
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

=======
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
    token = _strip_bearer(credentials.credentials)
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
<<<<<<< HEAD
        # user_id may be str, convert safely
        try:
            uid = int(user_id)
        except Exception:
            # if sub contained something else, we try string lookup
            uid = user_id

=======
        try:
            uid = int(user_id)
        except Exception:
            uid = user_id
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
        user = session.get(User, uid)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
