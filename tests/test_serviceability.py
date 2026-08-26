"""
Reference-example check for the serviceability (deflection) module.

Continuing the B1 example (span=5000mm, b=300mm, d=459mm, Fe415, M25,
Ast,required=737.7 mm^2, Ast,provided=804.2 mm^2 [4x16mm], no compression steel):

    Basic L/d (simply supported, span <= 10m) = 20

    fs = 0.58 * 415 * (737.7/804.2) = 220.8 N/mm^2
    pt = 100 * 804.2 / (300*459) = 0.584 %
    kt = 1 / (0.225 + 0.00322*220.8 - 0.625*log10(0.584))
       = 1 / (0.225 + 0.7109 + 0.1466) = 1 / 1.0825 = 0.924

    kc = 1.0 (no compression steel)
    kf = 1.0 (rectangular section)

    Allowable L/d = 20 * 0.924 = 18.48
    Actual L/d = 5000/459 = 10.89  -> well within limit, SAFE
"""

import pytest

from app.serviceability import (
    calc_basic_ratio,
    calc_kc,
    calc_kt,
    calc_service_stress_fs_N_mm2,
    check_deflection_span_to_depth,
)

SPAN, B, D = 5000, 300, 459
FY = 415
AST_REQ, AST_PROV = 737.7, 804.2


def test_basic_ratio_short_span_simply_supported():
    basic, explicit_calc = calc_basic_ratio("simply_supported", SPAN)
    assert basic == 20
    assert explicit_calc is False


def test_basic_ratio_long_span_correction():
    # 12m span -> basic * 10/12
    basic, explicit_calc = calc_basic_ratio("simply_supported", 12_000)
    assert basic == pytest.approx(20 * 10 / 12, rel=1e-6)
    assert explicit_calc is False


def test_basic_ratio_long_span_cantilever_requires_explicit_calc():
    basic, explicit_calc = calc_basic_ratio("cantilever", 12_000)
    assert explicit_calc is True


def test_service_stress_reference_case():
    fs = calc_service_stress_fs_N_mm2(FY, AST_REQ, AST_PROV)
    assert fs == pytest.approx(220.8, rel=1e-2)


def test_kt_reference_case():
    fs = calc_service_stress_fs_N_mm2(FY, AST_REQ, AST_PROV)
    pt = 100 * AST_PROV / (B * D)
    kt = calc_kt(fs, pt)
    assert kt == pytest.approx(0.924, rel=1e-2)


def test_kc_no_compression_steel():
    assert calc_kc(0) == 1.0


def test_kc_with_compression_steel_saturates():
    assert calc_kc(1000) == pytest.approx(1.5, rel=1e-6)  # far beyond normal range, hits cap


def test_full_deflection_check_reference_case():
    result = check_deflection_span_to_depth(
        span_mm=SPAN, d_mm=D, support_condition="simply_supported",
        fy=FY, ast_required_mm2=AST_REQ, ast_provided_mm2=AST_PROV, b_mm=B,
    )
    assert result.actual_ratio == pytest.approx(10.89, rel=1e-2)
    assert result.allowable_ratio == pytest.approx(18.48, rel=1e-2)
    assert result.is_safe is True


def test_deflection_fails_when_actual_exceeds_allowable():
    # very shallow, lightly-reinforced beam -> should fail
    result = check_deflection_span_to_depth(
        span_mm=12_000, d_mm=300, support_condition="simply_supported",
        fy=FY, ast_required_mm2=1500, ast_provided_mm2=1520, b_mm=300,
    )
    assert result.actual_ratio > result.allowable_ratio
    assert result.is_safe is False
