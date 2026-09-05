import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core import db
from app.modules.notifications.models import EmailOutbox


async def emailed_code(email: str, category: str) -> str:
    async with db.SessionFactory() as session:
        message = await session.scalar(
            select(EmailOutbox)
            .where(
                EmailOutbox.recipient_email == email.lower(),
                EmailOutbox.category == category,
            )
            .order_by(EmailOutbox.created_at.desc())
        )
    assert message is not None
    match = re.search(r"\b\d{6}\b", message.text_body)
    assert match is not None
    return match.group()


async def signup(
    client: AsyncClient,
    *,
    email: str,
    display_name: str,
    password: str = "correct horse battery staple",
) -> str:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "display_name": display_name,
            "password": password,
        },
    )
    assert response.status_code == 202, response.text
    assert "code" not in response.json()
    verification = await client.post(
        "/api/v1/auth/signup/verify",
        json={"email": email, "code": await emailed_code(email, "registration_otp")},
    )
    assert verification.status_code == 201, verification.text
    return str(verification.json()["access_token"])


def auth(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_signup_login_profile_and_duplicate_email(client: AsyncClient) -> None:
    token = await signup(client, email="Ahmed@example.com", display_name="Ahmed")

    profile = await client.get("/api/v1/users/me", headers=auth(token))
    assert profile.status_code == 200
    assert profile.json()["email"] == "ahmed@example.com"
    assert profile.json()["balance"] == "1000.00000000"

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "ahmed@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert login.status_code == 200

    duplicate = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "AHMED@example.com",
            "display_name": "Other Ahmed",
            "password": "another valid password",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_taken"


@pytest.mark.asyncio
async def test_group_join_roles_and_removal_state(client: AsyncClient) -> None:
    admin_token = await signup(client, email="admin@example.com", display_name="Admin")
    member_token = await signup(client, email="member@example.com", display_name="Member")

    created = await client.post(
        "/api/v1/groups",
        json={"name": "Riyadh Friends", "description": "Weekend bets"},
        headers=auth(admin_token),
    )
    assert created.status_code == 201, created.text
    group: dict[str, Any] = created.json()
    assert group["role"] == "admin"

    joined = await client.post(
        "/api/v1/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth(member_token),
    )
    assert joined.status_code == 200
    assert joined.json()["role"] == "member"

    members = await client.get(
        f"/api/v1/groups/{group['id']}/members",
        headers=auth(admin_token),
    )
    assert {row["display_name"] for row in members.json()} == {"Admin", "Member"}
    member = next(row for row in members.json() if row["role"] == "member")

    forbidden = await client.delete(
        f"/api/v1/groups/{group['id']}/members/{member['user_id']}",
        headers=auth(member_token),
    )
    assert forbidden.status_code == 403

    removed = await client.delete(
        f"/api/v1/groups/{group['id']}/members/{member['user_id']}",
        headers=auth(admin_token),
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "removed"
    assert removed.json()["display_name"] == "Member"

    member_groups = await client.get("/api/v1/groups", headers=auth(member_token))
    assert member_groups.status_code == 200
    assert member_groups.json() == []


@pytest.mark.asyncio
async def test_unauthenticated_request_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_uploaded_image_can_be_assigned_to_a_group_and_bet(
    client: AsyncClient,
) -> None:
    token = await signup(client, email="images@example.com", display_name="Images")
    uploaded = await client.post(
        "/api/v1/uploads/images",
        files={"image": ("cover.png", b"\x89PNG\r\n\x1a\ncover", "image/png")},
        headers=auth(token),
    )
    assert uploaded.status_code == 201, uploaded.text
    image_url = uploaded.json()["image_url"]
    assert image_url.startswith("/media/images/")

    served = await client.get(image_url)
    assert served.status_code == 200
    assert served.content.startswith(b"\x89PNG")

    created_group = await client.post(
        "/api/v1/groups",
        json={"name": "Photo group", "image_url": image_url},
        headers=auth(token),
    )
    assert created_group.status_code == 201, created_group.text
    assert created_group.json()["image_url"] == image_url

    created_bet = await client.post(
        f"/api/v1/groups/{created_group.json()['id']}/bets",
        json={
            "question": "Does this cover render?",
            "image_url": image_url,
            "end_time": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "outcome_labels": ["Yes", "No"],
        },
        headers=auth(token),
    )
    assert created_bet.status_code == 201, created_bet.text
    assert created_bet.json()["image_url"] == image_url

    unmanaged = await client.post(
        "/api/v1/groups",
        json={"name": "External image", "image_url": "https://example.com/image.png"},
        headers=auth(token),
    )
    assert unmanaged.status_code == 422


@pytest.mark.asyncio
async def test_registration_otp_and_password_reset_are_backend_verified(
    client: AsyncClient,
) -> None:
    email = "secure@example.com"
    requested = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "display_name": "Secure",
            "password": "old-password",
        },
    )
    assert requested.status_code == 202
    assert "code" not in requested.json()
    registration_code = await emailed_code(email, "registration_otp")
    wrong_code = "999999" if registration_code != "999999" else "888888"
    wrong = await client.post(
        "/api/v1/auth/signup/verify",
        json={"email": email, "code": wrong_code},
    )
    assert wrong.status_code == 400
    verified = await client.post(
        "/api/v1/auth/signup/verify",
        json={"email": email, "code": registration_code},
    )
    assert verified.status_code == 201

    forgot = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 202
    assert "code" not in forgot.json()
    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": email,
            "code": await emailed_code(email, "password_reset_otp"),
            "new_password": "new-password",
        },
    )
    assert reset.status_code == 200
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "old-password"},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "new-password"},
    )
    assert new_login.status_code == 200

    unknown = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "missing@example.com"},
    )
    assert unknown.status_code == 202
    assert unknown.json()["message"] == forgot.json()["message"]
