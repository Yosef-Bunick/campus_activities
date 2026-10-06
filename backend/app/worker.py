"""Daily jobs (architecture §2, §9): the 150-day inactivity purge.

Runs inside the API process as a background task (no paid cron service needed),
once shortly after startup and then every 24 hours. Turn off with
WORKER_ENABLED=0 (tests do). Run once by hand with `python -m app.worker`.
"""

from __future__ import annotations

import asyncio
import logging

from sqlmodel import Session

from app.core import database
from app.services.purge import purge_inactive

log = logging.getLogger("worker")
EVERY = 24 * 3600
FIRST_RUN_DELAY = 60


def run_once() -> int:
    with Session(database.engine) as s:
        deleted = purge_inactive(s)
    log.info("inactivity purge: deleted %d account(s)", deleted)
    return deleted


async def daily_loop() -> None:
    await asyncio.sleep(FIRST_RUN_DELAY)
    while True:
        try:
            await asyncio.to_thread(run_once)
        except Exception:  # never let one bad night kill the API
            log.exception("daily jobs failed")
        await asyncio.sleep(EVERY)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Deleted {run_once()} inactive account(s)")
