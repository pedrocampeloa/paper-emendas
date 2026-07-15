"""
43_t1_corrected.py
-------------------
Refaz T1 (IV-DML com proxies) corrigindo o bug em get_full_controls:
removendo manualmente T_rp*, share_*, d_rp9_*, n_apoiamentos_* do ctrl_base
para que a comparacao base-vs-base+proxies seja informativa.

Roda para ambos outcomes:
- gov outcome (alinhamento)
- centrao outcome (y_centrao)

n_folds=2, n_reps=1.

Outputs:
    results/followup_t1_iv_corrected_gov.csv
    results/followup_t1_iv_corrected_centrao.csv
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
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("t1_corr")

POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
INTERIM = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
CENTRAO_PARTIES = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE",
                   "UNIAO", "PTB", "AVANTE", "PSD", "MDB"}

# Colunas que devem ser EXCLUIDAS do ctrl_base por serem proxies/treatment-correlated
EXTRA_TREATMENT_VARS = [
    "T_rp6_pre60", "T_rp6_pre60_M",
    "T_rp6_pix_pre60", "T_rp6_pix_pre60_M",
    "T_rp8_pre60", "T_rp8_pre60_M",
    "T_rp9_imputed_pre60", "T_rp9_imputed_pre60_M",
    "T_rp7_pre60", "T_rp7_pre60_M",
    "T_rp9_pre60", "T_rp9_pre60_M",
    "d_rp9_solicitante", "share_pork_opaco", "share_rp9",
    "share_pix", "n_apoiamentos_opaco",
]

# Proxies que entram na spec aug.
# Decisao via analise de correlacao (jun 2026):
# - usar apenas d_rp9_solicitante (dummy, mais robusta)
# - share_pork_opaco e T_rp9_imputed_pre60_M tem corr 0.6-0.7 entre si e
#   com d_rp9_solicitante, geram redundancia que infla SEs
# - share_pix tem corr 0.996 com T_rp6_pix_pre60_M; usar share_pix isolado
# Como mediadores secundarios, podemos rodar spec C (so com share_pix) depois.
EXTRA_PROXIES = ["d_rp9_solicitante", "share_pix"]


def load_panel_aug(use_centrao_outcome=False):
    log.info(f"\n>>> Loading panel (centrao_outcome={use_centrao_outcome})")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)

    # voto+partido necessario para y_centrao
    if use_centrao_outcome:
        pf = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                         usecols=["idDeputado", "idVotacao", "voto", "siglaPartido"],
                         dtype=str, low_memory=False)
        pf["idDeputado"] = pf["idDeputado"].astype(str)
        df["idDeputado"] = df["idDeputado"].astype(str)
        for c in ["voto", "siglaPartido"]:
            if c in df.columns:
                df = df.drop(columns=[c])
        df = df.merge(pf, on=["idDeputado", "idVotacao"], how="left")

        df["d_centrao_party"] = df["siglaPartido"].astype(str).str.upper().str.strip().isin(CENTRAO_PARTIES).astype(int)
        cen = df[df["d_centrao_party"] == 1]
        cen_major = cen.groupby("idVotacao")["voto"].apply(
            lambda s: s.value_counts().index[0] if not s.value_counts().empty else np.nan
        ).reset_index().rename(columns={"voto": "voto_centrao_major"})
        df = df.merge(cen_major, on="idVotacao", how="left")
        df["y_centrao"] = (df["voto"] == df["voto_centrao_major"]).astype(int)
        df.loc[df["voto_centrao_major"].isna(), "y_centrao"] = np.nan
        df = df.dropna(subset=["y_centrao"])
        log.info(f"  y_centrao mean Leg55={df[df['idLegislatura']==55]['y_centrao'].mean():.3f}, "
                 f"Leg56={df[df['idLegislatura']==56]['y_centrao'].mean():.3f}")
        df["alinhamento"] = df["y_centrao"].astype(int)

    # multi-RP
    mr = pd.read_csv(INTERIM / "panel_emendas_pre_multi_rp.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    mr["idDeputado"] = mr["idDeputado"].astype(str)
    df["idDeputado"] = df["idDeputado"].astype(str)
    mr_cols = ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60", "T_rp9_imputed_pre60"]
    df = df.merge(mr[["idDeputado", "idVotacao"] + mr_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in mr_cols:
        df[c] = df[c].fillna(0)
        df[c + "_M"] = df[c] / 1e6

    # proxies
    px = pd.read_csv(INTERIM / "panel_secret_budget_proxies.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    px["idDeputado"] = px["idDeputado"].astype(str)
    px_cols = ["d_rp9_solicitante", "share_pork_opaco", "share_rp9",
               "share_pix", "n_apoiamentos_opaco"]
    df = df.merge(px[["idDeputado", "idVotacao"] + px_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in px_cols:
        df[c] = df[c].fillna(0)

    log.info(f"  panel: {len(df):,} rows x {len(df.columns)} cols")
    return df


def safe_pliv(df_l, controls, label):
    log.info(f"\n  --> PLIV: {label}")
    log.info(f"      n={len(df_l):,}, clusters={df_l['idDeputado'].nunique()}")
    controls = list(dict.fromkeys(controls))
    valid_ctrl = [c for c in controls if c in df_l.columns
                  and df_l[c].notna().mean() > 0.5
                  and df_l[c].nunique() > 1]
    log.info(f"      valid ctrls: {len(valid_ctrl)} of {len(controls)}")
    try:
        res = U2.run_pliv_main(df_l, controls=valid_ctrl, iv_set="backlog",
                                n_folds=2, n_reps=1)
        if res is None:
            log.warning(f"      [WARN] None"); return None
        log.info(f"      [OK] theta={res.get('pp_per_unit'):.4f} pp, pval={res.get('pval'):.4f}")
        return res
    except Exception as e:
        log.error(f"      [FAIL] {e}\n{traceback.format_exc()}")
        return None


def run_t1(df, suffix):
    log.info("\n" + "="*70)
    log.info(f"T1 corrected ({suffix}): IV-DML with proxies")
    log.info("="*70)
    ctrl_full = U2.get_clean_full_controls(df)
    ctrl_base = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    log.info(f"  ctrl_full = {len(ctrl_full)}, ctrl_base (after removing T_rp*/proxies) = {len(ctrl_base)}")
    excluded = [c for c in ctrl_full if c in EXTRA_TREATMENT_VARS]
    log.info(f"  excluded: {excluded}")

    rows = []
    for leg in [55, 56]:
        df_l = df[df["idLegislatura"] == leg].copy()
        log.info(f"\n[Leg {leg}] n={len(df_l):,}")

        # Spec A: base puro (sem nenhuma proxie)
        res_base = safe_pliv(df_l, ctrl_base, f"leg={leg} base_pure")
        if res_base:
            res_base["spec"] = "base_pure"
            res_base["leg"] = leg
            rows.append(res_base)

        # Spec B: base + proxies (controles + as proxies de exposicao opaca)
        ctrl_aug = ctrl_base + [c for c in EXTRA_PROXIES if c in df_l.columns]
        ctrl_aug = list(dict.fromkeys(ctrl_aug))
        res_aug = safe_pliv(df_l, ctrl_aug, f"leg={leg} base+proxies")
        if res_aug:
            res_aug["spec"] = "base_plus_proxies"
            res_aug["leg"] = leg
            rows.append(res_aug)

    if rows:
        out = pd.DataFrame(rows)
        out_path = RESULTS / f"followup_t1_iv_corrected_{suffix}.csv"
        out.to_csv(out_path, sep=";", index=False)
        log.info(f"\n  saved {out_path}")
        print(out[["leg", "spec", "pp_per_unit", "ci95_lo_pp", "ci95_hi_pp", "pval"]].to_string(index=False))


if __name__ == "__main__":
    log.info("=== T1 corrected for GOV outcome ===")
    df_gov = load_panel_aug(use_centrao_outcome=False)
    run_t1(df_gov, "gov")

    log.info("\n\n=== T1 corrected for CENTRAO outcome ===")
    df_cen = load_panel_aug(use_centrao_outcome=True)
    run_t1(df_cen, "centrao")

    log.info("\nDone.")
