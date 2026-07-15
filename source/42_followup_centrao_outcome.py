"""
42_followup_centrao_outcome.py
-------------------------------
Refaz T1, T2, T3, T4 com y = alinhamento com Centrao (em vez de alinhamento
com governo). Espelha 41_finish_followup.py com a unica diferenca de
substituir o outcome.

Estrategia: contruir y_centrao para cada (idDeputado, idVotacao) a partir do
voto majoritario do Centrao em cada votacao, depois sobrescrever a coluna
'alinhamento' no painel temporariamente. Como _utils_v2 le C.TARGET=alinhamento,
basta substituir o conteudo.

Outputs (todos com sufixo _centrao):
    results/followup_centrao_t1_iv_with_rp9_controls.csv
    results/followup_centrao_t2_het_rp9_exposure.csv
    results/followup_centrao_t3_mediation_pix.csv
    results/followup_centrao_t4_tercis_by_leg.csv

Roda T3 (rapido), T2 (rapido), T4 (longo), T1 (longo) nessa ordem.

n_folds=2, n_reps=1.
"""

import logging
import sys
import warnings
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("centrao")

POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
INTERIM = Path(C.PANEL)
RESULTS = Path(C.RESULTS)

CENTRAO_PARTIES = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE",
                   "UNIAO", "PTB", "AVANTE", "PSD", "MDB"}


def check(name, cond, *details):
    if cond:
        log.info(f"  [OK] {name}")
    else:
        log.error(f"  [FAIL] {name}")
        for d in details: log.error(f"         {d}")
        raise AssertionError(f"Safety check failed: {name}")


def warn(name, cond, *details):
    if not cond:
        log.warning(f"  [WARN] {name}")
        for d in details: log.warning(f"         {d}")


def attach_pol_paper(df):
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name in ["euclidean", "forte", "fraca"]:
        path = POL_PAPER_DIR / f"average_mds_distances_{name}.csv"
        if not path.exists(): continue
        pol = pd.read_csv(path)
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        col = f"pol_paper_{name}_mds"
        df[col] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col] = r["Euclidiana_MDS"]
    return df


def load_and_attach_centrao(df_with_party):
    """Constroi y_centrao para cada (idDeputado, idVotacao).

    df_with_party: precisa ter idVotacao, voto, siglaPartido.
    """
    log.info("Building y_centrao from per-vote Centrao majority")
    df = df_with_party.copy()
    df["d_centrao_party"] = df["siglaPartido"].astype(str).str.upper().str.strip().isin(CENTRAO_PARTIES).astype(int)

    cen_votes = df[df["d_centrao_party"] == 1]
    log.info(f"  Centrao votes: {len(cen_votes):,}")

    def majority(s):
        vc = s.value_counts()
        return vc.index[0] if not vc.empty else np.nan

    cen_major = cen_votes.groupby("idVotacao")["voto"].apply(majority).reset_index()
    cen_major.columns = ["idVotacao", "voto_centrao_major"]
    log.info(f"  Centrao majority per vote: {len(cen_major):,}")

    df = df.merge(cen_major, on="idVotacao", how="left")
    df["y_centrao"] = (df["voto"] == df["voto_centrao_major"]).astype(int)
    df.loc[df["voto_centrao_major"].isna(), "y_centrao"] = np.nan

    n_valid = df["y_centrao"].notna().sum()
    log.info(f"  y_centrao non-null: {n_valid:,} ({100*n_valid/len(df):.1f}%)")
    log.info(f"  y_centrao mean (Leg 55): {df[df['idLegislatura']==55]['y_centrao'].mean():.3f}")
    log.info(f"  y_centrao mean (Leg 56): {df[df['idLegislatura']==56]['y_centrao'].mean():.3f}")
    return df


