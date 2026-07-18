"""M1 草稿用户 24h 转正 cron（手动可调用 / 也可被 scheduler 周期执行）。

真源：``docs/spec/TDS-M1-wechat-login.md`` §5.1 + AC-M1-03。

调用方式：
1. ``python -m backend.app.cron.promote_drafts`` （一次性）
2. ``python -m backend.app.jobs.promote_drafts_job`` （常驻 worker，hourly）
"""

from __future__ import annotations

import asyncio

from app.core.log import logger, setup_logging
from app.db.session import dispose_engine, get_sessionmaker
from app.services.users.draft_promotion import promote_due_drafts


async def _run() -> int:
    setup_logging(level="INFO")
    sm = get_sessionmaker()
    async with sm() as session:
        promoted = await promote_due_drafts(session)
        await session.commit()
    logger.info("promote_drafts_done", promoted=promoted)
    return promoted


def main() -> None:
    promoted = asyncio.run(_run())
    logger.info("promote_drafts_main_done", promoted=promoted)


if __name__ == "__main__":
    try:
        main()
    finally:
        asyncio.run(dispose_engine())
