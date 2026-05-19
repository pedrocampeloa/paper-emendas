# -*- coding: utf-8 -*-
"""
03_decomposition.py — Decomposition of the leg 55 vs 56 gap (MUSTDO R2.7–R2.9)
================================================================================
Per Rafael's feedback: the gap between leg 55 (large effect) and leg 56
(small effect) is currently attributed entirely to the Secret Budget (RP-9).
He proposes opening it into 3 hypotheses:

  R2.7 RP-9 imputation (Secret Budget). If we had RP-9 data per deputy
       padrinho post-STF release, we could re-estimate
       Y = θ × (emenda + RP9_padrinho) + g(X). Predicted: θ in leg 56 rises,
       gap shrinks. STATUS: data not currently available; we run an UPPER
       BOUND scenario (assume RP-9 doubled emenda budget on average).
  R2.8 Polarization × emenda interaction. When coalition vs opposition
       are sharply divided, emenda buys less alignment. Build pol_v per vote
       (already done in b09), interact with emenda. Predicted: coef_int < 0.
  R2.9 Oaxaca-Blinder decomposition of the average effect difference.
       Decompose θ_56 - θ_55 = (X_56 - X_55)' β_55  +  X_56' (β_56 - β_55).
       Predicted: composition explains a relevant share of the gap.

Outputs:
  results/decomp_R2_7_rp9_scenario.csv
  results/decomp_R2_8_polarization_int.csv
  results/decomp_R2_9_oaxaca.csv
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


# ============================================================================
# R2.7 — RP-9 scenario analysis
# ============================================================================

def decomp_rp9_scenario(df: pd.DataFrame, controls: list,
                          log: logging.Logger, n_reps: int) -> pd.DataFrame:
    """
    Without RP-9 data, we simulate an upper bound: assume that during leg 56
    (2019–2022) the TRUE emenda flowing to each deputy was 2× the visible
    emenda (consistent with R$45B Secret Budget vs ~R$20B individual budget).

    Then re-estimate. If true effect is similar to leg 55, the implied θ_56
    should rise to roughly half its current level when emenda is doubled.

    NOTE: this is a SCENARIO, not a causal estimate. Real R2.7 awaits the
    STF post-2022 release of named RP-9 padrinho data.
    """
    log.info("\n=== R2.7 — RP-9 upper-bound scenario ===")
    rows = []

    for label, scale_56 in [("baseline", 1.0),
                                ("rp9_x2_leg56", 2.0),
                                ("rp9_x3_leg56", 3.0)]:
        df2 = df.copy()
        if scale_56 != 1.0:
            mask = df2["idLegislatura"] == 56
            df2.loc[mask, C.TREATMENT] *= scale_56

        for legis in (None, 55, 56):
            leg_label = "all" if legis is None else str(legis)
            df_l = df2 if legis is None else df2[df2["idLegislatura"] == legis]
            if len(df_l) < 1000:
                continue
            local_controls = [c for c in controls
                                if c in df_l.columns
                                and df_l[c].notna().mean() > 0.5
                                and df_l[c].nunique() > 1]
            try:
                t0 = time.time()
                avail = [z for z in C.IV_SETS["backlog"]
                           if z in df_l.columns and df_l[z].std() > 0]
                res = U.run_pliv(df_l, ivs=avail, controls=local_controls,
                                    n_reps=n_reps)
                row = U.extract_row(res, {"scenario": label,
                                              "legis": leg_label,
                                              "model": "PLIV_backlog"})
                if row:
                    rows.append(row)
                    log.info("  %s leg %s (%ds): pp_per_unit=%+.3f%s",
                             label, leg_label, time.time() - t0,
                             row["pp_per_unit"], row["stars"])
            except Exception as e:
                log.error("  %s leg %s failed: %s", label, leg_label, e)
    return pd.DataFrame(rows)


# ============================================================================
# R2.8 — Polarization × emenda interaction
# ============================================================================

def decomp_polarization(df: pd.DataFrame, controls: list,
                          log: logging.Logger, n_reps: int) -> pd.DataFrame:
    """
    For each polarization metric, build interaction term emenda × pol_v.
    Estimate via PLIV with both emenda and the interaction.

    DML standard recipe: include emenda × pol_v as an additional treatment;
    instrument with iv × pol_v. Implementation: simpler approach — split
    by pol_v terciles and report stratified PLIV-backlog. Negative effect
    of pol on |theta| → consistent with Rafael's hypothesis.
    """
    log.info("\n=== R2.8 — polarization × emenda ===")
    rows = []

    # Ensure pol_simple exists
    if "pol_simple" not in df.columns:
        log.warning("pol_simple not in panel; skipped")
        return pd.DataFrame()

    qs = df["pol_simple"].quantile([0.33, 0.67]).values
    df = df.copy()
    df["pol_tercil"] = "mid"
    df.loc[df["pol_simple"] <= qs[0], "pol_tercil"] = "low"
    df.loc[df["pol_simple"] >= qs[1], "pol_tercil"] = "high"

    log.info("  polarization terciles: %s",
             df["pol_tercil"].value_counts().to_dict())

    for tercil in ("low", "mid", "high"):
        df_t = df[df["pol_tercil"] == tercil]
        if len(df_t) < 1000:
            continue
        local_controls = [c for c in controls if c in df_t.columns
                            and df_t[c].notna().mean() > 0.5
                            and df_t[c].nunique() > 1]
        try:
            t0 = time.time()
            avail = [z for z in C.IV_SETS["backlog"]
                       if z in df_t.columns and df_t[z].std() > 0]
            res = U.run_pliv(df_t, ivs=avail, controls=local_controls,
                                n_reps=n_reps)
            row = U.extract_row(res, {"pol_tercil": tercil,
                                          "model": "PLIV_backlog"})
            if row:
                rows.append(row)
                log.info("  pol=%s (%ds): pp_per_unit=%+.3f%s n=%d",
                         tercil, time.time() - t0,
                         row["pp_per_unit"], row["stars"], row["n_obs"])
        except Exception as e:
            log.error("  pol=%s failed: %s", tercil, e)
    return pd.DataFrame(rows)


# ============================================================================
# R2.9 — Oaxaca-Blinder of the gap
# ============================================================================

def decomp_oaxaca(df: pd.DataFrame, controls: list,
                    log: logging.Logger) -> pd.DataFrame:
    """
    Oaxaca-Blinder: decompose mean(Y|leg=56) - mean(Y|leg=55) into
    composition + coefficient effects. Run separate OLS regressions of Y
    on emenda + controls in each leg, then decompose.

    Composition: (X_bar_56 - X_bar_55) @ beta_55
    Coefficient: X_bar_56 @ (beta_56 - beta_55)
    """
    import statsmodels.api as sm

    log.info("\n=== R2.9 — Oaxaca-Blinder gap decomposition ===")

    df_55 = df[df["idLegislatura"] == 55].copy()
    df_56 = df[df["idLegislatura"] == 56].copy()
    log.info("  leg 55: n=%d | mean Y=%.4f", len(df_55), df_55[C.TARGET].mean())
    log.info("  leg 56: n=%d | mean Y=%.4f", len(df_56), df_56[C.TARGET].mean())

    # Variables for decomposition
    cols = [C.TREATMENT] + [c for c in controls if c in df.columns
                              and df[c].notna().mean() > 0.5
                              and df[c].nunique() > 1]
    cols = [c for c in cols if c != C.TARGET]

    df_55c = df_55[cols + [C.TARGET]].dropna()
    df_56c = df_56[cols + [C.TARGET]].dropna()

    Y55 = df_55c[C.TARGET].values
    Y56 = df_56c[C.TARGET].values
    X55 = sm.add_constant(df_55c[cols].values)
    X56 = sm.add_constant(df_56c[cols].values)

    m55 = sm.OLS(Y55, X55).fit()
    m56 = sm.OLS(Y56, X56).fit()

    Xbar55 = X55.mean(axis=0)
    Xbar56 = X56.mean(axis=0)

    delta_total = float(Y56.mean() - Y55.mean())
    composition = float((Xbar56 - Xbar55) @ m55.params)
    coefficient = float(Xbar56 @ (m56.params - m55.params))

    rows = [
        {"component": "delta_total", "value": delta_total,
         "pp": 100 * delta_total},
        {"component": "composition", "value": composition,
         "pp": 100 * composition,
         "share": composition / delta_total if delta_total else np.nan},
        {"component": "coefficient", "value": coefficient,
         "pp": 100 * coefficient,
         "share": coefficient / delta_total if delta_total else np.nan},
    ]
    log.info("  Δ total: %.4f (%+.3f pp)", delta_total, 100 * delta_total)
    log.info("  composition: %.4f (%+.3f pp; %.1f%% of Δ)",
             composition, 100 * composition,
             100 * composition / delta_total if delta_total else float("nan"))
    log.info("  coefficient: %.4f (%+.3f pp; %.1f%% of Δ)",
             coefficient, 100 * coefficient,
             100 * coefficient / delta_total if delta_total else float("nan"))
    return pd.DataFrame(rows)


# ============================================================================
# Main
# ============================================================================

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--fast", action="store_true")
    p.add_argument("--reps", type=int, default=1)
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("03_decomposition")

    df = U.load_modeling_panel(window=C.MAIN_WINDOW, legis=C.LEGISLATURAS,
                                  log=log)
    if args.fast:
        df = df.sample(frac=0.20, random_state=42)

    controls = [c for c in C.CONTROLS_REDUCED if c in df.columns]

    out_dir = C.RESULTS

    # R2.7
    df_r7 = decomp_rp9_scenario(df, controls, log, args.reps)
    df_r7.to_csv(out_dir / "decomp_R2_7_rp9_scenario.csv",
                  sep=";", index=False)

    # R2.8
    df_r8 = decomp_polarization(df, controls, log, args.reps)
    df_r8.to_csv(out_dir / "decomp_R2_8_polarization_int.csv",
                  sep=";", index=False)

    # R2.9
    df_r9 = decomp_oaxaca(df, controls, log)
    df_r9.to_csv(out_dir / "decomp_R2_9_oaxaca.csv",
                  sep=";", index=False)

    log.info("✓ saved 3 decomposition files to %s", out_dir)


if __name__ == "__main__":
    main()
