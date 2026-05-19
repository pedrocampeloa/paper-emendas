# -*- coding: utf-8 -*-
"""
04_counterfactual_price.py — Price of legislative support
==========================================================
Per Daniel's feedback (May 2026): the Public Choice paper should compute
the "price of legislative support" — the dollar cost per pp of alignment
gained — using the IV-corrected estimate.

Two related deliverables:

  1. Price per pp:
       price = R$1M / pp_per_R$M
     i.e., how many R$ buy 1 pp of alignment increase.

  2. Counterfactual: alignment if all emendas were zero
       Y_cf = Y_obs - θ × T̄
     reported per legislature.

Outputs:
  results/price_legislative_support.csv
  results/counterfactual_alignment.csv

NOTE on units: θ is in (probability per R$M) = (pp/100 per R$M). So:
  pp_per_R$M = 100 * θ
  R$M_per_pp  = 1 / pp_per_R$M  = 0.01 / θ
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--from-results", action="store_true",
                    help="Load coefficients from results/main_results.csv "
                         "instead of re-estimating")
    p.add_argument("--reps", type=int, default=C.N_REPS)
    return p.parse_args()


def estimate_or_load(args, df, controls, log) -> dict:
    """
    Get the PLIV-backlog coefficient per legislature. Either load from
    results/main_results.csv (faster) or re-estimate.
    """
    if args.from_results:
        path = C.RESULTS / "main_results.csv"
        if not path.exists():
            log.warning("main_results.csv not found; re-estimating")
        else:
            r = pd.read_csv(path, sep=";")
            sub = r[(r["model"] == "PLIV") & (r["iv_set"] == "backlog")
                       & (r["spec"] == "reduced")]
            return {row["legis"]: dict(row) for _, row in sub.iterrows()}

    # Re-estimate
    log.info("re-estimating PLIV-backlog per legislatura")
    out = {}
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else str(leg)
        df_l = df.copy() if leg is None else df[df["idLegislatura"] == leg]
        local_controls = [c for c in controls if c in df_l.columns
                            and df_l[c].notna().mean() > 0.5
                            and df_l[c].nunique() > 1]
        avail = [z for z in C.IV_SETS["backlog"]
                   if z in df_l.columns and df_l[z].std() > 0]
        res = U.run_pliv(df_l, ivs=avail, controls=local_controls,
                            n_reps=args.reps)
        row = U.extract_row(res, {"legis": leg_label})
        out[leg_label] = row
    return out


def compute_price_table(estimates: dict, df: pd.DataFrame) -> pd.DataFrame:
    """
    Price of support: R$M per pp of alignment.
      pp_per_RM = coef_per_unit * 100
      RM_per_pp = 1 / pp_per_RM
    """
    rows = []
    for leg_label, est in estimates.items():
        if est is None:
            continue
        # Take the normalised pp_per_unit
        pp_per_RM = float(est.get("pp_per_unit", 0.0))
        rm_per_pp = (1.0 / pp_per_RM) if pp_per_RM != 0 else float("inf")
        # Mean treatment in this leg
        if leg_label == "all":
            df_l = df
        else:
            df_l = df[df["idLegislatura"] == int(leg_label)]
        T_mean = float(df_l[C.TREATMENT].mean())
        Y_mean = float(df_l[C.TARGET].mean())

        rows.append({
            "legis": leg_label,
            "pp_per_R$M": round(pp_per_RM, 4),
            "R$M_per_pp": round(rm_per_pp, 4) if rm_per_pp != float("inf") else None,
            "R$_per_pp": (round(rm_per_pp * 1e6, 0)
                            if rm_per_pp != float("inf") else None),
            "se_per_unit": round(float(est.get("se_per_unit", 0)), 8),
            "pp_per_R$M_lo95": round(pp_per_RM - 1.96 * 100 * float(est.get("se_per_unit", 0)), 4),
            "pp_per_R$M_hi95": round(pp_per_RM + 1.96 * 100 * float(est.get("se_per_unit", 0)), 4),
            "stars": est.get("stars", ""),
            "n_obs": int(est.get("n_obs", 0)),
            "T_mean_R$M": round(T_mean, 3),
            "Y_mean": round(Y_mean, 4),
        })
    return pd.DataFrame(rows)


def compute_counterfactual_table(estimates: dict, df: pd.DataFrame) -> pd.DataFrame:
    """
    For each leg: Y_cf(T=0) = Y_obs - θ × T̄
    where θ is in pp/R$M (so use coef_per_unit, not pp_per_unit).
    """
    rows = []
    for leg_label, est in estimates.items():
        if est is None:
            continue
        if leg_label == "all":
            df_l = df
        else:
            df_l = df[df["idLegislatura"] == int(leg_label)]
        coef_per_unit = float(est.get("coef_per_unit", 0))
        T_mean = float(df_l[C.TREATMENT].mean())
        Y_obs = float(df_l[C.TARGET].mean())
        delta = coef_per_unit * T_mean   # in probability units
        Y_cf = Y_obs - delta

        rows.append({
            "legis": leg_label,
            "Y_observed_pct": round(100 * Y_obs, 2),
            "Y_counterfactual_pct": round(100 * Y_cf, 2),
            "delta_pp": round(100 * delta, 3),
            "%_of_Y_obs": round(100 * delta / Y_obs, 2) if Y_obs else None,
            "T_mean_R$M": round(T_mean, 3),
            "n_obs": int(est.get("n_obs", 0)),
        })
    return pd.DataFrame(rows)


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("04_counterfactual_price")

    df = U.load_modeling_panel(window=C.MAIN_WINDOW, legis=C.LEGISLATURAS,
                                  log=log)

    controls = [c for c in C.CONTROLS_REDUCED if c in df.columns]

    estimates = estimate_or_load(args, df, controls, log)

    price_df = compute_price_table(estimates, df)
    cf_df = compute_counterfactual_table(estimates, df)

    out_dir = C.RESULTS
    price_df.to_csv(out_dir / "price_legislative_support.csv",
                      sep=";", index=False)
    cf_df.to_csv(out_dir / "counterfactual_alignment.csv",
                   sep=";", index=False)

    log.info("\n=== PRICE OF LEGISLATIVE SUPPORT ===")
    log.info("\n%s", price_df.to_string(index=False))

    log.info("\n=== COUNTERFACTUAL Y(T=0) ===")
    log.info("\n%s", cf_df.to_string(index=False))


if __name__ == "__main__":
    main()
