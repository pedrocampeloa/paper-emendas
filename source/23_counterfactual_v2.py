# -*- coding: utf-8 -*-
"""
23_counterfactual_v2.py — Preço político + counterfactual com main spec
===========================================================================
Lê os coeficientes do main_results_v2.csv (PLIV-bl + FE + cluster) e
calcula:
  - R$/pp de alinhamento (preço político)
  - Y(T=0) counterfactual: alinhamento se emendas zeradas

Output:
  results/price_legislative_support_v2.csv
  results/counterfactual_alignment_v2.csv
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils_v2 as U2


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("23_cf_v2")

    main_path = C.RESULTS / "main_results_v2.csv"
    if not main_path.exists():
        log.error("main_results_v2.csv não encontrado. Rode 20_main_results_v2.py primeiro.")
        return 1
    main = pd.read_csv(main_path, sep=";")

    # Selecionar PLIV-backlog + spec preferida
    sub = main[(main["model"] == "PLIV_FE_cluster")
                  & (main["iv_set"] == "backlog")
                  & (main["spec"] == "full_clean")].copy()
    log.info("Coeficientes PLIV-bl (full_clean+FE+cluster): %d", len(sub))
    log.info("\n%s", sub[["legis","pp_per_unit","ci95_lo_pp","ci95_hi_pp",
                                "stars"]].to_string(index=False))

    # Carregar painel para T̄ e Ȳ
    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["idLegislatura"] = df["idLegislatura"].astype(int)

    rows_price = []
    rows_cf = []
    for _, r in sub.iterrows():
        leg_label = r["legis"]
        df_l = df.copy() if leg_label == "all" else df[df["idLegislatura"] == int(leg_label)]
        T_mean = float(df_l[C.TREATMENT].mean())
        Y_mean = float(df_l[C.TARGET].mean())
        pp = float(r["pp_per_unit"])
        # Preço: R$1M / |pp_per_unit| × R$1M = R$ por pp
        rm_per_pp = (1.0 / pp) if pp != 0 else float("inf")
        rows_price.append({
            "legis": leg_label,
            "pp_per_R$M": round(pp, 4),
            "ci95_lo_pp": r["ci95_lo_pp"],
            "ci95_hi_pp": r["ci95_hi_pp"],
            "R$M_per_pp": round(rm_per_pp, 4) if abs(rm_per_pp) < 1e6 else None,
            "R$_per_pp": (round(rm_per_pp * 1e6, 0)
                            if abs(rm_per_pp) < 1e6 else None),
            "stars": r["stars"],
            "n_obs": int(r["n_obs"]),
            "T_mean_R$M": round(T_mean, 3),
            "Y_mean": round(Y_mean, 4),
        })

        # Counterfactual: Δ pp = pp_per_unit × T̄
        delta_prob = (pp / 100) * T_mean   # delta em probabilidade
        Y_cf = Y_mean - delta_prob
        rows_cf.append({
            "legis": leg_label,
            "Y_observed_pct": round(100 * Y_mean, 2),
            "Y_counterfactual_pct": round(100 * Y_cf, 2),
            "delta_pp": round(100 * delta_prob, 3),
            "%_of_Y_obs": round(100 * delta_prob / Y_mean, 2) if Y_mean else None,
            "T_mean_R$M": round(T_mean, 3),
            "n_obs": int(r["n_obs"]),
        })

    df_price = pd.DataFrame(rows_price)
    df_cf = pd.DataFrame(rows_cf)

    df_price.to_csv(C.RESULTS / "price_legislative_support_v2.csv",
                      sep=";", index=False)
    df_cf.to_csv(C.RESULTS / "counterfactual_alignment_v2.csv",
                   sep=";", index=False)

    log.info("\n=== PRICE OF LEGISLATIVE SUPPORT (v2) ===")
    log.info("\n%s", df_price.to_string(index=False))
    log.info("\n=== COUNTERFACTUAL Y(T=0) (v2) ===")
    log.info("\n%s", df_cf.to_string(index=False))


if __name__ == "__main__":
    main()
