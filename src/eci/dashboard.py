"""ECI Neural Simulation Lab — local dashboard server (stdlib only).

Serves the web UI (web/) and exposes a bounded SNN simulation API backed by
the real :class:`~eci.neuromorphic.snn.SpikingNeuralNetwork`. Research-prototype
tooling: outputs are exploratory dynamics, not claims about brains or consciousness.

Run:  python -m eci.dashboard --host 127.0.0.1 --port 8780
"""

from __future__ import annotations

import argparse
import json
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import torch

from eci.neuromorphic.snn import NEURON_TYPES, SpikingNeuralNetwork
from eci.version import __version__

__all__ = ["run_simulation", "DashboardState", "make_handler", "serve"]

WEB_DIR = Path(__file__).resolve().parent.parent.parent / "web"

LIMITS = {
    "n_input": (1, 32),
    "n_hidden": (1, 128),
    "n_output": (1, 32),
    "n_steps": (10, 2000),
}


def _bounded(name: str, value: Any, default: int) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    lo, hi = LIMITS[name]
    return max(lo, min(hi, v))


def _finite_list(values: Any, expected: int) -> list[float]:
    if not isinstance(values, list):
        raise ValueError("input_pattern must be a list")
    if len(values) != expected:
        raise ValueError(f"input_pattern length {len(values)} != n_input {expected}")
    out: list[float] = []
    for idx, raw in enumerate(values):
        try:
            v = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"input_pattern[{idx}] not finite: {raw!r}") from exc
        if not math.isfinite(v):
            raise ValueError(f"input_pattern[{idx}] not finite: {raw!r}")
        out.append(v)
    return out


def run_simulation(settings: dict[str, Any]) -> dict[str, Any]:
    """Run one bounded SNN trial with full telemetry (raster, voltages, weights)."""
    t0 = time.perf_counter()
    n_input = _bounded("n_input", settings.get("n_input", 4), 4)
    n_hidden = _bounded("n_hidden", settings.get("n_hidden", 6), 6)
    n_output = _bounded("n_output", settings.get("n_output", 2), 2)
    n_steps = _bounded("n_steps", settings.get("n_steps", 100), 100)
    neuron_type = str(settings.get("neuron_type", "lif"))
    if neuron_type not in NEURON_TYPES:
        raise ValueError(f"unknown neuron_type {neuron_type!r}")
    learn = bool(settings.get("learn", False))
    seed = settings.get("seed", 42)
    try:
        seed = int(seed)
    except (TypeError, ValueError):
        seed = 42
    input_pattern = _finite_list(settings.get("input_pattern", [0.1, 0.4, 0.7, 1.0]), n_input)
    x = torch.tensor([input_pattern], dtype=torch.float32)

    torch.manual_seed(seed)
    net = SpikingNeuralNetwork(n_input, n_hidden, n_output, neuron_type=neuron_type)
    net.eval()

    initial_input_weights = [[round(float(v), 6) for v in row] for row in net.input_weights.detach().tolist()]
    initial_output_weights = [[round(float(v), 6) for v in row] for row in net.output_weights.detach().tolist()]

    input_spikes_hist: list[list[int]] = []
    hidden_spikes_hist: list[list[int]] = []
    output_spikes_hist: list[list[int]] = []
    hidden_v_hist: list[list[float]] = []
    output_v_hist: list[list[float]] = []
    pre_hist: list[list[float]] = []
    post_hist: list[list[float]] = []

    def _voltages(layer: torch.nn.Module) -> list[float]:
        for attr in ("membrane_potential", "v"):
            v = getattr(layer, attr, None)
            if v is not None and isinstance(v, torch.Tensor):
                return [round(float(z), 4) for z in v.detach().flatten().tolist()]
        return []

    with torch.no_grad():
        net.reset_state(1)
        input_train = net._rate_encode(x[0], n_steps)
        for t in range(n_steps):
            pre = input_train[t]
            input_spikes_hist.append([int(v) for v in pre.tolist()])
            hidden_current = pre @ net.input_weights
            hs = net.hidden_layer(hidden_current.unsqueeze(0))[0]
            oc = hs @ net.output_weights
            os_ = net.output_layer(oc.unsqueeze(0))[0]
            hidden_spikes_hist.append([int(v) for v in hs.tolist()])
            output_spikes_hist.append([int(v) for v in os_.tolist()])
            hidden_v_hist.append(_voltages(net.hidden_layer))
            output_v_hist.append(_voltages(net.output_layer))
            pre_hist.append([round(float(v), 4) for v in net.pre_trace.tolist()])
            post_hist.append([round(float(v), 4) for v in net.post_trace.tolist()])
            if learn:
                net.pre_trace = net.pre_trace * (1 - 1.0 / net.tau_plus) + pre
                net.post_trace = net.post_trace * (1 - 1.0 / net.tau_minus) + hs
                dw = (
                    net.a_plus * torch.outer(net.pre_trace, hs)
                    - net.a_minus * (net.post_trace.unsqueeze(0) * pre.unsqueeze(1))
                )
                net.input_weights.add_(dw)
                net.input_weights.clamp_(net.w_min, net.w_max)

    out_counts = [sum(col) for col in zip(*output_spikes_hist)] if output_spikes_hist else [0] * n_output
    hid_counts = [sum(col) for col in zip(*hidden_spikes_hist)] if hidden_spikes_hist else [0] * n_hidden
    inp_counts = [sum(col) for col in zip(*input_spikes_hist)] if input_spikes_hist else [0] * n_input

    def _w(w: torch.Tensor) -> list[list[float]]:
        return [[round(float(v), 6) for v in row] for row in w.detach().tolist()]

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        "ok": True,
        "settings": {
            "n_input": n_input,
            "n_hidden": n_hidden,
            "n_output": n_output,
            "n_steps": n_steps,
            "neuron_type": neuron_type,
            "learn": learn,
            "seed": seed,
            "input_pattern": x[0].tolist(),
        },
        "input_counts": inp_counts,
        "hidden_counts": hid_counts,
        "output_counts": out_counts,
        "input_spikes": input_spikes_hist,
        "hidden_spikes": hidden_spikes_hist,
        "output_spikes": output_spikes_hist,
        "hidden_voltage": hidden_v_hist,
        "output_voltage": output_v_hist,
        "pre_trace": pre_hist,
        "post_trace": post_hist,
        "input_weights": _w(net.input_weights),
        "output_weights": _w(net.output_weights),
        "initial_input_weights": initial_input_weights,
        "initial_output_weights": initial_output_weights,
        "elapsed_ms": elapsed_ms,
        "honesty": "research-prototype dynamics; not biological fidelity",
    }


