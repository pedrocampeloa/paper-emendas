"""
86_fig_v6_status_split.py
--------------------------
Final Figure 1 design: each RP is colored by its LEGAL STATUS in each year.

Color rules:
  Mandatory family (blue tones):
    RP-6 mandatory  -> deep navy (#1f3a68)
    RP-6 Pix        -> medium blue (#5d8fc4)
    RP-7 mandatory  -> light blue (#a8c7e6)

  Discretionary family (red/orange tones):
    RP-6 discretionary (pre-2015) -> dark wine red (#7a2a36)
    RP-7 discretionary (pre-2020) -> brick red (#c4615b)
    RP-8 (always discr.)          -> amber (#d8973c)
    RP-9 (always discr.)          -> deep red (#9c3848)

So a single RP can appear in TWO legend entries: e.g. "RP-6 (discretionary,
pre-2015)" and "RP-6 (mandatory, EC 86/2015)".

We split the year axis: for each RP that switched status, the pre-switch
segment is plotted in the discretionary palette, and the post-switch
segment in the mandatory palette. Both segments occupy the SAME stack
position (so the total height is preserved).

Output: paper-emendas/docs/figs/fig_composition.pdf (replaces the production
figure if approved).
"""

import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "paper-emendas" / "results"
FIGS = REPO / "paper-emendas" / "docs" / "figs"

mpl.rcParams.update({
    "font.family": "serif", "font.size": 10,
    "axes.spines.right": False, "axes.spines.top": False,
    "savefig.bbox": "tight",
    "text.usetex": False,
})

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("v6")


# Year from which each RP becomes mandatory
MANDATORY_FROM = {
    "RP-6":     2015,
    "RP-6 Pix": 2020,
    "RP-7":     2020,
    "RP-8":     np.inf,
    "RP-9":     np.inf,
}

# Color palette: 2 sets (mandatory = blues, discretionary = warm).
# Each RP has 1 or 2 entries depending on whether it ever switched.
COLOR = {
    # --- Mandatory family (blues) ---
    "RP-6_mand":       "#1f3a68",   # deep navy
    "RP-6 Pix_mand":   "#5d8fc4",   # medium blue
    "RP-7_mand":       "#a8c7e6",   # light blue

    # --- Discretionary family (warms) ---
    "RP-6_disc":       "#7a2a36",   # dark wine (RP-6 before EC 86)
    "RP-7_disc":       "#c4615b",   # brick red (RP-7 before EC 100)
    "RP-8_disc":       "#d8973c",   # amber (RP-8 always discr.)
    "RP-9_disc":       "#9c3848",   # deep red (RP-9, Secret Budget)
}

LABEL = {
    "RP-6_mand":       "RP-6 Individual (mandatory, EC 86/2015)",
    "RP-6 Pix_mand":   "RP-6 Pix (mandatory, EC 105/2019)",
    "RP-7_mand":       "RP-7 State bench (mandatory, EC 100/2019)",
    "RP-6_disc":       "RP-6 Individual (discretionary, pre-2015)",
    "RP-7_disc":       "RP-7 State bench (discretionary, pre-2020)",
    "RP-8_disc":       "RP-8 Committee (discretionary)",
    "RP-9_disc":       "RP-9 Rapporteur, Secret Budget (discretionary)",
}


def status_of(rp, year):
    return "mand" if year >= MANDATORY_FROM[rp] else "disc"


