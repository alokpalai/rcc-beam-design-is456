"""
Generates a reinforcement detailing schematic (cross-section + longitudinal
elevation) for a beam, using the same design pipeline as run_example.py.

This is a design visualization, not a construction-ready drawing.

Run:
    python generate_drawing.py

Creates: drawings/Beam_Drawing_<BEAM_NAME>.png
"""

import os

from app.loads import BeamGeometry, compute_loads_simply_supported_udl
from app.flexure import design_flexure_singly_reinforced, design_flexure_doubly_reinforced
from app.shear import design_shear_reinforcement
from app.reinforcement import derive_effective_depth_mm, select_optimal_bars
from app.drawing import generate_reinforcement_drawing

# --- Inputs (same B1 reference case) -----------------------------------------
BEAM_NAME = "B1"
SPAN_MM = 5000
WIDTH_MM = 300
OVERALL_DEPTH_MM = 500
CLEAR_COVER_MM = 25
TRIAL_BAR_DIA_MM = 16
COMPRESSION_COVER_MM = 50
CONCRETE_GRADE = "M25"
STEEL_GRADE = "Fe415"
DEAD_LOAD_KN_M = 12
LIVE_LOAD_KN_M = 8
STIRRUP_DIA_MM = 8
STIRRUP_LEGS = 2

NOMINAL_HANGER_BAR_DIA_MM = 10  # detailing practice, not a strength requirement
NOMINAL_HANGER_BAR_COUNT = 2

# --- Design pipeline (same sequence as run_example.py) -----------------------
geometry = BeamGeometry(span_mm=SPAN_MM, width_mm=WIDTH_MM, overall_depth_mm=OVERALL_DEPTH_MM)
loads = compute_loads_simply_supported_udl(geometry, DEAD_LOAD_KN_M, LIVE_LOAD_KN_M)

d_trial = derive_effective_depth_mm(OVERALL_DEPTH_MM, CLEAR_COVER_MM, STIRRUP_DIA_MM, TRIAL_BAR_DIA_MM)
flexure_trial = design_flexure_singly_reinforced(
    b_mm=WIDTH_MM, d_mm=d_trial, overall_depth_mm=OVERALL_DEPTH_MM,
    mu_kNm=loads.max_bending_moment, fck_grade=CONCRETE_GRADE, steel_grade=STEEL_GRADE,
)

doubly = None
if flexure_trial.needs_doubly_reinforced:
    doubly = design_flexure_doubly_reinforced(
        b_mm=WIDTH_MM, d_mm=d_trial, d_dash_mm=COMPRESSION_COVER_MM, overall_depth_mm=OVERALL_DEPTH_MM,
        mu_kNm=loads.max_bending_moment, fck_grade=CONCRETE_GRADE, steel_grade=STEEL_GRADE,
    )

tension_ast_required = doubly.ast_total_mm2 if doubly else flexure_trial.ast_design_mm2
bars = select_optimal_bars(tension_ast_required, WIDTH_MM, CLEAR_COVER_MM, STIRRUP_DIA_MM)
d_final = derive_effective_depth_mm(OVERALL_DEPTH_MM, CLEAR_COVER_MM, STIRRUP_DIA_MM, bars.diameter_mm)

flexure_final = design_flexure_singly_reinforced(
    b_mm=WIDTH_MM, d_mm=d_final, overall_depth_mm=OVERALL_DEPTH_MM,
    mu_kNm=loads.max_bending_moment, fck_grade=CONCRETE_GRADE, steel_grade=STEEL_GRADE,
)
if flexure_final.needs_doubly_reinforced:
    doubly = design_flexure_doubly_reinforced(
        b_mm=WIDTH_MM, d_mm=d_final, d_dash_mm=COMPRESSION_COVER_MM, overall_depth_mm=OVERALL_DEPTH_MM,
        mu_kNm=loads.max_bending_moment, fck_grade=CONCRETE_GRADE, steel_grade=STEEL_GRADE,
    )
else:
    doubly = None

shear = design_shear_reinforcement(
    vu_kN=loads.max_shear_force, b_mm=WIDTH_MM, d_mm=d_final,
    ast_provided_mm2=bars.area_provided_mm2, fck_grade=CONCRETE_GRADE,
    steel_grade=STEEL_GRADE, stirrup_dia_mm=STIRRUP_DIA_MM, legs=STIRRUP_LEGS,
)

# --- Top reinforcement: real compression steel if doubly reinforced, --------
# otherwise nominal hanger bars (standard detailing practice, not calculated
# for strength - only used to hold the stirrups in place).
if doubly:
    top_bars = select_optimal_bars(doubly.asc_mm2, WIDTH_MM, COMPRESSION_COVER_MM, STIRRUP_DIA_MM)
    top_bar_dia = top_bars.diameter_mm
    top_bar_count = top_bars.count
    top_cover = COMPRESSION_COVER_MM
    is_nominal_top = False
else:
    top_bar_dia = NOMINAL_HANGER_BAR_DIA_MM
    top_bar_count = NOMINAL_HANGER_BAR_COUNT
    top_cover = None
    is_nominal_top = True

# --- Generate and save the drawing --------------------------------------------
os.makedirs("drawings", exist_ok=True)
output_path = f"drawings/Beam_Drawing_{BEAM_NAME}.png"

fig = generate_reinforcement_drawing(
    beam_name=BEAM_NAME, span_mm=SPAN_MM, b_mm=WIDTH_MM, D_mm=OVERALL_DEPTH_MM,
    cover_mm=CLEAR_COVER_MM, stirrup_dia_mm=STIRRUP_DIA_MM,
    stirrup_spacing_mm=shear.spacing_provided_mm,
    bottom_bar_dia_mm=bars.diameter_mm, bottom_bar_count=bars.count,
    top_bar_dia_mm=top_bar_dia, top_bar_count=top_bar_count,
    top_cover_mm=top_cover, is_nominal_top=is_nominal_top,
    save_path=output_path,
)

print(f"Saved {output_path}")
print(f"Bottom: {bars.count} x {bars.diameter_mm:.0f}mm | "
      f"Top: {top_bar_count} x {top_bar_dia:.0f}mm{' (nominal)' if is_nominal_top else ''} | "
      f"Stirrups @ {shear.spacing_provided_mm:.0f}mm c/c")
