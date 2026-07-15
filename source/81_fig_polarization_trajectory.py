"""
81_fig_polarization_trajectory.py
-----------------------------------
Figure 2 of paper-emendas (Polarization section).

Two versions of the same plot:
  - Version A: single panel with 3 measures (Strong / Weak / MDS-Euclidean)
               + 2 sets of vertical lines (BR presidents + Chamber presidents)
  - Version B: two panels stacked, top = BR-presidents periods,
               bottom = Chamber-presidents periods, both showing the 3 measures

Source: paper-polarization/data/processed/average_mds_distances_*.csv (rolling
12-month windows, 94 periods).

Outputs:
  paper-emendas/docs/figs/fig_polarization_traj_A.pdf  (1 panel)
  paper-emendas/docs/figs/fig_polarization_traj_B.pdf  (2 panels)
"""

import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

REPO = Path(__file__).resolve().parents[2]
POL_DIR = REPO / "paper-polarization" / "data" / "processed"
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
log = logging.getLogger("polfig")


# Presidential sub-periods
BR_PRES = [
    (pd.Timestamp("2011-01-01"), pd.Timestamp("2016-05-12"), "Rousseff (PT)", "#a02020"),
    (pd.Timestamp("2016-05-13"), pd.Timestamp("2018-12-31"), "Temer (MDB)", "#3b8758"),
    (pd.Timestamp("2019-01-01"), pd.Timestamp("2022-12-31"), "Bolsonaro (PL)", "#1f3a68"),
    (pd.Timestamp("2023-01-01"), pd.Timestamp("2026-12-31"), "Lula 3 (PT)", "#a02020"),
]
CHAMBER_PRES = [
    (pd.Timestamp("2015-02-02"), pd.Timestamp("2016-07-13"), "Cunha (PMDB)", "#5a5aa6"),
    (pd.Timestamp("2016-07-14"), pd.Timestamp("2021-01-31"), "Maia (DEM)", "#d97706"),
    (pd.Timestamp("2021-02-01"), pd.Timestamp("2025-01-31"), "Lira (PP)", "#552288"),
    (pd.Timestamp("2025-02-01"), pd.Timestamp("2026-12-31"), "Motta\n(Republicanos)", "#888888"),
]


def load_series():
    series = {}
    for nm, lbl in [("euclidean", "MDS-Euclidean"),
                     ("forte", "Antagonism (Strong)")]:
        df = pd.read_csv(POL_DIR / f"average_mds_distances_{nm}.csv")
        df["period_start"] = pd.to_datetime(df["period_start"])
        df["period_end"] = pd.to_datetime(df["period_end"])
        df["mid_date"] = df["period_start"] + (df["period_end"] - df["period_start"]) / 2
        df = df.sort_values("mid_date").reset_index(drop=True)
        # Normalize to z-score for visual comparability
        v = df["Euclidiana_MDS"]
        df["z"] = (v - v.mean()) / v.std()
        series[lbl] = df
    return series


def draw_period_shades(ax, periods, ymin, ymax, alpha=0.08, label_y=None,
                         show_labels=True, font=8.0):
    """Shade alternating sub-periods + label them."""
    for i, (t0, t1, lbl, c) in enumerate(periods):
        ax.axvspan(t0, t1, color=c, alpha=alpha, zorder=0)
        if show_labels and label_y is not None:
            mid = t0 + (t1 - t0) / 2
            ax.text(mid, label_y, lbl, ha="center", va="bottom",
                    fontsize=font, color=c, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2",
                              fc="white", ec=c, lw=0.5, alpha=0.85))


