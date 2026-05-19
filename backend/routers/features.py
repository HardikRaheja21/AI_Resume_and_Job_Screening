from datetime import datetime
from io import StringIO
import json
from typing import List, Optional
import random

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..database import get_session
from ..integrations.webhooks import post_webhook
from ..models import ActivityLog, InterviewAnswer, InterviewSession, Job, JobTemplate, Resume, User
from ..resume_parser_service import email_sender
from ..services import ai_assistant
from ..services import interview_system
from ..services import recruiter_assistant
from ..services import vector_search
from ..services import vector_service
from ..utils.auth_deps import get_current_user
from ..utils.config import settings

router = APIRouter(prefix="/features", tags=["features"])

VALID_STAGES = ["new", "screened", "shortlisted", "interview", "offer", "rejected"]
VALID_ROLES = {"recruiter", "admin"}


def _build_resume_context_from_chunks(chunks: List[dict]) -> str:
    parts: List[str] = []
    for chunk in chunks:
        snippet = str(chunk.get("content_snippet", "") or "").strip()
        if snippet:
            parts.append(f"{str(chunk.get('chunk_type', 'summary')).title()}: {snippet}")
    return "\n".join(parts)


class ResumeStageRequest(BaseModel):
    stage: str


class ResumeNoteRequest(BaseModel):
    notes: str


class ResumeTagRequest(BaseModel):
    tags: List[str]


class BulkActionRequest(BaseModel):
    resume_ids: List[int]
    action: str
    stage: Optional[str] = None


class AssignRequest(BaseModel):
    assigned_to_email: str


class JobTemplateRequest(BaseModel):
    title: str
    description: str
    required_skills: List[str] = []
    optional_skills: List[str] = []


class JobCreateRequest(BaseModel):
    title: str
    description: str


class JobUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class JobRead(BaseModel):
    id: int
    owner_id: int
    title: str
    description: str
    role: Optional[str]
    role_category: Optional[str]
    required_skills: List[str]
    optional_skills: List[str]
    keywords: List[str]
    education_requirements: List[str]
    minimum_experience_years: Optional[float]
    is_active: bool


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 20


class SemanticRetrieveRequest(BaseModel):
    query: str
    limit: int = 10
    max_chunks: int = 3


class RecruiterAssistantRequest(BaseModel):
    query: str
    resume_id: Optional[int] = None
    limit: int = 5


class RecruiterAssistantChunk(BaseModel):
    resume_id: int
    resume_name: Optional[str]
    chunk_type: str
    content_snippet: str


class RecruiterAssistantReference(BaseModel):
    resume_id: int
    name: Optional[str]
    filename: Optional[str]
    stage: Optional[str]
    score: float


class RecruiterAssistantResponse(BaseModel):
    answer: str
    supporting_chunks: List[RecruiterAssistantChunk] = Field(default_factory=list)
    candidate_references: List[RecruiterAssistantReference] = Field(default_factory=list)
    confidence: float = 0.0


class SemanticChunkResult(BaseModel):
    chunk_type: str
    content_snippet: str
    score: float


