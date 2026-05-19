import logging
import os
import re
from time import perf_counter
from typing import Dict, List, Optional

from pdfminer.high_level import extract_text
from docx import Document

from ..services import nlp_extractor
from ..utils.config import settings
from .matcher import extract_skills
from . import ocr as resume_ocr

logger = logging.getLogger("resume_parser.parser")

def save_upload_file(upload_file, destination: str):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "wb") as buffer:
        buffer.write(upload_file.file.read())

def parse_pdf(file_path: str) -> str:
    text = ""
    try:
        text = extract_text(file_path) or ""
    except Exception as exc:
        logger.warning("Text extraction failed for %s: %s", file_path, exc)
        text = ""

    if text.strip() and len(text.strip()) > 40:
        return text

    if settings.OCR_ENABLE and resume_ocr.is_ocr_available():
        if resume_ocr.is_scanned_pdf(file_path) or len(text.strip()) < 40:
            try:
                start = perf_counter()
                ocr_text = resume_ocr.ocr_pdf(file_path)
                duration_ms = round((perf_counter() - start) * 1000, 2)
                if ocr_text.strip():
                    logger.info(
                        "ocr_completed",
                        extra={
                            "file_name": os.path.basename(file_path),
                            "duration_ms": duration_ms,
                            "method": "tesseract",
                        },
                    )
                    return ocr_text
            except Exception as exc:
                logger.warning(
                    "OCR extraction failed",
                    extra={
                        "file_name": os.path.basename(file_path),
                        "error": str(exc),
                    },
                )

    return text

def parse_docx(file_path: str) -> str:
    try:
        doc = Document(file_path)
        full = []
        for p in doc.paragraphs:
            full.append(p.text)
        return "\n".join(full)
    except Exception:
        return ""

def parse_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def parse_resume(file_path: str, filename: str) -> str:
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        return parse_pdf(file_path)
    if ext in ("docx", "doc"):
        return parse_docx(file_path)
    if ext in ("txt",):
        return parse_text(file_path)
    # fallback attempt: try pdf then docx
    text = parse_pdf(file_path)
    if text.strip():
        return text
    return parse_docx(file_path)


def clean_text(text: str) -> str:
    normalized = re.sub(r"[^\w@\.\+\#\-/\s]", " ", text or "")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def extract_candidate_name(text: str) -> Optional[str]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return None
    candidate = re.sub(r"[^A-Za-z\s]", "", lines[0]).strip()
    if 1 < len(candidate.split()) <= 4:
        return candidate[:120]
    return lines[0][:120]


def extract_email(text: str) -> Optional[str]:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    match = re.search(r"(\+?\d[\d\-\s]{8,}\d)", text or "")
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def extract_education(text: str) -> Optional[str]:
    patterns = [
        r"(b\.?\s?tech[^\n,;]*)",
        r"(m\.?\s?tech[^\n,;]*)",
        r"(bachelor[^\n,;]*)",
        r"(master[^\n,;]*)",
        r"(b\.?\s?e\.?[^\n,;]*)",
        r"(m\.?\s?e\.?[^\n,;]*)",
        r"(mba[^\n,;]*)",
    ]
    lowered = text.lower() if text else ""
    for pattern in patterns:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()[:160]
    return None


def extract_experience_years(text: str) -> Optional[float]:
    lowered = text.lower() if text else ""
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s+years?\s+of\s+experience",
        r"experience\s+of\s+(\d+(?:\.\d+)?)\+?\s+years?",
        r"(\d+(?:\.\d+)?)\+?\s+years?\s+experience",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def build_feature_text(
    *,
    name: Optional[str],
    skills: List[str],
    education: Optional[str],
    experience_years: Optional[float],
    parsed_text: str,
    roles: Optional[List[str]] = None,
    organizations: Optional[List[str]] = None,
) -> str:
    parts: List[str] = []
    if name:
        parts.append(name)
    if roles:
        parts.append(" ".join(roles))
    if organizations:
        parts.append(" ".join(organizations))
    if skills:
        parts.append(" ".join(skills))
    if education:
        parts.append(education)
    if experience_years is not None:
        parts.append(f"{experience_years} years experience")
    cleaned = clean_text(parsed_text)
    if cleaned:
        parts.append(cleaned[:1200])
    return " | ".join(part for part in parts if part)


def extract_structured_resume_data(text: str) -> Dict[str, object]:
    cleaned = clean_text(text)
    nlp_data = nlp_extractor.extract_resume_entities(text)
    skills = nlp_data.get("technologies") or extract_skills(cleaned)
    name = extract_candidate_name(text)
    education = extract_education(text)
    experience_years = extract_experience_years(text)
    structured = {
        "name": name,
        "email": extract_email(text),
        "phone": extract_phone(text),
        "education": education,
        "experience_years": experience_years,
        "skills": skills,
        "organizations": nlp_data.get("organizations", []),
        "roles": nlp_data.get("roles", []),
        "certifications": nlp_data.get("certifications", []),
        "project_keywords": nlp_data.get("project_keywords", []),
    }
    structured["feature_text"] = build_feature_text(
        name=name,
        roles=structured.get("roles"),
        organizations=structured.get("organizations"),
        skills=skills,
        education=education,
        experience_years=experience_years,
        parsed_text=cleaned,
    )
    return structured
