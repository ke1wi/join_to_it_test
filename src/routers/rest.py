from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from src.connection_manager import connection_manager
from src.schemas import BroadcastRequest, PersonalMessageRequest

router = APIRouter(tags=["REST"])


@router.get("/")
async def root():
    logger.info("Health check")
    return {
        "status": "ok",
        "service": "WebSocket Notification Server",
        "websocket_endpoint": "/ws",
    }


@router.get("/status")
async def get_status():
    manager = connection_manager
    active = await manager.count()

    return {
        "status": "running",
        "active_connections": active,
        "accepting_new_connections": manager.accepting_connections,
        "clients": await manager.get_active_clients(),
    }


@router.post("/notify/broadcast")
async def broadcast_message(payload: BroadcastRequest):
    manager = connection_manager

    if not payload.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    logger.info("Broadcast request", message=payload.message)

    await manager.broadcast(payload.message)

    return {
        "status": "sent",
        "target": "all",
        "active_connections": await manager.count(),
    }


@router.post("/notify/{client_id}")
async def send_to_client(client_id: str, payload: PersonalMessageRequest):
    manager = connection_manager

    ws = await manager.get_websocket(client_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Client not connected")

    logger.info("Sending personal message", client_id=client_id)

    await manager.send_personal_message(payload.message, ws)

    return {
        "status": "sent",
        "client_id": client_id,
    }
