# -*- coding: utf-8 -*-
"""
13_deputy_fe.py — TIER 1.2 Deputy Fixed Effects
=================================================
Adiciona fixed effects de deputado para absorver propensão idiossincrática
de votar com o governo.

Por que importa:
  No diagnóstico anterior (TIER 1 escopo), o placebo `vote_sim` (votar Sim
  independente da orientação) deu coef +0.18*** quando deveria ser zero.
  Isso indica seleção: deputados tipo "Sim sempre" tendem a receber mais
  emenda mas não porque a emenda os causou — porque eles já são aliados.
  Deputy FE absorve essa propensão.

Implementação:
  Within-transformation antes do DML — cada (deputado, votação) tem
  Y_demeaned = Y - mean(Y | deputado)
  T_demeaned = T - mean(T | deputado)
  X_demeaned analogamente
  Aí roda DML normal sobre os demeaned.

Equivalente a one-hot encoding de idDeputado mas O(n) memória/CPU.

Output:
  results/tier1_deputy_fe.csv

Replicar 12_cluster_bootstrap mas com FE upstream.
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


def within_transform(df: pd.DataFrame, group_col: str,
                       cols_to_demean: list) -> pd.DataFrame:
    """
    Within-deputy demeaning. Subtract the deputy mean from each column.
    Equivalent to including deputy fixed effects.
    """
    df = df.copy()
    means = df.groupby(group_col)[cols_to_demean].transform("mean")
    df[cols_to_demean] = df[cols_to_demean] - means
    return df


def run_with_deputy_fe(df: pd.DataFrame, controls: list, ivs: list = None,
                          cluster_col: str = "idDeputado",
                          n_folds: int = 3, n_reps: int = 3):
    """
    DML PLR (or PLIV if ivs is not None) with deputy FE via within transform
    + cluster-robust SE.
    """
    from doubleml import DoubleMLClusterData, DoubleMLPLR, DoubleMLPLIV
    from sklearn.linear_model import ElasticNetCV
    from sklearn.preprocessing import StandardScaler

    # Build column lists with dedup
    iv_set = set(ivs) if ivs else set()
    controls = [c for c in controls
                  if c not in iv_set and c != C.TREATMENT and c != C.TARGET
                  and c != cluster_col]
    cols = [C.TARGET, C.TREATMENT] + list(controls)
    if ivs: cols += list(ivs)
    cols += [cluster_col]
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    cols = cu
    work = df[cols].dropna().copy()

    # Within-demean Y, T, X, and Z (FE absorbs deputy-level constants)
    cols_to_demean = [C.TARGET, C.TREATMENT] + list(controls)
    if ivs: cols_to_demean += list(ivs)
    work = within_transform(work, cluster_col, cols_to_demean)

    # Standardize
    sc_t = StandardScaler(); sc_x = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[C.TREATMENT]]),
                          columns=[C.TREATMENT], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    parts = [work[[C.TARGET]], T_s, X_s]
    if ivs:
        sc_z = StandardScaler()
        Z_s = pd.DataFrame(sc_z.fit_transform(work[ivs]),
                              columns=ivs, index=work.index)
        parts.append(Z_s)
    parts.append(work[[cluster_col]])
    df_dml = pd.concat(parts, axis=1)

    if ivs:
        data = DoubleMLClusterData(df_dml, y_col=C.TARGET, d_cols=C.TREATMENT,
                                       cluster_cols=cluster_col,
                                       x_cols=list(controls), z_cols=list(ivs))
    else:
        data = DoubleMLClusterData(df_dml, y_col=C.TARGET, d_cols=C.TREATMENT,
                                       cluster_cols=cluster_col,
                                       x_cols=list(controls))

    kw = dict(l1_ratio=[0.1, 0.5, 1.0], alphas=np.logspace(-3, 1, 10),
                cv=3, max_iter=2000, precompute=False)
    if ivs:
        m = DoubleMLPLIV(data,
                            ml_l=ElasticNetCV(**kw),
                            ml_m=ElasticNetCV(**kw),
                            ml_r=ElasticNetCV(**kw),
                            n_folds=n_folds, n_rep=n_reps)
    else:
        m = DoubleMLPLR(data,
                          ml_l=ElasticNetCV(**kw),
                          ml_m=ElasticNetCV(**kw),
                          n_folds=n_folds, n_rep=n_reps)
    m.fit()
    res = m.summary.copy()
    res["std_T"] = sc_t.scale_[0]
    res["n_obs"] = len(work)
    res["n_clusters"] = work[cluster_col].nunique()
    return res


def extract_row_fe(res, label):
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
        "pp_per_unit": round(100 * coef / std_t, 4),
        "ci95_lo_pp": round(100 * (coef - 1.96 * se) / std_t, 4),
        "ci95_hi_pp": round(100 * (coef + 1.96 * se) / std_t, 4),
        "pval": round(pval, 6),
        "stars": stars,
        "n_obs": n_obs,
        "n_clusters": n_clusters,
        "std_T": round(std_t, 6),
    }


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--specs", default="reduced",
                    help="reduced or full_clean")
    p.add_argument("--legs", default="all,55,56")
    p.add_argument("--placebo", action="store_true",
                    help="Run vote_sim placebo to verify FE absorbs it")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("13_deputy_fe")

    log.info("Loading panel (window=pre)")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    log.info("Final panel: %d rows | %d unique deputies",
             len(df), df["idDeputado"].nunique())

    specs_list = [s.strip() for s in args.specs.split(",")]
    legs_list = [s.strip() for s in args.legs.split(",")]

    rows = []
    for spec_name in specs_list:
        if spec_name == "reduced":
            ctrl = [c for c in C.CONTROLS_REDUCED if c in df.columns]
        else:
            ctrl = get_clean_full_controls(df)

        for leg_label in legs_list:
            df_l = df.copy() if leg_label == "all" else df[df["idLegislatura"] == int(leg_label)]
            if len(df_l) < 1000: continue
            local_ctrl = [c for c in ctrl if c in df_l.columns
                            and df_l[c].notna().mean() > 0.5
                            and df_l[c].nunique() > 1]
            log.info("\n--- spec=%s leg=%s n=%d controls=%d clusters=%d ---",
                     spec_name, leg_label, len(df_l), len(local_ctrl),
                     df_l["idDeputado"].nunique())

            # PLR with deputy FE
            try:
                t0 = time.time()
                res = run_with_deputy_fe(df_l, local_ctrl, ivs=None,
                                                n_folds=3, n_reps=args.reps)
                row = extract_row_fe(res, {"spec": spec_name, "legis": leg_label,
                                              "model": "PLR_deputyFE",
                                              "iv_set": "none"})
                if row:
                    rows.append(row)
                    log.info("  PLR+FE (%ds): pp/R$M=%+.3f%s CI=[%+.3f,%+.3f]",
                             int(time.time()-t0), row["pp_per_unit"], row["stars"],
                             row["ci95_lo_pp"], row["ci95_hi_pp"])
            except Exception as e:
                log.error("  PLR+FE failed: %s", e)

            # PLIV-backlog with deputy FE
            try:
                t0 = time.time()
                avail = [z for z in C.IV_SETS["backlog"]
                           if z in df_l.columns and df_l[z].std() > 0]
                res = run_with_deputy_fe(df_l, local_ctrl, ivs=avail,
                                                n_folds=3, n_reps=args.reps)
                row = extract_row_fe(res, {"spec": spec_name, "legis": leg_label,
                                              "model": "PLIV_deputyFE",
                                              "iv_set": "backlog"})
                if row:
                    rows.append(row)
                    log.info("  PLIV-bl+FE (%ds): pp/R$M=%+.3f%s CI=[%+.3f,%+.3f]",
                             int(time.time()-t0), row["pp_per_unit"], row["stars"],
                             row["ci95_lo_pp"], row["ci95_hi_pp"])
            except Exception as e:
                log.error("  PLIV-bl+FE failed: %s", e)

            # Vote_sim placebo with FE — should now go to zero
            if args.placebo and leg_label == "all":
                log.info("  [placebo] vote_sim with deputy FE")
                df_l2 = df_l.copy()
                df_l2["voto_sim"] = (df_l2["voto"].astype(str).str.lower() == "sim").astype(int)
                try:
                    df_pl = df_l2.rename(columns={"voto_sim": "_y_voto_sim"})
                    # Override TARGET temporarily
                    import _config as Ctmp
                    orig_target = Ctmp.TARGET
                    # We'll do PLR with custom outcome by passing voto_sim manually
                    # Easier: include voto_sim as both outcome
                    ctrl2 = [c for c in local_ctrl if c != "voto"]
                    cols = ["_y_voto_sim", C.TREATMENT] + ctrl2 + ["idDeputado"]
                    seen, cu = set(), []
                    for c in cols:
                        if c not in seen: cu.append(c); seen.add(c)
                    work = df_pl[cu].dropna().copy()
                    means = work.groupby("idDeputado")[
                        ["_y_voto_sim", C.TREATMENT] + ctrl2].transform("mean")
                    work[["_y_voto_sim", C.TREATMENT] + ctrl2] = (
                        work[["_y_voto_sim", C.TREATMENT] + ctrl2] - means
                    )
                    from sklearn.preprocessing import StandardScaler
                    from doubleml import DoubleMLClusterData, DoubleMLPLR
                    from sklearn.linear_model import ElasticNetCV
                    sc_t = StandardScaler(); sc_x = StandardScaler()
                    T_s = pd.DataFrame(sc_t.fit_transform(work[[C.TREATMENT]]),
                                          columns=[C.TREATMENT], index=work.index)
                    X_s = pd.DataFrame(sc_x.fit_transform(work[ctrl2]),
                                          columns=ctrl2, index=work.index)
                    df_dml = pd.concat([work[["_y_voto_sim"]], T_s, X_s,
                                          work[["idDeputado"]]], axis=1)
                    data = DoubleMLClusterData(df_dml, y_col="_y_voto_sim",
                                                   d_cols=C.TREATMENT,
                                                   cluster_cols="idDeputado",
                                                   x_cols=list(ctrl2))
                    kw = dict(l1_ratio=[0.1,0.5,1.0],
                                alphas=np.logspace(-3,1,10),
                                cv=3, max_iter=2000, precompute=False)
                    plr = DoubleMLPLR(data, ml_l=ElasticNetCV(**kw),
                                          ml_m=ElasticNetCV(**kw),
                                          n_folds=3, n_rep=args.reps)
                    plr.fit()
                    res2 = plr.summary.copy()
                    res2["std_T"] = sc_t.scale_[0]
                    res2["n_obs"] = len(work)
                    res2["n_clusters"] = work["idDeputado"].nunique()
                    row = extract_row_fe(res2, {"spec": spec_name, "legis": "all",
                                                    "model": "PLR_deputyFE_placebo_voteSim",
                                                    "iv_set": "none"})
                    if row:
                        rows.append(row)
                        log.info("    placebo (vote_sim) (FE): pp/R$M=%+.4f%s p=%.3f → should be ~0",
                                 row["pp_per_unit"], row["stars"], row["pval"])
                except Exception as e:
                    log.error("    placebo failed: %s", e)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "tier1_deputy_fe.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))
    log.info("\n%s", df_out[["spec","legis","model","iv_set","pp_per_unit",
                                  "ci95_lo_pp","ci95_hi_pp","pval","stars",
                                  "n_clusters"]].to_string(index=False))


if __name__ == "__main__":
    main()
