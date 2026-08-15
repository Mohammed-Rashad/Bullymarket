import sqlite3
from pathlib import Path

import pytest
from alembic import command

from tests.conftest import alembic_config


def _sqlite_path(database_url: str) -> Path:
    return Path(database_url.removeprefix("sqlite+aiosqlite:///"))


def test_initial_migration_upgrades_and_downgrades(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'migration.db'}"
    config = alembic_config(database_url)

    command.upgrade(config, "head")
    with sqlite3.connect(_sqlite_path(database_url)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "users",
        "groups",
        "group_members",
        "bets",
        "outcomes",
        "positions",
        "ledger_entries",
        "resolution_events",
        "bet_visibility_overrides",
        "bet_edit_events",
        "trades",
        "house_ledger_entries",
    } <= tables
    command.check(config)

    with sqlite3.connect(_sqlite_path(database_url)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        user_id = "11111111111111111111111111111111"
        group_id = "22222222222222222222222222222222"
        public_bet_id = "33333333333333333333333333333333"
        connection.execute(
            "INSERT INTO users (id, email, display_name, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, "scope@example.com", "Scope", "not-a-real-hash"),
        )
        connection.execute(
            "INSERT INTO groups (id, name, created_by, invite_code) VALUES (?, ?, ?, ?)",
            (group_id, "Scope group", user_id, "scope-code"),
        )
        connection.execute(
            "INSERT INTO group_members (id, group_id, user_id, role) VALUES (?, ?, ?, ?)",
            ("44444444444444444444444444444444", group_id, user_id, "admin"),
        )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO bets "
                "(id, group_id, created_by, question, visibility, end_time, liquidity_seed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    public_bet_id,
                    group_id,
                    user_id,
                    "Invalid mixed-scope bet?",
                    "public",
                    "2030-01-01T00:00:00+00:00",
                    100,
                ),
            )

        connection.execute(
            "INSERT INTO bets "
            "(id, group_id, created_by, question, visibility, end_time, liquidity_seed) "
            "VALUES (?, NULL, ?, ?, ?, ?, ?)",
            (
                public_bet_id,
                user_id,
                "Valid public bet?",
                "public",
                "2030-01-01T00:00:00+00:00",
                100,
            ),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO bet_visibility_overrides "
                "(id, bet_id, group_id, user_id) VALUES (?, ?, ?, ?)",
                (
                    "55555555555555555555555555555555",
                    public_bet_id,
                    group_id,
                    user_id,
                ),
            )

    command.downgrade(config, "base")
    with sqlite3.connect(_sqlite_path(database_url)) as connection:
        remaining = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' "
                "AND name NOT IN ('sqlite_sequence', 'alembic_version')"
            )
        }
    assert remaining == set()
