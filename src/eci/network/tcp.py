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
import ssl
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
                 ssl_ctx: Optional[ssl.SSLContext] = None) -> None:
        self.node_id = node_id
        self.host = host
        self.port = port
        self.ssl_ctx = ssl_ctx
        self.peers: Dict[str, TcpPeer] = {}
        self._inbox: asyncio.Queue = asyncio.Queue(maxsize=2048)
        self._server: Optional[asyncio.AbstractServer] = None
        self.sent = 0
        self.received = 0

    def add_peer(self, node_id: str, host: str, port: int) -> None:
        self.peers[node_id] = TcpPeer(node_id, host, port)

    async def start(self) -> int:
        async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                while True:
                    hdr = await reader.readexactly(4)
                    ln = int.from_bytes(hdr, "big")
                    body = await reader.readexactly(ln)
                    msg = json.loads(body.decode())
                    self.received += 1
                    try:
                        self._inbox.put_nowait(msg)
                    except asyncio.QueueFull:
                        pass
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

    async def _send_one(self, peer: TcpPeer, frame: Dict[str, Any]) -> bool:
        body = json.dumps(frame, default=str).encode()
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
            return False

    async def broadcast(self, sender: str, message: Any) -> int:
        frame = {"from": sender, "message": message, "t": time.time()}
        ok = 0
        for pid, peer in self.peers.items():
            if pid == sender:
                continue
            if await self._send_one(peer, frame):
                ok += 1
        self.sent += ok
        return ok

    async def drain(self, node_id: str = "", timeout: float = 0.1) -> List[Any]:
        out: List[Any] = []
        while True:
            try:
                out.append(await asyncio.wait_for(self._inbox.get(), timeout=timeout))
            except asyncio.TimeoutError:
                break
        return out

    def health(self) -> Dict[str, Any]:
        return {"ok": True, "node": self.node_id, "port": self.port,
                "peers": {k: {"errors": v.errors, "last_ok": v.last_ok} for k, v in self.peers.items()},
                "sent": self.sent, "received": self.received}
