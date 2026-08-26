"""
Reference-example checks for the reinforcement detailing module.

Effective depth: D=500, cover=25, stirrup=8, main bar=16mm
    d = 500 - 25 - 8 - 16/2 = 459 mm

Development length: 20mm deformed bar, Fe415, M25
    tau_bd = 1.4 * 1.6 = 2.24 N/mm^2
    sigma_s = 0.87 * 415 = 361.05 N/mm^2
    Ld = 20 * 361.05 / (4 * 2.24) = 806.1 mm

Bar combination search: Ast,required = 755.8 mm^2, b=300mm, cover=25mm, stirrup=8mm
    4 x 16mm -> area = 804.2 mm^2 (excess 6.4%), clear spacing = 56.7mm  <- lowest score
    3 x 20mm -> area = 942.5 mm^2 (excess 24.7%), clear spacing = 87mm
    2 x 25mm -> area = 981.7 mm^2 (excess 29.9%), clear spacing = 184mm
    all three fit and satisfy Cl. 26.3.2 (min spacing 25mm); 4x16mm should win
    on the default score weights (closest to required area, moderate bar count).
"""

import pytest

from app.reinforcement import (
    calc_clear_spacing_mm,
    calc_development_length_mm,
    derive_effective_depth_mm,
    find_bar_combinations,
    min_clear_spacing_mm,
    select_optimal_bars,
)

AST_REQUIRED = 755.8
B, COVER, STIRRUP_DIA = 300, 25, 8


def test_effective_depth_reference_case():
    d = derive_effective_depth_mm(overall_depth_mm=500, clear_cover_mm=25, stirrup_dia_mm=8, main_bar_dia_mm=16)
    assert d == pytest.approx(459, abs=1e-6)


def test_development_length_reference_case():
    ld = calc_development_length_mm(bar_dia_mm=20, steel_grade="Fe415", fck_grade="M25")
    assert ld == pytest.approx(806.1, rel=2e-3)


def test_min_clear_spacing():
    # 16mm bar vs 25mm aggregate: bar dia (16) < aggregate+5 (25) -> 25 governs
    assert min_clear_spacing_mm(16) == 25
    # 32mm bar > aggregate+5 (25) -> bar diameter governs
    assert min_clear_spacing_mm(32) == 32


def test_clear_spacing_calculation():
    spacing = calc_clear_spacing_mm(B, COVER, STIRRUP_DIA, bar_dia_mm=16, count=4)
    assert spacing == pytest.approx(56.7, rel=2e-2)


def test_clear_spacing_returns_none_when_bars_dont_fit():
    spacing = calc_clear_spacing_mm(b_mm=200, cover_mm=25, stirrup_dia_mm=8, bar_dia_mm=32, count=6)
    assert spacing is None


def test_bar_combination_search_finds_expected_candidates():
    combos = find_bar_combinations(AST_REQUIRED, B, COVER, STIRRUP_DIA)
    found = {(c.diameter_mm, c.count) for c in combos}
    assert (16, 4) in found
    assert (20, 3) in found
    assert (25, 2) in found


def test_optimal_bar_selection_prefers_low_excess_moderate_count():
    best = select_optimal_bars(AST_REQUIRED, B, COVER, STIRRUP_DIA)
    assert (best.diameter_mm, best.count) == (16, 4)
    assert best.area_provided_mm2 == pytest.approx(804.2, rel=2e-3)
    assert best.excess_fraction == pytest.approx(0.064, rel=2e-2)


def test_no_combination_raises_when_ast_required_too_high():
    with pytest.raises(ValueError):
        select_optimal_bars(ast_required_mm2=1_000_000, b_mm=B, cover_mm=COVER, stirrup_dia_mm=STIRRUP_DIA)
