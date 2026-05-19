# -*- coding: utf-8 -*-
"""
15_anderson_rubin.py — TIER 1.4 Anderson-Rubin Confidence Intervals
=====================================================================
AR confidence intervals are robust to weak instruments AND partial IV
violations. They invert the AR test:

  H0(beta_0):  Y - beta_0 * T  is uncorrelated with Z (conditional on X)

For each candidate beta_0, compute the AR statistic from a regression of
(Y - beta_0 * T) on X and Z, controlling for X. The AR-CI is the set of
beta_0 NOT rejected at level alpha.

This is computed analytically via the residualized form (Frisch-Waugh).

Why this matters:
  - DML-PLIV inference uses score-function asymptotics that can fail
    when IV is weak (low first-stage F) or when overid restrictions
    are violated (Sargan rejects).
  - AR CIs are valid even in those cases.
  - For our setting: leg 55 backlog has F=358 in full_clean (weakish);
    Sargan rejects almost always. AR is the safest inference tool.

Output:
  results/tier1_anderson_rubin.csv

Implementation:
  Use partialled-out (residualized) Y, T, Z by X via fast OLS.
  Then sweep beta_0 over a grid; compute Wald-type AR statistic.
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


BAD_CONTROLS = ["votosSim", "votosNao", "votosOutros", "aprovacao"]


def get_clean_full_controls(df):
    return [c for c in C.get_full_controls(df) if c not in BAD_CONTROLS]


def partial_out(M: np.ndarray, X: np.ndarray) -> np.ndarray:
    """
    Residualize M on X: returns M - X @ (X'X)^{-1} X' M.
    Numerically stable via lstsq.
    """
    if X.shape[1] == 0:
        return M
    # Add constant
    X_c = np.column_stack([np.ones(X.shape[0]), X])
    beta, *_ = np.linalg.lstsq(X_c, M, rcond=None)
    return M - X_c @ beta


def ar_test_stat(y_res: np.ndarray, t_res: np.ndarray, z_res: np.ndarray,
                   beta: float, cluster_ids: np.ndarray = None) -> float:
    """
    Compute AR statistic for H0: beta_T = beta.

    AR(beta) = N * (epsilon' Z) (Z'Z)^{-1} (Z' epsilon) / (epsilon'epsilon)
    where epsilon = y_res - beta * t_res.

    With clusters, use CGM cluster-robust (sum of cluster sums).
    Returns chi^2-distributed test statistic with q=#IVs DOF.
    """
    eps = y_res - beta * t_res
    n = len(eps)
    # Residualized Z'Z
    ZZ = z_res.T @ z_res
    # Z'eps
    if cluster_ids is not None:
        # Cluster-robust: V = sum over clusters of (Z_g' eps_g)(eps_g' Z_g)
        unique_clusters = np.unique(cluster_ids)
        V = np.zeros_like(ZZ)
        for g in unique_clusters:
            mask = cluster_ids == g
            zg = z_res[mask]
            eg = eps[mask]
            ze = zg.T @ eg
            V += np.outer(ze, ze)
        Z_eps_total = z_res.T @ eps
        try:
            V_inv = np.linalg.inv(V)
            ar = float(Z_eps_total @ V_inv @ Z_eps_total)
        except np.linalg.LinAlgError:
            return np.nan
    else:
        Z_eps = z_res.T @ eps
        try:
            sigma2 = (eps @ eps) / n
            ar = float(Z_eps @ np.linalg.inv(ZZ) @ Z_eps / sigma2)
        except np.linalg.LinAlgError:
            return np.nan
    return ar


def ar_ci(y_res: np.ndarray, t_res: np.ndarray, z_res: np.ndarray,
           cluster_ids: np.ndarray = None, alpha: float = 0.05,
           coef_grid: np.ndarray = None) -> tuple:
    """Invert AR test to get CI."""
    from scipy.stats import chi2
    q = z_res.shape[1]
    crit = chi2.ppf(1 - alpha, df=q)

    # Default grid: wide range around TSLS
    if coef_grid is None:
        # TSLS: beta = (T' P_Z T)^-1 T' P_Z Y where P_Z = Z (Z'Z)^-1 Z'
        ZZ_inv = np.linalg.pinv(z_res.T @ z_res)
        TZ = t_res.T @ z_res
        beta_tsls = float((TZ @ ZZ_inv @ z_res.T @ y_res)
                            / (TZ @ ZZ_inv @ z_res.T @ t_res))
        # Wide grid: ±20 abs(beta_tsls) plus ±0.5 if beta_tsls is small
        spread = max(20 * abs(beta_tsls), 0.5)
        coef_grid = np.linspace(beta_tsls - spread,
                                   beta_tsls + spread, 1000)

    ar_values = np.array([
        ar_test_stat(y_res, t_res, z_res, b, cluster_ids)
        for b in coef_grid
    ])
    not_rejected = (ar_values < crit) & np.isfinite(ar_values)
    if not not_rejected.any():
        return float("nan"), float("nan"), beta_tsls
    accepted = coef_grid[not_rejected]
    return float(accepted.min()), float(accepted.max()), beta_tsls


def run_ar(df: pd.DataFrame, controls: list, ivs: list,
             cluster_col: str = "idDeputado") -> dict:
    """Compute AR CI for the leg+spec subset."""
    # Build data
    ivs = [z for z in ivs if z != C.TREATMENT and z != C.TARGET]
    controls = [c for c in controls if c not in ivs and c != C.TREATMENT
                  and c != C.TARGET and c != cluster_col]
    cols = [C.TARGET, C.TREATMENT] + ivs + controls + [cluster_col]
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    work = df[cu].dropna().copy()

    Y = work[C.TARGET].values.astype(float)
    T = work[C.TREATMENT].values.astype(float)
    Z = work[ivs].values.astype(float)
    X = work[controls].values.astype(float) if controls else np.zeros((len(work), 0))
    cl = work[cluster_col].values

    # Standardize T (so coefs in pp are interpretable)
    T_std = T.std()
    T = (T - T.mean()) / T_std

    # Partial out X from Y, T, Z
    Y_res = partial_out(Y, X)
    T_res = partial_out(T, X)
    Z_res = partial_out(Z, X)

    lo, hi, beta_tsls = ar_ci(Y_res, T_res, Z_res, cluster_ids=cl, alpha=0.05)

    # Convert to pp/R$M units (T was scaled to unit variance):
    # beta_pp_per_RM = beta * 100 / std_T_orig
    return {
        "beta_tsls_sd": round(beta_tsls, 4),
        "ci_lo_sd": round(lo, 4),
        "ci_hi_sd": round(hi, 4),
        "pp_per_unit": round(beta_tsls * 100 / T_std, 4),
        "ar_ci_lo_pp": round(lo * 100 / T_std, 4),
        "ar_ci_hi_pp": round(hi * 100 / T_std, 4),
        "n_obs": len(work),
        "n_clusters": len(np.unique(cl)),
        "n_iv": len(ivs),
        "T_std": round(T_std, 4),
    }


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--specs", default="reduced,full_clean")
    p.add_argument("--legs", default="all,55,56")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("15_AR")

    log.info("Loading panel (window=pre)")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    log.info("Final panel: %d rows", len(df))

    specs_list = [s.strip() for s in args.specs.split(",")]
    legs_list = [s.strip() for s in args.legs.split(",")]

    rows = []
    for spec_name in specs_list:
        if spec_name == "reduced":
            ctrl_all = [c for c in C.CONTROLS_REDUCED if c in df.columns]
        else:
            ctrl_all = get_clean_full_controls(df)

        for leg_label in legs_list:
            df_l = df.copy() if leg_label == "all" else df[df["idLegislatura"] == int(leg_label)]
            if len(df_l) < 1000: continue
            local_ctrl = [c for c in ctrl_all if c in df_l.columns
                            and df_l[c].notna().mean() > 0.5
                            and df_l[c].nunique() > 1]
            log.info("--- spec=%s leg=%s n=%d ctrl=%d ---",
                     spec_name, leg_label, len(df_l), len(local_ctrl))

            avail = [z for z in C.IV_SETS["backlog"]
                       if z in df_l.columns and df_l[z].std() > 0]
            try:
                r = run_ar(df_l, local_ctrl, avail)
                r.update({"spec": spec_name, "legis": leg_label,
                            "iv_set": "backlog"})
                rows.append(r)
                log.info("  TSLS_pp=%+.3f  AR-CI=[%+.3f, %+.3f] pp/R$M",
                         r["pp_per_unit"], r["ar_ci_lo_pp"], r["ar_ci_hi_pp"])
            except Exception as e:
                log.error("  AR failed: %s", e)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "tier1_anderson_rubin.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s", out)
    log.info("\n%s", df_out.to_string(index=False))


if __name__ == "__main__":
    main()
