import json
import os
import subprocess
import sys
import tempfile
import time

import pytest


def _env(role, node_id, port, peers, **extra):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..", "src")
    env["ROLE"] = role
    env["NODE_ID"] = node_id
    env["PORT"] = str(port)
    env["PEERS"] = peers
    env.update({k: str(v) for k, v in extra.items()})
    return env


@pytest.mark.timeout(180)
def test_multiproc_crash_recovery():
    tmp = tempfile.mkdtemp()
    store = os.path.join(tmp, "ops.db")
    task_file = os.path.join(tmp, "status.json")
    base = os.path.join(os.path.dirname(__file__), "..")
    script = os.path.join(base, "tools", "taskmesh_proc.py")
    procs = []
    try:
        procs.append(subprocess.Popen([sys.executable, script], env=_env(
            "coordinator", "coord", 29200, "127.0.0.1:29201,127.0.0.1:29202",
            STORE=store, TASK_FILE=task_file, DURATION=30)))
        procs.append(subprocess.Popen([sys.executable, script], env=_env(
            "relay", "relay1", 29201, "127.0.0.1:29200,127.0.0.1:29203,127.0.0.1:29204,127.0.0.1:29205",
            DURATION=30)))
        procs.append(subprocess.Popen([sys.executable, script], env=_env(
            "relay", "relay2", 29202, "127.0.0.1:29200,127.0.0.1:29203,127.0.0.1:29204,127.0.0.1:29205",
            DURATION=30)))
        # agent1 slow (will be killed)
        p_agent1 = subprocess.Popen([sys.executable, script], env=_env(
            "agent", "agent1", 29203, "127.0.0.1:29201,127.0.0.1:29202",
            STORE=store, DURATION=30, HANDLER_SLEEP=10),
            stdout=open(os.path.join(tmp, "agent1.out"), "w"),
            stderr=open(os.path.join(tmp, "agent1.err"), "w"))
        procs.append(p_agent1)
        for i in range(2):
            procs.append(subprocess.Popen([sys.executable, script], env=_env(
                "agent", f"agent{i+2}", 29204 + i, "127.0.0.1:29201,127.0.0.1:29202",
                STORE=store, DURATION=30, HANDLER_SLEEP=1)))
        time.sleep(8)
        # kill agent1 after task assigned
        p_agent1.terminate()
        p_agent1.wait(timeout=5)
        # wait for completion
        deadline = time.time() + 40
        status = None
        while time.time() < deadline:
            if os.path.exists(task_file):
                try:
                    status = json.load(open(task_file))
                    if status.get("tasks", {}).get("task1", {}).get("status") == "completed":
                        break
                except Exception:
                    pass
            time.sleep(0.5)
        assert status is not None
        task = status["tasks"]["task1"]
        assert task["status"] == "completed", task
        assert os.path.exists(os.path.join(tmp, "effect_op1.txt"))
        # count effect file lines (should be one agent id)
        content = open(os.path.join(tmp, "effect_op1.txt")).read().strip()
        assert content in ("agent2", "agent3"), content
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                pass