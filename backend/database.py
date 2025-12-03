<<<<<<< HEAD
from sqlmodel import SQLModel, create_engine, Session
from .utils.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False, connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {})

def init_db():
    SQLModel.metadata.create_all(engine)
=======
from sqlmodel import create_engine, Session, SQLModel
from .utils.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91

def get_session():
    with Session(engine) as session:
        yield session
