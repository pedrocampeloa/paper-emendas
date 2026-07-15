"""
85_fig_variants_status.py
--------------------------
Build several variants of the composition figure showing how parliamentary
amendment categories changed status (discretionary -> mandatory) over time.

The transition rules used (legal definition):
  - RP-6        : discretionary up to 2014, mandatory from 2015 (EC 86/2015)
  - RP-6 Pix    : did not exist before 2020, mandatory subset of RP-6 thereafter
  - RP-7        : discretionary up to 2019, mandatory from 2020 (EC 100/2019)
  - RP-8        : discretionary throughout
  - RP-9        : discretionary throughout (extinguished by ADPF 854 in 2022)

Variants produced (each saved to docs/figs/variants/ for inspection):
  V1  baseline (current production figure: colored by RP, solid)
  V2  hatched discretionary, solid mandatory, colors preserved (5 colors)
  V3  status-only colors: blue=mandatory, red=discretionary, one shade each
  V4  status-only with hatching: solid mandatory, hatched discretionary,
        single neutral palette
  V5  same as V2 but with two-tone palette (mandatory family = blue tones,
        discretionary family = red tones)

All outputs land in paper-emendas/docs/figs/variants/.
"""

import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "paper-emendas" / "results"
FIGS = REPO / "paper-emendas" / "docs" / "figs" / "variants"
FIGS.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": "serif", "font.size": 9.5,
    "axes.spines.right": False, "axes.spines.top": False,
    "savefig.bbox": "tight",
    "text.usetex": False,
})

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("variants")


# Status transition: year from which each RP becomes mandatory.
# np.inf means never (always discretionary).
MANDATORY_FROM = {
    "RP-6":     2015,
    "RP-6 Pix": 2020,  # only exists from 2020 anyway, born mandatory
    "RP-7":     2020,
    "RP-8":     np.inf,
    "RP-9":     np.inf,
}


def is_mandatory(rp, year):
    return year >= MANDATORY_FROM[rp]


def draw_baseline(ax, pivot, years, rp_cols, labels):
    """V1 baseline: colored areas, no hatching."""
    colors = {
        "RP-6":     "#1f3a68",
        "RP-6 Pix": "#5d8fc4",
        "RP-7":     "#a8c7e6",
        "RP-8":     "#d8973c",
        "RP-9":     "#9c3848",
    }
    bottom = np.zeros(len(years))
    for c in rp_cols:
        vals = pivot[c].values
        ax.fill_between(years, bottom, bottom + vals, label=labels[c],
                         color=colors[c], alpha=0.90, linewidth=0.4,
                         edgecolor="white")
        bottom += vals
    return ax


def draw_segmented(ax, pivot, years, rp_cols, labels, colors,
                    hatch_pre=True, hatch_pattern="//"):
    """V2/V5: solid where mandatory, hatched where discretionary, preserving
       per-RP color."""
    bottom = np.zeros(len(years))
    for c in rp_cols:
        vals = pivot[c].values
        # Per-year, plot mandatory and discretionary segments separately.
        # We draw 2 fills per RP: one for years where it's mandatory, one for
        # discretionary years. fill_between with `where` lets matplotlib handle
        # the segmentation.
        is_mand = np.array([is_mandatory(c, y) for y in years])

        # Mandatory segments: solid fill
        ax.fill_between(years, bottom, bottom + vals,
                         where=is_mand, interpolate=False,
                         color=colors[c], alpha=0.90, linewidth=0.4,
                         edgecolor="white",
                         label=f"{labels[c]}")
        # Discretionary segments: hatched
        if hatch_pre:
            ax.fill_between(years, bottom, bottom + vals,
                             where=~is_mand, interpolate=False,
                             facecolor=colors[c], alpha=0.45,
                             hatch=hatch_pattern, linewidth=0.4,
                             edgecolor="white")
        bottom += vals
    return ax


def draw_status_only(ax, pivot, years, rp_cols):
    """V3: two macro-colors (mandatory blue, discretionary red), no per-RP detail."""
    MAND = "#1f3a68"
    DISC = "#9c3848"
    # For each year, sum mandatory vs discretionary amendments
    mand_sum = np.zeros(len(years))
    disc_sum = np.zeros(len(years))
    for c in rp_cols:
        vals = pivot[c].values
        for i, y in enumerate(years):
            if is_mandatory(c, y): mand_sum[i] += vals[i]
            else:                   disc_sum[i] += vals[i]
    ax.fill_between(years, 0, mand_sum, label="Mandatory channel",
                     color=MAND, alpha=0.90, linewidth=0.4, edgecolor="white")
    ax.fill_between(years, mand_sum, mand_sum + disc_sum,
                     label="Discretionary channel",
                     color=DISC, alpha=0.90, linewidth=0.4, edgecolor="white")
    return ax


