"""
71_t6_cargos_quad.py
---------------------
T6 + T7:
  T6. Heterogeneidade por cargo legislativo (Mesa / Tier 2 = lider/pres comissao).
      Spec: PLIV-DML Leg 56, sub-amostras has_mesa=0/1 e n_tier2=0/>0.
      Hipotese narrativa F: deputados em cargos altos sao recipientes preferenciais
      do pork redirecionado pelo presidente da Camara.

  T7. Tratamento quadratico T + T^2 (curva resposta).
      Spec: PLIV-DML pooled e por leg, com (T, T^2) como tratamentos.
      Usa 2 IVs (backlog Q4 + execucao YTD) para identificar.
      Identificacao parcial pode ocorrer; reportamos KP F e CI.

Config: n_folds=3, n_reps=3 (replicacao do paper).

Outputs:
  results/n3_t6_cargos_het.csv
  results/n3_t7_quadratic.csv
"""

import sys
import time
import warnings
import logging
import traceback
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")

PANEL = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
# Config rapida para sensibilidade. Main paper n_reps=3 ja' confirmou variancia Monte Carlo
# tolerável. Para T6/T7 (analises descritivas adicionais nao incorporadas na main table),
# usamos n_reps=1 e seed fixa para tempo viavel.
N_FOLDS, N_REPS = 3, 1

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("t6t7")


EXTRA_TREATMENT_VARS = [
    "T_rp6_pre60", "T_rp6_pre60_M",
    "T_rp6_pix_pre60", "T_rp6_pix_pre60_M",
    "T_rp7_pre60", "T_rp7_pre60_M",
    "T_rp8_pre60", "T_rp8_pre60_M",
    "T_rp9_pre60", "T_rp9_pre60_M",
    "T_rp9_imputed_pre60", "T_rp9_imputed_pre60_M",
    "d_rp9_solicitante", "share_pork_opaco", "share_rp9",
    "share_pix", "n_apoiamentos_opaco",
]


def safe_pliv(df_l, controls, label):
    log.info(f"  PLIV: {label}  n={len(df_l):,}")
    if len(df_l) < 5000:
        log.warning(f"    too small ({len(df_l)})")
        return None
    controls = [c for c in controls if c in df_l.columns
                and df_l[c].notna().mean() > 0.5
                and df_l[c].nunique() > 1
                and c not in ("alinhamento", "emenda_M", "idDeputado")]
    t0 = time.time()
    try:
        res = U2.run_pliv_main(df_l, controls=controls, iv_set="backlog",
                                n_folds=N_FOLDS, n_reps=N_REPS)
        if res is None: return None
        log.info(f"    theta={res['pp_per_unit']:+.4f} pp p={res['pval']:.4f} "
                 f"({time.time()-t0:.0f}s)")
        return res
    except Exception as e:
        log.error(f"    FAIL: {e}")
        traceback.print_exc()
        return None


def build_panel():
    log.info("Loading modeling panel via U.load_modeling_panel(window='pre')")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    log.info(f"  panel: {len(df):,} rows; alinhamento mean={df['alinhamento'].mean():.4f}")
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["ano"] = df["data"].dt.year

    log.info("Loading panel_proxy_cargos for has_mesa / n_tier2")
    p6 = pd.read_csv(PANEL / "panel_proxy_cargos.csv", sep=";",
                     dtype={"idDeputado": str})
    p6["ano"] = p6["ano"].astype(int)
    p6 = p6[["idDeputado", "ano", "has_mesa", "n_tier2", "n_cargos"]]

    df = df.merge(p6, on=["idDeputado", "ano"], how="left")
    df["has_mesa"] = df["has_mesa"].fillna(0).astype(int)
    df["n_tier2"] = df["n_tier2"].fillna(0)
    df["has_tier2"] = (df["n_tier2"] > 0).astype(int)
    log.info(f"  has_mesa mean = {df['has_mesa'].mean():.4f}")
    log.info(f"  has_tier2 mean = {df['has_tier2'].mean():.4f}")
    return df


def run_t6_cargos_het(df):
    """T6: het por cargo (Leg 56 onde Lira preside)."""
    log.info("\n" + "="*70)
    log.info("T6: Heterogeneidade por cargo legislativo (Leg 56)")
    log.info("="*70)
    df56 = df[df["idLegislatura"] == 56].copy()
    ctrl_full = U2.get_clean_full_controls(df56)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS
             and c not in ("has_mesa", "has_tier2", "n_tier2", "n_cargos")]
    log.info(f"  ctrl: {len(ctrl)} cols")

    rows = []
    for label, mask in [
        ("mesa", df56["has_mesa"] == 1),
        ("no_mesa", df56["has_mesa"] == 0),
        ("tier2", df56["has_tier2"] == 1),
        ("no_tier2", df56["has_tier2"] == 0),
    ]:
        sub = df56[mask].copy()
        log.info(f"  -- {label}: n={len(sub):,}")
        res = safe_pliv(sub, ctrl, f"T6 {label}")
        if res:
            res.update({"subgroup": label, "outcome": "gov"})
            rows.append(res)
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "n3_t6_cargos_het.csv", sep=";", index=False)
    log.info(f"  saved {RESULTS / 'n3_t6_cargos_het.csv'}")
    if len(out):
        print(out[["subgroup", "pp_per_unit", "ci95_lo_pp", "ci95_hi_pp",
                    "pval", "stars", "n_obs", "n_clusters"]].to_string(index=False))


