from datetime import datetime
import json
import logging
from time import perf_counter
from typing import List, Optional
import os
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from ..database import get_session
from ..models import Job, Resume, User
from ..resume_parser_service import email_sender
from ..resume_parser_service import matcher as resume_matcher
from ..resume_parser_service import parser as resume_parser
from ..services import task_service, vector_store
from ..utils.auth_deps import get_current_user
from ..utils.config import settings
from ..utils import metrics

logger = logging.getLogger("resume_parser.routers.resumes")

router = APIRouter(prefix="/resumes", tags=["resumes"])
SELECTION_THRESHOLD = 0.6
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt"}
ALLOWED_MIME_TYPES_BY_EXTENSION = {
    "pdf": {"application/pdf"},
    "doc": {"application/msword", "application/octet-stream"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    "txt": {"text/plain", "application/octet-stream"},
}


class UploadResumesRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    resume_files: List[UploadFile] = Field(default_factory=list)
    jd_text: Optional[str] = None
    jd_file: Optional[UploadFile] = None
    job_id: Optional[int] = None


class ResumeResult(BaseModel):
    model_config = ConfigDict(extra="ignore", exclude_none=True)

    id: int
    filename: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: Optional[str] = None
    experience_years: Optional[float] = None
    score: float
    summary: str
    selected: bool
    selected_label: str
    skills: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    optional_skills: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    related_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    role: Optional[str] = None
    role_category: Optional[str] = None
    jd_keywords: List[str] = Field(default_factory=list)
    score_breakdown: dict = Field(default_factory=dict)
    ai_evaluation: Optional[str] = None
    processing_status: Optional[str] = None


class JobDescriptionAnalysis(BaseModel):
    role: Optional[str] = None
    role_category: str = "General"
    required_skills: List[str] = Field(default_factory=list)
    optional_skills: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    minimum_experience_years: Optional[float] = None
    education_requirements: List[str] = Field(default_factory=list)


class UploadResumesResponse(BaseModel):
    jd_summary: str
    jd_analysis: JobDescriptionAnalysis
    total_resumes: int
    results: List[ResumeResult]


class ResumeRead(BaseModel):
    model_config = ConfigDict(extra="ignore", exclude_none=True)

    id: int
    owner_id: int
    job_id: Optional[int] = None
    filename: str
    filepath: str
    parsed_text: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    education: Optional[str] = None
    experience_years: Optional[float] = None
    extracted_skills: Optional[str] = None
    feature_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    matched_job: Optional[str] = None
    match_score: Optional[float] = None
    role: Optional[str] = None
    role_category: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    optional_skills: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    related_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    jd_keywords: List[str] = Field(default_factory=list)
    score_breakdown: dict = Field(default_factory=dict)
    jd_analysis: dict = Field(default_factory=dict)
    ai_evaluation: Optional[str] = None
    interview_score: Optional[float] = None
    final_score: Optional[float] = None
    final_decision: Optional[str] = None
    stage: str
    notes: Optional[str] = None
    tags: Optional[str] = None
    is_starred: bool = False
    assigned_to_email: Optional[str] = None
    duplicate_of_id: Optional[int] = None
    processing_status: Optional[str] = None
    processing_error: Optional[str] = None


class ResumeStats(BaseModel):
    total: int
    selected: int
    rejected: int
    average_score: float


class ResumeUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    matched_job: Optional[str] = None
    match_score: Optional[float] = None
    education: Optional[str] = None
    experience_years: Optional[float] = None


class ResumeDeleteResponse(BaseModel):
    deleted: bool
    id: int


def _normalize_filename(filename: str) -> str:
    return os.path.basename((filename or "").replace(" ", "_"))


def _file_extension(filename: str) -> str:
    return filename.lower().rsplit(".", 1)[-1] if "." in filename else ""


def _assert_allowed_extension(filename: str) -> None:
    ext = _file_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type for '{filename}'. Allowed types: {allowed}",
        )


def _assert_allowed_mime_type(upload: UploadFile, filename: str) -> None:
    ext = _file_extension(filename)
    allowed_mimes = ALLOWED_MIME_TYPES_BY_EXTENSION.get(ext, set())
    if not allowed_mimes:
        return
    content_type = (upload.content_type or "").lower().strip()
    if content_type and content_type not in allowed_mimes:
        allowed_list = ", ".join(sorted(allowed_mimes))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported MIME type '{content_type}' for '{filename}'. Allowed: {allowed_list}",
        )


def _assert_max_file_size(upload: UploadFile, filename: str) -> None:
    limit_bytes = settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024
    current_pos = upload.file.tell()
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > limit_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File '{filename}' exceeds {settings.MAX_UPLOAD_FILE_SIZE_MB}MB limit",
        )
    if current_pos:
        upload.file.seek(0)


