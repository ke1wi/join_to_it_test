import asyncio
import os
import signal
from functools import partial

from loguru import logger

from src.config import AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN
from src.connection_manager import connection_manager
from src.utils import graceful_shutdown


class SignalHandler:
    """
    Safe pre-uvicorn signal handler with:
    - graceful WebSocket shutdown
    - multi-signal protection (3 attempts → force stop)
    - uvicorn forwarding
    - safe async/sync bridging
    """

    def __init__(self):
        self.shutdown_in_progress = False
        self.signal_count = 0

        self.original = {
            signal.SIGINT: signal.getsignal(signal.SIGINT),
            signal.SIGTERM: signal.getsignal(signal.SIGTERM),
        }

    async def handle(self, sig: signal.Signals):
        """Main graceful-shutdown flow."""

        self.signal_count += 1
        if self.signal_count >= AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN:
            logger.warning("Force shutdown activated — forwarding signal immediately.")
            self.restore_original_handlers()
            await self.forward_signal(sig)
            return

        if self.shutdown_in_progress:
            logger.warning(
                f"Received {sig.name} ({self.signal_count}/{AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN})"
            )
            return

        self.shutdown_in_progress = True
        logger.info("Starting graceful shutdown...")

        connection_manager.accepting_connections = False

        try:
            await graceful_shutdown(connection_manager)
        except Exception as e:
            logger.exception(f"Graceful shutdown failure: {e}")
        finally:
            logger.info("Graceful shutdown complete. Forwarding signal to uvicorn.")

        self.restore_original_handlers()
        await self.forward_signal(sig)

    async def forward_signal(self, sig: signal.Signals):
        """
        Sends signal to uvicorn AFTER the next event loop tick.
        Prevents race conditions where the signal arrives too early.
        """
        loop = asyncio.get_running_loop()

        await asyncio.sleep(0)

        loop.call_soon(os.kill, os.getpid(), sig.value)

    def restore_original_handlers(self):
        """Restore uvicorn's original handlers before forwarding the signal."""
        for sig, handler in self.original.items():
            signal.signal(sig, handler)

    def install(self):
        """
        Install our handlers before uvicorn registers its own.
        """

        def sync_wrapper(sig, *_):
            asyncio.create_task(self.handle(sig))

        # partial prevents late binding bugs
        signal.signal(signal.SIGINT, partial(sync_wrapper, signal.SIGINT))
        signal.signal(signal.SIGTERM, partial(sync_wrapper, signal.SIGTERM))


signal_handler = SignalHandler()
