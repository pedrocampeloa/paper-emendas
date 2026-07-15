"""
91_fig_cforest.py
------------------
Figure: CATE vs polarization for the 3 outcomes (gov, pres, centrao).

Three panels horizontally, each showing pointwise CATE (from CausalIVForest)
as a function of Strong Divergence. Smoothed via local regression for the
trend line; scatter for the point-wise estimates.

Source: results/n3_cforest_cate.csv (produced by 90_causal_forest_iv.py)
Output: docs/figs/fig_cforest_cate.pdf
"""

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
})


def lowess_smooth(x, y, frac=0.3, n_pts=80):
    """Manual lowess-like smoothing for plotting trend lines."""
    order = np.argsort(x)
    x_sorted, y_sorted = x[order], y[order]
    grid = np.linspace(x.min(), x.max(), n_pts)
    smoothed = np.full(n_pts, np.nan)
    h = frac * len(x_sorted)
    for i, g in enumerate(grid):
        dist = np.abs(x_sorted - g)
        k = max(50, int(h))
        idx = np.argsort(dist)[:k]
        w = (1 - (dist[idx] / dist[idx].max()) ** 3) ** 3
        # Locally weighted linear regression
        x_local = x_sorted[idx]
        y_local = y_sorted[idx]
        try:
            X = np.column_stack([np.ones_like(x_local), x_local])
            W = np.diag(w)
            coef = np.linalg.solve(X.T @ W @ X, X.T @ W @ y_local)
            smoothed[i] = coef[0] + coef[1] * g
        except Exception:
            smoothed[i] = np.average(y_local, weights=w)
    return grid, smoothed


def main():
    df = pd.read_csv(RESULTS / "n3_cforest_cate.csv", sep=";")
    print(f"loaded {len(df)} CATE records ({df['outcome'].value_counts().to_dict()})")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharey=True)

    outcomes = [
        ("gov", "Alignment with Executive", "#a02020"),
        ("pres", "Alignment with Chamber president", "#1f3a68"),
        ("centrao", "Alignment with Centrão", "#3b8758"),
    ]

    for ax, (tag, title, color) in zip(axes, outcomes):
        d = df[df["outcome"] == tag].dropna(subset=["pol_forte", "cate_pp"]).copy()
        if len(d) < 30:
            ax.set_title(title)
            ax.text(0.5, 0.5, "insufficient data", ha="center",
                    transform=ax.transAxes)
            continue
        # Tighter clipping at p5/p95 within outcome for visualization
        lo, hi = np.percentile(d["cate_pp"], [5, 95])
        d = d[(d["cate_pp"] >= lo) & (d["cate_pp"] <= hi)]

        x = d["pol_forte"].values
        y = d["cate_pp"].values

        ax.scatter(x, y, s=5, c=color, alpha=0.18)
        gx, gy = lowess_smooth(x, y, frac=0.4)
        ax.plot(gx, gy, color="black", linewidth=2.2, label="LOWESS fit")
        ax.axhline(0, color="black", linewidth=0.6, alpha=0.5, linestyle=":")

        ax.set_xlabel("Strong Divergence (polarization)")
        ax.set_title(title, fontsize=10.5)
        if ax is axes[0]:
            ax.set_ylabel("CATE (pp per R\\$1M)")

    fig.suptitle("Heterogeneous treatment effects via Causal IV Forest, by polarization",
                  fontsize=12, y=1.02)
    out = FIGS / "fig_cforest_cate.pdf"
    fig.savefig(out)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
