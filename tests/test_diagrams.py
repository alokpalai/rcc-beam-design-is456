"""
Reference-example check for SFD/BMD generation.

Same B1 beam as the other tests: span=5000mm, wu=35.625 kN/m (factored).
    x=0.00: V=89.0625 kN,  M=0 kNm
    x=1.25: V=44.5312 kN,  M=83.4961 kNm
    x=2.50: V=0 kN,        M=111.3281 kNm (peak, matches Mu elsewhere)
    x=3.75: V=-44.5312 kN, M=83.4961 kNm
    x=5.00: V=-89.0625 kN, M=0 kNm
"""

import pytest

from app.diagrams import compute_sfd_bmd_simply_supported_udl

SPAN_MM = 5000
WU = 35.625


def test_sfd_bmd_reference_points():
    x, V, M = compute_sfd_bmd_simply_supported_udl(SPAN_MM, WU, num_points=5)

    assert x[0] == pytest.approx(0.0)
    assert x[-1] == pytest.approx(5.0)

    assert V[0] == pytest.approx(89.0625, rel=1e-4)
    assert V[2] == pytest.approx(0.0, abs=1e-9)
    assert V[-1] == pytest.approx(-89.0625, rel=1e-4)

    assert M[0] == pytest.approx(0.0, abs=1e-9)
    assert M[2] == pytest.approx(111.328125, rel=1e-4)
    assert M[-1] == pytest.approx(0.0, abs=1e-9)


def test_bmd_peak_matches_manual_formula():
    x, V, M = compute_sfd_bmd_simply_supported_udl(SPAN_MM, WU, num_points=101)
    span_m = SPAN_MM / 1000
    expected_peak = WU * span_m ** 2 / 8  # standard Mu = wL^2/8
    assert M.max() == pytest.approx(expected_peak, rel=1e-3)