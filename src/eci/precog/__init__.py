"""Precog: forward-looking violation forecasting (obedience insurance).
Validation note: forecasts are heuristic (see docs/VALIDATION_STATUS.md) —
tiers are policy conventions, holds are decisions under uncertainty.

Everything else judges the past (ledger), the present (policy gates), or
reacts (immunity). Precog predicts P(violation | trajectory) from behavior
features and acts BEFORE the breach: watch -> harder challenges ->
provisional hold (releasable by fresh challenge, never silent punishment).
Biased toward caution (cheap false positives, expensive misses) and
self-correcting: every forecast + outcome updates the model by Bayes rule.
"""

from eci.precog.hold import ProvisionalHold
from eci.precog.risk import RiskEngine, RiskTier, forecast

__all__ = ["RiskEngine", "RiskTier", "forecast", "ProvisionalHold"]
