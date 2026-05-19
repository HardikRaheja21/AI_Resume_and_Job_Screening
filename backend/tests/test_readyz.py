from fastapi.testclient import TestClient
from backend import main


def test_readyz_endpoint_monkeypatched(monkeypatch):
    # Avoid heavy checks by monkeypatching health.readiness_summary
    def fake_summary():
        return {"embedding_model": True, "vector_db": True, "ocr": True, "spacy": True}

    monkeypatch.setattr("backend.utils.health.readiness_summary", fake_summary)
    client = TestClient(main.app)
    resp = client.get("/readyz")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ready"
    assert data.get("embedding_model") is True
    assert data.get("vector_db") is True
    assert data.get("ocr") is True
    assert data.get("spacy") is True
