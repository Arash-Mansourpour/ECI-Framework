"""ECI cybernetics package: autopoietic closure + second-order control.
Validation note: viability is a directional scalar with no external
reference (see docs/VALIDATION_STATUS.md)."""

from eci.cybernetics.autopoiesis import (
    AutopoieticNetwork,
    ashby_requisite_variety,
    viability_margin,
)

__all__ = ["AutopoieticNetwork", "viability_margin", "ashby_requisite_variety"]
