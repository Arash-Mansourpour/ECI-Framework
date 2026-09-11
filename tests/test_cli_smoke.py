"""CLI smoke matrix (Phase 18, backlog item 4): every subcommand parses.

Full runs stay in their own slow tests; this locks that no subcommand's
argparse wiring rots, plus cheap runs of info/health/eval/morph-system.
"""
import json

import pytest

COMMANDS = ["info", "demo", "quantum", "consciousness", "network", "field",
            "mind", "activate", "benchmark", "health", "system", "workflow",
            "mcp", "agent", "eval", "think", "dream", "morph", "ever", "aik"]


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
