"""M1 草稿转正常驻 job（小时级）。

真源：``docs/spec/SPEC-M1-wechat-login.md`` §5.1 + §8 数据流图底部 cron。
"""

from __future__ import annotations

import asyncio

from app.core.log import logger, setup_logging
from app.db.session import dispose_engine, get_sessionmaker
from app.services.users.draft_promotion import promote_due_drafts

JOB_INTERVAL_SECONDS = 3600  # 1h


async def _loop() -> None:
    setup_logging(level="INFO")
    sm = get_sessionmaker()
    while True:
        try:
            async with sm() as session:
                promoted = await promote_due_drafts(session)
                await session.commit()
            logger.info("promote_drafts_tick", promoted=promoted)
        except Exception:
            logger.exception("promote_drafts_tick_failed")
        await asyncio.sleep(JOB_INTERVAL_SECONDS)


def main() -> None:
    try:
        asyncio.run(_loop())
    finally:
        asyncio.run(dispose_engine())


if __name__ == "__main__":
    main()