def load_augmented_panel_centrao():
    log.info("\n" + "="*70)
    log.info("STEP 0: Loading augmented panel with y_centrao")
    log.info("="*70)

    log.info("[0.1] Base panel")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    check("base loaded", len(df) > 0)

    # Precisa de voto, siglaPartido — recarregar de panel_features
    log.info("[0.2] Loading voto + siglaPartido from panel_features")
    pf = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "idVotacao", "voto", "siglaPartido"],
                     dtype=str, low_memory=False)
    pf["idDeputado"] = pf["idDeputado"].astype(str)
    df["idDeputado"] = df["idDeputado"].astype(str)
    # voto/siglaPartido podem ja existir; se sim, droppar antes do merge
    for c in ["voto", "siglaPartido"]:
        if c in df.columns:
            df = df.drop(columns=[c])
    n_before = len(df)
    df = df.merge(pf, on=["idDeputado", "idVotacao"], how="left")
    check("voto/partido merge preserved rows", len(df) == n_before)

    log.info("[0.3] Building y_centrao")
    df = load_and_attach_centrao(df)

    # Substituir alinhamento por y_centrao (somente nas linhas com y_centrao valido)
    log.info("[0.4] Replacing alinhamento with y_centrao (only where valid)")
    n_before_drop = len(df)
    df = df.dropna(subset=["y_centrao"])
    log.info(f"  dropped {n_before_drop - len(df):,} rows without Centrao majority")
    df["alinhamento_gov_orig"] = df["alinhamento"].copy()
    df["alinhamento"] = df["y_centrao"].astype(int)
    check("alinhamento is binary after replacement", set(df["alinhamento"].unique()) <= {0, 1})

    log.info("[0.5] Merging multi-RP + proxies + MDS")
    mr = pd.read_csv(INTERIM / "panel_emendas_pre_multi_rp.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    mr["idDeputado"] = mr["idDeputado"].astype(str)
    mr_cols = ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60", "T_rp9_imputed_pre60"]
    df = df.merge(mr[["idDeputado", "idVotacao"] + mr_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in mr_cols:
        df[c] = df[c].fillna(0)
        df[c + "_M"] = df[c] / 1e6

    px = pd.read_csv(INTERIM / "panel_secret_budget_proxies.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    px["idDeputado"] = px["idDeputado"].astype(str)
    px_cols = ["d_rp9_solicitante", "share_pork_opaco", "share_rp9",
               "share_pix", "n_apoiamentos_opaco"]
    df = df.merge(px[["idDeputado", "idVotacao"] + px_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in px_cols:
        df[c] = df[c].fillna(0)

    df = attach_pol_paper(df)
    log.info(f"  final panel (y_centrao): {len(df):,} rows x {len(df.columns)} cols")
    return df


def safe_pliv(df_l, controls, label):
    log.info(f"\n  --> running PLIV: {label}")
    log.info(f"      n_obs = {len(df_l):,}, n_clusters = {df_l['idDeputado'].nunique()}")
    if len(df_l) < 5000:
        log.warning(f"      [WARN] too small")
        return None
    controls = list(dict.fromkeys(controls))
    bad = [c for c in controls if c in ("alinhamento", "emenda_M", "idDeputado",
                                          "y_centrao", "alinhamento_gov_orig",
                                          "voto", "voto_centrao_major", "d_centrao_party")]
    if bad:
        controls = [c for c in controls if c not in bad]
    valid_ctrl = [c for c in controls if c in df_l.columns
                  and df_l[c].notna().mean() > 0.5
                  and df_l[c].nunique() > 1]
    log.info(f"      valid controls: {len(valid_ctrl)} of {len(controls)}")
    try:
        res = U2.run_pliv_main(df_l, controls=valid_ctrl, iv_set="backlog",
                                n_folds=2, n_reps=1)
        if res is None:
            log.warning("      [WARN] None")
            return None
        log.info(f"      [OK] theta = {res.get('pp_per_unit'):.4f} pp/R$M, pval = {res.get('pval'):.4f}")
        return res
    except Exception as e:
        log.error(f"      [FAIL] {e}")
        log.error(traceback.format_exc())
        return None


def t3_mediation_pix(df):
    log.info("\n" + "="*70)
    log.info("T3 (Centrao): ABS mediation with share_pix")
    log.info("="*70)
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant

    rows = []
    for leg_label, leg in [("pooled", None), ("leg55", 55), ("leg56", 56)]:
        df_l = df.copy() if leg is None else df[df["idLegislatura"] == leg].copy()
        df_l = df_l.dropna(subset=["alinhamento", "emenda_M", "share_pix"])
        if len(df_l) < 5000:
            continue
        T = df_l["emenda_M"]
        M = df_l["share_pix"]
        Y = df_l["alinhamento"]
        X1 = add_constant(T)
        m1 = OLS(M, X1).fit(cov_type="cluster",
                              cov_kwds={"groups": df_l["idDeputado"]})
        theta_TM = m1.params.iloc[1]

        X2 = add_constant(pd.DataFrame({"T": T, "M": M}))
        m2 = OLS(Y, X2).fit(cov_type="cluster",
                              cov_kwds={"groups": df_l["idDeputado"]})
        beta_T_direct = m2.params.iloc[1]
        gamma_M = m2.params.iloc[2]

        m3 = OLS(Y, X1).fit(cov_type="cluster",
                              cov_kwds={"groups": df_l["idDeputado"]})
        beta_T_total = m3.params.iloc[1]

        indirect = theta_TM * gamma_M
        prop_med = indirect / beta_T_total if beta_T_total != 0 else np.nan

        rows.append({
            "leg": leg_label,
            "theta_TM": round(theta_TM, 4),
            "beta_T_direct": round(beta_T_direct, 4),
            "gamma_M": round(gamma_M, 4),
            "beta_T_total": round(beta_T_total, 4),
            "indirect_effect": round(indirect, 4),
            "prop_mediated": round(prop_med, 4),
            "n_obs": len(df_l),
        })
        log.info(f"  {leg_label}: total={beta_T_total:.4f}, indirect={indirect:.4f}, "
                 f"prop={prop_med:.2%}")

    if rows:
        out = pd.DataFrame(rows)
        out.to_csv(RESULTS / "followup_centrao_t3_mediation_pix.csv", sep=";", index=False)
        log.info(f"[T3] saved")


def t2_het_rp9_exposure(df):
    log.info("\n" + "="*70)
    log.info("T2 (Centrao): Het by RP-9 exposure, Leg 56")
    log.info("="*70)
    df_56 = df[df["idLegislatura"] == 56].copy()
    df_56["d_rp9_exposed"] = (df_56["d_rp9_solicitante"] == 1).astype(int)
    ctrl = U2.get_clean_full_controls(df_56)

    rows = []
    for label, mask in [
        ("rp9_exposed", df_56["d_rp9_exposed"] == 1),
        ("rp9_not_exposed", df_56["d_rp9_exposed"] == 0),
    ]:
        sub = df_56[mask].copy()
        res = safe_pliv(sub, ctrl, f"T2 {label}")
        if res:
            res["subgroup"] = label
            rows.append(res)

    if rows:
        pd.DataFrame(rows).to_csv(RESULTS / "followup_centrao_t2_het_rp9_exposure.csv",
                                    sep=";", index=False)
        log.info(f"[T2] saved")


def t4_tercis_by_leg(df):
    log.info("\n" + "="*70)
    log.info("T4 (Centrao): tercis MDS por leg")
    log.info("="*70)
    ctrl = U2.get_clean_full_controls(df)
    ctrl = [c for c in ctrl if not c.startswith("pol_")]

    rows = []
    measures = [
        ("pol_paper_euclidean_mds", "MDS-Euclidean"),
        ("pol_paper_fraca_mds", "MDS-Weak"),
        ("pol_paper_forte_mds", "MDS-Strong"),
    ]
    for col, label in measures:
        if col not in df.columns:
            continue
        for leg in [55, 56]:
            df_l = df[df["idLegislatura"] == leg].copy()
            df_l = df_l.dropna(subset=[col])
            if len(df_l) < 5000:
                continue
            df_l["tercil"] = pd.qcut(df_l[col], 3, labels=["low", "mid", "high"],
                                       duplicates="drop")
            for tlabel in ["low", "mid", "high"]:
                sub = df_l[df_l["tercil"] == tlabel]
                res = safe_pliv(sub, ctrl, f"T4 {label} leg={leg} tercil={tlabel}")
                if res:
                    res["measure"] = label
                    res["leg"] = leg
                    res["tercil"] = tlabel
                    res["n_obs_tercil"] = len(sub)
                    rows.append(res)

    if rows:
        pd.DataFrame(rows).to_csv(RESULTS / "followup_centrao_t4_tercis_by_leg.csv",
                                    sep=";", index=False)
        log.info(f"[T4] saved")


def t1_iv_with_proxies(df):
    log.info("\n" + "="*70)
    log.info("T1 (Centrao): IV-DML with proxies")
    log.info("="*70)
    ctrl_base = U2.get_clean_full_controls(df)
    extra = ["d_rp9_solicitante", "share_pork_opaco", "share_pix",
             "T_rp9_imputed_pre60_M"]

    rows = []
    for leg in [55, 56]:
        df_l = df[df["idLegislatura"] == leg].copy()
        res_base = safe_pliv(df_l, ctrl_base, f"T1 leg={leg} base")
        if res_base:
            res_base["spec"] = "base"; res_base["leg"] = leg
            rows.append(res_base)
        ctrl_aug = ctrl_base + [c for c in extra if c not in ctrl_base]
        ctrl_aug = list(dict.fromkeys(ctrl_aug))
        res_aug = safe_pliv(df_l, ctrl_aug, f"T1 leg={leg} base+proxies")
        if res_aug:
            res_aug["spec"] = "base_plus_proxies"; res_aug["leg"] = leg
            rows.append(res_aug)

    if rows:
        pd.DataFrame(rows).to_csv(RESULTS / "followup_centrao_t1_iv_with_rp9_controls.csv",
                                    sep=";", index=False)
        log.info(f"[T1] saved")


if __name__ == "__main__":
    df = load_augmented_panel_centrao()

    log.info("\n[T3 - OLS, rapido]")
    t3_mediation_pix(df)
    log.info("\n[T2 - 2 PLIVs]")
    t2_het_rp9_exposure(df)
    log.info("\n[T4 - 18 PLIVs]")
    t4_tercis_by_leg(df)
    log.info("\n[T1 - 4 PLIVs]")
    t1_iv_with_proxies(df)

    log.info("\n\nDone. Centrao outcome analyses complete.")
