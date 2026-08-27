"""
Generates a PDF design report for a beam, using the same calculation
engine and design sequence as run_example.py / streamlit_app.py.

Run:
    python generate_report.py

Creates: reports/Beam_Design_<BEAM_NAME>.pdf
"""

import io
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)

from app.loads import BeamGeometry, compute_loads_simply_supported_udl
from app.flexure import design_flexure_singly_reinforced, design_flexure_doubly_reinforced
from app.shear import design_shear_reinforcement
from app.reinforcement import calc_development_length_mm, derive_effective_depth_mm, select_optimal_bars
from app.materials import fy as get_fy
from app.serviceability import check_deflection_span_to_depth
from app.diagrams import compute_sfd_bmd_simply_supported_udl, plot_sfd_bmd

# --- Inputs (same as run_example.py's B1 reference case) --------------------
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

# --- Design pipeline (identical sequence to run_example.py) -----------------
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

ld = calc_development_length_mm(bars.diameter_mm, STEEL_GRADE, CONCRETE_GRADE)

ast_required_for_deflection = doubly.ast_total_mm2 if doubly else flexure_final.ast_required_mm2
deflection = check_deflection_span_to_depth(
    span_mm=SPAN_MM, d_mm=d_final, support_condition="simply_supported",
    fy=get_fy(STEEL_GRADE), ast_required_mm2=ast_required_for_deflection,
    ast_provided_mm2=bars.area_provided_mm2, b_mm=WIDTH_MM,
)

flex_status = doubly.within_limits if doubly else flexure_final.within_min_max_limits
overall_safe = flex_status and shear.is_safe and deflection.is_safe

x, V, M = compute_sfd_bmd_simply_supported_udl(SPAN_MM, loads.factored_udl)
sfd_bmd_fig = plot_sfd_bmd(x, V, M, beam_name=BEAM_NAME, figsize=(7, 5))

# --- PDF styling helpers ------------------------------------------------------
styles = getSampleStyleSheet()
styles.add(ParagraphStyle("SectionHeading", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle("SafeStatus", parent=styles["Normal"], textColor=colors.HexColor("#1a7f37"), fontSize=12, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("FailStatus", parent=styles["Normal"], textColor=colors.HexColor("#cf222e"), fontSize=12, fontName="Helvetica-Bold"))

TABLE_STYLE = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
])


def kv_table(header, rows, col_widths=(7 * cm, 5 * cm, 4.5 * cm)):
    data = [header] + rows
    t = Table(data, colWidths=list(col_widths))
    t.setStyle(TABLE_STYLE)
    return t


def status_flowable(label, is_safe):
    style = styles["SafeStatus"] if is_safe else styles["FailStatus"]
    text = f"[OK] {label}: SAFE" if is_safe else f"[FAIL] {label}: FAIL"
    return Paragraph(text, style)


# --- Build the document -------------------------------------------------------
os.makedirs("reports", exist_ok=True)
output_path = f"reports/Beam_Design_{BEAM_NAME}.pdf"
doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
story = []

story.append(Paragraph(f"RCC BEAM DESIGN REPORT - {BEAM_NAME}", styles["Title"]))
story.append(Paragraph(f"IS 456:2000 Limit State Design | Generated {date.today().isoformat()}", styles["Normal"]))
story.append(Spacer(1, 10))

# 1. Design Parameters
story.append(Paragraph("1. Design Parameters", styles["SectionHeading"]))
story.append(kv_table(
    ["Parameter", "Value", "Unit"],
    [
        ["Span", f"{SPAN_MM/1000:.2f}", "m"],
        ["Width, b", f"{WIDTH_MM}", "mm"],
        ["Overall Depth, D", f"{OVERALL_DEPTH_MM}", "mm"],
        ["Clear Cover", f"{CLEAR_COVER_MM}", "mm"],
        ["Support Condition", "Simply Supported", "-"],
        ["Loading", "Uniformly Distributed", "-"],
    ],
))

# 2. Material Properties
story.append(Paragraph("2. Material Properties", styles["SectionHeading"]))
story.append(kv_table(
    ["Parameter", "Value", "Unit"],
    [
        ["Concrete Grade", CONCRETE_GRADE, "-"],
        ["Steel Grade", STEEL_GRADE, "-"],
        ["Stirrup Diameter", f"{STIRRUP_DIA_MM}", "mm"],
        ["Stirrup Legs", f"{STIRRUP_LEGS}", "-"],
    ],
))

