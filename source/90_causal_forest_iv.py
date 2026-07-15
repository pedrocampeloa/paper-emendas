"""
90_causal_forest_iv.py
-----------------------
Causal Forest IV (Athey-Tibshirani-Wager 2019) for heterogeneous treatment
effects, replicating the main result and adding a non-parametric robustness layer.

Three outcomes:
  Y_gov     -- alignment with Executive (main paper)
  Y_pres    -- alignment with party of Chamber president (Section 5.2)
  Y_centrao -- alignment with the Centrao bloc majority

Estimands:
  1. ATE via DMLIV (parametric DML-IV, comparable to PLIV-DML baseline)
  2. CATE(X) via CausalIVForest with X = (polarization, deputy controls)
  3. Best Linear Predictor (BLP) of CATE on polarization features
     (Chernozhukov-Demirer-Duflo-Fernandez-Val 2018)

Polarization features used for CATE projection:
  - pol_paper_euclidean_mds
  - pol_paper_forte_mds (Strong Divergence)
  - pol_paper_fraca_mds (Weak Divergence)

Plus standard controls so the forest can pick up other heterogeneity.

Outputs:
  results/n3_cforest_ate.csv             (ATE comparison: PLIV-DML vs DMLIV vs forest)
  results/n3_cforest_blp_<outcome>.csv   (BLP of CATE on polarization)
  results/n3_cforest_cate_<outcome>.csv  (point-wise CATE for plotting)
  docs/figs/fig_cforest_cate_<outcome>.pdf  (CATE-vs-polarization curve, all 3 outcomes)
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
FIGS = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-emendas/docs/figs")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("cf")


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
    """Loads y_centrao_orient (EX-ANTE) from panel_y_centrao_orient.csv.
    The ex-ante version uses the published orientations of the 9 Centrao
    parties (majority among Sim/Nao/Obstrucao) rather than the realized
    vote majority, avoiding the endogeneity of having the deputy's own
    vote contribute to the alignment target."""
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
    """Builds y_pres = alignment with party of Chamber president orientation.
       Maps: DEM under Maia (2016-07 to 2021-01), PP under Lira (2021-02 onward).
       Uses panel_y_pres_camara_orient if available, else fallback."""
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
        log.warning(f"  panel_y_pres_camara_orient.csv not found - y_pres NaN")
        df["y_pres"] = np.nan
    return df


def get_control_cols(df):
    """Select a leaner control set suitable for forest: numeric, low-correlation."""
    candidates = U2.get_clean_full_controls(df)
    EXCLUDE = {
        "alinhamento", "emenda_M", "idDeputado", "idVotacao", "voto", "siglaPartido",
        "y_centrao", "y_pres", "y_pres_camara_orient",
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
    """Drop NaNs in core columns + IV projection (no demeaning here -- DMLIV
       handles it via W, and the forest gets demeaned data only in run_causal)."""
    iv_candidates = ["iv_q4_no_ytd", "iv_ytd_exec_pct"]
    iv_cols = [c for c in iv_candidates if c in df.columns]
    log.info(f"  IVs (raw): {iv_cols}")

    pol_cols = [c for c in POL_FEATS if c in df.columns]
    ctrl = get_control_cols(df)

    keep = [outcome_col, "emenda_M", "idDeputado"] + iv_cols + pol_cols + ctrl
    keep = list(dict.fromkeys(keep))
    sub = df[keep].dropna().copy()
    sub["idDeputado_int"] = sub["idDeputado"].astype("category").cat.codes

    # ---- IV projection: project T onto IVs (scalar instrument for forest) ----
    from sklearn.linear_model import LinearRegression
    fs = LinearRegression()
    fs.fit(sub[iv_cols].values, sub["emenda_M"].values)
    sub["z_proj"] = fs.predict(sub[iv_cols].values)
    log.info(f"  first-stage R^2 = {fs.score(sub[iv_cols].values, sub['emenda_M'].values):.4f}")
    log.info(f"  IV coefs: {dict(zip(iv_cols, [round(float(c), 6) for c in fs.coef_]))}")

    log.info(f"  n={len(sub):,}, ctrl={len(ctrl)}, pol_feats={len(pol_cols)}")
    return sub, iv_cols, pol_cols, ctrl


def demean_for_forest(sub, outcome_col, iv_cols, pol_cols, ctrl):
    """Apply within-deputy demeaning ONLY to the data fed to the forest."""
    out = sub.copy()
    cols_to_demean = list(dict.fromkeys(
        [outcome_col, "emenda_M", "z_proj"] + pol_cols + ctrl
    ))
    cols_to_demean = [c for c in cols_to_demean if c in out.columns]
    means = out.groupby("idDeputado")[cols_to_demean].transform("mean")
    for c in cols_to_demean:
        out[c] = out[c] - means[c]
    return out


def run_dmliv(sub, outcome_col, iv_cols, pol_cols, ctrl):
    """Parametric DMLIV (linear treatment, no heterogeneity) as benchmark."""
    from econml.iv.dml import DMLIV
    from sklearn.linear_model import LassoCV, LogisticRegressionCV

    log.info(f"  [DMLIV] fitting...")
    t0 = time.time()
    Y = sub[outcome_col].values
    T = sub["emenda_M"].values
    Z = sub[iv_cols].values
    X = sub[pol_cols].values
    W = sub[ctrl].values

    # Models for nuisance
    model_y_xw = LassoCV(cv=3, max_iter=2000)
    model_t_xw = LassoCV(cv=3, max_iter=2000)
    model_z_xw = LassoCV(cv=3, max_iter=2000)

    dmliv = DMLIV(
        model_y_xw=model_y_xw,
        model_t_xw=model_t_xw,
        model_t_xwz=model_t_xw,
        model_final=LassoCV(cv=3, max_iter=2000),
        discrete_treatment=False,
        discrete_instrument=False,
        cv=3,
        random_state=42,
    )
    dmliv.fit(Y, T, Z=Z, X=X, W=W)
    log.info(f"  [DMLIV] done ({time.time()-t0:.0f}s)")

    # ATE estimate (constant marginal effect)
    ate = float(dmliv.const_marginal_effect(X).mean())
    log.info(f"  ATE (DMLIV) = {ate*100:+.4f} pp/R$1M")
    return dmliv, ate


def run_causal_iv_forest(sub_raw, outcome_col, iv_cols, pol_cols, ctrl,
                            n_estimators=500):
    """Causal IV Forest (Athey-Tibshirani-Wager 2019).
       Uses z_proj as scalar IV; data demeaned by deputy beforehand."""
    from econml.grf import CausalIVForest

    # Demean within-deputy
    sub = demean_for_forest(sub_raw, outcome_col, iv_cols, pol_cols, ctrl)

    log.info(f"  [CausalIVForest] fitting with n_estimators={n_estimators}, "
             f"min_samples_leaf=200...")
    t0 = time.time()
    Y = sub[outcome_col].values.reshape(-1, 1)
    T = sub["emenda_M"].values.reshape(-1, 1)
    Z = sub["z_proj"].values.reshape(-1, 1)
    X = sub[pol_cols + ctrl].values

    forest = CausalIVForest(
        n_estimators=n_estimators,
        min_samples_leaf=200,      # larger leaves = less overfitting
        max_depth=10,              # cap depth to prevent extreme CATE values
        random_state=42,
        n_jobs=-1,
        honest=True,
    )
    forest.fit(X, T, Y, Z=Z)
    log.info(f"  [CausalIVForest] fit done ({time.time()-t0:.0f}s)")

    # Predict pointwise CATE
    cate = forest.predict(X).ravel()
    # Winsorize the CATE at p1/p99 to handle extreme outliers
    p1, p99 = np.percentile(cate, [1, 99])
    cate_w = np.clip(cate, p1, p99)
    log.info(f"  CATE (raw)        mean={cate.mean()*100:+.4f}  std={cate.std()*100:+.4f}")
    log.info(f"  CATE (winsorized) mean={cate_w.mean()*100:+.4f}  std={cate_w.std()*100:+.4f}")
    log.info(f"  CATE quantiles (winsor) p10={np.percentile(cate_w, 10)*100:+.4f}  "
             f"p50={np.percentile(cate_w, 50)*100:+.4f}  p90={np.percentile(cate_w, 90)*100:+.4f}")

    return forest, cate_w, sub


def best_linear_predictor(cate, pol_features, pol_names, cluster=None):
    """Best Linear Predictor of CATE on polarization features (Chernozhukov et al. 2018).
       Tests H0: CATE is constant. Reject => significant heterogeneity."""
    import statsmodels.api as sm
    X = pol_features
    X = sm.add_constant(X)
    if cluster is not None:
        m = sm.OLS(cate, X).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    else:
        m = sm.OLS(cate, X).fit(cov_type="HC1")
    params = np.asarray(m.params)
    bse    = np.asarray(m.bse)
    tval   = np.asarray(m.tvalues)
    pval   = np.asarray(m.pvalues)
    rows = []
    for i, name in enumerate(["const"] + list(pol_names)):
        rows.append({
            "var": name,
            "coef":  round(float(params[i]), 6),
            "se":    round(float(bse[i]),    6),
            "tstat": round(float(tval[i]),   3),
            "pval":  round(float(pval[i]),   6),
        })
    return pd.DataFrame(rows), m


def main():
    log.info("=" * 70)
    log.info("Causal Forest IV: heterogeneous effects, 3 outcomes")
    log.info("=" * 70)

    log.info("[1] Loading panel + outcomes + polarization")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df = attach_pol_paper(df)
    df = attach_centrao(df)
    df = attach_y_pres(df)

    df["y_gov"] = df["alinhamento"]
    log.info(f"  panel: {len(df):,} rows")
    log.info(f"  y_gov non-null:     {df['y_gov'].notna().sum():,}")
    log.info(f"  y_pres non-null:    {df['y_pres'].notna().sum():,}")
    log.info(f"  y_centrao non-null: {df['y_centrao'].notna().sum():,}")

    outcomes = [("gov", "y_gov"), ("pres", "y_pres"), ("centrao", "y_centrao")]

    all_ate = []
    all_blp = []
    cate_records = []

    for tag, outcol in outcomes:
        log.info(f"\n{'='*70}")
        log.info(f"OUTCOME: {tag}  ({outcol})")
        log.info(f"{'='*70}")

        sub = df.dropna(subset=[outcol]).copy()
        sub, iv_cols, pol_cols, ctrl = prepare_sub(sub, outcol)
        if len(sub) < 20000:
            log.warning(f"  small sample, skipping forest")
            continue

        # 1. DMLIV ATE (sanity)
        try:
            _, ate = run_dmliv(sub, outcol, iv_cols, pol_cols, ctrl)
            all_ate.append({"outcome": tag, "method": "DMLIV", "ate_pp": ate*100, "n": len(sub)})
        except Exception as e:
            log.error(f"  DMLIV failed: {e}")

        # 2. CausalIVForest
        # NOTE: forest training scales O(n_est * n log n). With n>500k, we sample
        # for tractability and keep cluster-respecting subsample.
        n_max = 80000
        if len(sub) > n_max:
            # cluster-aware subsample: pick all obs from a sample of deputies
            n_dep = sub["idDeputado"].nunique()
            sub_dep = (sub.drop_duplicates("idDeputado")
                       .sample(n=min(n_dep, max(100, n_max // 100)),
                               random_state=42)["idDeputado"])
            sub_f = sub[sub["idDeputado"].isin(sub_dep)].copy()
            if len(sub_f) > n_max:
                sub_f = sub_f.sample(n=n_max, random_state=42)
            log.info(f"  subsampled to {len(sub_f):,} (from {len(sub):,}) for forest tractability")
        else:
            sub_f = sub

        try:
            forest, cate, sub_dm = run_causal_iv_forest(
                sub_f, outcol, iv_cols, pol_cols, ctrl, n_estimators=300)
            all_ate.append({"outcome": tag, "method": "CausalIVForest",
                            "ate_pp": cate.mean()*100, "n": len(sub_f)})

            # 3. BLP on polarization features (use the demeaned panel)
            pol_mat = sub_dm[pol_cols].values
            blp_df, blp_model = best_linear_predictor(
                cate, pol_mat, pol_cols,
                cluster=sub_f["idDeputado"].values)
            blp_df["outcome"] = tag
            log.info(f"\n  BLP of CATE on polarization:")
            log.info("\n" + blp_df.to_string(index=False))
            all_blp.append(blp_df)

            # 4. Record CATE for plotting (downsample for figure).
            # Use ORIGINAL (non-demeaned) polarization values for plotting,
            # so the axis is interpretable as the level of polarization.
            sub_orig = sub_f.reset_index(drop=True)
            sample_idx = np.random.choice(len(cate), min(5000, len(cate)),
                                            replace=False)
            for i in sample_idx:
                row = sub_orig.iloc[i]
                cate_records.append({
                    "outcome": tag,
                    "cate_pp": cate[i] * 100,
                    "pol_euclidean": row.get("pol_paper_euclidean_mds", np.nan),
                    "pol_forte": row.get("pol_paper_forte_mds", np.nan),
                    "pol_fraca": row.get("pol_paper_fraca_mds", np.nan),
                })

        except Exception as e:
            log.error(f"  CausalIVForest failed: {e}")
            import traceback; traceback.print_exc()

    # Save
    ate_df = pd.DataFrame(all_ate)
    ate_df.to_csv(RESULTS / "n3_cforest_ate.csv", sep=";", index=False)
    log.info(f"\nSaved {RESULTS/'n3_cforest_ate.csv'}")
    print(ate_df.to_string(index=False))

    if all_blp:
        blp_full = pd.concat(all_blp, ignore_index=True)
        blp_full.to_csv(RESULTS / "n3_cforest_blp.csv", sep=";", index=False)
        log.info(f"Saved {RESULTS/'n3_cforest_blp.csv'}")
        print("\nBLP results:")
        print(blp_full.to_string(index=False))

    if cate_records:
        cate_df = pd.DataFrame(cate_records)
        cate_df.to_csv(RESULTS / "n3_cforest_cate.csv", sep=";", index=False)
        log.info(f"Saved {RESULTS/'n3_cforest_cate.csv'}")


if __name__ == "__main__":
    main()
