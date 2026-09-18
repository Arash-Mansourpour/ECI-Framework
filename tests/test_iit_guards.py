"""Guard: IIT gaussian exhaustive fallback flag (Phase 1.5)."""

import torch

from eci.consciousness.iit import IntegratedInformationTheory


def test_gaussian_exhaustive_fallback_flag():
    iit = IntegratedInformationTheory()
    # n=10, exhaustive=True -> must fallback to heuristic with flag True and warning
    X = torch.randn(64, 10)
    out = iit.calculate_phi(X, method="gaussian", exhaustive=True)
    assert out["heuristic_fallback"] is True
    assert "phi_total" in out
    # n=6 exhaustive should be exact, no fallback
    Y = torch.randn(64, 6)
    out2 = iit.calculate_phi(Y, method="gaussian", exhaustive=True)
    assert out2["heuristic_fallback"] is False
    # non-exhaustive never fallbacks
    out3 = iit.calculate_phi(Y, method="gaussian", exhaustive=False)
    assert out3["heuristic_fallback"] is False


def test_gaussian_exhaustive_fallback_via_state():
    from eci.aikernel.generative_model import GenerativeState

    iit = IntegratedInformationTheory()
    # create a GenerativeState with dim=10
    cov = torch.eye(10) * 0.5 + torch.randn(10, 10) * 0.01
    cov = 0.5 * (cov + cov.T)
    cov = cov + torch.eye(10) * 0.1
    mu = torch.zeros(10)
    st = GenerativeState(mu=mu, cov=cov)
    out = iit.calculate_phi(state=st, method="gaussian", exhaustive=True)
    assert out["heuristic_fallback"] is True
