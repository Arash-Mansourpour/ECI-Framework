"""BrainMesh: the whole ECI framework thinking as one brain.

Each of the 8 ECI subsystems is a cortical region (neural population):
  quantum->sensory input, consciousness->prefrontal, governance->cingulate,
  memory->hippocampus, market->striatum (value), immune->amygdala (threat),
  federation->corpus-callosum (binding), cognition->parietal (integration)

One tick:
  1. subsystems report state -> normalized currents (subsystem adapter)
  2. event-driven spiking rollout (T ms, sparse: silent regions cost ~0)
  3. local STDP + metaplasticity on every spike (Loihi-style, no backprop)
  4. region salience = firing rate -> predictive GNW ignition
  5. broadcast (third factor) gates next plasticity + modulates currents

Also a StateContributor: free_energy_contribution() = workspace F, so the
brain's surprise is priced in the unification ledger (aikernel).
"""

from __future__ import annotations

from typing import Any

import torch

from eci.brain.connectome import REGIONS, Connectome
from eci.brain.neuron import BrainNeuron
from eci.brain.synapse import PlasticSynapse
from eci.brain.workspace import BrainWorkspace

__all__ = ["BrainMesh", "REGION_TO_SUBSYSTEM", "build_default_mesh"]

REGION_TO_SUBSYSTEM = {
    "quantum": "quantum_sim",
    "consciousness": "consciousness_analyzer",
    "governance": "dao",
    "memory": "agents",
    "market": "market_commons",
    "immune": "immune",
    "federation": "network_manager",
    "cognition": "cognition",
}


def _encode_subsystem(name: str, snapshot: dict[str, float]) -> float:
    """Map heterogeneous subsystem health into salience current in [0, 2]."""
    if name == "quantum":
        return min(2.0, max(0.0, snapshot.get("entanglement", 0.5) + snapshot.get("coherence", 0.5)))
    if name == "consciousness":
        return min(2.0, max(0.0, snapshot.get("phi", 0.3) + snapshot.get("awareness", 0.3)))
    if name == "governance":
        return min(2.0, max(0.0, 1.0 - snapshot.get("risk", 0.3) + 0.4 * snapshot.get("participation", 0.5)))
    if name == "memory":
        return min(2.0, max(0.0, snapshot.get("recall", 0.5) + 0.5 * snapshot.get("novelty", 0.3)))
    if name == "market":
        return min(2.0, max(0.0, snapshot.get("confidence", 0.5) + snapshot.get("liquidity", 0.4)))
    if name == "immune":
        return min(2.0, max(0.0, snapshot.get("threat", 0.4) + 0.5))
    if name == "federation":
        return min(2.0, max(0.0, snapshot.get("peers", 0.5) + snapshot.get("quorum", 0.5)))
    if name == "cognition":
        return min(2.0, max(0.0, snapshot.get("coherence", 0.5) + snapshot.get("forecast", 0.4)))
    return 0.5


