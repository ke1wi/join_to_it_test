import asyncio
import os
import signal

from loguru import logger

from src.config import AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN
from src.connection_manager import connection_manager
from src.utils import graceful_shutdown


class SignalHandler:
    """
    Pre-uvicorn signal handler that performs graceful shutdown of WebSocket clients.
    Safe for:
    - uvicorn CLI
    - uvicorn workers
    - Docker SIGTERM
    - press-Ctrl+C multiple times
    """

    def __init__(self):
        self.shutdown_in_progress = False
        self.signal_count = 0

        self.original = {
            signal.SIGINT: signal.getsignal(signal.SIGINT),
            signal.SIGTERM: signal.getsignal(signal.SIGTERM),
        }

    async def handle(self, sig: signal.Signals):
        """Main async shutdown logic."""

        self.signal_count += 1
        logger.info(
            f"Signal received: {sig.name} | count={self.signal_count}/{AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN}"
        )

        if self.signal_count >= AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN:
            logger.warning("Force shutdown triggered — sending signal back to uvicorn.")
            self.restore_original_handlers()
            os.kill(os.getpid(), sig.value)
            return

        if self.shutdown_in_progress:
            logger.warning("Shutdown already in progress — ignoring signal.")
            return

        self.shutdown_in_progress = True

        logger.info("Starting graceful shutdown...")
        connection_manager.accepting_connections = False

        await graceful_shutdown(connection_manager)

        logger.info("Graceful shutdown finished. Passing signal to uvicorn...")

        self.restore_original_handlers()
        os.kill(os.getpid(), sig.value)

    def restore_original_handlers(self):
        for sig, handler in self.original.items():
            signal.signal(sig, handler)

    def install(self):
        """Install handlers BEFORE uvicorn installs its own."""

        def wrapper(sig):
            asyncio.create_task(self.handle(sig))

        # Need explicit sig value binding to avoid late binding bug
        signal.signal(signal.SIGINT, lambda *_: wrapper(signal.SIGINT))
        signal.signal(signal.SIGTERM, lambda *_: wrapper(signal.SIGTERM))


signal_handler = SignalHandler()
