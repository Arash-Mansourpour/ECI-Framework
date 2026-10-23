"""Lease-based distributed task mesh over FramedTcpTransport.

This module reuses the existing real TCP transport (length-prefixed JSON,
bounded inbox, retry, dedup, TTL forwarding). It does not create a second
network stack or a second event bus.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from eci.network.tcp import FramedTcpTransport

__all__ = ["TaskRecord", "TaskMeshCoordinator", "TaskMeshAgent"]


@dataclass
class TaskRecord:
    task_id: str
    operation_id: str
    payload: dict[str, Any]
    capability: str = "default"
    status: str = "pending"  # pending | assigned | completed | failed | cancelled
    owner: str | None = None
    lease_id: str | None = None
    fencing_token: int = 0
    deadline: float = 0.0
    lease_expiry: float = 0.0
    attempts: int = 0
    max_attempts: int = 5
    result: Any = None
    error: str | None = None
    reason: str | None = None
    updated_at: float = field(default_factory=time.time)


class TaskMeshCoordinator:
    def __init__(self, node_id: str, transport: FramedTcpTransport,
                 state_path: str | Path, lease_ttl: float = 5.0,
                 heartbeat_timeout: float = 8.0) -> None:
        self.node_id = node_id
        self.transport = transport
        self.state_path = Path(state_path)
        self.lease_ttl = lease_ttl
        self.heartbeat_timeout = heartbeat_timeout
        self.tasks: dict[str, TaskRecord] = {}
        self.agent_heartbeats: dict[str, float] = {}
        self.agent_capabilities: dict[str, set[str]] = {}
        self.agent_capacity: dict[str, int] = {}
        self.agent_load: dict[str, int] = {}
        self._load_state()

    def _load_state(self) -> None:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                for item in data.get("tasks", []):
                    rec = TaskRecord(**item)
                    self.tasks[rec.task_id] = rec
            except Exception:  # noqa: BLE001
                pass

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"tasks": [asdict(t) for t in self.tasks.values()]}
        self.state_path.write_text(json.dumps(payload, default=str), encoding="utf-8")

    def add_task(self, task_id: str, operation_id: str, payload: dict[str, Any],
                 capability: str = "default", deadline: float = 0.0,
                 max_attempts: int = 5) -> TaskRecord:
        rec = TaskRecord(task_id=task_id, operation_id=operation_id, payload=payload,
                         capability=capability, deadline=deadline, max_attempts=max_attempts)
        self.tasks[task_id] = rec
        self._save_state()
        return rec

    def _healthy_agents(self) -> list[str]:
        now = time.time()
        return [aid for aid, ts in self.agent_heartbeats.items()
                if now - ts <= self.heartbeat_timeout]

    def _choose_agent(self, capability: str = "default") -> str | None:
        healthy = self._healthy_agents()
        candidates = []
        for aid in healthy:
            caps = self.agent_capabilities.get(aid, {"default"})
            if capability not in caps and "default" not in caps:
                continue
            load = self.agent_load.get(aid, 0)
            capacity = self.agent_capacity.get(aid, 2)
            if load >= capacity:
                continue
            candidates.append(aid)
        if not candidates:
            return None
        loads = {aid: self.agent_load.get(aid, 0) for aid in candidates}
        return min(candidates, key=lambda aid: loads.get(aid, 0))

    async def _send(self, msg: dict[str, Any]) -> None:
        await self.transport.broadcast(self.node_id, msg)

    async def handle_message(self, msg: dict[str, Any]) -> None:
        payload = msg.get("message", msg)
        if not isinstance(payload, dict):
            payload = msg
        mtype = payload.get("type")
        msg = payload
        if mtype == "heartbeat":
            aid = msg.get("agent_id")
            if isinstance(aid, str):
                self.agent_heartbeats[aid] = time.time()
                caps = msg.get("capabilities")
                if isinstance(caps, list):
                    self.agent_capabilities[aid] = {str(c) for c in caps}
                cap = msg.get("capacity")
                if isinstance(cap, int) and cap > 0:
                    self.agent_capacity[aid] = cap
        elif mtype == "task_result":
            await self._handle_result(msg)

    async def _handle_result(self, msg: dict[str, Any]) -> None:
        task_id = msg.get("task_id")
        rec = self.tasks.get(task_id) if isinstance(task_id, str) else None
        if rec is None:
            return
        lease_id = msg.get("lease_id")
        fencing_token = msg.get("fencing_token")
        if rec.lease_id != lease_id or rec.owner != msg.get("agent_id"):
            await self._send({"type": "result_rejected", "task_id": task_id,
                              "reason": "stale_lease_or_owner"})
            return
        if fencing_token is not None and rec.fencing_token != fencing_token:
            await self._send({"type": "result_rejected", "task_id": task_id,
                              "reason": "stale_fencing_token"})
            return
        if time.time() > rec.lease_expiry and rec.status != "completed":
            await self._send({"type": "result_rejected", "task_id": task_id,
                              "reason": "lease_expired"})
            return
        rec.status = "completed" if msg.get("ok", True) else "failed"
        rec.result = msg.get("result")
        rec.error = msg.get("error")
        rec.reason = "result_accepted"
        rec.updated_at = time.time()
        self._save_state()
        await self._send({"type": "result_accepted", "task_id": task_id,
                          "agent_id": rec.owner})

    async def _assign_pending(self) -> None:
        for rec in list(self.tasks.values()):
            if rec.status in ("completed", "failed", "cancelled"):
                continue
            if rec.attempts >= rec.max_attempts:
                rec.status = "failed"
                rec.reason = "max_attempts_exceeded"
                self._save_state()
                continue
            if rec.deadline and time.time() > rec.deadline:
                rec.status = "failed"
                rec.reason = "deadline_exceeded"
                self._save_state()
                continue
            if rec.status == "assigned" and time.time() <= rec.lease_expiry:
                continue
            if rec.status == "assigned":
                rec.reason = "lease_expired_reassign"
            agent = self._choose_agent(rec.capability)
            if agent is None:
                rec.reason = "no_capable_healthy_agent"
                continue
            rec.status = "assigned"
            rec.owner = agent
            rec.lease_id = str(uuid.uuid4())
            rec.fencing_token += 1
            rec.lease_expiry = time.time() + self.lease_ttl
            rec.attempts += 1
            rec.reason = "assigned"
            rec.updated_at = time.time()
            self.agent_load[agent] = self.agent_load.get(agent, 0) + 1
            self._save_state()
            await self._send({
                "type": "task_assign",
                "task_id": rec.task_id,
                "operation_id": rec.operation_id,
                "capability": rec.capability,
                "payload": rec.payload,
                "lease_id": rec.lease_id,
                "fencing_token": rec.fencing_token,
                "lease_expiry": rec.lease_expiry,
                "attempt": rec.attempts,
            })

    async def _check_leases(self) -> None:
        now = time.time()
        for rec in self.tasks.values():
            if rec.status == "assigned" and now > rec.lease_expiry:
                rec.status = "pending"
                rec.reason = "lease_expired"
                rec.updated_at = now
                self._save_state()

    async def run(self, duration: float | None = None) -> None:
        t0 = time.time()
        while duration is None or time.time() - t0 < duration:
            # Drain inbox
            msgs = await self.transport.drain(timeout=0.1)
            for m in msgs:
                await self.handle_message(m)
            await self._check_leases()
            await self._assign_pending()
            await asyncio.sleep(0.2)

    def status(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "agents": {aid: time.time() - ts for aid, ts in self.agent_heartbeats.items()},
            "tasks": {tid: {
                "status": t.status,
                "owner": t.owner,
                "lease_id": t.lease_id,
                "attempts": t.attempts,
                "reason": t.reason,
                "result": t.result,
            } for tid, t in self.tasks.items()},
        }


class TaskMeshAgent:
    def __init__(self, node_id: str, transport: FramedTcpTransport,
                 handler: Callable[[dict[str, Any]], Any],
                 result_store: str | Path,
                 operation_store: Any = None) -> None:
        self.node_id = node_id
        self.transport = transport
        self.handler = handler
        self.result_store = Path(result_store)
        self.operation_store = operation_store
        self.completed: dict[str, Any] = {}
        self._load_results()

    def _load_results(self) -> None:
        if self.result_store.exists():
            try:
                self.completed = json.loads(self.result_store.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                self.completed = {}

    def _save_results(self) -> None:
        self.result_store.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.result_store.with_suffix(self.result_store.suffix + ".tmp")
        tmp.write_text(json.dumps(self.completed, default=str), encoding="utf-8")
        os.replace(tmp, self.result_store)

    async def _heartbeat(self) -> None:
        while True:
            await self.transport.broadcast(self.node_id, {
                "type": "heartbeat", "agent_id": self.node_id,
                "capabilities": ["default"], "capacity": 2,
            })
            await asyncio.sleep(1.0)

    async def _execute_task(self, msg: dict[str, Any]) -> None:
        task_id = msg.get("task_id")
        operation_id = msg.get("operation_id")
        lease_id = msg.get("lease_id")
        fencing_token = msg.get("fencing_token")
        if not isinstance(task_id, str) or not isinstance(operation_id, str) or not isinstance(lease_id, str):
            return
        # Idempotent: if already completed, resubmit cached result.
        if operation_id in self.completed:
            await self.transport.broadcast(self.node_id, {
                "type": "task_result",
                "task_id": task_id,
                "operation_id": operation_id,
                "lease_id": lease_id,
                "fencing_token": fencing_token,
                "agent_id": self.node_id,
                "ok": True,
                "result": self.completed[operation_id],
            })
            return
        try:
            result = self.handler(msg.get("payload", {}))
            if asyncio.iscoroutine(result):
                result = await result
            if self.operation_store is not None:
                token = fencing_token if isinstance(fencing_token, int) else None
                created = self.operation_store.record_if_absent(operation_id, result, token)
                stored = self.operation_store.get(operation_id)
                if stored is not None and stored.get("result") is not None:
                    result = stored["result"]
                if not created:
                    # Another agent/process already recorded this operation.
                    pass
            self.completed[operation_id] = result
            self._save_results()
            await self.transport.broadcast(self.node_id, {
                "type": "task_result",
                "task_id": task_id,
                "operation_id": operation_id,
                "lease_id": lease_id,
                "fencing_token": fencing_token,
                "agent_id": self.node_id,
                "ok": True,
                "result": result,
            })
        except Exception as exc:  # noqa: BLE001
            await self.transport.broadcast(self.node_id, {
                "type": "task_result",
                "task_id": task_id,
                "operation_id": operation_id,
                "lease_id": lease_id,
                "fencing_token": fencing_token,
                "agent_id": self.node_id,
                "ok": False,
                "error": repr(exc),
            })

    async def run(self, duration: float | None = None) -> None:
        hb = asyncio.create_task(self._heartbeat())
        t0 = time.time()
        try:
            while duration is None or time.time() - t0 < duration:
                msgs = await self.transport.drain(timeout=0.1)
                for m in msgs:
                    payload = m.get("message", m)
                    if isinstance(payload, dict) and payload.get("type") == "task_assign":
                        await self._execute_task(payload)
                await asyncio.sleep(0.1)
        finally:
            hb.cancel()
            try:
                await hb
            except asyncio.CancelledError:
                pass