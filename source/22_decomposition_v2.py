# -*- coding: utf-8 -*-
"""
22_decomposition_v2.py — R2.7-R2.9 na spec definitiva
========================================================
R2.7: RP-9 imputado scenarios (×2, ×3 leg 56)
R2.8: Polarização × emenda (terciles)
R2.9: Oaxaca-Blinder (mantém analítico)

Todos com spec full_clean + Deputy FE + cluster-SE.

Output: results/decomposition_v2.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils_v2 as U2


def decomp_rp9_scenario(df, ctrl, log, n_reps=1):
    """R2.7 — RP-9 cenários: T_56 × {1, 2, 3}."""
    log.info("\n=== R2.7 — RP-9 scenarios ===")
    rows = []
    for label, scale in [("baseline", 1.0), ("rp9_x2", 2.0), ("rp9_x3", 3.0)]:
        df2 = df.copy()
        if scale != 1.0:
            mask = df2["idLegislatura"] == 56
            df2.loc[mask, C.TREATMENT] *= scale
        for leg in (55, 56, "all"):
            df_l = df2.copy() if leg == "all" else df2[df2["idLegislatura"] == leg]
            try:
                r = U2.run_pliv_main(df_l, controls=ctrl, n_reps=n_reps)
                if r:
                    r.update({"category": "R2.7_rp9",
                                "scenario": label, "legis": str(leg)})
                    rows.append(r)
                    log.info("  %s leg%s: pp/R$M=%+.3f%s",
                             label, leg, r["pp_per_unit"], r["stars"])
            except Exception as e:
                log.error("  failed %s leg%s: %s", label, leg, e)
    return rows


def decomp_polarization(df, ctrl, log, n_reps=1):
    """R2.8 — efeito por tercil de polarização."""
    log.info("\n=== R2.8 — polarização × emenda ===")
    rows = []
    if "pol_simple" not in df.columns:
        log.warning("pol_simple ausente"); return rows

    qs = df["pol_simple"].quantile([0.33, 0.67]).values
    df = df.copy()
    df["pol_tercil"] = "mid"
    df.loc[df["pol_simple"] <= qs[0], "pol_tercil"] = "low"
    df.loc[df["pol_simple"] >= qs[1], "pol_tercil"] = "high"

    for tercil in ("low", "mid", "high"):
        df_g = df[df["pol_tercil"] == tercil]
        try:
            r = U2.run_pliv_main(df_g, controls=ctrl, n_reps=n_reps)
            if r:
                r.update({"category": "R2.8_polarization",
                            "group": f"pol_{tercil}"})
                rows.append(r)
                log.info("  pol=%s: pp/R$M=%+.3f%s n=%d",
                         tercil, r["pp_per_unit"], r["stars"], r["n_obs"])
        except Exception as e:
            log.error("  pol=%s failed: %s", tercil, e)
    return rows


def decomp_oaxaca(df, ctrl, log):
    """R2.9 — Oaxaca-Blinder analítico."""
    log.info("\n=== R2.9 — Oaxaca-Blinder ===")
    df_55 = df[df["idLegislatura"] == 55]
    df_56 = df[df["idLegislatura"] == 56]
    cols = [C.TREATMENT] + [c for c in ctrl if c in df.columns
                                and df[c].notna().mean() > 0.5
                                and df[c].nunique() > 1]
    df_55c = df_55[cols + [C.TARGET]].dropna()
    df_56c = df_56[cols + [C.TARGET]].dropna()
    Y55 = df_55c[C.TARGET].values; Y56 = df_56c[C.TARGET].values
    X55 = sm.add_constant(df_55c[cols].values)
    X56 = sm.add_constant(df_56c[cols].values)
    m55 = sm.OLS(Y55, X55).fit()
    m56 = sm.OLS(Y56, X56).fit()
    Xb55 = X55.mean(axis=0); Xb56 = X56.mean(axis=0)
    delta = float(Y56.mean() - Y55.mean())
    composition = float((Xb56 - Xb55) @ m55.params)
    coefficient = float(Xb56 @ (m56.params - m55.params))
    return [
        {"category": "R2.9_oaxaca", "component": "delta_total",
          "value": delta, "pp": 100*delta},
        {"category": "R2.9_oaxaca", "component": "composition",
          "value": composition, "pp": 100*composition,
          "share_of_delta": composition/delta if delta else None},
        {"category": "R2.9_oaxaca", "component": "coefficient",
          "value": coefficient, "pp": 100*coefficient,
          "share_of_delta": coefficient/delta if delta else None},
    ]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=1)
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("22_decomp_v2")

    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["idLegislatura"] = df["idLegislatura"].astype(int)
    ctrl = U2.get_clean_full_controls(df)

    rows = []
    rows.extend(decomp_rp9_scenario(df, ctrl, log, args.reps))
    rows.extend(decomp_polarization(df, ctrl, log, args.reps))
    rows.extend(decomp_oaxaca(df, ctrl, log))

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "decomposition_v2.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))


if __name__ == "__main__":
    main()
