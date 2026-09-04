"""ECI Framework v5 command-line interface.

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
