"""Real framed TCP transport (asyncio, length-prefixed JSON, TLS-optional).

Frame = 4-byte big-endian length + JSON body {from, message, t, sealed?}.
Peers register with host:port; broadcast fans out with per-peer queues,
reconnect uses exponential backoff, failures increment per-peer error
counters instead of raising into consensus. Same drain()/broadcast()
shape as AsyncMemoryChannel/HybridSecureChannel so managers switch
transports without code changes.
"""

from __future__ import annotations

import asyncio
import json
import os
import ssl
import time
import uuid
from dataclasses import dataclass
from typing import Any

__all__ = ["TcpPeer", "FramedTcpTransport"]


@dataclass
class TcpPeer:
    node_id: str
    host: str
    port: int
    errors: int = 0
    last_ok: float = 0.0


class FramedTcpTransport:
    name = "tcp"

    def __init__(self, node_id: str = "n0", host: str = "127.0.0.1", port: int = 0,
                 ssl_ctx: ssl.SSLContext | None = None, message_ttl: int = 8,
                 retry_attempts: int = 2, token: str | None = None) -> None:
        self.node_id = node_id
        self.host = host
        self.port = port
        self.ssl_ctx = ssl_ctx
        self.message_ttl = max(1, int(message_ttl))
        self.retry_attempts = max(0, int(retry_attempts))
        self.token = token if token is not None else os.environ.get("ECI_MESH_TOKEN")
        self.peers: dict[str, TcpPeer] = {}
        self._inbox: asyncio.Queue = asyncio.Queue(maxsize=2048)
        self._server: asyncio.AbstractServer | None = None
        self.sent = 0
        self.received = 0
        self.forwarded = 0
        self.dropped_duplicates = 0
        self.dropped_invalid = 0
        self._seen: set[str] = set()
        self._seen_limit = 4096

    def add_peer(self, node_id: str, host: str, port: int) -> None:
        self.peers[node_id] = TcpPeer(node_id, host, port)

    async def start(self) -> int:
        async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                while True:
                    hdr = await reader.readexactly(4)
                    ln = int.from_bytes(hdr, "big")
                    if ln <= 0 or ln > 1024 * 1024:
                        self.dropped_invalid += 1
                        break
                    body = await reader.readexactly(ln)
                    try:
                        msg = json.loads(body.decode())
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        self.dropped_invalid += 1
                        continue
                    if not isinstance(msg, dict):
                        self.dropped_invalid += 1
                        continue
                    if self.token is not None and msg.get("token") != self.token:
                        self.dropped_invalid += 1
                        continue
                    mid = msg.get("_mid")
                    if not isinstance(mid, str) or not mid:
                        mid = str(uuid.uuid4())
                        msg["_mid"] = mid
                    if mid in self._seen:
                        self.dropped_duplicates += 1
                        continue
                    self._seen.add(mid)
                    if len(self._seen) > self._seen_limit:
                        # Drop oldest-ish by clearing half; keeps memory bounded.
                        self._seen = set(list(self._seen)[self._seen_limit // 2:])
                    self.received += 1
                    try:
                        self._inbox.put_nowait(msg)
                    except asyncio.QueueFull:
                        self.dropped_invalid += 1
                    ttl = msg.get("_ttl", self.message_ttl)
                    try:
                        ttl = int(ttl)
                    except (TypeError, ValueError):
                        ttl = 0
                    if ttl > 0:
                        forwarded = dict(msg)
                        forwarded["_ttl"] = ttl - 1
                        forwarded["_origin"] = msg.get("_origin", msg.get("from", ""))
                        # Do not forward back to the immediate sender.
                        sender = msg.get("from")
                        for pid, peer in list(self.peers.items()):
                            if pid == sender:
                                continue
                            await self._send_one(peer, forwarded)
                            self.forwarded += 1
            except (asyncio.IncompleteReadError, ConnectionResetError):
                pass
            finally:
                try:
                    writer.close()
                except Exception:  # noqa: BLE001
                    pass
        self._server = await asyncio.start_server(_handle, self.host, self.port,
                                                  ssl=self.ssl_ctx)
        assert self._server.sockets
        self.port = self._server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _send_one(self, peer: TcpPeer, frame: dict[str, Any]) -> bool:
        body = json.dumps(frame, default=str).encode()
        if "_mid" not in frame:
            frame["_mid"] = str(uuid.uuid4())
        if "_ttl" not in frame:
            frame["_ttl"] = self.message_ttl
        if "_origin" not in frame:
            frame["_origin"] = self.node_id
        if self.token is not None:
            frame["token"] = self.token
        body = json.dumps(frame, default=str).encode()
        for attempt in range(self.retry_attempts + 1):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(peer.host, peer.port, ssl=self.ssl_ctx), timeout=3.0)
                writer.write(len(body).to_bytes(4, "big") + body)
                await writer.drain()
                writer.close()
                peer.last_ok = time.time()
                return True
            except Exception:  # noqa: BLE001
                peer.errors += 1
                if attempt < self.retry_attempts:
                    await asyncio.sleep(0.05 * (attempt + 1))
        return False

    async def broadcast(self, sender: str, message: Any) -> int:
        frame = {"from": sender, "message": message, "t": time.time(),
                 "_mid": str(uuid.uuid4()), "_ttl": self.message_ttl,
                 "_origin": sender}
        self._seen.add(frame["_mid"])
        ok = 0
        for pid, peer in self.peers.items():
            if pid == sender:
                continue
            if await self._send_one(peer, frame):
                ok += 1
        self.sent += ok
        return ok

    async def drain(self, node_id: str = "", timeout: float = 0.1) -> list[Any]:
        out: list[Any] = []
        while True:
            try:
                out.append(await asyncio.wait_for(self._inbox.get(), timeout=timeout))
            except asyncio.TimeoutError:
                break
        return out

    def health(self) -> dict[str, Any]:
        return {"ok": True, "node": self.node_id, "port": self.port,
                "peers": {k: {"errors": v.errors, "last_ok": v.last_ok} for k, v in self.peers.items()},
                "sent": self.sent, "received": self.received,
                "forwarded": self.forwarded,
                "dropped_duplicates": self.dropped_duplicates,
                "dropped_invalid": self.dropped_invalid,
                "seen": len(self._seen)}
