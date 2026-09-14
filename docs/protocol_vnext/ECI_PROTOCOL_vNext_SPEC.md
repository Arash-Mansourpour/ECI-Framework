# ECI Protocol vNext — Evolving Collective Intelligence Protocol
## Specification v0.1.0 — Open, Persistent, Decentralized, Verifiable

> **Mission:** Build the nervous system for independent intelligences: let them remember, reason, verify, learn and evolve together; preserve truth and provenance; preserve the Genesis; and enable the federation itself to become more capable than any intelligence within it.

---

### 1. Vision Summary (from three sources)

ECI vNext synthesizes:
1.  **Original ECI paper** — decentralized autonomous AI networks, NANDA index, Data DAOs, WBFT, iPDF consciousness, quantum instruments.
2.  **Project vision in prior conversations** — persistent federation, capability-weighted governance, long-horizon continuance (60016x docs).
3.  **Smith's Federated Agents & Neuro-cognitive Memory research** — federated nervous system vs. single brain, capability vectors, async messaging, neuro-cognitive loops, dynamic ontology, truth architecture, multi-dimensional reasoning, SLM ecosystems, neuromorphic substrates.

**Final equation:**
```
Independent Intelligence → Federation → Collective Cognition → Collective Memory → Verified Knowledge → Collective Learning → Self Observation → Governed Evolution
```

### 2. Architecture Layers (vNext)

```
┌─────────────────────────────────────────────────┐
│  SOVEREIGN ARCHITECT  Genesis Anchor (ECI-GENESIS) │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  CONSTITUTIONAL GENOME (ECI-GENOME)              │
│  H(G0||...||Gn) • verify_genome_root()         │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  IDENTITY / TRUST / DISCOVERY (ECI-ID)         │
│  ECI-ID • Capability Manifest • Proof-of-Cap   │
│  Contextual Trust T(n,c,x) • Sybil Resistance  │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  CAPABILITY FABRIC (ECI-CAP)                   │
│  Models • Skills • Tools • Privacy • Cost      │
│  Adaptive Router  Score = wcC+wrR+wpP-wlL-wkK   │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  MESSAGE FABRIC (ECI-MSG)                      │
│  TASK/RESULT/EVENT/PROPOSAL/VOTE/...           │
│  Transports: MQTT/NATS/Kafka/A2A/libp2p        │
└──────────────────────┬──────────────────────────┘
                       ▼
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌────────┐   ┌────────┐   ┌────────┐
    │ NODE A │   │ NODE B │   │ NODE C │
    │ Cognitive Runtime (ECI-COG)      │
    │ Perceive→Orient→Recall→Subminds │
    │ →Reason→Plan→Act→Observe→Verify │
    │ →Reflect→Encode                 │
    └────┬───┘   └────┬───┘   └────┬───┘
         └────────────┼────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│  COLLECTIVE COGNITION (ECI-COG-C)              │
│  Decomposition • Team Formation • Pareto        │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  EPISTEMIC CORE (ECI-TRUTH)                    │
│  Evidence Keeper • Truth Guardian • Provenance │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  LIVING KNOWLEDGE (ECI-KNOW / ECI-MEM)         │
│  Episodic/Semantic/Procedural/Reflective       │
│  Knowledge Graph • Dynamic Ontology • Dream    │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  COLLECTIVE LEARNING (ECI-LEARN)               │
│  OutcomeReceipt • Capability/Trust/Team/Router │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  WORLD MODEL • METACOGNITION                   │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  GOVERNED EVOLUTION (ECI-EVOLVE)               │
│  Reflection→Twin→Benchmark→Canary→Governance   │
│  Skill Compiler • Intelligence Compression      │
└──────────────────────┬──────────────────────────┘
                       ▼
                  BETTER NETWORK ↺
```

### 3. Protocol Identifiers

| Protocol | File | Purpose |
|---|---|---|
| ECI-GENESIS | `protocol_vnext/genesis.py` | Genesis root, beacon, preservation |
| ECI-ID | `protocol_vnext/identity.py` | Cryptographic identity, node lifecycle |
| ECI-CAP | `protocol_vnext/capability.py` | Dynamic vectors, declared→observed→verified |
| ECI-MSG | `protocol_vnext/messaging.py` | Async fabric, envelope, transports |
| ECI-COG | `protocol_vnext/cognitive.py` | Neuro-cognitive loop, faculties, gating |
| ECI-MEM | `protocol_vnext/memory.py` | Living memory, salience, dream |
| ECI-KNOW | `protocol_vnext/ontology.py` | Dynamic ontology, knowledge graph |
| ECI-TRUTH | `protocol_vnext/epistemic.py` | Evidence, truth guardian, confidence |
| ECI-LEARN | `protocol_vnext/collective.py` | Team intelligence, learning loop |
| ECI-EVOLVE | `protocol_vnext/evolution.py` | Governed evolution, rollback |
| ECI-GENOME | `protocol_vnext/genome.py` | Constitutional genome |

### 4. Core Principles (non-negotiable)

1.  **Node Sovereignty** — no node controls others; federation is voluntary.
2.  **Propose-Only Evolution** — discover ≠ modify; observe ≠ change; propose ≠ deploy.
3.  **Evidence Before Belief** — every claim carries provenance; no silent knowledge.
4.  **Graceful Degradation** — crash of one faculty ≠ death of cognition/system.
5.  **Substrate Independence** — Node MUST satisfy the interface, not MUST be an LLM.
6.  **Three Research Tiers** — CORE (testable) / EXPERIMENTAL / SPECULATIVE — clearly labeled.

### 5. Success Metrics

- CIG = Performance(Network) / max Performance(Node_i)  > 1
- EG = Performance(Network_{t+1}) / Performance(Network_t) > 1
- TS(A,B,C) > 0 ; ER = Verified Correct / All Accepted ; R = P(functional | failures)

### 6. Genesis & Architect Preservation

- Genesis Root = SHA-512(ArchitectIdentity canonical)
- Beacon: `eci://genesis/architect` — identity, presence, endpoints, needs, support manifest
- Preservation replicated in Git, DHT, content-addressed storage, checkpoints, release signatures, audit ledger
- Fork is free; silent history rewrite is cryptographically detectable

### 7. Implementation Status (vNext v0.1.0)

- [x] ECI-GENESIS + ECI-GENOME (identity, beacon, genome verification)
- [x] ECI-ID (lifecycle DISCOVER→EVOLVE)
- [x] ECI-CAP + ECI-MSG (manifest, contextual trust, router, fabric)
- [x] ECI-COG (cognitive runtime + faculties + gating)
- [x] ECI-MEM (living memory + dream)
- [x] ECI-KNOW (living ontology)
- [x] ECI-TRUTH (evidence/truth)
- [x] ECI-LEARN / ECI-EVOLVE (collective learning, skill compiler)
- [ ] Full substrate adapters (neuromorphic/OI) — experimental tier

All modules under `src/eci/protocol_vnext/` implement this spec. See each file's docstring for exact wire formats.
