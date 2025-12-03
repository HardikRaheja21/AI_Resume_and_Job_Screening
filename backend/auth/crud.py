<<<<<<< HEAD
from sqlmodel import Session, select
from ..models import User
from ..utils.security import get_password_hash, verify_password

def get_user_by_email(session: Session, email: str):
    return session.exec(select(User).where(User.email == email)).first()

def create_user(session: Session, email: str, password: str, full_name: str | None = None):
    user = User(email=email, hashed_password=get_password_hash(password), full_name=full_name)
=======
# # from sqlmodel import Session
# # from ..models import User
# # from ..utils.security import get_password_hash
# # from typing import Optional

# # def get_user_by_username(session: Session, username: str) -> Optional[User]:
# #     statement = session.exec(session.select(User).where(User.username == username))
# #     return statement.first()

# # def create_user(session: Session, username: str, password: str) -> User:
# #     user = User(username=username, hashed_password=get_password_hash(password))
# #     session.add(user)
# #     session.commit()
# #     session.refresh(user)
# #     return user
# from sqlmodel import Session, select
# from ..models import User
# from ..utils.security import get_password_hash
# from typing import Optional

# def get_user_by_username(session: Session, username: str) -> Optional[User]:
#     statement = select(User).where(User.username == username)
#     result = session.exec(statement)
#     return result.first()

# def create_user(session: Session, username: str, password: str) -> User:
#     user = User(
#         username=username,
#         hashed_password=get_password_hash(password)
#     )
#     session.add(user)
#     session.commit()
#     session.refresh(user)
#     return user
from sqlmodel import Session, select
from ..models import User
from ..utils.security import get_password_hash
from typing import Optional

def get_user_by_email(session: Session, email: str) -> Optional[User]:
    statement = select(User).where(User.email == email)
    result = session.exec(statement)
    return result.first()

def create_user(session: Session, email: str, password: str) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash(password)
    )
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
<<<<<<< HEAD

def authenticate_user(session: Session, email: str, password: str):
    user = get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
=======
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
