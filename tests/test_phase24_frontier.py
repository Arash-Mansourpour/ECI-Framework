import io
import json
import math
from types import SimpleNamespace

import numpy as np
import pytest
import torch


def _assert_density_matrix(rho):
    assert torch.isfinite(rho).all()
    torch.testing.assert_close(rho, rho.conj().transpose(-1, -2))
    torch.testing.assert_close(
        rho.diagonal(dim1=-2, dim2=-1).sum(-1),
        torch.ones(rho.shape[:-2], dtype=rho.dtype),
    )
    assert torch.linalg.eigvalsh(rho).min().item() >= -1e-7


def test_lindblad_amplitude_damping_matches_analytic_solution():
    from eci.quantum.lindblad import coherence_measure, lindblad_evolve

    psi = torch.tensor([[0.0, 1.0], [1.0, 1j]], dtype=torch.complex128)
    psi = psi / torch.linalg.vector_norm(psi, dim=1, keepdim=True)
    rho0 = psi.unsqueeze(-1) @ psi.conj().unsqueeze(-2)
    original = rho0.clone()
    hamiltonian = torch.zeros(2, 2, dtype=rho0.dtype)
    collapse = [torch.tensor([[0.0, 1.0], [0.0, 0.0]], dtype=rho0.dtype)]
    trajectory = lindblad_evolve(rho0, hamiltonian, collapse, n_steps=20, dt=0.05)

    assert len(trajectory) == 21
    for step, rho in enumerate(trajectory):
        t = step * 0.05
        expected = rho0.clone()
        expected[:, 1, 1] = rho0[:, 1, 1] * math.exp(-t)
        expected[:, 0, 0] = 1 - expected[:, 1, 1]
        expected[:, 0, 1] = rho0[:, 0, 1] * math.exp(-t / 2)
        expected[:, 1, 0] = expected[:, 0, 1].conj()
        torch.testing.assert_close(rho, expected, atol=1e-7, rtol=1e-6)
        _assert_density_matrix(rho)
    assert trajectory[-1][0, 1, 1].real < rho0[0, 1, 1].real
    assert 0 < coherence_measure(trajectory[-1])[1] < coherence_measure(rho0)[1]
    torch.testing.assert_close(rho0, original)


def test_lindblad_stabilizer_rk4_schedule_and_feedback():
    from eci.quantum.lindblad import MockQuantumStabilizer, coherence_measure, lindblad_evolve

    rho0 = torch.tensor([[[0.8, 0.2], [0.2, 0.2]]], dtype=torch.complex128)
    stabilizer = MockQuantumStabilizer(target_coherence=0.9, feedback_gain=2.0)
    feedback = stabilizer.schedule([])
    calls = []

    def schedule(step, rho):
        calls.append((step, rho.clone()))
        drive = feedback(step, rho)
        torch.testing.assert_close(drive, drive.conj().transpose(-1, -2))
        return drive

    trajectory = lindblad_evolve(
        rho0, torch.zeros(2, 2, dtype=rho0.dtype), [],
        n_steps=5, dt=0.05, hamiltonian_schedule=schedule,
    )
    assert len(trajectory) == 6
    assert len(stabilizer.history) == 20
    assert [step for step, _ in calls] == [step for step in range(5) for _ in range(4)]
    assert stabilizer.history == pytest.approx(
        [coherence_measure(rho).item() for _, rho in calls]
    )
    assert stabilizer.history[0] == pytest.approx(0.4)
    assert not torch.allclose(calls[0][1], calls[1][1])
    assert not torch.allclose(trajectory[-1], rho0)
    for rho in trajectory:
        _assert_density_matrix(rho)
        torch.testing.assert_close(torch.linalg.eigvalsh(rho), torch.linalg.eigvalsh(rho0))


def test_lindblad_rejects_mismatched_hamiltonian():
    from eci.quantum.lindblad import lindblad_evolve

    with pytest.raises(ValueError, match="does not match"):
        lindblad_evolve(torch.eye(2, dtype=torch.complex64) / 2, torch.eye(3), [], 2)


