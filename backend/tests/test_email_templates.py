from datetime import UTC, datetime

from pydantic import SecretStr

from app.core.config import Settings
from app.modules.notifications.email import _build_email_message, _send_smtp
from app.modules.notifications.models import EmailOutbox
from app.modules.notifications.templates import branded_email


def test_branded_email_contains_logo_details_action_and_plain_text_fallback() -> None:
    email = branded_email(
        frontend_url="https://bullymarket.example/",
        subject="A useful subject",
        preheader="A concise preview",
        eyebrow="New bet",
        title="A market update",
        greeting="Hi Rashad,",
        paragraphs=("A <new> market is ready.",),
        details=(("Group", "Friends & Rivals"),),
        code="123456",
        action_label="Open bet",
        action_path="/bets/market-id",
        note="Do not share this code.",
    )

    assert email.subject == "A useful subject"
    assert 'src="cid:bullymarket-logo"' in email.html
    assert 'href="https://bullymarket.example/bets/market-id"' in email.html
    assert "A &lt;new&gt; market is ready." in email.html
    assert "Friends &amp; Rivals" in email.html
    assert "123456" in email.html
    assert "Verification code: 123456" in email.text
    assert "Open bet: https://bullymarket.example/bets/market-id" in email.text
    assert "A <new> market is ready." in email.text


def test_email_message_embeds_the_logo_as_an_inline_image() -> None:
    outbox = EmailOutbox(
        recipient_email="player@example.com",
        subject="Test message",
        text_body="Plain text",
        html_body='<html><img src="cid:bullymarket-logo"></html>',
        category="test",
        available_at=datetime.now(UTC),
    )
    settings = Settings(
        smtp_password=SecretStr("test-only-key"),
        email_from_address="no-reply@bullymarket.example",
    )

    message = _build_email_message(outbox, settings)
    logo_parts = [part for part in message.walk() if part.get_content_type() == "image/png"]

    assert message["From"] == "BullyMarket <no-reply@bullymarket.example>"
    assert len(logo_parts) == 1
    assert logo_parts[0]["Content-ID"] == "<bullymarket-logo>"
    assert logo_parts[0].get_content_disposition() == "inline"


def test_brevo_port_587_uses_starttls(monkeypatch) -> None:
    calls: list[str] = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            assert (host, port, timeout) == ("smtp-relay.brevo.com", 587, 20)

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def ehlo(self) -> None:
            calls.append("ehlo")

        def starttls(self) -> None:
            calls.append("starttls")

        def login(self, username: str, password: str) -> None:
            assert (username, password) == ("smtp-login", "smtp-key")
            calls.append("login")

        def send_message(self, _message) -> None:
            calls.append("send")

    monkeypatch.setattr("app.modules.notifications.email.smtplib.SMTP", FakeSmtp)
    outbox = EmailOutbox(
        recipient_email="player@example.com",
        subject="Test delivery",
        text_body="Plain text",
        html_body="<p>HTML</p>",
        category="test",
    )
    settings = Settings(
        smtp_username="smtp-login",
        smtp_password="smtp-key",
    )

    _send_smtp(outbox, settings)

    assert calls == ["ehlo", "starttls", "ehlo", "login", "send"]
