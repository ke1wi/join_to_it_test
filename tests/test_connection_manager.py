import pytest

from src.connection_manager import ConnectionManager
from tests.helpers.fake_websocket import FakeWebSocket


@pytest.mark.asyncio
async def test_connect_and_disconnect():
    manager = ConnectionManager()
    manager._ws_to_info.clear()
    manager._id_to_ws.clear()

    ws = FakeWebSocket()

    client_id = await manager.connect(ws)

    assert await manager.count() == 1
    assert client_id.startswith("cli_")

    await manager.disconnect(ws)
    assert await manager.count() == 0


@pytest.mark.asyncio
async def test_broadcast_message():
    manager = ConnectionManager()
    manager._ws_to_info.clear()
    manager._id_to_ws.clear()

    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    await manager.connect(ws1)
    await manager.connect(ws2)

    await manager.broadcast("hello")

    ws1.send_text.assert_called_with("hello")
    ws2.send_text.assert_called_with("hello")


@pytest.mark.asyncio
async def test_close_all_connections():
    manager = ConnectionManager()
    manager._ws_to_info.clear()
    manager._id_to_ws.clear()

    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    await manager.connect(ws1)
    await manager.connect(ws2)

    await manager.close_all()

    assert await manager.count() == 0
    ws1.close.assert_called_once()
    ws2.close.assert_called_once()
