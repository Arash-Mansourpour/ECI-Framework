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

## [7.1.0] — 2026-09-14 — PROTOCOL-vNext + Phase 19 coverage closure

- Evolving Collective Intelligence Protocol (`src/eci/protocol_vnext/`):
  genesis + genome, identity lifecycle, capability vectors + `T(n,c,x)` +
  adaptive router, signed messaging (13 types), cognitive loop + 9 faculties,
  living memory (5 layers, salience/forgetting, Dream Engine), federated
  ontology, truth layer (Evidence Keeper + Truth Guardian), multi-dimensional
  reasoning (Pareto frontier), collective learning (CIG/EG/TS), governed
  evolution + Skill Compiler, resilience lab.
- `eci protocol --nodes 3` demo; `FRAMEWORK_VERSION = 7.1.0-PROTOCOL-vNext`.
- Version source is `src/eci/version.py` (`__version__ = 7.1.0`).
- **Phase 19 (2026-09-14, coverage closure)**: `learning` 41%→97% (NAS forward/derive/search), `__main__` 46%→94% (21/21 CLI light-run matrix), total 74%→83% (232 tests, 172 ruff, 72 mypy). Backlog items 2–4 closed; see `docs/CODEBASE_AUDIT.md` Phase 19.
- **Phase 20 (2026-09-14, hot-path mypy + quantum smoke)**: `network/manager` **kwargs→explicit (mypy 72→64), `quantum` 57%→68% (QFT/Grover/QPE/VQE/QAOA/operator/qec/statevector smoke), total 83%→85% (241 tests). Backlog item 5 (mypy) and 85% milestone hit; 172 ruff remains boy-scout.
- **Phase 21 (2026-09-14, transports/fabric smoke)**: `mcp/transports` InProcess/Stdio/Http + `mcp/fabric` build + `network/tcp`/`security/secure_channel` smoke (6 tests), total 241→247 held at 85% (16735 stmts). Remaining low pockets (fabric 40%, transports 32% etc.) stay boy-scout.

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
