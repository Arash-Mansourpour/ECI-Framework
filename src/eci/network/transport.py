"""Async in-process transport for real multi-node consensus demos.

``AsyncMemoryChannel`` is a tiny length-bounded asyncio queue mesh:
every node owns an inbox; ``broadcast()`` fans out; ``drain()`` collects
with timeout. It replaces the previous single-loop vote counting with
genuine concurrent tasks so equivocation / latency actually manifest.
No sockets yet — swap with websockets/gRPC without changing callers.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List

__all__ = ["AsyncMemoryChannel", "ChannelStats"]


@dataclass
class ChannelStats:
    sent: int = 0
    delivered: int = 0
    dropped: int = 0


class AsyncMemoryChannel:
    """Bounded async broadcast mesh between named nodes."""

    def __init__(self, capacity: int = 256, latency_s: float = 0.0) -> None:
        self.capacity = capacity
        self.latency_s = latency_s
        self._inboxes: Dict[str, asyncio.Queue] = {}
        self.stats = ChannelStats()

    def register(self, node_id: str) -> None:
        if node_id not in self._inboxes:
            self._inboxes[node_id] = asyncio.Queue(maxsize=self.capacity)

    async def broadcast(self, sender: str, message: Any) -> int:
        self.register(sender)
        delivered = 0
        for nid, q in self._inboxes.items():
            if nid == sender:
                continue
            try:
                q.put_nowait({"from": sender, "message": message, "t": time.time()})
                delivered += 1
            except asyncio.QueueFull:
                self.stats.dropped += 1
        self.stats.sent += delivered
        if self.latency_s > 0:
            await asyncio.sleep(self.latency_s)
        return delivered

    async def drain(self, node_id: str, timeout: float = 0.1) -> List[Any]:
        self.register(node_id)
        q = self._inboxes[node_id]
        out: List[Any] = []
        while True:
            try:
                out.append(await asyncio.wait_for(q.get(), timeout=timeout))
            except asyncio.TimeoutError:
                break
        self.stats.delivered += len(out)
        return out
