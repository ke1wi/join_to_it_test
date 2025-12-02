import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.connection_manager import connection_manager
from src.routers.rest import router as rest_router
from src.routers.websocket import router as websocket_router
from src.signal_handler import signal_handler
from src.utils import notification_loop

# --------------------- SIGNAL HANDLER------------------------
signal_handler.install()

# ------------------------ LOGGING ------------------------
logging.getLogger("uvicorn.error").disabled = True
logging.getLogger("uvicorn.access").disabled = True


# ------------------------ FASTAPI APP ------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 [{os.getpid()}] Application started (docs: /docs)")

    # Start background notification task
    notification_task = asyncio.create_task(notification_loop(connection_manager))

    await connection_manager.start_connection_cleanup()

    try:
        yield
    finally:
        notification_task.cancel()
        with suppress(asyncio.CancelledError):
            await notification_task

        await connection_manager.stop_connection_cleanup()

        logger.info(f"🛑 [{os.getpid()}] Application shutdown complete")


app = FastAPI(
    title="WebSocket Notification Server",
    description="WebSocket notification server with broadcast and personal message support",
    version="2.0.0",
    lifespan=lifespan,
)

# ------------------------ ROUTES ------------------------
app.include_router(rest_router)
app.include_router(websocket_router)

# ------------------------ CORS ------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # SAFE default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
