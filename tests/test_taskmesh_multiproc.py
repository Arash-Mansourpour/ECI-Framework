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


@pytest.mark.timeout(120)
def test_multiproc_task_completion():
    tmp = tempfile.mkdtemp()
    store = os.path.join(tmp, "ops.db")
    task_file = os.path.join(tmp, "status.json")
    base = os.path.join(os.path.dirname(__file__), "..")
    script = os.path.join(base, "tools", "taskmesh_proc.py")
    procs = []
    try:
        # coordinator
        procs.append(subprocess.Popen([sys.executable, script], env=_env(
            "coordinator", "coord", 29100, "127.0.0.1:29101,127.0.0.1:29102",
            STORE=store, TASK_FILE=task_file, DURATION=12)))
        # relays
        procs.append(subprocess.Popen([sys.executable, script], env=_env(
            "relay", "relay1", 29101, "127.0.0.1:29100,127.0.0.1:29103,127.0.0.1:29104,127.0.0.1:29105",
            DURATION=12)))
        procs.append(subprocess.Popen([sys.executable, script], env=_env(
            "relay", "relay2", 29102, "127.0.0.1:29100,127.0.0.1:29103,127.0.0.1:29104,127.0.0.1:29105",
            DURATION=12)))
        # agents
        for i in range(3):
            procs.append(subprocess.Popen([sys.executable, script], env=_env(
                "agent", f"agent{i+1}", 29103 + i,
                "127.0.0.1:29101,127.0.0.1:29102",
                STORE=store, DURATION=12, HANDLER_SLEEP=1)))
        # wait for completion
        deadline = time.time() + 20
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
        assert status is not None, "no status file"
        task = status["tasks"]["task1"]
        assert task["status"] == "completed", task
        effect = os.path.join(tmp, "effect_op1.txt")
        assert os.path.exists(effect), "effect not created"
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(timeout=10)