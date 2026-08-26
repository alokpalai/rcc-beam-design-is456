"""
Reference-example checks for the flexure design module.

Reference case: b = 300 mm, d = 450 mm, D = 500 mm, M25, Fe415.

Mu,lim hand check (IS 456 Annex G-1.1(c), xu,max/d = 0.48 for Fe415):
    coeff = 0.36 * 0.48 * (1 - 0.42 * 0.48) = 0.13796352
    Mu,lim = coeff * 25 * 300 * 450^2 / 1e6 = 209.53 kNm

Ast,required hand check at Mu = 150 kNm (< Mu,lim, singly reinforced valid):
    discriminant = 1 - 4.6 * 150e6 / (25 * 300 * 450^2) = 0.545679
    Ast = 0.5 * (25/415) * 300 * 450 * (1 - sqrt(0.545679)) = 1062.7 mm^2 (approx)

Ast,min / Ast,max (IS 456 Cl. 26.5.1.1):
    Ast,min = 0.85 * 300 * 450 / 415 = 276.5 mm^2
    Ast,max = 0.04 * 300 * 500 = 6000 mm^2
"""

import pytest

from app.flexure import (
    calc_ast_max_mm2,
    calc_ast_min_mm2,
    calc_ast_required_mm2,
    calc_mu_lim_kNm,
    design_flexure_singly_reinforced,
)

B, D_EFF, D_OVERALL = 300, 450, 500
FCK, FY = "M25", "Fe415"


def test_mu_lim_reference_case():
    mu_lim = calc_mu_lim_kNm(B, D_EFF, FCK, FY)
    assert mu_lim == pytest.approx(209.53, rel=2e-3)


def test_ast_required_reference_case():
    ast = calc_ast_required_mm2(B, D_EFF, mu_kNm=150, fck_grade=FCK, steel_grade=FY)
    assert ast == pytest.approx(1062.7, rel=2e-3)


def test_ast_min_and_max():
    assert calc_ast_min_mm2(B, D_EFF, FY) == pytest.approx(276.5, rel=1e-3)
    assert calc_ast_max_mm2(B, D_OVERALL) == pytest.approx(6000, rel=1e-6)


def test_full_singly_reinforced_design_safe_case():
    result = design_flexure_singly_reinforced(
        b_mm=B, d_mm=D_EFF, overall_depth_mm=D_OVERALL,
        mu_kNm=150, fck_grade=FCK, steel_grade=FY,
    )
    assert result.needs_doubly_reinforced is False
    assert result.ast_design_mm2 == pytest.approx(1062.7, rel=2e-3)
    assert result.within_min_max_limits is True


def test_over_capacity_section_flags_doubly_reinforced():
    # Mu = 250 kNm > Mu,lim (~209.5 kNm) for this section -> needs compression steel
    result = design_flexure_singly_reinforced(
        b_mm=B, d_mm=D_EFF, overall_depth_mm=D_OVERALL,
        mu_kNm=250, fck_grade=FCK, steel_grade=FY,
    )
    assert result.needs_doubly_reinforced is True
    assert result.ast_required_mm2 is None
