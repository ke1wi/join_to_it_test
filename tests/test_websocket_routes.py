from fastapi.testclient import TestClient

from src.main import app


def test_websocket_connection():
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("ping")
        response = websocket.receive_text()
        assert response
