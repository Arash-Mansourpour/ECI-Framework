# ECI Framework — Deployment Status (audit 2026-09-25)

Scope: `Dockerfile`, `docker-compose.yml`, `k8s/deployment.yaml`, `k8s/service.yaml`
against `src/eci/health.py` + `src/eci/__main__.py` (CLI) + env-var grep over `src/`.
Nothing below was `docker build`/`docker run`/`kubectl apply`d in this pass
(deliberately untested — see §4). No code/tests touched.

How to re-verify everything on Windows PowerShell 5.1:

```powershell
docker version
$env:PYTHONPATH="src"; python -m eci health --once
$env:PYTHONPATH="src"; python -m eci health --serve --port 8777
# in another shell:
curl.exe http://localhost:8777/health
curl.exe http://localhost:8777/metrics
python -c "import yaml; yaml.safe_load(open('docker-compose.yml')); yaml.safe_load(open('k8s/deployment.yaml')); yaml.safe_load(open('k8s/service.yaml')); print('yaml ok')"
$env:PYTHONPATH="src"; python -m pytest tests/test_repo_hygiene.py -k readme -q
```

## 1. Endpoint audit (`src/eci/health.py`, `src/eci/__main__.py`)

| Claim | Verdict | Evidence |
|---|---|---|
| `python -m eci health --serve --port 8777` serves HTTP | VERIFIED (by reading) | `src/eci/__main__.py:132-142` (`cmd_health` → `serve(args.port)`), `480-483` (`--serve`, `--port default 8777`); `src/eci/health.py:69-72` binds `0.0.0.0:<port>` |
| `GET /health` returns 200 JSON | VERIFIED (by reading) | `src/eci/health.py:56-66`: any non-`/metrics` path returns 200 + JSON `status()`. Note: handler is catch-all, so `/health`, `/`, and even `/bogus` all 200 — probes pass, but there is no 404 routing |
| `GET /metrics` returns Prometheus text | VERIFIED (by reading) | `src/eci/health.py:58-59` + `41-47` (`eci_up`, `eci_ledger_height`, `eci_ledger_ok`, `eci_peers`, `eci_uptime_s`) |
| `python -m eci health --once` prints JSON, exit 0 (used by Dockerfile HEALTHCHECK) | VERIFIED (by reading) | Flag registered `__main__.py:482`; `cmd_health` prints `status()` whenever `--serve` is absent, so `--once` and bare `health` both print JSON and return 0 |

Prove it (no docker needed):

```powershell
$env:PYTHONPATH="src"; python -m eci health --once
$env:PYTHONPATH="src"; python -m eci health --serve --port 8777
curl.exe http://localhost:8777/health
curl.exe http://localhost:8777/metrics
```

## 2. Env-var audit (grep over `src/`)

Grep run: `ECI_PROFILE|ECI_NODE_ID|ECI_BOOTSTRAP|ECI_PORT` over `src/**/*.py`.

| Var | Read anywhere in `src/`? | Verdict |
|---|---|---|
| `ECI_PROFILE` | Yes — `src/eci/health.py:33` (`status()["profile"]`, default `"server"`) | VERIFIED — but display-only; no behavior branches on `server` vs `edge` |
| `ECI_NODE_ID` | Yes — `src/eci/health.py:34` (`status()["node"]`, default `"local"`) | VERIFIED — display-only |
| `ECI_BOOTSTRAP` | **No hits in `src/`** (only `docker-compose.yml` + its comment) | SCAFFOLDING (aspirational) — no code parses it, nothing dials it |
| `ECI_PORT` | **No hits in `src/`** (only `Dockerfile:9` `ENV ECI_PORT=8777`) | SCAFFOLDING (unwired) — serve port comes from CLI `--port`, not the env var. Image still works because `CMD ["health","--serve","--port","8777"]` hardcodes it |

Prove it:

```powershell
Select-String -Path src\eci\*.py, src\eci\**\*.py -Pattern 'ECI_PROFILE|ECI_NODE_ID|ECI_BOOTSTRAP|ECI_PORT'
# expect only health.py:33-34; ECI_BOOTSTRAP / ECI_PORT have zero src/ hits
```

## 3. Per-item verdicts

