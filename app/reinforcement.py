"""
Reinforcement detailing: effective depth derivation, bar selection/optimization,
bar spacing checks, and development length.

References (IS 456:2000):
    Cl. 25.4          - Effective depth (overall depth less effective cover to
                        the centroid of tension reinforcement)
    Table 16          - Nominal cover to meet durability requirements (user
                        supplies cover directly for now; exposure-based lookup
                        is a possible future refinement)
    Cl. 26.3.2        - Minimum clear horizontal distance between parallel
                        reinforcement bars: not less than the bar diameter,
                        nor less than (nominal maximum aggregate size + 5 mm)
    Cl. 26.2.1        - Development length, Ld = phi * sigma_s / (4 * tau_bd)
    Cl. 26.2.1.1      - Design bond stress tau_bd for plain bars in tension
                        (M20=1.2, M25=1.4, M30=1.5, M35=1.7, M40=1.9 N/mm2),
                        increased by 60% for deformed (HYSD) bars
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.materials import STANDARD_BAR_DIAMETERS, bar_area, fy as get_fy

# Design bond stress, tau_bd (N/mm2), for PLAIN bars in tension - IS 456 Cl. 26.2.1.1
TAU_BD_PLAIN_BARS = {"M20": 1.2, "M25": 1.4, "M30": 1.5, "M35": 1.7, "M40": 1.9}

DEFORMED_BAR_INCREASE_FACTOR = 1.6   # Cl. 26.2.1.1, deformed (HYSD) bars in tension
COMPRESSION_BAR_INCREASE_FACTOR = 1.25  # Cl. 26.2.1.1, additional increase for compression

DEFAULT_AGGREGATE_SIZE_MM = 20  # nominal maximum aggregate size, common assumption
DEFAULT_BAR_COUNT_RANGE = range(2, 7)  # 2 to 6 bars per layer, practical range

# Score weights for bar-combination optimization - see optimization_score() docstring
DEFAULT_SCORE_WEIGHTS = (1.0, 0.05, 2.0)


def derive_effective_depth_mm(
    overall_depth_mm: float, clear_cover_mm: float, stirrup_dia_mm: float, main_bar_dia_mm: float
) -> float:
    """
    Effective depth, d (mm) - IS 456 Cl. 25.4, single layer of tension bars.

    d = D - clear cover - stirrup diameter - (main bar diameter / 2)
    """
    return overall_depth_mm - clear_cover_mm - stirrup_dia_mm - main_bar_dia_mm / 2.0


def min_clear_spacing_mm(bar_dia_mm: float, aggregate_size_mm: float = DEFAULT_AGGREGATE_SIZE_MM) -> float:
    """Minimum clear horizontal spacing between bars (mm) - IS 456 Cl. 26.3.2."""
    return max(bar_dia_mm, aggregate_size_mm + 5)


def calc_tau_bd_N_mm2(fck_grade: str, bar_type: str = "deformed") -> float:
    """Design bond stress, tau_bd (N/mm2) - IS 456 Cl. 26.2.1.1."""
    grade = fck_grade.upper()
    if grade not in TAU_BD_PLAIN_BARS:
        raise ValueError(
            f"No tabulated bond stress for grade '{fck_grade}' "
            f"(IS 456 lists M20 and above). Supported: {list(TAU_BD_PLAIN_BARS)}"
        )
    tau_bd = TAU_BD_PLAIN_BARS[grade]
    if bar_type == "deformed":
        tau_bd *= DEFORMED_BAR_INCREASE_FACTOR
    elif bar_type != "plain":
        raise ValueError("bar_type must be 'deformed' or 'plain'")
    return tau_bd


def calc_development_length_mm(
    bar_dia_mm: float, steel_grade: str, fck_grade: str,
    bar_type: str = "deformed", in_compression: bool = False,
) -> float:
    """
    Development length, Ld (mm) - IS 456 Cl. 26.2.1.

    Ld = phi * sigma_s / (4 * tau_bd), with sigma_s = 0.87 * fy (design stress
    in the bar at limit state, i.e. fully stressed tension reinforcement).
    """
    fy_val = get_fy(steel_grade)
    tau_bd = calc_tau_bd_N_mm2(fck_grade, bar_type)
    if in_compression:
        tau_bd *= COMPRESSION_BAR_INCREASE_FACTOR
    sigma_s = 0.87 * fy_val
    return (bar_dia_mm * sigma_s) / (4 * tau_bd)


@dataclass
class BarCombination:
    diameter_mm: float
    count: int
    area_provided_mm2: float
    excess_fraction: float      # (provided - required) / required
    clear_spacing_mm: float
    score: float                 # lower is better


def calc_clear_spacing_mm(
    b_mm: float, cover_mm: float, stirrup_dia_mm: float, bar_dia_mm: float, count: int
) -> Optional[float]:
    """
    Clear horizontal spacing between bars in a single layer (mm), or None if
    the bars do not physically fit within the width at all.
    """
    available_mm = b_mm - 2 * cover_mm - 2 * stirrup_dia_mm - count * bar_dia_mm
    if available_mm < 0:
        return None
    if count <= 1:
        return available_mm
    return available_mm / (count - 1)


def optimization_score(
    excess_fraction: float, count: int, clear_spacing_mm: float,
    weights: Sequence[float] = DEFAULT_SCORE_WEIGHTS,
) -> float:
    """
    Lower is better. score = w1*(excess steel fraction) + w2*(number of bars)
    + w3*(congestion penalty, ~1/clear_spacing).

    This rewards combinations close to the required area, with fewer bars,
    and more breathing room between bars. Weights are a starting point, not
    a code requirement - tune them if the recommended combos don't match
    engineering judgement on a given project.
    """
    w1, w2, w3 = weights
    congestion_penalty = 1.0 / (clear_spacing_mm + 1.0)
    return w1 * excess_fraction + w2 * count + w3 * congestion_penalty


def find_bar_combinations(
    ast_required_mm2: float,
    b_mm: float,
    cover_mm: float,
    stirrup_dia_mm: float,
    candidate_diameters: Sequence[float] = STANDARD_BAR_DIAMETERS,
    bar_count_range: range = DEFAULT_BAR_COUNT_RANGE,
    aggregate_size_mm: float = DEFAULT_AGGREGATE_SIZE_MM,
    weights: Sequence[float] = DEFAULT_SCORE_WEIGHTS,
) -> List[BarCombination]:
    """
    Search (diameter x count) combinations that meet Ast,required and fit
    within the beam width per Cl. 26.3.2, scored by optimization_score().

    Returns combinations sorted best (lowest score) first. Empty list means
    no candidate combination fits - widen the section or the search ranges.
    """
    results: List[BarCombination] = []
    for dia in candidate_diameters:
        area_each = bar_area(dia)
        for count in bar_count_range:
            area_total = count * area_each
            if area_total < ast_required_mm2:
                continue
            clear_spacing = calc_clear_spacing_mm(b_mm, cover_mm, stirrup_dia_mm, dia, count)
            if clear_spacing is None:
                continue
            required_spacing = min_clear_spacing_mm(dia, aggregate_size_mm)
            if count > 1 and clear_spacing < required_spacing:
                continue

            excess_fraction = (area_total - ast_required_mm2) / ast_required_mm2
            score = optimization_score(excess_fraction, count, clear_spacing, weights)
            results.append(BarCombination(
                diameter_mm=dia, count=count, area_provided_mm2=area_total,
                excess_fraction=excess_fraction, clear_spacing_mm=clear_spacing, score=score,
            ))

    results.sort(key=lambda c: c.score)
    return results


def select_optimal_bars(ast_required_mm2: float, b_mm: float, cover_mm: float, stirrup_dia_mm: float, **kwargs) -> BarCombination:
    """Return the single best bar combination, or raise if none fit."""
    combos = find_bar_combinations(ast_required_mm2, b_mm, cover_mm, stirrup_dia_mm, **kwargs)
    if not combos:
        raise ValueError(
            "No bar combination fits this section (Ast,required too high for "
            "the given width/cover, or search ranges too narrow)."
        )
    return combos[0]
