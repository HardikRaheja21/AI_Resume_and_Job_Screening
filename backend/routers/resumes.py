from typing import List, Optional
import os, re
from uuid import uuid4

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from sqlmodel import Session

from ..database import get_session
from ..models import Resume, User
from ..utils.config import settings
from ..utils.auth_deps import get_current_user

from .. import parser as resume_parser
from .. import matcher as resume_matcher
from .. import email_sender

router = APIRouter()

def _unique_filename(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    name = name.replace(" ", "_")
    return f"{name}_{uuid4().hex}{ext}"

def _extract_email(text: str) -> Optional[str]:
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    return m.group(0) if m else None

def _extract_name(text: str) -> Optional[str]:
    if not text:
        return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines[:6]:
        if "@" in ln or "http" in ln.lower() or any(c.isdigit() for c in ln):
            continue
        if len(ln.split()) <= 4:
            return ln[:120]
    return lines[0][:120] if lines else None

@router.post("/upload", summary="Upload JD (optional) + multiple resumes (protected)")
async def upload_resumes(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    jd_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one resume file.")

    # handle JD
    if jd_file:
        jd_filename = _unique_filename(jd_file.filename)
        jd_path = os.path.join(settings.UPLOAD_DIR, jd_filename)
        resume_parser.save_upload_file(jd_file, jd_path)
        jd_text_parsed = resume_parser.parse_resume(jd_path, jd_filename)
        jd_text = jd_text_parsed or jd_text

    jd_tokens = set(resume_matcher.extract_tokens(jd_text)) if jd_text else set()

    results = []
    for upload in files:
        orig = upload.filename or "unknown"
        saved_name = _unique_filename(orig)
        dest_path = os.path.join(settings.UPLOAD_DIR, saved_name)
        resume_parser.save_upload_file(upload, dest_path)

        parsed_text = resume_parser.parse_resume(dest_path, saved_name)

        email = _extract_email(parsed_text)
        name = _extract_name(parsed_text)

        score = 0.0
        match_info = {}
        if jd_text:
            try:
                match_info = resume_matcher.match_resume(parsed_text, jd_text)
                score = float(match_info.get("score", 0.0))
            except Exception:
                score = 0.0

        # persist
        rec_id = None
        try:
            rec = Resume(
                filename=orig,
                filepath=dest_path,
                parsed_text=parsed_text,
                email=email,
                name=name,
                matched_job=match_info.get("title") if isinstance(match_info, dict) else None,
                match_score=score
            )
            session.add(rec)
            session.commit()
            session.refresh(rec)
            rec_id = rec.id
        except Exception:
            session.rollback()

        # queue email
        try:
            threshold = float(getattr(settings, "SELECTION_THRESHOLD", 0.3))
            selected = score >= threshold
            if email:
                email_sender.queue_result_email(background_tasks, email, selected, match_info.get("title") or "Uploaded JD")
        except Exception:
            pass

        results.append({
            "id": rec_id,
            "filename": orig,
            "saved_as": saved_name,
            "email": email,
            "name": name,
            "score": round(score, 4),
            "selected": score >= float(getattr(settings, "SELECTION_THRESHOLD", 0.3))
        })

    return {
        "jd_summary": (jd_text[:300] + "...") if jd_text and len(jd_text) > 300 else (jd_text or ""),
        "total_resumes": len(results),
        "results": results
    }
