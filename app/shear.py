"""
Shear design of rectangular RCC beams - Limit State of Collapse.

Scope (current milestone): vertical (2-legged, or user-specified legs) stirrups
only, for a section with known Vu and provided tension steel. Bent-up bars /
inclined stirrups are not covered.

References (IS 456:2000):
    Cl. 40.1              - Nominal shear stress, tau_v = Vu / (b*d)
    Cl. 40.2.1, Table 19   - Design shear strength of concrete, tau_c
                             (function of pt = 100*Ast/(b*d) and fck; code permits
                             linear interpolation between tabulated pt values)
    Cl. 40.2.3, Table 20   - Maximum shear stress, tau_c,max (section fails if
                             tau_v exceeds this regardless of stirrups provided)
    Cl. 40.4               - Design shear reinforcement: Vus = Vu - tau_c*b*d,
                             Sv = 0.87*fy*Asv*d / Vus
    Cl. 40.3               - Minimum shear reinforcement when tau_v <= tau_c:
                             Sv <= 0.87*fy*Asv / (0.4*b)
    Cl. 26.5.1.5           - Maximum spacing of vertical stirrups: lesser of
                             0.75*d and 300 mm
"""

import numpy as np
from dataclasses import dataclass

from app.materials import bar_area, fy as get_fy

# IS 456 Table 19 - pt (%) values for which tau_c is tabulated
PT_VALUES = [0.15, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 2.25, 2.50, 2.75, 3.00]

# IS 456 Table 19 - design shear strength of concrete, tau_c (N/mm2)
TAU_C_TABLE = {
    "M15": [0.28, 0.35, 0.46, 0.54, 0.60, 0.64, 0.68, 0.71, 0.71, 0.71, 0.71, 0.71, 0.71],
    "M20": [0.28, 0.36, 0.48, 0.56, 0.62, 0.67, 0.72, 0.75, 0.79, 0.81, 0.82, 0.82, 0.82],
    "M25": [0.29, 0.36, 0.49, 0.57, 0.64, 0.70, 0.74, 0.78, 0.82, 0.85, 0.88, 0.90, 0.92],
    "M30": [0.29, 0.37, 0.50, 0.59, 0.66, 0.71, 0.76, 0.80, 0.84, 0.88, 0.91, 0.94, 0.96],
    "M35": [0.29, 0.37, 0.50, 0.59, 0.67, 0.73, 0.78, 0.82, 0.86, 0.90, 0.93, 0.96, 0.99],
    "M40": [0.30, 0.38, 0.51, 0.60, 0.68, 0.74, 0.79, 0.84, 0.88, 0.92, 0.95, 0.98, 1.01],
}

# IS 456 Table 20 - maximum shear stress, tau_c,max (N/mm2)
TAU_C_MAX = {"M15": 2.5, "M20": 2.8, "M25": 3.1, "M30": 3.5, "M35": 3.7, "M40": 4.0}

MAX_STIRRUP_SPACING_MM = 300  # Cl. 26.5.1.5 (absolute cap; also capped at 0.75*d)


def calc_tau_v_N_mm2(vu_kN: float, b_mm: float, d_mm: float) -> float:
    """Nominal shear stress, tau_v (N/mm2) - IS 456 Cl. 40.1."""
    return (vu_kN * 1000) / (b_mm * d_mm)


def calc_pt_percent(ast_mm2: float, b_mm: float, d_mm: float) -> float:
    """Percentage tension reinforcement, pt = 100 * Ast / (b*d) - used to enter Table 19."""
    return 100.0 * ast_mm2 / (b_mm * d_mm)


def calc_tau_c_N_mm2(pt_percent: float, fck_grade: str) -> float:
    """
    Design shear strength of concrete, tau_c (N/mm2) - IS 456 Table 19.

    Linearly interpolated between tabulated pt values (permitted by the code).
    Clamped at the table's ends: pt < 0.15% uses the 0.15% value, pt > 3.00%
    uses the 3.00% value (per the note under Table 19).
    """
    grade = fck_grade.upper()
    if grade not in TAU_C_TABLE:
        raise ValueError(f"No Table 19 data for grade '{fck_grade}'. Supported: {list(TAU_C_TABLE)}")
    return float(np.interp(pt_percent, PT_VALUES, TAU_C_TABLE[grade]))


