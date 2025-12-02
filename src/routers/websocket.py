import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from src.connection_manager import connection_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str | None = None):
    """
    WebSocket endpoint:
    - assigns unique client_id
    - supports echo & broadcast commands
    - handles ping/pong
    - handles graceful disconnect
    """
    manager = connection_manager
    assigned_id = None

    try:
        assigned_id = await manager.connect(websocket, client_id)

        await manager.send_personal_message(
            f"Welcome! Your client ID is: {assigned_id}", websocket
        )

        logger.info("WS client connected", client_id=assigned_id)

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300)

                cleaned = data.strip().lower()

                if cleaned == "ping":
                    await manager.send_personal_message("pong", websocket)
                    continue

                if cleaned.startswith("/broadcast "):
                    message = data[len("/broadcast ") :].strip()
                    await manager.broadcast(
                        f"[Broadcast from {assigned_id}]: {message}",
                        exclude={websocket},
                    )
                    await manager.send_personal_message("Broadcast sent.", websocket)
                    continue

                await manager.send_personal_message(f"Echo: {data}", websocket)

            except asyncio.TimeoutError:
                try:
                    await manager.send_personal_message("ping", websocket)
                except Exception:
                    logger.warning(
                        "Client unresponsive — closing connection",
                        client_id=assigned_id,
                    )
                    break

    except WebSocketDisconnect:
        logger.info("Client disconnected", client_id=assigned_id)
    except Exception as exc:
        logger.exception(f"Unhandled WebSocket error for client {assigned_id}: {exc}")
    finally:
        await manager.disconnect(websocket)
        logger.info("Client cleanup done", client_id=assigned_id)
