"""
Quick manual smoke-test: load calc -> flexure -> bar selection -> shear ->
development length, printed as a plain-text summary. This is a scratch
script, not the final CLI/GUI.

Design sequence (standard iterative RCC practice - effective depth depends on
the main bar diameter, which isn't known until flexure design picks bars):
    1. Assume a trial main bar diameter -> trial effective depth
    2. Flexural design with the trial depth -> Ast,required
    3. Select actual bars (diameter x count) for that Ast
    4. Re-derive effective depth from the *selected* bar diameter
    5. Re-check flexure with the final depth (d only increases if the
       selected bar is smaller than the trial - conservative either way here)
    6. Shear design using the actual provided Ast (not an estimate)
    7. Development length for the selected bar

Run:
    python run_example.py
"""

from app.loads import BeamGeometry, compute_loads_simply_supported_udl
from app.flexure import design_flexure_singly_reinforced, design_flexure_doubly_reinforced
from app.shear import design_shear_reinforcement
from app.reinforcement import (
    calc_development_length_mm,
    derive_effective_depth_mm,
    select_optimal_bars,
)
from app.materials import fy as get_fy
from app.serviceability import check_deflection_span_to_depth
from app.serviceability import check_deflection_span_to_depth
from app.diagrams import compute_sfd_bmd_simply_supported_udl, plot_sfd_bmd

# --- Inputs ---------------------------------------------------------------
BEAM_NAME = "B1"
SPAN_MM = 5000
WIDTH_MM = 300
OVERALL_DEPTH_MM = 500
CLEAR_COVER_MM = 25         # nominal cover, mild exposure assumption (Table 16)
TRIAL_BAR_DIA_MM = 16       # assumed for the first effective-depth estimate
COMPRESSION_COVER_MM = 50   # d' - effective cover to compression steel centroid, typical assumption
CONCRETE_GRADE = "M25"
STEEL_GRADE = "Fe415"
DEAD_LOAD_KN_M = 12
LIVE_LOAD_KN_M = 8
STIRRUP_DIA_MM = 8
STIRRUP_LEGS = 2

# --- 1-2: Loads + trial flexure ---------------------------------------------
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

# --- 3-5: Bar selection + re-check with actual bar diameter ------------------
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

# --- 6: Shear design with actual provided Ast --------------------------------
shear = design_shear_reinforcement(
    vu_kN=loads.max_shear_force, b_mm=WIDTH_MM, d_mm=d_final,
    ast_provided_mm2=bars.area_provided_mm2, fck_grade=CONCRETE_GRADE,
    steel_grade=STEEL_GRADE, stirrup_dia_mm=STIRRUP_DIA_MM, legs=STIRRUP_LEGS,
)

# --- 7: Development length ----------------------------------------------------
ld = calc_development_length_mm(bars.diameter_mm, STEEL_GRADE, CONCRETE_GRADE)

# --- 8: Serviceability (deflection, span/depth method) -----------------------
ast_required_for_deflection = doubly.ast_total_mm2 if doubly else flexure_final.ast_required_mm2
deflection = check_deflection_span_to_depth(
    span_mm=SPAN_MM, d_mm=d_final, support_condition="simply_supported",
    fy=get_fy(STEEL_GRADE), ast_required_mm2=ast_required_for_deflection,
    ast_provided_mm2=bars.area_provided_mm2, b_mm=WIDTH_MM,
)

# --- 9: SFD/BMD -----------------------------------------------------------
x, V, M = compute_sfd_bmd_simply_supported_udl(SPAN_MM, loads.factored_udl)
fig = plot_sfd_bmd(x, V, M, beam_name=BEAM_NAME, save_path=f"sfd_bmd_{BEAM_NAME}.png")


