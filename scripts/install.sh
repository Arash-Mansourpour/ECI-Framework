#!/usr/bin/env bash
# ECI one-line installer: python SDK + JS SDK + health probe.
# Usage:  curl -fsSL https://raw.githubusercontent.com/Arash-Mansourpour/ECI-Framework/main/scripts/install.sh | bash
set -euo pipefail
echo "== ECI Framework installer =="
python3 --version
pip install -e "git+https://github.com/Arash-Mansourpour/ECI-Framework.git#egg=eci-framework[dev]" 2>/dev/null \
  || pip install eci-framework 2>/dev/null \
  || echo "(clone the repo and run: pip install -e .[dev])"
command -v node >/dev/null && (cd js/eci-protocol0 && node test.js) || echo "(node not found: JS SDK skipped)"
python3 -m eci health --once 2>/dev/null || PYTHONPATH=src python3 -m eci health --once || true
echo "== done: try 'eci demo' =="
