import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.connection_manager import connection_manager
from src.routers.rest import router as rest_router
from src.routers.websocket import router as websocket_router
from src.signal_handler import signal_handler
from src.utils import notification_loop

# ------------------------ LOGGING ------------------------
logging.disable()
# ------------------------ FASTAPI ------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[Dict[str, Any]]:
    """
    Production-safe lifespan.
    Uvicorn will not close WebSocket connections
    until we call restore handlers and re-send the signal.
    """
    logger.info(
        f"🚀 [{os.getpid()}] Application started on http://127.0.0.1:8000, Docs: http://127.0.0.1:8000/docs"
    )

    notification_task = asyncio.create_task(notification_loop(connection_manager))
    signal_handler.install()

    await connection_manager.start_connection_cleanup()

    try:
        yield
    finally:

        notification_task.cancel()
        with suppress(asyncio.CancelledError):
            await notification_task

        await connection_manager.stop_connection_cleanup()

        logger.info("Application shutdown")


app = FastAPI(
    title="WebSocket Notification Server",
    description="WebSocket notification server with broadcast and personal message support",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(rest_router)
app.include_router(websocket_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