def main():
    t = pd.read_csv(RESULTS / "table1_emendas_by_rp_year.csv", sep=";")
    t = t.set_index("year")
    t = t[t.index <= 2025]
    years = t.index.values
    n = len(years)
    rp_cols = ["RP-6", "RP-6 Pix", "RP-7", "RP-8", "RP-9"]

    # Build a per-(year, segment-key) value matrix. For each RP we create
    # two sub-series (mandatory and discretionary), masked to NaN where the
    # other status applies. Both sub-series feed fill_between -- the
    # discretionary mask covers the pre-switch years, mandatory covers
    # post-switch.
    log.info("Building status-split stacks")
    series = {}
    for rp in rp_cols:
        vals = t[rp].values.astype(float)
        mand_vals = np.zeros(n)
        disc_vals = np.zeros(n)
        for i, y in enumerate(years):
            if status_of(rp, y) == "mand":
                mand_vals[i] = vals[i]
            else:
                disc_vals[i] = vals[i]
        # Only add segments that have any positive value across the panel
        if mand_vals.sum() > 0:
            series[f"{rp}_mand"] = mand_vals
        if disc_vals.sum() > 0:
            series[f"{rp}_disc"] = disc_vals

    # Stack order: mandatory family (bottom, blues) then discretionary on top.
    # Within each family, follow RP numerical order.
    stack_order = [
        # mandatory bottom
        "RP-6_mand", "RP-6 Pix_mand", "RP-7_mand",
        # discretionary on top
        "RP-6_disc", "RP-7_disc", "RP-8_disc", "RP-9_disc",
    ]
    stack_order = [k for k in stack_order if k in series]
    log.info(f"  stack segments present: {stack_order}")

    # Plot
    fig, ax1 = plt.subplots(figsize=(11, 5.5))

    bottom = np.zeros(n)
    for key in stack_order:
        vals = series[key]
        ax1.fill_between(years, bottom, bottom + vals,
                          color=COLOR[key], alpha=0.92, linewidth=0.4,
                          edgecolor="white",
                          label=LABEL[key])
        bottom += vals

    ax1.set_xlabel("Year")
    ax1.set_ylabel("Committed value (R$ billions, nominal)")
    ax1.grid(axis="y", alpha=0.18)
    ax1.set_ylim(bottom=0)
    ax1.set_xlim(2014, 2025.4)

    # Right axis: share-of-discretionary line (single, dashed)
    SHARE_COLOR = "#0a3d4a"
    ax2 = ax1.twinx()
    ax2.plot(years, t["share_discr_pct"].values, color=SHARE_COLOR,
              linewidth=2.4, marker="o", markersize=6, linestyle="--",
              label="Total amendments / discretionary spending (right axis, %)",
              zorder=11)
    ax2.set_ylabel("Share of federal discretionary spending (%)",
                    color=SHARE_COLOR)
    ax2.tick_params(axis="y", labelcolor=SHARE_COLOR)
    ax2.set_ylim(0, max(t["share_discr_pct"].dropna()) * 1.2)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(SHARE_COLOR)

    # Event lines
    events = [
        (2015.0, "EC 86/2015\nRP-6 mandatory", "#1f3a68"),
        (2019.0, "EC 100 & 105/2019\nRP-7 mandatory,\nPix transfers", "#5d8fc4"),
        (2020.0, "RP-9 expansion\n(Secret Budget)", "#9c3848"),
        (2021.083, "Lira (PP)\npresides", "#d8973c"),
        (2021.85, "STF injunction\n(ADPF 854)", "#7a2a36"),
        (2023.0, "ADPF 854 ruling;\nRP-8 + Pix expand", "#444444"),
    ]
    ymax = ax1.get_ylim()[1]
    stagger_y = [0.98, 0.98, 0.86, 0.74, 0.62, 0.98]
    for (yr, lbl, c), yp in zip(events, stagger_y):
        ax1.axvline(yr, color=c, linestyle="--", linewidth=0.9, alpha=0.45)
        ax1.annotate(lbl, xy=(yr, ymax * yp),
                      xytext=(yr, ymax * yp), ha="center", va="top",
                      fontsize=6.8, color=c, fontweight="bold",
                      bbox=dict(boxstyle="round,pad=0.18", fc="white",
                                ec=c, lw=0.5, alpha=0.92))

    ax1.set_title("Composition of parliamentary amendments by category and legal status, 2014-2025",
                   fontsize=11.5, pad=10)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
                loc="upper left", bbox_to_anchor=(1.10, 1.0),
                fontsize=8.0, frameon=False)

    plt.subplots_adjust(left=0.08, right=0.70, top=0.92, bottom=0.10)
    out = FIGS / "fig_composition.pdf"
    fig.savefig(out)
    log.info(f"  saved {out}")


if __name__ == "__main__":
    main()
