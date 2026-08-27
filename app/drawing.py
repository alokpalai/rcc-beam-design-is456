"""
Reinforcement detailing schematic - cross-section and longitudinal elevation.

IMPORTANT: this is a DESIGN VISUALIZATION / DETAILING SCHEMATIC, not a
construction-ready drawing. It shows bar count, diameter, spacing, and cover
as derived by the design engine, drawn to approximate scale, for engineering
review and portfolio/demo purposes - it omits lap lengths, bend details,
curtailment, and bar bending schedules that a real construction drawing needs.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches


def compute_bar_x_positions(b_mm, cover_mm, stirrup_dia_mm, bar_dia_mm, count):
    """
    X-coordinates (mm, from the left face) of bar centres in a single layer,
    evenly spaced - same geometry as app/reinforcement.py's clear-spacing calc.
    """
    if count == 1:
        return [b_mm / 2]
    available = b_mm - 2 * cover_mm - 2 * stirrup_dia_mm - count * bar_dia_mm
    gap = available / (count - 1)
    start = cover_mm + stirrup_dia_mm + bar_dia_mm / 2
    return [start + i * (bar_dia_mm + gap) for i in range(count)]


def draw_cross_section(
    ax, b_mm, D_mm, cover_mm, stirrup_dia_mm,
    bottom_bar_dia_mm, bottom_bar_count,
    top_bar_dia_mm=None, top_bar_count=None, top_cover_mm=None, is_nominal_top=False,
):
    """Draws a beam cross-section: concrete outline, stirrup, bottom bars, top bars."""
    ax.add_patch(patches.Rectangle((0, 0), b_mm, D_mm, fill=False, edgecolor="black", linewidth=1.5))

    ax.add_patch(patches.Rectangle(
        (cover_mm, cover_mm), b_mm - 2 * cover_mm, D_mm - 2 * cover_mm,
        fill=False, edgecolor="tab:blue", linewidth=1.2, linestyle="--",
    ))

    y_bottom = cover_mm + stirrup_dia_mm + bottom_bar_dia_mm / 2
    for x in compute_bar_x_positions(b_mm, cover_mm, stirrup_dia_mm, bottom_bar_dia_mm, bottom_bar_count):
        ax.add_patch(patches.Circle((x, y_bottom), bottom_bar_dia_mm / 2, color="tab:red", zorder=3))

    if top_bar_count and top_bar_dia_mm:
        y_top = D_mm - (top_cover_mm if top_cover_mm else (cover_mm + stirrup_dia_mm + top_bar_dia_mm / 2))
        color = "tab:orange" if is_nominal_top else "tab:red"
        for x in compute_bar_x_positions(b_mm, cover_mm, stirrup_dia_mm, top_bar_dia_mm, top_bar_count):
            ax.add_patch(patches.Circle((x, y_top), top_bar_dia_mm / 2, color=color, zorder=3))

    ax.set_xlim(-45, b_mm + 45)
    ax.set_ylim(-45, D_mm + 45)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.annotate("", xy=(0, -22), xytext=(b_mm, -22), arrowprops=dict(arrowstyle="<->"))
    ax.text(b_mm / 2, -36, f"{b_mm:.0f} mm", ha="center", fontsize=9)
    ax.annotate("", xy=(-22, 0), xytext=(-22, D_mm), arrowprops=dict(arrowstyle="<->"))
    ax.text(-36, D_mm / 2, f"{D_mm:.0f} mm", va="center", ha="center", rotation=90, fontsize=9)

    label_bbox = dict(facecolor="white", edgecolor="none", pad=1.5)
    ax.text(b_mm / 2, y_bottom - 30, f"{bottom_bar_count} - {bottom_bar_dia_mm:.0f}mm",
            ha="center", va="top", fontsize=9, color="tab:red", bbox=label_bbox)
    if top_bar_count and top_bar_dia_mm:
        label = f"{top_bar_count} - {top_bar_dia_mm:.0f}mm" + (" (nominal)" if is_nominal_top else "")
        color = "tab:orange" if is_nominal_top else "tab:red"
        ax.text(b_mm / 2, y_top + 26, label, ha="center", va="bottom", fontsize=9, color=color, bbox=label_bbox)

    ax.set_title("Cross-Section", fontsize=10)


def draw_longitudinal_view(
    ax, span_mm, D_mm, cover_mm, stirrup_dia_mm,
    bottom_bar_dia_mm, bottom_bar_count, stirrup_spacing_mm,
    top_bar_dia_mm=None, top_bar_count=None, is_nominal_top=False,
):
    """Draws a simplified elevation: outline, supports, bar layer lines, stirrup ticks."""
    ax.add_patch(patches.Rectangle((0, 0), span_mm, D_mm, fill=False, edgecolor="black", linewidth=1.5))

    tri_size = D_mm * 0.18
    for x in (0, span_mm):
        ax.add_patch(patches.Polygon(
            [[x - tri_size / 2, -tri_size], [x + tri_size / 2, -tri_size], [x, 0]],
            closed=True, facecolor="black",
        ))

    y_bottom = cover_mm + stirrup_dia_mm + bottom_bar_dia_mm / 2
    ax.plot([cover_mm, span_mm - cover_mm], [y_bottom, y_bottom], color="tab:red", linewidth=2)
    label_bbox = dict(facecolor="white", edgecolor="none", pad=1.5)
    ax.text(span_mm / 2, y_bottom - 45, f"{bottom_bar_count}-{bottom_bar_dia_mm:.0f}mm (bottom)",
            ha="center", va="top", fontsize=8, color="tab:red", bbox=label_bbox)

    if top_bar_count and top_bar_dia_mm:
        y_top = D_mm - (cover_mm + stirrup_dia_mm + top_bar_dia_mm / 2)
        color = "tab:orange" if is_nominal_top else "tab:red"
        ax.plot([cover_mm, span_mm - cover_mm], [y_top, y_top], color=color, linewidth=2)
        label = f"{top_bar_count}-{top_bar_dia_mm:.0f}mm" + (" (nominal)" if is_nominal_top else " (top)")
        ax.text(span_mm / 2, y_top + 40, label, ha="center", va="bottom", fontsize=8, color=color, bbox=label_bbox)

    x = cover_mm
    while x <= span_mm - cover_mm:
        ax.plot([x, x], [cover_mm * 0.3, D_mm - cover_mm * 0.3], color="tab:blue", linewidth=0.8)
        x += stirrup_spacing_mm

    ax.set_xlim(-tri_size * 2, span_mm + tri_size * 2)
    ax.set_ylim(-tri_size * 2.2, D_mm + 70)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.annotate("", xy=(0, -tri_size * 1.5), xytext=(span_mm, -tri_size * 1.5), arrowprops=dict(arrowstyle="<->"))
    ax.text(span_mm / 2, -tri_size * 1.5 - 45, f"Span = {span_mm/1000:.2f} m", ha="center", fontsize=9)

    ax.set_title(f"Longitudinal Elevation - stirrups @ {stirrup_spacing_mm:.0f} mm c/c", fontsize=10)


def generate_reinforcement_drawing(
    beam_name, span_mm, b_mm, D_mm, cover_mm, stirrup_dia_mm, stirrup_spacing_mm,
    bottom_bar_dia_mm, bottom_bar_count,
    top_bar_dia_mm=None, top_bar_count=None, top_cover_mm=None, is_nominal_top=False,
    save_path=None,
):
    """
    Combined figure: longitudinal elevation (top) + cross-section (bottom).
    A design visualization / detailing schematic - NOT construction-ready
    (no lap lengths, bend details, curtailment, or bar bending schedule).
    """
    fig = plt.figure(figsize=(10, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.5])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    draw_longitudinal_view(
        ax1, span_mm, D_mm, cover_mm, stirrup_dia_mm,
        bottom_bar_dia_mm, bottom_bar_count, stirrup_spacing_mm,
        top_bar_dia_mm, top_bar_count, is_nominal_top,
    )
    draw_cross_section(
        ax2, b_mm, D_mm, cover_mm, stirrup_dia_mm,
        bottom_bar_dia_mm, bottom_bar_count,
        top_bar_dia_mm, top_bar_count, top_cover_mm, is_nominal_top,
    )

    fig.suptitle(
        f"{beam_name}: Reinforcement Detailing Schematic\n"
        "(design visualization - not construction-ready)",
        fontsize=11,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
