"""
Serviceability (deflection) check using the span/effective-depth method.

Scope (current milestone): the simplified span-to-depth method only (no
direct deflection calculation, no crack-width check).

References (IS 456:2000):
    Cl. 23.2.1        - Basic span/effective-depth ratios for span <= 10 m:
                        cantilever 7, simply supported 20, continuous 26.
                        For span > 10 m, multiply the basic ratio by 10/span(m)
                        (except cantilevers, where deflection must be computed
                        explicitly - the simplified method does not apply).
    Fig. 4            - Modification factor kt for tension reinforcement,
                        a function of service stress fs and pt (% tension
                        steel provided). IS 456 gives this as a graph; the
                        formula used here is the standard closed-form fit to
                        that graph published in SP:24 (Explanatory Handbook
                        to IS 456) and used throughout Indian RCC design
                        software - not verbatim code text, but the accepted
                        analytical equivalent of Fig. 4.
                            kt = 1 / (0.225 + 0.00322*fs - 0.625*log10(pt))
    Note under Fig. 4  - Service stress estimate:
                            fs = 0.58 * fy * (Ast,required / Ast,provided)
    Fig. 5            - Modification factor kc for compression reinforcement
                        (empirical fit, saturates near 1.5):
                            kc = 1 + pc / (3 + pc), pc = 100*Asc/(b*d)
    Fig. 6            - Reduction factor kf for flanged (T/L) beams; kf = 1.0
                        for rectangular sections (not yet applicable - no
                        flanged-beam support in this milestone).
"""

import math
from dataclasses import dataclass

BASIC_SPAN_TO_DEPTH_RATIO = {
    "cantilever": 7,
    "simply_supported": 20,
    "continuous": 26,
}

LONG_SPAN_THRESHOLD_MM = 10_000  # Cl. 23.2.1(b)

# Empirical clamp on kt, matching the practical range of Fig. 4's curves
KT_MIN, KT_MAX = 0.4, 2.0
KC_MAX = 1.5  # Fig. 5 saturates near this value


def calc_service_stress_fs_N_mm2(fy: float, ast_required_mm2: float, ast_provided_mm2: float) -> float:
    """Estimated service stress in tension steel - note under IS 456 Fig. 4."""
    return 0.58 * fy * (ast_required_mm2 / ast_provided_mm2)


def calc_kt(fs_N_mm2: float, pt_percent: float) -> float:
    """Modification factor for tension reinforcement - IS 456 Fig. 4 (SP:24 fit)."""
    kt = 1.0 / (0.225 + 0.00322 * fs_N_mm2 - 0.625 * math.log10(pt_percent))
    return max(KT_MIN, min(KT_MAX, kt))


def calc_kc(pc_percent: float) -> float:
    """Modification factor for compression reinforcement - IS 456 Fig. 5. pc=0 -> kc=1.0."""
    if pc_percent <= 0:
        return 1.0
    kc = 1.0 + pc_percent / (3 + pc_percent)
    return min(KC_MAX, kc)


def calc_basic_ratio(support_condition: str, span_mm: float) -> tuple:
    """
    Basic span/depth ratio after the long-span correction (Cl. 23.2.1).

    Returns (basic_ratio, explicit_calc_required). explicit_calc_required is
    True only for a cantilever with span > 10 m, where the simplified method
    does not apply and deflection must be computed directly (not yet
    implemented - flagged, not silently approximated).
    """
    condition = support_condition.lower()
    if condition not in BASIC_SPAN_TO_DEPTH_RATIO:
        raise ValueError(
            f"Unknown support condition '{support_condition}'. "
            f"Supported: {list(BASIC_SPAN_TO_DEPTH_RATIO)}"
        )
    basic = BASIC_SPAN_TO_DEPTH_RATIO[condition]

    if span_mm <= LONG_SPAN_THRESHOLD_MM:
        return basic, False

    if condition == "cantilever":
        return basic, True  # explicit deflection calc required, not this method

    span_m = span_mm / 1000.0
    return basic * (10.0 / span_m), False


@dataclass
class ServiceabilityResult:
    actual_ratio: float
    basic_ratio: float
    kt: float
    kc: float
    kf: float
    allowable_ratio: float
    explicit_calc_required: bool
    is_safe: bool


def check_deflection_span_to_depth(
    span_mm: float,
    d_mm: float,
    support_condition: str,
    fy: float,
    ast_required_mm2: float,
    ast_provided_mm2: float,
    asc_provided_mm2: float = 0.0,
    b_mm: float = None,
) -> ServiceabilityResult:
    """
    Full span/effective-depth deflection check - IS 456 Cl. 23.2.1.

    b_mm is required only if asc_provided_mm2 > 0 (needed to compute pc for kc).
    kf (flanged-beam factor) is fixed at 1.0 - rectangular sections only.
    """
    if b_mm is None:
        raise ValueError("b_mm is required to compute pt (% tension steel) for the kt lookup.")

    basic_ratio, explicit_calc_required = calc_basic_ratio(support_condition, span_mm)
    pt = 100.0 * ast_provided_mm2 / (b_mm * d_mm)

    fs = calc_service_stress_fs_N_mm2(fy, ast_required_mm2, ast_provided_mm2)
    kt = calc_kt(fs, pt)

    pc = 100.0 * asc_provided_mm2 / (b_mm * d_mm) if asc_provided_mm2 > 0 else 0.0
    kc = calc_kc(pc)

    kf = 1.0  # rectangular section only, this milestone

    allowable_ratio = basic_ratio * kt * kc * kf
    actual_ratio = span_mm / d_mm

    is_safe = (not explicit_calc_required) and (actual_ratio <= allowable_ratio)

    return ServiceabilityResult(
        actual_ratio=actual_ratio,
        basic_ratio=basic_ratio,
        kt=kt,
        kc=kc,
        kf=kf,
        allowable_ratio=allowable_ratio,
        explicit_calc_required=explicit_calc_required,
        is_safe=is_safe,
    )
