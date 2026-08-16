import asyncio
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.notifications.models import EmailOutbox, EmailOutboxStatus
from app.modules.notifications.repository import pending_emails


def _send_smtp(message: EmailOutbox, settings: Settings) -> None:
    password = settings.smtp_password
    if password is None:
        raise RuntimeError("SMTP password is not configured")
    email = EmailMessage()
    email["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
    email["To"] = message.recipient_email
    email["Subject"] = message.subject
    email.set_content(message.text_body)
    email.add_alternative(message.html_body, subtype="html")
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
