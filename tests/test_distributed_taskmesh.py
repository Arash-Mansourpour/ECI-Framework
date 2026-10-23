import asyncio
import os
import tempfile

import pytest

from eci.distributed.taskmesh import TaskMeshAgent, TaskMeshCoordinator
from eci.network.tcp import FramedTcpTransport


@pytest.mark.asyncio
async def test_taskmesh_crash_recovery_and_stale_result():
    tmp = tempfile.mkdtemp()
    c = FramedTcpTransport(node_id="coord", host="127.0.0.1", port=0)
    a1 = FramedTcpTransport(node_id="agent1", host="127.0.0.1", port=0)
    a2 = FramedTcpTransport(node_id="agent2", host="127.0.0.1", port=0)
    r1 = FramedTcpTransport(node_id="relay1", host="127.0.0.1", port=0)
    r2 = FramedTcpTransport(node_id="relay2", host="127.0.0.1", port=0)
    transports = [c, a1, a2, r1, r2]
    for t in transports:
        await t.start()
    ports = {t.node_id: t.port for t in transports}

    def link(x, y):
        x.add_peer(y.node_id, "127.0.0.1", ports[y.node_id])
        y.add_peer(x.node_id, "127.0.0.1", ports[x.node_id])

    for r in (r1, r2):
        link(c, r)
    for a in (a1, a2):
        for r in (r1, r2):
            link(a, r)
    await asyncio.sleep(0.2)

    async def handler(payload):
        await asyncio.sleep(0.5)
        op = payload["operation_id"]
        out = os.path.join(payload["_tmp"], f"effect_{op}.txt")
        if not os.path.exists(out):
            with open(out, "w") as f:
                f.write("done")
        return {"file": out}

    coord = TaskMeshCoordinator("coord", c, os.path.join(tmp, "state.json"), lease_ttl=1.0, heartbeat_timeout=2.0)
    coord.add_task("task1", "op1", {"operation_id": "op1", "_tmp": tmp})
    agents = {
        "agent1": TaskMeshAgent("agent1", a1, handler, os.path.join(tmp, "agent1.json")),
        "agent2": TaskMeshAgent("agent2", a2, handler, os.path.join(tmp, "agent2.json")),
    }
    agent_tasks = [asyncio.create_task(ag.run(duration=8)) for ag in agents.values()]
    coord_task = asyncio.create_task(coord.run(duration=8))
    await asyncio.sleep(0.5)
    agent_tasks[0].cancel()
    try:
        await agent_tasks[0]
    except asyncio.CancelledError:
        pass
    await asyncio.sleep(3)
    status = coord.status()["tasks"]["task1"]
    assert status["status"] == "completed"
    assert os.path.exists(os.path.join(tmp, "effect_op1.txt"))
    # stale result rejected
    rec = coord.tasks["task1"]
    await coord.handle_message({"message": {"type": "task_result", "task_id": "task1", "operation_id": "op1",
                                           "lease_id": "bad", "agent_id": "agent1", "ok": True, "result": "x"}})
    assert coord.tasks["task1"].status == "completed"
    for t in agent_tasks[1:]:
        t.cancel()
    coord_task.cancel()
    try:
        await coord_task
    except asyncio.CancelledError:
        pass
    for t in transports:
        await t.stop()