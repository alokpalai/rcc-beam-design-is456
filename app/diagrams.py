"""
Shear Force Diagram (SFD) and Bending Moment Diagram (BMD) generation.

Scope (current milestone): simply supported beam, uniformly distributed
load only - matches app/loads.py's compute_loads_simply_supported_udl().

Sign convention: x measured from the left support (0 to span). V(x) and M(x)
use standard beam statics for a simply supported UDL beam:
    Reactions: RA = RB = wu*L/2
    V(x) = RA - wu*x = wu*(L/2 - x)
    M(x) = RA*x - wu*x^2/2 = (wu*x/2)*(L - x)
"""

import numpy as np
import matplotlib.pyplot as plt


def compute_sfd_bmd_simply_supported_udl(span_mm: float, wu_kN_per_m: float, num_points: int = 101):
    """
    Returns (x, V, M): x in metres along the span, V in kN, M in kNm,
    for a simply supported beam under a factored UDL wu.
    """
    span_m = span_mm / 1000.0
    x = np.linspace(0, span_m, num_points)
    V = wu_kN_per_m * (span_m / 2 - x)
    M = (wu_kN_per_m * x / 2) * (span_m - x)
    return x, V, M


def plot_sfd_bmd(x, V, M, beam_name: str = "Beam", save_path: str = None):
    """
    Plots SFD (top) and BMD (bottom) stacked, sharing the x-axis.
    Saves to save_path if given (e.g. 'sfd_bmd_B1.png'); always returns the figure.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

    ax1.plot(x, V, color="tab:blue")
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.fill_between(x, V, 0, alpha=0.2, color="tab:blue")
    ax1.set_ylabel("Shear Force, V (kN)")
    ax1.set_title(f"{beam_name}: Shear Force Diagram (SFD)")
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2.plot(x, M, color="tab:red")
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.fill_between(x, M, 0, alpha=0.2, color="tab:red")
    ax2.set_ylabel("Bending Moment, M (kNm)")
    ax2.set_xlabel("Distance along beam, x (m)")
    ax2.set_title(f"{beam_name}: Bending Moment Diagram (BMD)")
    ax2.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig