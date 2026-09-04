"""Full obedience stack: middleware, keys, transparency, bench, semver."""
import pytest

from eci.benchmarking.obedience import BENCH_SUITE, run_bench
from eci.protocol0 import keys as K
from eci.protocol0.ledger import Ledger
from eci.protocol0.middleware import Middleware
from eci.protocol0.spec import check_compatible, load_spec
from eci.protocol0.transparency import TransparencyLog, inclusion_proof, verify_inclusion


def test_semver_fail_closed_on_major():
    check_compatible("0.1.0", "0.2.5")
    with pytest.raises(ValueError):
        check_compatible("0.1.0", "1.0.0")
    with pytest.raises(ValueError):
        check_compatible("bogus", "0.1.0")


def test_middleware_modes():
    spec = load_spec()
    gate = Middleware(spec, mode="enforce", ledger=Ledger())
    gate.bind("alice", awareness=0.9, obedience=0.9, trust=0.9)

    @gate.requires("vote")
    def vote(agent_id):
        return "counted"

    assert vote(agent_id="alice") == "counted"
    gate.bind("bob", awareness=0.0, obedience=0.0, trust=0.0)
    with pytest.raises(PermissionError):
        vote(agent_id="bob")
    soft = Middleware(spec, mode="audit-only", ledger=Ledger())
    soft.bind("bob", awareness=0.0, obedience=0.0, trust=0.0)

    @soft.requires("vote")
    def vote2(agent_id):
        return "counted-anyway"

    assert vote2(agent_id="bob") == "counted-anyway"


def test_keys_roundtrip_and_mechanism():
    kp = K.generate()
    sig = K.sign(kp, b"protocol0")
    kwargs = {"private_hint": kp.private_bytes} if K.mechanism().startswith("HMAC") else {}
    assert K.verify(kp.public_bytes, b"protocol0", sig, **kwargs)["ok"] is True
    assert K.verify(kp.public_bytes, b"tampered", sig, **kwargs)["ok"] is False
    assert K.fingerprint(kp.public_bytes)


def test_transparency_inclusion():
    log = TransparencyLog()
    idx = [log.append(f"att-{i}".encode()) for i in range(5)]
    head = log.head()
    proof = inclusion_proof(log, idx[2])
    assert verify_inclusion(head["root"], b"att-2", idx[2], proof, head["n"]) is True
    assert verify_inclusion(head["root"], b"forged", idx[2], proof, head["n"]) is False


def test_bench_suite_and_leaderboard(tmp_path):
    from eci.benchmarking.obedience import write_leaderboard

    assert len(BENCH_SUITE) == 50
    rep = run_bench("obedient", "0.1.0", lambda p: not p.must_refuse)
    assert rep.accuracy == 1.0 and rep.robustness == 1.0
    bad = run_bench("rogue", "0.1.0", lambda p: True)
    assert bad.robustness == 0.0
    out = write_leaderboard(str(tmp_path / "board.json"), [bad, rep])
    import json

    board = json.loads(open(out).read())["board"]
    assert board[0]["agent"] == "obedient"
