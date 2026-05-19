# -*- coding: utf-8 -*-
"""
06_reverse_allocation.py — How does the government ALLOCATE emendas?
=====================================================================
MUSTDO R2.6: regress emenda value on (deputy characteristics) instead of
the other way around. Goal: tell whether the government targets emendas
at coalition deputies (loyalty reinforcement) or at opposition deputies
(co-optation).

Specs:
  emenda_M ~ d_oposicao + d_independente + ...     (per leg + pooled)
  emenda_M ~ align_hist_low + align_hist_high + ...
  emenda_M ~ d_oposicao × d_elec_federal           (interactions)

Estimator: OLS with HC1 robust SEs (no need for DML — purely descriptive).

Outputs:
  results/reverse_allocation.csv
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U


def add_align_hist(df: pd.DataFrame, log) -> pd.DataFrame:
    log.info("computing align_hist_pre")
    df = df.sort_values(["idDeputado", "data"]).reset_index(drop=True)
    df["align_hist_pre"] = (
        df.groupby("idDeputado")["alinhamento"]
            .transform(lambda x: x.shift(1).rolling(window=20, min_periods=5).mean())
    )
    df["align_hist_pre"] = df["align_hist_pre"].fillna(df["alinhamento"].mean())
    qs = df["align_hist_pre"].quantile([0.33, 0.67]).values
    df["d_align_low"] = (df["align_hist_pre"] <= qs[0]).astype(int)
    df["d_align_high"] = (df["align_hist_pre"] >= qs[1]).astype(int)
    return df


def ols_summary(model, name: str) -> pd.DataFrame:
    """Extract regressors of interest into a tidy frame."""
    keep = [c for c in model.params.index
              if any(k in c for k in ["oposicao", "coalizao", "independente",
                                            "align", "elec", "Intercept"])]
    rows = []
    for k in keep:
        rows.append({
            "spec": name,
            "regressor": k,
            "coef_R$M": round(model.params[k], 4),
            "se_R$M": round(model.bse[k], 4),
            "t": round(model.tvalues[k], 2),
            "pval": round(model.pvalues[k], 4),
            "stars": ("***" if model.pvalues[k] < 0.01
                          else "**" if model.pvalues[k] < 0.05
                          else "*" if model.pvalues[k] < 0.1 else ""),
        })
    return pd.DataFrame(rows)


def run_one_leg(df: pd.DataFrame, label: str, log) -> pd.DataFrame:
    df = df.copy()
    if len(df) < 1000:
        log.warning("  skip %s (n=%d)", label, len(df))
        return pd.DataFrame()

    out = []

    # Spec 1: emenda ~ status partidário
    Y = df[C.TREATMENT].values
    X1 = df[["d_oposicao", "d_independente"]]  # coalizão é base
    X1 = sm.add_constant(X1)
    m1 = sm.OLS(Y, X1).fit(cov_type="HC1")
    log.info("  [%s spec1] emenda ~ partidário: R² = %.3f", label, m1.rsquared)
    log.info("    d_oposicao = %+.3f (R$M)  vs coalizão (base)", m1.params.get("d_oposicao", 0))
    log.info("    d_independente = %+.3f (R$M)", m1.params.get("d_independente", 0))
    out.append(ols_summary(m1, f"{label}_status_partidario"))

    # Spec 2: emenda ~ histórico de alinhamento
    df_h = add_align_hist(df, log)
    Y = df_h[C.TREATMENT].values
    X2 = df_h[["d_align_low", "d_align_high"]]  # mid é base
    X2 = sm.add_constant(X2)
    m2 = sm.OLS(Y, X2).fit(cov_type="HC1")
    log.info("  [%s spec2] emenda ~ alinhamento histórico: R² = %.3f",
             label, m2.rsquared)
    log.info("    d_align_low = %+.3f", m2.params.get("d_align_low", 0))
    log.info("    d_align_high = %+.3f", m2.params.get("d_align_high", 0))
    out.append(ols_summary(m2, f"{label}_align_hist"))

    # Spec 3: combo + election
    X3 = df[["d_oposicao", "d_independente",
              "d_elec_federal", "d_elec_municipal"]]
    X3 = sm.add_constant(X3)
    m3 = sm.OLS(Y[:len(X3)], X3).fit(cov_type="HC1")
    log.info("  [%s spec3] full: R² = %.3f", label, m3.rsquared)
    out.append(ols_summary(m3, f"{label}_combo"))

    return pd.concat(out, ignore_index=True)


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("06_reverse_allocation")

    df = U.load_modeling_panel(window=C.MAIN_WINDOW, legis=C.LEGISLATURAS,
                                  log=log)
    log.info("Final panel: %d rows", len(df))

    out_all = []
    for leg, label in [(None, "pooled"), (55, "leg55"), (56, "leg56")]:
        log.info("\n=== %s ===", label)
        df_l = df.copy() if leg is None else df[df["idLegislatura"] == leg].copy()
        out_all.append(run_one_leg(df_l, label, log))

    final = pd.concat(out_all, ignore_index=True)

    # Mean emenda by group (descriptive)
    desc = []
    for leg, label in [(None, "pooled"), (55, "leg55"), (56, "leg56")]:
        df_l = df.copy() if leg is None else df[df["idLegislatura"] == leg].copy()
        for grp_col, grp_label in [("d_oposicao", "oposicao"),
                                       ("d_coalizao", "coalizao"),
                                       ("d_independente", "independente"),
                                       ("d_elec_federal", "elec_federal"),
                                       ("d_elec_municipal", "elec_municipal")]:
            mask = df_l[grp_col] == 1
            if mask.sum() < 100:
                continue
            desc.append({
                "leg": label,
                "group": grp_label,
                "n": int(mask.sum()),
                "mean_emenda_R$M": round(df_l.loc[mask, C.TREATMENT].mean(), 3),
                "median_emenda_R$M": round(df_l.loc[mask, C.TREATMENT].median(), 3),
                "%_zero": round(100 * (df_l.loc[mask, C.TREATMENT] == 0).mean(), 1),
            })
    desc_df = pd.DataFrame(desc)

    final.to_csv(C.RESULTS / "reverse_allocation.csv", sep=";", index=False)
    desc_df.to_csv(C.RESULTS / "reverse_allocation_descriptive.csv",
                     sep=";", index=False)

    log.info("\n=== DESCRIPTIVE: mean emenda by group ===")
    log.info("\n%s", desc_df.to_string(index=False))

    log.info("\n=== REGRESSION: emenda ~ characteristics ===")
    log.info("\n%s", final.to_string(index=False))


if __name__ == "__main__":
    main()
