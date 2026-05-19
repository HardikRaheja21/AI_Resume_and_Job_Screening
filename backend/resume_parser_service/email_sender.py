from email.mime.text import MIMEText
from pathlib import Path
import logging
import smtplib
from typing import Optional

from fastapi import BackgroundTasks
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..integrations.reliability import retry_call, write_dead_letter
from ..services.task_service import schedule_task
from ..utils.config import settings

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
logger = logging.getLogger("resume_parser.email")
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_result_email(selected: bool, job_title: str, candidate_email: str) -> tuple[str, str]:
    if selected:
        subject = f"Congratulations - You matched for {job_title}"
        template = jinja_env.get_template("result_selected.html")
    else:
        subject = "Update on your application"
        template = jinja_env.get_template("result_rejected.html")

    body = template.render(job_title=job_title, candidate_email=candidate_email)
    return subject, body


def send_email_sync(to_email: str, subject: str, body: str, request_id: Optional[str] = None) -> None:
    def _send_once() -> dict:
        try:
            msg = MIMEText(body, "html")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM or settings.smtp_user
            msg["To"] = to_email

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.EMAIL_USE_TLS:
                    server.starttls()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    result = retry_call(
        operation_name="email_send",
        fn=_send_once,
        attempts=settings.EMAIL_RETRY_ATTEMPTS,
        base_backoff_seconds=settings.EMAIL_RETRY_BACKOFF_SECONDS,
    )
    if result.get("ok"):
        logger.info(
            "email_sent",
            extra={"to_email": to_email, "subject": subject, "request_id": request_id},
        )
        return

    dead_letter_path = write_dead_letter(
        "email",
        {
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "result": result,
        },
    )
    logger.error(
        "email_failed",
        extra={
            "to_email": to_email,
            "subject": subject,
            "dead_letter": dead_letter_path,
            "error": str(result.get("error", "unknown_error"))[:240],
            "request_id": request_id,
        },
    )


def queue_custom_email(
    background_tasks: BackgroundTasks,
    to_email: Optional[str],
    subject: str,
    body: str,
    request_id: Optional[str] = None,
) -> None:
    if not to_email:
        return
    schedule_task(
        background_tasks,
        "send_email",
        send_email_sync,
        to_email,
        subject,
        body,
        request_id=request_id,
    )


def queue_result_email(
    background_tasks: BackgroundTasks,
    to_email: Optional[str],
    selected: bool,
    job_title: Optional[str],
    request_id: Optional[str] = None,
) -> None:
    if not to_email:
        return
    safe_job_title = job_title or "the role"
    subject, body = render_result_email(selected, safe_job_title, to_email)
    queue_custom_email(background_tasks, to_email, subject, body, request_id=request_id)


def queue_interview_invitation_email(
    background_tasks: BackgroundTasks,
    to_email: Optional[str],
    candidate_name: Optional[str],
    job_title: Optional[str],
    request_id: Optional[str] = None,
) -> None:
    if not to_email:
        return
    safe_name = candidate_name or "Candidate"
    safe_role = job_title or "the role"
    subject = f"Interview invitation for {safe_role}"
    body = (
        f"<p>Hello {safe_name},</p>"
        f"<p>You have been shortlisted for {safe_role}. "
        "Please proceed with the adaptive interview round.</p>"
        "<p>Regards,<br/>ResumeMatch</p>"
    )
    queue_custom_email(background_tasks, to_email, subject, body, request_id=request_id)