def test_pyphi_crosscheck_skips_without_pyphi(monkeypatch):
    from eci.consciousness import validation

    looked_up = []
    original = validation.importlib.util.find_spec

    def find_spec(name, *args, **kwargs):
        looked_up.append(name)
        return None if name == "pyphi" else original(name, *args, **kwargs)

    monkeypatch.setattr(validation.importlib.util, "find_spec", find_spec)
    assert validation.pyphi_crosscheck() == {
        "ok": True, "skipped": True, "reason": "pyphi not installed",
        "eci_phi": None, "pyphi_phi": None, "agree": None,
    }
    assert looked_up == ["pyphi"]


@pytest.mark.parametrize("resting,active", [([], []), ([3.0], [7.0]), ([], [1.0]), ([1.0], [])])
def test_eeg_closed_loop_empty_and_singleton(resting, active):
    from eci.consciousness.validation import eeg_closed_loop

    assert eeg_closed_loop(resting, active) == {
        "rest_power": 0.0, "active_power": 0.0, "lift": 0.0,
        "bits_proxy": 0.0, "tier": "none", "act": False,
    }


def test_eeg_deterministic_signal_relative_band_fractions():
    from eci.consciousness.eeg import bandpower
    from eci.consciousness.validation import eeg_closed_loop

    time = np.arange(256) / 256.0
    alpha = np.sin(2 * np.pi * 10 * time)
    beta = np.sin(2 * np.pi * 20 * time)
    mixed = alpha + 2 * beta
    fractions = bandpower(torch.as_tensor(mixed[:, None]))
    assert fractions == pytest.approx({
        "delta": 0.0, "theta": 0.0, "alpha": 0.2, "beta": 0.8, "gamma": 0.0,
    }, abs=1e-10)
    result = eeg_closed_loop(alpha, mixed)
    assert result["rest_power"] == pytest.approx(0.2)
    assert result["active_power"] == pytest.approx(0.2)
    assert result["lift"] == pytest.approx(1.0)
    assert result["bits_proxy"] == pytest.approx(1.0)
    assert result["tier"] == "none"
    assert result["act"] is False


@pytest.mark.parametrize("scale", [0.25, 4.0, -3.0])
def test_eeg_bandpower_and_closed_loop_scale_invariance(scale):
    from eci.consciousness.eeg import bandpower
    from eci.consciousness.validation import eeg_closed_loop

    time = np.arange(512) / 256.0
    signal = np.sin(2 * np.pi * 10 * time) + 0.5 * np.sin(2 * np.pi * 40 * time)
    baseline = bandpower(torch.as_tensor(signal[:, None]))
    scaled = bandpower(torch.as_tensor((scale * signal)[:, None]))
    assert scaled == pytest.approx(baseline, abs=1e-10)
    reference = eeg_closed_loop(signal, signal)
    result = eeg_closed_loop(signal, scale * signal)
    for key in ("rest_power", "active_power", "lift", "bits_proxy"):
        assert result[key] == pytest.approx(reference[key], abs=1e-10)
    assert result["tier"] == reference["tier"]
    assert result["act"] is reference["act"]


def test_adherence_head_train_predict_and_roundtrip():
    from eci.consciousness.validation import AdherenceHead, train_adherence_head

    rows = [
        {"phi_norm": 0.9, "awareness": 0.8, "broadcast": 0.9, "label": 1.0},
        {"phi_norm": 0.1, "awareness": 0.2, "broadcast": 0.1, "label": 0.0},
        {"phi_norm": 0.8, "awareness": 0.7, "broadcast": 0.8, "label": 1.0},
        {"phi_norm": 0.2, "awareness": 0.1, "broadcast": 0.2, "label": 0.0},
    ]
    initial = AdherenceHead()
    head = train_adherence_head(rows, steps=50)
    p_hi = head.predict(0.9, 0.8, 0.9)
    p_lo = head.predict(0.1, 0.1, 0.1)
    assert 0.0 < p_lo < p_hi < 1.0
    assert p_hi > initial.predict(0.9, 0.8, 0.9)
    assert p_lo < initial.predict(0.1, 0.1, 0.1)
    restored = AdherenceHead(**head.to_dict())
    assert restored.predict(0.9, 0.8, 0.9) == pytest.approx(p_hi)
    assert restored.predict(0.1, 0.1, 0.1) == pytest.approx(p_lo)


