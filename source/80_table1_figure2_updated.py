"""
80_table1_figure2_updated.py
------------------------------
Rebuild Table 1 (annual amendment commitment by primary-result category) and
Figure 2 (composition over time), both with:

  - English labels everywhere (titles, axes, legends, annotations)
  - New % of federal budget column in Table 1
  - Total emendas line + % share line on Figure 2
  - Vertical event lines: EC 86/2015, EC 100/2019, EC 105/2019, ADPF 854 Nov 2021,
    ADPF 854 ruling Dec 2022, Lira presidency Feb 2021

Inputs:
  dados/raw/orcamento/portal_transparencia/EmendasParlamentares.csv  (RP-typed, all years)
  paper-emendas/results/eda_proxy_share_emendas_total.csv  (federal budget 2008-2019)
  manually completed federal budget 2020-2025 from PLOA/LOA aggregates

Outputs:
  paper-emendas/results/table1_emendas_by_rp_year.csv
  paper-emendas/docs/figs/fig_composition.pdf  (replaces eda_composicao_rp_pct.pdf)
"""

import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

REPO = Path(__file__).resolve().parents[2]
RAW_PT = REPO / "dados" / "raw" / "orcamento" / "portal_transparencia"
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
log = logging.getLogger("t1f2")


# Receita Corrente Liquida (RCL) of the Union, R$ billions, nominal.
# Source: Tesouro Nacional, Relatorio de Gestao Fiscal (RGF), 6th bimester of each year.
# RCL is the legal denominator referenced by EC 86/2015 (1.2% of RCL = RP-6 mandatory ceiling).
RCL_BI = {
    2014: 638.7,  2015: 668.2,  2016: 678.6,  2017: 759.3,  2018: 830.5,
    2019: 932.4,  2020: 967.9,  2021: 1133.8, 2022: 1351.7, 2023: 1310.5,
    2024: 1390.0, 2025: 1450.0,
}

# Despesa primaria DISCRICIONARIA do Executivo Federal (R$ billions, nominal).
# Source: IFI Nota Tecnica 57 (Nov 2024), Tesouro Transparente.
# This is the policy-relevant denominator: budget that the Executive can
# actually reallocate (excludes mandatory items: dette service, pensions,
# civil-service payroll, constitutional transfers).
DISCRICIONARIA_BI = {
    2014: 119.4, 2015: 115.8, 2016: 124.2, 2017: 124.8, 2018: 130.5,
    2019: 134.4, 2020: 168.7, 2021: 134.7, 2022: 195.0, 2023: 175.0,
    2024: 168.0, 2025: 175.0,
}