def _build_unique_storage_path(filename: str) -> str:
    stored_name = f"{uuid4().hex}_{filename}"
    return os.path.join(settings.UPLOAD_DIR, stored_name)


def _assert_owned(record: Optional[Resume], current_user: User) -> Resume:
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    return record


def _json_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return []


def _json_dict(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _serialize_resume(record: Resume) -> dict:
    status = task_service.get_resume_task_status(int(record.id or 0))
    result = {
        "id": record.id,
        "owner_id": record.owner_id,
        "job_id": record.job_id,
        "filename": record.filename,
        "filepath": record.filepath,
        "parsed_text": record.parsed_text,
        "email": record.email,
        "phone": record.phone,
        "name": record.name,
        "education": record.education,
        "experience_years": record.experience_years,
        "extracted_skills": record.extracted_skills,
        "feature_text": record.feature_text,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "matched_job": record.matched_job,
        "match_score": record.match_score,
        "role": record.role,
        "role_category": record.role_category,
        "required_skills": _json_list(record.required_skills_json),
        "optional_skills": _json_list(record.optional_skills_json),
        "matched_skills": _json_list(record.matched_skills_json),
        "related_skills": _json_list(record.related_skills_json),
        "missing_skills": _json_list(record.missing_skills_json),
        "jd_keywords": _json_list(record.jd_keywords_json),
        "score_breakdown": _json_dict(record.score_breakdown_json),
        "jd_analysis": _json_dict(record.jd_analysis_json),
        "ai_evaluation": record.ai_evaluation_text,
        "interview_score": record.interview_score,
        "final_score": record.final_score,
        "final_decision": record.final_decision,
        "stage": record.stage,
        "notes": record.notes,
        "tags": record.tags,
        "is_starred": record.is_starred,
        "assigned_to_email": record.assigned_to_email,
        "duplicate_of_id": record.duplicate_of_id,
    }
    if status.get("status") and status["status"] != "idle":
        result["processing_status"] = status["status"]
    if status.get("error"):
        result["processing_error"] = status["error"]
    return result


def _apply_resume_filters(
    statement,
    job_id: Optional[int] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
):
    if job_id is not None:
        statement = statement.where(Resume.job_id == job_id)
    if email:
        statement = statement.where(Resume.email.ilike(f"%{email}%"))
    if name:
        statement = statement.where(Resume.name.ilike(f"%{name}%"))
    if min_score is not None:
        statement = statement.where(Resume.match_score >= min_score)
    if max_score is not None:
        statement = statement.where(Resume.match_score <= max_score)
    if created_from is not None:
        statement = statement.where(Resume.created_at >= created_from)
    if created_to is not None:
        statement = statement.where(Resume.created_at <= created_to)
    return statement


def parse_upload_request(
    files: Optional[List[UploadFile]] = File(None),
    resumes: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    jd: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    job_id: Optional[int] = Form(None),
) -> UploadResumesRequest:
    resume_uploads: List[UploadFile] = []
    if files:
        resume_uploads.extend(files)
    if resumes:
        resume_uploads.extend(resumes)
    if file:
        resume_uploads.append(file)

    normalized_jd_text = jd_text or job_description or jd
    return UploadResumesRequest(
        resume_files=resume_uploads,
        jd_text=normalized_jd_text,
        jd_file=jd_file,
        job_id=job_id,
    )


@router.get("/search", response_model=List[ResumeRead], summary="Search resumes (protected)")
def search_resumes(
    job_id: Optional[int] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    safe_limit = min(max(limit, 1), 200)
    safe_offset = max(offset, 0)
    statement = select(Resume).where(Resume.owner_id == current_user.id).order_by(Resume.created_at.desc())
    statement = _apply_resume_filters(
        statement,
        job_id=job_id,
        email=email,
        name=name,
        min_score=min_score,
        max_score=max_score,
        created_from=created_from,
        created_to=created_to,
    )
    statement = statement.offset(safe_offset).limit(safe_limit)
    rows = session.exec(statement).all()
    return [_serialize_resume(row) for row in rows]


@router.get("/stats", response_model=ResumeStats, summary="Resume analytics summary (protected)")
def resume_stats(
    job_id: Optional[int] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(Resume)
    statement = statement.where(Resume.owner_id == current_user.id)
    statement = _apply_resume_filters(
        statement,
        job_id=job_id,
        min_score=min_score,
        max_score=max_score,
        created_from=created_from,
        created_to=created_to,
    )
    rows = session.exec(statement).all()
    total = len(rows)
    selected_count = len([row for row in rows if (row.match_score or 0.0) >= SELECTION_THRESHOLD])
    rejected_count = total - selected_count
    average_score = sum((row.match_score or 0.0) for row in rows) / total if total else 0.0
    return {
        "total": total,
        "selected": selected_count,
        "rejected": rejected_count,
        "average_score": round(average_score, 4),
    }


@router.get("", response_model=List[ResumeRead], summary="List uploaded resumes (protected)")
def list_resumes(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    safe_limit = min(max(limit, 1), 200)
    safe_offset = max(offset, 0)
    statement = (
        select(Resume)
        .where(Resume.owner_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .offset(safe_offset)
        .limit(safe_limit)
    )
    rows = session.exec(statement).all()
    return [_serialize_resume(row) for row in rows]


@router.get("/{resume_id}", response_model=ResumeRead, summary="Get a resume by id (protected)")
def get_resume(
    resume_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = session.get(Resume, resume_id)
    return _serialize_resume(_assert_owned(record, current_user))


@router.patch("/{resume_id}", response_model=ResumeRead, summary="Update resume metadata (protected)")
def update_resume(
    resume_id: int,
    payload: ResumeUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = _assert_owned(session.get(Resume, resume_id), current_user)
    if payload.match_score is not None and not (0.0 <= payload.match_score <= 1.0):
        raise HTTPException(status_code=400, detail="match_score must be between 0 and 1")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(record, key, value)

    session.add(record)
    session.commit()
    session.refresh(record)
    return _serialize_resume(record)


@router.delete("/{resume_id}", response_model=ResumeDeleteResponse, summary="Delete a resume by id (protected)")
def delete_resume(
    resume_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = _assert_owned(session.get(Resume, resume_id), current_user)
    session.delete(record)
    session.commit()
    return {"deleted": True, "id": resume_id}


@router.post("/upload", response_model=UploadResumesResponse, summary="Upload JD and resumes (protected)")
async def upload_resumes(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: UploadResumesRequest = Depends(parse_upload_request),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Accept both legacy and current frontend field names:
    - resume files: files | resumes | file
    - JD text: jd_text | job_description | jd
    - JD file: jd_file
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    start = perf_counter()
    resume_uploads = payload.resume_files
    request_id = getattr(request.state, "request_id", None)
    if not resume_uploads:
        raise HTTPException(status_code=400, detail="Please provide at least one resume file")

    logger.info(
        "upload_started",
        extra={
            "request_id": request_id,
            "user_id": current_user.id,
            "resume_count": len(resume_uploads),
            "job_id": payload.job_id,
        },
    )

    normalized_jd_text = payload.jd_text
    jd_file = payload.jd_file
    selected_job: Optional[Job] = None
    if payload.job_id is not None:
        selected_job = session.get(Job, payload.job_id)
        if not selected_job or selected_job.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Job not found")
        if not normalized_jd_text and not jd_file:
            normalized_jd_text = selected_job.description
    if not normalized_jd_text and not jd_file:
        raise HTTPException(status_code=400, detail="Please provide either jd text, jd_file, or job_id")

    if jd_file:
        jd_filename = _normalize_filename(jd_file.filename)
        _assert_allowed_extension(jd_filename)
        _assert_allowed_mime_type(jd_file, jd_filename)
        _assert_max_file_size(jd_file, jd_filename)
        jd_path = _build_unique_storage_path(jd_filename)
        resume_parser.save_upload_file(jd_file, jd_path)
        normalized_jd_text = resume_parser.parse_resume(jd_path, jd_filename)

    if not (normalized_jd_text or "").strip():
        raise HTTPException(status_code=400, detail="Could not extract keywords from JD")

    jd_analysis = resume_matcher.parse_job_description(normalized_jd_text or "")
    results = []
    for upload in resume_uploads:
        fname = _normalize_filename(upload.filename)
        _assert_allowed_extension(fname)
        _assert_allowed_mime_type(upload, fname)
        _assert_max_file_size(upload, fname)
        dest_path = _build_unique_storage_path(fname)
        resume_parser.save_upload_file(upload, dest_path)

        text = resume_parser.parse_resume(dest_path, fname)
        structured = resume_parser.extract_structured_resume_data(text)
        email = structured.get("email")
        name = structured.get("name")
        phone = structured.get("phone")
        education = structured.get("education")
        experience_years = structured.get("experience_years")
        feature_text = str(structured.get("feature_text") or text)

        match_result = resume_matcher.compare_resume_to_jd(normalized_jd_text or "", text)
        score = float(match_result["score"])
        summary = str(match_result["summary"])
        skills = [str(s) for s in (match_result.get("skills") or [])]
        required_skills = [str(s) for s in (match_result.get("required_skills") or [])]
        optional_skills = [str(s) for s in (match_result.get("optional_skills") or [])]
        matched_skills = [str(s) for s in (match_result.get("matched_skills") or [])]
        related_skills = [str(s) for s in (match_result.get("related_skills") or [])]
        missing_skills = [str(s) for s in (match_result.get("missing_skills") or [])]
        current_jd_analysis = dict(match_result.get("jd_analysis") or jd_analysis)
        score_breakdown = dict(match_result.get("score_breakdown") or {})
        ai_evaluation = str(match_result.get("ai_evaluation") or "")
        selected = bool(match_result.get("selected", score >= 0.6))

        record = Resume(
            owner_id=current_user.id,
            job_id=selected_job.id if selected_job and selected_job.id is not None else None,
            filename=fname,
            filepath=dest_path,
            parsed_text=text,
            email=str(email) if email else None,
            phone=str(phone) if phone else None,
            name=str(name) if name else None,
            education=str(education) if education else None,
            experience_years=float(experience_years) if experience_years is not None else None,
            extracted_skills=",".join(skills),
            feature_text=feature_text,
            matched_job=selected_job.title if selected_job else "Uploaded JD",
            match_score=score,
            role=str(current_jd_analysis.get("role")) if current_jd_analysis.get("role") else None,
            role_category=str(current_jd_analysis.get("role_category")) if current_jd_analysis.get("role_category") else None,
            required_skills_json=json.dumps(required_skills),
            optional_skills_json=json.dumps(optional_skills),
            matched_skills_json=json.dumps(matched_skills),
            related_skills_json=json.dumps(related_skills),
            missing_skills_json=json.dumps(missing_skills),
            jd_keywords_json=json.dumps([str(s) for s in (current_jd_analysis.get("keywords") or [])]),
            score_breakdown_json=json.dumps(score_breakdown),
            jd_analysis_json=json.dumps(current_jd_analysis),
            ai_evaluation_text=ai_evaluation or None,
            final_score=score,
            final_decision="selected" if selected else "rejected",
            tags=",".join(skills),
        )
        if email:
            existing = session.exec(
                select(Resume)
                .where(Resume.owner_id == current_user.id)
                .where(Resume.email == email)
                .order_by(Resume.created_at.asc())
            ).first()
            if existing:
                record.duplicate_of_id = existing.id
        session.add(record)
        session.commit()
        session.refresh(record)

        try:
            task_service.schedule_task(
                background_tasks,
                "index_resume_chunks",
                vector_store.index_resume_chunks,
                record,
                track_resume_id=int(record.id or 0),
                request_id=request_id,
            )
        except Exception as exc:
            logger.warning(
                "Vector store indexing task scheduling failed",
                extra={
                    "request_id": request_id,
                    "resume_id": record.id,
                    "error": str(exc),
                },
            )

        email_sender.queue_result_email(
            background_tasks,
            email,
            selected,
            selected_job.title if selected_job else "Uploaded JD",
            request_id=request_id,
        )

        logger.info(
            "resume_uploaded",
            extra={
                "request_id": request_id,
                "resume_id": record.id,
                "file_name": fname,
                "score": round(score, 2),
                "selected": selected,
                "job_id": selected_job.id if selected_job else None,
            },
        )

        results.append(
            {
                "id": record.id,
                "filename": fname,
                "name": name,
                "email": email,
                "phone": phone,
                "education": education,
                "experience_years": experience_years,
                "score": round(score, 2),
                "summary": summary,
                "selected": selected,
                "selected_label": "Selected" if selected else "Not Selected",
                "skills": skills,
                "required_skills": required_skills,
                "optional_skills": optional_skills,
                "matched_skills": matched_skills,
                "related_skills": related_skills,
                "missing_skills": missing_skills,
                "role": current_jd_analysis.get("role"),
                "role_category": current_jd_analysis.get("role_category"),
                "jd_keywords": [str(s) for s in (current_jd_analysis.get("keywords") or [])],
                "score_breakdown": score_breakdown,
                "ai_evaluation": ai_evaluation,
                "processing_status": "queued",
            }
        )

    results = sorted(results, key=lambda item: float(item.get("score", 0.0)), reverse=True)

    jd_summary = normalized_jd_text or ""
    if len(jd_summary) > 300:
        jd_summary = jd_summary[:300] + "..."

    duration_ms = round((perf_counter() - start) * 1000, 2)
    try:
        metrics.observe_upload_processing_duration(duration_ms / 1000.0)
    except Exception:
        pass

    return {
        "jd_summary": jd_summary,
        "jd_analysis": jd_analysis,
        "total_resumes": len(results),
        "results": results,
    }
