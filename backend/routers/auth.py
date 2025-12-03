# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm
# from sqlmodel import Session
# from ..database import get_session
# from ..auth import crud, schemas
# from ..utils.security import create_access_token, verify_password
# from datetime import timedelta
# from ..utils.config import settings

# router = APIRouter()

# @router.post("/register", response_model=schemas.UserRead)
# def register(user_in: schemas.UserCreate, session: Session = Depends(get_session)):
#     existing = crud.get_user_by_username(session, user_in.username)
#     if existing:
#         raise HTTPException(status_code=400, detail="Username already exists")
#     user = crud.create_user(session, user_in.username, user_in.password)
#     return schemas.UserRead(id=user.id, username=user.username)

# @router.post("/login", response_model=schemas.Token)
# def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
#     user = crud.get_user_by_username(session, form_data.username)
#     if not user or not verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
#     access_token = create_access_token(subject=str(user.id), expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
#     return {"access_token": access_token, "token_type": "bearer"}
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from ..database import get_session
from ..auth import crud, schemas
from ..utils.security import create_access_token, verify_password
from datetime import timedelta
from ..utils.config import settings

router = APIRouter()

@router.post("/register", response_model=schemas.UserRead)
def register(user_in: schemas.UserCreate, session: Session = Depends(get_session)):
    existing = crud.get_user_by_email(session, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(session, user_in.email, user_in.password)
    return schemas.UserRead(id=user.id, email=user.email)

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    # form_data.username contains email
    user = crud.get_user_by_email(session, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