def run_t7_quadratic(df):
    """T7: T + T^2 simultaneamente (dois tratamentos)."""
    log.info("\n" + "="*70)
    log.info("T7: Tratamento quadratico T + T^2")
    log.info("="*70)
    from doubleml import DoubleMLPLIV, DoubleMLClusterData
    from sklearn.linear_model import ElasticNetCV

    rows = []
    for leg_lbl, leg in [("pooled", None), ("leg55", 55), ("leg56", 56)]:
        df_l = df.copy() if leg is None else df[df["idLegislatura"] == leg].copy()
        df_l = df_l.dropna(subset=["alinhamento", "emenda_M"]).copy()
        # T2
        df_l["emenda_M_sq"] = df_l["emenda_M"] ** 2
        # IVs adicionais: usar backlog + Q4 (precisa de 2 IVs para identificar 2 ts)
        iv_cols = []
        for iv_name in ["iv_q4_no_ytd", "iv_ytd_exec_pct", "iv_q4_dummy",
                         "iv_days_to_dec31"]:
            if iv_name in df_l.columns:
                iv_cols.append(iv_name)
        # Garantir pelo menos 2 IVs
        if len(iv_cols) < 2:
            log.warning(f"  {leg_lbl}: only {len(iv_cols)} IVs, need >=2")
            continue
        iv_cols = iv_cols[:2]

        ctrl_full = U2.get_clean_full_controls(df_l)
        ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS
                 and c not in iv_cols
                 and c in df_l.columns
                 and df_l[c].notna().mean() > 0.5
                 and df_l[c].nunique() > 1
                 and c not in ("alinhamento", "emenda_M", "emenda_M_sq",
                               "idDeputado", "has_mesa", "has_tier2",
                               "n_tier2", "n_cargos")]

        # Drop rows com NaN nos IVs ou ctrl
        keep = ["idDeputado", "alinhamento", "emenda_M", "emenda_M_sq"] + iv_cols + ctrl
        keep = list(dict.fromkeys(keep))
        sub = df_l[keep].dropna().copy()
        sub["idDeputado_int"] = sub["idDeputado"].astype("category").cat.codes
        log.info(f"  {leg_lbl}: n={len(sub):,}, ctrl={len(ctrl)}, ivs={iv_cols}")

        if len(sub) < 5000:
            continue

        try:
            data = DoubleMLClusterData(
                sub, y_col="alinhamento",
                d_cols=["emenda_M", "emenda_M_sq"],
                z_cols=iv_cols,
                x_cols=ctrl,
                cluster_cols="idDeputado_int",
            )
            t0 = time.time()
            ml_l = ElasticNetCV(cv=3, max_iter=2000, n_jobs=-1)
            ml_m = ElasticNetCV(cv=3, max_iter=2000, n_jobs=-1)
            ml_r = ElasticNetCV(cv=3, max_iter=2000, n_jobs=-1)
            dml = DoubleMLPLIV(data, ml_l=ml_l, ml_m=ml_m, ml_r=ml_r,
                                n_folds=N_FOLDS, n_rep=N_REPS, score="partialling out")
            dml.fit()
            theta = dml.coef
            se = dml.se
            ci = dml.confint(level=0.95)
            log.info(f"    fit done ({time.time()-t0:.0f}s)")
            log.info(f"    theta(T)={theta[0]:+.4f} se={se[0]:.4f}")
            log.info(f"    theta(T^2)={theta[1]:+.4f} se={se[1]:.4f}")
            # Inflection: dY/dT = theta1 + 2*theta2*T = 0 -> T* = -theta1/(2*theta2)
            t_star = -theta[0] / (2 * theta[1]) if theta[1] != 0 else np.nan
            log.info(f"    T* (inflection) = {t_star:.3f} R$M")
            rows.append({
                "leg": leg_lbl,
                "theta_T": round(theta[0], 6),
                "se_T": round(se[0], 6),
                "ci_T_lo": round(ci.iloc[0, 0], 6),
                "ci_T_hi": round(ci.iloc[0, 1], 6),
                "theta_Tsq": round(theta[1], 6),
                "se_Tsq": round(se[1], 6),
                "ci_Tsq_lo": round(ci.iloc[1, 0], 6),
                "ci_Tsq_hi": round(ci.iloc[1, 1], 6),
                "T_inflection_RM": round(t_star, 3),
                "n_obs": len(sub),
                "n_ctrl": len(ctrl),
                "ivs": ",".join(iv_cols),
            })
        except Exception as e:
            log.error(f"  {leg_lbl} FAILED: {e}")
            traceback.print_exc()
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "n3_t7_quadratic.csv", sep=";", index=False)
    log.info(f"  saved {RESULTS / 'n3_t7_quadratic.csv'}")
    if len(out): print(out.to_string(index=False))


def main():
    df = build_panel()
    run_t6_cargos_het(df)
    run_t7_quadratic(df)
    log.info("\n  done.")


if __name__ == "__main__":
    main()
