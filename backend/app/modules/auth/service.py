import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth import repository
from app.modules.auth.models import VerificationChallenge, VerificationPurpose
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerificationChallengeResponse,
    VerifySignupRequest,
)
from app.modules.ledger.models import LedgerEntryType
from app.modules.ledger.service import add_entry
from app.modules.notifications.service import queue_email
from app.modules.notifications.templates import branded_email
from app.modules.users.repository import create_user, get_user_by_email


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _code_hash(
    *, email: str, purpose: VerificationPurpose, code: str, settings: Settings
) -> str:
    message = f"{purpose.value}:{email.lower()}:{code}".encode()
    return hmac.new(settings.jwt_secret.encode(), message, hashlib.sha256).hexdigest()


def _valid_code(
    challenge: VerificationChallenge, code: str, settings: Settings
) -> bool:
    candidate = _code_hash(
        email=challenge.email,
        purpose=challenge.purpose,
        code=code,
        settings=settings,
    )
    return hmac.compare_digest(challenge.code_hash, candidate)


async def _check_challenge(
    session: AsyncSession,
    challenge: VerificationChallenge | None,
    *,
    code: str,
    settings: Settings,
) -> VerificationChallenge:
    now = datetime.now(UTC)
    if challenge is None or _aware(challenge.expires_at) <= now:
        raise DomainError(
            "verification_expired",
            "The verification code is invalid or expired",
            400,
        )
    if challenge.attempts >= settings.verification_max_attempts:
        raise DomainError("verification_locked", "Too many incorrect verification attempts", 429)
    if not _valid_code(challenge, code, settings):
        challenge.attempts += 1
        await session.commit()
        raise DomainError("invalid_verification_code", "The verification code is incorrect", 400)
    challenge.consumed_at = now
    return challenge


async def request_signup(
    session: AsyncSession, payload: SignupRequest, settings: Settings
) -> VerificationChallengeResponse:
    if await get_user_by_email(session, str(payload.email)) is not None:
        raise DomainError("email_taken", "An account with this email already exists", 409)
    now = datetime.now(UTC)
    email = str(payload.email).lower()
    previous = await repository.latest_challenge(
        session,
        email=email,
        purpose=VerificationPurpose.REGISTRATION,
        lock=True,
    )
    if previous and (
        now - _aware(previous.sent_at)
    ).total_seconds() < settings.verification_resend_seconds:
        raise DomainError("verification_cooldown", "Wait before requesting another code", 429)
    await repository.consume_active_challenges(
        session,
        email=email,
        purpose=VerificationPurpose.REGISTRATION,
        consumed_at=now,
    )
    code = _new_code()
    challenge = VerificationChallenge(
        purpose=VerificationPurpose.REGISTRATION,
        email=email,
        display_name=payload.display_name.strip(),
        pending_password_hash=hash_password(payload.password),
        code_hash=_code_hash(
            email=email,
            purpose=VerificationPurpose.REGISTRATION,
            code=code,
            settings=settings,
        ),
        expires_at=now + timedelta(minutes=settings.verification_code_minutes),
        sent_at=now,
    )
    session.add(challenge)
    expiry = settings.verification_code_minutes
    email_content = branded_email(
        frontend_url=settings.frontend_url,
        subject="Confirm your BullyMarket email",
        preheader=f"Use code {code} to finish creating your BullyMarket account.",
        eyebrow="Email verification",
        title="You’re one step away",
        greeting=f"Hi {challenge.display_name},",
        paragraphs=(
            "Use the code below to confirm your email and finish creating your account.",
            "Once verified, you’ll receive your starting points and can join your first group.",
        ),
        details=(("Account", email), ("Expires in", f"{expiry} minutes")),
        code=code,
        action_label="Return to signup",
        action_path="/signup",
        note=(
            "You did not create a BullyMarket account? You can safely ignore this email. "
            "Never share this code with anyone."
        ),
    )
    await queue_email(
        session,
        recipient_email=email,
        subject=email_content.subject,
        text_body=email_content.text,
        html_body=email_content.html,
        category="registration_otp",
    )
    return VerificationChallengeResponse(
        expires_in_seconds=settings.verification_code_minutes * 60,
        message="A verification code was sent if email delivery is configured.",
    )