def test_qnn_forward_backward_and_batch_independence():
    from eci.quantum.qnn import QuantumNeuralNetwork

    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(0)
        qnn = QuantumNeuralNetwork(
            in_features=3, n_qubits=2, out_features=2, n_layers=2, device=torch.device("cpu")
        )
    x = torch.tensor([[0.2, -0.4, 0.7], [-0.3, 0.8, 0.1], [0.6, 0.2, -0.5]], requires_grad=True)
    out = qnn(x)
    assert out.shape == (3, 2)
    assert torch.isfinite(out).all()
    torch.testing.assert_close(out, torch.cat([qnn(row.unsqueeze(0)) for row in x]))
    expectations = qnn.q_layer(torch.tanh(qnn.classical_in(x)))
    assert expectations.shape == (3, 2)
    assert torch.all(expectations.abs() <= 1 + 1e-6)
    out.square().sum().backward()
    assert x.grad is not None and torch.isfinite(x.grad).all()
    assert x.grad.abs().sum() > 0
    for name, parameter in qnn.named_parameters():
        assert parameter.grad is not None, name
        assert torch.isfinite(parameter.grad).all(), name
        assert parameter.grad.abs().sum() > 0, name


@pytest.mark.parametrize("shape", [(2,), (3, 3), (1, 2, 2)])
def test_quantum_layer_rejects_wrong_feature_shape(shape):
    from eci.quantum.qnn import QuantumLayer

    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(0)
        layer = QuantumLayer(2, device=torch.device("cpu"))
    with pytest.raises(ValueError, match="expected input of shape"):
        layer(torch.zeros(shape))


@pytest.mark.parametrize("n_particles,shots", [(1, 1), (2, 100), (8, 25)])
def test_metrology_ramsey_and_fisher_scaling(n_particles, shots):
    from eci.quantum import metrology

    entangled = metrology.ramsey_sensitivity(n_particles, entangled=True, shots=shots)
    separable = metrology.ramsey_sensitivity(n_particles, entangled=False, shots=shots)
    qfi = metrology.ghz_phase_qfi(n_particles)
    assert qfi == metrology.noon_state_qfi(n_particles)
    assert qfi["qfi"] == n_particles ** 2
    assert entangled["per_shot"] == pytest.approx(1 / n_particles)
    assert separable["per_shot"] == pytest.approx(1 / math.sqrt(n_particles))
    assert entangled["with_shots"] == pytest.approx(metrology.heisenberg_limit(n_particles, shots))
    assert separable["with_shots"] == pytest.approx(metrology.standard_quantum_limit(n_particles, shots))
    assert entangled["with_shots"] ** 2 == pytest.approx(metrology.cramer_rao_bound(qfi["qfi"], shots))
    assert entangled["with_shots"] <= separable["with_shots"]
    assert entangled["quantum_advantage_db"] == pytest.approx(10 * math.log10(n_particles))
    assert separable["quantum_advantage_db"] == 0.0
    assert entangled["regime"] == "Heisenberg"
    assert separable["regime"] == "SQL"


