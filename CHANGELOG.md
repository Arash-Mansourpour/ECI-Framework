# Changelog

All notable changes to the ECI Framework. Versions prior to 6.0 are under
MIT; from 6.0 onward the ECI Non-Commercial License v1.0 applies
(see `LICENSE`). The single source of truth for the current code version
is `src/eci/version.py`.

## License change (Phase 18 — 2026-09-14)

- **v5.9.0 and earlier**: released under **MIT** (Zenodo archive, citable;
  MIT grant survives for that artifact only).
- **v6.0.0 → v7.0.0 → v7.1.0 (current)**: released under **ECI Non-Commercial
  License v1.0** (`LICENSE`). Commercial use requires prior written permission
  from Arash Mansourpour. The `pyproject.toml` `license` field and
  `classifiers` were corrected in Phase 18 to match the authoritative
  `LICENSE` file; prior `pyproject.toml` MIT declarations after v6.0 were
  drift and do not relicense later code.

| Version | License | Notes |
|---|---|---|
| ≤ 5.9.0 | MIT | Last MIT release, archived on Zenodo |
| 6.0.0 – 7.0.0 | ECI Non-Commercial v1.0 | `LICENSE` file already ECI NC, `pyproject.toml` still said MIT (drift, fixed Phase 18) |
| 7.1.0 (current) | ECI Non-Commercial v1.0 | All metadata (pyproject, classifiers, README badge, CITATION.cff) now consistent |

## [7.1.0] — 2026-09-14 — PROTOCOL-vNext

- Evolving Collective Intelligence Protocol (`src/eci/protocol_vnext/`):
  genesis + genome, identity lifecycle, capability vectors + `T(n,c,x)` +
  adaptive router, signed messaging (13 types), cognitive loop + 9 faculties,
  living memory (5 layers, salience/forgetting, Dream Engine), federated
  ontology, truth layer (Evidence Keeper + Truth Guardian), multi-dimensional
  reasoning (Pareto frontier), collective learning (CIG/EG/TS), governed
  evolution + Skill Compiler, resilience lab.
- `eci protocol --nodes 3` demo; `FRAMEWORK_VERSION = 7.1.0-PROTOCOL-vNext`.
- Version source is `src/eci/version.py` (`__version__ = 7.1.0`).

## [7.0.0] — 2026-09 — EVERLASTING Continuance

- Seven pillars: capability tokens (HMAC macaroons), runtime verification
  (LTL-lite + watchtower), temporal continuum (hash-chained snapshots),
  autonomic MAPE-K, interface compat (fail-closed + sunsets), governance
  futures (futarchy/sortition/emergency), adversarial epistemology.
- `src/eci/aikernel/` unification mesh grew to 8 adapters; see
  `docs/AIKERNEL_UNIFICATION.md`.
- Codebase audit at 209 tests, 74% coverage, 168 ruff findings, 72 mypy errors
  (`docs/CODEBASE_AUDIT.md`, Phase 17).

## [6.x] — 2025-2026 — Hyper-architecture + deep systems

- Kernel/bus/lifecycle, observability, persistence, resilience, orchestration,
  plugins, authz, streaming, API gateway, tenancy, health, caps, verify,
  continuum, mapek, compat, futura, redteam, MCP fabric (`mcp/`), frontier
  systems.

## [5.9.0] — last MIT release

- Ecosystem justice: court, LMSR markets, semantic commons, privacy guardian,
  genome. Archived on Zenodo under MIT.
