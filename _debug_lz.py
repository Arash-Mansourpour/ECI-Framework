"""Verify fast LZ76 against the classic reference implementation."""
import sys, time

sys.path.insert(0, "src")
import numpy as np
import torch

from eci.consciousness.metrics import lempel_ziv_complexity


def lz76_reference(x: np.ndarray) -> float:
    flat = x.flatten()
    binary = (flat > np.median(flat)).astype(np.uint8)
    s = "".join(str(b) for b in binary)
    n = len(s)
    if n < 2:
        return 0.0
    i, c, u, v, vmax = 0, 1, 1, 1, 1
    while u + v <= n:
        if s[i + v - 1] == s[u + v - 1]:
            v += 1
            if u + v > n:
                break
        else:
            vmax = max(v, vmax)
            i += 1
            if i == u:
                c += 1
                u += vmax
                v = 1
                i = 0
                vmax = 1
            else:
                v = 1
    if v != 1:
        c += 1
    return float(min(c / (n / np.log2(n)), 1.0))


torch.manual_seed(1)
cases = {
    "zeros": np.zeros(500),
    "alternating": np.tile([0.0, 1.0], 250),
    "random": torch.rand(500).numpy(),
    "correlated": (torch.sin(torch.linspace(0, 40, 500)).unsqueeze(1).expand(500, 4) + 0.1 * torch.randn(500, 4)).numpy().flatten(),
    "short": np.array([1.0, 2.0, 1.0, 2.0, 3.0]),
}
for name, x in cases.items():
    ref = lz76_reference(x.copy())
    fast = lempel_ziv_complexity(x.copy())
    status = "OK " if abs(ref - fast) < 1e-9 else "DIFF"
    print(f"{status} {name:12s} ref={ref:.6f} fast={fast:.6f}")

# Speed on the analyzer-sized input
big = (torch.sin(torch.linspace(0, 30, 1000)).unsqueeze(1).expand(1000, 64) + 0.15 * torch.randn(1000, 64)).numpy()
t0 = time.perf_counter()
v = lempel_ziv_complexity(big)
print(f"fast on 64k samples: {time.perf_counter()-t0:.3f}s value={v:.4f}")
