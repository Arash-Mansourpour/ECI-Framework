"""Profile consciousness analyzer components."""
import sys, time

sys.path.insert(0, "src")
import torch

from eci.consciousness import metrics as cmetrics
from eci.consciousness.iit import IntegratedInformationTheory

torch.manual_seed(0)
t = torch.linspace(0, 30, 1000)
shared = torch.sin(t).unsqueeze(1) + 0.5 * torch.sin(3.7 * t).unsqueeze(1)
data = shared * (0.5 + 0.5 * torch.rand(1, 64)) + 0.15 * torch.randn(1000, 64)

t0 = time.perf_counter()
iit = IntegratedInformationTheory()
r = iit.calculate_phi(data, method="gaussian")
print(f"IIT gaussian: {time.perf_counter()-t0:.2f}s  phi={r['phi_total']:.4f}")

t0 = time.perf_counter()
lz = cmetrics.lempel_ziv_complexity(data.numpy())
print(f"LZ76: {time.perf_counter()-t0:.2f}s  value={lz:.4f}")

t0 = time.perf_counter()
se = cmetrics.sample_entropy(data)
print(f"sample entropy: {time.perf_counter()-t0:.2f}s  value={se:.4f}")

t0 = time.perf_counter()
spe = cmetrics.spectral_entropy(data)
print(f"spectral entropy: {time.perf_counter()-t0:.2f}s  value={spe:.4f}")

t0 = time.perf_counter()
mi = cmetrics.mutual_information(data[:, 0], data[:, 1])
print(f"MI single pair: {time.perf_counter()-t0:.2f}s  value={mi:.4f}")