# --- Report -----------------------------------------------------------------
print("=" * 55)
print(f"RCC BEAM DESIGN SUMMARY - {BEAM_NAME}")
print("=" * 55)
print(f"Span:              {SPAN_MM/1000:.2f} m")
print(f"Width:             {WIDTH_MM} mm")
print(f"Overall depth:     {OVERALL_DEPTH_MM} mm")
print(f"Effective depth:   {d_final:.1f} mm  (trial was {d_trial:.1f} mm @ {TRIAL_BAR_DIA_MM}mm bars)")
print(f"Concrete:          {CONCRETE_GRADE}")
print(f"Steel:             {STEEL_GRADE}")
print("-" * 55)
print(f"Self-weight:       {loads.self_weight_udl:.2f} kN/m")
print(f"Total service load:{loads.total_service_udl:.2f} kN/m")
print(f"Factored load:     {loads.factored_udl:.2f} kN/m")
print(f"Design Moment Mu:  {loads.max_bending_moment:.2f} kNm")
print(f"Design Shear Vu:   {loads.max_shear_force:.2f} kN")
print("-" * 55)
print(f"Mu,lim:            {flexure_final.mu_lim_kNm:.2f} kNm")
if doubly:
    print(f"DOUBLY REINFORCED SECTION (Mu > Mu,lim)")
    print(f"Ast1 / Ast2:       {doubly.ast1_mm2:.1f} / {doubly.ast2_mm2:.1f} mm^2")
    print(f"Ast,required (tension, total): {doubly.ast_total_mm2:.1f} mm^2")
    print(f"Asc,required (compression):    {doubly.asc_mm2:.1f} mm^2 (fsc={doubly.fsc_N_mm2:.1f} N/mm^2)")
    flex_status = "SAFE" if doubly.within_limits else "FAIL (exceeds max reinforcement)"
else:
    print(f"Ast,required:      {flexure_final.ast_required_mm2:.1f} mm^2")
    print(f"Ast,min / Ast,max: {flexure_final.ast_min_mm2:.1f} / {flexure_final.ast_max_mm2:.1f} mm^2")
    flex_status = "SAFE" if flexure_final.within_min_max_limits else "FAIL (exceeds Ast,max)"
print(f"Flexure status:    {flex_status}")
print("-" * 55)
print(f"Main reinforcement: {bars.count} x {bars.diameter_mm:.0f} mm  "
      f"(provided {bars.area_provided_mm2:.1f} mm^2, {bars.excess_fraction*100:.1f}% excess)")
print(f"Clear bar spacing: {bars.clear_spacing_mm:.1f} mm")
print(f"Development length Ld: {ld:.0f} mm")
print("-" * 55)
print(f"tau_v / tau_c / tau_c,max: {shear.tau_v:.3f} / {shear.tau_c:.3f} / {shear.tau_c_max:.2f} N/mm^2")
print(f"Stirrups:          {STIRRUP_LEGS}-legged {STIRRUP_DIA_MM} mm @ {shear.spacing_provided_mm:.0f} mm c/c "
      f"({shear.reinforcement_basis})")
shear_status = "SAFE" if shear.is_safe else "FAIL"
print(f"Shear status:      {shear_status}")
print("-" * 55)
print(f"L/d actual / allowable: {deflection.actual_ratio:.2f} / {deflection.allowable_ratio:.2f}  "
      f"(basic {deflection.basic_ratio:.1f}, kt={deflection.kt:.3f}, kc={deflection.kc:.2f})")
deflection_status = "SAFE" if deflection.is_safe else "FAIL"
print(f"Serviceability:    {deflection_status}")
print("=" * 55)
overall_safe = flex_status == "SAFE" and shear.is_safe and deflection.is_safe
print(f"OVERALL STATUS: {'SAFE' if overall_safe else 'NOT SAFE - see above'}")
print("NOTE: Ductile-detailing checks (IS 13920) and crack-width checks are")
print("      not implemented yet.")
print(f"SFD/BMD saved to: sfd_bmd_{BEAM_NAME}.png")
