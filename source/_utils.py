# -*- coding: utf-8 -*-
"""
_utils.py — paper-emendas modeling helpers
==========================================
Reusable functions for assembling the modeling panel and running DML.

Critical: every assembly function ASSERTS that the joined panel has
unique (idDeputado, idVotacao). If it doesn't, we abort loud rather
than silently inflate (the bug that produced the original paper's
N=1,288,167 instead of N=761,016).
"""
from __future__ import annotations

import warnings
from typing import Iterable

import numpy as np
import pandas as pd

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
import _config as C

warnings.filterwarnings("ignore")


# ============================================================================
# Panel assembly
# ============================================================================

def assert_unique(df: pd.DataFrame, cols, label: str = "panel") -> None:
    n_dups = df.duplicated(subset=list(cols)).sum()
    if n_dups > 0:
        raise AssertionError(f"{label}: {n_dups:,} duplicate rows on {cols}")


def load_modeling_panel(
    window: str = "pre",
    legis: list | tuple = C.LEGISLATURAS,
    include_polarization: bool = True,
    include_coalizao: bool = True,
    log=None,
) -> pd.DataFrame:
    """
    Assemble the (idDeputado, idVotacao) modeling panel for the given window.

    Pieces joined:
      1. panel_features.csv      — base panel + 212 features
      2. panel_emendas_<window>  — emenda_valor in window
      3. iv_features.csv         — instruments
      4. coalizao_partido_data   — coalition/opposition status
      5. polarizacao_votacao     — vote-level polarization indices

    Filters:
      - idLegislatura ∈ legis (default: 55, 56)
      - alinhamento ∈ {0, 1}

    Returns DataFrame with all columns + derived:
      - emenda_M = emenda_valor / 1e6 (R$M)
      - log1p_emenda = log(1 + emenda_M)
      - d_elec_federal, d_elec_municipal
    """
    if log:
        log.info("loading panel_features")
    pf = pd.read_csv(C.PANEL / "panel_features.csv", sep=";", low_memory=False)
    pf["data"] = pd.to_datetime(pf["data"])
    pf = pf[pf["idLegislatura"].isin(legis)].copy()
    assert_unique(pf, ["idDeputado", "idVotacao"], "panel_features")

    if log:
        log.info(f"loading panel_emendas_{window}")
    em = pd.read_csv(C.WINDOW_FILES[window], sep=";", low_memory=False,
                       usecols=["idDeputado", "idVotacao", "emenda_valor",
                                 "n_empenhos"])
    assert_unique(em, ["idDeputado", "idVotacao"], f"panel_emendas_{window}")

    if log:
        log.info("loading iv_features")
    iv = pd.read_csv(C.PANEL / "iv_features.csv", sep=";", low_memory=False)
    assert_unique(iv, ["idDeputado", "idVotacao"], "iv_features")

    # Inner-join: panel_features ⋂ panel_emendas ⋂ iv_features
    df = pf.merge(em, on=["idDeputado", "idVotacao"], how="inner")
    df = df.merge(iv, on=["idDeputado", "idVotacao"], how="inner")
    assert_unique(df, ["idDeputado", "idVotacao"], "merged panel")

    # Drop rows with NaN treatment/outcome
    n_before = len(df)
    df = df.dropna(subset=["emenda_valor", C.TARGET])
    if log and len(df) < n_before:
        log.info(f"  dropped {n_before - len(df)} rows with NaN treatment/outcome")

    # Keep alinhamento ∈ {0,1}
    df = df[df[C.TARGET].isin([0, 1])].copy()

    # Derived treatment columns
    df["emenda_M"] = df["emenda_valor"] / 1e6
    df["log1p_emenda"] = np.log1p(df["emenda_M"].clip(lower=0))

    # Election year dummies
    df["y"] = df["data"].dt.year
    df["d_elec_federal"] = df["y"].isin(C.FEDERAL_ELECTIONS).astype(int)
    df["d_elec_municipal"] = df["y"].isin(C.MUNICIPAL_ELECTIONS).astype(int)

    # Impute missing idade / idade2 with legislature-level median
    # (44% of dep_info has missing dataNascimento)
    if "idade" in df.columns:
        med = df.groupby("idLegislatura")["idade"].transform("median")
        df["idade"] = df["idade"].fillna(med)
        df["idade"] = df["idade"].fillna(df["idade"].median())
        df["idade2"] = df["idade"].pow(2).round(1)

    # Coalition status
    if include_coalizao:
        if log:
            log.info("merging coalizao status")
        coal = pd.read_csv(C.PANEL / "coalizao_partido_data.csv", sep=";",
                              low_memory=False)
        coal["data"] = pd.to_datetime(coal["data"])
        coal["siglaPartido"] = coal["siglaPartido"].astype(str).str.upper().str.strip()
        df["siglaPartido_norm"] = df["siglaPartido"].astype(str).str.upper().str.strip()
        df = df.merge(
            coal[["siglaPartido", "data", "d_oposicao", "d_coalizao",
                    "d_independente", "coalizao_status"]]
                .rename(columns={"siglaPartido": "siglaPartido_norm"}),
            on=["siglaPartido_norm", "data"], how="left",
        )
        df = df.drop(columns=["siglaPartido_norm"])
        df[["d_oposicao", "d_coalizao", "d_independente"]] = (
            df[["d_oposicao", "d_coalizao", "d_independente"]].fillna(0).astype(int)
        )
        # Independente if not classified (small parties not in our list)
        unclassified = (df["d_oposicao"] + df["d_coalizao"] + df["d_independente"] == 0)
        df.loc[unclassified, "d_independente"] = 1

    # Polarization
    if include_polarization:
        if log:
            log.info("merging polarization indices")
        pol = pd.read_csv(C.PANEL / "polarizacao_votacao.csv", sep=";",
                            low_memory=False)
        df = df.merge(pol, on="idVotacao", how="left")
        df[["pol_simple", "pol_jaccard"]] = df[["pol_simple", "pol_jaccard"]].fillna(0)

    # Final assertion
    assert_unique(df, ["idDeputado", "idVotacao"], "final modeling panel")
    if log:
        log.info(f"final panel: {len(df):,} rows × {df.shape[1]} cols")

    return df


