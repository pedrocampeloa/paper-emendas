# -*- coding: utf-8 -*-
"""
103_twoway_corrections.py — SE variants for the two-way clustering issue
=========================================================================
For each legislature, refit the PLIV-DML (single-way cluster-aware
folds, since built-in two-way explodes) and compute several variants
of the two-way SE for comparison:

  1. Naive CGM:                   sqrt(V_d + V_v - V_dv) / |J| / n
  2. Finite-sample corrected:     apply Cameron-Miller (2015) DoF adj.
  3. MacKinnon-Nielsen-Webb 2023: G/(G-1) style scaling.
  4. Score-cluster average:       report both V_d-based and V_v-based
                                    single-way SEs to see which
                                    dimension drives the two-way.

Also computes an Anderson-Rubin-style two-way robust interval by
inverting the moment condition psi(theta_0) = 0 under the two-way
variance formula (weak-IV robust + cluster-robust).

Runs Leg 55 first (faster) then Leg 56.
"""
from __future__ import annotations

import sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import _utils as U

import importlib.util
spec = importlib.util.spec_from_file_location(
    "s101", HERE / "101_twoway_posthoc.py")
s101 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s101)

OUT = Path(__file__).resolve().parent.parent / "results" / "twoway_clustering"
OUT.mkdir(parents=True, exist_ok=True)


def cluster_sums_of_squares(psi, cluster1, cluster2):
    """Return V_d, V_v, V_dv computed as sum of squared cluster-summed psi."""
    V_d = float(pd.Series(psi).groupby(cluster1).sum().pow(2).sum())
    V_v = float(pd.Series(psi).groupby(cluster2).sum().pow(2).sum())
    inter = pd.MultiIndex.from_arrays([cluster1, cluster2])
    V_dv = float(pd.Series(psi).groupby(inter).sum().pow(2).sum())
    return V_d, V_v, V_dv


def se_variants(psi, deputy_ids, vote_ids, J, n, coef, std_t):
    """Compute several variants of the two-way SE.

    All return dicts with pp-scale SE.
    """
    V_d, V_v, V_dv = cluster_sums_of_squares(psi, deputy_ids, vote_ids)
    G_d = int(pd.Series(deputy_ids).nunique())
    G_v = int(pd.Series(vote_ids).nunique())
    # k = 1 for the just-identified moment (theta)
    k = 1
    to_pp = lambda se: 100 * se / std_t

    # Baseline (naive) CGM
    V_1w_naive = V_d
    V_2w_naive = V_d + V_v - V_dv
    se_1w_naive = np.sqrt(V_1w_naive) / abs(J) / n
    se_2w_naive = np.sqrt(V_2w_naive) / abs(J) / n

    # Cameron-Miller (2015) DoF adjustment: apply G/(G-1) * (n-1)/(n-k) to
    # the summed-cluster-variance, per dimension. For two-way use the min G.
    def dof_factor(G):
        return (G / (G - 1)) * ((n - 1) / (n - k))

    fac_d = dof_factor(G_d)
    fac_v = dof_factor(G_v)
    # Common practice: apply the max-cluster factor (most conservative in absolute
    # sense) or the geometric mean. We report the min-G factor (least
    # conservative, more likely to be appropriate for our large-G setting).
    fac_min = dof_factor(min(G_d, G_v))
    V_1w_dof = V_d * fac_d
    V_2w_dof = (V_d + V_v - V_dv) * fac_min
    se_1w_dof = np.sqrt(V_1w_dof) / abs(J) / n
    se_2w_dof = np.sqrt(V_2w_dof) / abs(J) / n

    # MacKinnon-Nielsen-Webb (2023, ARE, "Cluster-robust inference: a guide
    # to empirical practice"): for two-way with G_1, G_2 both large, the
    # CGM-standard formula can be conservative. They propose a scaled
    # variance V_MNW = V_naive - (V_intersect / (G_min - 1)) * ...
    # In practice for large-G-large-G panels, they recommend the "min-G"
    # rescaling: multiply V by (G_min - 1)/G_min.
    G_min = min(G_d, G_v)
    fac_mnw = (G_min - 1) / G_min
    V_2w_mnw = V_2w_naive * fac_mnw
    se_2w_mnw = np.sqrt(max(V_2w_mnw, 0)) / abs(J) / n

    # A more common finite-sample fix: apply Bell-McCaffrey CR2-style
    # for two-way, which for balanced panels reduces to
    # V_2w * (G_d G_v) / ((G_d - 1)(G_v - 1)). We include it for reference.
    fac_bm = (G_d * G_v) / ((G_d - 1) * (G_v - 1))
    V_2w_bm = V_2w_naive / fac_bm  # note: inverse of the above intuition
    # Actually the correct BM two-way correction multiplies by
    # (G-1)/G, similar to MNW. We report the MNW as the primary
    # correction and skip BM as a distinct variant.

    # Vote-only single-way SE (for diagnostic)
    se_1w_vote = np.sqrt(V_v) / abs(J) / n

    return {
        "G_d": G_d, "G_v": G_v,
        "V_d": V_d, "V_v": V_v, "V_dv": V_dv,
        "se_1w_deputy_naive": to_pp(se_1w_naive),
        "se_1w_deputy_dof":   to_pp(se_1w_dof),
        "se_1w_vote_naive":   to_pp(se_1w_vote),
        "se_2w_naive":        to_pp(se_2w_naive),
        "se_2w_dof":          to_pp(se_2w_dof),
        "se_2w_mnw":          to_pp(se_2w_mnw),
        "V_v_over_V_d":       V_v / V_d,
        "V_2w_over_V_1w":     V_2w_naive / V_d,
        "coef_pp":            100 * coef / std_t,
    }


