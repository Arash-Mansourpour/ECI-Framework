"""Phase 4 — noise + ZNE + PEC + hybrid scheduler.

Calibrated numbers (Bell ZZ, true = 1.0; ZNE scales 1,3,5):
  q=0.01: biased 0.9801 -> mitigated 1.0000 (1028x)
  q=0.05: biased 0.9025 -> mitigated 0.9978 (45x)
  q=0.10: biased 0.8100 -> mitigated 0.9852 (13x)
  q=0.30: biased 0.4900 -> mitigated 0.7823 (2.3x, degrading gracefully)
VQE 2-qubit TFI, 60 steps, q=0.02:
  ideal err +0.0034 | noisy err +0.0566 | zne err +0.0035 (16x recovery)
Tolerances below are looser than measured (CI headroom); relations
(noisy worse than zne; mitigation strictly improves here) are asserted.
"""
import torch


def _bell():
    bell = torch.zeros(4, 4, dtype=torch.complex64)
    bell[0, 0] = bell[0, 3] = bell[3, 0] = bell[3, 3] = 0.5
    return bell


def test_depolarizing_definition_and_shape_regression():
    """Textbook N_q + regression: unbatched (D,D) density no longer corrupted."""
    from eci.quantum.mitigation import apply_depolarizing
    zero = torch.zeros(2, 2, dtype=torch.complex64)
    zero[0, 0] = 1.0
    out = apply_depolarizing(zero, 1, 0.2)
    assert out.shape == (2, 2), out.shape
    assert torch.allclose(out.diag().real, torch.tensor([0.9, 0.1]), atol=1e-5), out.diag()
    # statevector input still accepted (backward compat: batched density out)
    sv = torch.tensor([[1.0, 0.0]], dtype=torch.complex64)
    out_sv = apply_depolarizing(sv, 1, 0.2)
    assert out_sv.shape == (1, 2, 2), out_sv.shape
    assert torch.allclose(out_sv[0].diag().real, torch.tensor([0.9, 0.1]), atol=1e-5)
    # trace preserved, PSD preserved
    assert abs(float(torch.trace(out).real.item()) - 1.0) < 1e-6


def test_richardson_synthetic_exact():
    from eci.quantum.mitigation import richardson_extrapolate
    lin = [2.0 + 3.0 * x for x in (1.0, 3.0, 5.0)]
    assert abs(richardson_extrapolate((1.0, 3.0, 5.0), lin) - 2.0) < 1e-9
    quad = [2.0 + 3.0 * x + 0.5 * x * x for x in (1.0, 3.0, 5.0)]
    assert abs(richardson_extrapolate((1.0, 3.0, 5.0), quad) - 2.0) < 1e-9
    assert abs(richardson_extrapolate((1.0, 3.0, 5.0), lin, order=1) - 2.0) < 1e-9


def test_zne_combine_matches_and_preserves_grad():
    from eci.quantum.mitigation import lagrange_weights_0, richardson_extrapolate, zne_combine
    w = lagrange_weights_0((1.0, 3.0, 5.0))
    assert abs(sum(w) - 1.0) < 1e-12  # constant signals pass through untouched
    vals = [torch.tensor([0.9, 0.4], requires_grad=True),
            torch.tensor([0.7, 0.2], requires_grad=True),
            torch.tensor([0.5, 0.1], requires_grad=True)]
    out = zne_combine(vals, (1.0, 3.0, 5.0))
    assert out.grad_fn is not None  # the calibration bug (detached floats) stays fixed
    ref = [richardson_extrapolate((1.0, 3.0, 5.0), [float(v[i].item()) for v in vals])
           for i in range(2)]
    assert torch.allclose(out.detach(), torch.tensor(ref), atol=1e-6)
    out.sum().backward()
    assert all(v.grad is not None and bool((v.grad != 0).any()) for v in vals)


def test_bell_zz_bias_table():
    from eci.aikernel.functors import pauli_string_matrix
    from eci.quantum.mitigation import apply_depolarizing, zne_means
    bell, ZZ = _bell(), pauli_string_matrix("ZZ", 2)

    def ev(rho):
        return float(torch.trace(rho @ ZZ).real.item())

    def at_scale(lam, q):
        r = bell
        for _ in range(max(1, lam)):
            r = apply_depolarizing(r, 2, q)
        return r

    for q, exp_bias in ((0.01, 1 - 0.99 ** 2), (0.05, 1 - 0.95 ** 2), (0.10, 1 - 0.90 ** 2)):
        biased = ev(at_scale(1, q))
        assert abs((1 - biased) - exp_bias) < 1e-4, (q, biased)  # noise model itself verified
        mit = zne_means(lambda lam, _q=q: at_scale(lam, _q), ["ZZ"])["mitigated"][0]
        assert abs(1 - mit) < (1 - biased) / 5, (q, biased, mit)  # >=5x improvement
    # high-noise tail: still helps, gracefully degrading (measured 2.3x at q=0.3)
    mit30 = zne_means(lambda lam: at_scale(lam, 0.30), ["ZZ"])["mitigated"][0]
    assert abs(1 - mit30) < (1 - ev(at_scale(1, 0.30))), mit30


