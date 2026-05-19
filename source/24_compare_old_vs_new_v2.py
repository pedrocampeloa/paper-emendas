# -*- coding: utf-8 -*-
"""
24_compare_old_vs_new_v2.py — Tabela comparativa OLD vs NEW v2
==================================================================
Compara coefientes:
  OLD: paper antigo `unified_results.csv` (theta × 100 = pp/R$M)
  NEW: main_results_v2.csv (PLIV_FE_cluster, full_clean)

Output: results/comparison_old_vs_new_v2.csv
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("24_cmp_v2")

    old = pd.read_csv(C.LEGACY / "unified_results.csv", sep=";")
    # Old window labels: left=pre, both=sym
    old = old[old["window"].isin(["left", "both"])].copy()
    old["window"] = old["window"].replace({"left": "pre", "both": "sym"})
    # OLD `theta` is approx pp/R$M / 100
    old["pp_per_R$M_OLD"] = (100 * old["theta"]).round(4)
    old = old.rename(columns={"pval": "pval_OLD", "stars": "stars_OLD",
                                  "n_obs": "n_obs_OLD"})

    new_v2 = pd.read_csv(C.RESULTS / "main_results_v2.csv", sep=";")
    new_v2 = new_v2[new_v2["spec"] == "full_clean"].copy()
    new_v2["window"] = "pre"
    new_v2 = new_v2.rename(columns={
        "pp_per_unit": "pp_per_R$M_NEW",
        "stars": "stars_NEW",
        "pval": "pval_NEW",
        "n_obs": "n_obs_NEW",
    })
    new_v2["model_clean"] = new_v2["model"].map({
        "PLR_FE_cluster": "PLR",
        "PLIV_FE_cluster": "PLIV",
    })

    cmp = old[["legis", "model", "iv_set", "window",
                  "pp_per_R$M_OLD", "stars_OLD", "n_obs_OLD"]] \
              .merge(
                  new_v2[["legis", "model_clean", "iv_set", "window",
                            "pp_per_R$M_NEW", "ci95_lo_pp", "ci95_hi_pp",
                            "stars_NEW", "n_clusters", "n_obs_NEW"]] \
                      .rename(columns={"model_clean": "model"}),
                  on=["legis", "model", "iv_set", "window"],
                  how="outer", indicator=True,
              )
    cmp["delta"] = cmp["pp_per_R$M_NEW"] - cmp["pp_per_R$M_OLD"]
    cmp["sign_change"] = (cmp["pp_per_R$M_OLD"].fillna(0).gt(0)
                              != cmp["pp_per_R$M_NEW"].fillna(0).gt(0))

    out = C.RESULTS / "comparison_old_vs_new_v2.csv"
    cmp.sort_values(["window", "legis", "model", "iv_set"]).to_csv(out, sep=";", index=False)
    log.info("✓ saved %s (%d rows)", out, len(cmp))

    log.info("\n=== OLD vs NEW v2 (pp/R$1M) ===")
    log.info("\n%s", cmp.sort_values(["window","legis","model","iv_set"])
                          .to_string(index=False))


if __name__ == "__main__":
    main()
