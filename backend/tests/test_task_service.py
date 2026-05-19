import pytest
from fastapi import BackgroundTasks

from backend.services import task_service


def test_schedule_task_creates_status_record(monkeypatch):
    tasks = BackgroundTasks()
    called = []

    def dummy_task(value):
        called.append(value)
        return "ok"

    task_id = task_service.schedule_task(tasks, "dummy", dummy_task, "hello", track_resume_id=123)
    assert task_id.startswith("dummy:")

    status = task_service.get_task_status(task_id)
    assert status["status"] == "queued"
    assert status["task_name"] == "dummy"
    assert status["created_at"] is not None

    # run scheduled background task manually
    for task in tasks.tasks:
        task.func(*task.args, **task.kwargs)

    status = task_service.get_task_status(task_id)
    assert status["status"] == "completed"
    resume_status = task_service.get_resume_task_status(123)
    assert resume_status["status"] == "completed"
    assert called == ["hello"]


def test_schedule_task_handles_exception(monkeypatch):
    tasks = BackgroundTasks()

    def failing_task():
        raise RuntimeError("boom")

    task_id = task_service.schedule_task(tasks, "fail", failing_task)
    assert task_id.startswith("fail:")

    for task in tasks.tasks:
        task.func(*task.args, **task.kwargs)

    status = task_service.get_task_status(task_id)
    assert status["status"] == "failed"
    assert "boom" in status["error"]


def test_upload_resumes_schedules_indexing(client, monkeypatch):
    from backend.routers import resumes as resumes_router

    scheduled = []

    def fake_schedule_task(background_tasks, task_name, fn, *args, track_resume_id=None, **kwargs):
        scheduled.append((task_name, track_resume_id))
        return "fake-task"

    monkeypatch.setattr(resumes_router.task_service, "schedule_task", fake_schedule_task)

    token = client.post("/auth/signup", json={"email": "taskuser@example.com", "password": "Secret123"})
    login = client.post("/auth/login", json={"email": "taskuser@example.com", "password": "Secret123"})
    auth_token = login.json()["access_token"]

    files = [
        ("resumes", ("candidate.txt", b"John Doe john@example.com python fastapi sql", "text/plain")),
    ]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}

    response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert scheduled
    assert scheduled[0][0] == "index_resume_chunks"
    assert scheduled[0][1] is not None
