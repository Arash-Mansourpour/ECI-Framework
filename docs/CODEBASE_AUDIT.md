# Codebase audit — test/lint/type ground truth (Phase 17)

Measured 2026-09-11 on Python 3.12, torch CPU: **209 tests green
(incl. 2 new ratchet tests), 74% total statement coverage,
168 ruff findings (down from 2267 after this phase's fixes), 72 mypy
errors (down from 76).** Method: `coverage run -m pytest`,
`ruff check src tests`, `mypy src/eci`, plus a static import scan
mapping test files to packages. A test file covering N packages counts
toward each — per-package test counts don't sum to the total. Coverage
is statement coverage, not branch coverage. Ruff/mypy columns are
post-fix values; the debt profile section records what was fixed vs.
flagged.

## Per-package table

Legend: tests = directly-importing test files (count of test fns in
brackets, shared files counted per package) · cov = statement coverage ·
ruff/mypy = finding counts at audit time.

| package | tests (n) | cov% | ruff | mypy | notes |
|---|---|---|---|---|---|
| agents | test_cognition (11) | 75 | 56 | 0 |  |
| aikernel | 15 files (85) | 93 | 4 | 0 | unification core; NaN-guard added P17 |
| api | test_v6_hyper (20, shared) | 82 | 1 | 0 |  |
| authz | test_v6_hyper (shared) | 92 | 0 | 0 |  |
| benchmarking | test_max, test_obedience_stack (11) | 75 | 0 | 2 |  |
| caps | test_everlasting (8, shared) | 92 | 0 | 0 |  |
| chaos | test_v6_hyper (shared) | 95 | 0 | 0 |  |
| cognition | test_cognition, phase6/7 (18) | 95 | 9 | 2 | F841 dead vars fixed P17 |
| compat | test_everlasting (shared) | 93 | 0 | 0 |  |
| consciousness | 11 files (40+) | 67 | 15 | 18 | largest ruff count; mostly UP006/UP035 modernization debt |
| continuum | test_everlasting (shared) | 96 | 0 | 0 |  |
| core | test_network/partition/protocol0 (9) | 70 | 1 | 0 |  |
| cybernetics | **none (zero-direct)** | 49 | 0 | 1 | poor-fit per AIK audit; viability scalar untested beyond transitive |
| data | **none (zero-direct)** | 61 | 0 | 0 | poor-fit; cache/vectors only transitively covered |
| eval | test_mcp_fabric (13, shared) | 92 | 0 | 0 |  |
| federation | test_frontier (6, shared) | 97 | 0 | 0 |  |
| futura | test_everlasting (shared) | 97 | 0 | 0 | dead import removed P17 |
| genome | test_ecosystem (5, shared) | 87 | 0 | 0 |  |
| governance | 6 files (25+) | 75 | 8 | 0 |  |
| health | test_mesh (5, shared) | 54 | 0 | 0 | CLI probe paths mostly untested |
| immune | test_immune (3) | 90 | 4 | 0 |  |
| kernel | test_v6_hyper (shared) | 81 | 1 | 0 |  |
| learning | phase8/13 (7) | 41 | 10 | 4 | EWC covered; MAML/NAS/federated untested → biggest real gap |
| logging | **none (zero-direct)** | 84 | 0 | 0 | trivial; transitive only |
| mapek | test_everlasting (shared) | 86 | 0 | 1 | dict-item annotation smell, flagged |
| market | test_ecosystem (shared) | 98 | 0 | 0 |  |
| mcp | 7 files (30+) | 68 | 17 | 2 | re-exports added to `__all__` P17; transports/HTTP paths thin |
| mlops | test_v6_hyper (shared) | 94 | 1 | 0 |  |
| morph | test_morph (9) | 91 | 5 | 4 | union-attr None-deref reviewed safe (P17) |
| network | 8 files (25+) | 69 | 2 | 8 | primary-var now logged (P17); transport/tcp thin |
| neural | test_nervous (3, shared) | 99 | 1 | 1 |  |
| neuromorphic | **none (zero-direct)** | 22 | 0 | 9 | least-tested dynamics in tree; has-type noise + union-attr smell |
| observability | test_v6_hyper (shared) | 83 | 1 | 0 |  |
| orchestration | test_v6_hyper (shared) | 91 | 2 | 0 |  |
| persistence | test_v6_hyper (shared) | 83 | 2 | 3 | exit-return annotation (cosmetic) |
| plugins | test_v6_hyper (shared) | 90 | 0 | 0 |  |
| precog | test_nervous (shared) | 91 | 1 | 0 |  |
| privacy | test_ecosystem (shared) | 97 | 0 | 0 |  |
| protocol0 | 9 files (30+) | 87 | 5 | 5 |  |
| provenance | test_morph/v6_hyper (shared) | 94 | 0 | 0 |  |
| quantum | 12 files (40+) | 57 | 17 | 21 | biggest package; sim-heavy paths (topological/metrology) thin; stale ignores fixed P17 |
| recovery | test_frontier (shared) | 95 | 0 | 0 | B011→pytest.raises fixed P17 |
| redteam | test_everlasting (shared) | 97 | 1 | 0 |  |
| resilience | test_v6_hyper (shared) | 80 | 1 | 0 |  |
| rollout | test_mesh (shared) | 65 | 0 | 0 | rollback paths thin |
| security | test_v6_hyper (shared) | 66 | 4 | 0 | pqc seed annotation fixed P17 (was 1) |
| semantic | test_ecosystem (shared) | 92 | 0 | 0 |  |
| streaming | test_v6_hyper (shared) | 100 | 0 | 0 |  |
| supply | **none (zero-direct)** | 92 | 0 | 0 | transitive only (via mcp fabric); factual inventory, low risk |
| tenancy | test_v6_hyper (shared) | 89 | 0 | 0 |  |
| twin | test_frontier (shared) | 100 | 0 | 0 |  |
| verify | test_everlasting (shared) | 91 | 2 | 0 |  |
| causal | test_frontier (shared) | 90 | 0 | 0 |  |
| config | test_v6_hyper (shared) | 85 | 3 | 1 |  |
| constants | **none (zero-direct)** | 100 | 0 | 0 | constants; nothing to test |
| court | test_ecosystem (shared) | 98 | 0 | 0 |  |
| economy | test_frontier (shared) | 90 | 1 | 0 |  |
| framework | 9 files (40+) | 61 | 6 | 2 | demo/CLI paths thin; arg-type smells, flagged |
| health | test_mesh (5, shared) | 54 | 0 | 0 | CLI probe paths mostly untested |
| __init__ (top) | — (imported by all) | 100 | 0 | 0 | **Envelope collision FIXED P17** (treasury alias) |
| __main__ (CLI) | phase11 (3) | 53 | 3 | 0 | most subcommands untested |

Zero-direct-coverage packages (7): cybernetics, data, logging,
neuromorphic, supply, version, constants. Of these, only neuromorphic
(22%), cybernetics (49%), and data (61%) matter — the rest are trivial
or transitively saturated. All 7 were already poor-fit in
`docs/AIKERNEL_AUDIT.md`; poor-fit for unification ≠ no tests needed,
and this table is the receipt for that distinction.

## Debt profile (ruff 2267 → 168; what actually happened)

- UP006 + UP035 + UP045 + UP037 + UP007: **bulk-fixed** (repo-wide
  `--fix`, then the FULL suite as regression check — green). Annotation
  and import modernization only; no logic touched. This was the 1700-site
  item the plan originally deferred; the suite made it safe to take.
- 199 F401 + 39 I001 + 4 B011: **fixed to zero** (auto + manual, incl. 10
  re-exports added to `__all__` and the `inverse_qft` phantom export).
- 19 F841: **triaged individually, not bulk-fixed** — most were dead
  aliases (deleted), but the pass found real issues (below).
- Remaining ~168: B905×46, SIM105×19, E701/E702 (one-liners), E741×13,
  B007×11, N-rules (naming churn) — style-level backlog, explicitly
  NOT swept (see backlog).

## Real bugs found by this pass (full weight)

1. **`eci.Envelope` silently rebound (export table)** — treasury's
   `Envelope` overwrote the signed-transport `Envelope` in
   `src/eci/__init__.py` (mypy `[assignment]`). Fixed: canonical name
   kept for transport, treasury uses `TreasuryEnvelope`. No in-repo
   consumer used the wrong one (verified by search).
2. **Phantom export `inverse_qft`** (`quantum/algorithms.py` `__all__`,
   F822) — never defined anywhere in the repo; inverse QFT is
   `qft(..., inverse=True)`. Removed from `__all__`.
3. **`protected_ratio` computed and dropped** (`quantum_mind.py`) —
   now returned as `protected_ratio_or_over_t2`.
4. **PBFT `primary` computed and ignored** (`network/consensus.py`) —
   now debug-logged per round (view rotation inspectable, no API change).
5. **Decorative `seed` in `DreamConsolidator.sleep()`** — the RNG was
   constructed and never used; it now drives tie-breaks (ranking
   semantics preserved: stable sort after seeded shuffle).
6. **B023 false positive in own test** (`test_aikernel_phase14.py`) —
   analyzed (eager evaluation inside `_gate_tpm` makes it safe), then
   bound explicitly anyway; reported numbers unchanged, proving the analysis.
7. **Stale `_phi_side` docstring** (`iit4.py`) described a partition
   scheme the code no longer implements — rewritten to match.

## mypy profile (72 errors / 33 files, down from 76)

Mostly arg-type (20) + union-attr (14) annotation debt. Reviewed
individually: morph/graph None-deref provably safe (adjacency built
from the same edge set); neuromorphic has-type is torch-inference
noise; persistence exit-return and mapek dict-item are cosmetic.
Fixed: Envelope collision, pqc seed, 2 stale ignores.

## Follow-up backlog (usable, not a gesture)

1. ~~UP006/UP035 bulk modernization~~ DONE this phase (see debt profile
   above): 2267 → 168 findings with the full suite green throughout.
   Remaining bulk-ish item: none at this scale; leftovers are listed below.
2. **learning coverage (41%)**: MAML/NAS/federated have no direct
   tests; EWC is covered. Highest-value test gap in the tree.
3. **neuromorphic (22%, zero-direct)**: least-tested dynamics; needs
   at least a smoke harness before any claim is made about it.
4. **__main__ CLI (53%) / framework demo paths (61%)**: most
   subcommands untested; a CLI smoke matrix (one --help + one run per
   subcommand) is cheap and missing.
5. **mypy arg-type/union-attr debt** (34 across quantum/consciousness/
   network): annotate hot paths first (statevector, consensus, iit),
   not the whole tree at once.
6. **E741/B007/E701 style residue**: mechanical, low value alone —
   fold into whichever PR touches those files next (boy-scout rule),
   don't schedule alone.

## CI gate decision (§4)

Retroactive full-tree gating was rejected: 1959 ruff findings and 72
mypy errors cannot go green without the disruptive clean sweep this
phase deliberately avoided. Instead, `tests/test_repo_hygiene.py`
ratchets what Phase 17 actually cleaned:
- F401 + I001 + B011 must stay at **zero** repo-wide (fails on any return).
- mypy total must stay **≤ 72** (fixes just work; growth fails).
New debt is gated; old debt is listed above with owners-by-package.
The pre-existing `ruff check src tests` CI step cannot pass as written
— recommend scoping it to this ratchet test until backlog item 1 lands.
