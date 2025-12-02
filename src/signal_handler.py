import asyncio
import signal

from loguru import logger

from src.config import AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN
from src.connection_manager import connection_manager
from src.utils import graceful_shutdown


class SignalHandler:
    """Handles graceful shutdown on SIGINT/SIGTERM signals."""

    def __init__(self):
        self.shutdown_in_progress = False
        self.signal_count = 0
        self.original_sigint = signal.getsignal(signal.SIGINT)
        self.original_sigterm = signal.getsignal(signal.SIGTERM)

    async def shutdown_handler(self, sig: signal.Signals):
        """
        Graceful shutdown entry point.
        Called BEFORE uvicorn receives the signal.
        Three consecutive signals will force immediate shutdown.
        """
        self.signal_count += 1

        if self.signal_count >= AMOUNT_OF_SIGNALS_TO_FORCE_SHUTDOWN:
            logger.warning(
                f"Received {sig.name} {self.signal_count} times — forcing immediate shutdown!"
            )
            signal.signal(signal.SIGINT, self.original_sigint)
            signal.signal(signal.SIGTERM, self.original_sigterm)
            signal.raise_signal(sig)
            return

        if self.shutdown_in_progress:
            logger.warning(
                f"Shutdown already in progress — signal count: {self.signal_count}/3"
            )
            return

        self.shutdown_in_progress = True

        logger.info(
            f"Received {sig.name} — starting graceful shutdown... (signal {self.signal_count}/3)"
        )

        connection_manager.accepting_connections = False

        await graceful_shutdown(connection_manager)

        signal.signal(signal.SIGINT, self.original_sigint)
        signal.signal(signal.SIGTERM, self.original_sigterm)

        signal.raise_signal(sig)

    def install(self):
        """
        Installs signal handlers BEFORE uvicorn installs its own.
        Intercepts SIGINT/SIGTERM, runs shutdown, then hands control back.
        """
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(
                sig,
                lambda s, *_: asyncio.create_task(
                    self.shutdown_handler(signal.Signals(s))
                ),
            )


signal_handler = SignalHandler()