def draw_status_hatched(ax, pivot, years, rp_cols):
    """V4: neutral single base color (gray) with hatch indicating discretionary."""
    BASE = "#5b7c99"   # muted slate
    DISC_HATCH = "//"
    mand_sum = np.zeros(len(years))
    disc_sum = np.zeros(len(years))
    for c in rp_cols:
        vals = pivot[c].values
        for i, y in enumerate(years):
            if is_mandatory(c, y): mand_sum[i] += vals[i]
            else:                   disc_sum[i] += vals[i]
    ax.fill_between(years, 0, mand_sum, label="Mandatory (solid)",
                     color=BASE, alpha=0.90, linewidth=0.4, edgecolor="white")
    ax.fill_between(years, mand_sum, mand_sum + disc_sum,
                     label="Discretionary (hatched)",
                     facecolor=BASE, alpha=0.55, hatch=DISC_HATCH,
                     linewidth=0.4, edgecolor="white")
    return ax


def add_share_line(ax1, pivot, years):
    """Right axis with the share-of-discretionary dashed line."""
    SHARE = "#0a3d4a"
    ax2 = ax1.twinx()
    ax2.plot(years, pivot["share_discr_pct"].values, color=SHARE,
             linewidth=2.0, marker="o", markersize=5, linestyle="--",
             label="Total amendments / discretionary spending (right axis, %)",
             zorder=11)
    ax2.set_ylabel("Share of discretionary (%)", color=SHARE, fontsize=9)
    ax2.tick_params(axis="y", labelcolor=SHARE)
    ax2.set_ylim(0, max(pivot["share_discr_pct"].dropna()) * 1.2)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(SHARE)
    return ax2


def add_events(ax, ymax):
    events = [
        (2015.0, "EC 86", "#1f3a68"),
        (2019.0, "EC 100&105", "#1f6e3d"),
        (2020.0, "RP-9 expansion", "#9c3848"),
        (2021.083, "Lira", "#d8973c"),
        (2023.0, "ADPF 854", "#444"),
    ]
    for yr, lbl, c in events:
        ax.axvline(yr, color=c, linestyle="--", linewidth=0.8, alpha=0.45)


def variant_plot(variant_name, draw_fn, title, save_path, pivot, years,
                  rp_cols, labels, colors=None, **kwargs):
    fig, ax1 = plt.subplots(figsize=(11, 5))
    if colors is not None and draw_fn is draw_segmented:
        draw_fn(ax1, pivot, years, rp_cols, labels, colors, **kwargs)
    else:
        draw_fn(ax1, pivot, years, rp_cols, labels, **kwargs) if draw_fn is draw_baseline else draw_fn(ax1, pivot, years, rp_cols)

    ax1.set_xlabel("Year")
    ax1.set_ylabel("Committed value (R$ billions, nominal)")
    ax1.set_title(title, fontsize=11, pad=8)
    ax1.set_xlim(2014, 2025.4)
    ax1.set_ylim(bottom=0)
    ax1.grid(axis="y", alpha=0.18)

    add_share_line(ax1, pivot, years)
    add_events(ax1, ax1.get_ylim()[1])

    lines1, labels1 = ax1.get_legend_handles_labels()
    ax1.legend(lines1, labels1, loc="upper left",
                bbox_to_anchor=(1.10, 1.0), fontsize=8, frameon=False)

    plt.subplots_adjust(left=0.07, right=0.74, top=0.92, bottom=0.10)
    fig.savefig(save_path)
    log.info(f"  saved {save_path.name}")
    plt.close(fig)