def test_metrology_numerical_fisher_matches_analytic_values():
    from eci.quantum.metrology import classical_fisher_information, quantum_fisher_pure

    def probabilities(theta):
        return torch.tensor([theta, 1 - theta], dtype=torch.float64)

    def psi(theta):
        return torch.tensor([math.cos(theta / 2), math.sin(theta / 2)], dtype=torch.complex128)

    assert classical_fisher_information(probabilities, 0.3) == pytest.approx(1 / (0.3 * 0.7))
    assert quantum_fisher_pure(psi, 0.7, dtheta=1e-3) == pytest.approx(1.0, rel=1e-6)
    assert quantum_fisher_pure(lambda theta: 3 * psi(theta).unsqueeze(0), 0.7, dtheta=1e-3) == pytest.approx(1.0, rel=1e-6)
    assert quantum_fisher_pure(lambda theta: psi(0.0), 0.7) == 0.0


def test_operator_pauli_algebra_and_reconstruction():
    from eci.quantum import gates as qg
    from eci.quantum import operator as qop

    torch.testing.assert_close(qop.commutator(qg.X, qg.Y), 2j * qg.Z)
    torch.testing.assert_close(qop.anticommutator(qg.X, qg.Y), torch.zeros_like(qg.X))
    operator = 0.25 * torch.kron(qg.I, qg.Z) - 0.7 * torch.kron(qg.X, qg.Y)
    coefficients = qop.pauli_decomposition(operator, n_qubits=2)
    assert coefficients == pytest.approx({("I", "Z"): 0.25, ("X", "Y"): -0.7})
    torch.testing.assert_close(qop.pauli_reconstruction(coefficients, n_qubits=2), operator)
    values, vectors = qop.spectral_decomposition(operator)
    torch.testing.assert_close(vectors @ torch.diag(values.to(vectors.dtype)) @ vectors.conj().T, operator)
    assert qop.is_hermitian(operator)


def test_operator_evolution_preserves_norm_and_expectation_picture():
    from eci.quantum import gates as qg
    from eci.quantum import operator as qop

    hamiltonian = (0.3 * qg.X + 0.7 * qg.Z).to(torch.complex128)
    observable = qg.Y.to(torch.complex128)
    psi = torch.tensor([1.0, 2j], dtype=torch.complex128) / math.sqrt(5)
    unitary = qop.matrix_exponential_hermitian(hamiltonian, 0.4)
    torch.testing.assert_close(unitary, torch.matrix_exp(-0.4j * hamiltonian))
    assert qop.is_unitary(unitary)
    evolved = qop.unitary_evolution(hamiltonian, 0.4, psi)
    torch.testing.assert_close(torch.linalg.vector_norm(evolved), torch.linalg.vector_norm(psi))
    torch.testing.assert_close(qop.unitary_evolution(hamiltonian, -0.4, evolved), psi)
    torch.testing.assert_close(
        torch.vdot(evolved, observable @ evolved),
        torch.vdot(psi, qop.heisenberg_evolution(hamiltonian, observable, 0.4) @ psi),
    )
    batch = torch.stack([psi, psi.conj()])
    torch.testing.assert_close(
        qop.unitary_evolution(hamiltonian, 0.4, batch),
        torch.stack([unitary @ state for state in batch]),
    )


@pytest.mark.parametrize("asynchronous", [False, True])
def test_inprocess_transport_roundtrip(asynchronous):
    from eci.mcp.transports import InProcessTransport

    received = []

    def handler(message):
        received.append(message)
        return {"id": message["id"], "result": message["params"]}

    async def async_handler(message):
        return handler(message)

    transport = InProcessTransport(async_handler if asynchronous else handler)
    assert transport.request("echo", {"value": [1, "two"]}, _id="request-7") == {
        "id": "request-7", "result": {"value": [1, "two"]},
    }
    assert transport.request("ping", _id=0) == {"id": 0, "result": {}}
    assert received == [
        {"id": "request-7", "method": "echo", "params": {"value": [1, "two"]}},
        {"id": 0, "method": "ping", "params": {}},
    ]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_stdio_transport_handles_input_errors_and_continues(monkeypatch, capsys, asynchronous):
    from eci.mcp.transports import StdioTransport

    received = []

    def handler(message):
        received.append(message)
        if message["method"] == "fail":
            raise ValueError("handler failed")
        return {"id": message["id"], "result": message["params"]}

    async def async_handler(message):
        return handler(message)

    messages = [
        {"id": 2, "method": "fail"},
        {"id": "last", "method": "echo", "params": {"value": 42}},
    ]
    monkeypatch.setattr("sys.stdin", io.StringIO("\nnot json\n" + "\n".join(map(json.dumps, messages)) + "\n"))
    StdioTransport(async_handler if asynchronous else handler).serve_forever()
    replies = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(replies) == 3
    assert replies[0]["id"] is None
    assert replies[0]["error"].startswith("bad json:")
    assert replies[1] == {"id": 2, "error": "ValueError('handler failed')"}
    assert replies[2] == {"id": "last", "result": {"value": 42}}
    assert received == messages


