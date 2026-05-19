from backend.utils.config import settings
from backend.resume_parser_service import matcher


def _auth_token(client, email: str = "upload@example.com"):
    client.post("/auth/signup", json={"email": email, "password": "Secret123"})
    login = client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return login.json()["access_token"]


def test_upload_resumes_with_frontend_fields(client):
    token = _auth_token(client)
    files = [
        ("resumes", ("candidate.txt", b"John Doe john@example.com python fastapi sql", "text/plain")),
    ]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}

    response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_resumes"] == 1
    assert len(payload["results"]) == 1
    assert "id" in payload["results"][0]
    assert payload["results"][0]["filename"] == "candidate.txt"
    assert "score" in payload["results"][0]
    assert "summary" in payload["results"][0]
    assert payload["results"][0]["email"] == "john@example.com"
    assert "skills" in payload["results"][0]
    assert "jd_analysis" in payload
    assert payload["jd_analysis"]["role_category"] == "Backend Engineer"
    assert "score_breakdown" in payload["results"][0]
    assert "required_skill_score" in payload["results"][0]["score_breakdown"]


def test_upload_scanned_pdf_uses_ocr_fallback(client, monkeypatch, tmp_path):
    token = _auth_token(client, "ocr_upload@example.com")
    pdf_path = tmp_path / "scanned_resume.pdf"
    from PyPDF2 import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(pdf_path, "wb") as output_pdf:
        writer.write(output_pdf)

    monkeypatch.setattr(
        "backend.resume_parser_service.parser.resume_ocr.is_ocr_available",
        lambda: True,
    )
    monkeypatch.setattr(
        "backend.resume_parser_service.parser.resume_ocr.ocr_pdf",
        lambda path: "Jane Doe jane@example.com python fastapi sql docker",
    )

    with open(pdf_path, "rb") as upload_file:
        files = [("resumes", ("scanned_resume.pdf", upload_file, "application/pdf"))]
        data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}
        response = client.post(
            "/resumes/upload",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_resumes"] == 1
    assert payload["results"][0]["filename"] == "scanned_resume.pdf"
    assert payload["results"][0]["email"] == "jane@example.com"
    extracted_skills = [skill.lower() for skill in payload["results"][0]["skills"]]
    assert "python" in extracted_skills
    assert "docker" in extracted_skills


def test_matcher_returns_structured_jd_analysis_and_breakdown():
    job_description = """
    Role: Backend Developer
    Requirements:
    - Python
    - FastAPI
    - SQL
    - 2+ years of experience
    Preferred:
    - Docker
    - AWS
    """
    resume_text = """
    Jane Doe
    jane@example.com
    Backend engineer with 3 years of experience building Python APIs with FastAPI and SQL.
    Worked with Docker in production.
    """

    result = matcher.compare_resume_to_jd(job_description, resume_text)

    assert result["jd_analysis"]["role"] == "Backend Developer"
    assert result["jd_analysis"]["role_category"] == "Backend Engineer"
    assert result["jd_analysis"]["minimum_experience_years"] == 2.0
    assert "Python" in result["jd_analysis"]["required_skills"]
    assert "Docker" in result["jd_analysis"]["optional_skills"]
    assert 0.0 <= result["score_breakdown"]["required_skill_score"] <= 1.0
    assert 0.0 <= result["score_breakdown"]["experience_score"] <= 1.0
    assert result["score_breakdown"]["final_score"] == round(result["score"], 4)
    assert result["score_breakdown"]["required_skill_weight"] == 0.45
    assert result["score_breakdown"]["optional_skill_weight"] == 0.15
    assert result["score_breakdown"]["semantic_weight"] == 0.25
    assert result["score_breakdown"]["experience_weight"] == 0.15
    assert result["score_breakdown"]["total_weight"] == 1.0


def test_matcher_honors_custom_weight_configuration(monkeypatch):
    job_description = "Python FastAPI SQL"
    resume_text = "Experienced backend engineer with Python, FastAPI, and SQL skills."

    monkeypatch.setattr(settings, "MATCHER_REQUIRED_SKILL_WEIGHT", 1.0)
    monkeypatch.setattr(settings, "MATCHER_OPTIONAL_SKILL_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "MATCHER_SEMANTIC_WEIGHT", 0.0)
    monkeypatch.setattr(settings, "MATCHER_EXPERIENCE_WEIGHT", 0.0)

    result = matcher.compare_resume_to_jd(job_description, resume_text)

    assert result["score_breakdown"]["required_skill_weight"] == 1.0
    assert result["score_breakdown"]["optional_skill_weight"] == 0.0
    assert result["score_breakdown"]["semantic_weight"] == 0.0
    assert result["score_breakdown"]["experience_weight"] == 0.0
    assert result["score"] == result["score_breakdown"]["required_skill_score"]


def test_list_and_get_uploaded_resume(client):
    token = _auth_token(client)
    files = [
        (
            "resumes",
            (
                "candidate.txt",
                b"Jane Doe\njane@example.com\n+91 9876543210\nB.Tech AIML\n2 years of experience\npython fastapi sql",
                "text/plain",
            ),
        ),
    ]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}

    upload_response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_response.status_code == 200

    listing_response = client.get(
        "/resumes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing_response.status_code == 200
    listing = listing_response.json()
    assert len(listing) == 1
    assert listing[0]["filename"] == "candidate.txt"
    resume_id = listing[0]["id"]

    detail_response = client.get(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == resume_id
    assert "owner_id" in detail
    assert detail["filename"] == "candidate.txt"
    assert detail["phone"] == "+91 9876543210"
    assert detail["education"] is not None
    assert detail["experience_years"] == 2.0
    assert detail["feature_text"]
    assert isinstance(detail["score_breakdown"], dict)
    assert "semantic_score" in detail["score_breakdown"]
    assert isinstance(detail["jd_analysis"], dict)
    assert detail["role_category"] == "Backend Engineer"


def test_history_endpoints_persist_explainability_fields(client):
    token = _auth_token(client, "history@example.com")
    files = [
        ("resumes", ("candidate.txt", b"Alex alex@example.com python fastapi sql docker 3 years of experience", "text/plain")),
    ]
    data = {
        "job_description": """
        Role: Backend Developer
        Requirements:
        - Python
        - FastAPI
        - SQL
        Preferred:
        - Docker
        - AWS
        2+ years of experience
        """
    }

    upload_response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_response.status_code == 200

    listing_response = client.get("/resumes", headers={"Authorization": f"Bearer {token}"})
    assert listing_response.status_code == 200
    listing = listing_response.json()
    assert len(listing) == 1
    row = listing[0]
    assert row["role"] == "Backend Developer"
    assert row["role_category"] == "Backend Engineer"
    assert "Python" in row["required_skills"]
    assert "Docker" in row["optional_skills"]
    assert isinstance(row["jd_analysis"], dict)
    assert isinstance(row["score_breakdown"], dict)
    assert row["score_breakdown"]["final_score"] == round(float(row["match_score"]), 4)


def test_upload_rejects_unsupported_file_type(client):
    token = _auth_token(client)
    files = [
        ("resumes", ("candidate.exe", b"binary-data", "application/octet-stream")),
    ]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}

    response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_search_and_stats_endpoints(client):
    token = _auth_token(client)
    files = [
        ("resumes", ("candidate1.txt", b"Alice alice@example.com python fastapi sql docker", "text/plain")),
        ("resumes", ("candidate2.txt", b"Bob bob@example.com react javascript css html", "text/plain")),
    ]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}

    upload_response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["total_resumes"] == 2

    search_response = client.get(
        "/resumes/search",
        params={"email": "alice@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert len(search_payload) == 1
    assert search_payload[0]["email"] == "alice@example.com"

    stats_response = client.get(
        "/resumes/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["total"] == 2
    assert stats_payload["selected"] + stats_payload["rejected"] == 2
    assert isinstance(stats_payload["average_score"], float)


def test_update_and_delete_resume(client):
    token = _auth_token(client)
    files = [
        ("resumes", ("candidate.txt", b"Carol carol@example.com python fastapi sql", "text/plain")),
    ]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}
    upload_response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_response.status_code == 200

    listing_response = client.get("/resumes", headers={"Authorization": f"Bearer {token}"})
    resume_id = listing_response.json()[0]["id"]

    patch_response = client.patch(
        f"/resumes/{resume_id}",
        json={"matched_job": "Backend Developer", "match_score": 0.95},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_response.status_code == 200
    patch_payload = patch_response.json()
    assert patch_payload["matched_job"] == "Backend Developer"
    assert patch_payload["match_score"] == 0.95

    bad_patch_response = client.patch(
        f"/resumes/{resume_id}",
        json={"match_score": 1.5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_patch_response.status_code == 400
    assert "match_score must be between 0 and 1" in bad_patch_response.json()["detail"]

    delete_response = client.delete(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True, "id": resume_id}

    missing_response = client.get(
        f"/resumes/{resume_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing_response.status_code == 404


def test_user_cannot_access_other_users_resume(client):
    token_user_a = _auth_token(client, "ownera@example.com")
    token_user_b = _auth_token(client, "ownerb@example.com")

    files = [
        ("resumes", ("candidate.txt", b"Owner A a@example.com python fastapi sql", "text/plain")),
    ]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}
    upload_response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token_user_a}"},
    )
    assert upload_response.status_code == 200
    resume_id = upload_response.json()["results"][0]["id"]

    user_b_list = client.get("/resumes", headers={"Authorization": f"Bearer {token_user_b}"})
    assert user_b_list.status_code == 200
    assert user_b_list.json() == []

    user_b_detail = client.get(f"/resumes/{resume_id}", headers={"Authorization": f"Bearer {token_user_b}"})
    assert user_b_detail.status_code == 404

    user_b_delete = client.delete(f"/resumes/{resume_id}", headers={"Authorization": f"Bearer {token_user_b}"})
    assert user_b_delete.status_code == 404


def test_upload_rejects_file_exceeding_size_limit(client, monkeypatch):
    token = _auth_token(client, "sizelimit@example.com")
    monkeypatch.setattr(settings, "MAX_UPLOAD_FILE_SIZE_MB", 1)

    oversized = b"x" * (2 * 1024 * 1024)
    files = [
        ("resumes", ("big_resume.txt", oversized, "text/plain")),
    ]
    data = {"job_description": "Looking for Python FastAPI SQL backend engineer"}

    response = client.post(
        "/resumes/upload",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "exceeds 1MB limit" in response.json()["detail"]
