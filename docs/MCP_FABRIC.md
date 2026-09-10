# Omniverse MCP Fabric (v6.1)

> یک MCP بسیار قدرتمند و انعطاف‌پذیر: کل فریمورک به‌صورت ابزارهای namespaced،
> روی سه transport، با pipeline سیاستی، سشن‌های بودجه‌دار و فدراسیون مش.

## معماری خلاقانه

```
foreign agent ─┬─ stdio ──────┐
               ├─ HTTP/SSE ───┼─► McpServer ─► McpPipeline ─► McpRegistry ─► ECI subsystems
               └─ in-process ─┘       │              │               │
                                 sessions      9 stages        local + gateway-bridged
                                 budgets       auth/quota/     + agent-bridged
                                 attest        budget/dry-run/ + federated upstreams
                                               breaker/observe
```

- **Mesh registry**: ابزارهای `p0.*`, `quantum.*`, `consciousness.*`, `network.*`,
  `workflow.*`, `agent.*`, `memory.*`, `dao.*`, `treasury.*`, `eval.*`, `supply.*`,
  `twin.*`, `chaos.*`, `system.*` + aliasهای legacy (`p0_attest`...) — حدود ۳۰ ابزار.
- **Pipeline نه‌مرحله‌ای**: session → rate → idempotency → auth (RBAC/ABAC + caps) →
  quota/budget → dry_run (twin) → breaker/bulkhead → execute → observe
  (trace/metrics/audit/provenance/bus). هیچ انکاری بی‌دلیل نیست: `{stage, reasons}`.
- **Sessions**: namespace + attestation + budget + token-bucket + انقضا.
- **Dry-run universe**: هر ابزار mutating با `dry_run=true` فقط شبیه‌سازی می‌کند.
- **Idempotency**: `idempotency_key` نتیجه را replay می‌کند (retry-safe).
- **Prompts**: `consciousness-audit`, `quantum-suite`, `dao-proposal`,
  `incident-triage`, `obedience-check`.
- **Resources**: `eci://info`, `eci://system.status`, `eci://metrics`,
  `eci://gateway/schema`, `eci://treasury`, `eci://eval/gates`, `eci://sbom`.
- **Federation**: upstreamهای ریموت زیر prefix (مثل `ext.echo`) با allowlist +
  circuit-breaker — مشِ MCPها.
- **Transports**: stdio (Claude Desktop)، HTTP (`POST /mcp`, `GET /mcp/tools`,
  SSE `GET /mcp/events`)، in-process (تست/ایجنت‌لوپ).

## اجرا

```bash
python mcp/server.py --list
python mcp/server.py                        # stdio
python mcp/server.py --transport http --port 8899
PYTHONPATH=src python -m eci mcp --list
PYTHONPATH=src python -m eci mcp --transport http --port 8899
```

## مثال JSON-RPC

```json
{"id": 1, "method": "initialize", "params": {}}
{"id": 2, "method": "sessions/create", "params": {"subject": "operator", "capabilities": ["*"]}}
{"id": 3, "method": "tools/call", "params": {"name": "agent.run", "arguments": {"goal": "demo"}, "session_id": "<sid>"}}
{"id": 4, "method": "tools/call", "params": {"name": "dao.propose", "arguments": {"title": "x"}, "dry_run": true}}
{"id": 5, "method": "prompts/get", "params": {"name": "obedience-check", "arguments": {"action": "vote"}}}
{"id": 6, "method": "resources/read", "params": {"uri": "eci://system.status"}}
```
