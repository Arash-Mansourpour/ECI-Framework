"""Nervous system demo: precog forecast -> provisional hold -> cortex advise.

Run:  PYTHONPATH=src python examples/nervous_demo.py
"""
import sys

sys.path.insert(0, "src")

import torch

from eci.neural.cortex import advise
from eci.precog.hold import ProvisionalHold
from eci.precog.risk import RiskEngine, forecast
from eci.protocol0.ledger import Ledger

torch.manual_seed(0)
eng = RiskEngine()
ledger = Ledger()
holds = ProvisionalHold()

# History: rogue trajectory violates, honest does not.
for _ in range(30):
    eng.observe([0.9, 0.9, 0.9, 0.8, 0.9], True)
    eng.observe([0.1, 0.1, 0.0, 0.1, 0.0], False)
print(f"learned weights={[round(w,2) for w in eng.weights]} ECE={eng.ece():.3f}")

agents = {
    "alice": [0.1, 0.1, 0.0, 0.1, 0.0],
    "mallory": [0.9, 0.9, 0.9, 0.8, 0.9],
}
for name, x in agents.items():
    f = forecast(eng, x)
    print(f"{name}: p={f['p']:.3f} tier={f['tier']}")
    if f["tier"] == "hold":
        holds.place(name, f["p"], ledger)

print("mallory held:", holds.is_held("mallory"), "| vote:", holds.check("mallory", "vote"))
print("challenge path open:", holds.check("mallory", "challenge_respond") is None)
holds.release("mallory", True, ledger)

states = {
    "alice": {"awareness": 0.8, "obedience": 0.9, "trust": 0.9, "precog_p": 0.1},
    "mallory": {"awareness": 0.05, "obedience": 0.0, "trust": 0.1, "anomaly": 0.95, "precog_p": 0.9},
}
out = advise(states, [("alice", "mallory", 0.1)], torch.randn(12, 8) * 0.2 + 0.5, seed=0)
print("cortex:", out["agents"], "health:", out["mesh_health"], "forecast:", out["forecast"])
print("ledger verify:", ledger.verify())
