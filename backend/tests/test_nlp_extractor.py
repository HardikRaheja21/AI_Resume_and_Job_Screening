import re

from backend.resume_parser_service import parser as resume_parser
from backend.resume_parser_service import matcher as resume_matcher
from backend.services import nlp_extractor


def test_nlp_extractor_falls_back_when_spacy_unavailable(monkeypatch):
    monkeypatch.setattr(nlp_extractor, "spacy", None)
    monkeypatch.setattr(nlp_extractor, "_get_nlp_model", lambda: None)

    found_technologies = nlp_extractor.extract_technologies("Python AWS Docker")
    assert "Python" in found_technologies
    assert "AWS" in found_technologies or "Docker" in found_technologies
    orgs = nlp_extractor.extract_organizations("Worked at Acme Corp and Azure Cloud Services")
    assert any(re.search(r"Acme", org, re.IGNORECASE) for org in orgs)
    certs = nlp_extractor.extract_certifications("AWS Certified Solutions Architect and PMP certification")
    assert any("Aws Certified" in cert or "Pmp" in cert for cert in certs)
    projects = nlp_extractor.extract_project_keywords("Project: built a Flask API with PostgreSQL and Docker deployment")
    assert any("Flask" in pk or "PostgreSQL" in pk or "Docker" in pk for pk in projects)


def test_parse_structured_resume_data_uses_nlp_entities(monkeypatch):
    def fake_resume_entities(text: str):
        return {
            "technologies": ["Python", "FastAPI", "AWS"],
            "organizations": ["Acme Corp"],
            "roles": ["Backend Engineer"],
            "certifications": ["AWS Certified Solutions Architect"],
            "project_keywords": ["API deployment", "cloud automation"],
        }

    monkeypatch.setattr(nlp_extractor, "extract_resume_entities", fake_resume_entities)
    structured = resume_parser.extract_structured_resume_data("Dummy resume text")

    assert structured["skills"] == ["Python", "FastAPI", "AWS"]
    assert structured["organizations"] == ["Acme Corp"]
    assert structured["roles"] == ["Backend Engineer"]
    assert "AWS Certified Solutions Architect" in structured["certifications"]
    assert "API deployment" in structured["project_keywords"]


def test_parse_jd_skill_buckets_uses_nlp_when_no_sections(monkeypatch):
    def fake_jd_entities(text: str):
        return {"technologies": ["Python", "FastAPI", "SQL"]}

    monkeypatch.setattr(nlp_extractor, "is_nlp_available", lambda: True)
    monkeypatch.setattr(nlp_extractor, "extract_jd_entities", fake_jd_entities)
    required, optional = resume_matcher.parse_jd_skill_buckets("We need Python developers with FastAPI and SQL experience.")

    assert "Python" in required
    assert "FastAPI" in required or "SQL" in required
    assert optional == []
