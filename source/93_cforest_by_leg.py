"""
93_cforest_by_leg.py
---------------------
Causal Forest IV by LEGISLATURE only (no Maia/Lira split within Leg 56).
Goal: maximize sample per cell to give the forest fair statistical power
and check whether the leg-level result reproduces PLIV-DML.

Sub-samples: leg55 (Temer), leg56 (Bolsonaro, all).
Three outcomes: gov, pres, centrao.

For each cell: full PLIV-DML benchmark + CausalIVForest with no subsampling.
"""

import sys, logging, warnings, time
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as _CFG
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")
np.random.seed(42)

PANEL = Path(_CFG.PANEL)
RESULTS = Path(_CFG.RESULTS)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("cf3")


CENTRAO = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE", "UNIAO", "PTB",
            "AVANTE", "PSD", "MDB"}
POL_FEATS = ["pol_paper_euclidean_mds", "pol_paper_forte_mds", "pol_paper_fraca_mds"]


def attach_pol_paper(df):
    POL_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name in ["euclidean", "forte", "fraca"]:
        p = POL_DIR / f"average_mds_distances_{name}.csv"
        if not p.exists(): continue
        pol = pd.read_csv(p)
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        col = f"pol_paper_{name}_mds"
        df[col] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col] = r["Euclidiana_MDS"]
    return df


def attach_centrao(df):
    """Loads y_centrao_orient (EX-ANTE) from panel_y_centrao_orient.csv
    rather than constructing the ex-post vote-majority version, which would
    be endogenous (the deputy's own vote contributes to the majority)."""
    yc_path = PANEL / "panel_y_centrao_orient.csv"
    if not yc_path.exists():
        log.warning(f"  {yc_path} missing -- y_centrao set to NaN")
        df = df.copy()
        df["y_centrao"] = np.nan
        return df
    yc = pd.read_csv(yc_path, sep=";",
                     usecols=["idDeputado", "idVotacao", "y_centrao_orient"],
                     dtype={"idDeputado": str, "idVotacao": str})
    df = df.copy()
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["idVotacao"] = df["idVotacao"].astype(str)
    df = df.merge(yc, on=["idDeputado", "idVotacao"], how="left")
    df["y_centrao"] = df["y_centrao_orient"]
    return df


def attach_y_pres(df):
    pres_file = PANEL / "panel_y_pres_camara_orient.csv"
    if pres_file.exists():
        ypres = pd.read_csv(pres_file, sep=";",
                             usecols=["idDeputado", "idVotacao", "y_pres_camara_orient"],
                             dtype={"idDeputado": str, "idVotacao": str})
        ypres["idDeputado"] = ypres["idDeputado"].astype(str)
        ypres["idVotacao"] = ypres["idVotacao"].astype(str)
        df = df.copy()
        df["idDeputado"] = df["idDeputado"].astype(str)
        df["idVotacao"] = df["idVotacao"].astype(str)
        df = df.merge(ypres, on=["idDeputado", "idVotacao"], how="left")
        df["y_pres"] = df["y_pres_camara_orient"]
    else:
        df["y_pres"] = np.nan
    return df


def get_control_cols(df):
    candidates = U2.get_clean_full_controls(df)
    EXCLUDE = {
        "alinhamento", "emenda_M", "idDeputado", "idVotacao", "voto", "siglaPartido",
        "y_centrao", "y_pres", "y_pres_camara_orient", "y_gov",
        "T_rp6_pre60", "T_rp6_pre60_M", "T_rp6_pix_pre60", "T_rp6_pix_pre60_M",
        "T_rp7_pre60", "T_rp7_pre60_M", "T_rp8_pre60", "T_rp8_pre60_M",
        "T_rp9_pre60", "T_rp9_pre60_M", "T_rp9_imputed_pre60", "T_rp9_imputed_pre60_M",
        "d_rp9_solicitante", "share_pork_opaco", "share_rp9",
        "share_pix", "n_apoiamentos_opaco",
        "iv_q4_no_ytd", "iv_ytd_exec_pct", "iv_q4_dummy", "iv_days_to_dec31",
    }
    ctrl = [c for c in candidates if c not in EXCLUDE
             and c in df.columns
             and df[c].notna().mean() > 0.5
             and df[c].nunique() > 1
             and pd.api.types.is_numeric_dtype(df[c])]
    return ctrl


