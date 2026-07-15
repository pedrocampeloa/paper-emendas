"""
36_followup_analyses.py
------------------------
Cinco analises follow-up apos integracao das variaveis multi-RP e proxies.

PERFORMANCE: usa n_folds=2, n_reps=1 (vs default 3/3) para tornar viavel
o tempo de execucao. O preco e' SE ligeiramente maior, mas o sinal estrutural
e' robusto.

Priorizacao:
T3 (mediacao Pix, OLS): rapida, roda primeiro.
T5 (Centrao outcome): substantivamente central, prioridade.
T4 (tercis por leg): Bernardo pediu, prioridade.
T1 (proxies como controle): confirmatorio.
T2 (heterogeneidade): redundante com tercis, opcional.

Outputs:
    results/followup_t1_iv_with_rp9_controls.csv
    results/followup_t2_het_rp9_exposure.csv
    results/followup_t3_mediation_pix.csv
    results/followup_t4_tercis_by_leg.csv
    results/followup_t5_centrao_alignment.csv
"""

import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# Para reusar a infraestrutura existente
sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("followup")

INTERIM = Path(C.PANEL)
RESULTS = Path(C.RESULTS)


# ============================================================================
# Helper: load augmented panel (with multi-RP + proxies merged)
# ============================================================================

def load_augmented_panel():
    """Carrega painel base + multi-RP + proxies em um unico DataFrame."""
    log.info("Loading base panel via U.load_modeling_panel")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    log.info(f"  base: {len(df):,} rows")

    log.info("Merging multi-RP variables")
    mr = pd.read_csv(INTERIM / "panel_emendas_pre_multi_rp.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    mr["idDeputado"] = mr["idDeputado"].astype(str)
    df["idDeputado"] = df["idDeputado"].astype(str)
    mr_cols = ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60",
               "T_rp9_imputed_pre60"]
    df = df.merge(mr[["idDeputado", "idVotacao"] + mr_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in mr_cols:
        df[c] = df[c].fillna(0)
        df[c + "_M"] = df[c] / 1e6   # convert to R$M

    log.info("Merging secret budget proxies")
    px = pd.read_csv(INTERIM / "panel_secret_budget_proxies.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    px["idDeputado"] = px["idDeputado"].astype(str)
    px_cols = ["d_rp9_solicitante", "share_pork_opaco", "share_rp9",
               "share_pix", "n_apoiamentos_opaco"]
    df = df.merge(px[["idDeputado", "idVotacao"] + px_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in px_cols:
        df[c] = df[c].fillna(0)

    log.info(f"  augmented: {len(df):,} rows, {len([c for c in df.columns if c.startswith('T_rp')])} new T_rp* cols")
    return df


# ============================================================================
# T1 -- IV-DML controlando por proxies
# ============================================================================

def t1_iv_with_proxies(df):
    """Reestima IV-DML adicionando proxies como controles."""
    log.info("\n" + "="*70)
    log.info("T1: IV-DML with secret-budget proxies as additional controls")
    log.info("="*70)
    ctrl_base = U2.get_clean_full_controls(df)
    extra_proxies = ["d_rp9_solicitante", "share_pork_opaco", "share_pix",
                     "T_rp9_imputed_pre60_M"]

    rows = []
    for leg in [55, 56, "pooled"]:
        if leg == "pooled":
            df_l = df.copy()
        else:
            df_l = df[df["idLegislatura"] == leg].copy()
        if len(df_l) < 5000:
            log.warning(f"  skip leg={leg} (n={len(df_l)})")
            continue

        # Spec A: base (sem proxies)
        res_base = U2.run_pliv_main(df_l, controls=ctrl_base, iv_set="backlog")
        if res_base is not None:
            res_base["spec"] = "base"
            res_base["leg"] = leg
            rows.append(res_base)
        log.info(f"  leg={leg} base done")

        # Spec B: base + proxies (dedup p/ evitar duplicatas que quebram within_transform)
        ctrl_aug = ctrl_base + [c for c in extra_proxies if c in df_l.columns
                                  and c not in ctrl_base
                                  and df_l[c].notna().mean() > 0.5
                                  and df_l[c].nunique() > 1]
        ctrl_aug = list(dict.fromkeys(ctrl_aug))
        res_aug = U2.run_pliv_main(df_l, controls=ctrl_aug, iv_set="backlog", n_folds=2, n_reps=1)
        if res_aug is not None:
            res_aug["spec"] = "base_plus_proxies"
            res_aug["leg"] = leg
            rows.append(res_aug)
        log.info(f"  leg={leg} base+proxies done")

    if not rows:
        log.warning("T1: no results")
        return
    out = pd.DataFrame(rows)
    out_path = RESULTS / "followup_t1_iv_with_rp9_controls.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"  saved {out_path}")
    print(out.to_string(index=False))
    return out


# ============================================================================
# T2 -- Heterogeneidade Leg 56 com/sem exposicao RP-9
# ============================================================================

def t2_heterogeneity_rp9_exposure(df):
    log.info("\n" + "="*70)
    log.info("T2: Heterogeneity Leg 56 by RP-9 exposure")
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
        if len(sub) < 1000:
            log.warning(f"  skip {label} (n={len(sub)})")
            continue
        res = U2.run_pliv_main(sub, controls=ctrl, iv_set="backlog", n_folds=2, n_reps=1)
        if res is not None:
            res["subgroup"] = label
            rows.append(res)
        log.info(f"  {label} n={len(sub):,} done")

    if not rows:
        return
    out = pd.DataFrame(rows)
    out_path = RESULTS / "followup_t2_het_rp9_exposure.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"  saved {out_path}")
    print(out.to_string(index=False))
    return out


# ============================================================================
# T3 -- Mediacao dupla (Pix)
# ============================================================================

def t3_mediation_pix(df):
    """Mediacao Acharya-Blackwell-Sen com share_pix como mediador."""
    log.info("\n" + "="*70)
    log.info("T3: ABS mediation with share_pix as mediator")
    log.info("="*70)

    # Implementacao manual (sem dependencia DML para o mediador)
    from sklearn.linear_model import LinearRegression
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

        # Stage 1: T -> M
        X1 = add_constant(T)
        m1 = OLS(M, X1).fit(cov_type="cluster",
                              cov_kwds={"groups": df_l["idDeputado"]})
        theta_TM = m1.params.iloc[1]

        # Stage 2: Y ~ T + M (direct + mediator)
        X2 = add_constant(pd.DataFrame({"T": T, "M": M}))
        m2 = OLS(Y, X2).fit(cov_type="cluster",
                              cov_kwds={"groups": df_l["idDeputado"]})
        beta_T_direct = m2.params.iloc[1]
        gamma_M = m2.params.iloc[2]

        # Stage 3: total effect Y ~ T
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
                 f"prop_mediated={prop_med:.2%}")

    if not rows:
        return
    out = pd.DataFrame(rows)
    out_path = RESULTS / "followup_t3_mediation_pix.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"  saved {out_path}")
    print(out.to_string(index=False))
    return out


# ============================================================================
# T4 -- Tercis polarizacao SEPARADOS por legislatura
# ============================================================================

def t4_tercis_by_leg(df):
    """Tercis MDS-Euclidean e Weak Divergence dentro de cada leg."""
    log.info("\n" + "="*70)
    log.info("T4: Polarization terciles SEPARATED by legislature")
    log.info("="*70)
    ctrl = U2.get_clean_full_controls(df)

    rows = []
    measures = [
        ("pol_paper_euclidean_mds", "MDS-Euclidean"),
        ("pol_paper_fraca_mds", "MDS-Weak"),
        ("pol_paper_forte_mds", "MDS-Strong"),
    ]
    for col, label in measures:
        if col not in df.columns:
            log.warning(f"  skip {col} (missing)")
            continue
        for leg in [55, 56]:
            df_l = df[df["idLegislatura"] == leg].copy()
            df_l = df_l.dropna(subset=[col])
            if len(df_l) < 5000:
                continue
            # Tercis DENTRO da legislatura (nao pooled)
            df_l["tercil"] = pd.qcut(df_l[col], 3, labels=["low", "mid", "high"],
                                       duplicates="drop")
            for tlabel in ["low", "mid", "high"]:
                sub = df_l[df_l["tercil"] == tlabel]
                if len(sub) < 2000:
                    continue
                res = U2.run_pliv_main(sub, controls=ctrl, iv_set="backlog", n_folds=2, n_reps=1)
                if res is not None:
                    res["measure"] = label
                    res["leg"] = leg
                    res["tercil"] = tlabel
                    res["n_obs_tercil"] = len(sub)
                    rows.append(res)
                log.info(f"  {label} leg={leg} tercil={tlabel} n={len(sub):,} done")

    if not rows:
        return
    out = pd.DataFrame(rows)
    out_path = RESULTS / "followup_t4_tercis_by_leg.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"  saved {out_path}")
    print(out.to_string(index=False))
    return out


# ============================================================================
# T5 -- Outcome alternativo: alinhamento Centrao
# ============================================================================

def t5_centrao_alignment(df):
    """Reconstroi y como alinhamento com Centrao, reestima Leg 56 e
    sub-periodo Lira (pos fev/2021)."""
    log.info("\n" + "="*70)
    log.info("T5: Outcome = alignment with Centrão (Leg 56, post-Lira focus)")
    log.info("="*70)

    # Definicao do Centrao (literatura: Power, Melo, Limongi)
    CENTRAO_PARTIES = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE",
                       "UNIAO", "PTB", "AVANTE", "PSD", "MDB"}
    df["d_centrao"] = df["siglaPartido"].astype(str).str.upper().str.strip().isin(CENTRAO_PARTIES).astype(int)

    # Para cada voto, qual e' a posicao majoritaria do Centrao?
    log.info("  Computing per-vote Centrao majority")
    grp = df[df["d_centrao"] == 1].groupby("idVotacao")["voto"]
    # voto codifica Sim/Nao/Outros — usar a moda
    def majority_centrao(s):
        vc = s.value_counts()
        if vc.empty: return np.nan
        return vc.index[0]
    centrao_vote = grp.apply(majority_centrao).reset_index().rename(
        columns={"voto": "voto_majoritario_centrao"})
    df = df.merge(centrao_vote, on="idVotacao", how="left")
    df["y_centrao"] = (df["voto"] == df["voto_majoritario_centrao"]).astype(int)
    df.loc[df["voto_majoritario_centrao"].isna(), "y_centrao"] = np.nan

    log.info(f"  y_centrao mean (full): {df['y_centrao'].mean():.3f}")
    log.info(f"  y_centrao mean (Leg 56): {df[df['idLegislatura']==56]['y_centrao'].mean():.3f}")

    ctrl = U2.get_clean_full_controls(df)
    ctrl = [c for c in ctrl if c not in ("alinhamento", "y_centrao", "d_centrao")]

    rows = []
    for label, mask in [
        ("leg55_full", df["idLegislatura"] == 55),
        ("leg56_full", df["idLegislatura"] == 56),
        ("leg56_pre_lira", (df["idLegislatura"] == 56) & (df["data"] < "2021-02-01")),
        ("leg56_post_lira", (df["idLegislatura"] == 56) & (df["data"] >= "2021-02-01")),
        ("leg56_post_lira_excl_centrao",
            (df["idLegislatura"] == 56) & (df["data"] >= "2021-02-01") & (df["d_centrao"] == 0)),
    ]:
        sub = df[mask].copy()
        sub = sub.dropna(subset=["y_centrao", "emenda_M"])
        if len(sub) < 5000:
            continue
        # Substituir TARGET=alinhamento por y_centrao
        # _utils_v2 lê C.TARGET — preciso passar custom
        sub["alinhamento"] = sub["y_centrao"]  # hack: substituir
        res = U2.run_pliv_main(sub, controls=ctrl, iv_set="backlog", n_folds=2, n_reps=1)
        if res is not None:
            res["sample"] = label
            res["n_obs_sample"] = len(sub)
            res["y_centrao_mean"] = round(sub["y_centrao"].mean(), 3)
            rows.append(res)
        log.info(f"  {label} n={len(sub):,} done")

    if not rows:
        return
    out = pd.DataFrame(rows)
    out_path = RESULTS / "followup_t5_centrao_alignment.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"  saved {out_path}")
    print(out.to_string(index=False))
    return out


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    df = load_augmented_panel()

    # Ordem priorizada: rapidas e substantivamente centrais primeiro
    log.info("\n[Running T3 - OLS mediation, rapido]")
    t3_mediation_pix(df)
    log.info("\n[Running T5 - Centrao outcome]")
    t5_centrao_alignment(df)
    log.info("\n[Running T4 - tercis por leg]")
    t4_tercis_by_leg(df)
    log.info("\n[Running T1 - confirmatorio com proxies]")
    t1_iv_with_proxies(df)
    log.info("\n[Running T2 - heterogeneidade RP-9 exposure]")
    t2_heterogeneity_rp9_exposure(df)

    log.info("\nAll follow-up analyses complete.")
