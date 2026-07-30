from typing import Any

import pytest
from httpx import AsyncClient


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
    assert response.status_code == 201, response.text
    return str(response.json()["access_token"])


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

    member_groups = await client.get("/api/v1/groups", headers=auth(member_token))
    assert member_groups.status_code == 200
    assert member_groups.json() == []


@pytest.mark.asyncio
async def test_unauthenticated_request_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
