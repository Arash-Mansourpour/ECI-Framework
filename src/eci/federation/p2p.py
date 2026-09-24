"""Federation P2P transport v8 (ADR-003).

Transport protocol + InMemory (deterministic) + TCP (asyncio localhost)
+ GossipNode with 2/3 quorum + PartitionChaos for split-brain tests.

No external dependency. Deterministic unless TCPTransport is used.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class Transport(Protocol):
    name: str

    def send(self, peer: str, envelope: dict[str, Any]) -> None: ...
    def broadcast(self, envelope: dict[str, Any]) -> None: ...
    def register(self, node_id: str, handler: Callable[[dict[str, Any]], None]) -> None: ...


class InMemoryTransport:
    """Deterministic in-process mesh. Supports partition simulation."""

    name = "memory"

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[dict[str, Any]], None]] = {}
        self.partitions: set[frozenset[str]] = set()  # blocked pairs
        self.delivered = 0
        self.dropped = 0

    def register(self, node_id: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self.handlers[node_id] = handler

    def _blocked(self, a: str, b: str) -> bool:
        for part in self.partitions:
            # partition = set of nodes isolated from the rest
            if (a in part) != (b in part):
                return True
        return False

    def partition(self, isolated: set[str]) -> None:
        self.partitions.add(frozenset(isolated))

    def heal(self) -> None:
        self.partitions.clear()

    def send(self, peer: str, envelope: dict[str, Any]) -> None:
        sender = str(envelope.get("from", ""))
        if self._blocked(sender, peer):
            self.dropped += 1
            return
        h = self.handlers.get(peer)
        if h is not None:
            self.delivered += 1
            h(dict(envelope))

    def broadcast(self, envelope: dict[str, Any]) -> None:
        for peer in list(self.handlers):
            if peer != envelope.get("from"):
                self.send(peer, envelope)

    def health(self) -> dict[str, Any]:
        return {"backend": self.name, "peers": len(self.handlers),
                "delivered": self.delivered, "dropped": self.dropped,
                "partitioned": bool(self.partitions)}


class TCPTransport:
    """Asyncio TCP mesh on localhost. Each node listens + dials peers.

    Frame: 4-byte big-endian length + JSON. Fire-and-forget send from
    sync contexts via a private event loop-safe queue; for tests prefer
    InMemoryTransport (deterministic).
    """

    name = "tcp"

    def __init__(self, node_id: str, port: int) -> None:
        self.node_id = node_id
        self.port = port
        self.peers: dict[str, tuple[str, int]] = {}
        self._handler: Callable[[dict[str, Any]], None] | None = None
        self._server: asyncio.AbstractServer | None = None
        self.sent = 0

    def register(self, node_id: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self._handler = handler

    def add_peer(self, peer_id: str, host: str, port: int) -> None:
        self.peers[peer_id] = (host, port)

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._on_conn, "127.0.0.1", self.port)

    async def _on_conn(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            hdr = await reader.readexactly(4)
            n = int.from_bytes(hdr, "big")
            body = await reader.readexactly(n)
            env = json.loads(body.decode("utf-8"))
            if self._handler is not None:
                self._handler(env)
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass

    async def _send_async(self, host: str, port: int, envelope: dict[str, Any]) -> None:
        body = json.dumps(envelope, default=str).encode("utf-8")
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(len(body).to_bytes(4, "big") + body)
        await writer.drain()
        writer.close()
        self.sent += 1

    def send(self, peer: str, envelope: dict[str, Any]) -> None:
        if peer not in self.peers:
            return
        host, port = self.peers[peer]
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_async(host, port, envelope))
        except RuntimeError:
            asyncio.run(self._send_async(host, port, envelope))

    def broadcast(self, envelope: dict[str, Any]) -> None:
        for peer in list(self.peers):
            self.send(peer, envelope)

    def health(self) -> dict[str, Any]:
        return {"backend": self.name, "node": self.node_id, "port": self.port,
                "peers": len(self.peers), "sent": self.sent}


@dataclass
class GossipNode:
    """PBFT-style gossip node: proposes, votes, commits at 2/3 quorum."""

    node_id: str
    transport: Any
    peers: list[str] = field(default_factory=list)
    view: int = 0
    sequence: int = 0
    prepared: dict[str, set[str]] = field(default_factory=dict)
    committed: dict[str, Any] = field(default_factory=dict)
    seen: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.transport.register(self.node_id, self._on_envelope)

    def _digest(self, payload: Any) -> str:
        canon = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(canon.encode()).hexdigest()[:16]

    def propose(self, payload: Any) -> str:
        self.sequence += 1
        digest = self._digest(payload)
        env = {"kind": "pre-prepare", "from": self.node_id, "view": self.view,
               "seq": self.sequence, "digest": digest, "payload": payload,
               "ts": time.time()}
        self.seen.append(env)
        self.transport.broadcast(env)
        # self-vote
        self._on_envelope({"kind": "prepare", "from": self.node_id, "view": self.view,
                           "seq": self.sequence, "digest": digest})
        return digest

    def _on_envelope(self, env: dict[str, Any]) -> None:
        kind = env.get("kind")
        if kind == "pre-prepare":
            # echo prepare
            vote = {"kind": "prepare", "from": self.node_id, "view": env.get("view"),
                    "seq": env.get("seq"), "digest": env.get("digest")}
            self.seen.append(env)
            self.transport.broadcast(vote)
            self._on_envelope(vote)
        elif kind == "prepare":
            key = f"{env.get('view')}:{env.get('seq')}:{env.get('digest')}"
            self.prepared.setdefault(key, set()).add(str(env.get("from")))
            if self._quorum_reached(key):
                self.committed[key] = {"digest": env.get("digest"), "seq": env.get("seq"),
                                       "votes": sorted(self.prepared[key])}

    def _quorum_reached(self, key: str) -> bool:
        n = len(self.peers) + 1
        need = (2 * n) // 3 + 1 if n % 3 == 0 else int(2 * n / 3) + 1
        # standard PBFT: 2f+1 where f=(n-1)//3
        f = (n - 1) // 3
        need = 2 * f + 1
        return len(self.prepared.get(key, set())) >= need

    def commit_count(self) -> int:
        return len(self.committed)

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "view": self.view, "seq": self.sequence,
                "committed": len(self.committed), "peers": len(self.peers)}


def build_mesh(n: int) -> tuple[list[GossipNode], InMemoryTransport]:
    """Build a deterministic n-node full mesh (for tests/demos)."""
    t = InMemoryTransport()
    nodes = [GossipNode(node_id=f"node-{i}", transport=t) for i in range(n)]
    ids = [nd.node_id for nd in nodes]
    for nd in nodes:
        nd.peers = [i for i in ids if i != nd.node_id]
    return nodes, t


def run_partition_test(n: int = 4, proposals: int = 2) -> dict[str, Any]:
    """Jepsen-style: heal -> propose (commit) -> partition -> propose (stall) -> heal."""
    nodes, transport = build_mesh(n)
    primary = nodes[0]
    for i in range(proposals):
        primary.propose({"op": f"healed-{i}"})
    committed_healed = sum(nd.commit_count() for nd in nodes)
    # isolate primary
    transport.partition({primary.node_id})
    for i in range(proposals):
        primary.propose({"op": f"partitioned-{i}"})
    committed_partitioned = sum(nd.commit_count() for nd in nodes)
    transport.heal()
    return {"n": n, "committed_healed": committed_healed,
            "committed_partitioned": committed_partitioned,
            "partition_stalled": committed_partitioned == committed_healed,
            "delivered": transport.delivered, "dropped": transport.dropped}
