"""Global constants for the ECI Framework.

The architect identity is intentionally woven into every layer of the
framework: node identifiers, consensus records, quantum signatures and the
companion paper all carry the sovereign-architect stamp defined here.
"""

# ---------------------------------------------------------------------------
# Sovereign architect identity
# ---------------------------------------------------------------------------

ARCHITECT_NAME = "Arash Mansourpour"
ARCHITECT_TITLE = "Sovereign Architect (Ma'mar-e A'zam)"
CREATOR_WALLET = "GA4IHOJOXKIZDLNCXQT7NG65MT7Z3EQKRT4PYFYURIP7QRLY4CHMHILW"
ARCHITECT_SIGNATURE = "Arash_Mansourpour_ECI_v5.0_Quantum_Supremacy"

# ---------------------------------------------------------------------------
# Scientific constants (CODATA 2018)
# ---------------------------------------------------------------------------

PLANCK_CONSTANT = 6.62607015e-34  # J*s
REDUCED_PLANCK_CONSTANT = PLANCK_CONSTANT / (2.0 * 3.141592653589793)  # hbar, J*s
BOLTZMANN_CONSTANT = 1.380649e-23  # J/K
SPEED_OF_LIGHT = 299792458.0  # m/s

# ---------------------------------------------------------------------------
# Consciousness thresholds
# ---------------------------------------------------------------------------

# Phi (IIT) based thresholds - used by consciousness.iit
PHI_THRESHOLDS = (0.01, 0.1, 0.5, 1.0, 2.0, 5.0)

# Bit-based (iPDF) thresholds from paper section 2.1.2:
#   Level 0 unconscious  C < 0.1
#   Level 1 proto        0.1 <= C < 1.0
#   Level 2 self-aware   1.0 <= C < 5.0
#   Level 3 highly       5.0 <= C < 10.0
#   Level 4 super        C >= 10.0
IPDF_THRESHOLDS = (0.1, 1.0, 5.0, 10.0)

# ---------------------------------------------------------------------------
# Distributed consensus parameters
# ---------------------------------------------------------------------------

PBFT_QUORUM_FRACTION = 2.0 / 3.0
WBFT_QUORUM_WEIGHT = 2.0 / 3.0
BYZANTINE_FAULT_TOLERANCE_RATIO = 1.0 / 3.0

# ---------------------------------------------------------------------------
# Numerical stability
# ---------------------------------------------------------------------------

EPS = 1e-10
COVARIANCE_REGULARIZER = 1e-6