# ============================================================================
# DML primitives (PLR, PLIV)
# ============================================================================

_ALPHAS = np.logspace(-3, 1, 10)
_CV_KW = dict(l1_ratio=[0.1, 0.5, 1.0], alphas=_ALPHAS, cv=3, max_iter=2000)


def _make_dml_data(df, outcome, treatment, controls, ivs=None):
    from doubleml import DoubleMLData
    from sklearn.preprocessing import StandardScaler
    # Defensive: drop treatment/outcome/ivs from controls if accidentally included
    iv_set = set(ivs) if ivs else set()
    controls = [c for c in controls
                  if c != outcome and c != treatment and c not in iv_set]
    if ivs:
        ivs = [z for z in ivs if z != outcome and z != treatment]
    cols = [outcome, treatment] + list(controls)
    if ivs:
        cols += list(ivs)
    # Deduplicate preserving order
    seen, cols_unique = set(), []
    for c in cols:
        if c not in seen:
            cols_unique.append(c); seen.add(c)
    cols = cols_unique
    work = df[cols].dropna().copy()
    if len(work) < 300:
        return None, None, None

    sc_t = StandardScaler()
    sc_x = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[treatment]]),
                          columns=[treatment], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[controls]),
                          columns=controls, index=work.index)
    parts = [work[[outcome]], T_s, X_s]
    if ivs:
        sc_z = StandardScaler()
        Z_s = pd.DataFrame(sc_z.fit_transform(work[ivs]),
                              columns=ivs, index=work.index)
        parts.append(Z_s)
    df_dml = pd.concat(parts, axis=1)
    if ivs:
        data = DoubleMLData(df_dml, y_col=outcome, d_cols=treatment,
                              x_cols=list(controls), z_cols=list(ivs))
    else:
        data = DoubleMLData(df_dml, y_col=outcome, d_cols=treatment,
                              x_cols=list(controls))
    return data, sc_t, len(work)


def run_plr(df, outcome=C.TARGET, treatment=C.TREATMENT, controls=None,
              n_folds=C.N_FOLDS, n_reps=C.N_REPS):
    """DML Partially Linear Regression (no IV)."""
    from doubleml import DoubleMLPLR
    from sklearn.linear_model import ElasticNetCV
    if controls is None:
        controls = C.CONTROLS_REDUCED
    data, sc_t, n = _make_dml_data(df, outcome, treatment, controls)
    if data is None:
        return None
    plr = DoubleMLPLR(data,
                        ml_l=ElasticNetCV(**_CV_KW),
                        ml_m=ElasticNetCV(**_CV_KW),
                        n_folds=n_folds, n_rep=n_reps)
    plr.fit()
    res = plr.summary.copy()
    res["std_T"] = sc_t.scale_[0]
    res["n_obs"] = n
    return res


def run_pliv(df, ivs, outcome=C.TARGET, treatment=C.TREATMENT, controls=None,
               n_folds=C.N_FOLDS, n_reps=C.N_REPS):
    """DML PLR with IV (PLIV)."""
    from doubleml import DoubleMLPLIV
    from sklearn.linear_model import ElasticNetCV
    if controls is None:
        controls = C.CONTROLS_REDUCED
    data, sc_t, n = _make_dml_data(df, outcome, treatment, controls, ivs=ivs)
    if data is None:
        return None
    pliv = DoubleMLPLIV(data,
                          ml_l=ElasticNetCV(**_CV_KW),
                          ml_m=ElasticNetCV(**_CV_KW),
                          ml_r=ElasticNetCV(**_CV_KW),
                          n_folds=n_folds, n_rep=n_reps)
    pliv.fit()
    res = pliv.summary.copy()
    res["std_T"] = sc_t.scale_[0]
    res["n_obs"] = n
    return res