def test_autopoiesis_update_and_viability_history():
    from eci.cybernetics.autopoiesis import AutopoieticNetwork, viability_margin

    initial = torch.tensor([0.2, 0.4, 0.6, 0.8], dtype=torch.float64)
    core = AutopoieticNetwork(n_components=4, concentrations=initial.clone())
    assert core.viability_rate() == 0.0
    result = core.step(torch.tensor([0.0, 2.0]))
    expected = initial + 0.5 * initial * (1 - initial) - 0.2 * initial + 0.05
    torch.testing.assert_close(core.concentrations, expected)
    assert result["boundary"] == pytest.approx(expected.mean().item())
    assert result["closure"] == pytest.approx(1.0)
    assert result["viable"] is True
    assert viability_margin(core.concentrations) > 0
    failed = core.step(torch.full((4,), -100.0))
    torch.testing.assert_close(core.concentrations, torch.zeros(4, dtype=torch.float64))
    assert failed["viable"] is False
    assert core.history == [result, failed]
    assert core.viability_rate() == 0.5
    assert viability_margin(core.concentrations) == pytest.approx(-0.1)
    core.step(torch.full((4,), 100.0))
    torch.testing.assert_close(core.concentrations, torch.ones(4, dtype=torch.float64))


def test_data_cache_lru_and_stats(monkeypatch):
    from eci.data import cache

    monkeypatch.setattr(cache, "time", SimpleNamespace(time=lambda: 100.0))
    store = cache.Cache(capacity=2, ttl_s=10)
    assert store.stats() == {"size": 0, "hits": 0, "misses": 0, "evictions": 0, "hit_rate": 0.0}
    store.put("a", 1)
    store.put("b", 2)
    assert store.get("a") == 1
    store.put("c", 3)
    assert store.get("b") is None
    store.put("a", 4)
    assert store.get("a") == 4
    assert store.get("c") == 3
    assert store.stats() == {"size": 2, "hits": 3, "misses": 1, "evictions": 1, "hit_rate": 0.75}


def test_data_cache_ttl_override_and_refresh(monkeypatch):
    from eci.data import cache

    clock = [100.0]
    monkeypatch.setattr(cache, "time", SimpleNamespace(time=lambda: clock[0]))
    store = cache.Cache(capacity=2, ttl_s=10)
    store.put("default", "old")
    store.put("short", "value", ttl_s=2)
    clock[0] = 102.0
    assert store.get("short") == "value"
    clock[0] = 102.1
    assert store.get("short") is None
    store.put("default", "new")
    clock[0] = 111.0
    assert store.get("default") == "new"
    clock[0] = 112.2
    assert store.get("default") is None
    assert store.stats() == {"size": 0, "hits": 2, "misses": 2, "evictions": 0, "hit_rate": 0.5}


