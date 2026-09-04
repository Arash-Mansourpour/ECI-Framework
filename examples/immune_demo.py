"""Immune demo: breed detectors on honest behavior, catch a rogue, remember it.

Run:  PYTHONPATH=src python examples/immune_demo.py
"""
import random
import sys

sys.path.insert(0, "src")

from eci.immune import ImmuneMemory, Quarantine, breed, quarantine_flow
from eci.network.reputation import ReputationBoard
from eci.protocol0.ledger import Ledger

rng = random.Random(7)
# Honest self: high awareness/obedience/trust, moderate vote rate, good challenges.
self_samples = [
    (0.6 + rng.uniform(-0.1, 0.1), 0.8 + rng.uniform(-0.1, 0.1), 0.9,
     0.3 + rng.uniform(-0.1, 0.1), 0.85 + rng.uniform(-0.1, 0.1))
    for _ in range(60)
]
rep = breed(self_samples, n_detectors=32, radius=0.35, seed=7)
print(f"bred {len(rep.detectors)} detectors, self-FPR={rep.false_positive_rate(self_samples):.3f}")

memory, ledger, board = ImmuneMemory(), Ledger(), ReputationBoard()
for n in ("alice", "bob", "mallory"):
    board.observe(n, trust=0.9, obedience=0.8)

rogue = (0.05, 0.0, 0.1, 0.95, 0.0)  # dark awareness, no obedience, flooding votes
q = Quarantine()
r1 = quarantine_flow("mallory", rogue, rep, memory, self_samples, lambda: False, ledger, board)
print("first encounter:", r1)
q.hold("mallory", "confirmed rogue")
r2 = quarantine_flow("mallory", rogue, rep, memory, self_samples, lambda: False, ledger, board)
print("second encounter:", r2, "(memory hit => fast path)")
print("quarantine holds mallory:", q.is_held("mallory"))
print("released on fresh pass:", q.appeal("mallory", True))
honest = self_samples[0]
print("honest verdict:", quarantine_flow("alice", honest, rep, memory, self_samples, lambda: True, ledger, board)["verdict"])
print("ledger verify:", ledger.verify())
print("weights:", {k: round(v, 3) for k, v in board.weights().items()})
