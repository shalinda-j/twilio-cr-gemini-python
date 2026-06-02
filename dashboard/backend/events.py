# events.py - in-memory WebSocket hub for live dashboard updates, scoped per company.
import asyncio
from typing import Dict, Set

from fastapi import WebSocket


class LiveHub:
    def __init__(self):
        self._conns: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, company_id: int, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._conns.setdefault(company_id, set()).add(ws)

    async def disconnect(self, company_id: int, ws: WebSocket):
        async with self._lock:
            conns = self._conns.get(company_id)
            if conns and ws in conns:
                conns.discard(ws)

    async def broadcast(self, company_id: int, message: dict):
        """Push a JSON event to every open dashboard for this company."""
        async with self._lock:
            conns = list(self._conns.get(company_id, set()))
        dead = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._conns.get(company_id, set()).discard(ws)


hub = LiveHub()
