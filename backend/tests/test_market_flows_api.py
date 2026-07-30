from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core import db
from app.core.config import get_settings
from app.modules.bets.models import Bet
from app.modules.refill.service import run_refills
from app.modules.users.models import User


def auth(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


async def signup(client: AsyncClient, email: str, display_name: str) -> str:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "display_name": display_name,
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["access_token"])


async def create_group(client: AsyncClient, token: str, name: str = "Friends") -> dict[str, Any]:
    response = await client.post(
        "/api/v1/groups",
        json={"name": name},
        headers=auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def join_group(
    client: AsyncClient, token: str, invite_code: str
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/groups/join",
        json={"invite_code": invite_code},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


async def create_group_bet(
    client: AsyncClient,
    token: str,
    group_id: str,
    *,
    question: str = "Will the plan ship?",
    visible_to_user_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "question": question,
        "description": "Integration-test market",
        "end_time": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "outcome_labels": ["Yes", "No"],
    }
    if visible_to_user_ids is not None:
        payload["visible_to_user_ids"] = visible_to_user_ids
    response = await client.post(
        f"/api/v1/groups/{group_id}/bets",
        json=payload,
        headers=auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_public_bet(
    client: AsyncClient,
    token: str,
    *,
    question: str = "Will the public market resolve?",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/public-bets",
        json={
            "question": question,
            "end_time": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "outcome_labels": ["Yes", "No"],
        },
        headers=auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def expire_bet(bet_id: str) -> None:
    async with db.SessionFactory.begin() as session:
        bet = await session.get(Bet, UUID(bet_id))
        assert bet is not None
        bet.end_time = datetime.now(UTC) - timedelta(minutes=1)


async def balance(client: AsyncClient, token: str) -> Decimal:
    response = await client.get("/api/v1/users/me", headers=auth(token))
    assert response.status_code == 200
    return Decimal(str(response.json()["balance"]))


async def current_user_id(client: AsyncClient, token: str) -> str:
    response = await client.get("/api/v1/users/me", headers=auth(token))
    assert response.status_code == 200
    return str(response.json()["id"])


@pytest.mark.asyncio
async def test_trading_resolution_correction_and_scope_isolated_leaderboards(
    client: AsyncClient,
) -> None:
    admin_token = await signup(client, "admin@market.example", "Admin")
    member_token = await signup(client, "member@market.example", "Member")
    public_creator_token = await signup(
        client, "public@market.example", "Public Creator"
    )
    group = await create_group(client, admin_token)
    await join_group(client, member_token, group["invite_code"])

    group_bet = await create_group_bet(client, admin_token, group["id"])
    yes_id = group_bet["outcomes"][0]["id"]
    no_id = group_bet["outcomes"][1]["id"]

    too_small = await client.post(
        f"/api/v1/bets/{group_bet['id']}/preview-buy",
        json={"outcome_id": yes_id, "amount": "0.5"},
        headers=auth(member_token),
    )
    assert too_small.status_code == 400
    assert too_small.json()["error"]["code"] == "trade_below_minimum"

    member_trade = await client.post(
        f"/api/v1/bets/{group_bet['id']}/buy",
        json={"outcome_id": yes_id, "amount": "20"},
        headers=auth(member_token),
    )
    assert member_trade.status_code == 200, member_trade.text
    member_yes_shares = Decimal(str(member_trade.json()["shares_out"]))

    admin_trade = await client.post(
        f"/api/v1/bets/{group_bet['id']}/buy",
        json={"outcome_id": no_id, "amount": "20"},
        headers=auth(admin_token),
    )
    assert admin_trade.status_code == 200, admin_trade.text
    admin_no_shares = Decimal(str(admin_trade.json()["shares_out"]))

    public_bet = await create_public_bet(client, public_creator_token)
    public_yes_id = public_bet["outcomes"][0]["id"]
    public_trade = await client.post(
        f"/api/v1/bets/{public_bet['id']}/buy",
        json={"outcome_id": public_yes_id, "amount": "10"},
        headers=auth(member_token),
    )
    assert public_trade.status_code == 200
    public_shares = Decimal(str(public_trade.json()["shares_out"]))

    await expire_bet(group_bet["id"])
    await expire_bet(public_bet["id"])

    forbidden = await client.post(
        f"/api/v1/bets/{group_bet['id']}/resolve",
        json={"outcome_id": yes_id},
        headers=auth(member_token),
    )
    assert forbidden.status_code == 403

    first_resolution = await client.post(
        f"/api/v1/bets/{group_bet['id']}/resolve",
        json={"outcome_id": yes_id},
        headers=auth(admin_token),
    )
    assert first_resolution.status_code == 200, first_resolution.text
    assert Decimal(str(first_resolution.json()["total_payout"])) == member_yes_shares
    assert await balance(client, member_token) == Decimal(970) + member_yes_shares

    correction = await client.post(
        f"/api/v1/bets/{group_bet['id']}/resolve",
        json={"outcome_id": no_id},
        headers=auth(admin_token),
    )
    assert correction.status_code == 200
    assert correction.json()["is_correction"] is True
    assert await balance(client, member_token) == Decimal(970)
    assert await balance(client, admin_token) == Decimal(980) + admin_no_shares

    public_resolution = await client.post(
        f"/api/v1/bets/{public_bet['id']}/resolve",
        json={"outcome_id": public_yes_id},
        headers=auth(admin_token),
    )
    assert public_resolution.status_code == 200

    group_board = await client.get(
        f"/api/v1/groups/{group['id']}/leaderboard?window=all_time",
        headers=auth(admin_token),
    )
    assert group_board.status_code == 200
    group_results = {
        row["display_name"]: Decimal(str(row["net_profit_loss"]))
        for row in group_board.json()["entries"]
    }
    assert group_results == {
        "Admin": admin_no_shares - Decimal(20),
        "Member": Decimal(-20),
    }

    public_board = await client.get(
        "/api/v1/leaderboards/public?window=all_time",
        headers=auth(member_token),
    )
    assert public_board.status_code == 200
    assert public_board.json()["scope"] == "public"
    public_results = {
        row["display_name"]: Decimal(str(row["net_profit_loss"]))
        for row in public_board.json()["entries"]
    }
    assert public_results == {"Member": public_shares - Decimal(10)}

    events = await client.get(
        f"/api/v1/bets/{group_bet['id']}/resolution-events",
        headers=auth(member_token),
    )
    assert [event["is_correction"] for event in events.json()] == [False, True]


@pytest.mark.asyncio
async def test_cancellation_refunds_every_stake(client: AsyncClient) -> None:
    creator_token = await signup(client, "cancel@market.example", "Canceller")
    other_token = await signup(client, "other@market.example", "Other")
    bet = await create_public_bet(client, creator_token, question="Cancel me?")

    trade = await client.post(
        f"/api/v1/bets/{bet['id']}/buy",
        json={"outcome_id": bet["outcomes"][0]["id"], "amount": "25"},
        headers=auth(creator_token),
    )
    assert trade.status_code == 200
    assert await balance(client, creator_token) == Decimal(975)

    forbidden = await client.delete(
        f"/api/v1/bets/{bet['id']}",
        headers=auth(other_token),
    )
    assert forbidden.status_code == 403

    cancelled = await client.delete(
        f"/api/v1/bets/{bet['id']}",
        headers=auth(creator_token),
    )
    assert cancelled.status_code == 200
    assert Decimal(str(cancelled.json()["refunded_points"])) == Decimal(25)
    assert await balance(client, creator_token) == Decimal(1000)

    public_feed = await client.get("/api/v1/public-bets", headers=auth(other_token))
    assert all(row["id"] != bet["id"] for row in public_feed.json())
    board = await client.get(
        "/api/v1/leaderboards/public?window=all_time",
        headers=auth(other_token),
    )
    assert board.json()["entries"] == []


@pytest.mark.asyncio
async def test_removed_member_keeps_only_existing_market_until_settlement(
    client: AsyncClient,
) -> None:
    admin_token = await signup(client, "remove-admin@test.com", "Admin")
    member_token = await signup(client, "removed@test.com", "Removed")
    group = await create_group(client, admin_token, "Removal group")
    await join_group(client, member_token, group["invite_code"])
    member_id = await current_user_id(client, member_token)
    existing_bet = await create_group_bet(client, admin_token, group["id"])

    first_trade = await client.post(
        f"/api/v1/bets/{existing_bet['id']}/buy",
        json={"outcome_id": existing_bet["outcomes"][0]["id"], "amount": "5"},
        headers=auth(member_token),
    )
    assert first_trade.status_code == 200

    removed = await client.delete(
        f"/api/v1/groups/{group['id']}/members/{member_id}",
        headers=auth(admin_token),
    )
    assert removed.status_code == 200

    rejoin = await client.post(
        "/api/v1/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth(member_token),
    )
    assert rejoin.status_code == 403
    assert rejoin.json()["error"]["code"] == "membership_removed"

    pending_groups = await client.get("/api/v1/groups", headers=auth(member_token))
    assert pending_groups.json()[0]["membership_status"] == "removed"
    assert pending_groups.json()[0]["pending_settlement"] is True
    assert pending_groups.json()[0]["invite_code"] is None

    existing_access = await client.get(
        f"/api/v1/bets/{existing_bet['id']}",
        headers=auth(member_token),
    )
    assert existing_access.status_code == 200
    continuing_trade = await client.post(
        f"/api/v1/bets/{existing_bet['id']}/buy",
        json={"outcome_id": existing_bet["outcomes"][0]["id"], "amount": "1"},
        headers=auth(member_token),
    )
    assert continuing_trade.status_code == 200

    future_bet = await create_group_bet(
        client,
        admin_token,
        group["id"],
        question="Created after removal?",
    )
    future_access = await client.get(
        f"/api/v1/bets/{future_bet['id']}",
        headers=auth(member_token),
    )
    assert future_access.status_code == 404
    group_feed = await client.get(
        f"/api/v1/groups/{group['id']}/bets",
        headers=auth(member_token),
    )
    assert group_feed.status_code == 200
    assert [row["id"] for row in group_feed.json()] == [existing_bet["id"]]

    cancellation = await client.delete(
        f"/api/v1/bets/{existing_bet['id']}",
        headers=auth(admin_token),
    )
    assert cancellation.status_code == 200
    assert await balance(client, member_token) == Decimal(1000)
    settled_groups = await client.get("/api/v1/groups", headers=auth(member_token))
    assert settled_groups.json() == []


@pytest.mark.asyncio
async def test_visibility_end_time_audit_and_refill(client: AsyncClient) -> None:
    admin_token = await signup(client, "audit-admin@test.com", "Admin")
    allowed_token = await signup(client, "allowed@test.com", "Allowed")
    hidden_token = await signup(client, "hidden@test.com", "Hidden")
    group = await create_group(client, admin_token, "Private group")
    await join_group(client, allowed_token, group["invite_code"])
    await join_group(client, hidden_token, group["invite_code"])
    allowed_user_id = await current_user_id(client, allowed_token)

    bet = await create_group_bet(
        client,
        admin_token,
        group["id"],
        visible_to_user_ids=[allowed_user_id],
    )
    allowed = await client.get(
        f"/api/v1/bets/{bet['id']}",
        headers=auth(allowed_token),
    )
    assert allowed.status_code == 200

    hidden = await client.get(
        f"/api/v1/bets/{bet['id']}",
        headers=auth(hidden_token),
    )
    assert hidden.status_code == 404

    new_end_time = datetime.now(UTC) + timedelta(days=2)
    edited = await client.patch(
        f"/api/v1/bets/{bet['id']}/end-time",
        json={"end_time": new_end_time.isoformat()},
        headers=auth(admin_token),
    )
    assert edited.status_code == 200
    edit_events = await client.get(
        f"/api/v1/bets/{bet['id']}/edit-events",
        headers=auth(admin_token),
    )
    assert len(edit_events.json()) == 1
    assert edit_events.json()[0]["edit_type"] == "end_time"

    async with db.SessionFactory.begin() as session:
        user = await session.scalar(
            select(User).where(User.email == "audit-admin@test.com")
        )
        assert user is not None
        user.last_refill_at = datetime.now(UTC) - timedelta(days=8)
        count = await run_refills(
            session,
            settings=get_settings(),
            now=datetime.now(UTC),
        )
        assert count == 1
    assert await balance(client, admin_token) == Decimal(1500)
