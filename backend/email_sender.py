from fastapi import BackgroundTasks
from typing import Optional
import smtplib
from email.message import EmailMessage
from .utils.config import settings

def _send_email(to_email: str, subject: str, body: str) -> None:
    if not to_email:
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(body)

    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("EMAIL ERROR:", str(e))


def queue_result_email(background_tasks: BackgroundTasks, to_email: Optional[str], selected: bool, job_title: str):
    if not to_email:
        return
    subject = f"Application result — {job_title}"
    if selected:
        body = f"Congratulations! You have been shortlisted for {job_title}."
    else:
        body = f"Thank you for applying for {job_title}. We will keep your profile for future roles."
    background_tasks.add_task(_send_email, to_email, subject, body)