# 3. Load Calculation
story.append(Paragraph("3. Load Calculation", styles["SectionHeading"]))
story.append(kv_table(
    ["Parameter", "Value", "Unit"],
    [
        ["Dead Load (excl. self-weight)", f"{DEAD_LOAD_KN_M:.2f}", "kN/m"],
        ["Live Load", f"{LIVE_LOAD_KN_M:.2f}", "kN/m"],
        ["Self-weight", f"{loads.self_weight_udl:.2f}", "kN/m"],
        ["Total Service Load", f"{loads.total_service_udl:.2f}", "kN/m"],
        ["Factored Load, wu (1.5 x DL+LL)", f"{loads.factored_udl:.2f}", "kN/m"],
    ],
))

# 4-5. Bending Moment & Shear Force
story.append(Paragraph("4. Bending Moment and Shear Force", styles["SectionHeading"]))
story.append(kv_table(
    ["Parameter", "Value", "Unit"],
    [
        ["Design Moment, Mu = wu.L^2/8", f"{loads.max_bending_moment:.2f}", "kNm"],
        ["Design Shear, Vu = wu.L/2", f"{loads.max_shear_force:.2f}", "kN"],
        ["Effective Depth, d", f"{d_final:.1f}", "mm"],
    ],
))

# 6. Flexural Design
story.append(Paragraph("6. Flexural Design", styles["SectionHeading"]))
flexure_rows = [
    ["Mu,lim (Annex G-1.1(c))", f"{flexure_final.mu_lim_kNm:.2f}", "kNm"],
]
if doubly:
    flexure_rows += [
        ["Section Type", "Doubly Reinforced", "-"],
        ["Ast1 (balances Mu,lim)", f"{doubly.ast1_mm2:.1f}", "mm^2"],
        ["Ast2 (balances Mu2)", f"{doubly.ast2_mm2:.1f}", "mm^2"],
        ["Ast, total required", f"{doubly.ast_total_mm2:.1f}", "mm^2"],
        ["Asc, compression steel required", f"{doubly.asc_mm2:.1f}", "mm^2"],
        ["fsc (design stress, compression steel)", f"{doubly.fsc_N_mm2:.1f}", "N/mm^2"],
    ]
else:
    flexure_rows += [
        ["Section Type", "Singly Reinforced", "-"],
        ["Ast, required (Annex G-1.1(b))", f"{flexure_final.ast_required_mm2:.1f}", "mm^2"],
        ["Ast, min (Cl. 26.5.1.1(a))", f"{flexure_final.ast_min_mm2:.1f}", "mm^2"],
        ["Ast, max (Cl. 26.5.1.1(b))", f"{flexure_final.ast_max_mm2:.1f}", "mm^2"],
    ]
story.append(kv_table(["Parameter", "Value", "Unit"], flexure_rows))
story.append(Spacer(1, 4))
story.append(status_flowable("Flexure", flex_status))

# 7. Shear Design
story.append(Paragraph("7. Shear Design", styles["SectionHeading"]))
story.append(kv_table(
    ["Parameter", "Value", "Unit"],
    [
        ["Nominal Shear Stress, tau_v (Cl. 40.1)", f"{shear.tau_v:.3f}", "N/mm^2"],
        ["Design Shear Strength, tau_c (Table 19)", f"{shear.tau_c:.3f}", "N/mm^2"],
        ["Maximum Shear Stress, tau_c,max (Table 20)", f"{shear.tau_c_max:.2f}", "N/mm^2"],
        ["Reinforcement Basis", shear.reinforcement_basis.title(), "-"],
        ["Stirrup Spacing Provided", f"{shear.spacing_provided_mm:.0f}", "mm c/c"],
    ],
))
story.append(Spacer(1, 4))
story.append(status_flowable("Shear", shear.is_safe))

# 8. Reinforcement Details
story.append(Paragraph("8. Reinforcement Details", styles["SectionHeading"]))
story.append(kv_table(
    ["Parameter", "Value", "Unit"],
    [
        ["Main Reinforcement", f"{bars.count} x {bars.diameter_mm:.0f}", "mm"],
        ["Area Provided, Ast,provided", f"{bars.area_provided_mm2:.1f}", "mm^2"],
        ["Excess Steel", f"{bars.excess_fraction*100:.1f}", "%"],
        ["Clear Bar Spacing (Cl. 26.3.2)", f"{bars.clear_spacing_mm:.1f}", "mm"],
        ["Stirrups", f"{STIRRUP_LEGS}-legged {STIRRUP_DIA_MM}", f"mm @ {shear.spacing_provided_mm:.0f} mm c/c"],
        ["Development Length, Ld (Cl. 26.2.1)", f"{ld:.0f}", "mm"],
    ],
))

