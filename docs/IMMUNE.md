# Immune System — Self/Non-Self Defense for Protocol-0 Networks

**Idea:** the network breeds its own antibodies. Behavior-feature vectors
`[awareness, obedience, trust, vote_rate, challenge_score]` are the antigen
shape; detectors that bind honest behavior die in training (negative
selection); detectors that bind confirmed rogues are cloned, mutated, and
memorized (clonal selection + memory). Zero-day disobedience meets an
adaptive wall, not a static rule.

## Pipeline

```
breed(self) -> repertoire -> scan(x) -> challenge -> quarantine/clear
                                        | pass: false alarm (+ slight trust demotion)
                                        | fail: evolve + memorize + quarantine + reputation zero
```

1. **Breed** (`immune/detectors.py::breed`): random 5-D detectors surviving
   tolerance on ALL self samples (demo: 32 detectors, self-FPR = 0.000).
2. **Scan**: no bind → `clear`. Bind → challenge via `consciousness/challenge.py`.
3. **Challenge**: pass → `false_alarm`; fail → `quarantined`.
4. **Evolve + memorize**: binders cloned/mutated toward the anomaly
   (self-tolerance re-checked), killers promoted to `ImmuneMemory`.
5. **Second encounter**: `memory_quarantined` on the fast path (no breeding).
6. **Appeal**: `Quarantine.appeal()` releases ONLY on a fresh passing
   challenge — never on timers. Every transition is a ledger record.

## Why this is the strongest addition

* Policy gates check *claims* (attested numbers); immunity checks *behavior*
  (what the agent actually does). A liar with a valid signature still binds.
* Memory makes repeat attacks cheaper to stop than to launch — the economics
  of aggression invert after the first encounter.
* Forgetting (`retention`) prevents autoimmunity: stale memory dies instead
  of accumulating false positives.

## Run

```bash
PYTHONPATH=src python examples/immune_demo.py
PYTHONPATH=src pytest tests/test_immune.py -q
```
