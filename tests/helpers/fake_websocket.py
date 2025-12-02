from unittest.mock import AsyncMock


class FakeWebSocket:
    def __init__(self):
        self.accept = AsyncMock()
        self.send_text = AsyncMock()
        self.close = AsyncMock()
