"""
92_cforest_by_subperiod.py
----------------------------
Causal Forest IV by sub-period: Legislature and Chamber-president cuts.

Sub-samples:
  - leg55           (Temer presidency, Cunha+Maia chambers)
  - leg56_maia      (Bolsonaro x Maia chamber, Jan 2019 - Jan 2021)
  - leg56_lira      (Bolsonaro x Lira chamber, Feb 2021 - Dec 2022)

Three outcomes per sub-sample:
  - y_gov     (Executive alignment)
  - y_pres    (Chamber president's party alignment)
  - y_centrao (Centrao bloc majority alignment)

For each (subsample, outcome) cell we run:
  1. CausalIVForest with projected IV (1-dim) and within-deputy demeaning
  2. Best Linear Predictor (BLP) of CATE on polarization features

Output:
  results/n3_cforest_subperiod_ate.csv
  results/n3_cforest_subperiod_blp.csv
  results/n3_cforest_subperiod_cate.csv
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
log = logging.getLogger("cf2")


CENTRAO = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE", "UNIAO", "PTB",
            "AVANTE", "PSD", "MDB"}

POL_FEATS = ["pol_paper_euclidean_mds", "pol_paper_forte_mds", "pol_paper_fraca_mds"]

CUT_MAIA_END = pd.Timestamp("2021-02-01")


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
    df = df.copy()
    df["partido_norm"] = df["siglaPartido"].astype(str).str.upper().str.strip()
    df["is_centrao"] = df["partido_norm"].isin(CENTRAO).astype(int)
    df["voto_num"] = df["voto"].map({"Sim": 1, "Não": -1}).fillna(0)
    centrao_vote = (df[df["is_centrao"] == 1]
                    .groupby("idVotacao")["voto_num"]
                    .apply(lambda s: 1 if s.mean() > 0 else (-1 if s.mean() < 0 else 0))
                    .rename("centrao_major_vote"))
    df = df.merge(centrao_vote, on="idVotacao", how="left")
    df["y_centrao"] = (df["voto_num"] == df["centrao_major_vote"]).astype(int)
    df.loc[df["voto"].isna(), "y_centrao"] = np.nan
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

    # First-stage projection of IVs onto T (scalar instrument)
    from sklearn.linear_model import LinearRegression
    fs = LinearRegression()
    fs.fit(sub[iv_cols].values, sub["emenda_M"].values)
    sub["z_proj"] = fs.predict(sub[iv_cols].values)

    return sub, iv_cols, pol_cols, ctrl


def demean(sub, outcome_col, pol_cols, ctrl):
    out = sub.copy()
    cols = list(dict.fromkeys(
        [outcome_col, "emenda_M", "z_proj"] + pol_cols + ctrl
    ))
    cols = [c for c in cols if c in out.columns]
    means = out.groupby("idDeputado")[cols].transform("mean")
    for c in cols:
        out[c] = out[c] - means[c]
    return out


def run_forest(sub_dm, outcome_col, pol_cols, ctrl, n_estimators=300):
    from econml.grf import CausalIVForest
    log.info(f"  fitting CausalIVForest (n_est={n_estimators}, n={len(sub_dm):,})...")
    t0 = time.time()
    Y = sub_dm[outcome_col].values.reshape(-1, 1)
    T = sub_dm["emenda_M"].values.reshape(-1, 1)
    Z = sub_dm["z_proj"].values.reshape(-1, 1)
    X = sub_dm[pol_cols + ctrl].values

    f = CausalIVForest(
        n_estimators=n_estimators,
        min_samples_leaf=max(100, len(sub_dm) // 800),
        max_depth=8,
        random_state=42, n_jobs=-1, honest=True,
    )
    f.fit(X, T, Y, Z=Z)
    log.info(f"  done ({time.time()-t0:.0f}s)")
    cate = f.predict(X).ravel()
    p5, p95 = np.percentile(cate, [5, 95])
    cate_w = np.clip(cate, p5, p95)
    log.info(f"  CATE winsorized: mean={cate_w.mean()*100:+.3f}  "
             f"p10={np.percentile(cate_w, 10)*100:+.3f}  "
             f"p50={np.percentile(cate_w, 50)*100:+.3f}  "
             f"p90={np.percentile(cate_w, 90)*100:+.3f}")
    return f, cate_w


def blp(cate, pol_features, pol_names, cluster=None):
    import statsmodels.api as sm
    X = sm.add_constant(pol_features)
    if cluster is not None:
        m = sm.OLS(cate, X).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    else:
        m = sm.OLS(cate, X).fit(cov_type="HC1")
    params = np.asarray(m.params); bse = np.asarray(m.bse)
    tval = np.asarray(m.tvalues); pval = np.asarray(m.pvalues)
    rows = []
    for i, name in enumerate(["const"] + list(pol_names)):
        rows.append({
            "var": name,
            "coef":  round(float(params[i]), 6),
            "se":    round(float(bse[i]),    6),
            "tstat": round(float(tval[i]),   3),
            "pval":  round(float(pval[i]),   6),
        })
    return pd.DataFrame(rows)


def main():
    log.info("=" * 70)
    log.info("Causal Forest IV by sub-period: 3 outcomes x 3 sub-samples")
    log.info("=" * 70)

    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["data"] = pd.to_datetime(df["data"])
    df = attach_pol_paper(df)
    df = attach_centrao(df)
    df = attach_y_pres(df)
    df["y_gov"] = df["alinhamento"]

    log.info(f"panel: {len(df):,} rows")
    log.info(f"  y_gov     : {df['y_gov'].notna().sum():,}")
    log.info(f"  y_pres    : {df['y_pres'].notna().sum():,}")
    log.info(f"  y_centrao : {df['y_centrao'].notna().sum():,}")

    # Define sub-samples
    samples = {
        "leg55":      df["idLegislatura"] == 55,
        "leg56_maia": (df["idLegislatura"] == 56) & (df["data"] < CUT_MAIA_END),
        "leg56_lira": (df["idLegislatura"] == 56) & (df["data"] >= CUT_MAIA_END),
    }
    outcomes = [("gov", "y_gov"), ("pres", "y_pres"), ("centrao", "y_centrao")]

    all_ate = []; all_blp = []; cate_records = []

    for sample_name, mask in samples.items():
        df_s = df[mask].copy()
        log.info(f"\n{'='*70}\nSUB-SAMPLE: {sample_name}  n_total={len(df_s):,}\n{'='*70}")

        for tag, outcol in outcomes:
            log.info(f"\n  --- outcome: {tag} ({outcol}) ---")
            sub_o = df_s.dropna(subset=[outcol]).copy()
            if len(sub_o) < 15000:
                log.warning(f"  sample too small (n={len(sub_o)}), skipping")
                continue

            sub, iv_cols, pol_cols, ctrl = prepare_sub(sub_o, outcol)
            log.info(f"  n={len(sub):,}, ctrl={len(ctrl)}")

            # Subsample to keep forest tractable
            n_max = 80000
            if len(sub) > n_max:
                sub = sub.sample(n=n_max, random_state=42).copy()
                log.info(f"  subsampled to {len(sub):,}")

            sub_dm = demean(sub, outcol, pol_cols, ctrl)

            try:
                forest, cate = run_forest(sub_dm, outcol, pol_cols, ctrl,
                                          n_estimators=300)
            except Exception as e:
                log.error(f"  forest failed: {e}")
                continue

            all_ate.append({
                "sample": sample_name, "outcome": tag,
                "ate_pp": cate.mean() * 100,
                "p10_pp": np.percentile(cate, 10) * 100,
                "p50_pp": np.percentile(cate, 50) * 100,
                "p90_pp": np.percentile(cate, 90) * 100,
                "n": len(sub),
            })

            pol_mat = sub_dm[pol_cols].values
            blp_df = blp(cate, pol_mat, pol_cols, cluster=sub["idDeputado"].values)
            blp_df["sample"] = sample_name
            blp_df["outcome"] = tag
            log.info(f"  BLP:")
            log.info("\n" + blp_df.to_string(index=False))
            all_blp.append(blp_df)

            # Save CATE for plotting
            sub_orig = sub.reset_index(drop=True)
            idx = np.random.choice(len(cate), min(5000, len(cate)), replace=False)
            for i in idx:
                row = sub_orig.iloc[i]
                cate_records.append({
                    "sample": sample_name, "outcome": tag,
                    "cate_pp": cate[i] * 100,
                    "pol_euclidean": row.get("pol_paper_euclidean_mds", np.nan),
                    "pol_forte": row.get("pol_paper_forte_mds", np.nan),
                    "pol_fraca": row.get("pol_paper_fraca_mds", np.nan),
                })

    # Save
    pd.DataFrame(all_ate).to_csv(RESULTS / "n3_cforest_subperiod_ate.csv", sep=";", index=False)
    log.info(f"saved {RESULTS / 'n3_cforest_subperiod_ate.csv'}")
    print()
    print(pd.DataFrame(all_ate).to_string(index=False))

    if all_blp:
        blp_full = pd.concat(all_blp, ignore_index=True)
        blp_full.to_csv(RESULTS / "n3_cforest_subperiod_blp.csv", sep=";", index=False)
        log.info(f"saved {RESULTS / 'n3_cforest_subperiod_blp.csv'}")
        print()
        print(blp_full.to_string(index=False))

    if cate_records:
        pd.DataFrame(cate_records).to_csv(
            RESULTS / "n3_cforest_subperiod_cate.csv", sep=";", index=False)
        log.info(f"saved {RESULTS / 'n3_cforest_subperiod_cate.csv'}")


if __name__ == "__main__":
    main()
