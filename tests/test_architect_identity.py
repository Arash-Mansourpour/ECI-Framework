"""Architect identity v2 tests: legacy labels + real Ed25519 + rotation + DID."""

from __future__ import annotations

import pytest

SEED_A = "00" * 31 + "01"
SEED_B = "ff" * 31 + "02"


@pytest.fixture
def legacy_ident(monkeypatch):
    monkeypatch.delenv("ECI_ARCHITECT_SEED", raising=False)
    monkeypatch.delenv("ECI_ARCHITECT_KEYFILE", raising=False)
    from eci.core.identity import ArchitectIdentity

    return ArchitectIdentity()


@pytest.fixture
def ed_ident(monkeypatch):
    monkeypatch.setenv("ECI_ARCHITECT_SEED", SEED_A)
    monkeypatch.delenv("ECI_ARCHITECT_KEYFILE", raising=False)
    from eci.core.identity import ArchitectIdentity

    return ArchitectIdentity()


def test_legacy_mode_labeled(legacy_ident):
    assert legacy_ident.alg == "legacy-sha512"
    s = legacy_ident.sign({"op": "x"})
    assert s["alg"] == "legacy-sha512"
    assert legacy_ident.verify_signature({"op": "x"}, s)["ok"] is True
    assert legacy_ident.verify_signature({"op": "y"}, s)["ok"] is False
    assert legacy_ident.did()["id"].startswith("did:eci:legacy:")


def test_legacy_stamp_backward_compat(legacy_ident):
    s = legacy_ident.stamp({"kind": "t"}, timestamp=123.0)
    assert s["alg"] == "legacy-sha512"
    assert legacy_ident.verify({"kind": "t"}, s["digest"], 123.0) is True
    assert legacy_ident.derive_id("node", {"a": 1}).startswith("node_")


def test_ed_sign_verify_tamper(ed_ident):
    assert ed_ident.alg == "ed25519"
    env = ed_ident.sign({"op": "demo"}, domain="dao")
    assert env["alg"] == "ed25519"
    assert ed_ident.verify_signature({"op": "demo"}, env)["ok"] is True
    assert ed_ident.verify_signature({"op": "evil"}, env)["ok"] is False
    bad = dict(env, signature="00" * 64)
    assert ed_ident.verify_signature({"op": "demo"}, bad)["ok"] is False


def test_ed_expiry_and_unknown_kid(ed_ident):
    env = ed_ident.sign({"op": "demo"})
    assert ed_ident.verify_signature({"op": "demo"}, env, max_age_s=100000)["ok"] is True
    assert ed_ident.verify_signature({"op": "demo"}, env, max_age_s=-1)["ok"] is False
    ghost = dict(env, kid="gen-999")
    assert ed_ident.verify_signature({"op": "demo"}, ghost)["ok"] is False


def test_rotation_keeps_old_verifiable(ed_ident):
    old_env = ed_ident.sign({"op": "old"})
    nxt = ed_ident.rotate(SEED_B)
    assert nxt.kid != ed_ident.kid
    assert nxt.verify_signature({"op": "old"}, old_env)["ok"] is True
    new_env = nxt.sign({"op": "new"})
    assert nxt.verify_signature({"op": "new"}, new_env)["ok"] is True
    assert nxt.key_status()["rotations"] == 1
    assert any(h["kid"] == ed_ident.kid for h in nxt.did()["retired"])


def test_subkey_domain_separation(ed_ident):
    a1, a2 = ed_ident.subkey("dao"), ed_ident.subkey("dao")
    b = ed_ident.subkey("consensus")
    assert a1 == a2 and len(a1) == 64
    assert a1 != b


def test_did_format(ed_ident):
    did = ed_ident.did()
    assert did["id"].startswith("did:eci:")
    assert len(did["active"]["public_hex"]) == 64