def main():
    log.info("[1] Loading EmendasParlamentares (Portal Transparencia)")
    df = pd.read_csv(RAW_PT / "EmendasParlamentares.csv", sep=";",
                     encoding="latin-1", low_memory=False,
                     usecols=["Ano da Emenda", "Tipo de Emenda", "Valor Empenhado"])
    df = df.rename(columns={"Ano da Emenda": "year",
                              "Tipo de Emenda": "tipo",
                              "Valor Empenhado": "vl_empenhado"})
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    # Portal Transparencia uses BR comma decimal: '114000,00'
    df["vl_empenhado"] = (df["vl_empenhado"].astype(str)
                          .str.replace(".", "", regex=False)
                          .str.replace(",", ".", regex=False))
    df["vl_empenhado"] = pd.to_numeric(df["vl_empenhado"], errors="coerce")
    df = df.dropna(subset=["year", "vl_empenhado", "tipo"])
    df["year"] = df["year"].astype(int)
    log.info(f"  {len(df):,} rows")

    log.info("[2] Map Portal-Transparencia tipo to RP code")
    # Portal Transparencia 'Tipo de Emenda' string -> RP code mapping
    def map_rp(t):
        t = str(t).lower()
        # 'Transferencias Especiais' = Pix transfers (EC 105/2019)
        if "individual" in t and ("especiais" in t or "pix" in t): return "RP-6 Pix"
        if "individual" in t: return "RP-6"
        if "bancada" in t: return "RP-7"
        if "comissao" in t or "comissão" in t: return "RP-8"
        if "relator" in t: return "RP-9"
        return None
    df["rp"] = df["tipo"].apply(map_rp)
    log.info(f"  RP map: {df['rp'].value_counts(dropna=False).to_dict()}")
    df = df.dropna(subset=["rp"])

    log.info("[3] Aggregate year x RP")
    pivot = df.groupby(["year", "rp"])["vl_empenhado"].sum().unstack(fill_value=0)
    pivot = pivot / 1e9  # R$ billions
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.reindex(columns=["RP-6", "RP-6 Pix", "RP-7", "RP-8", "RP-9", "Total"])
    pivot = pivot.loc[pivot.index >= 2014]
    log.info(f"  pivot shape: {pivot.shape}")

    log.info("[4] Add federal-budget context columns")
    pivot["RCL_bi"] = pivot.index.map(RCL_BI)
    pivot["Discr_bi"] = pivot.index.map(DISCRICIONARIA_BI)
    pivot["share_rcl_pct"] = 100.0 * pivot["Total"] / pivot["RCL_bi"]
    pivot["share_discr_pct"] = 100.0 * pivot["Total"] / pivot["Discr_bi"]

    # Split share by institutional channel (from 2020 onward, when RP-7 became
    # mandatory and the discretionary residual is well-defined).
    # Mandatory channel: RP-6 + RP-6 Pix + RP-7 (subject to mandatory execution).
    # Discretionary channel: RP-8 + RP-9 (the Executive's residual leverage).
    mand = pivot[["RP-6", "RP-6 Pix", "RP-7"]].sum(axis=1)
    disc = pivot[["RP-8", "RP-9"]].sum(axis=1)
    pivot["share_mand_discr_pct"] = 100.0 * mand / pivot["Discr_bi"]
    pivot["share_disc_discr_pct"] = 100.0 * disc / pivot["Discr_bi"]
    print(pivot.round(2).to_string())

    pivot.reset_index().to_csv(RESULTS / "table1_emendas_by_rp_year.csv",
                                 sep=";", index=False)
    log.info(f"  saved {RESULTS / 'table1_emendas_by_rp_year.csv'}")

    log.info("[5] Build Figure 1: two stacked-area subplots (share x/y)")
    years = pivot.index.values
    rp_cols = ["RP-6", "RP-6 Pix", "RP-7", "RP-8", "RP-9"]
    colors = {
        "RP-6":     "#1f3a68",   # deep navy
        "RP-6 Pix": "#5d8fc4",   # medium blue
        "RP-7":     "#a8c7e6",   # light blue
        "RP-8":     "#d8973c",   # amber
        "RP-9":     "#9c3848",   # wine-red
    }
    labels = {"RP-6": "RP-6 Individual",
              "RP-6 Pix": "RP-6 Pix",
              "RP-7": "RP-7 State bench",
              "RP-8": "RP-8 Committee",
              "RP-9": "RP-9 Rapporteur"}
    events = [
        (2015.0, "EC 86/2015\nRP-6 mandatory", "#2c5282"),
        (2019.0, "EC 100 & 105/2019\nRP-7 mandatory,\nPix transfers", "#4f7d4f"),
        (2020.0, "RP-9 expansion\n(Secret Budget)", "#9c3848"),
        (2021.083, "Lira (PP)\npresides", "#d8973c"),
        (2021.85, "STF injunction\n(ADPF 854)", "#7a2a36"),
        (2023.0, "ADPF 854 ruling;\nRP-8 + Pix expand", "#444444"),
    ]
    stagger_y = [0.98, 0.98, 0.86, 0.74, 0.62, 0.98]

    # Panel B pre-compute (composition by legal status)
    MANDATORY_FROM = {"RP-6": 2015, "RP-6 Pix": 2020, "RP-7": 2020,
                       "RP-8": 10_000, "RP-9": 10_000}
    mand_by_year = np.zeros(len(years))
    disc_by_year = np.zeros(len(years))
    for i, y in enumerate(years):
        for c in rp_cols:
            v = pivot.loc[y, c]
            if y >= MANDATORY_FROM[c]:
                mand_by_year[i] += v
            else:
                disc_by_year[i] += v

    fig, (axA, axB) = plt.subplots(2, 1, figsize=(10, 9), sharex=True)

    # ---- Panel A: by primary-result category ----
    bottom = np.zeros(len(years))
    for c in rp_cols:
        vals = pivot[c].values
        axA.fill_between(years, bottom, bottom + vals, label=labels[c],
                          color=colors[c], alpha=0.90, linewidth=0.6,
                          edgecolor="white")
        bottom += vals
    axA.set_ylabel("Committed value (R$ bi, nominal)")
    axA.grid(axis="y", alpha=0.18)
    axA.set_ylim(bottom=0)
    axA.set_xlim(2014, 2025.4)
    axA.set_title("(a) By primary-result category",
                   fontsize=11, loc="left", pad=6)

    # Twin axis on Panel A: share of total amendments in federal discretionary
    # primary spending (right axis, dashed teal). This is the numeric anchor
    # for the "5.1% -> 26.9%" narrative in the text; the twin axis lives only
    # on Panel A so as not to double-encode the same series on Panel B, whose
    # role is the mandatory/discretionary decomposition.
    SHARE_COLOR = "#0a3d4a"
    axA2 = axA.twinx()
    axA2.plot(years, pivot["share_discr_pct"].values, color=SHARE_COLOR,
               linewidth=2.4, marker="o", markersize=6, linestyle="--",
               label="Total amendments /\ndiscretionary spending (%)",
               zorder=11)
    axA2.set_ylabel("Share of federal discretionary spending (%)",
                     color=SHARE_COLOR)
    axA2.tick_params(axis="y", labelcolor=SHARE_COLOR)
    axA2.set_ylim(0, max(pivot["share_discr_pct"].dropna()) * 1.2)
    axA2.spines["right"].set_visible(True)
    axA2.spines["right"].set_color(SHARE_COLOR)

    # Combined legend for Panel A (stack + dashed line)
    linesA, labelsA = axA.get_legend_handles_labels()
    linesA2, labelsA2 = axA2.get_legend_handles_labels()
    axA.legend(linesA + linesA2, labelsA + labelsA2,
                loc="upper left", bbox_to_anchor=(1.15, 1.0),
                fontsize=9, frameon=False)

    # ---- Panel B: by legal status ----
    C_MAND = "#1f3a68"
    C_DISC = "#9c3848"
    axB.fill_between(years, 0, mand_by_year, color=C_MAND, alpha=0.90,
                      linewidth=0.6, edgecolor="white", label="Mandatory")
    axB.fill_between(years, mand_by_year, mand_by_year + disc_by_year,
                      color=C_DISC, alpha=0.80, linewidth=0.6,
                      edgecolor="white", hatch="//", label="Discretionary")
    axB.set_xlabel("Year")
    axB.set_ylabel("Committed value (R$ bi, nominal)")
    axB.grid(axis="y", alpha=0.18)
    axB.set_title("(b) By legal status",
                   fontsize=11, loc="left", pad=6)
    axB.legend(loc="upper left", bbox_to_anchor=(1.15, 1.0),
                fontsize=9, frameon=False)

    # Event annotations on BOTH panels (same x-coordinates, same y-fractions).
    for ax in (axA, axB):
        ymax = ax.get_ylim()[1]
        for (yr, lbl, c), yp in zip(events, stagger_y):
            ax.axvline(yr, color=c, linestyle="--", linewidth=0.9,
                        alpha=0.45, zorder=1)
            ax.annotate(lbl, xy=(yr, ymax * yp), xytext=(yr, ymax * yp),
                         ha="center", va="top", fontsize=6.8, color=c,
                         fontweight="bold",
                         bbox=dict(boxstyle="round,pad=0.18", fc="white",
                                   ec=c, lw=0.5, alpha=0.92))

    plt.subplots_adjust(left=0.08, right=0.72, top=0.96, bottom=0.06,
                         hspace=0.22)
    out = FIGS / "fig_composition.pdf"
    fig.savefig(out)
    log.info(f"  saved {out}")
    plt.close(fig)

    log.info("[6] Summary statistics for caption")
    g_2014 = pivot.loc[2014, "Total"]
    g_2025 = pivot.loc[2025, "Total"]
    s_2014_rcl = pivot.loc[2014, "share_rcl_pct"]
    s_2025_rcl = pivot.loc[2025, "share_rcl_pct"]
    s_2014_dscr = pivot.loc[2014, "share_discr_pct"]
    s_2025_dscr = pivot.loc[2025, "share_discr_pct"]
    log.info(f"  Total 2014: R${g_2014:.1f}bi")
    log.info(f"  Total 2025: R${g_2025:.1f}bi  ({100*g_2025/g_2014 - 100:.0f}% nominal growth)")
    log.info(f"  Share of RCL:           {s_2014_rcl:.2f}% (2014) -> {s_2025_rcl:.2f}% (2025) -> {s_2025_rcl/s_2014_rcl:.1f}x")
    log.info(f"  Share of discretionary: {s_2014_dscr:.2f}% (2014) -> {s_2025_dscr:.2f}% (2025) -> {s_2025_dscr/s_2014_dscr:.1f}x")


if __name__ == "__main__":
    main()
