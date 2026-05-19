# -*- coding: utf-8 -*-
"""
11_benchmark_plr.py — PLR (no IV) benchmark for each heterogeneity break
==========================================================================
For every subgroup analyzed in 10_fine_heterogeneity (PLIV-backlog),
run the corresponding PLR (no IV) for direct PLR vs PLIV comparison.

This serves as:
  1. Benchmark: how does naive OLS look in each subgroup?
  2. Bias diagnostic: difference (PLIV − PLR) per group reveals where
     the OLS bias is largest (i.e., where IV correction matters most).

Output:
  results/benchmark_plr_per_group.csv
  results/benchmark_bias_diagnostic.csv  — PLIV minus PLR per group

Strategy: re-use 10_fine_heterogeneity output (which already has both
PLR and PLIV per group). Just split, pivot, and compute bias.
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
    log = logging.getLogger("11_bench")

    src = C.RESULTS / "fine_heterogeneity.csv"
    if not src.exists():
        log.error("missing %s. Run 10_fine_heterogeneity.py first.", src)
        return 1

    df = pd.read_csv(src, sep=";")
    log.info("Loaded %d rows from fine_heterogeneity.csv", len(df))

    # Pivot: index=group, columns=model, values=pp_per_unit (and pval, stars, n_obs)
    plr = df[df["model"] == "PLR"].set_index("group")[
        ["pp_per_unit", "pval", "stars", "n_obs"]
    ].rename(columns={
        "pp_per_unit": "plr_pp",
        "pval": "plr_pval",
        "stars": "plr_stars",
        "n_obs": "plr_n",
    })
    pliv = df[df["model"] == "PLIV"].set_index("group")[
        ["pp_per_unit", "pval", "stars", "n_obs"]
    ].rename(columns={
        "pp_per_unit": "pliv_pp",
        "pval": "pliv_pval",
        "stars": "pliv_stars",
        "n_obs": "pliv_n",
    })

    bench = plr.join(pliv, how="outer")
    bench["bias_iv_minus_plr"] = (bench["pliv_pp"] - bench["plr_pp"]).round(4)
    bench["bias_pct_of_plr"] = (
        (bench["pliv_pp"] / bench["plr_pp"].replace(0, float("nan"))) - 1
    ).round(3) * 100
    bench["sign_change"] = (
        (bench["plr_pp"].fillna(0) > 0) != (bench["pliv_pp"].fillna(0) > 0)
    )
    bench = bench.reset_index().sort_values("group")

    out = C.RESULTS / "benchmark_plr_per_group.csv"
    bench.to_csv(out, sep=";", index=False)
    log.info("✓ saved %s (%d groups)", out, len(bench))

    # Diagnostic table
    log.info("\n=== TOP-15 GROUPS WITH LARGEST IV-vs-PLR DIFFERENCE ===")
    log.info("(positive bias = PLIV > PLR; OLS underestimates effect)")
    log.info("\n%s", bench.sort_values(
        "bias_iv_minus_plr", key=abs, ascending=False).head(15)[
        ["group", "plr_pp", "pliv_pp", "bias_iv_minus_plr",
         "sign_change", "plr_stars", "pliv_stars", "plr_n"]
    ].to_string(index=False))

    log.info("\n=== GROUPS WHERE IV REVERTS SIGN ===")
    rev = bench[bench["sign_change"]]
    log.info("\n%s", rev[
        ["group", "plr_pp", "pliv_pp", "plr_stars", "pliv_stars", "plr_n"]
    ].to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
