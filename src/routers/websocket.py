import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from src.connection_manager import connection_manager

router = APIRouter(tags=["Websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """
    WebSocket endpoint with support for:
    - Echo messages
    - Broadcast messages
    - Ping/pong for health checking
    """
    manager = connection_manager

    try:
        assigned_id = await manager.connect(websocket, client_id)

        await manager.send_personal_message(
            f"Welcome! Your client ID: {assigned_id}", websocket
        )
        logger.info(f"[WS][/ws] New webSocket client: {assigned_id}")

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300)

                if data.strip().lower() == "ping":
                    await manager.send_personal_message("pong", websocket)
                    continue

                if data.startswith("/broadcast "):
                    message = data[len("/broadcast ") :]
                    await manager.broadcast(
                        f"[Broadcast from {assigned_id}]: {message}",
                        exclude={websocket},
                    )
                    await manager.send_personal_message(
                        "Message broadcasted to all clients", websocket
                    )
                else:
                    await manager.send_personal_message(f"Echo: {data}", websocket)

            except asyncio.TimeoutError:
                try:
                    await manager.send_personal_message("ping", websocket)
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info(f"Client {assigned_id} disconnected normally")
    except Exception as exc:
        logger.exception(f"Error in WebSocket connection {assigned_id}: {exc}")
    finally:
        await manager.disconnect(websocket)