def calc_tau_c_max_N_mm2(fck_grade: str) -> float:
    """Maximum shear stress, tau_c,max (N/mm2) - IS 456 Table 20."""
    grade = fck_grade.upper()
    if grade not in TAU_C_MAX:
        raise ValueError(f"No Table 20 data for grade '{fck_grade}'. Supported: {list(TAU_C_MAX)}")
    return TAU_C_MAX[grade]


def round_down_spacing(value_mm: float, step_mm: float = 25.0) -> float:
    """Round a calculated spacing down to a practical site value (nearest lower multiple of step_mm)."""
    return float(np.floor(value_mm / step_mm) * step_mm)


@dataclass
class ShearResult:
    tau_v: float                 # N/mm2, Cl. 40.1
    pt_percent: float             # %, based on Ast provided
    tau_c: float                  # N/mm2, Table 19
    tau_c_max: float              # N/mm2, Table 20
    section_adequate: bool        # tau_v <= tau_c,max (else section must be redesigned)
    reinforcement_basis: str      # "minimum" (tau_v <= tau_c) or "designed" (tau_v > tau_c)
    vus_kN: float                 # shear to be resisted by stirrups (0 if minimum governs)
    asv_mm2: float                # area of shear reinforcement (both/all legs)
    spacing_calculated_mm: float  # from strength/minimum-steel equation, before capping
    spacing_max_allowed_mm: float # lesser of 0.75d and 300mm - Cl. 26.5.1.5
    spacing_provided_mm: float    # governing spacing, rounded down to a practical value
    is_safe: bool                 # section_adequate AND spacing_provided <= spacing_max_allowed


def design_shear_reinforcement(
    vu_kN: float,
    b_mm: float,
    d_mm: float,
    ast_provided_mm2: float,
    fck_grade: str,
    steel_grade: str,
    stirrup_dia_mm: float = 8,
    legs: int = 2,
) -> ShearResult:
    """
    Full vertical-stirrup shear design check for one section.

    If section_adequate is False (tau_v > tau_c,max), the section itself is
    inadequate in shear - no amount of stirrups fixes this; b or d must increase.
    """
    tau_v = calc_tau_v_N_mm2(vu_kN, b_mm, d_mm)
    pt = calc_pt_percent(ast_provided_mm2, b_mm, d_mm)
    tau_c = calc_tau_c_N_mm2(pt, fck_grade)
    tau_c_max = calc_tau_c_max_N_mm2(fck_grade)
    section_adequate = tau_v <= tau_c_max

    fy_val = get_fy(steel_grade)
    asv = legs * bar_area(stirrup_dia_mm)
    spacing_max_allowed = min(0.75 * d_mm, MAX_STIRRUP_SPACING_MM)

    if tau_v <= tau_c:
        # Cl. 40.3 - minimum shear reinforcement governs
        reinforcement_basis = "minimum"
        vus_kN = 0.0
        spacing_calculated = 0.87 * fy_val * asv / (0.4 * b_mm)
    else:
        # Cl. 40.4 - stirrups designed to carry the excess shear
        reinforcement_basis = "designed"
        vus_kN = vu_kN - (tau_c * b_mm * d_mm) / 1000.0
        spacing_calculated = (0.87 * fy_val * asv * d_mm) / (vus_kN * 1000.0)

    spacing_governing = min(spacing_calculated, spacing_max_allowed)
    spacing_provided = round_down_spacing(spacing_governing)

    is_safe = bool(section_adequate and spacing_provided <= spacing_max_allowed and spacing_provided > 0)

    return ShearResult(
        tau_v=tau_v,
        pt_percent=pt,
        tau_c=tau_c,
        tau_c_max=tau_c_max,
        section_adequate=section_adequate,
        reinforcement_basis=reinforcement_basis,
        vus_kN=vus_kN,
        asv_mm2=asv,
        spacing_calculated_mm=spacing_calculated,
        spacing_max_allowed_mm=spacing_max_allowed,
        spacing_provided_mm=spacing_provided,
        is_safe=is_safe,
    )
