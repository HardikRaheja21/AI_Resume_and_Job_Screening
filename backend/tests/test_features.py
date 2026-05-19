import json

from backend.routers import features as feature_routes
from backend import database
from backend.models import Resume, User
from backend.services import vector_service
from backend.utils.config import settings
from sqlmodel import Session, select


def _auth_token(client, email: str = "features@example.com", password: str = "Secret123"):
    client.post("/auth/signup", json={"email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    return login.json()["access_token"]


def _set_user_role(email: str, role: str):
    with Session(database.engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        assert user is not None
        user.role = role
        session.add(user)
        session.commit()


def _upload_one_resume(client, token, filename="candidate.txt"):
    files = [("resumes", (filename, b"Sam sam@example.com python fastapi sql docker", "text/plain"))]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}
    response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["results"][0]["id"]


def test_vector_service_builds_resume_chunks():
    resume = Resume(
        id=1,
        owner_id=1,
        filename="candidate.txt",
        filepath="/tmp/candidate.txt",
        parsed_text="Python FastAPI\nProject: built API service\nEducation: B.Tech\n7 years experience",
        extracted_skills="Python,FastAPI",
        education="B.Tech",
        experience_years=7.0,
    )
    chunks = vector_service._build_resume_chunks(resume)
    assert any(chunk["chunk_type"] == "skills" for chunk in chunks)
    assert any(chunk["chunk_type"] == "projects" for chunk in chunks)
    assert any(chunk["chunk_type"] == "experience" for chunk in chunks)
    assert any(chunk["chunk_type"] == "education" for chunk in chunks)


def test_pipeline_notes_tags_and_assign(client):
    token = _auth_token(client, "pipeline@example.com")
    resume_id = _upload_one_resume(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    stage = client.patch(f"/features/resumes/{resume_id}/stage", json={"stage": "shortlisted"}, headers=headers)
    assert stage.status_code == 200
    assert stage.json()["stage"] == "shortlisted"

    notes = client.patch(f"/features/resumes/{resume_id}/notes", json={"notes": "Strong backend profile"}, headers=headers)
    assert notes.status_code == 200

    tags = client.patch(
        f"/features/resumes/{resume_id}/tags",
        json={"tags": ["Python", "FastAPI", "SQL"]},
        headers=headers,
    )
    assert tags.status_code == 200
    assert "python" in tags.json()["tags"]

    assign = client.patch(
        f"/features/resumes/{resume_id}/assign",
        json={"assigned_to_email": "recruiter@example.com"},
        headers=headers,
    )
    assert assign.status_code == 200
    assert assign.json()["assigned_to_email"] == "recruiter@example.com"


def test_interview_questions_use_retrieval_context(client, monkeypatch):
    token = _auth_token(client, "retrieval_questions@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post(
        "/resumes/upload",
        data={"job_description": "Senior Backend Engineer with API and cloud experience"},
        files=[
            (
                "resumes",
                (
                    "resume_retrieval.txt",
                    b"Sam sam@example.com python fastapi sql docker project: Built a production API platform. experience: 5 years in backend engineering. Education: B.Tech in Computer Science.",
                    "text/plain",
                ),
            )
        ],
        headers=headers,
    )
    assert upload_response.status_code == 200
    resume_id = upload_response.json()["results"][0]["id"]

    captured = {}

    monkeypatch.setattr(feature_routes.ai_assistant, "is_ai_enabled", lambda: True)
    monkeypatch.setattr(feature_routes.ai_assistant, "generate_interview_questions_from_skills", lambda skills: (_ for _ in ()).throw(RuntimeError("skip skills generation")))

    def fake_build_interview_questions(*, candidate_name, role_context, tags, parsed_text, resume_context=""):
        captured["parsed_text"] = parsed_text
        captured["resume_context"] = resume_context
        return {"raw": json.dumps({"questions": ["What was the most challenging API project you worked on?", "How did you ensure quality across architectural boundaries?"]})}

    monkeypatch.setattr(feature_routes.ai_assistant, "build_interview_questions", fake_build_interview_questions)

    response = client.get(f"/features/resumes/{resume_id}/interview-questions", headers=headers)
    assert response.status_code == 200
    assert "questions" in response.json()
    assert captured.get("resume_context"), "Expected resume retrieval context to be used"
    assert "Built a production API platform" in captured["resume_context"] or "production API" in captured["resume_context"]


def test_recruiter_assistant_endpoint_returns_fallback_response(client, monkeypatch):
    token = _auth_token(client, "recruiter_assistant@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resume_id = _upload_one_resume(client, token)

    monkeypatch.setattr(feature_routes.ai_assistant, "is_ai_enabled", lambda: False)

    response = client.post(
        "/features/recruiter-assistant/query",
        json={"query": "Summarize this candidate's backend experience.", "resume_id": resume_id},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("answer"), str)
    assert payload.get("answer")
    assert isinstance(payload.get("supporting_chunks"), list)
    assert payload.get("candidate_references")
    assert payload.get("confidence") >= 0.0


def test_recruiter_assistant_endpoint_uses_ai_response(client, monkeypatch):
    token = _auth_token(client, "recruiter_ai@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resume_id = _upload_one_resume(client, token)

    monkeypatch.setattr(feature_routes.ai_assistant, "is_ai_enabled", lambda: True)
    monkeypatch.setattr(
        feature_routes.ai_assistant,
        "_call_openai",
        lambda prompt, max_output_tokens=450: json.dumps(
            {
                "answer": "Candidate shows strong backend and API experience.",
                "supporting_chunks": [
                    {
                        "resume_id": resume_id,
                        "resume_name": "candidate.txt",
                        "chunk_type": "experience",
                        "content_snippet": "Built a production API platform",
                    }
                ],
                "candidate_references": [
                    {
                        "resume_id": resume_id,
                        "name": "candidate.txt",
                        "filename": "candidate.txt",
                        "stage": "new",
                        "score": 0.92,
                    }
                ],
                "confidence": 0.92,
            }
        ),
    )

    response = client.post(
        "/features/recruiter-assistant/query",
        json={"query": "Who is best aligned with backend API development?", "resume_id": resume_id},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["confidence"] == 0.92
    assert payload["answer"] == "Candidate shows strong backend and API experience."
    assert len(payload["supporting_chunks"]) == 1
    assert payload["candidate_references"][0]["resume_id"] == resume_id


def test_ai_summary_uses_retrieved_resume_chunks(client, monkeypatch):
    token = _auth_token(client, "retrieval_summary@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post(
        "/resumes/upload",
        data={"job_description": "Senior Python Backend Engineer"},
        files=[
            (
                "resumes",
                (
                    "summary_retrieval.txt",
                    b"Sam sam@example.com python fastapi sql docker project: Built a production API platform. experience: 5 years in backend engineering. Education: B.Tech in Computer Science.",
                    "text/plain",
                ),
            )
        ],
        headers=headers,
    )
    assert upload_response.status_code == 200
    resume_id = upload_response.json()["results"][0]["id"]

    captured = {}
    monkeypatch.setattr(feature_routes.ai_assistant, "is_ai_enabled", lambda: True)

    def fake_build_candidate_summary(*, candidate_name, stage, score, tags, parsed_text, resume_context=""):
        captured["parsed_text"] = parsed_text
        captured["resume_context"] = resume_context
        return {"raw": json.dumps({"summary": "Candidate has strong backend experience.", "strengths": ["API design", "cloud operations"], "risks": ["Needs deeper frontend exposure"]})}

    monkeypatch.setattr(feature_routes.ai_assistant, "build_candidate_summary", fake_build_candidate_summary)

    response = client.get(f"/features/resumes/{resume_id}/ai-summary", headers=headers)
    assert response.status_code == 200
    assert response.json()["summary"] == "Candidate has strong backend experience."
    assert captured.get("resume_context"), "Expected resume retrieval context to be used"
    assert "Built a production API platform" in captured["resume_context"] or "production API" in captured["resume_context"]


def test_bulk_template_search_and_ai_endpoints(client):
    token = _auth_token(client, "bulk@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resume_id_1 = _upload_one_resume(client, token, "one.txt")
    resume_id_2 = _upload_one_resume(client, token, "two.txt")

    bulk = client.post(
        "/features/resumes/bulk",
        json={"resume_ids": [resume_id_1, resume_id_2], "action": "shortlist"},
        headers=headers,
    )
    assert bulk.status_code == 200
    assert bulk.json()["updated"] == 2

    template = client.post(
        "/features/templates",
        json={
            "title": "Backend Engineer",
            "description": "Backend role",
            "required_skills": ["python", "fastapi", "sql"],
            "optional_skills": ["docker"],
        },
        headers=headers,
    )
    assert template.status_code == 200
    listing = client.get("/features/templates", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    semantic = client.post(
        "/features/semantic-search",
        json={"query": "python fastapi", "limit": 5},
        headers=headers,
    )
    assert semantic.status_code == 200
    assert len(semantic.json()) >= 1

    ai_summary = client.get(f"/features/resumes/{resume_id_1}/ai-summary", headers=headers)
    assert ai_summary.status_code == 200
    assert "summary" in ai_summary.json()

    questions = client.get(f"/features/resumes/{resume_id_1}/interview-questions", headers=headers)
    assert questions.status_code == 200
    assert len(questions.json()["questions"]) >= 3

    export_csv = client.get("/features/export/csv", headers=headers)
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers.get("content-type", "")


def test_jobs_module_and_upload_linkage(client):
    token = _auth_token(client, "jobs@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_job = client.post(
        "/features/jobs",
        json={
            "title": "Backend Engineer",
            "description": "Role: Backend Engineer\nRequirements:\n- Python\n- FastAPI\n- SQL\nPreferred:\n- Docker\n2+ years of experience",
        },
        headers=headers,
    )
    assert create_job.status_code == 200
    job_payload = create_job.json()
    assert job_payload["title"] == "Backend Engineer"
    assert job_payload["role_category"] == "Backend Engineer"
    job_id = job_payload["id"]

    list_jobs = client.get("/features/jobs", headers=headers)
    assert list_jobs.status_code == 200
    assert len(list_jobs.json()) == 1

    upload = client.post(
        "/resumes/upload",
        data={"job_id": str(job_id)},
        files=[("resumes", ("joblinked.txt", b"Sam sam@example.com python fastapi sql docker 3 years of experience", "text/plain"))],
        headers=headers,
    )
    assert upload.status_code == 200
    assert upload.json()["jd_analysis"]["role_category"] == "Backend Engineer"

    resumes = client.get("/resumes", headers=headers)
    assert resumes.status_code == 200
    payload = resumes.json()
    assert len(payload) == 1
    assert payload[0]["job_id"] == job_id
    assert payload[0]["matched_job"] == "Backend Engineer"

    update_job = client.patch(
        f"/features/jobs/{job_id}",
        json={"is_active": False, "title": "Backend Engineer Closed"},
        headers=headers,
    )
    assert update_job.status_code == 200
    assert update_job.json()["is_active"] is False

    include_inactive = client.get("/features/jobs?include_inactive=true", headers=headers)
    assert include_inactive.status_code == 200
    assert len(include_inactive.json()) == 1


def test_job_scoped_history_and_analytics(client):
    token = _auth_token(client, "jobscope@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    backend_job = client.post(
        "/features/jobs",
        json={
            "title": "Backend Engineer",
            "description": "Role: Backend Engineer\nRequirements:\n- Python\n- FastAPI\n- SQL",
        },
        headers=headers,
    ).json()
    frontend_job = client.post(
        "/features/jobs",
        json={
            "title": "Frontend Engineer",
            "description": "Role: Frontend Engineer\nRequirements:\n- React\n- JavaScript\n- CSS",
        },
        headers=headers,
    ).json()

    upload_backend = client.post(
        "/resumes/upload",
        data={"job_id": str(backend_job["id"])},
        files=[("resumes", ("backend.txt", b"Ann ann@example.com python fastapi sql", "text/plain"))],
        headers=headers,
    )
    upload_frontend = client.post(
        "/resumes/upload",
        data={"job_id": str(frontend_job["id"])},
        files=[("resumes", ("frontend.txt", b"Ben ben@example.com react javascript css", "text/plain"))],
        headers=headers,
    )
    assert upload_backend.status_code == 200
    assert upload_frontend.status_code == 200

    filtered_history = client.get(
        "/resumes/search",
        params={"job_id": backend_job["id"]},
        headers=headers,
    )
    assert filtered_history.status_code == 200
    history_payload = filtered_history.json()
    assert len(history_payload) == 1
    assert history_payload[0]["matched_job"] == "Backend Engineer"

    filtered_stats = client.get(
        "/resumes/stats",
        params={"job_id": backend_job["id"]},
        headers=headers,
    )
    assert filtered_stats.status_code == 200
    assert filtered_stats.json()["total"] == 1

    funnel = client.get(
        "/features/analytics/funnel",
        params={"job_id": backend_job["id"]},
        headers=headers,
    )
    assert funnel.status_code == 200
    assert funnel.json()["total"] == 1

    shortlist_speed = client.get(
        "/features/analytics/time-to-shortlist",
        params={"job_id": backend_job["id"]},
        headers=headers,
    )
    assert shortlist_speed.status_code == 200
    assert shortlist_speed.json()["count"] in {0, 1}


def test_webhook_notifications_and_ats_sync(client, monkeypatch):
    token = _auth_token(client, "integrations@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resume_id = _upload_one_resume(client, token, "integrations.txt")

    monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", "https://example.com/slack")
    monkeypatch.setattr(settings, "TEAMS_WEBHOOK_URL", "https://example.com/teams")
    monkeypatch.setattr(settings, "ATS_SYNC_URL", "https://example.com/ats")
    monkeypatch.setattr(settings, "ATS_SYNC_API_KEY", "dummy-key")
    monkeypatch.setattr(
        feature_routes,
        "post_webhook",
        lambda *args, **kwargs: {"ok": True, "status_code": 200},
    )

    slack = client.post("/features/notify/slack", json={"message": "hello slack"}, headers=headers)
    teams = client.post("/features/notify/teams", json={"message": "hello teams"}, headers=headers)
    ats = client.post(f"/features/integrations/ats-sync/{resume_id}", json={"include_parsed_text": False}, headers=headers)

    assert slack.status_code == 200
    assert teams.status_code == 200
    assert ats.status_code == 200
    assert ats.json()["provider"] == "ats"


def test_integration_status_and_connectivity_test_endpoint(client, monkeypatch):
    token = _auth_token(client, "connectivity@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", "https://example.com/slack")
    monkeypatch.setattr(settings, "TEAMS_WEBHOOK_URL", "")
    monkeypatch.setattr(settings, "ATS_SYNC_URL", "https://example.com/ats")
    monkeypatch.setattr(
        feature_routes,
        "post_webhook",
        lambda *args, **kwargs: {"ok": True, "status_code": 200},
    )

    status_resp = client.get("/features/integrations/status", headers=headers)
    assert status_resp.status_code == 200
    payload = status_resp.json()
    assert payload["slack_configured"] is True
    assert payload["teams_configured"] is False
    assert payload["ats_configured"] is True

    test_resp = client.post(
        "/features/integrations/test",
        json={"provider": "slack", "message": "ping"},
        headers=headers,
    )
    assert test_resp.status_code == 200
    assert test_resp.json()["status"] == "ok"


def test_demo_seed_and_reset(client):
    token = _auth_token(client, "demo@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    seed = client.post("/features/demo/seed", json={"count": 4}, headers=headers)
    assert seed.status_code == 200
    assert seed.json()["created"] == 4

    listing = client.get("/resumes", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 4

    reset = client.post("/features/demo/reset", headers=headers)
    assert reset.status_code == 200
    assert reset.json()["reset"] is True
    assert reset.json()["deleted"]["resumes"] == 4

    listing_after = client.get("/resumes", headers=headers)
    assert listing_after.status_code == 200
    assert listing_after.json() == []


def test_admin_user_role_management(client):
    admin_email = "admin@example.com"
    recruiter_email = "recruiter@example.com"
    admin_token = _auth_token(client, admin_email)
    _set_user_role(admin_email, "admin")
    _auth_token(client, recruiter_email)

    headers = {"Authorization": f"Bearer {admin_token}"}
    list_resp = client.get("/features/admin/users", headers=headers)
    assert list_resp.status_code == 200
    users = list_resp.json()
    recruiter = next(u for u in users if u["email"] == recruiter_email)

    promote_resp = client.patch(
        f"/features/admin/users/{recruiter['id']}/role",
        json={"role": "admin"},
        headers=headers,
    )
    assert promote_resp.status_code == 200
    assert promote_resp.json()["role"] == "admin"


def test_semantic_search_fallback_when_embeddings_disabled(client, monkeypatch):
    token = _auth_token(client, "semantic@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    _upload_one_resume(client, token, "semantic.txt")
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", True)

    semantic = client.post(
        "/features/semantic-search",
        json={"query": "python fastapi", "limit": 5},
        headers=headers,
    )
    assert semantic.status_code == 200
    payload = semantic.json()
    assert len(payload) >= 1
    assert 0.0 <= payload[0]["score"] <= 1.0


def test_semantic_search_with_vector_store(client, monkeypatch, tmp_path):
    token = _auth_token(client, "vectorsearch@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", False)
    monkeypatch.setattr(settings, "VECTOR_DB_DIR", str(tmp_path / "vector_store"))

    resume_id = _upload_one_resume(client, token, "vector_search.txt")

    semantic = client.post(
        "/features/semantic-search",
        json={"query": "python fastapi backend", "limit": 5},
        headers=headers,
    )
    assert semantic.status_code == 200
    payload = semantic.json()
    assert any(item["id"] == resume_id for item in payload)
    assert all(0.0 <= item["score"] <= 1.0 for item in payload)


def test_semantic_retrieve_with_vector_store(client, monkeypatch, tmp_path):
    token = _auth_token(client, "vectorretrieve@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(settings, "MATCHER_DISABLE_EMBEDDINGS", False)
    monkeypatch.setattr(settings, "VECTOR_DB_DIR", str(tmp_path / "vector_store"))

    resume_id = _upload_one_resume(client, token, "vector_retrieve.txt")

    response = client.post(
        "/features/semantic-retrieve",
        json={"query": "python fastapi backend", "limit": 5, "max_chunks": 3},
        headers=headers,
    )
    assert response.status_code == 200
    result = response.json()
    assert any(item["id"] == resume_id for item in result)
    assert all("top_chunks" in item for item in result)


def test_ai_endpoints_use_heuristic_when_openai_not_configured(client, monkeypatch):
    token = _auth_token(client, "aifallback@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resume_id = _upload_one_resume(client, token, "ai.txt")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    summary = client.get(f"/features/resumes/{resume_id}/ai-summary", headers=headers)
    questions = client.get(f"/features/resumes/{resume_id}/interview-questions", headers=headers)

    assert summary.status_code == 200
    assert questions.status_code == 200
    assert summary.json()["provider"] == "heuristic"
    assert questions.json()["provider"] == "heuristic"


def test_adaptive_interview_and_final_selection_flow(client):
    token = _auth_token(client, "interviewflow@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resume_id = _upload_one_resume(client, token, "interview.txt")

    start = client.post(
        f"/features/resumes/{resume_id}/interview/start",
        json={
            "job_description": "Python FastAPI SQL backend engineer",
            "max_questions": 4,
            "send_invitation_email": False,
        },
        headers=headers,
    )
    assert start.status_code == 200
    start_payload = start.json()
    assert start_payload["status"] == "active"
    assert start_payload["current_question"]
    session_id = start_payload["session_id"]

    first_answer = client.post(
        f"/features/interviews/{session_id}/answer",
        json={
            "answer_text": "I would debug with logs, profiling, SQL explain plans, testing, and performance analysis because API bottlenecks often come from DB queries.",
            "input_type": "text",
        },
        headers=headers,
    )
    assert first_answer.status_code == 200
    assert first_answer.json()["answer_score"] >= 0

    second_answer = client.post(
        f"/features/interviews/{session_id}/answer",
        json={
            "answer_text": "I have used Python and FastAPI in production, with testing, security, optimization, and example-driven debugging workflows.",
            "input_type": "voice",
        },
        headers=headers,
    )
    assert second_answer.status_code == 200

    while True:
        current = client.get(f"/features/interviews/{session_id}", headers=headers)
        assert current.status_code == 200
        if current.json()["status"] == "completed":
            break
        answer = client.post(
            f"/features/interviews/{session_id}/answer",
            json={
                "answer_text": "I would answer with practical examples, performance tradeoffs, testing strategy, and secure implementation details.",
                "input_type": "text",
            },
            headers=headers,
        )
        assert answer.status_code == 200
        if answer.json()["completed"]:
            break

    finalized = client.post(
        f"/features/resumes/{resume_id}/finalize-selection",
        json={"send_email": False, "job_title": "Backend Engineer"},
        headers=headers,
    )
    assert finalized.status_code == 200
    finalized_payload = finalized.json()
    assert 0.0 <= finalized_payload["final_score"] <= 1.0
    assert finalized_payload["decision"] in {"selected", "hold", "rejected"}

    resume = client.get(f"/resumes/{resume_id}", headers=headers)
    assert resume.status_code == 200
    payload = resume.json()
    assert payload["interview_score"] is not None
    assert payload["final_score"] is not None
    assert payload["final_decision"] in {"selected", "hold", "rejected"}
