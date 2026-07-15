"""
83_fig_seasonality_en.py
-------------------------
Rebuild fig_seasonality.pdf with English labels throughout.

The earlier version had "empenhos" (Portuguese for "commitments") in the
y-axis label, legend, title, and Q4 annotation. This script replaces all
of those with "commitments".

Data source: panel_emendas_pre.csv (treatment, in millions of R$),
             panel_features.csv (vote dates).
Output: paper-emendas/docs/figs/fig_seasonality.pdf
"""

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

sys.path.insert(0, str(Path(__file__).parent))
import _config as _CFG

REPO = Path(__file__).resolve().parents[2]
PANEL = Path(_CFG.PANEL)
FIGS = REPO / "paper-emendas" / "docs" / "figs"

mpl.rcParams.update({
    "font.family": "serif", "font.size": 10,
    "axes.spines.right": False, "axes.spines.top": False,
    "savefig.bbox": "tight",
})

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("seas")


def main():
    log.info("Loading panel_features for vote dates (Leg 55 + 56)")
    pf = pd.read_csv(PANEL / "panel_features.csv", sep=";",
                     usecols=["idVotacao", "data", "idLegislatura"],
                     low_memory=False)
    pf["data"] = pd.to_datetime(pf["data"])
    pf = pf[pf["idLegislatura"].isin([55, 56])].copy()
    votes_unique = pf.drop_duplicates("idVotacao")[["data"]]
    log.info(f"  {len(votes_unique):,} unique votacoes")

    log.info("Loading SICONV empenho + emenda + convenio to filter to "
             "individual amendments only (matches paper treatment RP-6)")
    SICONV_DIR = REPO / "dados" / "raw" / "orcamento" / "transferegov_bulk"

    # Step 1: convenios linked to deputy individual amendments
    cv = pd.read_csv(SICONV_DIR / "siconv_emenda.csv", sep=";",
                       usecols=["ID_PROPOSTA", "TIPO_PARLAMENTAR"],
                       dtype=str, low_memory=False)
    # INDIVIDUAL + BANCADA = the two mandatory-execution categories that
    # define the deputy-attributable amendment universe in our panel
    # (RP-6 + RP-7). The IV operates on the same universe.
    cv = cv[cv["TIPO_PARLAMENTAR"].isin(["INDIVIDUAL", "BANCADA"])]
    propostas_indiv = set(cv["ID_PROPOSTA"].dropna().unique())
    log.info(f"  {len(propostas_indiv):,} individual-amendment proposals")

    # Step 2: convenios from those proposals
    cnv = pd.read_csv(SICONV_DIR / "siconv_convenio.csv", sep=";",
                       usecols=["NR_CONVENIO", "ID_PROPOSTA"],
                       dtype=str, low_memory=False)
    cnv = cnv[cnv["ID_PROPOSTA"].isin(propostas_indiv)]
    nr_convenios_indiv = set(cnv["NR_CONVENIO"].dropna().unique())
    log.info(f"  {len(nr_convenios_indiv):,} convenios from individual amendments")

    # Step 3: empenhos for those convenios
    emp = pd.read_csv(SICONV_DIR / "siconv_empenho.csv", sep=";",
                       usecols=["NR_CONVENIO", "DATA_EMISSAO", "VALOR_EMPENHO",
                                 "DESC_TIPO_NOTA"],
                       dtype=str, low_memory=False)
    emp = emp[emp["NR_CONVENIO"].isin(nr_convenios_indiv)].copy()
    log.info(f"  {len(emp):,} empenhos for individual-amendment convenios")

    emp["VALOR_EMPENHO"] = (emp["VALOR_EMPENHO"].astype(str)
                              .str.replace(",", ".", regex=False))
    emp["VALOR_EMPENHO"] = pd.to_numeric(emp["VALOR_EMPENHO"], errors="coerce")
    emp["DATA_EMISSAO"] = pd.to_datetime(emp["DATA_EMISSAO"],
                                          format="%d/%m/%Y", errors="coerce")
    emp = emp.dropna(subset=["DATA_EMISSAO", "VALOR_EMPENHO"])

    # Keep only positive (forward) commitments, excluding cancellations
    KEEP_TYPES = {"Empenho Original", "Global", "Ordinário", "Estimativo",
                   "Reforço de Empenho", "Empenho de Despesa Pré-Empenhada"}
    emp = emp[emp["DESC_TIPO_NOTA"].isin(KEEP_TYPES)]
    emp = emp[emp["VALOR_EMPENHO"] > 0]

    # Restrict to study window
    emp = emp[(emp["DATA_EMISSAO"].dt.year >= 2016) &
                (emp["DATA_EMISSAO"].dt.year <= 2022)].copy()
    emp["month"] = emp["DATA_EMISSAO"].dt.month
    log.info(f"  {len(emp):,} positive original commitments (individual) 2016-2022")

    monthly_em = emp.groupby("month")["VALOR_EMPENHO"].sum()
    monthly_em_pct = 100 * monthly_em / monthly_em.sum()

    # Vote count per month
    monthly_votes = votes_unique["data"].dt.month.value_counts().sort_index()
    monthly_votes_pct = 100 * monthly_votes / monthly_votes.sum()

    months = list(range(1, 13))
    mlabels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    log.info(f"Dec commit %: {monthly_em_pct.get(12, 0):.1f}")
    log.info(f"May votes %:  {monthly_votes_pct.get(5, 0):.1f}")

    log.info("Building figure")
    fig, ax1 = plt.subplots(figsize=(10, 5))

    BAR_COLOR = "#5b8cb8"   # softer blue (commitments)
    LINE_COLOR = "#c0524d"  # warm red (votes)

    # Q4 shading
    ax1.axvspan(9.5, 12.5, color="#f5e6c8", alpha=0.45, zorder=0,
                label="Q4 (fiscal year-end)")

    bars = ax1.bar(months, [monthly_em_pct.get(m, 0) for m in months],
                    color=BAR_COLOR, alpha=0.92,
                    label="Amendment commitments (% of annual total)")
    ax1.set_ylabel("Amendment commitments (% of annual total)", color=BAR_COLOR)
    ax1.tick_params(axis="y", labelcolor=BAR_COLOR)
    ax1.set_xticks(months)
    ax1.set_xticklabels(mlabels)
    ax1.set_xlabel("Month")
    ax1.set_ylim(0, max(monthly_em_pct.max(), monthly_votes_pct.max()) * 1.15)
    ax1.grid(axis="y", alpha=0.15)

    ax2 = ax1.twinx()
    ax2.plot(months, [monthly_votes_pct.get(m, 0) for m in months],
             color=LINE_COLOR, marker="o", linewidth=2.0, markersize=6,
             label="Roll-call votes (% of annual total)")
    ax2.set_ylabel("Roll-call votes (% of annual total)", color=LINE_COLOR)
    ax2.tick_params(axis="y", labelcolor=LINE_COLOR)
    ax2.set_ylim(0, max(monthly_em_pct.max(), monthly_votes_pct.max()) * 1.4)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(LINE_COLOR)

    # Annotations
    dec_pct = monthly_em_pct.get(12, 0)
    ax1.annotate(f"Q4 deadline:\n{dec_pct:.1f}% of commitments\nin December alone",
                  xy=(12, dec_pct), xytext=(9.0, dec_pct - 8),
                  fontsize=8.5, color="#1f3a68", fontweight="bold",
                  ha="left", va="top",
                  bbox=dict(boxstyle="round,pad=0.3", fc="white",
                            ec="#1f3a68", lw=0.6, alpha=0.92),
                  arrowprops=dict(arrowstyle="->", color="#1f3a68", lw=0.8))
    max_v_month = monthly_votes_pct.idxmax()
    max_v_pct = monthly_votes_pct.max()
    ax1.annotate("Peak voting\nactivity",
                  xy=(max_v_month, max_v_pct * 0.4),
                  xytext=(max_v_month - 0.7, max_v_pct * 0.55),
                  fontsize=8.5, color=LINE_COLOR, fontweight="bold",
                  ha="center", va="bottom",
                  bbox=dict(boxstyle="round,pad=0.3", fc="white",
                            ec=LINE_COLOR, lw=0.6, alpha=0.92))

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
                loc="upper left", fontsize=8.5, frameon=True, framealpha=0.95)

    ax1.set_title("Seasonal misalignment: amendment commitments vs. roll-call votes\n"
                   "(Legislatures 55-56, 2016-2022)",
                   fontsize=11, pad=10)

    out = FIGS / "fig_seasonality.pdf"
    fig.savefig(out)
    log.info(f"saved {out}")


if __name__ == "__main__":
    main()
