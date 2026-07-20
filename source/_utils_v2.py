# -*- coding: utf-8 -*-
"""
_utils_v2.py — Helpers para a especificação PRINCIPAL definitiva
=================================================================
A spec principal do paper (decidida em 08/05/2026 após auditoria
e tuning):
  - window=pre (60d antes do voto)
  - controls=full_clean (~142, sem bad controls votosSim/Não/Outros/aprovacao)
  - Deputy fixed effects (within-transformation)
  - Cluster-SE por idDeputado (CGM via DoubleMLClusterData)

Funções:
  run_plr_main(df, leg=None) → resultado PLR principal
  run_pliv_main(df, leg=None, iv_set='backlog') → resultado PLIV principal
  extract_row_v2(res, label) → linha padronizada com pp/R$M e CIs

Para usar nos scripts 02/03/04 (heterogeneidades, decomposição, contrafactual).
"""
from __future__ import annotations

import warnings
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U  # for load_modeling_panel

warnings.filterwarnings("ignore")


BAD_CONTROLS = ["votosSim", "votosNao", "votosOutros", "aprovacao"]


def get_clean_full_controls(df: pd.DataFrame) -> list:
    """Full controls minus bad controls."""
    return [c for c in C.get_full_controls(df) if c not in BAD_CONTROLS]


def within_transform(df: pd.DataFrame, group_col: str,
                       cols_to_demean: list) -> pd.DataFrame:
    """Within-deputy demeaning. Equivalent to Deputy FE."""
    df = df.copy()
    means = df.groupby(group_col)[cols_to_demean].transform("mean")
    df[cols_to_demean] = df[cols_to_demean] - means
    return df


# ============================================================================
# PLR/PLIV with Deputy FE + cluster-SE (the main paper spec)
# ============================================================================

def run_plr_main(df: pd.DataFrame, controls: list = None,
                   target: str = C.TARGET, treatment: str = C.TREATMENT,
                   cluster_col="idDeputado",
                   n_folds: int = 3, n_reps: int = 3) -> dict | None:
    """DML PLR with Deputy FE + cluster-SE. Returns standardized row dict.

    cluster_col: str or list. Pass a list (e.g. ["idDeputado","idVotacao"])
    for two-way CGM clustering; the first element is used for the
    within-transformation.
    """
    from doubleml import DoubleMLClusterData, DoubleMLPLR
    from sklearn.linear_model import ElasticNetCV
    from sklearn.preprocessing import StandardScaler

    if isinstance(cluster_col, str):
        cluster_cols_list = [cluster_col]
    else:
        cluster_cols_list = list(cluster_col)
    demean_col = cluster_cols_list[0]

    if controls is None:
        controls = get_clean_full_controls(df)
    controls = [c for c in controls
                  if c not in (target, treatment)
                  and c not in cluster_cols_list]
    controls = [c for c in controls if c in df.columns
                  and df[c].notna().mean() > 0.5
                  and df[c].nunique() > 1]
    if len(controls) < 5:
        return None

    cols = [target, treatment] + controls + cluster_cols_list
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    work = df[cu].dropna().copy()
    if len(work) < 1000:
        return None
    for cc in cluster_cols_list:
        if work[cc].nunique() < 30:
            return None

    # Within-deputy demeaning
    cols_dem = [target, treatment] + controls
    work = within_transform(work, demean_col, cols_dem)

    sc_t = StandardScaler(); sc_x = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[treatment]]),
                          columns=[treatment], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    df_dml = pd.concat([work[[target]], T_s, X_s, work[cluster_cols_list]], axis=1)
    data = DoubleMLClusterData(df_dml, y_col=target, d_cols=treatment,
                                  cluster_cols=cluster_cols_list, x_cols=list(controls))
    kw = dict(l1_ratio=[0.1, 0.5, 1.0], alphas=np.logspace(-3, 1, 10),
                cv=3, max_iter=2000, precompute=False)
    plr = DoubleMLPLR(data,
                        ml_l=ElasticNetCV(**kw),
                        ml_m=ElasticNetCV(**kw),
                        n_folds=n_folds, n_rep=n_reps)
    plr.fit()

    coef = float(plr.summary["coef"].iloc[0])
    se = float(plr.summary["std err"].iloc[0])
    pval = float(plr.summary["P>|t|"].iloc[0])
    std_t = float(sc_t.scale_[0])
    n_obs = len(work)
    n_clusters_per_dim = {cc: int(work[cc].nunique()) for cc in cluster_cols_list}
    stars = ("***" if pval < 0.01 else "**" if pval < 0.05
                else "*" if pval < 0.10 else "")
    return {
        "model": "PLR_FE_cluster",
        "cluster_cols": ",".join(cluster_cols_list),
        "coef_sd": round(coef, 6),
        "se_sd_cluster": round(se, 6),
        "pp_per_unit": round(100 * coef / std_t, 4),
        "ci95_lo_pp": round(100 * (coef - 1.96 * se) / std_t, 4),
        "ci95_hi_pp": round(100 * (coef + 1.96 * se) / std_t, 4),
        "pval": round(pval, 6),
        "stars": stars,
        "n_obs": n_obs,
        "n_clusters_per_dim": n_clusters_per_dim,
        "n_controls": len(controls),
        "std_T": round(std_t, 6),
    }


