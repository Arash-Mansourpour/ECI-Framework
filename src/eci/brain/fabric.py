"""Optional neural fabric connecting live ECI subsystems.

The existing BrainMesh remains the global-workspace/cortical layer. This
module adds a sparse, dynamically registered population where framework
components and event sources become peripheral neural nodes. It communicates
over the existing EventBus and observes components through read-only health
adapters; it does not mutate subsystem state.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from eci.brain.connectome import REGIONS
from eci.brain.mesh import BrainMesh
from eci.kernel.bus import Event, EventBus, Subscription

__all__ = ["SubsystemNeuralFabric", "infer_region"]


_RISK_KEYS = {"risk", "threat", "errors", "failures", "denied", "dlq_depth", "dropped"}
_QUALITY_KEYS = {
    "ok", "healthy", "health", "availability", "confidence", "coherence", "quorum",
    "accuracy", "score", "quality", "recall", "adherence", "coverage", "success_rate",
}
_IGNORE_KEYS = {"version", "timestamp", "ts", "uptime_s", "duration_s", "name", "node"}


def infer_region(name: str) -> str:
    """Map component names onto one of the eight stable macro-regions."""
    value = name.lower().replace("-", "_").replace(".", "_")
    rules = (
        (("quantum", "qec", "qnn", "qft"), "quantum"),
        (("conscious", "iit", "gnwt", "fep", "awareness", "fcl", "calibration"), "consciousness"),
        (("govern", "dao", "authz", "court", "treasury", "futura", "sortition", "constitution"), "governance"),
        (("agent", "memory", "persistence", "continuum", "data", "repository"), "memory"),
        (("market", "economy", "forecaster", "energy"), "market"),
        (("immune", "security", "secret", "pqc", "redteam", "challenger", "precog"), "immune"),
        (("network", "federation", "transport", "mcp", "stream", "channel", "gossip"), "federation"),
    )
    for tokens, region in rules:
        if any(token in value for token in tokens):
            return region
    return "cognition"


@dataclass
class _Neuron:
    name: str
    region: str
    observe: Callable[[], Any] | None = None
    membrane: float = 0.0
    activation: float = 0.0
    spike_rate: float = 0.0
    event_drive: float = 0.0
    last_spike: bool = False
    last_error: str = ""


class SubsystemNeuralFabric:
    """Sparse, adaptive message-passing network around the existing BrainMesh.

    Nodes can be registered as live components or appear automatically as
    EventBus publishers. Hebbian updates are bounded and local to the fabric;
    downstream effects are advisory ``brain.subsystem.signal`` events.
    """

    name = "subsystem-neural-fabric"

    def __init__(self, brain: BrainMesh, bus: EventBus | None = None,
                 seed: int = 0, max_nodes: int = 512, event_decay: float = 0.8,
                 learning_rate: float = 0.01) -> None:
        if max_nodes < 1:
            raise ValueError("max_nodes must be positive")
        if not 0.0 <= event_decay < 1.0:
            raise ValueError("event_decay must be in [0, 1)")
        if not math.isfinite(learning_rate) or learning_rate < 0:
            raise ValueError("learning_rate must be finite and non-negative")
        self.brain = brain
        self.bus = bus
        self.seed = seed
        self.max_nodes = max_nodes
        self.event_decay = event_decay
        self.learning_rate = learning_rate
        self.nodes: dict[str, _Neuron] = {}
        self.weights: dict[tuple[str, str], float] = {}
        self.cycles = 0
        self.event_count = 0
        self.spikes = 0
        self.plasticity_updates = 0
        self._rng = random.Random(seed)
        self._subscription: Subscription | None = None
        if bus is not None:
            self._subscription = bus.subscribe("*", self._observe_event, name=self.name)

    def register(self, name: str, region: str | None = None,
                 observe: Callable[[], Any] | None = None) -> bool:
        """Register/update a read-only node; returns whether it was newly added."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("subsystem name must not be empty")
        selected_region = region or infer_region(clean_name)
        if selected_region not in REGIONS:
            raise ValueError(f"unknown macro-region {selected_region!r}")
        existing = self.nodes.get(clean_name)
        if existing is not None:
            existing.region = selected_region
            if observe is not None:
                existing.observe = observe
            return False
        if len(self.nodes) >= self.max_nodes:
            raise ValueError(f"neural fabric node limit reached ({self.max_nodes})")
        neuron = _Neuron(name=clean_name, region=selected_region, observe=observe)
        previous = list(self.nodes.values())
        self.nodes[clean_name] = neuron
        for other in previous:
            probability = 0.28 if other.region == selected_region else 0.07
            if self._rng.random() < probability:
                self._add_edge(other.name, clean_name)
                self._add_edge(clean_name, other.name)
        # A reciprocal low-gain backbone prevents disconnected islands while
        # random lateral/cross-region links keep the graph sparse.
        if previous:
            neighbor = previous[-1].name
            self.weights.setdefault((neighbor, clean_name), 0.08)
            self.weights.setdefault((clean_name, neighbor), 0.08)
        return True

    def unregister(self, name: str) -> bool:
        if name not in self.nodes:
            return False
        del self.nodes[name]
        self.weights = {edge: weight for edge, weight in self.weights.items()
                        if name not in edge}
        return True

    def register_components(self, components: Mapping[str, Any],
                            regions: Mapping[str, str] | None = None) -> int:
        """Attach framework objects through health/to_dict read adapters."""
        added = 0
        regions = regions or {}
        for name, component in components.items():
            if component is None:
                continue
            observe = lambda component=component: self._component_snapshot(component)
            added += int(self.register(name, regions.get(name), observe))
        return added

    def _component_snapshot(self, component: Any) -> Any:
        for method_name in ("health", "to_dict"):
            reporter = getattr(component, method_name, None)
            if callable(reporter):
                return reporter()
        return {"ok": True, "component_type": type(component).__name__}

    def _add_edge(self, source: str, target: str) -> None:
        if source == target or (source, target) in self.weights:
            return
        sign = -1.0 if self._rng.random() < 0.12 else 1.0
        self.weights[(source, target)] = sign * (0.08 + 0.22 * self._rng.random())

    def _observe_event(self, event: Event) -> None:
        if event.type.startswith("brain."):
            return
        source = event.source.strip() if event.source else ""
        if not source or source == "unknown":
            source = event.type.split(".", 1)[0]
        if not source or source == "brain-neural-fabric":
            return
        self.register(source)
        node = self.nodes[source]
        payload = event.payload if isinstance(event.payload, dict) else {}
        if payload.get("ok") is False or any(key in payload for key in ("error", "exception")):
            intensity = 1.0
        else:
            numeric = [abs(float(v)) for v in payload.values()
                       if isinstance(v, (int, float)) and not isinstance(v, bool)
                       and math.isfinite(float(v))]
            intensity = min(1.0, 0.25 + (max(numeric) / (1.0 + max(numeric)) if numeric else 0.0))
        node.event_drive = max(node.event_drive, intensity)
        self.event_count += 1

    @staticmethod
    def _flatten(value: Any, prefix: str = "", depth: int = 0,
                 visited: set[int] | None = None) -> list[tuple[str, float | bool]]:
        out: list[tuple[str, float | bool]] = []
        if isinstance(value, Mapping):
            if depth >= 8:
                return out
            visited = visited if visited is not None else set()
            if id(value) in visited:
                return out
            visited.add(id(value))
            for index, (key, item) in enumerate(value.items()):
                if index >= 256:
                    break
                name = f"{prefix}_{key}".lower().replace("-", "_") if prefix else str(key).lower()
                out.extend(SubsystemNeuralFabric._flatten(item, name, depth + 1, visited))
        elif isinstance(value, bool):
            out.append((prefix, value))
        elif isinstance(value, (int, float)) and math.isfinite(float(value)):
            out.append((prefix, float(value)))
        return out

    @classmethod
    def _health_drive(cls, report: Any, event_drive: float = 0.0) -> float:
        values = cls._flatten(report)
        if not values:
            base = 0.25
        else:
            fields = dict(values)
            base = 0.65 if fields.get("ok", fields.get("healthy")) is True else (
                0.12 if fields.get("ok", fields.get("healthy")) is False else 0.35
            )
            positive: list[float] = []
            risk: list[float] = []
            for key, value in values:
                short_key = key.rsplit("_", 1)[-1]
                if isinstance(value, bool) or short_key in _IGNORE_KEYS:
                    continue
                number = float(value)
                if short_key in _RISK_KEYS:
                    risk.append(min(1.0, abs(number) / (1.0 + abs(number))))
                elif short_key in _QUALITY_KEYS:
                    if short_key in {"health", "availability", "confidence", "coherence",
                                     "quorum", "accuracy", "score", "quality", "recall",
                                     "adherence", "coverage", "success_rate"}:
                        positive.append(min(1.0, max(0.0, number)))
                elif short_key in {"activity", "load", "calls", "cycles", "events", "spikes"}:
                    positive.append(min(1.0, abs(number) / (1.0 + abs(number))))
            if positive:
                base = 0.5 * base + 0.5 * (sum(positive) / len(positive))
            if risk:
                base *= 1.0 - 0.5 * (sum(risk) / len(risk))
        return min(1.0, max(0.0, 0.85 * base + 0.15 * event_drive))

    @staticmethod
    def _macro_snapshot(drives: Mapping[str, float]) -> dict[str, dict[str, float]]:
        grouped: dict[str, list[float]] = {region: [] for region in REGIONS}
        for name, value in drives.items():
            region = infer_region(name.split(":", 1)[-1])
            grouped[region].append(value)
        score = {region: sum(vals) / len(vals) if vals else 0.5
                 for region, vals in grouped.items()}
        return {
            "quantum": {"entanglement": score["quantum"], "coherence": score["quantum"]},
            "consciousness": {"phi": score["consciousness"], "awareness": score["consciousness"]},
            "governance": {"risk": 1.0 - score["governance"], "participation": score["governance"]},
            "memory": {"recall": score["memory"], "novelty": 0.2 * score["memory"]},
            "market": {"confidence": score["market"], "liquidity": 0.25 * score["market"]},
            "immune": {"threat": 1.0 - score["immune"]},
            "federation": {"peers": score["federation"], "quorum": 0.5 * score["federation"]},
            "cognition": {"coherence": score["cognition"], "forecast": 0.2 * score["cognition"]},
        }

    def tick(self, snapshot: Mapping[str, Any] | None = None,
             components: Mapping[str, Any] | None = None,
             regions: Mapping[str, str] | None = None) -> dict[str, Any]:
        """Assimilate component health/events, spike, learn, and broadcast signals."""
        if components:
            self.register_components(components, regions)
        if snapshot:
            for name, value in snapshot.items():
                if name in REGIONS and isinstance(value, Mapping):
                    self.register(f"input:{name}", name)
                elif isinstance(value, Mapping):
                    self.register(name)

        drives: dict[str, float] = {}
        for name, node in self.nodes.items():
            try:
                if node.observe is not None:
                    report = node.observe()
                elif snapshot is not None and name in snapshot:
                    report = snapshot[name]
                elif snapshot is not None and name.startswith("input:"):
                    report = snapshot.get(name.split(":", 1)[1], {})
                else:
                    report = {"activity": node.event_drive}
                node.last_error = ""
            except Exception as exc:  # noqa: BLE001
                report = {"ok": False}
                node.last_error = type(exc).__name__
            try:
                drives[name] = self._health_drive(report, node.event_drive)
            except Exception as exc:  # noqa: BLE001
                node.last_error = type(exc).__name__
                drives[name] = 0.0

        macro_snapshot: dict[str, Any]
        if snapshot is not None and set(REGIONS).intersection(snapshot):
            macro_snapshot = {key: value for key, value in snapshot.items()
                              if key in REGIONS and isinstance(value, Mapping)}
        else:
            macro_snapshot = self._macro_snapshot(drives)
        global_out = self.brain.sense(macro_snapshot)
        regional = global_out.get("salience", {})
        previous = {name: node.activation for name, node in self.nodes.items()}
        incoming_by_target: dict[str, list[tuple[str, float]]] = {name: [] for name in self.nodes}
        for (source, target), weight in self.weights.items():
            if source in previous and target in incoming_by_target:
                incoming_by_target[target].append((source, weight))
        next_activity: dict[str, float] = {}
        next_spikes: dict[str, bool] = {}
        for name, node in self.nodes.items():
            incident = incoming_by_target[name]
            denom = sum(abs(weight) for _, weight in incident)
            recurrent = (sum(previous[source] * weight for source, weight in incident) / denom
                         if denom else 0.0)
            attention = float(regional.get(node.region, 0.0))
            membrane = (0.55 * node.membrane + 0.48 * drives[name]
                        + 0.22 * recurrent + 0.16 * attention
                        + 0.12 * float(global_out.get("broadcast", 0.0))
                        + 0.14 * node.event_drive)
            membrane = min(1.5, max(0.0, membrane))
            threshold = 0.78 + 0.18 * node.spike_rate
            spike = membrane >= threshold
            activation = 1.0 if spike else min(1.0, membrane)
            node.membrane = 0.0 if spike else membrane
            node.spike_rate = 0.9 * node.spike_rate + 0.1 * float(spike)
            node.last_spike = spike
            next_activity[name] = activation
            next_spikes[name] = spike
            node.event_drive *= self.event_decay

        modulation = 0.25 + float(global_out.get("broadcast", 0.0))
        if self.learning_rate:
            for edge, weight in list(self.weights.items()):
                source, target = edge
                pre, post = next_spikes[source], next_spikes[target]
                if pre and post:
                    delta = self.learning_rate * modulation
                elif pre != post:
                    delta = -0.2 * self.learning_rate
                else:
                    continue
                self.weights[edge] = min(1.0, max(-1.0, weight + delta))
                self.plasticity_updates += 1
        for name, activation in next_activity.items():
            self.nodes[name].activation = activation
        self.cycles += 1
        spike_names = [name for name, spike in next_spikes.items() if spike]
        self.spikes += len(spike_names)

        if self.bus is not None:
            for name, node in self.nodes.items():
                self.bus.publish(Event(
                    type="brain.subsystem.signal",
                    source=self.name,
                    payload={"subsystem": name, "region": node.region,
                             "attention": round(next_activity[name], 6),
                             "spike": next_spikes[name],
                             "broadcast": float(global_out.get("broadcast", 0.0)),
                             "cycle": self.cycles},
                ))
            self.bus.publish(Event(
                type="brain.fabric.broadcast", source=self.name,
                payload={"cycle": self.cycles, "nodes": len(self.nodes),
                         "spikes": len(spike_names),
                         "winner": global_out.get("winner"),
                         "broadcast": float(global_out.get("broadcast", 0.0))},
            ))

        return {**global_out,
                "fabric": self.health(),
                "active_subsystems": sorted(name for name, value in next_activity.items()
                                             if value >= 0.2),
                "spiking_subsystems": spike_names,
                "component_errors": {name: node.last_error for name, node in self.nodes.items()
                                     if node.last_error}}

    def health(self) -> dict[str, Any]:
        node_count = len(self.nodes)
        possible = node_count * max(0, node_count - 1)
        counts = {region: sum(node.region == region for node in self.nodes.values())
                  for region in REGIONS}
        top = sorted(self.nodes.values(), key=lambda node: node.activation, reverse=True)[:8]
        components = self._weak_components()
        strong_edges = sorted(self.weights.items(), key=lambda item: abs(item[1]), reverse=True)[:12]
        return {"ok": True, "cycles": self.cycles, "nodes": node_count,
                "connections": len(self.weights),
                "connectivity": len(self.weights) / possible if possible else 0.0,
                "weakly_connected_components": components,
                "region_counts": counts, "event_count": self.event_count,
                "spikes": self.spikes, "plasticity_updates": self.plasticity_updates,
                "strongest_connections": [{"source": source, "target": target,
                                            "weight": round(weight, 6)}
                                           for (source, target), weight in strong_edges],
                "top_active": [{"name": node.name, "region": node.region,
                                "activation": round(node.activation, 6),
                                "spike_rate": round(node.spike_rate, 6)} for node in top]}

    def _weak_components(self) -> int:
        adjacency: dict[str, set[str]] = {name: set() for name in self.nodes}
        for source, target in self.weights:
            adjacency[source].add(target)
            adjacency[target].add(source)
        unseen = set(adjacency)
        count = 0
        while unseen:
            count += 1
            stack = [unseen.pop()]
            while stack:
                current = stack.pop()
                neighbors = adjacency[current] & unseen
                unseen.difference_update(neighbors)
                stack.extend(neighbors)
        return count

    def topology(self) -> dict[str, Any]:
        """Return a JSON-safe full node/edge snapshot for graph visualization."""
        return {
            "seed": self.seed,
            "nodes": [{"name": node.name, "region": node.region,
                       "activation": round(node.activation, 6),
                       "spike_rate": round(node.spike_rate, 6)}
                      for node in self.nodes.values()],
            "edges": [{"source": source, "target": target,
                       "weight": round(weight, 6),
                       "polarity": "inhibitory" if weight < 0 else "excitatory",
                       "kind": "lateral" if self.nodes[source].region == self.nodes[target].region
                       else "cross-region"}
                      for (source, target), weight in sorted(self.weights.items())],
        }

    def to_dict(self) -> dict[str, Any]:
        return self.health()

    def close(self) -> None:
        if self.bus is not None and self._subscription is not None:
            self.bus.unsubscribe(self._subscription)
            self._subscription = None