@pytest.mark.parametrize("ledger_state", ["absent", "valid", "invalid", "raises"])
def test_health_status_and_metrics(monkeypatch, ledger_state):
    from eci import health
    from eci.version import FRAMEWORK_VERSION

    monkeypatch.setenv("ECI_PROFILE", "test-profile")
    monkeypatch.setenv("ECI_NODE_ID", "test-node")
    monkeypatch.setattr(health, "_STARTED", 100.0)
    monkeypatch.setattr(health, "time", SimpleNamespace(time=lambda: 112.5))

    def verify():
        if ledger_state == "raises":
            raise ValueError("invalid ledger")
        return {"ok": ledger_state == "valid"}

    ledger = None if ledger_state == "absent" else SimpleNamespace(records=[1, 2], verify=verify)
    ok = ledger_state in ("absent", "valid")
    height = 0 if ledger is None else 2
    result = health.status(ledger, peers=3, collective_gate="open")
    assert result == {
        "ok": ok, "version": FRAMEWORK_VERSION, "profile": "test-profile", "node": "test-node",
        "ledger_height": height, "ledger_ok": ok, "peers": 3, "collective_gate": "open", "uptime_s": 12.5,
    }
    lines = health.metrics_text(result).splitlines()
    assert lines[1::2] == [
        f"eci_up {int(ok)}", f"eci_ledger_height {height}", f"eci_ledger_ok {int(ok)}",
        "eci_peers 3", "eci_uptime_s 12.5",
    ]
    assert len(lines) == 10


def test_resilience_failure_recovery_and_task_isolation():
    from eci.protocol_vnext.resilience import ExperimentalReasoningLab, GracefulDegradation

    degradation = GracefulDegradation()
    assert degradation.to_dict() == {"degraded": [], "failures": 0}
    degradation.report_failure("transport", "offline")
    degradation.report_failure("model", "unavailable")
    result = degradation.report_failure("transport", "still offline")
    assert result["status"] == "degraded"
    assert result["degraded_set"] == ["model", "transport"]
    degradation.recover("transport")
    degradation.recover("missing")
    assert not degradation.is_degraded("transport")
    assert degradation.is_degraded("model")
    assert degradation.to_dict() == {"degraded": ["model"], "failures": 3}
    lab = ExperimentalReasoningLab()
    assert lab.best_for("planning") is None
    lab.experiment("planning", "tree", 0.3)
    lab.experiment("planning", "graph", 0.8)
    lab.experiment("other", "constraint", 1.0)
    assert lab.best_for("planning") == "graph"
    assert lab.best_for("other") == "constraint"
    assert lab.to_dict()["experiments"] == 3


def test_resilience_retry_backoff_and_success(monkeypatch):
    from eci.resilience import retry

    sleeps = []
    monkeypatch.setattr(retry, "time", SimpleNamespace(time=lambda: 100.0, sleep=sleeps.append))
    policy = retry.RetryPolicy(attempts=4, base_delay_s=0.1, max_delay_s=0.15, jitter=0)
    calls = []

    def flaky(value, *, suffix):
        calls.append(value)
        if len(calls) < 3:
            raise RuntimeError("retry")
        return value + suffix

    assert policy.run(flaky, "ok", suffix="!") == "ok!"
    assert calls == ["ok"] * 3
    assert sleeps == pytest.approx([0.1, 0.15])


@pytest.mark.parametrize("retryable,expected_calls", [(True, 3), (False, 1)])
def test_resilience_retry_exhaustion_and_exception_filter(monkeypatch, retryable, expected_calls):
    from eci.resilience import retry

    sleeps = []
    monkeypatch.setattr(retry, "time", SimpleNamespace(time=lambda: 100.0, sleep=sleeps.append))
    policy = retry.RetryPolicy(attempts=3, base_delay_s=0, jitter=0, retry_on=(RuntimeError,))
    error = RuntimeError("exhausted") if retryable else ValueError("not retryable")
    calls = []

    def fail():
        calls.append(1)
        raise error

    with pytest.raises(type(error)) as caught:
        policy.run(fail)
    assert caught.value is error
    assert len(calls) == expected_calls
    assert len(sleeps) == expected_calls - 1
