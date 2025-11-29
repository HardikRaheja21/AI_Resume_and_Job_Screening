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
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
