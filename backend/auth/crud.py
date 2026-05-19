from sqlmodel import Session, select
from ..models import User
from ..utils.security import get_password_hash, verify_password

def get_user_by_email(session: Session, email: str):
    return session.exec(select(User).where(User.email == email)).first()

def create_user(session: Session, email: str, password: str, full_name: str | None = None):
    user = User(email=email, hashed_password=get_password_hash(password), full_name=full_name)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def authenticate_user(session: Session, email: str, password: str):
    user = get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
