"""
Reference-example check for the reinforcement drawing geometry.

b=300, cover=25, stirrup=8, bar=16mm, count=4 (same B1 reference case):
    available = 300 - 2*25 - 2*8 - 4*16 = 170 mm
    gap = 170/3 = 56.67 mm (matches app/reinforcement.py's clear spacing test)
    start = 25 + 8 + 8 = 41 mm
    positions: 41, 113.67, 186.33, 259
    last position + bar radius (8) = 267 = b - cover - stirrup (300-25-8) - touches
    the stirrup exactly, as expected for a fully-spread symmetric layout.
"""

import pytest

from app.drawing import compute_bar_x_positions


def test_bar_positions_reference_case():
    positions = compute_bar_x_positions(b_mm=300, cover_mm=25, stirrup_dia_mm=8, bar_dia_mm=16, count=4)
    assert len(positions) == 4
    assert positions[0] == pytest.approx(41, abs=0.1)
    assert positions[-1] == pytest.approx(259, abs=0.1)
    # evenly spaced
    gaps = [positions[i + 1] - positions[i] for i in range(3)]
    assert gaps[0] == pytest.approx(gaps[1], rel=1e-6)
    assert gaps[1] == pytest.approx(gaps[2], rel=1e-6)


def test_single_bar_centers_in_width():
    positions = compute_bar_x_positions(b_mm=300, cover_mm=25, stirrup_dia_mm=8, bar_dia_mm=20, count=1)
    assert positions == [150]


def test_bars_fit_within_stirrup_bounds():
    b, cover, stirrup, dia, count = 300, 25, 8, 16, 4
    positions = compute_bar_x_positions(b, cover, stirrup, dia, count)
    inner_left = cover + stirrup
    inner_right = b - cover - stirrup
    for x in positions:
        assert inner_left <= x - dia / 2
        assert x + dia / 2 <= inner_right + 1e-6
