# -*- coding: utf-8 -*-
"""
19_controls_tuning.py — USER2: testar várias estratégias de seleção de controles
==================================================================================
Avalia DML (PLIV-backlog, leg=56 — onde o efeito é mais robusto) sob
diferentes definições de controles. Objetivo: descobrir se existe uma
spec melhor que reduced/full_clean atuais.

Estratégias testadas:

  (A) reduced              — 29 controles definidos a priori
  (B) full_clean           — 142 controles (full minus bad)
  (C) full_clean_no_orient — 142 menos d_ori_part/mai/min/op (suspeitos endo)
  (D) lasso_selected       — pre-select via Lasso(Y~T+X) + Lasso(T~Z+X)
                              keep features selected by EITHER. Efeito double-selection
                              de Belloni-Chernozhukov-Hansen.
  (E) rf_top50             — top 50 features por importance no RF(Y~T+X)
  (F) buckets_safe         — só buckets que não mexeram coef no audit (idade,
                              uf_reg, escolaridade, prof, n_aggregates, election)
  (G) buckets_temporal     — só temporais (election, year, quarter, polarization)

Cada strategy: rodar PLR + PLIV-backlog em (leg=56) com cluster-SE
(sem FE, pra acelerar — depois refazemos top-3 com FE).

Output: results/controls_tuning.csv
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


def make_strategies(df: pd.DataFrame) -> dict:
    """Returns dict {strategy_name: list_of_controls}."""
    full_all = C.get_full_controls(df)
    full_clean = [c for c in full_all if c not in BAD_CONTROLS]
    reduced = [c for c in C.CONTROLS_REDUCED if c in df.columns]

    # (C) full_clean sem d_ori_part/mai/min/op (orientação de outros lados)
    full_no_orient = [c for c in full_clean
                          if not any(c.startswith(f"d_ori_{s}_") or c == f"d_ori_{s}"
                                     for s in ("part","mai","min","op","bancada"))]

    # (F) buckets safe — só os que não mexeram o coef no audit
    safe_buckets = [
        "idade", "idade2", "indice_escolaridade",
        "tamanho_partido", "n_legis", "n_part",
        "d_homem", "d_titular",
    ]
    safe = [c for c in full_clean if (
        c in safe_buckets or
        c.startswith("d_niv_esc_") or
        c.startswith("d_uf_") or c.startswith("d_reg_") or
        c.startswith("d_prof_") or
        c.startswith("d_elec_")
    )]
    safe = [c for c in safe if c in df.columns]

    # (G) só temporais
    temporal = [c for c in full_clean if (
        c in ("d_elec_federal", "d_elec_municipal", "y", "ano",
                "pol_simple", "pol_jaccard")
        or c.startswith("d_tipoVotacao_")
        or c.startswith("d_tema_")
    )]
    temporal = [c for c in temporal if c in df.columns]

    return {
        "A_reduced": reduced,
        "B_full_clean": full_clean,
        "C_full_no_orient": full_no_orient,
        "D_lasso_selected": "TODO_lasso",  # built dynamically per fit
        "E_rf_top50": "TODO_rf",
        "F_buckets_safe": safe,
        "G_buckets_temporal": temporal,
    }


def select_via_lasso(df: pd.DataFrame, candidates: list,
                       target=C.TARGET, treatment=C.TREATMENT,
                       ivs=("iv_q4_no_ytd", "iv_ytd_exec_pct")) -> list:
    """Belloni-Chernozhukov-Hansen double-selection: keep features chosen by
    Lasso(Y~T+X) OR Lasso(T~Z+X)."""
    from sklearn.linear_model import LassoCV
    work = df[[target, treatment] + list(candidates) + list(ivs)].dropna()
    X = work[candidates].values
    Y = work[target].values
    T = work[treatment].values

    # Lasso 1: Y ~ T + X (control selection for outcome)
    m1 = LassoCV(alphas=np.logspace(-4, 1, 30), cv=3, max_iter=3000,
                    n_jobs=-1, random_state=42).fit(np.column_stack([T, X]), Y)
    # First coef is T; rest are X
    sel1 = np.abs(m1.coef_[1:]) > 1e-8

    # Lasso 2: T ~ Z + X (control selection for treatment)
    Z = work[list(ivs)].values
    m2 = LassoCV(alphas=np.logspace(-4, 1, 30), cv=3, max_iter=3000,
                    n_jobs=-1, random_state=42).fit(np.column_stack([Z, X]), T)
    sel2 = np.abs(m2.coef_[len(ivs):]) > 1e-8

    keep = (sel1 | sel2)
    return [c for c, k in zip(candidates, keep) if k]


def select_via_rf(df: pd.DataFrame, candidates: list, top_k=50,
                    target=C.TARGET, treatment=C.TREATMENT) -> list:
    from sklearn.ensemble import RandomForestRegressor
    work = df[[target, treatment] + list(candidates)].dropna()
    X = np.column_stack([work[treatment].values, work[candidates].values])
    Y = work[target].values
    rf = RandomForestRegressor(n_estimators=100, max_depth=10,
                                  min_samples_leaf=20, n_jobs=-1,
                                  random_state=42).fit(X, Y)
    imp = rf.feature_importances_[1:]  # skip T
    rank = np.argsort(imp)[::-1][:top_k]
    return [candidates[i] for i in rank]


def run_one(df: pd.DataFrame, controls: list, leg: int,
             strategy_name: str, log,
             cluster_col="idDeputado", n_folds=3, n_reps=1) -> list:
    """PLR + PLIV-backlog cluster-robust on (leg, strategy)."""
    from doubleml import DoubleMLClusterData, DoubleMLPLR, DoubleMLPLIV
    from sklearn.linear_model import ElasticNetCV
    from sklearn.preprocessing import StandardScaler

    df_l = df[df["idLegislatura"]==leg].copy()
    local_ctrl = [c for c in controls if c in df_l.columns
                    and df_l[c].notna().mean() > 0.5
                    and df_l[c].nunique() > 1]
    log.info("--- %s leg%d n=%d ctrl=%d ---",
             strategy_name, leg, len(df_l), len(local_ctrl))
    rows = []

    ivs = list(C.IV_SETS["backlog"])

    # Build dml frame
    cols = [C.TARGET, C.TREATMENT] + local_ctrl + ivs + [cluster_col]
    seen, cu = set(), []
    for c in cols:
        if c not in seen: cu.append(c); seen.add(c)
    work = df_l[cu].dropna().copy()
    if len(work) < 1000: return rows
    sc_t = StandardScaler(); sc_x = StandardScaler(); sc_z = StandardScaler()
    T_s = pd.DataFrame(sc_t.fit_transform(work[[C.TREATMENT]]),
                          columns=[C.TREATMENT], index=work.index)
    X_s = pd.DataFrame(sc_x.fit_transform(work[local_ctrl]),
                          columns=local_ctrl, index=work.index)
    Z_s = pd.DataFrame(sc_z.fit_transform(work[ivs]),
                          columns=ivs, index=work.index)
    df_dml = pd.concat([work[[C.TARGET]], T_s, X_s, Z_s,
                          work[[cluster_col]]], axis=1)
    kw = dict(l1_ratio=[0.1,0.5,1.0], alphas=np.logspace(-3,1,10),
                cv=3, max_iter=2000, precompute=False)

    # PLR
    try:
        t0 = time.time()
        data = DoubleMLClusterData(df_dml, y_col=C.TARGET, d_cols=C.TREATMENT,
                                       cluster_cols=cluster_col,
                                       x_cols=list(local_ctrl))
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
            "strategy": strategy_name, "legis": leg, "model": "PLR",
            "n_controls": len(local_ctrl),
            "pp_per_unit": round(100 * coef / std_t, 4),
            "ci95_lo_pp": round(100 * (coef - 1.96 * se) / std_t, 4),
            "ci95_hi_pp": round(100 * (coef + 1.96 * se) / std_t, 4),
            "pval": round(pval, 6), "stars": stars,
            "n_obs": len(work),
        })
        log.info("  PLR (%ds): pp=%+.3f%s",
                 int(time.time()-t0), rows[-1]["pp_per_unit"], stars)
    except Exception as e:
        log.error("  PLR failed: %s", e)

    # PLIV
    try:
        t0 = time.time()
        data = DoubleMLClusterData(df_dml, y_col=C.TARGET, d_cols=C.TREATMENT,
                                       cluster_cols=cluster_col,
                                       x_cols=list(local_ctrl), z_cols=list(ivs))
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
            "strategy": strategy_name, "legis": leg, "model": "PLIV_backlog",
            "n_controls": len(local_ctrl),
            "pp_per_unit": round(100 * coef / std_t, 4),
            "ci95_lo_pp": round(100 * (coef - 1.96 * se) / std_t, 4),
            "ci95_hi_pp": round(100 * (coef + 1.96 * se) / std_t, 4),
            "pval": round(pval, 6), "stars": stars,
            "n_obs": len(work),
        })
        log.info("  PLIV-bl (%ds): pp=%+.3f%s",
                 int(time.time()-t0), rows[-1]["pp_per_unit"], stars)
    except Exception as e:
        log.error("  PLIV failed: %s", e)

    return rows


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--legs", default="55,56,all")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("19_ctrl_tune")

    log.info("Loading panel (window=pre)")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["idLegislatura"] = df["idLegislatura"].astype(int)

    strategies = make_strategies(df)

    # Build dynamic strategies (lasso, rf) on full sample (or pooled subsample)
    log.info("\nBuilding dynamic strategies (Lasso, RF) on pooled sample")
    full_clean = [c for c in C.get_full_controls(df) if c not in BAD_CONTROLS]
    sample = df.sample(n=min(100_000, len(df)), random_state=42)
    try:
        lasso_sel = select_via_lasso(sample, full_clean)
        log.info("  Lasso selected: %d / %d controls", len(lasso_sel), len(full_clean))
        strategies["D_lasso_selected"] = lasso_sel
    except Exception as e:
        log.error("  Lasso failed: %s", e)
        strategies["D_lasso_selected"] = full_clean
    try:
        rf_sel = select_via_rf(sample, full_clean, top_k=50)
        log.info("  RF top-50: %d controls", len(rf_sel))
        strategies["E_rf_top50"] = rf_sel
    except Exception as e:
        log.error("  RF failed: %s", e)
        strategies["E_rf_top50"] = full_clean[:50]

    log.info("\nStrategies: %s", {k: len(v) for k, v in strategies.items()})

    legs_list = []
    for s in args.legs.split(","):
        s = s.strip()
        if s == "all": continue  # cluster-SE pooled is heavy, skip pooled for tuning
        legs_list.append(int(s))

    rows = []
    for strat_name, controls in strategies.items():
        for leg in legs_list:
            t0 = time.time()
            r = run_one(df, controls, leg, strat_name, log, n_reps=args.reps)
            rows.extend(r)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "controls_tuning.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))

    # Summary table
    pliv = df_out[df_out["model"]=="PLIV_backlog"].copy()
    log.info("\n=== PLIV-backlog comparison across strategies ===")
    log.info("\n%s", pliv[["strategy","legis","n_controls","pp_per_unit",
                                "ci95_lo_pp","ci95_hi_pp","stars","n_obs"]]
                          .to_string(index=False))


if __name__ == "__main__":
    main()