async def verify_signup(
    session: AsyncSession, payload: VerifySignupRequest, settings: Settings
) -> str:
    email = str(payload.email).lower()
    challenge = await _check_challenge(
        session,
        await repository.latest_challenge(
            session,
            email=email,
            purpose=VerificationPurpose.REGISTRATION,
            lock=True,
        ),
        code=payload.code,
        settings=settings,
    )
    if not challenge.display_name or not challenge.pending_password_hash:
        raise DomainError("invalid_verification", "Registration data is incomplete", 500)
    if await get_user_by_email(session, email) is not None:
        raise DomainError("email_taken", "An account with this email already exists", 409)
    try:
        user = await create_user(
            session,
            email=email,
            display_name=challenge.display_name,
            password_hash=challenge.pending_password_hash,
        )
        user.last_refill_at = datetime.now(UTC)
        await add_entry(
            session,
            user_id=user.id,
            amount=Decimal(settings.default_starting_balance),
            entry_type=LedgerEntryType.REFILL,
        )
    except IntegrityError as exc:
        raise DomainError("email_taken", "An account with this email already exists", 409) from exc
    return create_access_token(user.id, settings)


async def request_password_reset(
    session: AsyncSession, payload: ForgotPasswordRequest, settings: Settings
) -> VerificationChallengeResponse:
    now = datetime.now(UTC)
    email = str(payload.email).lower()
    user = await get_user_by_email(session, email)
    if user is not None:
        previous = await repository.latest_challenge(
            session,
            email=email,
            purpose=VerificationPurpose.PASSWORD_RESET,
            lock=True,
        )
        if not previous or (
            now - _aware(previous.sent_at)
        ).total_seconds() >= settings.verification_resend_seconds:
            await repository.consume_active_challenges(
                session,
                email=email,
                purpose=VerificationPurpose.PASSWORD_RESET,
                consumed_at=now,
            )
            code = _new_code()
            session.add(
                VerificationChallenge(
                    purpose=VerificationPurpose.PASSWORD_RESET,
                    email=email,
                    user_id=user.id,
                    code_hash=_code_hash(
                        email=email,
                        purpose=VerificationPurpose.PASSWORD_RESET,
                        code=code,
                        settings=settings,
                    ),
                    expires_at=now + timedelta(minutes=settings.verification_code_minutes),
                    sent_at=now,
                )
            )
            email_content = branded_email(
                frontend_url=settings.frontend_url,
                subject="Reset your BullyMarket password",
                preheader=f"Use code {code} to reset your BullyMarket password.",
                eyebrow="Password recovery",
                title="Reset your password",
                greeting=f"Hi {user.display_name},",
                paragraphs=(
                    "We received a request to reset the password for your account.",
                    "Enter the code below on the password-reset page, then choose a new password.",
                ),
                details=(
                    ("Account", email),
                    ("Expires in", f"{settings.verification_code_minutes} minutes"),
                ),
                code=code,
                action_label="Continue password reset",
                action_path="/forgot-password",
                note=(
                    "If you did not request a password reset, ignore this email. Your current "
                    "password will remain unchanged. Never share this code with anyone."
                ),
            )
            await queue_email(
                session,
                recipient_email=email,
                subject=email_content.subject,
                text_body=email_content.text,
                html_body=email_content.html,
                category="password_reset_otp",
                user_id=user.id,
            )
    return VerificationChallengeResponse(
        expires_in_seconds=settings.verification_code_minutes * 60,
        message="If the account exists, a password reset code was sent.",
    )


async def reset_password(
    session: AsyncSession, payload: ResetPasswordRequest, settings: Settings
) -> str:
    email = str(payload.email).lower()
    challenge = await _check_challenge(
        session,
        await repository.latest_challenge(
            session,
            email=email,
            purpose=VerificationPurpose.PASSWORD_RESET,
            lock=True,
        ),
        code=payload.code,
        settings=settings,
    )
    user = await get_user_by_email(session, email)
    if user is None or challenge.user_id != user.id:
        raise DomainError(
            "verification_expired",
            "The verification code is invalid or expired",
            400,
        )
    user.password_hash = hash_password(payload.new_password)
    await session.flush()
    return create_access_token(user.id, settings)


async def login(session: AsyncSession, payload: LoginRequest, settings: Settings) -> str:
    user = await get_user_by_email(session, str(payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise DomainError("invalid_credentials", "Email or password is incorrect", 401)
    return create_access_token(user.id, settings)
