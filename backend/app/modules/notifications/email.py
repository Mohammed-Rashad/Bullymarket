import asyncio
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.notifications.models import EmailOutbox, EmailOutboxStatus
from app.modules.notifications.repository import pending_emails
from app.modules.notifications.templates import LOGO_CONTENT_ID

LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo.png"


def _build_email_message(message: EmailOutbox, settings: Settings) -> EmailMessage:
    email = EmailMessage()
    email["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
    email["To"] = message.recipient_email
    email["Subject"] = message.subject
    email.set_content(message.text_body)
    email.add_alternative(message.html_body, subtype="html")
    html_part = email.get_body(preferencelist=("html",))
    if not isinstance(html_part, EmailMessage):
        raise RuntimeError("Could not construct the HTML email part")
    html_part.add_related(
        LOGO_PATH.read_bytes(),
        maintype="image",
        subtype="png",
        cid=f"<{LOGO_CONTENT_ID}>",
        filename="bullymarket-logo.png",
        disposition="inline",
    )
    return email


def _send_smtp(message: EmailOutbox, settings: Settings) -> None:
    password = settings.smtp_password
    if password is None:
        raise RuntimeError("SMTP password is not configured")
    email = _build_email_message(message, settings)
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.login(settings.smtp_username, password.get_secret_value())
        smtp.send_message(email)


async def deliver_pending_emails(session: AsyncSession, settings: Settings) -> int:
    if not settings.email_enabled:
        return 0
    now = datetime.now(UTC)
    messages = await pending_emails(
        session,
        now=now,
        limit=settings.email_delivery_batch_size,
    )
    sent = 0
    for message in messages:
        try:
            await asyncio.to_thread(_send_smtp, message, settings)
        except Exception as exc:  # delivery errors are persisted and retried
            message.attempts += 1
            message.last_error = str(exc)[:2000]
            if message.attempts >= 5:
                message.status = EmailOutboxStatus.FAILED
            else:
                message.available_at = now + timedelta(minutes=2**message.attempts)
        else:
            message.attempts += 1
            message.status = EmailOutboxStatus.SENT
            message.sent_at = datetime.now(UTC)
            message.last_error = None
            sent += 1
    await session.flush()
    return sent