# 9. Serviceability
story.append(Paragraph("9. Serviceability Checks", styles["SectionHeading"]))
story.append(kv_table(
    ["Parameter", "Value", "Unit"],
    [
        ["Basic Span/Depth Ratio (Cl. 23.2.1)", f"{deflection.basic_ratio:.1f}", "-"],
        ["Modification Factor, kt (Fig. 4)", f"{deflection.kt:.3f}", "-"],
        ["Modification Factor, kc (Fig. 5)", f"{deflection.kc:.2f}", "-"],
        ["Allowable Span/Depth Ratio", f"{deflection.allowable_ratio:.2f}", "-"],
        ["Actual Span/Depth Ratio", f"{deflection.actual_ratio:.2f}", "-"],
    ],
))
story.append(Spacer(1, 4))
story.append(status_flowable("Serviceability", deflection.is_safe))

# 10. IS 456 Compliance
story.append(Paragraph("10. IS 456 Compliance Summary", styles["SectionHeading"]))
story.append(kv_table(
    ["Check", "Clause", "Status"],
    [
        ["Load Factor", "Table 18 / Cl. 36.4.1", "Applied"],
        ["Flexural Design", "Annex G", "SAFE" if flex_status else "FAIL"],
        ["Minimum/Maximum Reinforcement", "Cl. 26.5.1.1", "SAFE" if flex_status else "FAIL"],
        ["Shear Design", "Cl. 40", "SAFE" if shear.is_safe else "FAIL"],
        ["Bar Spacing", "Cl. 26.3.2", "OK"],
        ["Development Length", "Cl. 26.2.1", "Checked (not a pass/fail limit)"],
        ["Deflection (Span/Depth)", "Cl. 23.2.1", "SAFE" if deflection.is_safe else "FAIL"],
    ],
    col_widths=(6.5 * cm, 5 * cm, 5 * cm),
))

story.append(PageBreak())

# 11. Final Design Summary
story.append(Paragraph("11. Final Design Summary", styles["SectionHeading"]))
story.append(kv_table(
    ["Parameter", "Value", "Unit"],
    [
        ["Beam", BEAM_NAME, "-"],
        ["Span", f"{SPAN_MM/1000:.1f}", "m"],
        ["Section", f"{WIDTH_MM} x {OVERALL_DEPTH_MM}", "mm"],
        ["Concrete / Steel", f"{CONCRETE_GRADE} / {STEEL_GRADE}", "-"],
        ["Factored Load", f"{loads.factored_udl:.2f}", "kN/m"],
        ["Design Moment, Mu", f"{loads.max_bending_moment:.2f}", "kNm"],
        ["Design Shear, Vu", f"{loads.max_shear_force:.2f}", "kN"],
        ["Main Reinforcement", f"{bars.count} x {bars.diameter_mm:.0f} mm", "-"],
        ["Stirrups", f"{STIRRUP_LEGS}-legged {STIRRUP_DIA_MM} mm @ {shear.spacing_provided_mm:.0f} mm c/c", "-"],
    ],
))
story.append(Spacer(1, 10))
story.append(status_flowable("Flexure", flex_status))
story.append(status_flowable("Shear", shear.is_safe))
story.append(status_flowable("Serviceability", deflection.is_safe))
story.append(Spacer(1, 6))
story.append(status_flowable("OVERALL DESIGN STATUS", overall_safe))

# 12. SFD/BMD
story.append(Spacer(1, 14))
story.append(Paragraph("12. Shear Force and Bending Moment Diagrams", styles["SectionHeading"]))
img_buffer = io.BytesIO()
sfd_bmd_fig.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight")
img_buffer.seek(0)
story.append(Image(img_buffer, width=14 * cm, height=10 * cm))

story.append(Spacer(1, 10))
story.append(Paragraph(
    "Note: This report is a design-calculation summary generated for engineering review. "
    "It is not a substitute for a licensed structural engineer's sign-off, and does not yet "
    "include ductile-detailing (IS 13920) or crack-width checks. A reinforcement detailing "
    "sketch is planned for a future version of this tool.",
    styles["Normal"],
))

doc.build(story)
print(f"Saved {output_path}")
