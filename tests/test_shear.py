"""
Reference-example checks for the shear design module.

Common section: b = 300 mm, d = 450 mm, M20, Fe415, Ast provided = 1000 mm^2
    pt = 100 * 1000 / (300*450) = 0.7407 %
    tau_c (Table 19, M20): interpolate between pt=0.50 (0.48) and pt=0.75 (0.56)
        frac = (0.7407-0.50)/(0.75-0.50) = 0.9628
        tau_c = 0.48 + 0.9628*(0.56-0.48) = 0.5570 N/mm^2
    tau_c,max (Table 20, M20) = 2.8 N/mm^2

Case A - Vu = 90 kN (tau_v just above tau_c, small Vus -> max spacing governs):
    tau_v = 90*1000/(300*450) = 0.6667 N/mm^2  (> tau_c -> designed stirrups)
    Vuc = 0.5570*300*450/1000 = 75.20 kN
    Vus = 90 - 75.20 = 14.80 kN
    Asv (2-legged, 8mm) = 2 * pi/4 * 8^2 = 100.53 mm^2
    Sv = 0.87*415*100.53*450 / (14.80*1000) = 1103 mm  (>> 300mm cap -> capped)

Case B - Vu = 150 kN (tau_v < tau_c,max, meaningful Vus):
    tau_v = 150*1000/135000 = 1.1111 N/mm^2  (< 2.8 -> section adequate)
    Vus = 150 - 75.20 = 74.80 kN
    Sv = 0.87*415*100.53*450 / (74.80*1000) = 218.4 mm (before rounding/capping)
"""

import pytest

from app.shear import (
    calc_pt_percent,
    calc_tau_c_N_mm2,
    calc_tau_c_max_N_mm2,
    calc_tau_v_N_mm2,
    design_shear_reinforcement,
)

B, D = 300, 450
FCK, FY = "M20", "Fe415"
AST_PROVIDED = 1000


def test_pt_and_tau_c_reference_case():
    pt = calc_pt_percent(AST_PROVIDED, B, D)
    assert pt == pytest.approx(0.7407, rel=1e-3)

    tau_c = calc_tau_c_N_mm2(pt, FCK)
    assert tau_c == pytest.approx(0.5570, rel=2e-3)


def test_tau_c_max_lookup():
    assert calc_tau_c_max_N_mm2(FCK) == pytest.approx(2.8, rel=1e-6)


def test_tau_c_table_clamps_outside_range():
    # below the table's lowest pt -> lowest tau_c; above the highest -> highest tau_c
    assert calc_tau_c_N_mm2(0.05, "M25") == pytest.approx(0.29, rel=1e-6)
    assert calc_tau_c_N_mm2(5.0, "M25") == pytest.approx(0.92, rel=1e-6)


def test_case_a_small_vus_spacing_capped_at_maximum():
    result = design_shear_reinforcement(
        vu_kN=90, b_mm=B, d_mm=D, ast_provided_mm2=AST_PROVIDED,
        fck_grade=FCK, steel_grade=FY,
    )
    assert result.tau_v == pytest.approx(0.6667, rel=1e-3)
    assert result.reinforcement_basis == "designed"
    assert result.vus_kN == pytest.approx(14.80, rel=2e-2)
    assert result.spacing_calculated_mm > result.spacing_max_allowed_mm
    assert result.spacing_provided_mm == pytest.approx(300, abs=1)
    assert result.section_adequate is True
    assert result.is_safe is True


def test_case_b_designed_spacing_within_cap():
    result = design_shear_reinforcement(
        vu_kN=150, b_mm=B, d_mm=D, ast_provided_mm2=AST_PROVIDED,
        fck_grade=FCK, steel_grade=FY,
    )
    assert result.vus_kN == pytest.approx(74.80, rel=2e-2)
    assert result.spacing_calculated_mm == pytest.approx(218.4, rel=2e-2)
    # rounded down to nearest 25mm and below the 300mm/0.75d cap
    assert result.spacing_provided_mm == pytest.approx(200, abs=1)
    assert result.is_safe is True


def test_section_inadequate_when_tau_v_exceeds_tau_c_max():
    # Vu large enough that tau_v > tau_c,max (2.8 N/mm2) for this section
    huge_vu = 2.9 * B * D / 1000 + 10  # kN, comfortably past tau_c,max
    result = design_shear_reinforcement(
        vu_kN=huge_vu, b_mm=B, d_mm=D, ast_provided_mm2=AST_PROVIDED,
        fck_grade=FCK, steel_grade=FY,
    )
    assert result.section_adequate is False
    assert result.is_safe is False
