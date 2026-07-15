"""
55_n3_pres_camara_orient.py
----------------------------
RODADA DEFINITIVA do outcome alternativo: y_pres_camara_orient.

Outcome: voto[i,t] == orientacao do partido do presidente da Camara em t.

Linha do tempo dos presidentes:
  - 2015-02 a 2016-07-13: Cunha (PMDB) — Leg 55
  - 2016-07-14 a 2019-01-31: Maia (DEM) — Leg 55
  - 2019-02-01 a 2021-01-31: Maia (DEM) — Leg 56
  - 2021-02-01 em diante: Lira (PP) — Leg 56

Estratégia:
  Para cada votação, partido_presidente é determinado pela data.
  Tomamos a orientação formal desse partido naquela votação (do painel).
  y = 1 se voto coincide; NaN se orientação for Liberado/Abstenção/ausente.

Cobertura conhecida:
  PMDB (Cunha): 39%
  DEM (Maia): 95%
  PP (Lira): 66%

T5 com 6 sub-amostras (4 sub-períodos por presidente + 2 amostras especiais):
  - leg55_cunha (PMDB)
  - leg55_maia (DEM)
  - leg56_maia (DEM)
  - leg56_lira (PP)
  - leg56_lira_excl_pp (Lira, excluindo deputados do PP)
  - leg56_lira_excl_centrao (Lira, excluindo deputados do Centrão histórico)

n_folds=3, n_reps=3.

Outputs (prefixo n3_pres_):
  results/n3_pres_t1_iv.csv
  results/n3_pres_t2_het.csv
  results/n3_pres_t3_mediation_pix.csv
  results/n3_pres_t4_tercis.csv
  results/n3_pres_t5_subsamples.csv
  results/n3_pres_progress.md
  results/n3_pres_full.log
"""

import logging
import sys
import traceback
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
INTERIM = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
LOG_FILE = RESULTS / "n3_pres_full.log"
PROGRESS = RESULTS / "n3_pres_progress.md"

# Partidos do Centrão histórico amplo (para sub-amostra T5 excluindo Centrão)
CENTRAO_HIST = {"MDB", "PMDB", "PP", "PL", "PR", "PRB", "REPUBLICANOS",
                "DEM", "UNIAO", "PTB", "SD", "SOLIDARIEDADE", "PSC",
                "AVANTE", "PROS", "CIDADANIA", "PODE", "PSD"}

N_FOLDS = 3
N_REPS = 3

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
EXTRA_PROXIES = ["d_rp9_solicitante", "share_pix"]


# Logger
log = logging.getLogger("n3pres")
log.setLevel(logging.INFO)
for h in list(log.handlers): log.removeHandler(h)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
sh = logging.StreamHandler(sys.stdout); sh.setFormatter(fmt); log.addHandler(sh)
fh = logging.FileHandler(LOG_FILE, mode="a"); fh.setFormatter(fmt); log.addHandler(fh)


def init_progress():
    PROGRESS.write_text(
        f"# n3 — outcome y_pres_camara_orient\n\n"
        f"Started: {datetime.now().isoformat()}\n\n"
        f"Outcome: voto == orientação do partido do presidente da Câmara em t\n\n"
        f"Sub-períodos:\n"
        f"- 2015-02 a 2016-07: Cunha (PMDB)\n"
        f"- 2016-07 a 2021-02: Maia (DEM)\n"
        f"- 2021-02 em diante: Lira (PP)\n\n"
        f"Config: n_folds={N_FOLDS}, n_reps={N_REPS}\n\n"
    )


def append(line):
    with open(PROGRESS, "a") as f: f.write(line + "\n")


def check(name, cond, *details):
    if cond:
        log.info(f"  [OK] {name}")
    else:
        log.error(f"  [FAIL] {name}")
        for d in details: log.error(f"         {d}")
        raise AssertionError(name)


def get_partido_presidente(data: pd.Timestamp) -> str:
    if data < pd.Timestamp("2016-07-14"): return "PMDB"
    if data < pd.Timestamp("2021-02-01"): return "DEM"
    return "PP"


def attach_pol_paper(df):
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name in ["euclidean", "forte", "fraca"]:
        path = POL_PAPER_DIR / f"average_mds_distances_{name}.csv"
        pol = pd.read_csv(path)
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        col = f"pol_paper_{name}_mds"
        df[col] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col] = r["Euclidiana_MDS"]
    return df


