"""
Load calculation module.

Scope (current milestone): simply supported beam, uniformly distributed load (UDL) only.
Point loads / continuous beams are later milestones.

References:
    IS 456:2000 Cl. 36.4.1 - Partial safety factor for loads, limit state of collapse
        (1.5 x DL, 1.5 x LL for DL + LL combination)
    IS 875 (Part 1):1987 - Dead loads / unit weights
    IS 875 (Part 2):1987 - Live loads (imposed loads) - values supplied by user
"""

from dataclasses import dataclass

from app.materials import UNIT_WEIGHT_RCC

LOAD_FACTOR = 1.5  # IS 456 Table 18, DL + LL combination, limit state of collapse


@dataclass
class BeamGeometry:
    span_mm: float          # effective span, L
    width_mm: float          # breadth, b
    overall_depth_mm: float  # overall depth, D


def self_weight_udl(geometry: BeamGeometry) -> float:
    """
    Self-weight of the beam as a UDL (kN/m), from its own cross-section.

    self-weight = b (m) x D (m) x unit weight of RCC (kN/m3)
    """
    b_m = geometry.width_mm / 1000.0
    d_m = geometry.overall_depth_mm / 1000.0
    return b_m * d_m * UNIT_WEIGHT_RCC


@dataclass
class LoadSummary:
    dead_load_udl: float       # kN/m, excluding self-weight
    live_load_udl: float       # kN/m
    self_weight_udl: float     # kN/m
    total_service_udl: float   # kN/m, unfactored
    factored_udl: float        # kN/m, w_u
    max_bending_moment: float  # kNm, M_u = w_u * L^2 / 8
    max_shear_force: float     # kN,  V_u = w_u * L / 2


def compute_loads_simply_supported_udl(
    geometry: BeamGeometry,
    dead_load_udl_kn_m: float,
    live_load_udl_kn_m: float,
    include_self_weight: bool = True,
) -> LoadSummary:
    """
    Compute factored design moment and shear for a simply supported beam
    carrying a uniformly distributed load.

    Mu = wu * L^2 / 8   (span at midspan, max moment)
    Vu = wu * L / 2     (at supports, max shear)
    """
    sw = self_weight_udl(geometry) if include_self_weight else 0.0
    total_service = dead_load_udl_kn_m + live_load_udl_kn_m + sw
    factored = LOAD_FACTOR * total_service

    span_m = geometry.span_mm / 1000.0
    mu = factored * span_m ** 2 / 8.0   # kNm
    vu = factored * span_m / 2.0        # kN

    return LoadSummary(
        dead_load_udl=dead_load_udl_kn_m,
        live_load_udl=live_load_udl_kn_m,
        self_weight_udl=sw,
        total_service_udl=total_service,
        factored_udl=factored,
        max_bending_moment=mu,
        max_shear_force=vu,
    )
