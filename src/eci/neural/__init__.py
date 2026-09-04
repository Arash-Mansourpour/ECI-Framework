"""Neural cortex: one learned substrate for the whole architecture.

Today every subsystem scores in isolation (awareness here, risk there,
reputation elsewhere). The cortex fuses them: agents become graph nodes
with rich features, edges carry interaction trust, a message-passing GNN
reads the mesh state, and a temporal world-model predicts the collective
future under candidate policies. advise() returns one decision-ready
struct: risk per agent, collective forecast, and the recommended gate.
Pure torch, no new dependencies;abler on CPU for edge profiles.
"""

from eci.neural.graph import MeshGraph, build_graph, gnn_step
from eci.neural.world import WorldModel, rollout as world_rollout
from eci.neural.cortex import Cortex, advise

__all__ = ["MeshGraph", "build_graph", "gnn_step", "WorldModel", "world_rollout", "Cortex", "advise"]