def load_panel_with_y_pres():
    log.info("="*70)
    log.info("STEP 0: Loading panel + y_pres_camara_orient")
    log.info("="*70)

    log.info("[0.1] Base panel via U.load_modeling_panel")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    check("base panel non-empty", len(df) > 0)

    log.info("[0.2] Carregar voto + sigla + orientacao_partido")
    pf = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "idVotacao", "voto", "siglaPartido",
                              "d_ori_part_sim", "d_ori_part_nao",
                              "d_ori_part_obstrucao", "d_ori_part_liberado",
                              "d_ori_part_abstencao"],
                     dtype=str, low_memory=False)
    pf["idDeputado"] = pf["idDeputado"].astype(str)
    for c in ["d_ori_part_sim", "d_ori_part_nao", "d_ori_part_obstrucao",
              "d_ori_part_liberado", "d_ori_part_abstencao"]:
        pf[c] = pd.to_numeric(pf[c], errors="coerce")
    pf["partido_norm"] = pf["siglaPartido"].astype(str).str.upper().str.strip()

    def get_ori_str(row):
        if row["d_ori_part_sim"] == 1: return "Sim"
        if row["d_ori_part_nao"] == 1: return "Não"
        if row["d_ori_part_obstrucao"] == 1: return "Obstrução"
        if row["d_ori_part_liberado"] == 1: return "Liberado"
        if row["d_ori_part_abstencao"] == 1: return "Abstenção"
        return None
    pf["ori_partido_str"] = pf.apply(get_ori_str, axis=1)

    log.info("[0.3] Construindo orientacao do partido presidente por votacao")
    # Para cada votação, qual o partido do presidente (depende da data)?
    voto_data = pf[["idVotacao"]].drop_duplicates().merge(
        df[["idVotacao", "data"]].drop_duplicates(), on="idVotacao", how="left")
    voto_data["data"] = pd.to_datetime(voto_data["data"])
    voto_data["partido_presidente"] = voto_data["data"].apply(get_partido_presidente)

    # Para cada votação, pegar a orientação do partido do presidente daquela época
    # Mapeamento: (idVotacao, partido_pres) -> orientacao
    pf_for_lookup = pf[["idVotacao", "partido_norm", "ori_partido_str"]].drop_duplicates(
        subset=["idVotacao", "partido_norm"]
    )
    voto_data = voto_data.merge(
        pf_for_lookup, left_on=["idVotacao", "partido_presidente"],
        right_on=["idVotacao", "partido_norm"], how="left"
    ).rename(columns={"ori_partido_str": "ori_pres_camara"})

    log.info(f"    Total votacoes: {len(voto_data):,}")
    log.info(f"    Com orientacao do partido pres: {voto_data['ori_pres_camara'].notna().sum():,}")

    log.info("[0.4] Construindo y_pres_camara_orient")
    # Merge voto + orientação no painel
    voto_simples = pf[["idDeputado", "idVotacao", "voto"]]
    df = df.drop(columns=[c for c in ["voto", "siglaPartido"] if c in df.columns])
    df = df.merge(voto_simples, on=["idDeputado", "idVotacao"], how="left")
    df = df.merge(voto_data[["idVotacao", "partido_presidente", "ori_pres_camara"]],
                  on="idVotacao", how="left")

    df["y_pres"] = (df["voto"] == df["ori_pres_camara"]).astype(int)
    invalid = df["ori_pres_camara"].isin(["Liberado", "Abstenção"]) | df["ori_pres_camara"].isna()
    df.loc[invalid, "y_pres"] = np.nan

    n_total = len(df)
    n_with = df["y_pres"].notna().sum()
    log.info(f"  Painel total: {n_total:,}")
    log.info(f"  Com y_pres valido: {n_with:,} ({100*n_with/n_total:.1f}%)")
    log.info(f"  Por partido_presidente:")
    for p in ["PMDB", "DEM", "PP"]:
        sub = df[df["partido_presidente"] == p]
        nv = sub["y_pres"].notna().sum()
        log.info(f"    {p}: n_total={len(sub):,}, n_valid={nv:,} ({100*nv/len(sub):.1f}%), mean={sub['y_pres'].mean():.4f}")

    # Substituir alinhamento por y_pres
    n_before = len(df)
    df = df.dropna(subset=["y_pres"])
    log.info(f"  Dropped {n_before - len(df):,} rows sem y_pres")
    df["alinhamento"] = df["y_pres"].astype(int)
    check("alinhamento binario", set(df["alinhamento"].unique()) <= {0, 1})

    log.info("[0.5] Merging multi-RP")
    mr = pd.read_csv(INTERIM / "panel_emendas_pre_multi_rp.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    mr["idDeputado"] = mr["idDeputado"].astype(str)
    mr_cols = ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60", "T_rp9_imputed_pre60"]
    df = df.merge(mr[["idDeputado", "idVotacao"] + mr_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in mr_cols:
        df[c] = df[c].fillna(0)
        df[c + "_M"] = df[c] / 1e6

    log.info("[0.6] Merging proxies")
    px = pd.read_csv(INTERIM / "panel_secret_budget_proxies.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    px["idDeputado"] = px["idDeputado"].astype(str)
    px_cols = ["d_rp9_solicitante", "share_pork_opaco", "share_rp9",
               "share_pix", "n_apoiamentos_opaco"]
    df = df.merge(px[["idDeputado", "idVotacao"] + px_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in px_cols:
        df[c] = df[c].fillna(0)

    log.info("[0.7] MDS attach")
    df = attach_pol_paper(df)

    # Reconstruir siglaPartido + d_centrao_hist para sub-amostras
    df = df.merge(pf[["idDeputado", "idVotacao", "siglaPartido", "partido_norm"]].drop_duplicates(),
                  on=["idDeputado", "idVotacao"], how="left")
    df["d_centrao_hist"] = df["partido_norm"].isin(CENTRAO_HIST).astype(int)
    df["d_pp"] = (df["partido_norm"] == "PP").astype(int)

    check("idLegislatura tem 55 e 56", set(df["idLegislatura"].unique()) >= {55, 56})
    check("sem duplicatas", not df.duplicated(["idDeputado", "idVotacao"]).any())

    log.info(f"\n  Final panel: {len(df):,} × {len(df.columns)} cols")
    return df


def safe_pliv(df_l, controls, label, tag=""):
    log.info(f"  --> PLIV: {label}  (n={len(df_l):,}, clusters={df_l['idDeputado'].nunique()})")
    if len(df_l) < 5000:
        log.warning(f"     [WARN] too small")
        return None
    controls = list(dict.fromkeys(controls))
    bad_set = {"alinhamento", "emenda_M", "idDeputado", "y_pres",
               "voto", "ori_pres_camara", "partido_presidente",
               "partido_norm", "siglaPartido", "d_centrao_hist", "d_pp"}
    controls = [c for c in controls if c not in bad_set]
    valid_ctrl = [c for c in controls if c in df_l.columns
                  and df_l[c].notna().mean() > 0.5
                  and df_l[c].nunique() > 1]
    t0 = time.time()
    try:
        res = U2.run_pliv_main(df_l, controls=valid_ctrl, iv_set="backlog",
                                n_folds=N_FOLDS, n_reps=N_REPS)
        elapsed = time.time() - t0
        if res is None:
            log.warning(f"     [WARN] None")
            return None
        log.info(f"     [OK] theta={res['pp_per_unit']:+.4f} pp, p={res['pval']:.4f} ({elapsed:.1f}s)")
        if tag:
            stars = "***" if res['pval']<0.01 else "**" if res['pval']<0.05 else "*" if res['pval']<0.10 else ""
            append(f"- **{datetime.now().strftime('%H:%M:%S')}** [{tag}] {label}: theta={res['pp_per_unit']:+.4f} pp/R$M{stars} p={res['pval']:.4f} n={res['n_obs']:,}")
        return res
    except Exception as e:
        log.error(f"     [FAIL] {e}\n{traceback.format_exc()}")
        return None


def save_inc(rows, fname):
    if not rows: return
    pd.DataFrame(rows).to_csv(RESULTS / fname, sep=";", index=False)
    log.info(f"  >> saved {fname} ({len(rows)} rows)")


def run_t3(df):
    log.info("\n" + "="*70)
    log.info("T3 (y_pres): OLS mediation Pix")
    log.info("="*70)
    append("\n### T3 — OLS mediation Pix\n")
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant
    rows = []
    for label, mask in [("pooled", df["alinhamento"].notna()),
                         ("leg55", df["idLegislatura"] == 55),
                         ("leg56", df["idLegislatura"] == 56)]:
        df_l = df[mask].dropna(subset=["alinhamento", "emenda_M", "share_pix"])
        if len(df_l) < 5000: continue
        T = df_l["emenda_M"]; M = df_l["share_pix"]; Y = df_l["alinhamento"]
        X1 = add_constant(T)
        m1 = OLS(M, X1).fit(cov_type="cluster", cov_kwds={"groups": df_l["idDeputado"]})
        theta_TM = m1.params.iloc[1]
        X2 = add_constant(pd.DataFrame({"T": T, "M": M}))
        m2 = OLS(Y, X2).fit(cov_type="cluster", cov_kwds={"groups": df_l["idDeputado"]})
        beta_T_direct = m2.params.iloc[1]; gamma_M = m2.params.iloc[2]
        m3 = OLS(Y, X1).fit(cov_type="cluster", cov_kwds={"groups": df_l["idDeputado"]})
        beta_T_total = m3.params.iloc[1]
        ind = theta_TM * gamma_M
        prop = ind / beta_T_total if beta_T_total != 0 else np.nan
        rows.append({"leg": label, "theta_TM": round(theta_TM,4),
                     "beta_T_direct": round(beta_T_direct,4),
                     "gamma_M": round(gamma_M,4),
                     "beta_T_total": round(beta_T_total,4),
                     "indirect_effect": round(ind,4),
                     "prop_mediated": round(prop,4), "n_obs": len(df_l)})
        log.info(f"  {label}: total={beta_T_total:.4f} indirect={ind:.4f} prop={prop:.2%}")
        append(f"- {label}: total={beta_T_total:+.4f}, indirect={ind:+.4f}, prop_med={prop*100:+.1f}%, n={len(df_l):,}")
        save_inc(rows, "n3_pres_t3_mediation_pix.csv")


def run_t5(df):
    """T5 com 6 sub-amostras correspondentes aos sub-periodos por presidente."""
    log.info("\n" + "="*70)
    log.info("T5 (y_pres): sub-amostras por presidente")
    log.info("="*70)
    append("\n### T5 — sub-amostras por presidente\n")
    df["data"] = pd.to_datetime(df["data"])
    ctrl_full = U2.get_clean_full_controls(df)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]

    rows = []
    # Nota: leg55_cunha tem apenas 116 obs (painel comeca ~2017), descartamos.
    samples = [
        ("leg55_maia",
         (df["idLegislatura"] == 55) & (df["data"] >= "2016-07-14")),
        ("leg56_maia",
         (df["idLegislatura"] == 56) & (df["data"] < "2021-02-01")),
        ("leg56_lira",
         (df["idLegislatura"] == 56) & (df["data"] >= "2021-02-01")),
        ("leg56_lira_excl_pp",
         (df["idLegislatura"] == 56) & (df["data"] >= "2021-02-01") & (df["d_pp"] == 0)),
        ("leg56_lira_excl_centrao",
         (df["idLegislatura"] == 56) & (df["data"] >= "2021-02-01") & (df["d_centrao_hist"] == 0)),
        ("leg56_lira_only_centrao",
         (df["idLegislatura"] == 56) & (df["data"] >= "2021-02-01") & (df["d_centrao_hist"] == 1)),
    ]
    for label, mask in samples:
        sub = df[mask].copy()
        res = safe_pliv(sub, ctrl, f"T5 {label}", tag="T5")
        if res:
            res["sample"] = label
            res["y_pres_mean"] = round(sub["alinhamento"].mean(), 4)
            rows.append(res)
            save_inc(rows, "n3_pres_t5_subsamples.csv")


def run_t2(df):
    log.info("\n" + "="*70)
    log.info("T2 (y_pres): RP-9 exposure heterogeneity, Leg 56")
    log.info("="*70)
    append("\n### T2 — RP-9 exposure (Leg 56)\n")
    df_56 = df[df["idLegislatura"] == 56].copy()
    df_56["d_rp9_exposed"] = (df_56["d_rp9_solicitante"] == 1).astype(int)
    ctrl_full = U2.get_clean_full_controls(df_56)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    rows = []
    for label, mask in [
        ("rp9_exposed", df_56["d_rp9_exposed"] == 1),
        ("rp9_not_exposed", df_56["d_rp9_exposed"] == 0),
    ]:
        sub = df_56[mask].copy()
        res = safe_pliv(sub, ctrl, f"T2 {label}", tag="T2")
        if res:
            res["subgroup"] = label
            rows.append(res)
            save_inc(rows, "n3_pres_t2_het.csv")


def run_t4(df):
    log.info("\n" + "="*70)
    log.info("T4 (y_pres): tercis MDS por leg")
    log.info("="*70)
    append("\n### T4 — tercis MDS por leg\n")
    ctrl_full = U2.get_clean_full_controls(df)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    ctrl = [c for c in ctrl if not c.startswith("pol_")]
    rows = []
    for col, mlabel in [("pol_paper_euclidean_mds", "MDS-Euclidean"),
                         ("pol_paper_fraca_mds", "MDS-Weak"),
                         ("pol_paper_forte_mds", "MDS-Strong")]:
        if col not in df.columns: continue
        for leg in [55, 56]:
            df_l = df[df["idLegislatura"] == leg].copy()
            df_l = df_l.dropna(subset=[col])
            if len(df_l) < 5000: continue
            try:
                df_l["tercil"] = pd.qcut(df_l[col], 3, labels=["low","mid","high"], duplicates="drop")
            except: continue
            for tlabel in ["low", "mid", "high"]:
                sub = df_l[df_l["tercil"] == tlabel]
                res = safe_pliv(sub, ctrl, f"T4 {mlabel} leg={leg} tercil={tlabel}", tag="T4")
                if res:
                    res.update({"measure": mlabel, "leg": leg, "tercil": tlabel,
                                "n_obs_tercil": len(sub)})
                    rows.append(res)
                    save_inc(rows, "n3_pres_t4_tercis.csv")


def run_t1(df):
    log.info("\n" + "="*70)
    log.info("T1 (y_pres): IV-DML base vs base+proxies")
    log.info("="*70)
    append("\n### T1 — IV-DML with proxies\n")
    ctrl_full = U2.get_clean_full_controls(df)
    ctrl_base = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    rows = []
    for leg in [55, 56]:
        df_l = df[df["idLegislatura"] == leg].copy()
        res_b = safe_pliv(df_l, ctrl_base, f"T1 leg={leg} base_pure", tag="T1")
        if res_b:
            res_b.update({"spec": "base_pure", "leg": leg})
            rows.append(res_b)
            save_inc(rows, "n3_pres_t1_iv.csv")
        ctrl_aug = list(dict.fromkeys(ctrl_base + EXTRA_PROXIES))
        res_a = safe_pliv(df_l, ctrl_aug, f"T1 leg={leg} base+proxies", tag="T1")
        if res_a:
            res_a.update({"spec": "base_plus_proxies", "leg": leg})
            rows.append(res_a)
            save_inc(rows, "n3_pres_t1_iv.csv")


if __name__ == "__main__":
    init_progress()
    log.info("FULL FOLLOWUP y_pres_camara_orient — n_folds=3, n_reps=3")
    log.info(f"Start: {datetime.now().isoformat()}")
    t0 = time.time()

    df = load_panel_with_y_pres()

    log.info("\n[Phase 1: T3 OLS]")
    run_t3(df)
    log.info("\n[Phase 2: T5 sub-amostras (6 PLIVs por presidente)]")
    run_t5(df)
    log.info("\n[Phase 3: T2 RP-9 het — 2 PLIVs]")
    run_t2(df)
    log.info("\n[Phase 4: T4 tercis MDS — 18 PLIVs]")
    run_t4(df)
    log.info("\n[Phase 5: T1 IV proxies — 4 PLIVs]")
    run_t1(df)

    elapsed = (time.time() - t0) / 3600
    log.info(f"\n\nDONE in {elapsed:.2f} hours")
    append(f"\n## End: {datetime.now().isoformat()} ({elapsed:.2f}h)")
