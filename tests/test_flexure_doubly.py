"""
Reference-example check for doubly reinforced flexure design.

b=300, d=450, D=500, d'=50 (cover to compression steel), M25, Fe415, Mu=260 kNm
(Mu,lim for this section is ~209.5 kNm - see test_flexure.py - so Mu exceeds
it and doubly reinforced design is required).

Hand check:
    xu,max = 0.48 * 450 = 216 mm
    Mu,lim = 209.53 kNm (from calc_mu_lim_kNm)
    Mu2 = 260 - 209.53 = 50.47 kNm
    Ast1 = 0.36*25*300*216 / (0.87*415) = 1615.3 mm^2
    Ast2 = 50.47e6 / (0.87*415*(450-50)) = 349.5 mm^2
    Ast,total = 1964.7 mm^2
    d'/d = 50/450 = 0.1111 -> interpolate Fe415 table (0.10:353, 0.15:342) -> fsc = 350.6 N/mm^2
    fcc = 0.45*25 = 11.25 N/mm^2
    Asc = 349.5 * 0.87*415 / (350.6-11.25) = 371.8 mm^2
"""

import pytest

from app.flexure import calc_fsc_N_mm2, design_flexure_doubly_reinforced

B, D_EFF, D_DASH, D_OVERALL = 300, 450, 50, 500
FCK, FY = "M25", "Fe415"
MU = 260


def test_fsc_interpolation_reference_case():
    fsc = calc_fsc_N_mm2(FY, D_DASH, D_EFF)
    assert fsc == pytest.approx(350.6, rel=1e-2)


def test_doubly_reinforced_reference_case():
    result = design_flexure_doubly_reinforced(
        b_mm=B, d_mm=D_EFF, d_dash_mm=D_DASH, overall_depth_mm=D_OVERALL,
        mu_kNm=MU, fck_grade=FCK, steel_grade=FY,
    )
    assert result.mu_lim_kNm == pytest.approx(209.53, rel=2e-3)
    assert result.ast1_mm2 == pytest.approx(1615.3, rel=1e-2)
    assert result.ast2_mm2 == pytest.approx(349.5, rel=1e-2)
    assert result.ast_total_mm2 == pytest.approx(1964.7, rel=1e-2)
    assert result.asc_mm2 == pytest.approx(371.8, rel=1e-2)
    assert result.within_limits is True


def test_raises_if_mu_below_mu_lim():
    with pytest.raises(ValueError):
        design_flexure_doubly_reinforced(
            b_mm=B, d_mm=D_EFF, d_dash_mm=D_DASH, overall_depth_mm=D_OVERALL,
            mu_kNm=100, fck_grade=FCK, steel_grade=FY,  # well below Mu,lim
        )