"""Keyfile/seed handling + egress secret-shape tests (proof for audit)."""

from __future__ import annotations

import os
import warnings

SEED_A = "00" * 31 + "01"


def _clear_env(monkeypatch):
    monkeypatch.delenv("ECI_ARCHITECT_SEED", raising=False)
    monkeypatch.delenv("ECI_ARCHITECT_KEYFILE", raising=False)


def test_seed_rejects_overlong_env(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ECI_ARCHITECT_SEED", SEED_A + "ff")
    from eci.core.identity import _read_seed

    assert _read_seed() is None


def test_seed_rejects_overlong_128_env(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ECI_ARCHITECT_SEED", SEED_A + SEED_A)
    from eci.core.identity import _read_seed

    assert _read_seed() is None


def test_seed_rejects_short_and_nonhex(monkeypatch):
    _clear_env(monkeypatch)
    from eci.core.identity import _read_seed

    monkeypatch.setenv("ECI_ARCHITECT_SEED", "00" * 31)
    assert _read_seed() is None
    monkeypatch.setenv("ECI_ARCHITECT_SEED", "zz" * 32)
    assert _read_seed() is None


def test_seed_empty_file_returns_none(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    p = tmp_path / "empty.key"
    p.write_bytes(b"")
    monkeypatch.setenv("ECI_ARCHITECT_KEYFILE", str(p))
    from eci.core.identity import _read_seed

    assert _read_seed() is None


def test_seed_keyfile_padded_path_stripped(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    p = tmp_path / "k.key"
    p.write_bytes((SEED_A + "\n").encode())
    monkeypatch.setenv("ECI_ARCHITECT_KEYFILE", f"  {p}  ")
    from eci.core.identity import _read_seed

    r = _read_seed()
    assert r is not None and r.hex() == SEED_A


def test_seed_keyfile_overlong_rejected(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    p = tmp_path / "k2.key"
    p.write_bytes((SEED_A + "ff").encode())
    monkeypatch.setenv("ECI_ARCHITECT_KEYFILE", str(p))
    from eci.core.identity import _read_seed

    assert _read_seed() is None


def test_seed_never_raises_on_bad_input(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ECI_ARCHITECT_SEED", "zz-not-hex!!")
    from eci.core.identity import _read_seed

    assert _read_seed() is None
    monkeypatch.delenv("ECI_ARCHITECT_SEED", raising=False)
    monkeypatch.setenv("ECI_ARCHITECT_KEYFILE", r"C:\nonexistent\eci-key-xyz")
    assert _read_seed() is None


def test_keyfile_warn_posix_only(monkeypatch):
    from eci.core import identity as ident

    class FakeStat:
        st_mode = 0o100644

    monkeypatch.setattr(ident.os, "name", "posix")
    monkeypatch.setattr(ident.os, "stat", lambda p: FakeStat())
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        ident._warn_if_world_readable("dummy")
    assert len(rec) == 1
    assert SEED_A not in str(rec[0].message)

    class TightStat:
        st_mode = 0o100600

    monkeypatch.setattr(ident.os, "stat", lambda p: TightStat())
    with warnings.catch_warnings(record=True) as rec2:
        warnings.simplefilter("always")
        ident._warn_if_world_readable("dummy")
    assert len(rec2) == 0


def test_keyfile_warn_never_crashes_nt(monkeypatch):
    from eci.core import identity as ident

    monkeypatch.setattr(ident.os, "name", "nt")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        ident._warn_if_world_readable(r"C:\nonexistent\path")
        ident._warn_if_world_readable("")


def test_egress_scrubs_architect_seed_assignment():
    from eci.protocol0.egress import scrub

    seed = "ab" * 32
    cleaned, n = scrub("ECI_ARCHITECT_SEED=" + seed)
    assert n >= 1 and seed not in cleaned


def test_egress_scrubs_seed_64hex_context():
    from eci.protocol0.egress import scrub

    seed = "ab" * 32
    cleaned, n = scrub("seed: " + seed)
    assert n >= 1 and seed not in cleaned


def test_egress_does_not_scrub_public_keys():
    from eci.protocol0.egress import scrub

    pub = "ab" * 32
    did_doc = '{"id": "did:eci:abc123", "public_hex": "' + pub + '"}'
    cleaned, n = scrub(did_doc)
    assert pub in cleaned
    cleaned2, _ = scrub(pub)
    assert pub in cleaned2


def test_egress_no_false_positive_seed_flag():
    from eci.protocol0.egress import scrub

    cleaned, n = scrub("seed=0")
    assert n == 0 and cleaned == "seed=0"
    cleaned2, n2 = scrub("seed_configured: True")
    assert n2 == 0


def test_egress_keeps_ghp_behavior():
    from eci.protocol0.egress import scrub

    cleaned, n = scrub("token ghp_abc123XYZ4567890 done")
    assert n >= 1 and "ghp_" not in cleaned


def test_env_seed_still_loads_valid(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ECI_ARCHITECT_SEED", SEED_A)
    from eci.core.identity import _read_seed

    assert _read_seed() is not None and _read_seed().hex() == SEED_A
    assert os.environ["ECI_ARCHITECT_SEED"] == SEED_A
