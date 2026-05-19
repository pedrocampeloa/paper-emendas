# -*- coding: utf-8 -*-
"""
08_tune_learners.py — Sensitivity to ML nuisance learners
==========================================================
TIER 2 item 9: rodar PLR e PLIV principais com 4 learners diferentes
para confirmar robustez. Resultado é uma tabela de sensibilidade publicável
e a decisão de qual learner usar no paper inteiro.

Learners testados:
  1. ElasticNetCV — atual (linear, penalizado, mistura L1+L2)
  2. LassoCV — linear, L1 puro (sparse)
  3. RandomForest — não-linear, robusto a outliers
  4. XGBoost — gradient boosting, state-of-the-art em alta-dimensão

Hyperparams testados (Fase A.2 + A.3):
  - n_folds: 3 (default DML), 5 (recomendado), 10 (gold standard mas caro)
  - alpha grid (apenas linear): atual logspace(-3,1,10) vs (-4,1,20)

Specs:
  - window=pre (MAIN, per Public Choice)
  - spec=full (~149 controls), spec=reduced (~29)
  - PLR + PLIV-backlog para cada (legs 55, 56, pooled)

Outputs:
  results/tune_learners.csv         — tabela completa de sensibilidade
  results/tune_learners_summary.csv — escolha do learner final

Usage:
  python 08_tune_learners.py --fast      # 20% sample for first screen
  python 08_tune_learners.py             # full sample (after fast screen)
  python 08_tune_learners.py --learner xgboost --full   # one learner only
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U


# ============================================================================
# Learner factory
# ============================================================================

def make_learners(name: str, random_state: int = 42, n_jobs: int = -1):
    """
    Return (ml_l, ml_m, ml_r) tuple of fresh learner instances.
    DML uses these for nuisance estimation:
      ml_l: E[Y|X], ml_m: E[T|X], ml_r: E[Z|X] (PLIV only)
    """
    from sklearn.linear_model import ElasticNetCV, LassoCV
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.base import clone

    if name == "elasticnet":
        kw = dict(
            l1_ratio=[0.1, 0.5, 1.0],
            alphas=np.logspace(-3, 1, 10),
            cv=3, max_iter=2000, random_state=random_state, n_jobs=n_jobs,
            precompute=False,  # avoid numerical instability of gram matrix
        )
        m = ElasticNetCV(**kw)

    elif name == "elasticnet_fine":
        # Finer grid for Fase A.3
        kw = dict(
            l1_ratio=[0.1, 0.3, 0.5, 0.7, 0.9, 1.0],
            alphas=np.logspace(-4, 1, 20),
            cv=3, max_iter=3000, random_state=random_state, n_jobs=n_jobs,
            precompute=False,
        )
        m = ElasticNetCV(**kw)

    elif name == "lasso":
        m = LassoCV(
            alphas=np.logspace(-4, 1, 20),
            cv=3, max_iter=3000, random_state=random_state, n_jobs=n_jobs,
            precompute=False,
        )

    elif name == "rf":
        m = RandomForestRegressor(
            n_estimators=200, max_depth=10, min_samples_leaf=20,
            random_state=random_state, n_jobs=n_jobs,
        )

    elif name == "xgboost":
        from xgboost import XGBRegressor
        m = XGBRegressor(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            random_state=random_state, n_jobs=n_jobs,
            tree_method="hist", verbosity=0,
        )

    elif name == "lightgbm":
        from lightgbm import LGBMRegressor
        m = LGBMRegressor(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            random_state=random_state, n_jobs=n_jobs, verbosity=-1,
        )

    else:
        raise ValueError(f"unknown learner: {name}")

    # Fresh clones for each nuisance
    return clone(m), clone(m), clone(m)


# ============================================================================
# Custom DML wrapper (uses generic learner)
# ============================================================================

def run_plr_with_learner(df, controls, learner_name,
                           outcome=C.TARGET, treatment=C.TREATMENT,
                           n_folds=3, n_reps=1):
    """PLR with arbitrary learner."""
    from doubleml import DoubleMLData, DoubleMLPLR
    from sklearn.preprocessing import StandardScaler
    cols = [outcome, treatment] + list(controls)
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    cols = cu
    work = df[cols].dropna().copy()
    if len(work) < 300:
        return None

    sc_t = StandardScaler(); sc_x = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[treatment]]),
                          columns=[treatment], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    df_dml = pd.concat([work[[outcome]], T_s, X_s], axis=1)
    data = DoubleMLData(df_dml, y_col=outcome, d_cols=treatment,
                          x_cols=list(controls))
    ml_l, ml_m, _ = make_learners(learner_name)
    plr = DoubleMLPLR(data, ml_l=ml_l, ml_m=ml_m,
                        n_folds=n_folds, n_rep=n_reps)
    plr.fit()
    res = plr.summary.copy()
    res["std_T"] = sc_t.scale_[0]
    res["n_obs"] = len(work)
    return res


def run_pliv_with_learner(df, ivs, controls, learner_name,
                            outcome=C.TARGET, treatment=C.TREATMENT,
                            n_folds=3, n_reps=1):
    """PLIV with arbitrary learner."""
    from doubleml import DoubleMLData, DoubleMLPLIV
    from sklearn.preprocessing import StandardScaler
    cols = [outcome, treatment] + list(controls) + list(ivs)
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    cols = cu
    work = df[cols].dropna().copy()
    if len(work) < 300:
        return None

    sc_t = StandardScaler(); sc_x = StandardScaler(); sc_z = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[treatment]]),
                          columns=[treatment], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    Z_s = pd.DataFrame(sc_z.fit_transform(work[ivs]),
                          columns=ivs, index=work.index)
    df_dml = pd.concat([work[[outcome]], T_s, X_s, Z_s], axis=1)
    data = DoubleMLData(df_dml, y_col=outcome, d_cols=treatment,
                          x_cols=list(controls), z_cols=list(ivs))
    ml_l, ml_m, ml_r = make_learners(learner_name)
    pliv = DoubleMLPLIV(data, ml_l=ml_l, ml_m=ml_m, ml_r=ml_r,
                          n_folds=n_folds, n_rep=n_reps)
    pliv.fit()
    res = pliv.summary.copy()
    res["std_T"] = sc_t.scale_[0]
    res["n_obs"] = len(work)
    return res


# ============================================================================
# Main loop
# ============================================================================

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--fast", action="store_true",
                    help="20%% sample (for first-screen tuning)")
    p.add_argument("--learners", default="elasticnet,lasso,rf,xgboost,lightgbm",
                    help="Comma-separated learners (default: all 5)")
    p.add_argument("--folds", default="3,5",
                    help="Comma-separated n_folds to test (default: 3,5)")
    p.add_argument("--specs", default="reduced,full",
                    help="reduced or full or both (default: both)")
    p.add_argument("--legs", default="all,55,56",
                    help="legs to run (default: all,55,56)")
    p.add_argument("--reps", type=int, default=1,
                    help="DML reps (default 1 for tuning)")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("08_tune")

    learners = [l.strip() for l in args.learners.split(",")]
    folds_list = [int(f) for f in args.folds.split(",")]
    specs_list = [s.strip() for s in args.specs.split(",")]
    legs_list = [s.strip() for s in args.legs.split(",")]

    log.info("Tuning grid: learners=%s folds=%s specs=%s legs=%s",
             learners, folds_list, specs_list, legs_list)

    log.info("Loading panel (window=pre)")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    if args.fast:
        log.info("FAST mode: 20%% sample")
        df = df.sample(frac=0.20, random_state=42)
    log.info("Final panel: %d rows × %d cols", len(df), df.shape[1])

    rows = []
    total_combos = (len(learners) * len(folds_list) * len(specs_list)
                      * len(legs_list))
    log.info("Total tuning combos: %d (× 2 for PLR+PLIV) = %d runs",
             total_combos, total_combos * 2)

    combo_idx = 0
    for learner_name in learners:
        for n_folds in folds_list:
            for spec in specs_list:
                # Pick controls
                if spec == "reduced":
                    controls_all = [c for c in C.CONTROLS_REDUCED
                                       if c in df.columns]
                else:
                    controls_all = C.get_full_controls(df)

                for leg_label in legs_list:
                    combo_idx += 1
                    df_l = (df.copy() if leg_label == "all"
                              else df[df["idLegislatura"] == int(leg_label)])
                    if len(df_l) < 1000:
                        continue
                    controls = [c for c in controls_all if c in df_l.columns
                                  and df_l[c].notna().mean() > 0.5
                                  and df_l[c].nunique() > 1]
                    log.info("[%d/%d] learner=%s folds=%d spec=%s leg=%s "
                              "n=%d controls=%d",
                              combo_idx, total_combos, learner_name,
                              n_folds, spec, leg_label, len(df_l),
                              len(controls))

                    label_base = {"learner": learner_name, "n_folds": n_folds,
                                    "spec": spec, "legis": leg_label,
                                    "n_controls": len(controls)}

                    # PLR
                    try:
                        t0 = time.time()
                        res = run_plr_with_learner(df_l, controls, learner_name,
                                                       n_folds=n_folds,
                                                       n_reps=args.reps)
                        row = U.extract_row(res,
                                                {**label_base, "model": "PLR",
                                                  "iv_set": "none",
                                                  "elapsed_s": int(time.time() - t0)})
                        if row:
                            rows.append(row)
                            log.info("  PLR (%ds): pp/R$M=%+.3f%s",
                                     int(time.time() - t0),
                                     row["pp_per_unit"], row["stars"])
                    except Exception as e:
                        log.error("  PLR %s failed: %s", learner_name, e)

                    # PLIV-backlog
                    try:
                        t0 = time.time()
                        avail = [z for z in C.IV_SETS["backlog"]
                                   if z in df_l.columns and df_l[z].std() > 0]
                        res = run_pliv_with_learner(df_l, avail, controls,
                                                        learner_name,
                                                        n_folds=n_folds,
                                                        n_reps=args.reps)
                        row = U.extract_row(res,
                                                {**label_base, "model": "PLIV",
                                                  "iv_set": "backlog",
                                                  "elapsed_s": int(time.time() - t0)})
                        if row:
                            rows.append(row)
                            log.info("  PLIV-backlog (%ds): pp/R$M=%+.3f%s",
                                     int(time.time() - t0),
                                     row["pp_per_unit"], row["stars"])
                    except Exception as e:
                        log.error("  PLIV-backlog %s failed: %s",
                                  learner_name, e)

    df_out = pd.DataFrame(rows)
    out_path = C.RESULTS / ("tune_learners_FAST.csv" if args.fast
                                else "tune_learners.csv")
    df_out.to_csv(out_path, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out_path, len(df_out))

    if len(df_out) == 0:
        log.error("All runs failed; nothing to summarize.")
        return 1

    # Summary: by (learner, spec, leg, model) → mean abs pp_per_unit, stability
    summary = df_out.groupby(["learner", "spec", "model", "iv_set", "legis"])[
        ["pp_per_unit", "pval"]].agg(["mean", "std", "count"]).round(4)
    log.info("\n=== SUMMARY (mean across folds) ===")
    log.info("\n%s", summary.to_string())
    return 0


if __name__ == "__main__":
    main()
