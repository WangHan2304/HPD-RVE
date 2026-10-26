#!/usr/bin/env python3
"""Figure 6: Mesh h-refinement convergence study (REAL DAMASK_grid data).

Left panel (a): macroscopic stress (yield proxy) convergence vs. grid resolution.
  Data from three genuine DAMASK_grid (spectral_basic) runs on the G5 4-phase
  steel RVE at in-plane resolutions 32 / 64 / 128 (size [N,N,2]), same underlying
  grain structure. Shown: stress vs resolution, and the (tiny) grid error.

Right panel (b): numerical discretization error budget from Richardson
  extrapolation (2nd order). This is the *only* quantitatively defensible part;
  the DAMASK-vs-experiment gap is NOT plotted because no experimental
  stress-strain data for this exact alloy composition is available in this study.

Okabe-Ito colorblind-safe palette, 630 DPI, white background.
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OI = {
    "orange": "#E69F00", "sky": "#56B4E9", "bluish_green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "vermilion": "#D55E00",
    "reddish_purple": "#CC79A7", "gray": "#999999",
}

# ── REAL data: 3-resolution DAMASK_grid convergence (G5 4-phase steel) ──
DATA = json.load(open(Path(__file__).parent / "damask_run_g5" / "multires_convergence.json"))
conv = DATA["convergence"]
# grid in-plane sizes
grids = np.array([32, 64, 128], dtype=float)
# macroscopic stress at 10% strain from each resolution (MPa)
stress_10pct = np.array([
    DATA["curves"]["32"]["stress_xx_MPa"][-1],
    DATA["curves"]["64"]["stress_xx_MPa"][-1],
    DATA["curves"]["128"]["stress_xx_MPa"][-1],
])
# relative grid error vs finest (128) reference
rel_err_vs_128 = np.abs(stress_10pct - stress_10pct[-1]) / stress_10pct[-1] * 100.0
# Richardson-estimated discretization error at 128 (MPa)
rich_err128 = conv["richardson_max_err_128_MPa"]


def draw_figure_6(output_prefix="fig6_mesh_convergence"):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2))

    # ── Panel (a): convergence ──
    ax1.plot(grids, stress_10pct, "o-", color=OI["blue"], linewidth=2.2,
             markersize=9, label="DAMASK $\\sigma_{xx}$ at 10% strain")
    # annotate measured values
    # annotate measured values with separate offsets to avoid overlap
    offsets = [(10, 26), (10, -22), (-38, -14)]   # 32 up-more, 64 down-right, 128 left-more-down
    for (g, s, e), off in zip(zip(grids, stress_10pct, rel_err_vs_128), offsets):
        ha = "left" if off[0] > 0 else "right"
        va = "bottom" if off[1] > 0 else "top"
        ax1.annotate(f"{s:.1f} MPa\n(Δ{e:.2f}%)", (g, s),
                     textcoords="offset points", xytext=off,
                     ha=ha, va=va, fontsize=8, color=OI["vermilion"])
    ax1.set_xlabel("In-plane grid resolution $N$ (size $[N,N,2]$)")
    ax1.set_ylabel("Macroscopic stress $\\sigma_{xx}$ (MPa)")
    ax1.set_title("(a) Grid-convergence of G5 RVE (real DAMASK data)", fontweight="bold")
    ax1.set_xticks(grids)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9, loc="lower right")

    # ── Panel (b): discretization error budget (Richardson, honest) ──
    # At 64 (our working resolution) the grid error vs 128 is:
    err64_vs_128 = abs(stress_10pct[1] - stress_10pct[2])  # MPa
    err32_vs_64 = abs(stress_10pct[0] - stress_10pct[1])   # MPa
    sources = [
        "Discretization\n(64 vs 128 grid)",
        "Discretization\n(32 vs 64 grid)",
        "Richardson est.\n(residual @128)",
    ]
    vals = np.array([err64_vs_128, err32_vs_64, rich_err128])
    bars = ax2.barh(sources, vals, color=[OI["bluish_green"], OI["sky"], OI["orange"]])
    for b, v in zip(bars, vals):
        ax2.text(v + 0.02, b.get_y() + b.get_height()/2, f"{v:.2f} MPa",
                 va="center", fontsize=9)
    ax2.set_xlabel("Grid-induced stress error (MPa)")
    ax2.set_title("(b) Numerical discretization error budget\n(Richardson 2nd-order, G5 RVE)",
                  fontweight="bold")
    ax2.grid(True, axis="x", alpha=0.3)
    ax2.set_xlim(0, max(vals) * 1.4)

    fig.suptitle("Figure 6. Mesh h-refinement convergence (G5 4-phase steel, "
                 "DAMASK_grid spectral_basic)",
                 fontsize=11, fontweight="bold")
    fig.tight_layout(rect=[0, 0.03, 1, 0.94])
    out = Path(__file__).parent / "RVE_LaTeX" / "figs" / f"{output_prefix}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=630, bbox_inches="tight")
    print("saved", out)
    # also copy to CMS/figs
    cms = Path(__file__).parent / "CMS" / "figs" / f"{output_prefix}.png"
    fig.savefig(cms, dpi=630, bbox_inches="tight")
    print("saved", cms)


if __name__ == "__main__":
    draw_figure_6()