class BrainMesh:
    name = "brain-mesh"

    def __init__(self, per_region: int = 8, ticks: int = 32, seed: int = 0,
                 beta: float = 6.0, theta: float = 0.08) -> None:
        self.per_region = per_region
        self.ticks = ticks
        self.seed = seed
        self.connectome = Connectome(per_region=per_region, seed=seed)
        self.workspace = BrainWorkspace(n_regions=len(REGIONS), beta=beta, theta=theta)
        # one population per region; 20% of regions inhibitory-led (immune, governance)
        self.populations: dict[str, BrainNeuron] = {}
        for i, r in enumerate(REGIONS):
            exc = r not in ("immune", "governance")
            self.populations[r] = BrainNeuron(per_region, excitatory=exc, seed=seed + i + 1)
        self.synapse = PlasticSynapse(self.connectome.n, self.connectome.n, seed=seed + 99)
        # mirror connectome sparsity into plastic weights
        with torch.no_grad():
            self.synapse.w = (self.connectome.w.clone())
        self.currents = torch.zeros(self.connectome.n)
        self.last_spikes = torch.zeros(self.connectome.n)
        self.last_ignition: dict[str, Any] = {"ignited": False, "broadcast": 0.0}
        self.cycles = 0
        self.total_spikes = 0
        self.total_plasticity = 0.0

    # -- aikernel StateContributor contract --
    def posterior(self) -> torch.Tensor:
        return self.last_spikes.clone()

    def update(self, data: Any = None) -> None:
        snap = data if isinstance(data, dict) else {}
        self.sense(snap)

    def free_energy_contribution(self) -> torch.Tensor:
        f = float(self.last_ignition.get("free_energy", 0.0) or 0.0)
        return torch.tensor(f)

    # -- core loop --
    def sense(self, snapshot: dict[str, dict[str, float]] | dict[str, float]) -> dict[str, Any]:
        """One brain cycle: encode -> spike -> plasticize -> ignite -> broadcast."""
        # 1. encode per-region drive
        drive = torch.zeros(self.connectome.n)
        for i, r in enumerate(REGIONS):
            sub = snapshot.get(r, {}) if isinstance(snapshot.get(r, {}), dict) else {}
            if not sub and r not in snapshot:
                # flat snapshot fallback: same value everywhere
                drive_raw = snapshot.get("drive", 0.6)
                val = float(drive_raw) if isinstance(drive_raw, (int, float)) else 0.6
            else:
                val = _encode_subsystem(r, sub if isinstance(sub, dict) else {})
            drive[i * self.per_region:(i + 1) * self.per_region] = val
        # global modulation from last broadcast (Dehaene descending projections)
        mod = 1.0 + 0.5 * float(self.last_ignition.get("broadcast", 0.0) or 0.0)
        drive = drive * mod
        self.currents = drive
        # 2. event-driven spiking rollout
        spikes_sum = torch.zeros(self.connectome.n)
        plast = 0.0
        for _ in range(self.ticks):
            # per-population integration
            pop_spikes = []
            for i, r in enumerate(REGIONS):
                seg = drive[i * self.per_region:(i + 1) * self.per_region]
                # recurrent input from connectome projection of last spikes
                # (weak 0.12 gain: long-range modulates, never washes out drive —
                #  preserves focused vs diffuse distinction for GNW ignition)
                rec = (self.last_spikes.abs() @ self.connectome.w)
                seg_total = seg + 0.12 * rec[i * self.per_region:(i + 1) * self.per_region]
                pop_spikes.append(self.populations[r].step(seg_total))
            whole = torch.cat(pop_spikes)
            spikes_sum = spikes_sum + whole.abs()
            # sparse long-range delivery (only if any spike: event-driven)
            if whole.abs().sum() > 0:
                _ = self.synapse.forward(whole)
                plast += self.synapse.stdp(whole, whole,
                                           mod=0.5 + float(self.last_ignition.get("broadcast", 0.0) or 0.0))
            self.last_spikes = whole
        self.total_spikes += int(spikes_sum.sum().item())
        self.total_plasticity += plast
        # 3. salience = max-normalized firing rate (scale-invariant competition:
        #    focused coalition -> winner ~1.0 -> ignition; diffuse -> uniform -> subliminal)
        rates = (spikes_sum.reshape(len(REGIONS), self.per_region).mean(dim=1) / max(1, self.ticks))
        peak = float(rates.max().item())
        if peak > 1e-9:
            salience = (rates / peak).clamp(0.0, 1.0)
        else:
            salience = rates.clamp(0.0, 1.0)
        # 4. predictive workspace ignition + broadcast
        ign = self.workspace.cycle(salience)
        self.last_ignition = dict(ign)
        self.cycles += 1
        per_tick_sparsity = float((self.last_spikes.abs() == 0).float().mean().item())
        return {"salience": {r: round(float(salience[i].item()), 4) for i, r in enumerate(REGIONS)},
                "ignited": bool(ign["ignited"]), "broadcast": round(float(ign["broadcast"]), 4),
                "winner": REGIONS[int(ign["winner"])],
                "spikes": int(spikes_sum.sum().item()),
                "plasticity": round(plast, 6),
                "sparsity": round(per_tick_sparsity, 4)}

    def adapt_structure(self, seed: int | None = None) -> dict[str, int]:
        """Neurogenesis/pruning pass driven by population firing rates."""
        rates = []
        for r in REGIONS:
            pop = self.populations[r]
            rates.extend([pop.spike_count / max(1, pop.steps)] * self.per_region)
        out = self.connectome.prune_and_grow(torch.tensor(rates, dtype=torch.float32),
                                             seed=self.cycles if seed is None else seed)
        # keep plastic weights in sync with structural mask
        with torch.no_grad():
            self.synapse.w[self.connectome.w == 0] = 0.0
        return out

    def sparsity(self) -> float:
        fired = (self.last_spikes.abs() > 0).float().mean().item()
        return 1.0 - fired

    def health(self) -> dict[str, Any]:
        return {"ok": True, "cycles": self.cycles, "total_spikes": self.total_spikes,
                "sparsity": round(self.sparsity(), 4),
                "ignition_rate": round(self.workspace.ignition_rate(), 4),
                "reportability": round(self.workspace.reportability(), 4),
                "plasticity_updates": self.synapse.updates,
                "connectome": self.connectome.to_dict(),
                "last": {k: v for k, v in self.last_ignition.items() if k != "probabilities"}}

    def to_dict(self) -> dict[str, Any]:
        return self.health()


def build_default_mesh(seed: int = 0) -> BrainMesh:
    return BrainMesh(seed=seed)