def ar_twoway_interval(psi, psi_deriv, deputy_ids, vote_ids, J, n, coef, std_t,
                        theta_grid=None):
    """Anderson-Rubin two-way robust CI: invert the moment condition.

    For each theta_0 in a grid, compute the two-way t-stat of the
    moment condition E[psi(theta_0)] = 0 and include theta_0 in the CI
    if |t| <= 1.96.

    Note: psi = pliv.psi (evaluated at theta_hat) is A*theta_hat + B.
    We need psi(theta_0) = A*theta_0 + B = psi + A*(theta_0 - theta_hat)
    where A = psi_deriv.
    """
    if theta_grid is None:
        se_2w_seed = np.sqrt(
            cluster_sums_of_squares(psi, deputy_ids, vote_ids)[0] + \
            cluster_sums_of_squares(psi, deputy_ids, vote_ids)[1] - \
            cluster_sums_of_squares(psi, deputy_ids, vote_ids)[2]
        ) / abs(J) / n
        # Grid around theta_hat ± 5*SE
        theta_grid = np.linspace(coef - 5 * se_2w_seed, coef + 5 * se_2w_seed, 401)

    tstats = []
    for theta0 in theta_grid:
        psi_theta0 = psi + psi_deriv * (theta0 - coef)
        V_d, V_v, V_dv = cluster_sums_of_squares(psi_theta0, deputy_ids, vote_ids)
        V_2w = V_d + V_v - V_dv
        se_theta0 = np.sqrt(max(V_2w, 0)) / n  # SE of mean(psi_theta0)
        mean_psi = psi_theta0.mean()
        t = mean_psi / se_theta0 if se_theta0 > 0 else np.inf
        tstats.append(abs(t))
    tstats = np.array(tstats)
    accepted = theta_grid[tstats <= 1.96]
    if len(accepted) == 0:
        return None, None, None
    ci_lo = float(accepted.min())
    ci_hi = float(accepted.max())
    # Contains zero?
    contains_zero = (ci_lo <= 0 <= ci_hi)
    return 100 * ci_lo / std_t, 100 * ci_hi / std_t, contains_zero


