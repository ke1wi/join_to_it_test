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

    try:
        while True:
            await asyncio.sleep(NOTIFICATION_INTERVAL)

            active_count = await manager.count()
            if active_count == 0:
                continue

            counter += 1
            msg = f"[System] Periodic notification #{counter} - Active clients: {active_count}"
            logger.info(f"Sending periodic notification: {msg}")

            try:
                await manager.broadcast(msg)
            except Exception as exc:
                logger.error(f"Broadcast failure: {exc}")

    except asyncio.CancelledError:
        logger.info("Notification loop cancelled — stopping cleanly.")


async def graceful_shutdown(
    manager: ConnectionManager,
    wait_seconds: int = TIME_TO_WAIT_FOR_SHUTDOWN,
    poll_interval: int = POLLING_INTERVAL,
):
    """
    Graceful shutdown:
      - if no clients → exit immediately
      - if clients exist → wait up to wait_seconds
      - then force close all
    """

    logger.info("Graceful shutdown started.")
    manager.accepting_connections = False

    start_ts = time.monotonic()
    last_broadcast_time = 0

    while True:
        active = await manager.count()

        if active == 0:
            logger.info("Graceful shutdown: no active clients — exiting immediately.")
            return

        elapsed = time.monotonic() - start_ts
        remaining = wait_seconds - elapsed

        if remaining <= 0:
            logger.warning(
                f"{wait_seconds} seconds elapsed. {active} clients still connected. "
                "Closing all connections forcibly..."
            )
            try:
                await manager.close_all(code=1001, reason="Server shutdown (timeout)")
            except Exception as exc:
                logger.error(f"Error during forced close_all: {exc}")
            return

        if elapsed - last_broadcast_time >= poll_interval * 10:
            last_broadcast_time = elapsed
            try:
                await manager.broadcast(
                    f"[System] Server is shutting down. Remaining ~{remaining:.0f} sec..."
                )
            except Exception as exc:
                logger.error(f"Shutdown broadcast failed: {exc}")

        logger.info(
            f"Shutdown waiting: active clients = {active}, "
            f"remaining ~{remaining:.0f} sec..."
        )

        await asyncio.sleep(poll_interval)