def version_A(series):
    log.info("Version A: single panel")
    fig, ax = plt.subplots(figsize=(11, 5.5))

    palette = {"MDS-Euclidean": "#222222",
               "Antagonism (Strong)": "#a02020"}
    styles = {"MDS-Euclidean": "-",
              "Antagonism (Strong)": "--"}

    for lbl, df in series.items():
        ax.plot(df["mid_date"], df["z"], color=palette[lbl], linestyle=styles[lbl],
                 linewidth=1.8, label=lbl, alpha=0.9)

    ax.set_ylabel("Polarization (z-score, normalized within measure)")
    ax.set_xlabel("Window mid-date (12-month rolling window)")
    ax.set_title("Brazilian legislative polarization 2014-2024 by presidential sub-period",
                  fontsize=11.5, pad=12)
    ax.axhline(0, color="black", linewidth=0.5, alpha=0.4, linestyle=":")
    ax.grid(axis="y", alpha=0.2)

    ymin, ymax = ax.get_ylim()
    # Top half: BR presidents (alpha 0.10) with labels at y=ymax*0.88
    draw_period_shades(ax, BR_PRES, ymin, ymax, alpha=0.10,
                        label_y=ymax * 0.85, font=8.5)
    # Bottom half: chamber presidents labels at y=ymin*0.95 (negative)
    for (t0, t1, lbl, c) in CHAMBER_PRES:
        ax.axvline(t0, color=c, linestyle=":", linewidth=1.2, alpha=0.7)
        mid = t0 + (t1 - t0) / 2
        ax.text(mid, ymin * 0.78 if ymin < 0 else 0.05, "Cham.: " + lbl,
                 ha="center", va="bottom", fontsize=7.5, color=c, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.18", fc="white", ec=c, lw=0.5,
                           alpha=0.85))

    ax.set_xlim(pd.Timestamp("2014-01-01"), pd.Timestamp("2026-06-30"))
    ax.legend(loc="lower right", fontsize=9, frameon=True, framealpha=0.95)

    out = FIGS / "fig_polarization_traj_A.pdf"
    fig.savefig(out)
    log.info(f"  saved {out}")


def version_B(series):
    log.info("Version B: two panels")
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    palette = {"MDS-Euclidean": "#222222",
               "Antagonism (Strong)": "#a02020"}
    styles = {"MDS-Euclidean": "-",
              "Antagonism (Strong)": "--"}

    for ax in axes:
        for lbl, df in series.items():
            ax.plot(df["mid_date"], df["z"], color=palette[lbl],
                     linestyle=styles[lbl], linewidth=1.8, label=lbl, alpha=0.9)
        ax.axhline(0, color="black", linewidth=0.5, alpha=0.4, linestyle=":")
        ax.grid(axis="y", alpha=0.2)
        ax.set_ylabel("Polarization (z-score)")

    # Top panel: Brazilian presidents
    ymin, ymax = axes[0].get_ylim()
    draw_period_shades(axes[0], BR_PRES, ymin, ymax, alpha=0.12,
                        label_y=ymax * 0.85, font=9)
    axes[0].set_title("(A) by Brazilian presidential sub-period",
                       fontsize=10.5, pad=6, loc="left")

    # Bottom panel: Chamber presidents
    ymin, ymax = axes[1].get_ylim()
    draw_period_shades(axes[1], CHAMBER_PRES, ymin, ymax, alpha=0.12,
                        label_y=ymax * 0.85, font=9)
    axes[1].set_title("(B) by Chamber of Deputies presidential sub-period",
                       fontsize=10.5, pad=6, loc="left")

    axes[1].set_xlabel("Window mid-date (12-month rolling window)")
    axes[0].set_xlim(pd.Timestamp("2014-01-01"), pd.Timestamp("2026-06-30"))

    axes[0].legend(loc="lower right", fontsize=9, frameon=True, framealpha=0.95)

    fig.suptitle("Brazilian legislative polarization 2014-2024 across institutional sub-periods",
                  fontsize=12, y=0.995)
    plt.tight_layout()
    out = FIGS / "fig_polarization_traj_B.pdf"
    fig.savefig(out)
    log.info(f"  saved {out}")


def main():
    series = load_series()
    log.info(f"  loaded {len(series)} polarization series")
    version_A(series)
    version_B(series)


if __name__ == "__main__":
    main()
