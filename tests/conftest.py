import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app


@pytest.fixture
def client():
    """Sync TestClient for WebSocket tests."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