class SemanticRetrieveResult(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    filename: str
    score: float
    stage: Optional[str]
    top_chunks: List[SemanticChunkResult] = Field(default_factory=list)


class SlackNotifyRequest(BaseModel):
    message: str


class TeamSummary(BaseModel):
    email: str
    role: str
    resumes_owned: int


class AtsSyncRequest(BaseModel):
    include_parsed_text: bool = False


class IntegrationTestRequest(BaseModel):
    provider: str
    message: str = "Resume parser connectivity test"


class DemoSeedRequest(BaseModel):
    count: int = 5


class UserRoleUpdateRequest(BaseModel):
    role: str


class AdminUserRead(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool


class StartInterviewRequest(BaseModel):
    job_description: Optional[str] = None
    max_questions: int = 5
    send_invitation_email: bool = False


class SubmitInterviewAnswerRequest(BaseModel):
    answer_text: str
    input_type: str = "text"


class FinalizeSelectionRequest(BaseModel):
    send_email: bool = True
    job_title: Optional[str] = None


class InterviewAnswerRead(BaseModel):
    question_index: int
    question_text: str
    answer_text: str
    input_type: str
    score: float
    feedback: Optional[str]
    matched_keywords: List[str]
    difficulty_before: int
    difficulty_after: int


class InterviewSessionRead(BaseModel):
    session_id: int
    resume_id: int
    status: str
    current_question_index: int
    difficulty_level: int
    question_count: int
    max_questions: int
    average_score: float
    recommended_decision: Optional[str]
    current_question: Optional[str]
    current_expected_keywords: List[str]
    answers: List[InterviewAnswerRead]


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def _owned_resume(session: Session, current_user: User, resume_id: int) -> Resume:
    record = session.get(Resume, resume_id)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    return record


def _owned_session(session: Session, current_user: User, session_id: int) -> InterviewSession:
    record = session.get(InterviewSession, session_id)
    if not record or record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return record


def _json_list(raw_text: Optional[str]) -> List[str]:
    if not raw_text:
        return []
    try:
        parsed = json.loads(raw_text)
    except Exception:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _serialize_job(record: Job) -> JobRead:
    return JobRead(
        id=int(record.id or 0),
        owner_id=record.owner_id,
        title=record.title,
        description=record.description,
        role=record.role,
        role_category=record.role_category,
        required_skills=_json_list(record.required_skills_json),
        optional_skills=_json_list(record.optional_skills_json),
        keywords=_json_list(record.keywords_json),
        education_requirements=_json_list(record.education_requirements_json),
        minimum_experience_years=record.minimum_experience_years,
        is_active=bool(record.is_active),
    )


def _load_answers(session: Session, session_id: int) -> List[InterviewAnswer]:
    return session.exec(
        select(InterviewAnswer)
        .where(InterviewAnswer.session_id == session_id)
        .order_by(InterviewAnswer.question_index.asc())
    ).all()


def _serialize_session(
    session_record: InterviewSession,
    answers: List[InterviewAnswer],
) -> InterviewSessionRead:
    question_plan = _safe_json_extract(session_record.question_plan_json or "") or {}
    questions = question_plan.get("questions") or []
    current_idx = session_record.current_question_index
    current_item = questions[current_idx] if 0 <= current_idx < len(questions) else {}
    return InterviewSessionRead(
        session_id=int(session_record.id or 0),
        resume_id=session_record.resume_id,
        status=session_record.status,
        current_question_index=session_record.current_question_index,
        difficulty_level=session_record.difficulty_level,
        question_count=session_record.question_count,
        max_questions=session_record.max_questions,
        average_score=round(float(session_record.average_score or 0.0), 2),
        recommended_decision=session_record.recommended_decision,
        current_question=current_item.get("question"),
        current_expected_keywords=[str(item) for item in (current_item.get("expected_keywords") or [])],
        answers=[
            InterviewAnswerRead(
                question_index=row.question_index,
                question_text=row.question_text,
                answer_text=row.answer_text,
                input_type=row.input_type,
                score=round(float(row.score or 0.0), 2),
                feedback=row.feedback,
                matched_keywords=[item for item in (row.matched_keywords or "").split(",") if item],
                difficulty_before=row.difficulty_before,
                difficulty_after=row.difficulty_after,
            )
            for row in answers
        ],
    )


def _log_action(session: Session, current_user: User, action: str, resume_id: Optional[int], details: str = ""):
    log = ActivityLog(
        owner_id=current_user.id,
        resume_id=resume_id,
        action=action,
        details=details or None,
    )
    session.add(log)
    session.commit()


def _safe_json_extract(raw_text: str) -> Optional[dict]:
    raw = (raw_text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except Exception:
        return None


def _token_overlap_score(query: str, text: str) -> float:
    query_tokens = {t for t in (query or "").lower().split() if t}
    text_tokens = {t for t in (text or "").lower().split() if t}
    if not query_tokens:
        return 0.0
    return len(query_tokens.intersection(text_tokens)) / len(query_tokens)


@router.patch("/resumes/{resume_id}/stage")
def update_stage(
    resume_id: int,
    payload: ResumeStageRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    stage = payload.stage.strip().lower()
    if stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Allowed: {', '.join(VALID_STAGES)}")
    record = _owned_resume(session, current_user, resume_id)
    record.stage = stage
    record.updated_at = datetime.utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    _log_action(session, current_user, "stage_update", resume_id, f"stage={stage}")
    return {"id": record.id, "stage": record.stage}


@router.patch("/resumes/{resume_id}/notes")
def update_notes(
    resume_id: int,
    payload: ResumeNoteRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = _owned_resume(session, current_user, resume_id)
    record.notes = payload.notes.strip()
    record.updated_at = datetime.utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    _log_action(session, current_user, "note_update", resume_id)
    return {"id": record.id, "notes": record.notes}


@router.patch("/resumes/{resume_id}/tags")
def update_tags(
    resume_id: int,
    payload: ResumeTagRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = _owned_resume(session, current_user, resume_id)
    clean_tags = sorted({tag.strip().lower() for tag in payload.tags if tag.strip()})
    record.tags = ",".join(clean_tags)
    record.updated_at = datetime.utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    _log_action(session, current_user, "tag_update", resume_id, record.tags or "")
    return {"id": record.id, "tags": clean_tags}


@router.patch("/resumes/{resume_id}/assign")
def assign_resume(
    resume_id: int,
    payload: AssignRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = _owned_resume(session, current_user, resume_id)
    record.assigned_to_email = payload.assigned_to_email.strip().lower()
    record.updated_at = datetime.utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    _log_action(session, current_user, "assign", resume_id, record.assigned_to_email or "")
    return {"id": record.id, "assigned_to_email": record.assigned_to_email}


@router.post("/resumes/bulk")
def bulk_action(
    payload: BulkActionRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not payload.resume_ids:
        raise HTTPException(status_code=400, detail="resume_ids cannot be empty")
    records = session.exec(
        select(Resume).where(Resume.owner_id == current_user.id).where(Resume.id.in_(payload.resume_ids))
    ).all()
    if not records:
        return {"updated": 0}

    action = payload.action.strip().lower()
    if action == "delete":
        for record in records:
            session.delete(record)
    else:
        for record in records:
            if action == "shortlist":
                record.stage = "shortlisted"
            elif action == "reject":
                record.stage = "rejected"
            elif action == "star":
                record.is_starred = True
            elif action == "unstar":
                record.is_starred = False
            elif action == "set_stage":
                stage = (payload.stage or "").strip().lower()
                if stage not in VALID_STAGES:
                    raise HTTPException(status_code=400, detail="Invalid stage for set_stage")
                record.stage = stage
            else:
                raise HTTPException(status_code=400, detail="Unsupported bulk action")
            record.updated_at = datetime.utcnow()
            session.add(record)
    session.commit()
    _log_action(session, current_user, "bulk_action", None, f"action={action},count={len(records)}")
    return {"updated": len(records), "action": action}


@router.post("/templates")
def save_template(
    payload: JobTemplateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    template = JobTemplate(
        owner_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        required_skills=",".join(sorted({s.strip().lower() for s in payload.required_skills if s.strip()})),
        optional_skills=",".join(sorted({s.strip().lower() for s in payload.optional_skills if s.strip()})),
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    _log_action(session, current_user, "template_create", None, template.title)
    return template


@router.post("/jobs", response_model=JobRead)
def create_job(
    payload: JobCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from ..resume_parser_service import matcher as resume_matcher

    analysis = resume_matcher.parse_job_description(payload.description.strip())
    job = Job(
        owner_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        role=str(analysis.get("role")) if analysis.get("role") else None,
        role_category=str(analysis.get("role_category")) if analysis.get("role_category") else None,
        required_skills_json=json.dumps(analysis.get("required_skills") or []),
        optional_skills_json=json.dumps(analysis.get("optional_skills") or []),
        keywords_json=json.dumps(analysis.get("keywords") or []),
        education_requirements_json=json.dumps(analysis.get("education_requirements") or []),
        minimum_experience_years=analysis.get("minimum_experience_years"),
        is_active=True,
        updated_at=datetime.utcnow(),
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    _log_action(session, current_user, "job_create", None, job.title)
    return _serialize_job(job)


@router.get("/jobs", response_model=List[JobRead])
def list_jobs(
    include_inactive: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(Job).where(Job.owner_id == current_user.id).order_by(Job.created_at.desc())
    if not include_inactive:
        statement = statement.where(Job.is_active == True)  # noqa: E712
    rows = session.exec(statement).all()
    return [_serialize_job(row) for row in rows]


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    row = session.get(Job, job_id)
    if not row or row.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(row)


@router.patch("/jobs/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    payload: JobUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from ..resume_parser_service import matcher as resume_matcher

    row = session.get(Job, job_id)
    if not row or row.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    if payload.title is not None:
        row.title = payload.title.strip()
    if payload.description is not None:
        row.description = payload.description.strip()
        analysis = resume_matcher.parse_job_description(row.description)
        row.role = str(analysis.get("role")) if analysis.get("role") else None
        row.role_category = str(analysis.get("role_category")) if analysis.get("role_category") else None
        row.required_skills_json = json.dumps(analysis.get("required_skills") or [])
        row.optional_skills_json = json.dumps(analysis.get("optional_skills") or [])
        row.keywords_json = json.dumps(analysis.get("keywords") or [])
        row.education_requirements_json = json.dumps(analysis.get("education_requirements") or [])
        row.minimum_experience_years = analysis.get("minimum_experience_years")
    if payload.is_active is not None:
        row.is_active = bool(payload.is_active)
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    _log_action(session, current_user, "job_update", None, f"job_id={job_id}")
    return _serialize_job(row)


@router.get("/templates")
def list_templates(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(
        select(JobTemplate).where(JobTemplate.owner_id == current_user.id).order_by(JobTemplate.created_at.desc())
    ).all()


@router.post("/semantic-search")
def semantic_search(
    payload: SemanticSearchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    limit = max(1, min(payload.limit, 100))
    try:
        return vector_search.semantic_search_resumes(
            session=session,
            current_user=current_user,
            query=payload.query,
            limit=limit,
        )
    except Exception:
        # fallback to token overlap when embeddings/faiss are unavailable
        rows = session.exec(select(Resume).where(Resume.owner_id == current_user.id)).all()
        scored = []
        for row in rows:
            text = f"{row.parsed_text or ''} {row.name or ''} {row.tags or ''}"
            score = _token_overlap_score(payload.query, text)
            scored.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "email": row.email,
                    "filename": row.filename,
                    "score": round(score, 4),
                    "stage": row.stage,
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]


@router.post("/semantic-retrieve")
def semantic_retrieve(
    payload: SemanticRetrieveRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    limit = max(1, min(payload.limit, 100))
    max_chunks = max(1, min(payload.max_chunks, 10))
    try:
        return vector_search.semantic_retrieve_chunks(
            session=session,
            current_user=current_user,
            query=payload.query,
            limit=limit,
            max_chunks=max_chunks,
        )
    except Exception:
        rows = session.exec(select(Resume).where(Resume.owner_id == current_user.id)).all()
        scored = []
        for row in rows:
            text = f"{row.parsed_text or ''} {row.name or ''} {row.tags or ''}"
            score = _token_overlap_score(payload.query, text)
            scored.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "email": row.email,
                    "filename": row.filename,
                    "score": round(score, 4),
                    "stage": row.stage,
                    "top_chunks": [],
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]


@router.get("/resumes/{resume_id}/chunks")
def resume_chunks(
    resume_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _owned_resume(session, current_user, resume_id)
    try:
        return vector_search.get_resume_chunks(current_user=current_user, resume_id=resume_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/analytics/funnel")
def funnel_analytics(
    job_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(Resume).where(Resume.owner_id == current_user.id)
    if job_id is not None:
        statement = statement.where(Resume.job_id == job_id)
    rows = session.exec(statement).all()
    counts = {stage: 0 for stage in VALID_STAGES}
    for row in rows:
        stage = (row.stage or "new").lower()
        if stage not in counts:
            counts["new"] += 1
        else:
            counts[stage] += 1
    return {"total": len(rows), "stages": counts}


@router.get("/analytics/time-to-shortlist")
def time_to_shortlist(
    job_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(Resume).where(Resume.owner_id == current_user.id)
    if job_id is not None:
        statement = statement.where(Resume.job_id == job_id)
    rows = session.exec(statement).all()
    shortlisted = [r for r in rows if (r.stage or "").lower() in {"shortlisted", "interview", "offer"}]
    if not shortlisted:
        return {"count": 0, "average_hours": 0.0}
    durations = [(r.updated_at - r.created_at).total_seconds() / 3600 for r in shortlisted]
    avg = sum(durations) / len(durations)
    return {"count": len(shortlisted), "average_hours": round(avg, 2)}


@router.get("/export/csv")
def export_csv(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    rows = session.exec(select(Resume).where(Resume.owner_id == current_user.id).order_by(Resume.created_at.desc())).all()
    buffer = StringIO()
    buffer.write("id,name,email,filename,score,stage,tags,starred,assigned_to\n")
    for row in rows:
        buffer.write(
            f"{row.id},{(row.name or '').replace(',', ' ')},{(row.email or '').replace(',', ' ')},"
            f"{row.filename},{row.match_score or 0},{row.stage or 'new'},{(row.tags or '').replace(',', '|')},"
            f"{int(bool(row.is_starred))},{(row.assigned_to_email or '').replace(',', ' ')}\n"
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resume_export.csv"},
    )


@router.get("/resumes/{resume_id}/ai-summary")
def ai_summary(
    resume_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    row = _owned_resume(session, current_user, resume_id)
    tags = [t for t in (row.tags or "").split(",") if t]
    if ai_assistant.is_ai_enabled():
        try:
            query = row.matched_job or " ".join(tags) or row.parsed_text or ""
            resume_chunks = vector_service.retrieve_resume_chunks(
                session=session,
                current_user=current_user,
                resume_id=resume_id,
                query=query,
                limit=4,
            )
            resume_context = _build_resume_context_from_chunks(resume_chunks)
            ai_result = ai_assistant.build_candidate_summary(
                candidate_name=row.name or row.filename,
                stage=row.stage or "new",
                score=float(row.match_score or 0.0),
                tags=tags,
                parsed_text=row.parsed_text or "",
                resume_context=resume_context,
            )
            parsed = _safe_json_extract(str(ai_result.get("raw", "")))
            if isinstance(parsed, dict):
                return {
                    "resume_id": row.id,
                    "summary": parsed.get("summary") or f"{row.name or row.filename} summary generated.",
                    "strengths": parsed.get("strengths") or [],
                    "risks": parsed.get("risks") or [],
                    "provider": "openai",
                }
        except Exception:
            pass

    strengths = tags[:5] if tags else ["general profile match", "adaptability"]
    risks = []
    if (row.match_score or 0) < 0.35:
        risks.append("Low JD similarity score")
    if not row.email:
        risks.append("No contact email parsed")
    if not risks:
        risks.append("No major risk signals detected")
    return {
        "resume_id": row.id,
        "summary": f"{row.name or row.filename} currently in stage '{row.stage}'.",
        "strengths": strengths,
        "risks": risks,
        "provider": "heuristic",
    }


@router.post("/recruiter-assistant/query", response_model=RecruiterAssistantResponse)
def recruiter_assistant_query(
    payload: RecruiterAssistantRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in VALID_ROLES:
        raise HTTPException(status_code=403, detail="Recruiter access required")
    if payload.resume_id is not None:
        _owned_resume(session, current_user, payload.resume_id)
    try:
        result = recruiter_assistant.answer_question(
            session=session,
            current_user=current_user,
            query=payload.query,
            resume_id=payload.resume_id,
            limit=max(1, min(int(payload.limit or 5), 10)),
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Recruiter assistant temporarily unavailable: {exc}")


@router.get("/resumes/{resume_id}/interview-questions")
def interview_questions(
    resume_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    row = _owned_resume(session, current_user, resume_id)
    tags = [t for t in (row.tags or "").split(",") if t]
    if ai_assistant.is_ai_enabled() and tags:
        try:
            ai_result = ai_assistant.generate_interview_questions_from_skills(tags)
            raw = str(ai_result.get("raw", "")).strip()
            if raw:
                questions = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    line = line.lstrip("0123456789). ").strip()
                    if line:
                        questions.append(line)
                if questions:
                    return {"resume_id": row.id, "questions": questions[:8], "provider": "openai_skills"}
        except Exception:
            pass

    tags = tags[:3]
    if ai_assistant.is_ai_enabled():
        try:
            query = row.matched_job or " ".join(tags) or row.parsed_text or ""
            resume_chunks = vector_service.retrieve_resume_chunks(
                session=session,
                current_user=current_user,
                resume_id=resume_id,
                query=query,
                limit=4,
            )
            resume_context = _build_resume_context_from_chunks(resume_chunks)
            ai_result = ai_assistant.build_interview_questions(
                candidate_name=row.name or row.filename,
                role_context=row.matched_job or "General hiring",
                tags=tags,
                parsed_text=row.parsed_text or "",
                resume_context=resume_context,
            )
            parsed = _safe_json_extract(str(ai_result.get("raw", "")))
            if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
                return {
                    "resume_id": row.id,
                    "questions": [str(q) for q in parsed["questions"] if str(q).strip()],
                    "provider": "openai",
                }
        except Exception:
            pass

    questions = [
        "Walk me through a recent project you are most proud of.",
        "How do you debug a production issue under time pressure?",
        "How do you prioritize tasks when requirements change quickly?",
    ]
    for tag in tags:
        questions.append(f"Can you explain your hands-on experience with {tag}?")
    if (row.match_score or 0) < 0.5:
        questions.append("What areas are you currently upskilling for this role?")
    return {"resume_id": row.id, "questions": questions, "provider": "heuristic"}


@router.post("/resumes/{resume_id}/interview/start", response_model=InterviewSessionRead)
def start_interview(
    resume_id: int,
    payload: Optional[StartInterviewRequest] = None,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    payload = payload or StartInterviewRequest()
    row = _owned_resume(session, current_user, resume_id)
    skills = [tag for tag in (row.tags or row.extracted_skills or "").split(",") if tag]
    plan = interview_system.generate_question_plan(
        candidate_name=row.name or row.filename,
        skills=skills,
        job_description=payload.job_description or row.matched_job or "General hiring role",
        max_questions=max(3, min(payload.max_questions, 10)),
    )
    interview_session = InterviewSession(
        owner_id=current_user.id,
        resume_id=int(row.id or 0),
        job_description=payload.job_description or row.matched_job or "General hiring role",
        question_plan_json=json.dumps({"questions": plan}),
        status="active",
        current_question_index=0,
        difficulty_level=int(plan[0].get("difficulty", 1)) if plan else 1,
        question_count=0,
        max_questions=len(plan),
        total_score=0.0,
        average_score=0.0,
        recommended_decision="hold",
    )
    session.add(interview_session)
    row.stage = "interview"
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(interview_session)
    session.refresh(row)
    _log_action(session, current_user, "interview_start", resume_id, f"session_id={interview_session.id}")

    if payload.send_invitation_email:
        email_sender.queue_interview_invitation_email(
            background_tasks,
            row.email,
            row.name,
            row.matched_job or payload.job_description or "the role",
        )
    return _serialize_session(interview_session, [])


@router.get("/interviews/{session_id}", response_model=InterviewSessionRead)
def get_interview_session(
    session_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    record = _owned_session(session, current_user, session_id)
    answers = _load_answers(session, session_id)
    return _serialize_session(record, answers)


@router.post("/interviews/{session_id}/answer")
def submit_interview_answer(
    session_id: int,
    payload: SubmitInterviewAnswerRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    interview_session = _owned_session(session, current_user, session_id)
    if interview_session.status != "active":
        raise HTTPException(status_code=400, detail="Interview session is not active")

    question_plan = _safe_json_extract(interview_session.question_plan_json or "") or {}
    questions = question_plan.get("questions") or []
    if interview_session.current_question_index >= len(questions):
        raise HTTPException(status_code=400, detail="Interview already completed")

    current_item = questions[interview_session.current_question_index]
    evaluation = interview_system.evaluate_answer_advanced(
        question=str(current_item.get("question") or ""),
        answer=payload.answer_text,
        expected_keywords=[str(item) for item in (current_item.get("expected_keywords") or [])],
        expected_concepts=[str(item) for item in (current_item.get("expected_keywords") or [])],
        difficulty_level=interview_session.difficulty_level,
        input_type=payload.input_type.strip().lower() or "text",
        session=session,
        current_user=current_user,
        resume_id=interview_session.resume_id,
    )

    answer_row = InterviewAnswer(
        session_id=int(interview_session.id or 0),
        resume_id=interview_session.resume_id,
        question_index=int(current_item.get("question_index") or (interview_session.current_question_index + 1)),
        question_text=str(current_item.get("question") or ""),
        answer_text=payload.answer_text.strip(),
        input_type=payload.input_type.strip().lower() or "text",
        expected_keywords=",".join([str(item) for item in (current_item.get("expected_keywords") or [])]),
        matched_keywords=",".join([str(item) for item in evaluation.get("matched_keywords", [])]),
        score=float(evaluation["score"]),
        feedback=str(evaluation["feedback"]),
        difficulty_before=interview_session.difficulty_level,
        difficulty_after=int(evaluation["next_difficulty"]),
    )
    session.add(answer_row)

    interview_session.total_score = float(interview_session.total_score or 0.0) + float(evaluation["score"])
    interview_session.question_count += 1
    interview_session.average_score = interview_session.total_score / max(interview_session.question_count, 1)
    interview_session.difficulty_level = int(evaluation["next_difficulty"])
    interview_session.current_question_index += 1
    interview_session.recommended_decision = str(evaluation["recommendation"])
    interview_session.input_modes_used = ",".join(
        sorted(
            {
                mode
                for mode in (interview_session.input_modes_used or "").split(",") + [answer_row.input_type]
                if mode
            }
        )
    )
    interview_session.updated_at = datetime.utcnow()
    if interview_session.current_question_index >= interview_session.max_questions:
        interview_session.status = "completed"

    resume = _owned_resume(session, current_user, interview_session.resume_id)
    resume.interview_score = round(float(interview_session.average_score or 0.0) / 10.0, 4)
    resume.updated_at = datetime.utcnow()
    session.add(interview_session)
    session.add(resume)
    session.commit()
    session.refresh(interview_session)

    answers = _load_answers(session, session_id)
    _log_action(
        session,
        current_user,
        "interview_answer",
        interview_session.resume_id,
        f"session_id={session_id},score={evaluation['score']}",
    )
    return {
        "session": _serialize_session(interview_session, answers).model_dump(),
        "answer_score": evaluation["score"],
        "feedback": evaluation["feedback"],
        "matched_keywords": evaluation["matched_keywords"],
        "completed": interview_session.status == "completed",
    }


@router.post("/resumes/{resume_id}/finalize-selection")
def finalize_selection(
    resume_id: int,
    payload: Optional[FinalizeSelectionRequest] = None,
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    payload = payload or FinalizeSelectionRequest()
    row = _owned_resume(session, current_user, resume_id)
    match_score = float(row.match_score or 0.0)
    interview_score = float(row.interview_score or 0.0)
    combined = interview_system.combine_final_scores(match_score, interview_score)

    row.final_score = float(combined["final_score"])
    row.final_decision = str(combined["decision"])
    row.stage = "offer" if row.final_decision == "selected" else "rejected" if row.final_decision == "rejected" else "shortlisted"
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    _log_action(
        session,
        current_user,
        "finalize_selection",
        resume_id,
        f"final_score={row.final_score},decision={row.final_decision}",
    )

    if payload.send_email:
        email_sender.queue_result_email(
            background_tasks,
            row.email,
            row.final_decision == "selected",
            payload.job_title or row.matched_job or "the role",
        )

    return {
        "resume_id": row.id,
        "match_score": match_score,
        "interview_score": interview_score,
        "final_score": row.final_score,
        "decision": row.final_decision,
        "stage": row.stage,
    }


@router.post("/notify/slack")
def notify_slack(
    payload: SlackNotifyRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    hook_payload = {"text": payload.message}
    result = post_webhook(settings.SLACK_WEBHOOK_URL, hook_payload)
    status = "sent" if result["ok"] else "failed"
    _log_action(
        session,
        current_user,
        "slack_notify",
        None,
        f"status={status},message={payload.message[:120]},error={result.get('error', '')[:160]}",
    )
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Slack notification failed"))
    return {"status": status, "provider": "slack"}


@router.post("/notify/teams")
def notify_teams(
    payload: SlackNotifyRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    hook_payload = {"text": payload.message}
    result = post_webhook(settings.TEAMS_WEBHOOK_URL, hook_payload)
    status = "sent" if result["ok"] else "failed"
    _log_action(
        session,
        current_user,
        "teams_notify",
        None,
        f"status={status},message={payload.message[:120]},error={result.get('error', '')[:160]}",
    )
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Teams notification failed"))
    return {"status": status, "provider": "teams"}


@router.post("/integrations/ats-sync/{resume_id}")
def sync_to_ats(
    resume_id: int,
    payload: Optional[AtsSyncRequest] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    payload = payload or AtsSyncRequest()
    row = _owned_resume(session, current_user, resume_id)
    ats_payload = {
        "candidate_id": row.id,
        "owner_email": current_user.email,
        "name": row.name,
        "email": row.email,
        "filename": row.filename,
        "score": row.match_score,
        "stage": row.stage,
        "tags": [t for t in (row.tags or "").split(",") if t],
        "assigned_to_email": row.assigned_to_email,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if payload.include_parsed_text:
        ats_payload["parsed_text"] = row.parsed_text

    headers = {"Content-Type": "application/json"}
    if settings.ATS_SYNC_API_KEY:
        headers["Authorization"] = f"Bearer {settings.ATS_SYNC_API_KEY}"
    result = post_webhook(settings.ATS_SYNC_URL, ats_payload, headers=headers)
    status = "sent" if result["ok"] else "failed"
    _log_action(
        session,
        current_user,
        "ats_sync",
        resume_id,
        f"status={status},error={result.get('error', '')[:180]}",
    )
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result.get("error", "ATS sync failed"))
    return {"status": status, "provider": "ats", "resume_id": resume_id}


@router.get("/team/summary", response_model=List[TeamSummary])
def team_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    users = session.exec(select(User)).all()
    out: List[TeamSummary] = []
    for user in users:
        count = session.exec(select(Resume).where(Resume.owner_id == user.id)).all()
        out.append(TeamSummary(email=user.email, role=user.role, resumes_owned=len(count)))
    return out


@router.get("/admin/users", response_model=List[AdminUserRead])
def list_users_for_admin(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    return users


@router.patch("/admin/users/{user_id}/role", response_model=AdminUserRead)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    role = payload.role.strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {', '.join(sorted(VALID_ROLES))}")
    target = session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.role = role
    session.add(target)
    session.commit()
    session.refresh(target)
    _log_action(session, current_user, "user_role_update", None, f"user_id={user_id},role={role}")
    return target


@router.get("/integrations/status")
def integrations_status(
    current_user: User = Depends(get_current_user),
):
    return {
        "slack_configured": bool(settings.SLACK_WEBHOOK_URL),
        "teams_configured": bool(settings.TEAMS_WEBHOOK_URL),
        "ats_configured": bool(settings.ATS_SYNC_URL),
    }


@router.post("/integrations/test")
def test_integration(
    payload: IntegrationTestRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    provider = payload.provider.strip().lower()
    if provider == "slack":
        result = post_webhook(settings.SLACK_WEBHOOK_URL, {"text": payload.message})
    elif provider == "teams":
        result = post_webhook(settings.TEAMS_WEBHOOK_URL, {"text": payload.message})
    elif provider == "ats":
        headers = {"Content-Type": "application/json"}
        if settings.ATS_SYNC_API_KEY:
            headers["Authorization"] = f"Bearer {settings.ATS_SYNC_API_KEY}"
        result = post_webhook(
            settings.ATS_SYNC_URL,
            {"type": "connectivity_test", "message": payload.message, "timestamp": datetime.utcnow().isoformat()},
            headers=headers,
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider. Use slack, teams, or ats")

    _log_action(
        session,
        current_user,
        "integration_test",
        None,
        f"provider={provider},ok={result.get('ok', False)},error={result.get('error', '')[:180]}",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result.get("error", "Integration connectivity test failed"))
    return {"status": "ok", "provider": provider}


@router.post("/demo/seed")
def seed_demo_data(
    payload: Optional[DemoSeedRequest] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    payload = payload or DemoSeedRequest()
    count = max(1, min(payload.count, 25))
    skills = [
        "python", "fastapi", "sql", "docker", "aws", "react", "typescript", "pandas", "ml", "api",
    ]
    stages = ["new", "screened", "shortlisted", "interview", "offer", "rejected"]
    created = 0
    if not session.exec(select(Job).where(Job.owner_id == current_user.id)).first():
        demo_job = Job(
            owner_id=current_user.id,
            title="Backend Engineer",
            description=(
                "Hiring for a full-stack backend engineer with Python, FastAPI, SQL, Docker, AWS, "
                "React, and automated applicant scoring expertise."
            ),
            role="Backend Engineer",
            role_category="Software",
            required_skills_json=json.dumps(["python", "fastapi", "sql", "docker", "aws", "react"]),
            optional_skills_json=json.dumps(["typescript", "ml", "api", "pandas"]),
            keywords_json=json.dumps(["backend", "api", "cloud", "devops", "ai"]),
            education_requirements_json=json.dumps(["bachelor's degree"]),
            minimum_experience_years=2.0,
            is_active=True,
            updated_at=datetime.utcnow(),
        )
        session.add(demo_job)

    for i in range(count):
        chosen = random.sample(skills, k=4)
        score = round(random.uniform(0.25, 0.95), 2)
        candidate_email = f"demo_candidate_{int(datetime.utcnow().timestamp())}_{i}@example.com"
        resume = Resume(
            owner_id=current_user.id,
            filename=f"demo_resume_{i+1}.txt",
            filepath=f"/demo/demo_resume_{i+1}.txt",
            parsed_text=f"Experienced in {' '.join(chosen)}",
            email=candidate_email,
            name=f"Demo Candidate {i+1}",
            matched_job="Backend Engineer",
            match_score=score,
            stage=random.choice(stages),
            tags=",".join(chosen),
            is_starred=score >= 0.8,
            updated_at=datetime.utcnow(),
        )
        session.add(resume)
        created += 1
    session.commit()
    _log_action(session, current_user, "demo_seed", None, f"created={created}")
    return {"created": created}


@router.post("/demo/reset")
def reset_demo_data(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    resumes = session.exec(select(Resume).where(Resume.owner_id == current_user.id)).all()
    jobs = session.exec(select(Job).where(Job.owner_id == current_user.id)).all()
    templates = session.exec(select(JobTemplate).where(JobTemplate.owner_id == current_user.id)).all()
    logs = session.exec(select(ActivityLog).where(ActivityLog.owner_id == current_user.id)).all()
    deleted = {"resumes": len(resumes), "jobs": len(jobs), "templates": len(templates), "logs": len(logs)}

    for row in resumes:
        session.delete(row)
    for row in jobs:
        session.delete(row)
    for row in templates:
        session.delete(row)
    for row in logs:
        session.delete(row)
    session.commit()
    return {"reset": True, "deleted": deleted}
