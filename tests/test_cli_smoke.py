"""CLI smoke matrix (Phase 18, backlog item 4): every subcommand parses.

Full runs stay in their own slow tests; this locks that no subcommand's
argparse wiring rots, plus cheap runs of info/health/eval/morph-system.
"""
import json

import pytest

COMMANDS = ["info", "demo", "quantum", "consciousness", "network", "field",
            "mind", "activate", "benchmark", "health", "system", "workflow",
            "mcp", "agent", "eval", "think", "dream", "morph", "ever", "aik",
            "protocol", "v8", "brain"]


def test_all_subcommands_have_help():
    from eci.__main__ import build_parser
    parser = build_parser()
    for cmd in COMMANDS:
        with pytest.raises(SystemExit) as e:
            parser.parse_args([cmd, "--help"])
        assert e.value.code == 0, cmd


def test_cli_info_health_eval_run():
    import io
    from contextlib import redirect_stdout

    from eci.__main__ import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert main(["info"]) == 0
    d = json.loads(buf.getvalue())
    assert "version" in d
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert main(["health", "--once"]) == 0
    assert "ok" in json.loads(buf.getvalue())
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert main(["eval"]) == 0
    assert json.loads(buf.getvalue())["failed"] == 0


def test_cli_all_light_runs():
    """Exercise every subcommand's handler at least once (light args, no serve/block)."""
    import io
    from contextlib import redirect_stdout
    from unittest.mock import patch

    from eci.__main__ import main

    # light-run matrix: (argv, needs_patch)
    cases = [
        (["demo"], True),
        (["quantum"], True),
        (["consciousness", "--steps", "4", "--neurons", "8", "--seed", "0"], False),
        (["network", "--joins", "1", "--proposals", "1"], False),
        (["field", "--qubits", "2"], False),
        (["mind"], False),
        (["activate"], False),
        (["benchmark"], False),
        (["system"], False),
        (["workflow"], False),
        (["mcp", "--list"], False),
        (["agent", "--goal", "test", "--budget", "1", "--steps", "1"], True),
        (["think", "--goal", "act", "--stakes", "0.2", "--seed", "0"], False),
        (["dream", "--episodes", "1", "--seed", "0"], False),
        (["morph", "--steps", "1"], False),
        (["ever"], False),
        (["aik", "shares"], False),
        (["aik", "total"], False),
        (["aik", "describe"], False),
        (["protocol", "--nodes", "2"], False),
        (["v8"], False),
        (["brain", "--ticks", "8", "--cycles", "1"], False),
    ]

    # patch heavy quantum/demo suites so demo test stays fast if added later
    with patch("eci.framework.ECIFramework.run_quantum_suite", return_value={"ok": True}), \
         patch("eci.framework.ECIFramework.run_network_simulation", return_value={"ok": True}), \
         patch("eci.agents.loop.AgentLoop.run") as mock_run:
        mock_run.return_value = {"ok": True}

        for argv, _ in cases:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(argv)
            assert rc == 0, f"{argv} returned {rc}: {buf.getvalue()[:500]}"
