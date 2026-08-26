"""
Flexural design of rectangular RCC beams - Limit State of Collapse.

Scope (current milestone): singly reinforced sections only.
Doubly reinforced design (when Mu > Mu,lim) is a later milestone -
for now the section is flagged as needing a compression design, not
silently under-designed.

References (IS 456:2000):
    Cl. 38.1        - Limiting depth of neutral axis, xu,max
    Annex G, G-1.1   - Limit state of collapse: flexure, singly reinforced
    Cl. 26.5.1.1(a)  - Minimum reinforcement, Ast,min = 0.85 b d / fy
    Cl. 26.5.1.1(b)  - Maximum reinforcement, Ast,max = 0.04 b D
"""

import math
from dataclasses import dataclass

import numpy as np

from app.materials import fck as get_fck, fy as get_fy, xu_max_d


@dataclass
class FlexureResult:
    mu_kNm: float               # design (factored) moment
    mu_lim_kNm: float           # limiting moment of resistance (singly reinforced)
    needs_doubly_reinforced: bool
    ast_required_mm2: float     # from Annex G-1.1(b), or None if not applicable
    ast_min_mm2: float          # Cl. 26.5.1.1(a)
    ast_max_mm2: float          # Cl. 26.5.1.1(b)
    ast_design_mm2: float       # governing value: max(ast_required, ast_min), capped check vs ast_max
    within_min_max_limits: bool


def calc_mu_lim_kNm(b_mm: float, d_mm: float, fck_grade: str, steel_grade: str) -> float:
    """
    Limiting moment of resistance of a singly reinforced section (kNm).

    Mu,lim = 0.36 * (xu,max/d) * [1 - 0.42 * (xu,max/d)] * fck * b * d^2   (IS 456 Annex G, G-1.1(c))
    """
    fck_val = get_fck(fck_grade)
    ratio = xu_max_d(steel_grade)
    coeff = 0.36 * ratio * (1 - 0.42 * ratio)
    mu_lim_Nmm = coeff * fck_val * b_mm * d_mm ** 2
    return mu_lim_Nmm / 1e6  # N-mm -> kNm


def calc_ast_required_mm2(b_mm: float, d_mm: float, mu_kNm: float, fck_grade: str, steel_grade: str) -> float:
    """
    Required tension reinforcement for a singly reinforced section (mm2).

    From Mu = 0.87 fy Ast d [1 - Ast fy / (b d fck)], solved for Ast:

    Ast = 0.5 * (fck / fy) * b * d * [1 - sqrt(1 - 4.6 Mu / (fck b d^2))]

    (IS 456 Annex G-1.1(b), standard rearranged / SP:16 design-aid form)
    """
    fck_val = get_fck(fck_grade)
    fy_val = get_fy(steel_grade)
    mu_Nmm = mu_kNm * 1e6

    discriminant = 1 - (4.6 * mu_Nmm) / (fck_val * b_mm * d_mm ** 2)
    if discriminant < 0:
        raise ValueError(
            "Section is inadequate for a singly reinforced design "
            "(discriminant < 0 - increase b/d or use doubly reinforced design)."
        )

    ast = 0.5 * (fck_val / fy_val) * b_mm * d_mm * (1 - math.sqrt(discriminant))
    return ast


def calc_ast_min_mm2(b_mm: float, d_mm: float, steel_grade: str) -> float:
    """Minimum tension reinforcement (mm2) - IS 456 Cl. 26.5.1.1(a): Ast,min = 0.85 b d / fy."""
    fy_val = get_fy(steel_grade)
    return 0.85 * b_mm * d_mm / fy_val


def calc_ast_max_mm2(b_mm: float, overall_depth_mm: float) -> float:
    """Maximum tension reinforcement (mm2) - IS 456 Cl. 26.5.1.1(b): Ast,max = 0.04 b D."""
    return 0.04 * b_mm * overall_depth_mm


def design_flexure_singly_reinforced(
    b_mm: float,
    d_mm: float,
    overall_depth_mm: float,
    mu_kNm: float,
    fck_grade: str,
    steel_grade: str,
) -> FlexureResult:
    """
    Full singly-reinforced flexure design check for one section.

    Returns a FlexureResult. If mu_kNm exceeds Mu,lim, ast_required_mm2 is left
    as None and needs_doubly_reinforced=True (doubly reinforced design is a
    later milestone) - do NOT treat the result as safe in that case.
    """
    mu_lim = calc_mu_lim_kNm(b_mm, d_mm, fck_grade, steel_grade)
    ast_min = calc_ast_min_mm2(b_mm, d_mm, steel_grade)
    ast_max = calc_ast_max_mm2(b_mm, overall_depth_mm)

    needs_doubly = mu_kNm > mu_lim

    if needs_doubly:
        return FlexureResult(
            mu_kNm=mu_kNm,
            mu_lim_kNm=mu_lim,
            needs_doubly_reinforced=True,
            ast_required_mm2=None,
            ast_min_mm2=ast_min,
            ast_max_mm2=ast_max,
            ast_design_mm2=None,
            within_min_max_limits=False,
        )

    ast_required = calc_ast_required_mm2(b_mm, d_mm, mu_kNm, fck_grade, steel_grade)
    ast_design = max(ast_required, ast_min)
    within_limits = ast_design <= ast_max

    return FlexureResult(
        mu_kNm=mu_kNm,
        mu_lim_kNm=mu_lim,
        needs_doubly_reinforced=False,
        ast_required_mm2=ast_required,
        ast_min_mm2=ast_min,
        ast_max_mm2=ast_max,
        ast_design_mm2=ast_design,
        within_min_max_limits=within_limits,
    )

