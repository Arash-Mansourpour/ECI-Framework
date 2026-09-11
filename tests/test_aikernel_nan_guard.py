"""NaN/Inf guard: every contributor update() fails loud, never silent."""
import pytest
import torch


def _mesh():
    from eci.aikernel.mcp_bridge import build_unification
    return build_unification()["contributors"]


def _bad_obs(name, fill):
    if name == "phi":
        return torch.full((4, 2), fill)
    if name == "world":
        return torch.full((11,), fill)  # 2*obs(4)+act(2)+rew(1)
    if name == "sci":
        return torch.tensor([fill, 0.0])
    if name == "ewc":
        return torch.full((6,), fill)
    if name == "fep":
        return torch.full((2,), fill)
    return torch.full((1,), fill)


def test_nan_rejected_loudly_everywhere():
    c = _mesh()
    for name, member in c.items():
        with pytest.raises(ValueError, match="non-finite"):
            member.update(_bad_obs(name, float("nan")))


def test_inf_rejected_loudly_everywhere():
    c = _mesh()
    for name, member in c.items():
        with pytest.raises(ValueError, match="non-finite"):
            member.update(_bad_obs(name, float("inf")))
