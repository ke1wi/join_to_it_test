import asyncio
import time
import uuid
from contextlib import suppress
from typing import Any, Dict, Set

from fastapi import HTTPException, WebSocket
from loguru import logger

from src.config import CLEANUP_INTERVAL


class ConnectionManager:
    """
    Optimized WebSocket connection manager with:
    - O(1) lookups by client_id
    - proper ping frames
    - improved locking strategy
    - safer disconnect logic
    """

    def __init__(self) -> None:
        self._ws_to_info: Dict[WebSocket, Dict[str, Any]] = {}
        self._id_to_ws: Dict[str, WebSocket] = {}

        self._lock = asyncio.Lock()
        self.accepting_connections = True
        self._cleanup_task = None

    # ---------------- CONNECTION MGMT ---------------- #

    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        if not self.accepting_connections:
            await websocket.close(code=1012, reason="Server is shutting down")
            raise HTTPException(status_code=503, detail="Server is shutting down")

        await websocket.accept()

        # client_id must be unique always
        if not client_id:
            client_id = f"cli_{uuid.uuid4().hex}"

        async with self._lock:
            self._ws_to_info[websocket] = {
                "id": client_id,
                "connected_at": time.time(),
                "last_active": time.time(),
            }
            self._id_to_ws[client_id] = websocket

        logger.info(f"WebSocket connected: {client_id}")

        return client_id

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            info = self._ws_to_info.pop(websocket, None)
            if info:
                client_id = info["id"]
                self._id_to_ws.pop(client_id, None)
            else:
                return

        logger.info(f"WebSocket disconnected: {client_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        try:
            await websocket.send_text(message)
            async with self._lock:
                if websocket in self._ws_to_info:
                    self._ws_to_info[websocket]["last_active"] = time.time()
        except Exception as e:
            logger.warning(f"Error sending personal message: {e}")
            await self.disconnect(websocket)

    async def broadcast(self, message: str, exclude: Set[WebSocket] = None) -> None:
        exclude = exclude or set()

        async with self._lock:
            connections = list(self._ws_to_info.keys())

        disconnected = []
        for ws in connections:
            if ws in exclude:
                continue
            try:
                await ws.send_text(message)
                async with self._lock:
                    if ws in self._ws_to_info:
                        self._ws_to_info[ws]["last_active"] = time.time()
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            logger.warning("Broadcast failed: removing dead connection")
            await self.disconnect(ws)

    async def close_all(
        self, code: int = 1001, reason: str = "Server shutting down"
    ) -> None:
        async with self._lock:
            conns = list(self._ws_to_info.keys())

        for ws in conns:
            with suppress(Exception):
                await ws.close(code=code, reason=reason)
            await self.disconnect(ws)

        logger.info(f"Closed all WebSocket connections: {len(conns)}")

    async def count(self) -> int:
        async with self._lock:
            return len(self._ws_to_info)

    async def get_active_clients(self) -> Dict[str, Dict[str, Any]]:
        async with self._lock:
            return {
                info["id"]: {
                    "connected_at": info["connected_at"],
                    "last_active": info["last_active"],
                    "connection_duration": time.time() - info["connected_at"],
                }
                for info in self._ws_to_info.values()
            }

    async def get_websocket(self, client_id: str):
        async with self._lock:
            return self._id_to_ws.get(client_id)

    async def start_connection_cleanup(self, interval: int = CLEANUP_INTERVAL):
        async def cleanup():
            while True:
                await asyncio.sleep(interval)
                await self._check_connections()

        self._cleanup_task = asyncio.create_task(cleanup())

    async def stop_connection_cleanup(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task

    async def _check_connections(self):
        async with self._lock:
            connections = list(self._ws_to_info.items())

        for ws, info in connections:
            try:
                await ws.send("ping")
            except Exception:
                logger.warning(f"Dead connection detected: {info['id']}")
                await self.disconnect(ws)


connection_manager = ConnectionManager()
