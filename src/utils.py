import asyncio
import time

from loguru import logger

from src.config import (
    NOTIFICATION_INTERVAL,
    POLLING_INTERVAL,
    TIME_TO_WAIT_FOR_SHUTDOWN,
)
from src.connection_manager import ConnectionManager


async def notification_loop(manager: ConnectionManager) -> None:
    """
    Background task for periodic notifications.
    """
    counter = 0
    while True:
        try:
            await asyncio.sleep(NOTIFICATION_INTERVAL)

            active_count = await manager.count()
            if active_count == 0:
                continue

            counter += 1
            msg = f"[System] Periodic notification #{counter} - Active clients: {active_count}"
            logger.info(f"Sending periodic notification: {msg}")

            await manager.broadcast(msg)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Error in notification loop: {exc}")
            await asyncio.sleep(POLLING_INTERVAL)


async def graceful_shutdown(
    manager: ConnectionManager,
    wait_seconds: int = TIME_TO_WAIT_FOR_SHUTDOWN,
    poll_interval: int = POLLING_INTERVAL,
):
    """
    Graceful shutdown:
      - if no clients → exit immediately
      - if clients exist → wait up to 30 minutes
      - after 30 minutes — forcibly close all connections
    """

    start_ts = time.monotonic()

    while True:
        active = await manager.count()

        if active == 0:
            logger.info("Graceful shutdown: no active clients — exiting immediately.")
            return

        elapsed = time.monotonic() - start_ts
        remaining = wait_seconds - elapsed

        if remaining <= 0:
            logger.warning(
                f"{wait_seconds} seconds elapsed. {active} clients remaining. "
                "Forcibly closing WebSocket connections."
            )
            await manager.close_all(code=1001, reason="Server shutdown (timeout)")
            return

        logger.info(
            f"Shutdown waiting: active clients = {active}, "
            f"remaining ~{remaining:.0f} sec..."
        )
        await manager.broadcast(
            f"[System] Server is shutting down. Remaining ~{remaining:.0f} sec..."
        )

        await asyncio.sleep(poll_interval)
