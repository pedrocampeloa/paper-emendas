# -*- coding: utf-8 -*-
"""
05_compare_old_new.py — Side-by-side comparison: new pipeline vs old paper
==========================================================================
Builds a single comparison table reporting old paper coefficients alongside
new pipeline results, for the eventual write-up that says "we re-estimated
with corrected pipeline; here's what changed".

Output:
  results/comparison_old_vs_new.csv

Note on units:
  Old `unified_results.csv` reports `coef_std` (effect of 1 SD T on
  P(Y=1)). For our R$M treatment, this is approximately
  pp_per_RSdM = 100 * coef_std. We need to translate to pp/R$1M:
       pp_per_R$M_old = 100 * coef_std / std_T_old
  The old CSV gives `theta` already as `coef_std / std_T` (effect per
  unit of T), so:
       pp_per_R$M_old = 100 * theta
  This is the column we compare with the new `pp_per_unit`.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("05_compare")

    # Old: paper antigo unified_results.csv
    old = pd.read_csv(C.LEGACY / "unified_results.csv", sep=";")
    # Map window: "left"=60d pre, "both"=±45d sym
    old = old[old["window"].isin(["left", "both"])].copy()
    old["pp_per_R$M_OLD"] = (100 * old["theta"]).round(4)
    old["window"] = old["window"].replace({"left": "pre", "both": "sym"})
    old_keep = old[["legis", "model", "iv_set", "window",
                     "pp_per_R$M_OLD", "pval", "stars", "n_obs"]] \
                  .rename(columns={"pval": "pval_OLD",
                                    "stars": "stars_OLD",
                                    "n_obs": "n_obs_OLD"})

    # New: main_results.csv
    new_path = C.RESULTS / "main_results.csv"
    if not new_path.exists():
        log.error("main_results.csv not found — run 01_run_dml.py first")
        return 1
    new = pd.read_csv(new_path, sep=";")
    # Filter reduced spec only (default; users can re-run with --legacy for full)
    new = new[new["spec"] == "reduced"].copy()
    new["window"] = "pre"  # we only ran pre window in 01
    new_keep = new[["legis", "model", "iv_set", "window",
                     "pp_per_unit", "pval", "stars", "n_obs"]] \
                  .rename(columns={"pp_per_unit": "pp_per_R$M_NEW",
                                    "pval": "pval_NEW",
                                    "stars": "stars_NEW",
                                    "n_obs": "n_obs_NEW"})

    # Outer merge on (legis, model, iv_set, window)
    cmp = old_keep.merge(new_keep,
                            on=["legis", "model", "iv_set", "window"],
                            how="outer", indicator=True)
    cmp["delta"] = cmp["pp_per_R$M_NEW"] - cmp["pp_per_R$M_OLD"]

    # Sign agreement
    cmp["sign_change"] = (cmp["pp_per_R$M_OLD"].fillna(0).gt(0)
                              != cmp["pp_per_R$M_NEW"].fillna(0).gt(0))
    cmp = cmp.sort_values(["window", "legis", "model", "iv_set"])

    # Save
    out = C.RESULTS / "comparison_old_vs_new.csv"
    cmp.to_csv(out, sep=";", index=False)
    log.info("✓ saved %s (%d rows)", out, len(cmp))

    # Print
    log.info("\n=== PP per R$1M: OLD vs NEW ===")
    log.info("\n%s", cmp.to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