def extract_row(res, label_dict, std_Y=None):
    """
    Build a result row from a DML summary.

    Coefficient interpretation:
      coef        : DML output (with T standardized, Y on its native scale).
                     For Y∈{0,1}, this is the change in P(Y=1) per 1 SD of T.
      coef_per_unit (theta): coef / std_T → effect of 1 unit of T (R$M for
                                    emenda_valor in R$M).
      pp_per_R$M  : same as coef_per_unit × 100 (since Y is binary).
      coef_std_pp : coef × 100 (effect of 1 SD of T in pp).
    """
    if res is None:
        return None
    coef = float(res["coef"].iloc[0])
    se = float(res["std err"].iloc[0])
    pval = float(res["P>|t|"].iloc[0])
    std_t = float(res["std_T"].iloc[0])
    n_obs = int(res["n_obs"].iloc[0])

    stars = ("***" if pval < 0.01 else
             "**" if pval < 0.05 else
             "*" if pval < 0.10 else "")

    row = {
        "coef_sd": round(coef, 6),                 # 1 SD T → ΔP(Y=1)
        "se_sd": round(se, 6),
        "coef_per_unit": round(coef / std_t, 8),   # per unit of T
        "se_per_unit": round(se / std_t, 8),
        "pp_per_unit": round(100 * coef / std_t, 4),  # pp (per unit)
        "pp_per_sd": round(100 * coef, 4),         # pp per 1 SD
        "pval": round(pval, 6),
        "stars": stars,
        "n_obs": n_obs,
        "std_T": round(std_t, 6),
    }
    row.update(label_dict)
    return row


def first_stage_F(df, treatment, ivs, controls):
    """Incremental F-stat for IV relevance."""
    import statsmodels.api as sm
    # Defensive: drop treatment/IVs from controls in case of duplicates
    controls = [c for c in controls if c != treatment and c not in ivs]
    ivs = [z for z in ivs if z != treatment]
    cols = [treatment] + list(ivs) + list(controls)
    # Deduplicate cols preserving order
    seen, cols_unique = set(), []
    for c in cols:
        if c not in seen:
            cols_unique.append(c); seen.add(c)
    cols = cols_unique
    work = df[cols].dropna()
    if len(work) < 100:
        return {"f_stat": 0, "n": len(work)}
    Y = work[treatment].values
    if Y.ndim > 1:
        Y = Y[:, 0]
    X_full = sm.add_constant(work[list(ivs) + list(controls)].values)
    X_red = sm.add_constant(work[list(controls)].values)
    full = sm.OLS(Y, X_full).fit()
    red = sm.OLS(Y, X_red).fit()
    n, k = len(Y), X_full.shape[1]
    q = len(ivs)
    f = ((red.ssr - full.ssr) / q) / (full.ssr / (n - k))
    return {"f_stat": round(f, 2), "n": n, "n_iv": q}


def sargan_J(df, treatment, ivs, controls, target=C.TARGET):
    """Sargan-Hansen overidentification test (only for #IVs > 1)."""
    if len(ivs) <= 1:
        return {"j_stat": np.nan, "j_pval": np.nan, "df": 0}
    import statsmodels.api as sm
    from scipy import stats as sp
    # Defensive: dedup
    controls = [c for c in controls if c != treatment and c != target
                  and c not in ivs]
    ivs = [z for z in ivs if z != treatment and z != target]
    cols = [target, treatment] + list(ivs) + list(controls)
    seen, cols_unique = set(), []
    for c in cols:
        if c not in seen:
            cols_unique.append(c); seen.add(c)
    cols = cols_unique
    work = df[cols].dropna()
    if len(work) < 100:
        return {"j_stat": np.nan, "j_pval": np.nan, "df": 0}
    X_fs = sm.add_constant(work[list(ivs) + list(controls)].values)
    T = work[treatment].values
    fs = sm.OLS(T, X_fs).fit()
    T_hat = fs.fittedvalues
    X_ss = sm.add_constant(np.column_stack([T_hat] +
                              [work[c].values for c in controls]))
    Y = work[target].values
    ss = sm.OLS(Y, X_ss).fit()
    resid = ss.resid
    X_j = sm.add_constant(work[list(ivs) + list(controls)].values)
    j_reg = sm.OLS(resid, X_j).fit()
    j_stat = len(work) * j_reg.rsquared
    j_df = len(ivs) - 1
    j_pval = 1 - sp.chi2.cdf(j_stat, j_df) if j_df > 0 else np.nan
    return {"j_stat": round(j_stat, 2), "j_pval": round(j_pval, 6),
              "df": j_df, "n": len(work)}