class DashboardState:
    """Shared, lock-guarded state (latest result + run counter)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.last_result: dict[str, Any] | None = None
        self.runs = 0

    def record(self, result: dict[str, Any]) -> None:
        with self.lock:
            self.last_result = result
            self.runs += 1

    def status(self) -> dict[str, Any]:
        with self.lock:
            return {
                "ok": True,
                "version": __version__,
                "runs": self.runs,
                "neuron_types": list(NEURON_TYPES),
                "limits": LIMITS,
                "last_run_settings": (self.last_result or {}).get("settings"),
                "last_elapsed_ms": (self.last_result or {}).get("elapsed_ms"),
            }


def make_handler(state: DashboardState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ECI-Dashboard/" + __version__

        def log_message(self, *a: Any) -> None:  # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: Any) -> None:
            self._send(code, json.dumps(obj, default=str).encode("utf-8"))

        def _static(self, rel: str, ctype: str) -> None:
            path = (WEB_DIR / rel).resolve()
            if not str(path).startswith(str(WEB_DIR.resolve())) or not path.is_file():
                self._json(404, {"ok": False, "error": "not found"})
                return
            self._send(200, path.read_bytes(), ctype)

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._static("index.html", "text/html; charset=utf-8")
            elif self.path == "/styles.css":
                self._static("styles.css", "text/css; charset=utf-8")
            elif self.path == "/dist/app.js":
                self._static("dist/app.js", "application/javascript; charset=utf-8")
            elif self.path == "/api/status":
                self._json(200, state.status())
            elif self.path == "/api/last":
                with state.lock:
                    self._json(200, state.last_result or {"ok": False, "error": "no run yet"})
            else:
                self._json(404, {"ok": False, "error": "unknown path"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/simulate":
                self._json(404, {"ok": False, "error": "unknown path"})
                return
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
                payload = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(payload, dict):
                    raise ValueError("body must be a JSON object")
                result = run_simulation(payload)
                state.record(result)
                self._json(200, result)
            except Exception as exc:  # noqa: BLE001
                self._json(400, {"ok": False, "error": repr(exc)})

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8780) -> None:
    state = DashboardState()
    httpd = ThreadingHTTPServer((host, port), make_handler(state))
    print(f"ECI Simulation Lab v{__version__} -> http://{host}:{port}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def main() -> None:
    ap = argparse.ArgumentParser(description="ECI Neural Simulation Lab")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8780)
    args = ap.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
