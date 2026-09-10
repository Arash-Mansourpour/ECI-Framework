"""Functors: exact, tested mappings between domain representations.

F1  density matrix  -> Gaussian (mu, cov)   [``density_to_cov``]
    The quantum covariance matrix of metrology: for Pauli strings P_k
    (Tr[P_k P_l] = D·delta_kl, D = 2^n):
        mu_k     = Re Tr[rho · P_k]
        Sig_kl   = Re Tr[rho · {P_k,P_l}/2] - mu_k·mu_l
    Exact properties (tested): maximally mixed -> mu = 0; pure |0> ->
    mu_Z = +1 with Var(Z) = 0; Sigma always PSD.

F2  shared posterior -> per-agent belief   [``split_belief`` / ``fuse_beliefs``]
    Precision-weighted split with weights w_i (sum 1):
        Lambda_i = w_i · Lambda,   mu_i = mu      (Lambda = cov^-1)
    Fusion inverts it exactly: Lambda = sum Lambda_i  =>  fuse(split(Q)) = Q.
    Composition law (tested commuting triangle):
        split_{v}(split_{w}(Q)) == split_{v·w}(Q).

Convention: big-endian qubits (q0 = MSB), matching eci.quantum.gates.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import torch

__all__ = ["pauli_1q", "pauli_string_matrix", "default_paulis",
           "pauli_expectations", "density_to_cov",
           "split_belief", "fuse_beliefs"]

_PAULI_1Q: Dict[str, torch.Tensor] = {
    "I": torch.tensor([[1, 0], [0, 1]], dtype=torch.complex64),
    "X": torch.tensor([[0, 1], [1, 0]], dtype=torch.complex64),
    "Y": torch.tensor([[0, -1j], [1j, 0]], dtype=torch.complex64),
    "Z": torch.tensor([[1, 0], [0, -1]], dtype=torch.complex64),
}


def pauli_1q(name: str) -> torch.Tensor:
    return _PAULI_1Q[name].clone()


def pauli_string_matrix(label: str, n_qubits: int | None = None) -> torch.Tensor:
    """E.g. 'X0' = X on qubit 0 (MSB), 'ZZ' = Z_0 Z_1. Single letter = qubit 0.

    ``n_qubits`` pads unwritten qubits with I (required when the operator
    must match a density matrix: 'X0' on 2 qubits is X⊗I, not 1-qubit X).
    """
    import re
    toks = re.findall(r"([IXYZ])(\d*)", label)
    if not toks or "".join(a + b for a, b in toks) != label:
        raise ValueError(f"bad pauli label {label!r}")
    # digitless letters consume successive free qubits from 0
    # ("ZZ" -> Z_0 Z_1; explicit digits pin first: "ZX1" -> Z_0 X_1)
    assign: List[int] = [-1] * len(toks)
    used: set = set()
    for i, (a, b) in enumerate(toks):
        if b:
            assign[i] = int(b)
            used.add(int(b))
    for i, (a, b) in enumerate(toks):
        if not b:
            q = 0
            while q in used:
                q += 1
            assign[i] = q
            used.add(q)
    need = max(assign) + 1
    n = max(need, n_qubits or 0)
    ops: List[torch.Tensor] = [pauli_1q("I") for _ in range(n)]
    for (a, _), q in zip(toks, assign):
        if not torch.equal(ops[q], _PAULI_1Q["I"]):
            raise ValueError(f"qubit {q} assigned twice in {label!r}")
        ops[q] = pauli_1q(a)
    M = ops[0]
    for o in ops[1:]:
        M = torch.kron(M, o)
    return M


def default_paulis(n_qubits: int) -> List[str]:
    return [f"{P}{q}" for q in range(n_qubits) for P in ("X", "Y", "Z")]


def pauli_expectations(rho: torch.Tensor, n_qubits: int,
                       labels: Sequence[str]) -> torch.Tensor:
    """mu_k = Re Tr[rho P_k]. Returns real (d,) float32."""
    vals = []
    for lab in labels:
        P = pauli_string_matrix(lab, n_qubits).to(rho.dtype)
        vals.append(torch.trace(rho @ P).real)
    return torch.stack(vals).to(torch.float32)


def density_to_cov(rho: torch.Tensor, n_qubits: int,
                   labels: Sequence[str]) -> Tuple[torch.Tensor, torch.Tensor]:
    """Quantum covariance matrix. Returns (mu (d,), cov (d,d)) float32."""
    labels = list(labels)
    d = len(labels)
    mu = pauli_expectations(rho, n_qubits, labels)
    mats = [pauli_string_matrix(lab, n_qubits).to(rho.dtype) for lab in labels]
    cov = torch.zeros(d, d, dtype=torch.float32)
    for k in range(d):
        for l in range(k, d):
            anti = (mats[k] @ mats[l] + mats[l] @ mats[k]) / 2
            second = torch.trace(rho @ anti).real.item()
            v = second - float(mu[k].item() * mu[l].item())
            cov[k, l] = v
            cov[l, k] = v
    # symmetrize + PSD projection (removes float dust, keeps exactness)
    cov = (cov + cov.T) / 2
    w, V = torch.linalg.eigh(cov)
    cov = (V * w.clamp_min(0.0)) @ V.T
    cov = (cov + cov.T) / 2
    return mu, cov


def split_belief(mu: torch.Tensor, cov: torch.Tensor,
                 weights: Sequence[float]) -> List[Tuple[torch.Tensor, torch.Tensor]]:
    """Precision-weighted split; weights must sum to 1 (checked)."""
    w = torch.as_tensor(list(weights), dtype=torch.float32)
    if abs(float(w.sum().item()) - 1.0) > 1e-5:
        raise ValueError(f"split weights must sum to 1, got {w.sum().item()}")
    if bool((w <= 0).any()):
        raise ValueError("split weights must be positive")
    out = []
    for wi in w:
        out.append((mu.clone(), cov / float(wi.item())))
    return out


def fuse_beliefs(parts: Sequence[Tuple[torch.Tensor, torch.Tensor]]) -> Tuple[torch.Tensor, torch.Tensor]:
    """Precision-sum fusion: the exact inverse of split_belief."""
    Lam = torch.zeros_like(parts[0][1])
    b = torch.zeros_like(parts[0][0])
    for mu_i, cov_i in parts:
        Li = torch.linalg.inv(cov_i)
        Lam = Lam + Li
        b = b + Li @ mu_i
    cov = torch.linalg.inv(Lam)
    return cov @ b, cov