def run_pliv_main(df: pd.DataFrame, controls: list = None,
                    iv_set: str = "backlog",
                    target: str = C.TARGET, treatment: str = C.TREATMENT,
                    cluster_col="idDeputado",
                    n_folds: int = 3, n_reps: int = 3) -> dict | None:
    """DML PLIV-backlog with Deputy FE + cluster-SE.

    cluster_col: str or list of str. If a list is passed (e.g.
    ["idDeputado", "idVotacao"]), doubleml computes two-way
    Cameron-Gelbach-Miller (2011) cluster-robust SEs. The first
    element is still used for the within-transformation (deputy demean).
    """
    from doubleml import DoubleMLClusterData, DoubleMLPLIV
    from sklearn.linear_model import ElasticNetCV
    from sklearn.preprocessing import StandardScaler

    # Normalise cluster_col to a list; keep first entry as the demean group
    if isinstance(cluster_col, str):
        cluster_cols_list = [cluster_col]
    else:
        cluster_cols_list = list(cluster_col)
    demean_col = cluster_cols_list[0]

    ivs = list(C.IV_SETS[iv_set])
    ivs = [z for z in ivs if z in df.columns and df[z].std() > 0]
    if not ivs:
        return None

    if controls is None:
        controls = get_clean_full_controls(df)
    controls = [c for c in controls
                  if c not in (target, treatment)
                  and c not in cluster_cols_list
                  and c not in ivs]
    controls = [c for c in controls if c in df.columns
                  and df[c].notna().mean() > 0.5
                  and df[c].nunique() > 1]
    if len(controls) < 5:
        return None

    cols = [target, treatment] + controls + ivs + cluster_cols_list
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    work = df[cu].dropna().copy()
    if len(work) < 1000:
        return None
    for cc in cluster_cols_list:
        if work[cc].nunique() < 30:
            return None

    cols_dem = [target, treatment] + controls + ivs
    work = within_transform(work, demean_col, cols_dem)

    sc_t = StandardScaler(); sc_x = StandardScaler(); sc_z = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[treatment]]),
                          columns=[treatment], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    Z_s = pd.DataFrame(sc_z.fit_transform(work[ivs]),
                          columns=ivs, index=work.index)
    df_dml = pd.concat([work[[target]], T_s, X_s, Z_s,
                          work[cluster_cols_list]], axis=1)
    data = DoubleMLClusterData(df_dml, y_col=target, d_cols=treatment,
                                  cluster_cols=cluster_cols_list,
                                  x_cols=list(controls), z_cols=list(ivs))
    kw = dict(l1_ratio=[0.1, 0.5, 1.0], alphas=np.logspace(-3, 1, 10),
                cv=3, max_iter=2000, precompute=False)
    pliv = DoubleMLPLIV(data,
                          ml_l=ElasticNetCV(**kw),
                          ml_m=ElasticNetCV(**kw),
                          ml_r=ElasticNetCV(**kw),
                          n_folds=n_folds, n_rep=n_reps)
    pliv.fit()

    coef = float(pliv.summary["coef"].iloc[0])
    se = float(pliv.summary["std err"].iloc[0])
    pval = float(pliv.summary["P>|t|"].iloc[0])
    std_t = float(sc_t.scale_[0])
    n_obs = len(work)
    n_clusters_per_dim = {cc: int(work[cc].nunique()) for cc in cluster_cols_list}
    stars = ("***" if pval < 0.01 else "**" if pval < 0.05
                else "*" if pval < 0.10 else "")
    return {
        "model": "PLIV_FE_cluster",
        "iv_set": iv_set,
        "cluster_cols": ",".join(cluster_cols_list),
        "coef_sd": round(coef, 6),
        "se_sd_cluster": round(se, 6),
        "pp_per_unit": round(100 * coef / std_t, 4),
        "ci95_lo_pp": round(100 * (coef - 1.96 * se) / std_t, 4),
        "ci95_hi_pp": round(100 * (coef + 1.96 * se) / std_t, 4),
        "pval": round(pval, 6),
        "stars": stars,
        "n_obs": n_obs,
        "n_clusters_per_dim": n_clusters_per_dim,
        "n_controls": len(controls),
        "std_T": round(std_t, 6),
    }


# Re-export load_modeling_panel for convenience
load_modeling_panel = U.load_modeling_panel
