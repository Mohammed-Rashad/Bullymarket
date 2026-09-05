from datetime import UTC, datetime

from pydantic import SecretStr

from app.core.config import Settings
from app.modules.notifications.email import _build_email_message
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
