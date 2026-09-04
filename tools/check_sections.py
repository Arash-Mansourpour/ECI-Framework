"""Verify every PDF section collected live data (no silent failures)."""
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
sys.path.insert(0, "benchmarks")
sys.path.insert(0, ".")

from tools.generate_pdf import collect_results

res = collect_results()
ex = res["extra"]
ok = sorted(k for k, v in ex.items() if k != "errors" and v is not None)
print("sections ok:", ok)
print("errors:", ex["errors"] if ex["errors"] else "NONE")
