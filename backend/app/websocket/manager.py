"""
manager.py

Minimal in-process WebSocket connection manager, keyed by scan_id.

For a single Oracle Cloud VM deployment (one FastAPI process) an in-memory
dict is sufficient. If Vulnara ever scales to multiple backend replicas,
this would need to move to a pub/sub backend (e.g. Redis) so a client
connected to replica A can receive events published by a scan running on
replica B — flagging that here as a known scaling limit, not solving it
now since the locked stack is a single always-on VM.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class ScanConnectionManager:
    def __init__(self) -> None:
        # scan_id -> set of active websocket connections
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, scan_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(scan_id, set()).add(websocket)

    async def disconnect(self, scan_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(scan_id)
            if conns and websocket in conns:
                conns.remove(websocket)
            if conns is not None and not conns:
                self._connections.pop(scan_id, None)

    async def broadcast(self, scan_id: str, event: str, data: dict[str, Any]) -> None:
        """
        Sends an envelope-shaped message to every socket currently
        subscribed to this scan_id. Matches the message envelope defined
        in the API contract: { event, scan_id, timestamp, data }.
        """
        message = {
            "event": event,
            "scan_id": scan_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        async with self._lock:
            conns = list(self._connections.get(scan_id, ()))

        # Send outside the lock so a slow/dead client can't block others.
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                conns_set = self._connections.get(scan_id)
                if conns_set:
                    for ws in stale:
                        conns_set.discard(ws)


# Single shared instance imported by both the WebSocket route and the
# background scan task.
scan_connection_manager = ScanConnectionManager()