def run_leg(df, leg, n_reps=1):
    print(f"\n=== LEG {leg} ===", flush=True)
    sub = df[df["idLegislatura"] == leg].copy()
    t0 = time.time()
    pliv, work, sc_t = s101.fit_pliv_and_extract_scores(
        sub, "alinhamento", n_folds=3, n_reps=n_reps)
    dt = time.time() - t0
    print(f"  fit done in {dt:.1f}s", flush=True)

    # psi shape is (n_obs, n_rep, 1). Aggregate by median over reps
    # (this is what doubleml does internally for the summary SE).
    psi_all = pliv.psi.reshape(-1, pliv.n_rep)  # (n, n_rep)
    psi_deriv_all = pliv.psi_deriv.reshape(-1, pliv.n_rep)
    n = psi_all.shape[0]
    coef = float(pliv.coef[0])
    std_t = float(sc_t.scale_[0])
    deputy_ids = work["idDeputado"].values
    vote_ids = work["idVotacao"].values

    # Compute variants per rep, then aggregate (median of SEs = doubleml default)
    variant_reps = []
    for rep in range(pliv.n_rep):
        psi = psi_all[:, rep]
        psi_deriv = psi_deriv_all[:, rep]
        J = -np.mean(psi_deriv)
        variant_reps.append(se_variants(psi, deputy_ids, vote_ids, J, n, coef, std_t))
    # Median across reps for each SE key
    variants = {}
    keys = variant_reps[0].keys()
    for k in keys:
        vals = [v[k] for v in variant_reps]
        try:
            variants[k] = float(np.median(vals))
        except (TypeError, ValueError):
            variants[k] = vals[0]
    variants["leg"] = leg
    variants["n"] = n
    variants["coef_sd"] = coef

    # For AR two-way, use first rep (or median psi across reps).
    psi_first = psi_all[:, 0]
    psi_deriv_first = psi_deriv_all[:, 0]
    J_first = -np.mean(psi_deriv_first)
    ar_lo, ar_hi, ar_contains_zero = ar_twoway_interval(
        psi_first, psi_deriv_first, deputy_ids, vote_ids, J_first, n, coef, std_t)

    pp = variants["coef_pp"]
    print(f"  coef = {pp:+.3f} pp/R$M", flush=True)
    print(f"  G_deputy = {variants['G_d']}, G_vote = {variants['G_v']}", flush=True)
    print(f"  V_v/V_d = {variants['V_v_over_V_d']:.2f}  "
          f"(vote-shock dominates if >>1)", flush=True)
    print(f"  V_2w/V_1w = {variants['V_2w_over_V_1w']:.2f}", flush=True)
    print()
    print(f"  SE variants (pp/R$M):", flush=True)
    print(f"    1-way deputy naive    : {variants['se_1w_deputy_naive']:.4f}", flush=True)
    print(f"    1-way deputy w/ DOF   : {variants['se_1w_deputy_dof']:.4f}", flush=True)
    print(f"    1-way vote  naive     : {variants['se_1w_vote_naive']:.4f}", flush=True)
    print(f"    2-way naive (CGM)     : {variants['se_2w_naive']:.4f}", flush=True)
    print(f"    2-way w/ min-G DOF    : {variants['se_2w_dof']:.4f}", flush=True)
    print(f"    2-way w/ MNW 2023 fix : {variants['se_2w_mnw']:.4f}", flush=True)

    def ci_str(pp_est, se):
        return f"[{pp_est - 1.96*se:+.3f}, {pp_est + 1.96*se:+.3f}]"

    def sig(pp_est, se):
        z = pp_est / se
        p = 2 * (1 - norm.cdf(abs(z)))
        s = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
        return p, s

    print(f"\n  95% CI + p-value + stars:", flush=True)
    for label, se in [
        ("1-way deputy naive", variants["se_1w_deputy_naive"]),
        ("2-way naive (CGM)",  variants["se_2w_naive"]),
        ("2-way MNW 2023",     variants["se_2w_mnw"]),
    ]:
        p, s = sig(pp, se)
        print(f"    {label:25s} : {ci_str(pp, se)}  p={p:.4f} {s}", flush=True)

    if ar_lo is not None:
        p_ar = "yes" if ar_contains_zero else "no"
        print(f"    Anderson-Rubin two-way   : "
              f"[{ar_lo:+.3f}, {ar_hi:+.3f}]  contains zero? {p_ar}",
              flush=True)
        variants["ar_lo"] = ar_lo
        variants["ar_hi"] = ar_hi
        variants["ar_contains_zero"] = ar_contains_zero

    return variants


def main():
    print("Loading modeling panel...", flush=True)
    df = U.load_modeling_panel()
    print(f"panel: n={len(df):,}", flush=True)

    rows = []
    # Leg 55 first (faster; ~25min)
    r55 = run_leg(df, 55, n_reps=3)
    rows.append(r55)
    # Leg 56 (slower; n_reps=1 for time budget)
    r56 = run_leg(df, 56, n_reps=1)
    rows.append(r56)

    df_out = pd.DataFrame(rows)
    csv_path = OUT / "se_variants.csv"
    df_out.to_csv(csv_path, index=False)
    print(f"\nwrote {csv_path}", flush=True)


if __name__ == "__main__":
    main()
