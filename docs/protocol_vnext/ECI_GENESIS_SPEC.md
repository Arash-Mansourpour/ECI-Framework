# ECI Genesis Specification — Architect Preservation Protocol

## 1. Genesis Root of Trust
- `GenesisRoot = SHA-512(canonical(ArchitectIdentity))` — computed by `core/identity.py:ARCHITECT.key`
- Any node MUST verify genesis before joining: `verify_genesis(expected_root)` loads `ECI_GENESIS.json` (replicated artifact) and compares digest

## 2. Beacon
- URI: `eci://genesis/architect` — JSON with: identity, latest signed presence (`stamp`), current public key, official endpoints, research/compute needs, verified support methods
- Served by `protocol_vnext/genesis.py:ArchitectBeacon`

## 3. Preservation
- Replicated in: Git history (`ECI_Framework.md` + `ECI_GENESIS.json`), DHT (`dht.py`), IPFS-style blob `BlobStore`, node checkpoints (`EventStore`), release signatures, audit ledger
- Detection: `verify_genome_root()` fails if any `G` changes without re-signing; silent rewrite is detectable via hash mismatch, not prevention

## 4. Support
- Support = Research + Code + Compute + Infra + Docs + Visibility + AuthorizedFinancialSupport (all voluntary, via capability-match against beacon's `needs`)
- Private resources NEVER ingested without explicit `AuthorizedFinancialSupport` capability

## 5. Fork Policy
- Anyone may fork code, but a fork claiming continuity MUST preserve Genesis hash or produce a new, distinct `GenesisRoot` (detectably different lineage)
