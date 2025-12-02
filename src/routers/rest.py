import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from src.config import NOTIFICATION_MESSAGE_STRIP
from src.connection_manager import connection_manager
from src.schemas import NotificationRequest

router = APIRouter(tags=["REST"])


@router.get("/")
async def root():
    """Root endpoint for checking server status"""
    logger.info("[GET][/] Root endpoint accessed")
    return JSONResponse(
        {
            "status": "ok",
            "service": "WebSocket Notification Server",
            "endpoints": {"websocket": "/ws", "notify": "/notify", "status": "/status"},
        }
    )


@router.get("/status")
async def get_status():
    """Server status and connection statistics"""
    logger.info("[GET][/status] Status endpoint accessed")
    manager = connection_manager
    active_clients = await manager.get_active_clients()

    return {
        "status": "running",
        "active_connections": await manager.count(),
        "accepting_new_connections": manager.accepting_connections,
        "clients": active_clients,
        "total_clients": len(active_clients),
    }


@router.post("/notify")
async def notify_all(notification: NotificationRequest):
    """
    HTTP endpoint for sending notifications to all clients.
    Supports broadcast and personal messages.
    """
    logger.info(f"[POST][/notify] Notify endpoint accessed: {notification}")
    manager = connection_manager

    if notification.broadcast:
        await manager.broadcast(notification.message)
        action = "broadcast"
    else:
        action = "personal"
        raise HTTPException(
            status_code=501,
            detail="Personal notifications not implemented in this endpoint",
        )

    return {
        "status": "sent",
        "action": action,
        "message": (
            notification.message[:NOTIFICATION_MESSAGE_STRIP] + "..."
            if len(notification.message) > NOTIFICATION_MESSAGE_STRIP
            else notification.message
        ),
        "active_connections": await manager.count(),
        "timestamp": time.time(),
    }


@router.post("/notify/{client_id}")
async def notify_client(client_id: str, message: str):
    """
    HTTP endpoint for sending a message to a specific client.
    Note: This is a demonstration implementation.
    In a real application, you need to store a mapping of client_id -> WebSocket.
    """
    logger.info(
        f"[POST][/notify/{client_id}] Notify client {client_id} with message: {message}"
    )
    manager = connection_manager

    # Find WebSocket by client_id
    async with manager._lock:
        target_websocket = None
        for ws, info in manager._connections.items():
            if info.get("id") == client_id:
                target_websocket = ws
                break

    if target_websocket is None:
        raise HTTPException(
            status_code=404, detail=f"Client {client_id} not found or not connected"
        )

    await manager.send_personal_message(
        f"[Direct message from server]: {message}", target_websocket
    )

    return {
        "status": "sent",
        "client_id": client_id,
        "message": (
            message[:NOTIFICATION_MESSAGE_STRIP] + "..."
            if len(message) > NOTIFICATION_MESSAGE_STRIP
            else message
        ),
        "timestamp": time.time(),
    }
