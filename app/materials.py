"""
Material properties and constants used across the design engine.

References:
    IS 456:2000 - Plain and Reinforced Concrete - Code of Practice
    IS 875 (Part 1):1987 - Unit weights of materials
"""

# Characteristic compressive strength of concrete, fck (N/mm2) - IS 456 Table 2
CONCRETE_GRADES = {
    "M15": 15,
    "M20": 20,
    "M25": 25,
    "M30": 30,
    "M35": 35,
    "M40": 40,
}

# Characteristic strength of reinforcement, fy (N/mm2) - IS 456 Table 3 / common practice
STEEL_GRADES = {
    "Fe250": 250,
    "Fe415": 415,
    "Fe500": 500,
    "Fe550": 550,
}

# Limiting neutral axis depth ratio, xu,max / d - IS 456 Cl. 38.1, Table not numbered
# (derived from strain compatibility at balanced condition)
XU_MAX_D_RATIO = {
    "Fe250": 0.53,
    "Fe415": 0.48,
    "Fe500": 0.46,
    "Fe550": 0.44,
}

# Unit weight of reinforced concrete (kN/m3) - IS 875 (Part 1)
UNIT_WEIGHT_RCC = 25.0

# Modulus of elasticity of steel (N/mm2) - IS 456 Cl. 5.6.3
ES = 2.0e5

# Standard bar diameters available (mm)
STANDARD_BAR_DIAMETERS = [8, 10, 12, 16, 20, 25, 28, 32]

# Standard stirrup (shear) bar diameters (mm)
STANDARD_STIRRUP_DIAMETERS = [6, 8, 10]


def fck(concrete_grade: str) -> float:
    """Return characteristic compressive strength fck (N/mm2) for a concrete grade like 'M25'."""
    try:
        return CONCRETE_GRADES[concrete_grade.upper()]
    except KeyError:
        raise ValueError(
            f"Unknown concrete grade '{concrete_grade}'. "
            f"Supported: {list(CONCRETE_GRADES)}"
        )


def fy(steel_grade: str) -> float:
    """Return characteristic strength fy (N/mm2) for a steel grade like 'Fe415'."""
    normalized = "Fe" + steel_grade.upper().replace("FE", "").strip()
    try:
        return STEEL_GRADES[normalized]
    except KeyError:
        raise ValueError(
            f"Unknown steel grade '{steel_grade}'. "
            f"Supported: {list(STEEL_GRADES)}"
        )


def xu_max_d(steel_grade: str) -> float:
    """Return limiting xu,max/d ratio for a steel grade - IS 456 Cl. 38.1."""
    normalized = "Fe" + steel_grade.upper().replace("FE", "").strip()
    try:
        return XU_MAX_D_RATIO[normalized]
    except KeyError:
        raise ValueError(
            f"Unknown steel grade '{steel_grade}'. "
            f"Supported: {list(XU_MAX_D_RATIO)}"
        )


def bar_area(diameter_mm: float) -> float:
    """Cross-sectional area of a single bar (mm2)."""
    import math
    return math.pi / 4 * diameter_mm ** 2
