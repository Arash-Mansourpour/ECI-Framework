# Contributing to ECI Framework

Two kinds of PRs. Say which one yours is in the title: `[hardening]` or `[feature]`.

## Hardening PRs (debt paydown, refactors, test/repo hygiene)

- No version bump. No new capability.
- Before/after evidence required (numbers, logs, or screenshots).
- Hygiene gate green: ruff F401/I001/B011 zero, mypy ratchet ≤66 does not grow.

## Feature PRs (new capability)

- Arch fitness green (no new violations).
- Docs updated (README / module docs as applicable).
- Honesty-ledger updated (no silent capability claims).
- New tests with real asserts (no vacuous `assert True`).

## How to run checks (Windows PowerShell)

```powershell
$env:PYTHONPATH="src"; python -m pytest -q
python -m ruff check --select F401,I001,B011 src tests
python -m mypy src/eci
```

Version is single-source: `src/eci/version.py` (`__version__`).
Do not bump versions in hardening PRs. Do not use tokens in CI.