def test_pec_exact_and_documented_cost():
    from eci.aikernel.functors import pauli_string_matrix
    from eci.quantum.mitigation import apply_depolarizing, pec_gamma, pec_mitigate
    bell, ZZ = _bell(), pauli_string_matrix("ZZ", 2)
    assert abs(pec_gamma(0.05, 2) - (1 + 1.5 * 0.05 / 0.95) ** 4) < 1e-9
    assert pec_gamma(0.3, 2) > pec_gamma(0.05, 2)  # cost grows with noise, as theorized
    pm = pec_mitigate(apply_depolarizing(bell, 2, 0.05), ZZ, 0.05, n_samples=4096, seed=0)
    assert abs(pm["mitigated"] - 1.0) < 3 * pm["stderr"] + 1e-3, pm  # exact-in-expectation
    assert pm["stderr"] > 0  # cost is real and reported, not hidden
    # convention map vs cited (1+2p/(1-p))^{2k} under p_tot = 3q/4:
    # within 0.5% (measured 1.35519 vs 1.35005) — convention, not physics
    cited = (1 + 2 * (0.75 * 0.05) / (1 - 0.75 * 0.05)) ** 4
    assert abs(pec_gamma(0.05, 2) - cited) < 1e-2, (pec_gamma(0.05, 2), cited)
    # cost scaling law, robust form: stderr ~ 1/sqrt(N) (measured 4.035 vs 4.0)
    noisy = apply_depolarizing(bell, 2, 0.05)
    s1 = pec_mitigate(noisy, ZZ, 0.05, n_samples=1024, seed=0)["stderr"]
    s2 = pec_mitigate(noisy, ZZ, 0.05, n_samples=16384, seed=0)["stderr"]
    assert abs(s1 / s2 - 4.0) < 0.3, (s1, s2)
    # q-scaling carries an O(1) observable prefactor over the gamma ratio
    # (measured 1.80 vs naive 1.37): assert direction + same order, not equality
    sh = pec_mitigate(apply_depolarizing(bell, 2, 0.15), ZZ, 0.15,
                      n_samples=20000, seed=1)["stderr"]
    sl = pec_mitigate(apply_depolarizing(bell, 2, 0.05), ZZ, 0.05,
                      n_samples=20000, seed=1)["stderr"]
    assert 1.0 < sh / sl < 3.0, (sh, sl)


def test_scheduler_modes_and_vqe_under_noise():
    from eci.aikernel.state_contract import KernelLedger, conforms
    from eci.quantum.aikernel_adapter import VQEContributor, tfi_hamiltonian
    from eci.quantum.mitigation import NoisyVQEContributor
    import pytest
    H = tfi_hamiltonian(2)
    E0 = float(torch.linalg.eigvalsh(H.to_matrix(2)).min().item())
    with pytest.raises(ValueError):
        NoisyVQEContributor(H, 2, mode="bogus")
    # ideal path is bit-identical to the 2a parent (same code path)
    a = VQEContributor(H, 2, e_target=E0 - 1.0)
    b = NoisyVQEContributor(H, 2, e_target=E0 - 1.0, mode="ideal")
    b.params.data.copy_(a.params.data)
    assert abs(float(a.free_energy_contribution().item()) -
               float(b.free_energy_contribution().item())) < 1e-9
    assert conforms(b) is True
    res = {}
    for mode in ("ideal", "noisy", "zne"):
        c = NoisyVQEContributor(H, 2, n_layers=2, e_target=E0 - 1.0,
                                mode=mode, noise_q=0.02)
        out = c.run(60)
        res[mode] = out["energy_final"]
        assert conforms(c) is True
    assert abs(res["ideal"] - E0) < 0.02, res
    assert (res["noisy"] - E0) > (res["zne"] - E0), res  # mitigation recovers
    assert abs(res["zne"] - E0) < 0.02, res
    # one ledger, three noise conditions, same harness
    led = KernelLedger()
    for mode in ("ideal", "noisy", "zne"):
        led.register(mode, NoisyVQEContributor(H, 2, e_target=E0 - 1.0,
                                               mode=mode, noise_q=0.02))
    assert set(led.shares()) == {"ideal", "noisy", "zne"}
    assert all(v == v and abs(v) < 1e6 for v in led.shares().values())