def main():
    t = pd.read_csv(RESULTS / "table1_emendas_by_rp_year.csv", sep=";")
    t = t.set_index("year")
    # Use full years 2014--2025 (drop partial 2026 from previous build)
    t = t[t.index <= 2025]
    years = t.index.values
    rp_cols = ["RP-6", "RP-6 Pix", "RP-7", "RP-8", "RP-9"]
    labels = {"RP-6": "RP-6 Individual",
              "RP-6 Pix": "RP-6 Pix (EC 105/2019)",
              "RP-7": "RP-7 State bench",
              "RP-8": "RP-8 Committee",
              "RP-9": "RP-9 Rapporteur"}

    # Standard 5-color palette (also used in V2/V5 as base)
    palette5 = {
        "RP-6":     "#1f3a68",
        "RP-6 Pix": "#5d8fc4",
        "RP-7":     "#a8c7e6",
        "RP-8":     "#d8973c",
        "RP-9":     "#9c3848",
    }
    # Two-tone status palette (mandatory blues, discretionary warms)
    palette_2t = {
        "RP-6":     "#1f3a68",
        "RP-6 Pix": "#5d8fc4",
        "RP-7":     "#a8c7e6",
        "RP-8":     "#d8973c",
        "RP-9":     "#9c3848",
    }

    # V1: baseline production
    variant_plot("V1", draw_baseline,
                  "V1 -- baseline (current production)",
                  FIGS / "v1_baseline.pdf",
                  t, years, rp_cols, labels)

    # V2: per-RP colors, hatched where discretionary
    variant_plot("V2", draw_segmented,
                  "V2 -- per-RP color, hatched where discretionary",
                  FIGS / "v2_per_rp_hatch.pdf",
                  t, years, rp_cols, labels, colors=palette5,
                  hatch_pre=True, hatch_pattern="//")

    # V3: macro colors only (mandatory blue / discretionary red)
    variant_plot("V3", draw_status_only,
                  "V3 -- two macro colors (mandatory vs discretionary)",
                  FIGS / "v3_status_two_colors.pdf",
                  t, years, rp_cols, labels)

    # V4: single base color, hatch = discretionary
    variant_plot("V4", draw_status_hatched,
                  "V4 -- single color, hatch = discretionary",
                  FIGS / "v4_status_hatch_only.pdf",
                  t, years, rp_cols, labels)

    # V5: same as V2 but with denser hatch pattern
    variant_plot("V5", draw_segmented,
                  "V5 -- per-RP color, dense hatch where discretionary",
                  FIGS / "v5_per_rp_dense_hatch.pdf",
                  t, years, rp_cols, labels, colors=palette5,
                  hatch_pre=True, hatch_pattern="xxx")

    log.info("\n  All variants saved in:")
    log.info(f"    {FIGS}/")

    # Combine all variants into one multi-page PDF for easy comparison
    from matplotlib.backends.backend_pdf import PdfPages
    combined_path = FIGS / "variants_combined.pdf"
    log.info("\n  Building combined multi-page PDF for side-by-side review...")
    with PdfPages(combined_path) as pdf:
        # Re-render each variant directly into the multi-page PDF
        variant_specs = [
            ("V1 -- baseline (current production)", draw_baseline, {}, None),
            ("V2 -- per-RP color, hatched where discretionary",
             draw_segmented, {"hatch_pre": True, "hatch_pattern": "//"}, palette5),
            ("V3 -- two macro colors (mandatory vs discretionary)",
             draw_status_only, {}, None),
            ("V4 -- single color, hatch = discretionary",
             draw_status_hatched, {}, None),
            ("V5 -- per-RP color, dense hatch where discretionary",
             draw_segmented, {"hatch_pre": True, "hatch_pattern": "xxx"}, palette5),
        ]
        for title, fn, kw, colors in variant_specs:
            fig, ax1 = plt.subplots(figsize=(11, 5))
            if fn is draw_baseline:
                fn(ax1, t, years, rp_cols, labels)
            elif fn is draw_segmented:
                fn(ax1, t, years, rp_cols, labels, colors, **kw)
            else:
                fn(ax1, t, years, rp_cols)

            ax1.set_xlabel("Year")
            ax1.set_ylabel("Committed value (R$ billions, nominal)")
            ax1.set_title(title, fontsize=11, pad=8)
            ax1.set_xlim(2014, 2025.4)
            ax1.set_ylim(bottom=0)
            ax1.grid(axis="y", alpha=0.18)
            add_share_line(ax1, t, years)
            add_events(ax1, ax1.get_ylim()[1])
            lines1, labels1 = ax1.get_legend_handles_labels()
            ax1.legend(lines1, labels1, loc="upper left",
                        bbox_to_anchor=(1.10, 1.0), fontsize=8, frameon=False)
            plt.subplots_adjust(left=0.07, right=0.74, top=0.92, bottom=0.10)
            pdf.savefig(fig)
            plt.close(fig)
    log.info(f"  combined PDF: {combined_path}")


if __name__ == "__main__":
    main()
