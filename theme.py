"""theme.py - one consistent visual language for every figure."""

import matplotlib as mpl
import matplotlib.pyplot as plt

INK = "#1a202c"
ACCENT = "#2b6cb0"
ACCENT_SOFT = "#bee3f8"
MUTED = "#a0aec0"
RED = "#c53030"
GREEN = "#2f855a"
GRID = "#e2e8f0"

# Bernstein's five-band continuum (matches his legend)
CLASS_COLOR = {
    "procedural": "#d53f8c",
    "procedural-integrative": "#dd6b20",
    "integrative": "#d69e2e",
    "integrative-perceptive": "#38a169",
    "perceptive": "#3182ce",
}


def apply_theme():
    mpl.rcParams.update({
        "figure.dpi": 130,
        "savefig.dpi": 130,
        "savefig.bbox": "tight",
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlepad": 14,
        "axes.labelsize": 11,
        "axes.labelcolor": INK,
        "axes.edgecolor": MUTED,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "legend.frameon": False,
        "legend.fontsize": 9,
    })


def titlecard(ax, title, subtitle=None):
    """Left-aligned title with an optional grey subtitle stacked beneath it,
    both placed above the axes so they never collide with the plot."""
    ax.text(0, 1.10, title, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=14, fontweight="bold", color=INK)
    if subtitle:
        ax.text(0, 1.03, subtitle, transform=ax.transAxes, ha="left",
                va="bottom", fontsize=9.5, color=MUTED)
