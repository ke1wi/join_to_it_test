import asyncio
import time
from contextlib import suppress
from typing import Any, Dict, Set

from fastapi import HTTPException, WebSocket
from loguru import logger

from src.config import CLEANUP_INTERVAL


class ConnectionManager:
    """
    Manages WebSocket connections with ping/pong support for health checking.
    """

    def __init__(self) -> None:
        self._connections: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.accepting_connections = True
        self._cleanup_task = None

    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """Accepts a new connection and assigns a unique ID"""
        if not self.accepting_connections:
            await websocket.close(
                code=1012, reason="Server is restarting / shutting down"
            )
            raise HTTPException(status_code=503, detail="Server is shutting down")

        await websocket.accept()

        if client_id is None:
            client_id = f"client_{len(self._connections)}_{int(time.time())}"

        async with self._lock:
            self._connections[websocket] = {
                "id": client_id,
                "connected_at": time.time(),
                "last_active": time.time(),
            }

        logger.info(
            f"WebSocket connected: {client_id}. Active connections: {len(self._connections)}"
        )
        return client_id

    async def disconnect(self, websocket: WebSocket) -> None:
        """Disconnects a client"""
        client_info = None
        async with self._lock:
            if websocket in self._connections:
                client_info = self._connections.pop(websocket)

        if client_info:
            logger.info(
                f"WebSocket disconnected: {client_info['id']}. Active connections: {len(self._connections)}"
            )

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Sends a message to a specific client"""
        try:
            await websocket.send_text(message)
            async with self._lock:
                if websocket in self._connections:
                    self._connections[websocket]["last_active"] = time.time()
        except Exception as e:
            logger.warning(f"Failed to send message to client: {e}")
            await self.disconnect(websocket)

    async def broadcast(self, message: str, exclude: Set[WebSocket] = None) -> None:
        """
        Broadcasts a message to all connected clients.
        """
        if exclude is None:
            exclude = set()

        async with self._lock:
            connections = list(self._connections.keys())

        disconnected = []
        for ws in connections:
            if ws in exclude:
                continue
            try:
                await ws.send_text(message)
                async with self._lock:
                    if ws in self._connections:
                        self._connections[ws]["last_active"] = time.time()
            except Exception:
                disconnected.append(ws)
                logger.warning("Failed to broadcast to a client")

        for ws in disconnected:
            await self.disconnect(ws)

    async def close_all(
        self, code: int = 1001, reason: str = "Server shutting down"
    ) -> None:
        """Closes all connections"""
        async with self._lock:
            connections = list(self._connections.keys())

        for ws in connections:
            with suppress(Exception):
                await ws.close(code=code, reason=reason)
            await self.disconnect(ws)

        logger.info(f"Closed all WebSocket connections: {len(connections)}")

    async def count(self) -> int:
        """Returns the number of active connections"""
        async with self._lock:
            return len(self._connections)

    async def get_active_clients(self) -> Dict[str, Dict[str, Any]]:
        """Returns information about active clients"""
        async with self._lock:
            return {
                info["id"]: {
                    "connected_at": info["connected_at"],
                    "last_active": info["last_active"],
                    "connection_duration": time.time() - info["connected_at"],
                }
                for ws, info in self._connections.items()
            }

    async def start_connection_cleanup(self, interval: int = CLEANUP_INTERVAL) -> None:
        """Starts a background task to clean up dead connections"""

        async def cleanup():
            while True:
                await asyncio.sleep(interval)
                await self._check_connections()

        self._cleanup_task = asyncio.create_task(cleanup())

    async def stop_connection_cleanup(self) -> None:
        """Stops the cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._cleanup_task

    async def _check_connections(self) -> None:
        """Checks and removes dead connections"""
        async with self._lock:
            connections = list(self._connections.items())

        for ws, info in connections:
            try:
                await ws.send_text("ping")
            except Exception:
                logger.warning(f"Connection {info['id']} seems dead, removing")
                await self.disconnect(ws)


connection_manager = ConnectionManager()
