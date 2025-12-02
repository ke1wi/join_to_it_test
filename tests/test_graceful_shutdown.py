from unittest.mock import AsyncMock, MagicMock

import pytest

from src.utils import graceful_shutdown


@pytest.mark.asyncio
async def test_graceful_shutdown_waits_and_exits():
    manager = MagicMock()
    manager.count = AsyncMock(side_effect=[2, 1, 0])
    manager.broadcast = AsyncMock()
    manager.close_all = AsyncMock()

    await graceful_shutdown(manager, wait_seconds=3, poll_interval=1)

    manager.close_all.assert_not_called()


@pytest.mark.asyncio
async def test_forced_shutdown_after_timeout():
    manager = MagicMock()
    manager.count = AsyncMock(return_value=2)
    manager.close_all = AsyncMock()

    await graceful_shutdown(manager, wait_seconds=0, poll_interval=1)

    manager.close_all.assert_called_once()
