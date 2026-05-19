# -*- coding: utf-8 -*-
"""
07_subperiods_leg56.py — leg 56 PSL era vs Centrão era
======================================================
Test if the negative effect on leg 56 is uniform or driven by one sub-period.

PSL_era: 2019-01-01 to 2020-04-30 (Bolsonaro + PSL)
Centrao_era: 2020-05-01 to 2022-12-31 (after PSL break, Centrão takes over)

Output:
  results/subperiods_leg56.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--full", action="store_true",
                    help="use full ~191 controls (legacy spec)")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("07_subperiods_leg56")

    df = U.load_modeling_panel(window=C.MAIN_WINDOW, legis=(56,), log=log)
    df["data"] = pd.to_datetime(df["data"])

    rows = []
    if args.full:
        controls = C.get_full_controls(df)
        spec_label = "full"
    else:
        controls = [c for c in C.CONTROLS_REDUCED if c in df.columns]
        spec_label = "reduced"
    log.info("Using %d controls (%s spec)", len(controls), spec_label)

    periodos = [
        ("PSL_era_2019", df["data"] < "2020-05-01"),
        ("Centrao_era_2020p", df["data"] >= "2020-05-01"),
        ("PSL_era_strict_2019_only", (df["data"] >= "2019-01-01") & (df["data"] < "2020-01-01")),
        ("Bolsonaro_2020", (df["data"] >= "2020-01-01") & (df["data"] < "2021-01-01")),
        ("Bolsonaro_2021", (df["data"] >= "2021-01-01") & (df["data"] < "2022-01-01")),
        ("Bolsonaro_2022", (df["data"] >= "2022-01-01") & (df["data"] < "2023-01-01")),
    ]

    for label, mask in periodos:
        df_p = df[mask].copy()
        if len(df_p) < 1000:
            log.warning("  skip %s (n=%d)", label, len(df_p))
            continue
        local_controls = [c for c in controls if c in df_p.columns
                            and df_p[c].notna().mean() > 0.5
                            and df_p[c].nunique() > 1]
        log.info("--- %s | n=%d | controls=%d ---",
                 label, len(df_p), len(local_controls))

        # PLR
        try:
            t0 = time.time()
            res = U.run_plr(df_p, controls=local_controls,
                              n_folds=3, n_reps=args.reps)
            row = U.extract_row(res, {"period": label, "model": "PLR",
                                          "iv_set": "none", "spec": spec_label})
            if row:
                rows.append(row)
                log.info("  PLR (%ds): pp/R$M=%+.3f%s p=%.4f",
                         time.time() - t0, row["pp_per_unit"],
                         row["stars"], row["pval"])
        except Exception as e:
            log.error("  PLR failed: %s", e)

        # PLIV backlog
        try:
            t0 = time.time()
            avail = [z for z in C.IV_SETS["backlog"]
                       if z in df_p.columns and df_p[z].std() > 0]
            res = U.run_pliv(df_p, ivs=avail, controls=local_controls,
                                n_folds=3, n_reps=args.reps)
            row = U.extract_row(res, {"period": label, "model": "PLIV",
                                          "iv_set": "backlog", "spec": spec_label})
            if row:
                rows.append(row)
                log.info("  PLIV-backlog (%ds): pp/R$M=%+.3f%s p=%.4f",
                         time.time() - t0, row["pp_per_unit"],
                         row["stars"], row["pval"])
        except Exception as e:
            log.error("  PLIV-backlog failed: %s", e)

        # Descritivos
        Y = df_p[C.TARGET].mean()
        T = df_p[C.TREATMENT].mean()
        pol = df_p["pol_simple"].mean() if "pol_simple" in df_p.columns else None
        log.info("  Y_mean=%.3f T_mean(R$M)=%.2f pol_simple=%s",
                 Y, T, f"{pol:.3f}" if pol else "n/a")

    out = pd.DataFrame(rows)
    out_path = C.RESULTS / f"subperiods_leg56_{spec_label}.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out_path, len(out))
    log.info("\n%s", out[["period", "model", "iv_set", "pp_per_unit",
                            "stars", "n_obs"]].to_string(index=False))


if __name__ == "__main__":
    main()
