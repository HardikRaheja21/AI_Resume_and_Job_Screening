from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from backend import database
from backend.auth import routes as auth_routes
from backend.main import app
from backend.resume_parser_service import email_sender
from backend.utils.config import settings


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_resumes.db"
    upload_dir = tmp_path / "uploads"
    db_url = f"sqlite:///{db_file.as_posix()}"

    monkeypatch.setattr(settings, "DATABASE_URL", db_url)
    monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir.as_posix())
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    auth_routes._LOGIN_FAILURES.clear()

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(database, "engine", engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[database.get_session] = override_get_session
    monkeypatch.setattr(email_sender, "queue_result_email", lambda *args, **kwargs: None)

    SQLModel.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