# --- Doubly reinforced design (IS 456 Annex G-1.2) --------------------------
# Use design_flexure_doubly_reinforced() only when design_flexure_singly_reinforced()
# reports needs_doubly_reinforced=True (i.e. Mu > Mu,lim).

# Design stress in compression reinforcement, fsc (N/mm2), as a function of
# d'/d - SP:16 (Design Aids to IS 456) design-aid table for Fe415 and Fe500.
# Fe250 is elastic-perfectly-plastic and yields well before these d'/d
# ratios, so fsc = 0.87*fy is used directly for Fe250 instead of a table.
FSC_TABLE_D_DASH_OVER_D = [0.05, 0.10, 0.15, 0.20]
FSC_TABLE = {
    "Fe415": [355, 353, 342, 329],
    "Fe500": [412, 412, 395, 370],
}

# fcc = design compressive stress in concrete at the level of the compression
# steel - standard approximation used in doubly-reinforced design (SP:16).
CONCRETE_STRESS_AT_COMPRESSION_STEEL_FACTOR = 0.45


def calc_fsc_N_mm2(steel_grade: str, d_dash_mm: float, d_mm: float) -> float:
    """
    Design stress in compression reinforcement, fsc (N/mm2) - SP:16 design aid,
    interpolated over d'/d = 0.05 to 0.20 (typical practical range).
    """
    if steel_grade == "Fe250":
        return 0.87 * get_fy(steel_grade)
    if steel_grade not in FSC_TABLE:
        raise ValueError(f"No fsc table for grade '{steel_grade}'. Supported: Fe250, Fe415, Fe500")

    d_dash_over_d = d_dash_mm / d_mm
    return float(np.interp(d_dash_over_d, FSC_TABLE_D_DASH_OVER_D, FSC_TABLE[steel_grade]))


@dataclass
class DoublyReinforcedResult:
    mu_kNm: float
    mu_lim_kNm: float
    mu2_kNm: float          # additional moment beyond Mu,lim, carried by Asc/Ast2
    ast1_mm2: float          # tension steel balancing the Mu,lim (concrete) part
    ast2_mm2: float          # additional tension steel balancing Mu2
    ast_total_mm2: float     # Ast1 + Ast2
    asc_mm2: float            # compression steel required
    fsc_N_mm2: float          # design stress used for the compression steel
    ast_max_mm2: float
    asc_max_mm2: float
    within_limits: bool


def design_flexure_doubly_reinforced(
    b_mm: float,
    d_mm: float,
    d_dash_mm: float,
    overall_depth_mm: float,
    mu_kNm: float,
    fck_grade: str,
    steel_grade: str,
) -> DoublyReinforcedResult:
    """
    Doubly reinforced flexure design - IS 456 Annex G-1.2.

    d_dash_mm is the effective cover to the centroid of compression
    reinforcement (distance from the extreme compression fibre), typically
    35-50 mm.
    """
    mu_lim = calc_mu_lim_kNm(b_mm, d_mm, fck_grade, steel_grade)
    if mu_kNm <= mu_lim:
        raise ValueError(
            f"Mu ({mu_kNm:.1f} kNm) <= Mu,lim ({mu_lim:.1f} kNm) - "
            "use design_flexure_singly_reinforced instead."
        )

    fck_val = get_fck(fck_grade)
    fy_val = get_fy(steel_grade)
    ratio = xu_max_d(steel_grade)
    xu_max = ratio * d_mm

    mu2 = mu_kNm - mu_lim
    mu2_Nmm = mu2 * 1e6

    ast1 = 0.36 * fck_val * b_mm * xu_max / (0.87 * fy_val)
    ast2 = mu2_Nmm / (0.87 * fy_val * (d_mm - d_dash_mm))
    ast_total = ast1 + ast2

    fsc = calc_fsc_N_mm2(steel_grade, d_dash_mm, d_mm)
    fcc = CONCRETE_STRESS_AT_COMPRESSION_STEEL_FACTOR * fck_val
    asc = ast2 * 0.87 * fy_val / (fsc - fcc)

    ast_max = calc_ast_max_mm2(b_mm, overall_depth_mm)   # Cl. 26.5.1.1(b)
    asc_max = calc_ast_max_mm2(b_mm, overall_depth_mm)   # Cl. 26.5.1.2, same 0.04bD limit
    within_limits = ast_total <= ast_max and asc <= asc_max

    return DoublyReinforcedResult(
        mu_kNm=mu_kNm, mu_lim_kNm=mu_lim, mu2_kNm=mu2,
        ast1_mm2=ast1, ast2_mm2=ast2, ast_total_mm2=ast_total,
        asc_mm2=asc, fsc_N_mm2=fsc,
        ast_max_mm2=ast_max, asc_max_mm2=asc_max, within_limits=within_limits,
    )