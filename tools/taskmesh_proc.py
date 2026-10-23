import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from eci.distributed.operation_store import OperationStore
from eci.distributed.taskmesh import TaskMeshAgent, TaskMeshCoordinator
from eci.network.tcp import FramedTcpTransport


def parse_peers(value: str):
    out = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        host, port = item.rsplit(":", 1)
        out.append((host, int(port)))
    return out


async def run_coordinator():
    node_id = os.environ["NODE_ID"]
    port = int(os.environ["PORT"])
    peers = parse_peers(os.environ.get("PEERS", ""))
    store_path = os.environ["STORE"]
    task_file = os.environ["TASK_FILE"]
    duration = float(os.environ.get("DURATION", "12"))
    t = FramedTcpTransport(node_id=node_id, host="0.0.0.0", port=port)
    await t.start()
    for host, p in peers:
        t.add_peer(f"{host}:{p}", host, p)
    coord = TaskMeshCoordinator(node_id, t, os.path.join(os.path.dirname(store_path), "coord_state.json"),
                               lease_ttl=10.0, heartbeat_timeout=3.0)
    await asyncio.sleep(3)
    coord.add_task("task1", "op1", {"operation_id": "op1", "value": 42})
    async def loop():
        end = time.time() + duration
        while time.time() < end:
            msgs = await t.drain(timeout=0.1)
            for m in msgs:
                payload = m.get("message", m)
                if isinstance(payload, dict):
                    if payload.get("type") in ("task_result", "result_accepted", "result_rejected"):
                        sys.stderr.write(f"COORD RECV {payload.get('type')} from {payload.get('agent_id')} task={payload.get('task_id')} lease={payload.get('lease_id')}\n")
                        sys.stderr.flush()
                    await coord.handle_message(payload)
            await coord._check_leases()
            await coord._assign_pending()
            # write status
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(coord.status(), f)
            await asyncio.sleep(0.5)
    await loop()
    await t.stop()


async def run_agent():
    node_id = os.environ["NODE_ID"]
    port = int(os.environ["PORT"])
    peers = parse_peers(os.environ.get("PEERS", ""))
    store_path = os.environ["STORE"]
    duration = float(os.environ.get("DURATION", "12"))
    sleep_s = float(os.environ.get("HANDLER_SLEEP", "2"))
    t = FramedTcpTransport(node_id=node_id, host="0.0.0.0", port=port)
    await t.start()
    for host, p in peers:
        t.add_peer(f"{host}:{p}", host, p)
    op_store = OperationStore(store_path)

    async def handler(payload):
        sys.stderr.write(f"{node_id} received task {payload.get('task_id')} lease={payload.get('lease_id')} at {time.time():.3f}\n")
        sys.stderr.flush()
        await asyncio.sleep(sleep_s)
        sys.stderr.write(f"{node_id} finished task {payload.get('task_id')} at {time.time():.3f}\n")
        sys.stderr.flush()
        op_id = payload["operation_id"]
        effect_file = os.path.join(os.path.dirname(store_path), f"effect_{op_id}.txt")
        created = op_store.record_if_absent(op_id, {"agent": node_id, "value": payload.get("value")})
        if created and not os.path.exists(effect_file):
            with open(effect_file, "w", encoding="utf-8") as f:
                f.write(node_id)
        stored = op_store.get(op_id)
        return {"operation_id": op_id, "created": created, "stored": stored}

    agent = TaskMeshAgent(node_id, t, handler, os.path.join(os.path.dirname(store_path), f"{node_id}.json"),
                         operation_store=op_store)
    await agent.run(duration=duration)
    await t.stop()


async def run_relay():
    node_id = os.environ["NODE_ID"]
    port = int(os.environ["PORT"])
    peers = parse_peers(os.environ.get("PEERS", ""))
    duration = float(os.environ.get("DURATION", "12"))
    t = FramedTcpTransport(node_id=node_id, host="0.0.0.0", port=port)
    await t.start()
    for host, p in peers:
        t.add_peer(f"{host}:{p}", host, p)
    end = time.time() + duration
    while time.time() < end:
        await t.drain(timeout=0.2)
        await asyncio.sleep(0.2)
    await t.stop()


async def main():
    role = os.environ["ROLE"]
    if role == "coordinator":
        await run_coordinator()
    elif role == "agent":
        await run_agent()
    elif role == "relay":
        await run_relay()
    else:
        raise ValueError(f"unknown ROLE {role}")


if __name__ == "__main__":
    asyncio.run(main())