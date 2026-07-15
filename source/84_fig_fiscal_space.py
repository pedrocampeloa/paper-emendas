"""
84_fig_fiscal_space.py
-----------------------
Two complementary figures showing how the Executive's discretionary
fiscal space eroded as parliamentary amendments grew and shifted from
discretionary to mandatory channels:

  Figure A (simple, 2 lines): Federal discretionary primary spending vs.
                              total parliamentary amendments, R$ billions.
                              Shows the "scissor": the discretionary base
                              hovering while amendments grow into it.

  Figure B (stacked 5 categories): Decomposition of federal primary spending
                                    into rigid (personnel + debt + pensions),
                                    other mandatory (constitutional transfers),
                                    mandatory amendments (RP-6 + RP-7 post-EC),
                                    discretionary amendments (RP-8 + RP-9),
                                    and free Executive discretionary.

Data sources:
  - Federal Treasury RGF reports (RCL series)
  - IFI Technical Note 57 (Nov 2024) for decomposition of primary spending
  - SICONV/Portal da Transparencia for amendment values (Table 1)

Outputs:
  paper-emendas/docs/figs/fig_fiscal_space_A.pdf
  paper-emendas/docs/figs/fig_fiscal_space_B.pdf
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
})

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("fiscal")


# ==========================================================================
# Federal primary-spending decomposition, R$ billions, nominal.
# Sources: IFI Technical Note 57 (Nov 2024) Table 1 + 2; Tesouro Transparente
# annual RGF aggregates; LOA 2025. Numbers rounded to nearest R$ billion.
# ==========================================================================

# Total primary spending of the Union (despesa primaria total, R$ bi)
PRIMARY_TOTAL_BI = {
    2014: 1100, 2015: 1170, 2016: 1290, 2017: 1340, 2018: 1390,
    2019: 1455, 2020: 1750, 2021: 1620, 2022: 1830, 2023: 2040,
    2024: 2155, 2025: 2235,
}

# RIGID: personnel + payroll + social-security benefits + debt service +
# unemployment + small structural transfers. Subject to legal/constitutional
# floor; truly impossible to reallocate within the year.
RIGID_BI = {
    2014: 720, 2015: 800, 2016: 880, 2017: 925, 2018: 970,
    2019: 1025, 2020: 1140, 2021: 1110, 2022: 1245, 2023: 1395,
    2024: 1475, 2025: 1530,
}

# OTHER MANDATORY: constitutional transfers to states/municipalities, FUNDEB,
# health/education legal floors NOT yet captured under the amendment regime
# (excludes RP-6/7 mandatory amendments, which we count separately).
OTHER_MANDATORY_BI = {
    2014: 261, 2015: 251, 2016: 297, 2017: 290, 2018: 290,
    2019: 296, 2020: 442, 2021: 374, 2022: 390, 2023: 470,
    2024: 510, 2025: 530,
}

# Discretionary residual = PRIMARY - RIGID - OTHER_MANDATORY (this is the
# IFI/Tesouro definition of despesa primaria discricionaria). Within this
# residual we further separate amendments (mandatory RP-6+RP-7, then
# discretionary RP-8+RP-9) from "free discretionary".
DISCRETIONARY_BI = {y: PRIMARY_TOTAL_BI[y] - RIGID_BI[y] - OTHER_MANDATORY_BI[y]
                    for y in PRIMARY_TOTAL_BI}
log.info(f"Discretionary derived: 2014={DISCRETIONARY_BI[2014]}, "
         f"2025={DISCRETIONARY_BI[2025]}")


def main():
    # ---- Load amendment composition from Table 1 ----
    t = pd.read_csv(RESULTS / "table1_emendas_by_rp_year.csv", sep=";")
    t = t.set_index("year")
    t = t[t.index <= 2025]

    log.info("Building fiscal-space panel")
    df = pd.DataFrame({"year": list(PRIMARY_TOTAL_BI.keys())}).set_index("year")
    df["primary_total"]   = df.index.map(PRIMARY_TOTAL_BI)
    df["rigid"]           = df.index.map(RIGID_BI)
    df["other_mandatory"] = df.index.map(OTHER_MANDATORY_BI)
    df["discretionary"]   = df.index.map(DISCRETIONARY_BI)
    df["mandatory_amend"] = t["RP-6"].fillna(0) + t["RP-6 Pix"].fillna(0) + t["RP-7"].fillna(0)
    df["discr_amend"]     = t["RP-8"].fillna(0) + t["RP-9"].fillna(0)
    df["total_amend"]     = df["mandatory_amend"] + df["discr_amend"]
    df["free_discr"]      = df["discretionary"] - df["mandatory_amend"] - df["discr_amend"]
    df["free_discr"] = df["free_discr"].clip(lower=0)
    print(df.round(1).to_string())

    # =====================================================================
    # FIGURE A — Simple: 2 lines (discretionary base vs total amendments)
    # =====================================================================
    log.info("Building Figure A (simple 2-line)")
    fig, ax = plt.subplots(figsize=(9, 4.8))

    yrs = df.index.values
    DISCR_C = "#0a3d4a"   # deep teal
    AMEND_C = "#9c3848"   # wine red

    ax.plot(yrs, df["discretionary"].values, color=DISCR_C,
            linewidth=2.2, marker="o", markersize=6, linestyle="-",
            label="Federal discretionary primary spending (R\\$ bi)")
    ax.plot(yrs, df["total_amend"].values, color=AMEND_C,
            linewidth=2.2, marker="s", markersize=6, linestyle="-",
            label="Total parliamentary amendments (R\\$ bi)")

    ax.fill_between(yrs, df["total_amend"].values, df["discretionary"].values,
                    where=(df["discretionary"].values > df["total_amend"].values),
                    color=DISCR_C, alpha=0.07,
                    label="Free fiscal space (residual)")

    # Annotations
    for yr, lbl, c in [
        (2015, "EC 86", "#2c5282"),
        (2019, "EC 100/105", "#4f7d4f"),
        (2020, "RP-9 expansion", "#9c3848"),
        (2023, "ADPF 854", "#444444"),
    ]:
        ax.axvline(yr, color=c, linestyle="--", linewidth=0.9, alpha=0.4)

    ax.set_xlabel("Year")
    ax.set_ylabel("R\\$ billions, nominal")
    ax.set_title("Federal discretionary base vs.\\ total parliamentary amendments, 2014--2025",
                 fontsize=11, pad=10)
    ax.grid(axis="y", alpha=0.2)
    ax.set_xlim(2014, 2025.4)
    ax.set_ylim(0, max(df["discretionary"].max(), df["total_amend"].max()) * 1.15)
    ax.legend(loc="upper left", fontsize=9, frameon=False)

    out_a = FIGS / "fig_fiscal_space_A.pdf"
    fig.savefig(out_a)
    log.info(f"  saved {out_a}")
    plt.close(fig)

    # =====================================================================
    # FIGURE B — Stacked: 5 categories of primary spending
    # =====================================================================
    log.info("Building Figure B (stacked 5-category)")
    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Convert to share of primary total (%)
    cats = ["rigid", "other_mandatory", "mandatory_amend", "discr_amend", "free_discr"]
    labels = {
        "rigid":            "Rigid (personnel, social security, debt service)",
        "other_mandatory":  "Other mandatory (constitutional transfers, health/educ floors)",
        "mandatory_amend":  "Mandatory amendments (RP-6 + RP-7, post EC 86/100)",
        "discr_amend":      "Discretionary amendments (RP-8 + RP-9)",
        "free_discr":       "Free Executive discretionary",
    }
    colors_b = {
        "rigid":            "#7a7a7a",   # neutral gray
        "other_mandatory":  "#b5b5b5",   # light gray
        "mandatory_amend":  "#1f6e3d",   # forest green
        "discr_amend":      "#9c3848",   # wine red
        "free_discr":       "#2c5282",   # deep blue
    }

    yrs = df.index.values
    bottom = np.zeros(len(yrs))
    for c in cats:
        share = 100.0 * df[c].values / df["primary_total"].values
        ax.fill_between(yrs, bottom, bottom + share, color=colors_b[c],
                        alpha=0.88, linewidth=0.4, edgecolor="white",
                        label=labels[c])
        bottom += share

    ax.set_xlabel("Year")
    ax.set_ylabel("Share of federal primary spending (\\%)")
    ax.set_title("Decomposition of federal primary spending, 2014--2025\n"
                 "Where parliamentary amendments fit in the fiscal architecture",
                 fontsize=11, pad=10)
    ax.set_xlim(2014, 2025.4)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.15)

    # Vertical event lines
    for yr in [2015, 2019, 2020, 2023]:
        ax.axvline(yr, color="white", linestyle=":", linewidth=0.7, alpha=0.6)

    ax.legend(loc="upper left", bbox_to_anchor=(1.005, 1.0),
              fontsize=8, frameon=False)
    plt.subplots_adjust(left=0.07, right=0.66, top=0.90, bottom=0.10)

    out_b = FIGS / "fig_fiscal_space_B.pdf"
    fig.savefig(out_b)
    log.info(f"  saved {out_b}")
    plt.close(fig)

    # =====================================================================
    # FIGURE C — Zoom into the top: show only the discretionary slice
    # decomposed (amendments mandatory, amendments discretionary, free)
    # =====================================================================
    log.info("Building Figure C (zoom on discretionary slice)")
    fig, ax = plt.subplots(figsize=(10, 5))

    # Within DISCRETIONARY only: 3 components
    free_pct = 100 * df["free_discr"] / df["discretionary"]
    mand_pct = 100 * df["mandatory_amend"] / df["discretionary"]
    disc_pct = 100 * df["discr_amend"] / df["discretionary"]
    yrs = df.index.values

    bottom = np.zeros(len(yrs))
    ax.fill_between(yrs, bottom, free_pct, color="#2c5282", alpha=0.88,
                    linewidth=0.4, edgecolor="white",
                    label="Free Executive discretionary (residual)")
    bottom = free_pct.values
    ax.fill_between(yrs, bottom, bottom + mand_pct.values, color="#1f6e3d",
                    alpha=0.88, linewidth=0.4, edgecolor="white",
                    label="Mandatory amendments (RP-6 + RP-7)")
    bottom = bottom + mand_pct.values
    ax.fill_between(yrs, bottom, bottom + disc_pct.values, color="#9c3848",
                    alpha=0.88, linewidth=0.4, edgecolor="white",
                    label="Discretionary amendments (RP-8 + RP-9, incl.\\ Secret Budget)")

    ax.set_xlabel("Year")
    ax.set_ylabel("Share of federal discretionary spending (\\%)")
    ax.set_title("Composition of the Executive's discretionary fiscal space, 2014--2025",
                 fontsize=11, pad=10)
    ax.set_xlim(2014, 2025.4)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.15)

    for yr in [2015, 2019, 2020, 2023]:
        ax.axvline(yr, color="white", linestyle=":", linewidth=0.7, alpha=0.7)

    ax.legend(loc="lower left", fontsize=9, frameon=True, framealpha=0.92)

    out_c = FIGS / "fig_fiscal_space_C.pdf"
    fig.savefig(out_c)
    log.info(f"  saved {out_c}")
    plt.close(fig)

    # Save the decomposition for table use
    df.to_csv(RESULTS / "fiscal_space_decomposition.csv", sep=";")
    log.info(f"  saved {RESULTS / 'fiscal_space_decomposition.csv'}")

    # Summary stats for caption
    log.info("\nSummary:")
    log.info(f"  2014 free discretionary: R${df.loc[2014,'free_discr']:.0f}bi "
             f"({100*df.loc[2014,'free_discr']/df.loc[2014,'primary_total']:.1f}% of primary)")
    log.info(f"  2025 free discretionary: R${df.loc[2025,'free_discr']:.0f}bi "
             f"({100*df.loc[2025,'free_discr']/df.loc[2025,'primary_total']:.1f}% of primary)")
    log.info(f"  2014 amendments share of primary: "
             f"{100*df.loc[2014,'total_amend']/df.loc[2014,'primary_total']:.2f}%")
    log.info(f"  2025 amendments share of primary: "
             f"{100*df.loc[2025,'total_amend']/df.loc[2025,'primary_total']:.2f}%")


if __name__ == "__main__":
    main()
