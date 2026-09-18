"""Dashboard backend: bounded, deterministic, JSON-safe telemetry."""

import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

from eci.dashboard import DashboardState, make_handler, run_simulation


def test_run_simulation_deterministic_and_bounded():
    settings = {"n_input": 4, "n_hidden": 6, "n_output": 2, "n_steps": 20, "seed": 7, "input_pattern": [0.1, 0.4, 0.7, 1.0]}
    r1 = run_simulation(settings)
    r2 = run_simulation(settings)
    assert r1["ok"] is True
    assert r1["output_counts"] == r2["output_counts"]
    assert r1["hidden_counts"] == r2["hidden_counts"]
    assert len(r1["input_spikes"]) == 20
    assert len(r1["hidden_spikes"]) == 20
    assert len(r1["output_spikes"]) == 20
    assert len(r1["hidden_voltage"]) == 20
    assert len(r1["initial_input_weights"]) == 4
    assert len(r1["input_weights"][0]) == 6
    assert "honesty" in r1


def test_run_simulation_input_pattern_validation():
    import pytest

    with pytest.raises(ValueError, match="input_pattern"):
        run_simulation({"n_input": 4, "input_pattern": [0.1, 0.2]})
    with pytest.raises(ValueError, match="not finite"):
        run_simulation({"n_input": 2, "input_pattern": [float("inf"), 0.5]})
    with pytest.raises(ValueError, match="unknown neuron_type"):
        run_simulation({"n_input": 2, "n_hidden": 2, "n_output": 2, "neuron_type": "hh", "input_pattern": [0.1, 0.2]})


def test_run_simulation_all_neuron_types():
    for kind in ("lif", "adlif", "izhikevich", "homeostatic"):
        r = run_simulation({"n_input": 2, "n_hidden": 3, "n_output": 2, "n_steps": 10, "neuron_type": kind, "input_pattern": [0.2, 0.8]})
        assert r["ok"] is True
        assert len(r["output_counts"]) == 2


def test_dashboard_http_status_and_simulate():
    state = DashboardState()
    Handler = make_handler(state)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = httpd.server_address
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)
    try:
        base = f"http://{host}:{port}"
        s = json.loads(urllib.request.urlopen(base + "/api/status").read().decode())
        assert s["ok"] is True
        assert "version" in s
        payload = json.dumps({"n_input": 3, "n_hidden": 4, "n_output": 2, "n_steps": 10, "input_pattern": [0.1, 0.5, 0.9]}).encode()
        req = urllib.request.Request(base + "/api/simulate", data=payload, headers={"Content-Type": "application/json"})
        r = json.loads(urllib.request.urlopen(req).read().decode())
        assert r["ok"] is True
        assert "input_spikes" in r
        last = json.loads(urllib.request.urlopen(base + "/api/last").read().decode())
        assert last["ok"] is True
        assert last["settings"]["n_input"] == 3
        bad = json.dumps({"n_input": 2, "input_pattern": [0.1]}).encode()
        req2 = urllib.request.Request(base + "/api/simulate", data=bad, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req2)
            raise AssertionError("expected 400")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            body = json.loads(exc.read().decode())
            assert body["ok"] is False
    finally:
        httpd.shutdown()
        t.join(timeout=2)