| Item | Verdict | Notes + proving command |
|---|---|---|
| `Dockerfile` | VERIFIED (by reading), UNTESTED (build not run) | `FROM python:3.11-slim`, `COPY pyproject.toml README.md`, `COPY src`, `COPY protocol0` (both exist), `pip install -e .[dev]`, `EXPOSE 8777`, `HEALTHCHECK CMD python -m eci health --once` (valid per §1), `ENTRYPOINT ["python","-m","eci"] + CMD ["health","--serve","--port","8777"]` = audited serve command. Caveat: `ENV ECI_PORT=8777` is unwired (§2) — left untouched, documented here. Change in this pass: **none** (no factually-wrong line). Prove: `docker build .` (NOT run in this pass, see §4) |
| `docker-compose.yml` (4 nodes, `ECI_BOOTSTRAP` gossip env) | SCAFFOLDING as a "gossip mesh"; VERIFIED as "4 isolated health servers" | Each service builds `.`, maps host 8777–8780 → container 8777, sets `ECI_PROFILE`/`ECI_NODE_ID` (display-only, §2). `ECI_BOOTSTRAP` is aspirational — kept + commented, not deleted, so future wiring keeps a stable env contract. `health.py --serve` never instantiates `TCPTransport`/`GossipNode` and always reports `peers=0`. Change in this pass: header + per-service comments marking `ECI_BOOTSTRAP` aspirational; added stdlib `urllib` `healthcheck` per service hitting `http://localhost:8777/health` (stronger than Dockerfile's `--once`, which never touches the socket; no `curl` needed on slim). Prove mesh-absence: `curl.exe http://localhost:8777/health` → `"peers": 0` on every node even with `ECI_BOOTSTRAP` set. Prove up: `docker compose up --build` (NOT run, see §4) |
| `k8s/deployment.yaml` | VERIFIED (by reading), UNTESTED (no cluster) | `selector.matchLabels {app: eci-framework}` == `template.metadata.labels.app` ✓; `containerPort: 8777` == probes `port: 8777` == `command --port 8777` ✓; probes `path: /health` → 200 per §1 (catch-all) ✓; `PYTHONPATH=src` harmless. Image `eci-framework:8.0.0` vs code `8.1.0` (pyproject) is a stale tag, not a functional break — left untouched. Change in this pass: **none** (already self-consistent). Prove: `kubectl apply --dry-run=client -f k8s/` + `kubectl get pods` + `curl <pod>:8777/health` (NOT run, see §4) |
| `k8s/service.yaml` | VERIFIED (by reading), UNTESTED (no cluster) | `selector {app: eci-framework}` matches Deployment pods ✓; `port: 8777 → targetPort: 8777` ✓; `prometheus.io/scrape=true port=8777 path=/metrics` matches §1 `/metrics` ✓; `ClusterIP` correct for in-cluster scrape. Change in this pass: **none**. Prove: `kubectl apply --dry-run=client -f k8s/` + Prometheus targets page (NOT run, see §4) |
| OTel collector | SCAFFOLDING (absent by design) | `src/eci/observability/otel.py` is a NoOp-unless-SDK `OtelBridge`; repo has no collector manifest/sidecar in `k8s/` and no OTLP exporter config. Nothing to scrape OTel — Prometheus path is the native `/metrics` text. Prove: `Test-Path k8s/*collector*` → false; `python -c "from eci.observability.otel import OtelBridge; print(OtelBridge().health())"` → `otel_available: False` without SDK |
| Hardware quantum backends (Qiskit / Braket) | SCAFFOLDING (fail-closed); sim VERIFIED | `src/eci/quantum/hardware.py`: `SimBackendAdapter.available()` always true (deterministic, dependency-free); `QiskitBackend`/`BraketBackend` return `available()=False` + `run()` error-result when SDKs missing — never silent fallback. `BackendRouter` routes to `sim` when hardware absent. Prove: `python -c "from eci.quantum.hardware import BackendRouter; print(BackendRouter().health())"` → sim ok, qiskit/braket unavailable |

## 4. What remains UNTESTED and why

| Not run | Reason |
|---|---|
| `docker build .`, `docker compose up --build`, `curl localhost:8777/health` against containers | Task scope forbade running docker beyond `docker version` (which reports client+server `28.0.1` present, so the commands *should* work but were deliberately not executed). Compose `healthcheck` YAML is `yaml.safe_load`-validated only |
| `kubectl apply --dry-run=client -f k8s/`, live probe check | No cluster in this environment; manifests validated for YAML parse + selector/port self-consistency by reading only |
| OTel collector export, Qiskit/Braket hardware runs | No collector manifest exists; hardware SDKs not installed — by design these degrade to NoOp/unavailable (fail-closed) |
| Live multi-node gossip | No code path wires `ECI_BOOTSTRAP` → transport; `TCPTransport`/`GossipNode` exist as library (`src/eci/federation/p2p.py`, `src/eci/network/tcp.py`, `src/eci/network/gossip.py`) but `health --serve` never calls them — integration is future work |

## 5. Validation run (this pass)

```powershell
python -c "import yaml; yaml.safe_load(open('docker-compose.yml')); yaml.safe_load(open('k8s/deployment.yaml')); yaml.safe_load(open('k8s/service.yaml')); print('yaml ok')"
$env:PYTHONPATH="src"; python -m pytest tests/test_repo_hygiene.py -k readme -q
```

Both must pass. The hygiene gate (`test_readme_version_matches_code`) is unrelated to infra files and should stay green.

## 6. Files changed in this pass

- `docker-compose.yml` — aspirational comments + per-service `/health` healthchecks (only functional change).
- `docs/DEPLOYMENT_STATUS.md` — new (this file).
- `k8s/deployment.yaml`, `k8s/service.yaml` — read + audited, no edit (already self-consistent).
- `Dockerfile` — read + audited, no edit (no factually-wrong line; `ECI_PORT` unwired noted in §2).
