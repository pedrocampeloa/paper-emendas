# -*- coding: utf-8 -*-
"""
101_twoway_posthoc.py — Cajueiro comment #2/#3 (feasible version)
==================================================================
Runs the main PLIV-DML spec once with single-way (deputy) clustering,
extracts the orthogonalized score psi_a, psi_b for each observation,
and computes two-way Cameron--Gelbach--Miller (2011) cluster-robust
standard errors by direct summation of the score over deputies, votes,
and their intersection.

Rationale: DoubleML's built-in two-way path multiplies fold count as
n_folds^2, and at n_folds=3, n_reps=3 with ~226k obs and 142 covariates
the runtime is intractable (>10h for a single legislature). The
orthogonalized-score representation of Chernozhukov et al. (2018)
allows post-hoc SE recomputation without refitting the nuisance
functions, using the same score psi that DoubleML already exposes.

CGM two-way variance for a moment-based estimator with score
psi_i(theta) = a_i * theta + b_i satisfying sum_i psi_i(hat theta) = 0:

    V_CGM = V_d + V_v - V_dv
    V_d   = sum over deputy clusters d of (sum_{i in d} psi_i)^2
    V_v   = sum over vote clusters v of (sum_{i in v} psi_i)^2
    V_dv  = sum over (d,v) intersections of (sum_{i in (d,v)} psi_i)^2

    Var(hat theta) = (1/J^2) * V_CGM,  J = -sum_i psi_a_i

Reference: Cameron, Gelbach & Miller (2011); Chiang, Kato, Ma & Sasaki
(2022) apply the same construction to DML.

Outputs
-------
results/twoway_clustering/table1_twoway.csv
results/twoway_clustering/table1_twoway.md
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import _utils as U
import _config as C
import _utils_v2 as UV

warnings.filterwarnings("ignore")

OUT = Path(__file__).resolve().parent.parent / "results" / "twoway_clustering"
OUT.mkdir(parents=True, exist_ok=True)


def fit_pliv_and_extract_scores(df, target, cluster_col="idDeputado",
                                  n_folds=3, n_reps=3):
    """Fit the same PLIV-DML as _utils_v2.run_pliv_main and return
    the fitted model plus the working dataframe with cluster columns
    aligned to the score vector."""
    from doubleml import DoubleMLClusterData, DoubleMLPLIV
    from sklearn.linear_model import ElasticNetCV
    from sklearn.preprocessing import StandardScaler

    ivs = list(C.IV_SETS["backlog"])
    ivs = [z for z in ivs if z in df.columns and df[z].std() > 0]
    controls = UV.get_clean_full_controls(df)
    controls = [c for c in controls
                  if c not in (target, C.TREATMENT, "idDeputado", "idVotacao")
                  and c not in ivs]
    controls = [c for c in controls if c in df.columns
                  and df[c].notna().mean() > 0.5
                  and df[c].nunique() > 1]

    cols = [target, C.TREATMENT] + controls + ivs + ["idDeputado", "idVotacao"]
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    work = df[cu].dropna().copy()

    cols_dem = [target, C.TREATMENT] + controls + ivs
    work = UV.within_transform(work, "idDeputado", cols_dem)

    sc_t = StandardScaler(); sc_x = StandardScaler(); sc_z = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[C.TREATMENT]]),
                          columns=[C.TREATMENT], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    Z_s = pd.DataFrame(sc_z.fit_transform(work[ivs]),
                          columns=ivs, index=work.index)
    df_dml = pd.concat([work[[target]], T_s, X_s, Z_s,
                          work[["idDeputado"]]], axis=1)
    data = DoubleMLClusterData(df_dml, y_col=target, d_cols=C.TREATMENT,
                                  cluster_cols="idDeputado",
                                  x_cols=list(controls), z_cols=list(ivs))
    kw = dict(l1_ratio=[0.1, 0.5, 1.0], alphas=np.logspace(-3, 1, 10),
                cv=3, max_iter=2000, precompute=False)
    pliv = DoubleMLPLIV(data,
                          ml_l=ElasticNetCV(**kw),
                          ml_m=ElasticNetCV(**kw),
                          ml_r=ElasticNetCV(**kw),
                          n_folds=n_folds, n_rep=n_reps)
    pliv.fit()

    return pliv, work, sc_t


def cgm_twoway_se(psi_a, psi_b, deputy_ids, vote_ids):
    """Cameron-Gelbach-Miller (2011) two-way cluster-robust SE for a
    just-identified moment estimator, using the orthogonalized score.

    psi_i(theta_hat) = psi_a_i * theta_hat + psi_b_i,  sum_i psi_i = 0.
    Var(theta_hat) = (1/J^2) * V_CGM,  J = -mean(psi_a).
    """
    psi = psi_a * 0.0  # allocated as evaluated-score, filled by caller
    return None  # placeholder — replaced below with actual routine


def cgm_variance(psi, cluster1, cluster2):
    """CGM two-way variance = V1 + V2 - V12 of the summed score."""
    psi = np.asarray(psi).reshape(-1)
    c1 = pd.Series(cluster1).values
    c2 = pd.Series(cluster2).values

    def sumsq_by(cluster):
        s = pd.Series(psi).groupby(cluster).sum().values
        return np.sum(s ** 2)

    V1 = sumsq_by(c1)
    V2 = sumsq_by(c2)
    inter = pd.MultiIndex.from_arrays([c1, c2])
    s12 = pd.Series(psi).groupby(inter).sum().values
    V12 = np.sum(s12 ** 2)
    return V1 + V2 - V12, V1, V2, V12


def se_from_pliv(pliv, work, sc_t):
    """Return dict with 1-way (deputy) and 2-way (deputy x vote) SEs."""
    # DoubleML exposes evaluated score psi as (n, n_rep, 1) tensor.
    psi_a = pliv.psi_deriv.reshape(-1, pliv.n_rep)  # d psi / d theta
    psi_b = pliv.psi.reshape(-1, pliv.n_rep) - psi_a * pliv.coef  # psi_i - a_i*theta
    # But the standard score is psi_i(theta) = a_i * theta + b_i, and
    # DoubleML's `pliv.psi` is already evaluated at theta_hat, so:
    #   psi_evaluated = pliv.psi  (n, n_rep, n_coefs) => sum_i = 0.
    psi = pliv.psi.reshape(-1, pliv.n_rep)  # shape (n, n_rep)
    # For each rep, compute CGM variance; then average across reps.
    n_obs = psi.shape[0]
    J_hat = -np.mean(pliv.psi_deriv.reshape(-1, pliv.n_rep), axis=0)  # (n_rep,)

    deputy_ids = work["idDeputado"].values
    vote_ids = work["idVotacao"].values

    ses = {"1way": [], "2way": []}
    for rep in range(pliv.n_rep):
        psi_rep = psi[:, rep]
        # 1-way (deputy)
        V1way, _, _, _ = cgm_variance(psi_rep, deputy_ids, deputy_ids)
        # V1way = V_d + V_d - V_d = V_d
        # Above formula collapses; compute directly:
        V_d = float(pd.Series(psi_rep).groupby(deputy_ids).sum().pow(2).sum())
        V_v = float(pd.Series(psi_rep).groupby(vote_ids).sum().pow(2).sum())
        inter = pd.MultiIndex.from_arrays([deputy_ids, vote_ids])
        V_dv = float(pd.Series(psi_rep).groupby(inter).sum().pow(2).sum())

        V_cgm_1way = V_d
        V_cgm_2way = V_d + V_v - V_dv

        # SE for theta = sqrt(V) / |J| / n  (DoubleML normalizes psi so
        # that sum psi = 0 in expectation; the variance of theta_hat is
        # V_cgm / (J^2 * n^2) if we don't average, or V_cgm / (J^2 * n^2)
        # if we do — the standard CGM form is V / J^2 with psi summed.)
        # Following Chiang-Kato-Ma-Sasaki (2022) eq (2.6): sigma^2 = V / J^2.
        se_1w = np.sqrt(V_cgm_1way) / abs(J_hat[rep]) / n_obs
        se_2w = np.sqrt(V_cgm_2way) / abs(J_hat[rep]) / n_obs
        ses["1way"].append(se_1w)
        ses["2way"].append(se_2w)

    # Aggregate across reps as sqrt(mean(se^2) + Var(theta_hat_r))
    # For simplicity report the mean SE (DoubleML default is median).
    se_1way = float(np.median(ses["1way"]))
    se_2way = float(np.median(ses["2way"]))
    return {
        "se_sd_1way": se_1way,
        "se_sd_2way": se_2way,
        "se_ratio_2w_1w": se_2way / se_1way if se_1way > 0 else float("nan"),
        "V_d": V_d, "V_v": V_v, "V_dv": V_dv,
        "n_deputies": pd.Series(deputy_ids).nunique(),
        "n_votes": pd.Series(vote_ids).nunique(),
        "n_obs": n_obs,
    }


def run_one(df, outcome, leg):
    print(f"\n=== outcome={outcome} | leg={leg} ===", flush=True)
    sub = df[df["idLegislatura"] == leg].copy()
    target = outcome if outcome != "gov" else "alinhamento"
    if target not in sub.columns:
        print(f"  target {target} not in panel, skipping")
        return None
    t0 = time.time()
    pliv, work, sc_t = fit_pliv_and_extract_scores(sub, target)
    dt_fit = time.time() - t0
    print(f"  PLIV fit done in {dt_fit:.1f}s", flush=True)
    coef = float(pliv.coef[0])
    std_t = float(sc_t.scale_[0])
    ses = se_from_pliv(pliv, work, sc_t)
    pp = 100 * coef / std_t
    ci_lo_1w = 100 * (coef - 1.96 * ses["se_sd_1way"]) / std_t
    ci_hi_1w = 100 * (coef + 1.96 * ses["se_sd_1way"]) / std_t
    ci_lo_2w = 100 * (coef - 1.96 * ses["se_sd_2way"]) / std_t
    ci_hi_2w = 100 * (coef + 1.96 * ses["se_sd_2way"]) / std_t
    z_1w = coef / ses["se_sd_1way"]
    z_2w = coef / ses["se_sd_2way"]
    from scipy.stats import norm
    pval_1w = 2 * (1 - norm.cdf(abs(z_1w)))
    pval_2w = 2 * (1 - norm.cdf(abs(z_2w)))
    stars = lambda p: ("***" if p < 0.01 else "**" if p < 0.05
                       else "*" if p < 0.10 else "")
    print(f"  1-way : pp={pp:+.3f} SE={ses['se_sd_1way']:.4f} "
          f"CI=[{ci_lo_1w:+.3f}, {ci_hi_1w:+.3f}] p={pval_1w:.4f} {stars(pval_1w)}", flush=True)
    print(f"  2-way : pp={pp:+.3f} SE={ses['se_sd_2way']:.4f} "
          f"CI=[{ci_lo_2w:+.3f}, {ci_hi_2w:+.3f}] p={pval_2w:.4f} {stars(pval_2w)}", flush=True)
    print(f"  SE ratio 2w/1w = {ses['se_ratio_2w_1w']:.3f}", flush=True)
    return {
        "outcome": outcome, "leg": leg,
        "coef_sd": coef, "pp_per_unit": pp,
        "se_1way": ses["se_sd_1way"], "se_2way": ses["se_sd_2way"],
        "se_ratio": ses["se_ratio_2w_1w"],
        "ci95_1way_lo": ci_lo_1w, "ci95_1way_hi": ci_hi_1w,
        "ci95_2way_lo": ci_lo_2w, "ci95_2way_hi": ci_hi_2w,
        "pval_1way": pval_1w, "pval_2way": pval_2w,
        "stars_1way": stars(pval_1w), "stars_2way": stars(pval_2w),
        "n_obs": ses["n_obs"],
        "n_deputies": ses["n_deputies"], "n_votes": ses["n_votes"],
        "V_d": ses["V_d"], "V_v": ses["V_v"], "V_dv": ses["V_dv"],
    }


def main():
    print("Loading modeling panel...", flush=True)
    df = U.load_modeling_panel()
    print(f"panel: n={len(df):,}, deputies={df['idDeputado'].nunique()}, "
          f"votes={df['idVotacao'].nunique()}", flush=True)

    rows = []
    for leg in (55, 56):
        r = run_one(df, "gov", leg)
        if r: rows.append(r)

    tab = pd.DataFrame(rows)
    csv_path = OUT / "table1_twoway.csv"
    tab.to_csv(csv_path, index=False)
    print(f"\nwrote {csv_path}", flush=True)

    lines = ["# Table 1 under two-way clustering (post-hoc CGM)", "",
             "Coefficient re-uses the PLIV-DML fit with single-way (deputy) "
             "cluster-aware cross-fitting; only the standard error is "
             "recomputed under Cameron--Gelbach--Miller two-way clustering "
             "(deputy and roll-call) via the orthogonalized score. See "
             "Chiang, Kato, Ma & Sasaki (2022, JBES) for the equivalence.", "",
             "| Outcome | Leg | Coef (pp/R$M) | SE 1-way | 95% CI 1-way | "
             "SE 2-way | 95% CI 2-way | p 1-way | p 2-way | Ratio 2w/1w |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in tab.iterrows():
        lines.append(
            f"| {r['outcome']} | {r['leg']} | {r['pp_per_unit']:+.3f} | "
            f"{r['se_1way']:.4f} | [{r['ci95_1way_lo']:+.3f}, {r['ci95_1way_hi']:+.3f}] {r['stars_1way']} | "
            f"{r['se_2way']:.4f} | [{r['ci95_2way_lo']:+.3f}, {r['ci95_2way_hi']:+.3f}] {r['stars_2way']} | "
            f"{r['pval_1way']:.4f} | {r['pval_2way']:.4f} | "
            f"{r['se_ratio']:.3f} |"
        )
    md_path = OUT / "table1_twoway.md"
    md_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {md_path}", flush=True)


if __name__ == "__main__":
    main()
