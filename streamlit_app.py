"""
RCC Beam Design Calculator - Streamlit GUI.

Wraps the app/ calculation engine (loads -> flexure -> bar selection ->
shear -> development length -> serviceability -> SFD/BMD) in an interactive
form, following the same design sequence as run_example.py.

Layout: inputs on the left, results on the right, compacted to fit a
typical laptop viewport (~1440x800) without scrolling.

Run:
    python -m streamlit run streamlit_app.py
"""

import streamlit as st

from app.loads import BeamGeometry, compute_loads_simply_supported_udl
from app.flexure import design_flexure_singly_reinforced, design_flexure_doubly_reinforced
from app.shear import design_shear_reinforcement
from app.reinforcement import calc_development_length_mm, derive_effective_depth_mm, select_optimal_bars
from app.materials import fy as get_fy
from app.serviceability import check_deflection_span_to_depth
from app.diagrams import compute_sfd_bmd_simply_supported_udl, plot_sfd_bmd

st.set_page_config(page_title="RCC Beam Design Calculator", page_icon="🏗️", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stHeader"] { display: none !important; }
    div[data-testid="stMainBlockContainer"] { padding-top: 0.8rem !important; padding-bottom: 0.8rem !important; max-width: 1300px; }
    div[data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
    div[data-testid="stElementContainer"] { margin-bottom: 0 !important; }
    div[data-testid="stHeading"] h1 { font-size: 1.6rem !important; margin: 0 !important; padding: 0.3rem 0 !important; }
    div[data-testid="stCaptionContainer"] { margin-bottom: 0 !important; }
    div[data-testid="stMetricValue"] { font-size: 1.15rem !important; }
    div[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏗️ RCC Beam Design Calculator")
st.caption("IS 456:2000 limit-state design - simply supported beam, uniformly distributed load")

left, right = st.columns([1, 1.3], gap="large")

with left:
    with st.container(border=True):
        st.subheader("Beam Inputs")
        with st.form("beam_inputs"):
            c0, c00 = st.columns(2)
            beam_name = c0.text_input("Beam Name", "B1")
            span_mm = c00.number_input("Span (mm)", min_value=1000, max_value=15000, value=5000, step=100)

            c1, c2 = st.columns(2)
            width_mm = c1.number_input("Width, b (mm)", min_value=150, max_value=1000, value=300, step=25)
            depth_mm = c2.number_input("Overall Depth, D (mm)", min_value=200, max_value=1500, value=500, step=25)

            c3, c4 = st.columns(2)
            concrete_grade = c3.selectbox("Concrete Grade", ["M15", "M20", "M25", "M30", "M35", "M40"], index=2)
            steel_grade = c4.selectbox("Steel Grade", ["Fe250", "Fe415", "Fe500", "Fe550"], index=1)

            c5, c6 = st.columns(2)
            dead_load = c5.number_input("Dead Load, excl. self-weight (kN/m)", min_value=0.0, value=12.0, step=0.5)
            live_load = c6.number_input("Live Load (kN/m)", min_value=0.0, value=8.0, step=0.5)

            c7, c8 = st.columns(2)
            cover_mm = c7.number_input("Clear Cover (mm)", min_value=15, max_value=75, value=25, step=5)
            stirrup_dia = c8.selectbox("Stirrup Diameter (mm)", [6, 8, 10], index=1)

            trial_bar_dia = st.selectbox("Trial Main Bar Diameter (mm)", [12, 16, 20, 25, 28, 32], index=1)

            with st.expander("Advanced (doubly reinforced sections only)"):
                compression_cover = st.number_input(
                    "Compression Cover, d' (mm)", min_value=25, max_value=75, value=50, step=5,
                    help="Only used if the section needs compression steel (Mu > Mu,lim).",
                )

            submitted = st.form_submit_button("DESIGN BEAM", use_container_width=True, type="primary")

with right:
    if not submitted:
        with st.container(border=True):
            st.info(
                "Fill in the beam parameters on the left and click **DESIGN BEAM** "
                "to see the full IS 456 design check here."
            )
    else:
        try:
            geometry = BeamGeometry(span_mm=span_mm, width_mm=width_mm, overall_depth_mm=depth_mm)
            loads = compute_loads_simply_supported_udl(geometry, dead_load, live_load)

            d_trial = derive_effective_depth_mm(depth_mm, cover_mm, stirrup_dia, trial_bar_dia)
            flexure_trial = design_flexure_singly_reinforced(
                b_mm=width_mm, d_mm=d_trial, overall_depth_mm=depth_mm,
                mu_kNm=loads.max_bending_moment, fck_grade=concrete_grade, steel_grade=steel_grade,
            )

            doubly = None
            if flexure_trial.needs_doubly_reinforced:
                doubly = design_flexure_doubly_reinforced(
                    b_mm=width_mm, d_mm=d_trial, d_dash_mm=compression_cover, overall_depth_mm=depth_mm,
                    mu_kNm=loads.max_bending_moment, fck_grade=concrete_grade, steel_grade=steel_grade,
                )

            tension_ast_required = doubly.ast_total_mm2 if doubly else flexure_trial.ast_design_mm2
            bars = select_optimal_bars(tension_ast_required, width_mm, cover_mm, stirrup_dia)
            d_final = derive_effective_depth_mm(depth_mm, cover_mm, stirrup_dia, bars.diameter_mm)

            flexure_final = design_flexure_singly_reinforced(
                b_mm=width_mm, d_mm=d_final, overall_depth_mm=depth_mm,
                mu_kNm=loads.max_bending_moment, fck_grade=concrete_grade, steel_grade=steel_grade,
            )
            if flexure_final.needs_doubly_reinforced:
                doubly = design_flexure_doubly_reinforced(
                    b_mm=width_mm, d_mm=d_final, d_dash_mm=compression_cover, overall_depth_mm=depth_mm,
                    mu_kNm=loads.max_bending_moment, fck_grade=concrete_grade, steel_grade=steel_grade,
                )
            else:
                doubly = None

            shear = design_shear_reinforcement(
                vu_kN=loads.max_shear_force, b_mm=width_mm, d_mm=d_final,
                ast_provided_mm2=bars.area_provided_mm2, fck_grade=concrete_grade,
                steel_grade=steel_grade, stirrup_dia_mm=stirrup_dia, legs=2,
            )

            ld = calc_development_length_mm(bars.diameter_mm, steel_grade, concrete_grade)

            ast_required_for_deflection = doubly.ast_total_mm2 if doubly else flexure_final.ast_required_mm2
            deflection = check_deflection_span_to_depth(
                span_mm=span_mm, d_mm=d_final, support_condition="simply_supported",
                fy=get_fy(steel_grade), ast_required_mm2=ast_required_for_deflection,
                ast_provided_mm2=bars.area_provided_mm2, b_mm=width_mm,
            )

            flex_status = doubly.within_limits if doubly else flexure_final.within_min_max_limits
            overall_safe = flex_status and shear.is_safe and deflection.is_safe

            # --- Header / overall status + key numbers, combined ----------------
            with st.container(border=True):
                head_l, head_r = st.columns([2, 1])
                head_l.subheader(f"Design Result - {beam_name}")
                if overall_safe:
                    head_r.success("SAFE", icon="✅")
                else:
                    head_r.error("NOT SAFE", icon="⚠️")

                m1, m2, m3 = st.columns(3)
                m1.metric("Design Moment, Mu", f"{loads.max_bending_moment:.2f} kNm")
                m2.metric("Design Shear, Vu", f"{loads.max_shear_force:.2f} kN")
                m3.metric("Effective Depth, d", f"{d_final:.1f} mm")

                m4, m5, m6 = st.columns(3)
                m4.metric("Ast, required", f"{tension_ast_required:.1f} mm²")
                m5.metric("Ast, provided", f"{bars.area_provided_mm2:.1f} mm²",
                          f"{bars.excess_fraction*100:.1f}% excess")
                m6.metric("Development Length, Ld", f"{ld:.0f} mm")

            # --- Reinforcement summary + status badges ----------------------------
            with st.container(border=True):
                st.markdown(
                    f"**Main Reinforcement:** {bars.count} x {bars.diameter_mm:.0f} mm &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"**Stirrups:** 2-legged {stirrup_dia} mm @ {shear.spacing_provided_mm:.0f} mm c/c "
                    f"({shear.reinforcement_basis})"
                )
                if doubly:
                    st.markdown(f"**Compression steel required:** {doubly.asc_mm2:.1f} mm² (doubly reinforced)")

                b1, b2, b3 = st.columns(3)
                if flex_status:
                    b1.success("Flexure: SAFE")
                else:
                    b1.error("Flexure: FAIL")
                if shear.is_safe:
                    b2.success("Shear: SAFE")
                else:
                    b2.error("Shear: FAIL")
                if deflection.is_safe:
                    b3.success("Serviceability: SAFE")
                else:
                    b3.error("Serviceability: FAIL")

            # --- SFD / BMD ----------------------------------------------------------
            with st.container(border=True):
                st.markdown("**Shear Force & Bending Moment Diagrams**")
                x, V, M = compute_sfd_bmd_simply_supported_udl(span_mm, loads.factored_udl)
                fig = plot_sfd_bmd(x, V, M, beam_name=beam_name, figsize=(7, 4))
                st.pyplot(fig, width=520)

        except ValueError as e:
            st.error(f"Design could not be completed: {e}")
