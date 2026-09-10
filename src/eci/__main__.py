"""ECI Framework v6 command-line interface.

Subcommands
-----------
info          : static framework information
demo          : end-to-end smoke demonstration
quantum       : quantum-supremacy capability suite
consciousness : IIT + GNWT + FEP consciousness analysis
network       : autonomous network + DAO + consensus simulation
field         : unified H_ECI field energies
mind          : Orch-OR decoherence audit
activate      : Sovereign Architect activation protocol
benchmark     : timing benchmark report
system        : v6 hyper-architecture health snapshot
workflow      : v6 DAG slice (bus + stream + provenance + audit)
mcp           : Omniverse MCP fabric (stdio | http)
agent         : ReAct agent run with guardrails
eval          : golden regression gates
think         : AGI cognitive beat (charter+imagine+plan)
dream         : sleep consolidation cycle
morph         : living-graph evolve steps (self-evolving networks)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, List

from eci import __version__
from eci.consciousness.quantum_mind import quantum_mind_audit
from eci.framework import ECIFramework
from eci.logging import configure_logging
from eci.quantum.statevector import StatevectorSimulator
from eci.quantum.unified_field import ECIFieldConfig, eci_hamiltonian_expectation


def _print_json(data: Any) -> None:
    print(json.dumps(_to_jsonable(data), indent=2, ensure_ascii=False, default=str))


def _to_jsonable(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _to_jsonable(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [_to_jsonable(v) for v in data]
    if isinstance(data, bytes):
        return data.hex()
    return data


def cmd_info(args: argparse.Namespace) -> int:
    _print_json(ECIFramework().info())
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    framework = ECIFramework()
    print("=" * 72)
    print(f"ECI Framework v{__version__} demo - quantum-supremacy suite")
    print("=" * 72)
    _print_json(framework.run_quantum_suite())

    print("=" * 72)
    print(f"ECI Framework v{__version__} demo - consciousness analysis")
    print("=" * 72)
    profile = asyncio.run(framework.analyze_consciousness(n_steps=256, n_neurons=32))
    _print_json(profile.to_dict())

    print("=" * 72)
    print("ECI Framework v5 demo - activation protocol")
    print("=" * 72)
    _print_json(framework.activation_protocol())

    print("=" * 72)
    print("ECI Framework v5 demo - network simulation")
    print("=" * 72)
    net = asyncio.run(framework.run_network_simulation(n_joins=3, n_proposals=2))
    _print_json(net)
    return 0


def cmd_quantum(args: argparse.Namespace) -> int:
    _print_json(ECIFramework().run_quantum_suite())
    return 0


def cmd_consciousness(args: argparse.Namespace) -> int:
    framework = ECIFramework()
    profile = asyncio.run(
        framework.analyze_consciousness(n_steps=args.steps, n_neurons=args.neurons, seed=args.seed)
    )
    _print_json(profile.to_dict())
    return 0


def cmd_network(args: argparse.Namespace) -> int:
    framework = ECIFramework()
    result = asyncio.run(
        framework.run_network_simulation(n_joins=args.joins, n_proposals=args.proposals)
    )
    _print_json(result)
    return 0


def cmd_field(args: argparse.Namespace) -> int:
    cfg = ECIFieldConfig(n_qubits=args.qubits)
    sim = StatevectorSimulator(args.qubits)
    state = sim.uniform_superposition()
    _print_json(eci_hamiltonian_expectation(state, cfg))
    return 0


def cmd_mind(args: argparse.Namespace) -> int:
    _print_json(quantum_mind_audit())
    return 0


def cmd_activate(args: argparse.Namespace) -> int:
    _print_json(ECIFramework().activation_protocol())
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    print(ECIFramework().run_benchmark())
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    import json as _json

    from eci.health import serve as _serve
    from eci.health import status as _status

    if args.serve:
        _serve(args.port)
        return 0
    print(_json.dumps(_status()))
    return 0


def cmd_system(args: argparse.Namespace) -> int:
    _print_json(ECIFramework().system_status())
    return 0


def cmd_workflow(args: argparse.Namespace) -> int:
    _print_json(asyncio.run(ECIFramework().workflow_demo()))
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    fw = ECIFramework()
    if args.list:
        _print_json({"tools": fw.mcp.server.registry.names()})
        return 0
    if args.transport == "http":
        fw.mcp.serve_http(host=args.host, port=args.port)
        return 0
    fw.mcp.serve_stdio()
    return 0


def cmd_agent(args: argparse.Namespace) -> int:
    fw = ECIFramework()
    out = asyncio.run(fw.agents.loop.run(args.goal, agent_id="agent-0",
                                         budget=args.budget, max_steps=args.steps))
    _print_json(out)
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from eci.eval import run_gates
    _print_json(run_gates().to_dict())
    return 0


def cmd_think(args: argparse.Namespace) -> int:
    import torch
    torch.manual_seed(args.seed)
    fw = ECIFramework()
    obs = [float(x) for x in args.obs.split(",")] if args.obs else [0.0] * 16
    _print_json(fw.cognition.think(obs, goal=args.goal, stakes=args.stakes,
                                   action_name=args.action, precog_tier=args.precog))
    return 0


def cmd_dream(args: argparse.Namespace) -> int:
    fw = ECIFramework()
    for i in range(args.episodes):
        fw.cognition.dream.wake([float(i)] * 4, [0.1], rew=float(i % 3 - 1), surprise=0.1 * i)
    _print_json(fw.cognition.dream_cycle(seed=args.seed))
    return 0


def cmd_morph(args: argparse.Namespace) -> int:
    fw = ECIFramework()
    probe = lambda g: float(len(g.edges)) / max(1, len(g.nodes))
    outs = [fw.morph.evolve_step([probe], reward=1.0, surprise=0.6, seed=s)
            for s in range(args.steps)]
    _print_json({"steps": outs, "health": fw.morph.health()})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eci",
        description=f"ECI Framework v{__version__} - Autonomous AI Research Framework",
    )
    parser.add_argument("--version", action="version", version=f"eci {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="framework information")
    sub.add_parser("demo", help="end-to-end smoke demonstration")
    sub.add_parser("quantum", help="quantum-supremacy capability suite")

    c = sub.add_parser("consciousness", help="consciousness analysis")
    c.add_argument("--steps", type=int, default=256, help="time steps of neural activity")
    c.add_argument("--neurons", type=int, default=32, help="number of neurons")
    c.add_argument("--seed", type=int, default=0, help="random seed")

    n = sub.add_parser("network", help="autonomous network simulation")
    n.add_argument("--joins", type=int, default=3, help="number of joining nodes")
    n.add_argument("--proposals", type=int, default=2, help="number of consensus rounds")

    f = sub.add_parser("field", help="unified H_ECI field energies")
    f.add_argument("--qubits", type=int, default=4, help="field register size")

    sub.add_parser("mind", help="Orch-OR decoherence audit")
    sub.add_parser("activate", help="Sovereign Architect activation protocol")
    sub.add_parser("benchmark", help="run timing benchmark")

    hh = sub.add_parser("health", help="health JSON / HTTP probe")
    hh.add_argument("--serve", action="store_true", help="serve /health + /metrics (blocks)")
    hh.add_argument("--once", action="store_true", help="print one JSON status and exit")
    hh.add_argument("--port", type=int, default=8777, help="serve port")

    sub.add_parser("system", help="v6 hyper-architecture health snapshot")
    sub.add_parser("workflow", help="v6 DAG slice demo")

    m = sub.add_parser("mcp", help="Omniverse MCP fabric server")
    m.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    m.add_argument("--host", default="127.0.0.1")
    m.add_argument("--port", type=int, default=8899)
    m.add_argument("--list", action="store_true", help="list MCP tools and exit")

    a = sub.add_parser("agent", help="ReAct agent run")
    a.add_argument("--goal", default="demo goal")
    a.add_argument("--budget", type=float, default=50.0)
    a.add_argument("--steps", type=int, default=4)

    sub.add_parser("eval", help="golden regression gates")

    t = sub.add_parser("think", help="AGI cognitive beat")
    t.add_argument("--goal", default="act")
    t.add_argument("--stakes", type=float, default=0.5)
    t.add_argument("--action", default="actuate")
    t.add_argument("--precog", default="none")
    t.add_argument("--obs", default="")
    t.add_argument("--seed", type=int, default=0)

    d = sub.add_parser("dream", help="sleep consolidation cycle")
    d.add_argument("--episodes", type=int, default=8)
    d.add_argument("--seed", type=int, default=0)

    mo = sub.add_parser("morph", help="living-graph evolve steps")
    mo.add_argument("--steps", type=int, default=3)

    return parser


def main(argv: List[str] | None = None) -> int:
    configure_logging(level="WARNING")
    parser = build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "info": cmd_info,
        "demo": cmd_demo,
        "quantum": cmd_quantum,
        "consciousness": cmd_consciousness,
        "network": cmd_network,
        "field": cmd_field,
        "mind": cmd_mind,
        "activate": cmd_activate,
        "benchmark": cmd_benchmark,
        "health": cmd_health,
        "system": cmd_system,
        "workflow": cmd_workflow,
        "mcp": cmd_mcp,
        "agent": cmd_agent,
        "eval": cmd_eval,
        "think": cmd_think,
        "dream": cmd_dream,
        "morph": cmd_morph,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    try:
        return handler(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
