import asyncio
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


async def trade(
    client: AsyncClient,
    token: str,
    bet_id: str,
    *,
    side: str,
    shares: str,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/markets/{bet_id}/trade",
        json={"side": side, "shares": shares},
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    return response.json()


async def current_user_id(client: AsyncClient, token: str) -> str:
    response = await client.get("/api/v1/users/me", headers=auth(token))
    assert response.status_code == 200
    return str(response.json()["id"])


@pytest.mark.asyncio
async def test_trading_resolution_is_final_and_scope_isolated_leaderboards(
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

    legacy_handler = await client.post(
        f"/api/v1/bets/{group_bet['id']}/preview-buy",
        json={"outcome_id": yes_id, "amount": "1"},
        headers=auth(member_token),
    )
    assert legacy_handler.status_code == 409
    assert legacy_handler.json()["error"]["code"] == "pricing_method_mismatch"

    member_trade = await trade(
        client,
        member_token,
        group_bet["id"],
        side="yes",
        shares="20",
    )
    member_yes_shares = Decimal(str(member_trade["delta_shares"]))
    member_cost = Decimal(str(member_trade["cost"]))

    admin_trade = await trade(
        client,
        admin_token,
        group_bet["id"],
        side="no",
        shares="20",
    )
    admin_cost = Decimal(str(admin_trade["cost"]))

    public_bet = await create_public_bet(client, public_creator_token)
    public_yes_id = public_bet["outcomes"][0]["id"]
    public_trade = await trade(
        client,
        member_token,
        public_bet["id"],
        side="yes",
        shares="10",
    )
    public_shares = Decimal(str(public_trade["delta_shares"]))
    public_cost = Decimal(str(public_trade["cost"]))

    await expire_bet(group_bet["id"])
    await expire_bet(public_bet["id"])

    forbidden_end_time_edit = await client.patch(
        f"/api/v1/bets/{group_bet['id']}/end-time",
        json={"end_time": (datetime.now(UTC) + timedelta(days=2)).isoformat()},
        headers=auth(member_token),
    )
    assert forbidden_end_time_edit.status_code == 403

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
    assert await balance(client, member_token) == (
        Decimal(1000) - member_cost - public_cost + member_yes_shares
    )

    resolved_end_time_edit = await client.patch(
        f"/api/v1/bets/{group_bet['id']}/end-time",
        json={"end_time": (datetime.now(UTC) + timedelta(days=2)).isoformat()},
        headers=auth(admin_token),
    )
    assert resolved_end_time_edit.status_code == 409
    assert resolved_end_time_edit.json()["error"]["code"] == "bet_immutable"

    second_resolution = await client.post(
        f"/api/v1/bets/{group_bet['id']}/resolve",
        json={"outcome_id": no_id},
        headers=auth(admin_token),
    )
    assert second_resolution.status_code == 409
    assert second_resolution.json()["error"]["code"] == "bet_already_resolved"
    assert await balance(client, member_token) == (
        Decimal(1000) - member_cost - public_cost + member_yes_shares
    )
    assert await balance(client, admin_token) == Decimal(1000) - admin_cost

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
        "Admin": -admin_cost,
        "Member": member_yes_shares - member_cost,
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
    assert public_results == {"Member": public_shares - public_cost}

    group_house = await client.get(
        f"/api/v1/groups/{group['id']}/house",
        headers=auth(admin_token),
    )
    assert group_house.status_code == 200
    assert Decimal(str(group_house.json()["realized_profit_loss"])) == (
        member_cost + admin_cost - member_yes_shares
    )

    events = await client.get(
        f"/api/v1/bets/{group_bet['id']}/resolution-events",
        headers=auth(member_token),
    )
    assert [event["is_correction"] for event in events.json()] == [False]


@pytest.mark.asyncio
async def test_cancellation_refunds_every_stake(client: AsyncClient) -> None:
    creator_token = await signup(client, "cancel@market.example", "Canceller")
    other_token = await signup(client, "other@market.example", "Other")
    bet = await create_public_bet(client, creator_token, question="Cancel me?")

    placed = await trade(
        client,
        creator_token,
        bet["id"],
        side="yes",
        shares="25",
    )
    cost = Decimal(str(placed["cost"]))
    assert await balance(client, creator_token) == Decimal(1000) - cost

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
    assert Decimal(str(cancelled.json()["refunded_points"])) == cost
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

    await trade(
        client,
        member_token,
        existing_bet["id"],
        side="yes",
        shares="5",
    )

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
        f"/api/v1/markets/{existing_bet['id']}/trade",
        json={"side": "yes", "shares": "1"},
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


@pytest.mark.asyncio
async def test_lmsr_quotes_sells_trade_audit_and_house_cash_flow(
    client: AsyncClient,
) -> None:
    trader_token = await signup(client, "lmsr-trader@test.com", "Trader")
    bet = await create_public_bet(client, trader_token, question="LMSR audit?")
    assert bet["pricing_method"] == "lmsr"
    assert Decimal(str(bet["b_liquidity"])) == Decimal(100)
    assert Decimal(str(bet["q_yes"])) == Decimal(0)
    assert Decimal(str(bet["q_no"])) == Decimal(0)

    unauthenticated_price = await client.get(
        f"/api/v1/markets/{bet['id']}/price"
    )
    assert unauthenticated_price.status_code == 200
    assert Decimal(str(unauthenticated_price.json()["price_yes"])) == Decimal("0.5")
    assert Decimal(str(unauthenticated_price.json()["price_no"])) == Decimal("0.5")

    buy_quote = await client.get(
        f"/api/v1/markets/{bet['id']}/quote",
        params={"side": "yes", "shares": "10"},
    )
    assert buy_quote.status_code == 200, buy_quote.text
    buy = await trade(
        client,
        trader_token,
        bet["id"],
        side="yes",
        shares="10",
    )
    assert buy["cost"] == buy_quote.json()["cost"]

    sell_quote = await client.get(
        f"/api/v1/markets/{bet['id']}/quote",
        params={"side": "yes", "shares": "-4"},
    )
    assert sell_quote.status_code == 200
    sell = await trade(
        client,
        trader_token,
        bet["id"],
        side="yes",
        shares="-4",
    )
    assert Decimal(str(sell["cost"])) < 0
    assert Decimal(str(sell["position_shares"])) == Decimal(6)

    oversell = await client.post(
        f"/api/v1/markets/{bet['id']}/trade",
        json={"side": "yes", "shares": "-7"},
        headers=auth(trader_token),
    )
    assert oversell.status_code == 409
    assert oversell.json()["error"]["code"] == "insufficient_shares"

    audits = await client.get(
        f"/api/v1/markets/{bet['id']}/trades",
        headers=auth(trader_token),
    )
    assert audits.status_code == 200
    assert [Decimal(str(row["delta_shares"])) for row in audits.json()] == [
        Decimal(10),
        Decimal(-4),
    ]
    expected_cash = Decimal(str(buy["cost"])) + Decimal(str(sell["cost"]))
    assert sum(
        (Decimal(str(row["house_cash_flow"])) for row in audits.json()),
        start=Decimal(0),
    ) == expected_cash

    house = await client.get(
        f"/api/v1/bets/{bet['id']}/house",
        headers=auth(trader_token),
    )
    assert house.status_code == 200
    assert house.json()["trades"] == 2
    assert Decimal(str(house.json()["trade_cash_flow"])) == expected_cash
    assert Decimal(str(house.json()["current_cash_balance"])) == expected_cash
    assert Decimal(str(house.json()["reserved_exposure"])) > 0

    ledger = await client.get(
        f"/api/v1/bets/{bet['id']}/house-ledger",
        headers=auth(trader_token),
    )
    assert [row["entry_type"] for row in ledger.json()] == [
        "reserve",
        "trade",
        "trade",
    ]


@pytest.mark.asyncio
async def test_concurrent_lmsr_trades_have_no_lost_update(
    client: AsyncClient,
) -> None:
    trader_token = await signup(client, "concurrent@test.com", "Concurrent")
    bet = await create_public_bet(client, trader_token, question="Concurrent LMSR?")

    async def buy_five() -> Any:
        return await client.post(
            f"/api/v1/markets/{bet['id']}/trade",
            json={"side": "yes", "shares": "5"},
            headers=auth(trader_token),
        )

    first, second = await asyncio.gather(buy_five(), buy_five())
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    price = await client.get(f"/api/v1/markets/{bet['id']}/price")
    assert Decimal(str(price.json()["q_yes"])) == Decimal(10)
    audits = await client.get(
        f"/api/v1/markets/{bet['id']}/trades",
        headers=auth(trader_token),
    )
    assert [row["sequence"] for row in audits.json()] == [1, 2]
    assert [Decimal(str(row["q_yes_after"])) for row in audits.json()] == [
        Decimal(5),
        Decimal(10),
    ]
