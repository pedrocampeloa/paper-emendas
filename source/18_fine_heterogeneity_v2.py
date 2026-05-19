# -*- coding: utf-8 -*-
"""
18_fine_heterogeneity_v2.py — Heterogeneidade fina na NOVA especificação principal
====================================================================================
Re-roda heterogeneidade por sub-grupo usando a spec defensável:
  - window=pre (60d antes do voto)
  - controls=full_clean (~142, sem bad controls)
  - Deputy fixed effects (within-transformation)
  - Cluster-robust SE por idDeputado (CGM)

Sub-grupos analisados (USER1 — onde negativo, onde positivo):
  - Status partidário × leg
  - Ano eleitoral × leg
  - Tipo de proposta × leg
  - Ano calendário
  - Orientação do governo × leg
  - Tercis de tratamento × leg
  - Coalizão × ano eleitoral × leg (interação tripla)

Output: results/fine_heterogeneity_v2.csv
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


def within_transform(df, group_col, cols_to_demean):
    df = df.copy()
    means = df.groupby(group_col)[cols_to_demean].transform("mean")
    df[cols_to_demean] = df[cols_to_demean] - means
    return df


def run_subgroup_v2(df_g, controls, ivs, label, log,
                       cluster_col="idDeputado", n_folds=3, n_reps=1):
    """
    PLR + PLIV-backlog em sub-grupo, com FE within-deputy + cluster-SE.
    """
    if len(df_g) < 2000 or df_g[cluster_col].nunique() < 30:
        log.warning("    skip %s (n=%d clusters=%d)", label,
                       len(df_g), df_g[cluster_col].nunique())
        return []
    local_ctrl = [c for c in controls if c in df_g.columns
                    and df_g[c].notna().mean() > 0.5
                    and df_g[c].nunique() > 1]
    avail_iv = [z for z in ivs if z in df_g.columns and df_g[z].std() > 0]

    rows = []

    # PLR with FE
    try:
        t0 = time.time()
        cols_dem = [C.TARGET, C.TREATMENT] + list(local_ctrl)
        seen, cu = set(), []
        for c in cols_dem + [cluster_col]:
            if c not in seen: cu.append(c); seen.add(c)
        work = df_g[cu].dropna().copy()
        if len(work) < 1000:
            log.warning("    skip after dropna %s (n=%d)", label, len(work))
            return rows
        work_dem = within_transform(work, cluster_col, cols_dem)
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import ElasticNetCV
        from doubleml import DoubleMLClusterData, DoubleMLPLR, DoubleMLPLIV
        sc_t = StandardScaler(); sc_x = StandardScaler()
        T_s = pd.DataFrame(sc_t.fit_transform(work_dem[[C.TREATMENT]]),
                              columns=[C.TREATMENT], index=work_dem.index)
        X_s = pd.DataFrame(sc_x.fit_transform(work_dem[local_ctrl]),
                              columns=local_ctrl, index=work_dem.index)
        df_dml = pd.concat([work_dem[[C.TARGET]], T_s, X_s,
                              work_dem[[cluster_col]]], axis=1)
        data = DoubleMLClusterData(df_dml, y_col=C.TARGET, d_cols=C.TREATMENT,
                                       cluster_cols=cluster_col,
                                       x_cols=list(local_ctrl))
        kw = dict(l1_ratio=[0.1,0.5,1.0], alphas=np.logspace(-3,1,10),
                    cv=3, max_iter=2000, precompute=False)
        plr = DoubleMLPLR(data, ml_l=ElasticNetCV(**kw),
                              ml_m=ElasticNetCV(**kw),
                              n_folds=n_folds, n_rep=n_reps)
        plr.fit()
        coef = float(plr.summary["coef"].iloc[0])
        se = float(plr.summary["std err"].iloc[0])
        pval = float(plr.summary["P>|t|"].iloc[0])
        std_t = float(sc_t.scale_[0])
        stars = ("***" if pval<0.01 else "**" if pval<0.05 else "*" if pval<0.10 else "")
        rows.append({
            "group": label, "model": "PLR_FE_cluster", "iv_set": "none",
            "pp_per_unit": round(100 * coef / std_t, 4),
            "ci95_lo_pp": round(100 * (coef - 1.96 * se) / std_t, 4),
            "ci95_hi_pp": round(100 * (coef + 1.96 * se) / std_t, 4),
            "pval": round(pval, 6), "stars": stars,
            "n_obs": len(work), "n_clusters": work[cluster_col].nunique(),
            "n_controls": len(local_ctrl),
        })
        log.info("    %s PLR (%ds): pp/R$M=%+.3f%s n=%d c=%d",
                 label, int(time.time()-t0),
                 rows[-1]["pp_per_unit"], stars, len(work),
                 work[cluster_col].nunique())
    except Exception as e:
        log.error("    %s PLR failed: %s", label, e)

    # PLIV-backlog with FE
    if avail_iv:
        try:
            t0 = time.time()
            cols_dem = [C.TARGET, C.TREATMENT] + list(local_ctrl) + list(avail_iv)
            seen, cu = set(), []
            for c in cols_dem + [cluster_col]:
                if c not in seen: cu.append(c); seen.add(c)
            work = df_g[cu].dropna().copy()
            if len(work) < 1000:
                return rows
            work_dem = within_transform(work, cluster_col, cols_dem)
            from sklearn.preprocessing import StandardScaler
            from sklearn.linear_model import ElasticNetCV
            from doubleml import DoubleMLClusterData, DoubleMLPLIV
            sc_t = StandardScaler(); sc_x = StandardScaler(); sc_z = StandardScaler()
            T_s = pd.DataFrame(sc_t.fit_transform(work_dem[[C.TREATMENT]]),
                                  columns=[C.TREATMENT], index=work_dem.index)
            X_s = pd.DataFrame(sc_x.fit_transform(work_dem[local_ctrl]),
                                  columns=local_ctrl, index=work_dem.index)
            Z_s = pd.DataFrame(sc_z.fit_transform(work_dem[avail_iv]),
                                  columns=avail_iv, index=work_dem.index)
            df_dml = pd.concat([work_dem[[C.TARGET]], T_s, X_s, Z_s,
                                  work_dem[[cluster_col]]], axis=1)
            data = DoubleMLClusterData(df_dml, y_col=C.TARGET, d_cols=C.TREATMENT,
                                           cluster_cols=cluster_col,
                                           x_cols=list(local_ctrl), z_cols=list(avail_iv))
            kw = dict(l1_ratio=[0.1,0.5,1.0], alphas=np.logspace(-3,1,10),
                        cv=3, max_iter=2000, precompute=False)
            pliv = DoubleMLPLIV(data, ml_l=ElasticNetCV(**kw),
                                    ml_m=ElasticNetCV(**kw),
                                    ml_r=ElasticNetCV(**kw),
                                    n_folds=n_folds, n_rep=n_reps)
            pliv.fit()
            coef = float(pliv.summary["coef"].iloc[0])
            se = float(pliv.summary["std err"].iloc[0])
            pval = float(pliv.summary["P>|t|"].iloc[0])
            std_t = float(sc_t.scale_[0])
            stars = ("***" if pval<0.01 else "**" if pval<0.05 else "*" if pval<0.10 else "")
            rows.append({
                "group": label, "model": "PLIV_FE_cluster", "iv_set": "backlog",
                "pp_per_unit": round(100 * coef / std_t, 4),
                "ci95_lo_pp": round(100 * (coef - 1.96 * se) / std_t, 4),
                "ci95_hi_pp": round(100 * (coef + 1.96 * se) / std_t, 4),
                "pval": round(pval, 6), "stars": stars,
                "n_obs": len(work), "n_clusters": work[cluster_col].nunique(),
                "n_controls": len(local_ctrl),
            })
            log.info("    %s PLIV-bl (%ds): pp/R$M=%+.3f%s",
                     label, int(time.time()-t0),
                     rows[-1]["pp_per_unit"], stars)
        except Exception as e:
            log.error("    %s PLIV-bl failed: %s", label, e)
    return rows


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=1,
                    help="DML reps (1 default for speed)")
    p.add_argument("--quick", action="store_true",
                    help="quick mode: skip lengthy pooled groups")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("18_fine_v2")

    log.info("Loading panel (window=pre)")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["data"] = pd.to_datetime(df["data"])
    df["ano"] = df["data"].dt.year
    log.info("Panel: %d rows | controls full_clean: ?", len(df))
    controls = get_clean_full_controls(df)
    log.info("Full clean controls: %d", len(controls))

    rows = []
    ivs = C.IV_SETS["backlog"]

    # ── Per-leg × status partidário ─────────────────────────────────────────
    log.info("\n=== A. Per-leg × status partidário ===")
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else f"leg{leg}"
        if args.quick and leg is None: continue
        df_l = df.copy() if leg is None else df[df["idLegislatura"]==leg]
        for status, mask_col in [("oposicao", "d_oposicao"),
                                       ("coalizao", "d_coalizao"),
                                       ("independente", "d_independente")]:
            df_g = df_l[df_l[mask_col]==1]
            label = f"{leg_label}_{status}"
            rows.extend(run_subgroup_v2(df_g, controls, ivs, label, log,
                                              n_reps=args.reps))

    # ── Per-leg × ano eleitoral ─────────────────────────────────────────────
    log.info("\n=== B. Per-leg × ano eleitoral ===")
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else f"leg{leg}"
        if args.quick and leg is None: continue
        df_l = df.copy() if leg is None else df[df["idLegislatura"]==leg]
        for fed_label, fed_val in [("nao_eleicao", 0), ("eleicao_federal", 1)]:
            df_g = df_l[df_l["d_elec_federal"]==fed_val]
            label = f"{leg_label}_{fed_label}"
            rows.extend(run_subgroup_v2(df_g, controls, ivs, label, log,
                                              n_reps=args.reps))

    # ── Per-leg × tipo da proposta ──────────────────────────────────────────
    log.info("\n=== C. Per-leg × tipo da proposta ===")
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else f"leg{leg}"
        if args.quick and leg is None: continue
        df_l = df.copy() if leg is None else df[df["idLegislatura"]==leg]
        for tcol, tname in [("d_tipoVotacao_PEC", "PEC"),
                                ("d_tipoVotacao_MPV", "MPV"),
                                ("d_tipoVotacao_PLP", "PLP"),
                                ("d_tipoVotacao_PL", "PL")]:
            if tcol not in df_l.columns: continue
            df_g = df_l[df_l[tcol]==1]
            label = f"{leg_label}_{tname}"
            rows.extend(run_subgroup_v2(df_g, controls, ivs, label, log,
                                              n_reps=args.reps))

    # ── Por ano calendário ──────────────────────────────────────────────────
    log.info("\n=== D. Por ano ===")
    for ano in range(2015, 2023):
        df_g = df[df["ano"]==ano]
        rows.extend(run_subgroup_v2(df_g, controls, ivs, f"ano{ano}", log,
                                          n_reps=args.reps))

    # ── Por orientação do governo × leg ─────────────────────────────────────
    log.info("\n=== E. Orientação do governo × leg ===")
    for col, ori_label in [("d_ori_gov_sim", "ori_Sim"),
                                ("d_ori_gov_nao", "ori_Nao")]:
        if col not in df.columns: continue
        for leg in (55, 56):
            df_g = df[(df["idLegislatura"]==leg) & (df[col]==1)]
            label = f"leg{leg}_{ori_label}"
            rows.extend(run_subgroup_v2(df_g, controls, ivs, label, log,
                                              n_reps=args.reps))

    # ── Tercis de tratamento × leg ──────────────────────────────────────────
    log.info("\n=== F. Tercis de tratamento × leg ===")
    for leg in (55, 56):
        df_l = df[df["idLegislatura"]==leg].copy()
        df_pos = df_l[df_l[C.TREATMENT] > 0].copy()
        if len(df_pos) < 6000: continue
        df_pos["T_tercil"] = pd.qcut(df_pos[C.TREATMENT], q=3,
                                          labels=["low","mid","high"])
        for t in ("low","mid","high"):
            df_g = df_pos[df_pos["T_tercil"]==t]
            label = f"leg{leg}_T_{t}"
            rows.extend(run_subgroup_v2(df_g, controls, ivs, label, log,
                                              n_reps=args.reps))

    # ── Leg × Status × Ano eleitoral (interação tripla) ─────────────────────
    log.info("\n=== G. Leg × Status × Ano eleitoral ===")
    for leg in (55, 56):
        df_l = df[df["idLegislatura"]==leg]
        for status, mask_col in [("opos","d_oposicao"),("coal","d_coalizao")]:
            for fed_label, fed_val in [("naoel",0),("el",1)]:
                df_g = df_l[(df_l[mask_col]==1) & (df_l["d_elec_federal"]==fed_val)]
                label = f"leg{leg}_{status}_{fed_label}"
                rows.extend(run_subgroup_v2(df_g, controls, ivs, label, log,
                                                  n_reps=args.reps))

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "fine_heterogeneity_v2.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))

    # Summary: PLIV-backlog only, sorted by pp_per_unit
    sub = df_out[df_out["model"]=="PLIV_FE_cluster"].copy()
    sub = sub.sort_values("pp_per_unit")
    log.info("\n=== TOP-15 most NEGATIVE ===")
    log.info("\n%s", sub.head(15)[["group","pp_per_unit","ci95_lo_pp",
                                         "ci95_hi_pp","stars","n_obs"]].to_string(index=False))
    log.info("\n=== TOP-15 most POSITIVE ===")
    log.info("\n%s", sub.tail(15)[["group","pp_per_unit","ci95_lo_pp",
                                         "ci95_hi_pp","stars","n_obs"]].to_string(index=False))


if __name__ == "__main__":
    main()
