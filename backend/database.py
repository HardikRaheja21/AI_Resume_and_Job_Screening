from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine
from .utils.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False, connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {})


def init_db():
    if settings.AUTO_DB_BOOTSTRAP:
        SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session


def is_database_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
