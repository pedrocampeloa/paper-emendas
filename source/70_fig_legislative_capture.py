"""
70_fig_legislative_capture.py
------------------------------
Figure fig_legislative_capture.pdf -- forest plot da Tabela 7 (T5 y_pres_camara).

Mostra o efeito pork-for-votes quando o outcome e' alinhamento com a orientacao
do partido do presidente da Camara, separado por sub-amostra:
  - Leg 55 Maia (DEM)
  - Leg 56 Maia (DEM)
  - Leg 56 Lira (PP)
  - Leg 56 Lira excl PP
  - Leg 56 Lira excl Centrao

Output: paper-emendas/docs/figs/fig_legislative_capture.pdf
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "paper-emendas" / "results"
FIGS = REPO / "paper-emendas" / "docs" / "figs"

mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "savefig.bbox": "tight",
})


def main():
    df = pd.read_csv(RESULTS / "n3_pres_t5_subsamples.csv", sep=";")

    label_map = {
        "leg55_maia": "Leg 55, Maia (DEM)",
        "leg56_maia": "Leg 56, Maia (DEM)",
        "leg56_lira": "Leg 56, Lira (PP)",
        "leg56_lira_excl_pp": r"$\quad$ excl. PP",
        "leg56_lira_excl_centrao": r"$\quad$ excl. Centrão",
    }
    order = ["leg55_maia", "leg56_maia", "leg56_lira",
             "leg56_lira_excl_pp", "leg56_lira_excl_centrao"]
    df = df.set_index("sample").loc[order].reset_index()

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    y = list(range(len(df)))[::-1]

    for i, (_, r) in enumerate(df.iterrows()):
        yi = y[i]
        coef = r["pp_per_unit"]
        lo, hi = r["ci95_lo_pp"], r["ci95_hi_pp"]
        sig = (lo > 0) or (hi < 0)
        color = "#1f3a68" if sig else "#888888"
        ax.errorbar(coef, yi, xerr=[[coef - lo], [hi - coef]],
                    fmt="o", color=color, ecolor=color, capsize=3,
                    markersize=6, linewidth=1.3)
        n_str = f"N = {int(r['n_obs']):,}"
        ax.text(hi + 0.18, yi, n_str, va="center", fontsize=8, color="#444444")

    ax.axvline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels([label_map[s] for s in df["sample"]])
    ax.set_xlabel("Effect (pp per R\\$1M)")
    ax.set_xlim(-5.5, 2.5)
    ax.set_title("Pork-for-votes effect when outcome is alignment with\nChamber president's party",
                 fontsize=11, pad=10)
    ax.grid(axis="x", alpha=0.2, linestyle=":")

    out = FIGS / "fig_legislative_capture.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
