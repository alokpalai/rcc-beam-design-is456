"""
Reference-example check for the load calculation module.

Hand-calculated reference (independent of the implementation, using the plain
IS 456 formulas):

    b = 300 mm, D = 500 mm, span = 5000 mm
    DL = 12 kN/m, LL = 8 kN/m
    self-weight = 0.3 * 0.5 * 25 = 3.75 kN/m
    total service load = 12 + 8 + 3.75 = 23.75 kN/m
    factored load, wu = 1.5 * 23.75 = 35.625 kN/m
    Mu = wu * L^2 / 8 = 35.625 * 5^2 / 8 = 111.328125 kNm
    Vu = wu * L / 2 = 35.625 * 5 / 2 = 89.0625 kN
"""

import pytest

from app.loads import BeamGeometry, compute_loads_simply_supported_udl


def test_simply_supported_udl_reference_case():
    geometry = BeamGeometry(span_mm=5000, width_mm=300, overall_depth_mm=500)
    result = compute_loads_simply_supported_udl(
        geometry, dead_load_udl_kn_m=12, live_load_udl_kn_m=8
    )

    assert result.self_weight_udl == pytest.approx(3.75, rel=1e-6)
    assert result.total_service_udl == pytest.approx(23.75, rel=1e-6)
    assert result.factored_udl == pytest.approx(35.625, rel=1e-6)
    assert result.max_bending_moment == pytest.approx(111.328125, rel=1e-6)
    assert result.max_shear_force == pytest.approx(89.0625, rel=1e-6)


def test_self_weight_can_be_excluded():
    geometry = BeamGeometry(span_mm=5000, width_mm=300, overall_depth_mm=500)
    result = compute_loads_simply_supported_udl(
        geometry, dead_load_udl_kn_m=12, live_load_udl_kn_m=8, include_self_weight=False
    )
    assert result.self_weight_udl == 0.0
    assert result.total_service_udl == pytest.approx(20.0, rel=1e-6)
