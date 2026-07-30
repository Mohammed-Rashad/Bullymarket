from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from app.core import db
from app.main import create_app


def alembic_config(database_url: str) -> Config:
    config_path = Path(__file__).parents[1] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", database_url)
    config.attributes["preserve_config_url"] = True
    return config


@pytest.fixture
def migrated_database(tmp_path: Path) -> Iterator[str]:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'bullymarket-test.db'}"
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    yield database_url
    command.downgrade(config, "base")


@pytest.fixture
async def client(migrated_database: str) -> AsyncIterator[AsyncClient]:
    await db.configure_database(migrated_database)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    await db.engine.dispose()

