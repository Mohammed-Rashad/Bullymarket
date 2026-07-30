import asyncio

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.modules.refill.service import run_refills


async def main() -> None:
    async with SessionFactory.begin() as session:
        await run_refills(session, settings=get_settings())


if __name__ == "__main__":
    asyncio.run(main())

