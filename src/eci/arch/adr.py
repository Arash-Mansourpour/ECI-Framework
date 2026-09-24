"""Architecture Decision Records for v8 OMNISCIENCE.

Immutable in-code log so future agents (and humans) know WHY
each structural choice was made. Mirrors docs/ADRs on disk.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ADR:
    id: str
    title: str
    status: str  # accepted | superseded | proposed
    context: str
    decision: str
    consequences: str = ""


ADR_REGISTRY: list[ADR] = [
    ADR(
        id="ADR-001",
        title="Facade decomposition without breaking ECIFramework",
        status="accepted",
        context="ECIFramework (~667 lines) is a God-Object. Full rewrite risks breaking 262 tests.",
        decision="Keep ECIFramework as stable facade; add v8 subsystems as lazily-wired "
        "composables (arch/quantum-router/p2p/research). Enforce size ceiling via fitness, not rewrite.",
        consequences="Facade stays; new code lives in arch/, quantum/hardware.py, federation/p2p.py, research/.",
    ),
    ADR(
        id="ADR-002",
        title="Backend abstraction over optional hardware SDKs",
        status="accepted",
        context="Qiskit/Braket may not be installed. Direct imports would break CI and offline labs.",
        decision="Define QuantumBackend protocol in quantum/hardware.py. Hardware adapters import SDKs "
        "lazily and report available=False when missing (fail-closed, never silent fallback).",
        consequences="SimBackendAdapter is default; Qiskit/Braket are opt-in extras.",
    ),
    ADR(
        id="ADR-003",
        title="P2P transport without external libp2p dependency",
        status="accepted",
        context="Adding libp2p-py would balloon install and flake on Windows CI.",
        decision="Define Transport protocol + InMemoryTransport (deterministic tests) + TCPTransport "
        "(asyncio, localhost). GossipNode runs PBFT-style 2/3 quorum over any transport. "
        "PartitionChaos simulates split-brain for Jepsen-style assertions.",
        consequences="No new hard dependency; real sockets covered, DHT deferred to v8.1.",
    ),
    ADR(
        id="ADR-004",
        title="Economic attacks as first-class simulation",
        status="accepted",
        context="MarketCommons confidence = money-at-risk, but no test proves resistance to whales/collusion.",
        decision="Add economy_attack.py with pure-math whale-wash + collusion-ring + slashing "
        "evaluation. All deterministic, seeded, no network needed.",
        consequences="Governance claims become falsifiable; Brier + slash path covered by tests.",
    ),
    ADR(
        id="ADR-005",
        title="Observability via graceful OTel + native Prometheus",
        status="accepted",
        context="MetricsRegistry already exposes to_prometheus(). OTel SDK is optional and heavy.",
        decision="Add observability/otel.py as NoOp-unless-installed bridge. Health endpoint gains "
        "/metrics Prometheus text without new hard deps.",
        consequences="Works offline; lights up automatically when opentelemetry is installed.",
    ),
    ADR(
        id="ADR-006",
        title="Autonomous research loop as ledgered composable",
        status="accepted",
        context="cognition/learning/redteam exist but no closed loop turns them into self-improvement.",
        decision="Add research/loop.py: Hypothesis -> twin_test -> canary -> DAO vote -> Brier update, "
        "every step stamped by ARCHITECT and recorded with provenance-friendly dicts.",
        consequences="Self-evolution becomes auditable; twin/morph fitness stays task-defined (honest).",
    ),
]

_BY_ID = {a.id: a for a in ADR_REGISTRY}


def list_adrs() -> list[dict[str, str]]:
    return [
        {"id": a.id, "title": a.title, "status": a.status,
         "decision": a.decision, "context": a.context, "consequences": a.consequences}
        for a in ADR_REGISTRY
    ]


def get_adr(adr_id: str) -> dict[str, str]:
    a = _BY_ID[adr_id]
    return {"id": a.id, "title": a.title, "status": a.status,
            "decision": a.decision, "context": a.context, "consequences": a.consequences}
