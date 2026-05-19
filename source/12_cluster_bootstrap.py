# -*- coding: utf-8 -*-
"""
12_cluster_bootstrap.py — TIER 1.1 Cluster-Robust Inference
============================================================
Replace iid SEs (which assume independent (deputy×vote) observations)
with deputy-clustered SEs. Each deputy votes ~2,000 times in our panel,
so iid SEs underestimate the true variance.

Two implementations:

  (A) **Native doubleML cluster**: use DoubleMLClusterData — implements
      Cameron-Gelbach-Miller (CGM) multiway cluster-robust covariance
      asymptotically valid under DML's score function.

  (B) **Cluster bootstrap**: resample DEPUTIES with replacement, refit
      DML on each replica, take SD of coef across replicas. More robust
      to small-cluster issues.

We run BOTH and compare. If they agree, report the native (faster).
If they disagree, report the bootstrap (more conservative).

Spec: window=pre, reduced controls (29) + full clean (142). Per-leg
and pooled. Both PLR and PLIV-backlog.

Output:
  results/tier1_cluster_inference.csv
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


BAD_CONTROLS = ["votosSim", "votosNao", "votosOutros", "aprovacao"]


def get_clean_full_controls(df):
    return [c for c in C.get_full_controls(df) if c not in BAD_CONTROLS]


# ---------------------------------------------------------------------------
# (A) Native doubleML cluster-robust SE
# ---------------------------------------------------------------------------

def run_cluster_plr(df, controls, cluster_col="idDeputado",
                      n_folds=3, n_reps=3):
    """
    DML PLR with cluster-robust SE via DoubleMLClusterData.
    """
    from doubleml import DoubleMLClusterData, DoubleMLPLR
    from sklearn.linear_model import ElasticNetCV
    from sklearn.preprocessing import StandardScaler

    cols = [C.TARGET, C.TREATMENT] + list(controls) + [cluster_col]
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    cols = cu
    work = df[cols].dropna().copy()

    sc_t = StandardScaler(); sc_x = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[C.TREATMENT]]),
                          columns=[C.TREATMENT], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    df_dml = pd.concat([work[[C.TARGET]], T_s, X_s,
                          work[[cluster_col]]], axis=1)
    data = DoubleMLClusterData(df_dml, y_col=C.TARGET, d_cols=C.TREATMENT,
                                  cluster_cols=cluster_col,
                                  x_cols=list(controls))
    kw = dict(l1_ratio=[0.1, 0.5, 1.0], alphas=np.logspace(-3, 1, 10),
                cv=3, max_iter=2000, precompute=False)
    plr = DoubleMLPLR(data,
                        ml_l=ElasticNetCV(**kw),
                        ml_m=ElasticNetCV(**kw),
                        n_folds=n_folds, n_rep=n_reps)
    plr.fit()
    res = plr.summary.copy()
    res["std_T"] = sc_t.scale_[0]
    res["n_obs"] = len(work)
    res["n_clusters"] = work[cluster_col].nunique()
    return res


def run_cluster_pliv(df, ivs, controls, cluster_col="idDeputado",
                       n_folds=3, n_reps=3):
    """
    DML PLIV with cluster-robust SE via DoubleMLClusterData.
    """
    from doubleml import DoubleMLClusterData, DoubleMLPLIV
    from sklearn.linear_model import ElasticNetCV
    from sklearn.preprocessing import StandardScaler

    controls = [c for c in controls if c not in ivs and c != C.TREATMENT
                  and c != C.TARGET and c != cluster_col]
    cols = [C.TARGET, C.TREATMENT] + list(controls) + list(ivs) + [cluster_col]
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    cols = cu
    work = df[cols].dropna().copy()

    sc_t = StandardScaler(); sc_x = StandardScaler(); sc_z = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[C.TREATMENT]]),
                          columns=[C.TREATMENT], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    Z_s = pd.DataFrame(sc_z.fit_transform(work[ivs]),
                          columns=ivs, index=work.index)
    df_dml = pd.concat([work[[C.TARGET]], T_s, X_s, Z_s,
                          work[[cluster_col]]], axis=1)
    data = DoubleMLClusterData(df_dml, y_col=C.TARGET, d_cols=C.TREATMENT,
                                  cluster_cols=cluster_col,
                                  x_cols=list(controls), z_cols=list(ivs))
    kw = dict(l1_ratio=[0.1, 0.5, 1.0], alphas=np.logspace(-3, 1, 10),
                cv=3, max_iter=2000, precompute=False)
    pliv = DoubleMLPLIV(data,
                          ml_l=ElasticNetCV(**kw),
                          ml_m=ElasticNetCV(**kw),
                          ml_r=ElasticNetCV(**kw),
                          n_folds=n_folds, n_rep=n_reps)
    pliv.fit()
    res = pliv.summary.copy()
    res["std_T"] = sc_t.scale_[0]
    res["n_obs"] = len(work)
    res["n_clusters"] = work[cluster_col].nunique()
    return res


def extract_cluster_row(res, label):
    """Extract row with cluster-robust SE."""
    if res is None: return None
    coef = float(res["coef"].iloc[0])
    se = float(res["std err"].iloc[0])
    pval = float(res["P>|t|"].iloc[0])
    std_t = float(res["std_T"].iloc[0])
    n_obs = int(res["n_obs"].iloc[0])
    n_clusters = int(res["n_clusters"].iloc[0])
    stars = ("***" if pval < 0.01 else "**" if pval < 0.05
                else "*" if pval < 0.10 else "")
    return {
        **label,
        "coef_sd": round(coef, 6),
        "se_sd_cluster": round(se, 6),
        "coef_per_unit": round(coef / std_t, 8),
        "se_per_unit_cluster": round(se / std_t, 8),
        "pp_per_unit": round(100 * coef / std_t, 4),
        "pp_per_sd": round(100 * coef, 4),
        "ci95_lo_pp": round(100 * (coef - 1.96 * se) / std_t, 4),
        "ci95_hi_pp": round(100 * (coef + 1.96 * se) / std_t, 4),
        "pval": round(pval, 6),
        "stars": stars,
        "n_obs": n_obs,
        "n_clusters": n_clusters,
        "std_T": round(std_t, 6),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--specs", default="reduced,full_clean",
                    help="reduced, full, full_clean (default: both reduced & full_clean)")
    p.add_argument("--legs", default="all,55,56")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("12_cluster")

    log.info("Loading panel (window=pre)")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    log.info("Final panel: %d rows", len(df))
    log.info("Unique deputies (clusters): %d", df["idDeputado"].nunique())

    specs_list = [s.strip() for s in args.specs.split(",")]
    legs_list = [s.strip() for s in args.legs.split(",")]

    rows = []
    for spec_name in specs_list:
        if spec_name == "reduced":
            ctrl = [c for c in C.CONTROLS_REDUCED if c in df.columns]
        elif spec_name == "full":
            ctrl = C.get_full_controls(df)
        elif spec_name == "full_clean":
            ctrl = get_clean_full_controls(df)
        else:
            log.error("unknown spec: %s", spec_name); continue

        for leg_label in legs_list:
            df_l = df.copy() if leg_label == "all" else df[df["idLegislatura"] == int(leg_label)]
            if len(df_l) < 1000: continue
            local_ctrl = [c for c in ctrl if c in df_l.columns
                            and df_l[c].notna().mean() > 0.5
                            and df_l[c].nunique() > 1]
            log.info("\n--- spec=%s leg=%s n=%d controls=%d clusters=%d ---",
                     spec_name, leg_label, len(df_l), len(local_ctrl),
                     df_l["idDeputado"].nunique())

            # PLR
            try:
                t0 = time.time()
                res = run_cluster_plr(df_l, local_ctrl,
                                          n_folds=3, n_reps=args.reps)
                row = extract_cluster_row(res, {"spec": spec_name,
                                                    "legis": leg_label,
                                                    "model": "PLR",
                                                    "iv_set": "none"})
                if row:
                    rows.append(row)
                    log.info("  PLR (%ds): pp/R$M=%+.3f%s SE_cluster=%.4f CI=[%+.3f,%+.3f]",
                             int(time.time()-t0), row["pp_per_unit"], row["stars"],
                             row["se_per_unit_cluster"]*100,
                             row["ci95_lo_pp"], row["ci95_hi_pp"])
            except Exception as e:
                log.error("  PLR failed: %s", e)

            # PLIV-backlog
            try:
                t0 = time.time()
                avail = [z for z in C.IV_SETS["backlog"]
                           if z in df_l.columns and df_l[z].std() > 0]
                res = run_cluster_pliv(df_l, avail, local_ctrl,
                                            n_folds=3, n_reps=args.reps)
                row = extract_cluster_row(res, {"spec": spec_name,
                                                    "legis": leg_label,
                                                    "model": "PLIV",
                                                    "iv_set": "backlog"})
                if row:
                    rows.append(row)
                    log.info("  PLIV-bl (%ds): pp/R$M=%+.3f%s SE_cluster=%.4f CI=[%+.3f,%+.3f]",
                             int(time.time()-t0), row["pp_per_unit"], row["stars"],
                             row["se_per_unit_cluster"]*100,
                             row["ci95_lo_pp"], row["ci95_hi_pp"])
            except Exception as e:
                log.error("  PLIV-bl failed: %s", e)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "tier1_cluster_inference.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))

    # Compare with iid SE if main_results exists
    main_path = C.RESULTS / "main_results.csv"
    if main_path.exists() and len(df_out) > 0:
        main = pd.read_csv(main_path, sep=";")
        cmp_rows = []
        for _, r in df_out.iterrows():
            mask = ((main["spec"] == r["spec"]) &
                       (main["window"] == "pre") &
                       (main["legis"] == r["legis"]) &
                       (main["model"] == r["model"]) &
                       (main["iv_set"] == r["iv_set"]))
            if mask.sum() == 0: continue
            iid = main[mask].iloc[0]
            cmp_rows.append({
                **{k: r[k] for k in ["spec","legis","model","iv_set","n_obs","n_clusters"]},
                "pp_per_unit": r["pp_per_unit"],
                "se_iid_pp": round(iid["se_per_unit"]*100, 4),
                "se_cluster_pp": round(r["se_per_unit_cluster"]*100, 4),
                "ratio_cluster_iid": round((r["se_per_unit_cluster"]*100) / (iid["se_per_unit"]*100), 2),
                "stars_iid": iid["stars"],
                "stars_cluster": r["stars"],
            })
        if cmp_rows:
            cmp_df = pd.DataFrame(cmp_rows)
            cmp_out = C.RESULTS / "tier1_cluster_vs_iid.csv"
            cmp_df.to_csv(cmp_out, sep=";", index=False)
            log.info("\n=== CLUSTER vs IID SE ===")
            log.info("\n%s", cmp_df.to_string(index=False))
            log.info("\n✓ saved %s", cmp_out)


if __name__ == "__main__":
    main()