def prepare_sub(df, outcome_col):
    iv_cols = [c for c in ["iv_q4_no_ytd", "iv_ytd_exec_pct"] if c in df.columns]
    pol_cols = [c for c in POL_FEATS if c in df.columns]
    ctrl = get_control_cols(df)
    keep = [outcome_col, "emenda_M", "idDeputado"] + iv_cols + pol_cols + ctrl
    keep = list(dict.fromkeys(keep))
    sub = df[keep].dropna().copy()

    from sklearn.linear_model import LinearRegression
    fs = LinearRegression()
    fs.fit(sub[iv_cols].values, sub["emenda_M"].values)
    sub["z_proj"] = fs.predict(sub[iv_cols].values)
    fs_r2 = fs.score(sub[iv_cols].values, sub["emenda_M"].values)
    return sub, iv_cols, pol_cols, ctrl, fs_r2


def demean(sub, outcome_col, pol_cols, ctrl):
    out = sub.copy()
    cols = list(dict.fromkeys(
        [outcome_col, "emenda_M", "z_proj"] + pol_cols + ctrl))
    cols = [c for c in cols if c in out.columns]
    means = out.groupby("idDeputado")[cols].transform("mean")
    for c in cols:
        out[c] = out[c] - means[c]
    return out


def run_forest(sub_dm, outcome_col, pol_cols, ctrl, n_estimators=500,
                cap_n=200000):
    """Run CausalIVForest. Subsample if needed."""
    from econml.grf import CausalIVForest
    if len(sub_dm) > cap_n:
        sub_dm = sub_dm.sample(n=cap_n, random_state=42).reset_index(drop=True)
        log.info(f"  subsampled to {len(sub_dm):,}")
    log.info(f"  fitting forest (n_est={n_estimators}, n={len(sub_dm):,}, "
             f"min_leaf={max(200, len(sub_dm)//500)})")
    t0 = time.time()
    Y = sub_dm[outcome_col].values.reshape(-1, 1)
    T = sub_dm["emenda_M"].values.reshape(-1, 1)
    Z = sub_dm["z_proj"].values.reshape(-1, 1)
    X = sub_dm[pol_cols + ctrl].values

    f = CausalIVForest(
        n_estimators=n_estimators,
        min_samples_leaf=max(200, len(sub_dm) // 500),
        max_depth=10,
        random_state=42, n_jobs=-1, honest=True,
    )
    f.fit(X, T, Y, Z=Z)
    log.info(f"  done ({time.time()-t0:.0f}s)")
    cate = f.predict(X).ravel()
    p1, p99 = np.percentile(cate, [1, 99])
    cate_w = np.clip(cate, p1, p99)
    return f, cate_w, sub_dm


def run_pliv_benchmark(sub_orig, outcome_col, iv_cols, ctrl):
    """Quick PLIV-DML benchmark on the same sub-sample."""
    try:
        from doubleml import DoubleMLPLIV, DoubleMLClusterData
        from sklearn.linear_model import ElasticNetCV
    except Exception as e:
        log.warning(f"  doubleml unavailable: {e}")
        return None

    df_l = sub_orig.copy()
    valid_ctrl = [c for c in ctrl if df_l[c].notna().mean() > 0.5
                    and df_l[c].nunique() > 1]
    # Drop NaN rows
    needed = ["idDeputado", outcome_col, "emenda_M"] + iv_cols + valid_ctrl
    df_l = df_l[needed].dropna().copy()
    df_l["idDeputado_int"] = df_l["idDeputado"].astype("category").cat.codes

    # Within-deputy demean for outcome + treatment
    for c in [outcome_col, "emenda_M"] + valid_ctrl:
        df_l[c] = df_l[c] - df_l.groupby("idDeputado_int")[c].transform("mean")

    log.info(f"  [PLIV bench] n={len(df_l):,}, ctrl={len(valid_ctrl)}")
    try:
        data = DoubleMLClusterData(
            df_l, y_col=outcome_col,
            d_cols=["emenda_M"], z_cols=iv_cols,
            x_cols=valid_ctrl,
            cluster_cols="idDeputado_int",
        )
        ml_l = ElasticNetCV(cv=3, max_iter=2000, n_jobs=-1)
        ml_m = ElasticNetCV(cv=3, max_iter=2000, n_jobs=-1)
        ml_r = ElasticNetCV(cv=3, max_iter=2000, n_jobs=-1)
        dml = DoubleMLPLIV(data, ml_l=ml_l, ml_m=ml_m, ml_r=ml_r,
                              n_folds=3, n_rep=1, score="partialling out")
        t0 = time.time()
        dml.fit()
        std_T = df_l["emenda_M"].std()
        theta_sd = dml.coef[0]
        pp = theta_sd * std_T * 100  # convert to pp/R$M (T in R$M)
        ci = dml.confint(level=0.95)
        ci_pp = (ci.iloc[0, 0] * std_T * 100, ci.iloc[0, 1] * std_T * 100)
        log.info(f"  [PLIV bench] theta_sd={theta_sd:+.5f} | pp/R$M={pp:+.3f}  "
                 f"CI95=[{ci_pp[0]:+.3f},{ci_pp[1]:+.3f}]  "
                 f"({time.time()-t0:.0f}s)")
        return {"pp": pp, "ci_lo": ci_pp[0], "ci_hi": ci_pp[1]}
    except Exception as e:
        log.error(f"  [PLIV bench] failed: {e}")
        return None


def main():
    log.info("=" * 70)
    log.info("Causal Forest IV BY LEGISLATURE (Leg 55 vs Leg 56), 3 outcomes")
    log.info("=" * 70)

    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["data"] = pd.to_datetime(df["data"])
    df = attach_pol_paper(df)
    df = attach_centrao(df)
    df = attach_y_pres(df)
    df["y_gov"] = df["alinhamento"]

    log.info(f"panel: {len(df):,} rows")

    samples = {
        "leg55": df["idLegislatura"] == 55,
        "leg56": df["idLegislatura"] == 56,
    }
    outcomes = [("gov", "y_gov"), ("pres", "y_pres"), ("centrao", "y_centrao")]

    rows = []
    for sample_name, mask in samples.items():
        df_s = df[mask].copy()
        log.info(f"\n{'='*70}\nSUB-SAMPLE: {sample_name}  n_total={len(df_s):,}\n{'='*70}")

        for tag, outcol in outcomes:
            log.info(f"\n  --- outcome: {tag} ({outcol}) ---")
            sub_o = df_s.dropna(subset=[outcol]).copy()
            if len(sub_o) < 15000:
                log.warning(f"  sample too small (n={len(sub_o)}), skipping")
                continue

            sub, iv_cols, pol_cols, ctrl, fs_r2 = prepare_sub(sub_o, outcol)
            log.info(f"  n_pre_dropna={len(sub_o):,}  n_post={len(sub):,}  "
                     f"first-stage R^2={fs_r2:.4f}  ctrl={len(ctrl)}")

            # 1. PLIV-DML benchmark
            pliv_res = run_pliv_benchmark(sub, outcol, iv_cols, ctrl)

            # 2. Causal IV Forest (with within-deputy demean)
            sub_dm = demean(sub, outcol, pol_cols, ctrl)
            try:
                _, cate, sub_dm_used = run_forest(
                    sub_dm, outcol, pol_cols, ctrl,
                    n_estimators=500, cap_n=200000)
                cate_mean = cate.mean() * 100
                cate_p10, cate_p50, cate_p90 = [np.percentile(cate, q) * 100
                                                  for q in (10, 50, 90)]
                # Bootstrap CI on the mean of CATE
                boot = []
                for _ in range(200):
                    idx = np.random.choice(len(cate), len(cate), replace=True)
                    boot.append(cate[idx].mean() * 100)
                ci_lo_b, ci_hi_b = np.percentile(boot, [2.5, 97.5])
            except Exception as e:
                log.error(f"  forest failed: {e}")
                cate_mean = cate_p10 = cate_p50 = cate_p90 = ci_lo_b = ci_hi_b = np.nan
                continue

            rows.append({
                "sample": sample_name, "outcome": tag,
                "n": len(sub_dm_used),
                "fs_R2": round(fs_r2, 4),
                "PLIV_pp":    round(pliv_res["pp"], 3) if pliv_res else None,
                "PLIV_lo":    round(pliv_res["ci_lo"], 3) if pliv_res else None,
                "PLIV_hi":    round(pliv_res["ci_hi"], 3) if pliv_res else None,
                "Forest_mean":  round(cate_mean, 3),
                "Forest_p10":   round(cate_p10, 3),
                "Forest_p50":   round(cate_p50, 3),
                "Forest_p90":   round(cate_p90, 3),
                "Forest_boot_lo": round(ci_lo_b, 3),
                "Forest_boot_hi": round(ci_hi_b, 3),
            })
            log.info(f"  --> PLIV theta={pliv_res['pp'] if pliv_res else 'NA'}, "
                     f"Forest mean={cate_mean:+.3f} median={cate_p50:+.3f}")

    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "n3_cforest_by_leg.csv", sep=";", index=False)
    log.info(f"\nSaved {RESULTS / 'n3_cforest_by_leg.csv'}")
    print()
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
