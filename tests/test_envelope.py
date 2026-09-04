"""Signed envelopes: auth, replay rejection, tamper rejection."""
import pytest

from eci.network.envelope import EnvelopeError, ReplayGuard, open_envelope, seal
from eci.protocol0 import keys as K


def _pair():
    kp = K.generate()
    return kp, { "alice": kp.public_bytes }


def test_seal_open_roundtrip():
    kp, keys = _pair()
    env = seal("alice", kp, 0, {"vote": 1})
    hints = {"alice": kp.private_bytes} if K.mechanism().startswith("HMAC") else {}
    assert open_envelope(env, keys, ReplayGuard(), private_hints=hints) == {"vote": 1}


def test_replay_and_tamper_rejected():
    kp, keys = _pair()
    hints = {"alice": kp.private_bytes} if K.mechanism().startswith("HMAC") else {}
    guard = ReplayGuard()
    env = seal("alice", kp, 0, {"vote": 1})
    open_envelope(env, keys, guard, private_hints=hints)
    with pytest.raises(EnvelopeError):
        open_envelope(env, keys, guard, private_hints=hints)  # replay
    env2 = seal("alice", kp, 1, {"vote": 1})
    env2.payload = {"vote": 2}  # tamper after signing
    with pytest.raises(EnvelopeError):
        open_envelope(env2, keys, ReplayGuard(), private_hints=hints)
    with pytest.raises(EnvelopeError):
        open_envelope(env2, {"mallory": keys["alice"]}, ReplayGuard(), private_hints=hints)
