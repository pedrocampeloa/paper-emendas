"""
53_n3_centrao_orient_correto.py
--------------------------------
RE-RODAR T1, T2, T3, T4, T5 para outcome CENTRAO corrigido (ex-ante).

Outcome anterior (errado): y_centrao = voto[i,t] == voto_majoritario_do_bloco[t]
  → ex-post, contaminado pelo proprio voto de i.

Outcome corrigido (este script): y_centrao = voto[i,t] == orientacao_centrao_majoritaria[t]
  → ex-ante, baseado nas orientacoes formais dos partidos do Centrao,
  anunciadas antes da votacao.

Detalhes:
- Para cada votacao, computar a maioria simples (>=5 partidos Centrao com mesma orientacao)
  entre Sim/Nao/Obstrucao.
- y_centrao_orient[i,t] = 1 se voto[i,t] == orientacao_majoritaria[t]
  - NaN se nao ha maioria clara (empate, todos liberados, <5 partidos com orientacao formal)
- Cobertura Leg 56: ~84% das votacoes tem maioria do Centrao definida.

n_folds=3, n_reps=3 (mesma config do main paper).

Outputs (todos n3_centrao_orient_*):
  results/n3_centrao_orient_t1_iv.csv
  results/n3_centrao_orient_t2_het.csv
  results/n3_centrao_orient_t3_mediation_pix.csv
  results/n3_centrao_orient_t4_tercis.csv
  results/n3_centrao_orient_t5_subsamples.csv
  results/n3_centrao_orient_progress.md
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
LOG_FILE = RESULTS / "n3_centrao_orient_full.log"
PROGRESS = RESULTS / "n3_centrao_orient_progress.md"

CENTRAO_PARTIES = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE",
                   "UNIAO", "PTB", "AVANTE", "PSD", "MDB"}

N_FOLDS = 3
N_REPS = 3
MAIORIA_THRESHOLD = 5  # >=5 dos 9 partidos com mesma orientacao

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
log = logging.getLogger("n3cent")
log.setLevel(logging.INFO)
for h in list(log.handlers): log.removeHandler(h)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
sh = logging.StreamHandler(sys.stdout); sh.setFormatter(fmt); log.addHandler(sh)
fh = logging.FileHandler(LOG_FILE, mode="a"); fh.setFormatter(fmt); log.addHandler(fh)


def init_progress():
    PROGRESS.write_text(
        f"# n3 Centrão (orientação ex-ante) — progress\n\n"
        f"Started: {datetime.now().isoformat()}\n\n"
        f"Outcome corrigido: y_centrao_orient = voto == maioria(>={MAIORIA_THRESHOLD}) das orientacoes dos partidos do Centrao\n\n"
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


def load_panel_with_y_centrao_orient():
    log.info("="*70)
    log.info("STEP 0: Loading panel + constructing y_centrao_orient (ex-ante)")
    log.info("="*70)

    log.info("[0.1] Base panel")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)

    log.info("[0.2] Loading voto + ori_partido + siglaPartido")
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

    log.info("[0.3] Computing orientacao Centrao majoritaria por votacao")
    pf["partido_norm"] = pf["siglaPartido"].astype(str).str.upper().str.strip()
    pf["d_centrao"] = pf["partido_norm"].isin(CENTRAO_PARTIES).astype(int)

    cen = pf[pf["d_centrao"] == 1].copy()
    cen_ori = (cen.groupby(["idVotacao", "partido_norm"])
                  .agg({"d_ori_part_sim": "first", "d_ori_part_nao": "first",
                        "d_ori_part_obstrucao": "first"})
                  .reset_index())
    log.info(f"    {len(cen_ori):,} pares (partido, votacao) do Centrao")

    by_vot = cen_ori.groupby("idVotacao").agg(
        n_sim=("d_ori_part_sim", "sum"),
        n_nao=("d_ori_part_nao", "sum"),
        n_obs=("d_ori_part_obstrucao", "sum"),
    ).reset_index()

    def consolida(row):
        sim, nao, obs = row["n_sim"], row["n_nao"], row["n_obs"]
        max_count = max(sim, nao, obs)
        if max_count < MAIORIA_THRESHOLD:
            return np.nan
        if (sim == max_count) and (nao < max_count) and (obs < max_count):
            return "Sim"
        if (nao == max_count) and (sim < max_count) and (obs < max_count):
            return "Não"
        if (obs == max_count) and (sim < max_count) and (nao < max_count):
            return "Obstrução"
        return np.nan  # empate

    by_vot["ori_centrao_maj"] = by_vot.apply(consolida, axis=1)
    n_with = by_vot["ori_centrao_maj"].notna().sum()
    log.info(f"    Votacoes com orientacao Centrao majoritaria: {n_with:,}/{len(by_vot):,} ({100*n_with/len(by_vot):.1f}%)")

    # Merge orientation back into the full panel (each row gets the ori of its votacao)
    voto_map = pf[["idDeputado", "idVotacao", "voto"]]
    df = df.drop(columns=[c for c in ["voto", "siglaPartido"] if c in df.columns])
    df = df.merge(voto_map, on=["idDeputado", "idVotacao"], how="left")
    df = df.merge(by_vot[["idVotacao", "ori_centrao_maj"]], on="idVotacao", how="left")

    df["y_centrao_orient"] = (df["voto"] == df["ori_centrao_maj"]).astype(int)
    df.loc[df["ori_centrao_maj"].isna(), "y_centrao_orient"] = np.nan

    n_total = len(df)
    n_with_outcome = df["y_centrao_orient"].notna().sum()
    log.info(f"  Panel total: {n_total:,}, com y_centrao_orient: {n_with_outcome:,} ({100*n_with_outcome/n_total:.1f}%)")
    log.info(f"  Leg 55 mean: {df[df['idLegislatura']==55]['y_centrao_orient'].mean():.4f}")
    log.info(f"  Leg 56 mean: {df[df['idLegislatura']==56]['y_centrao_orient'].mean():.4f}")

    # Now apply outcome substitution & merge multi-RP + proxies + MDS
    n_before = len(df)
    df = df.dropna(subset=["y_centrao_orient"])
    log.info(f"  Dropped {n_before - len(df):,} rows without majority centrao orientation")
    df["alinhamento"] = df["y_centrao_orient"].astype(int)

    log.info("[0.4] Merging multi-RP")
    mr = pd.read_csv(INTERIM / "panel_emendas_pre_multi_rp.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    mr["idDeputado"] = mr["idDeputado"].astype(str)
    mr_cols = ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60", "T_rp9_imputed_pre60"]
    df = df.merge(mr[["idDeputado", "idVotacao"] + mr_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in mr_cols:
        df[c] = df[c].fillna(0)
        df[c + "_M"] = df[c] / 1e6

    log.info("[0.5] Merging proxies")
    px = pd.read_csv(INTERIM / "panel_secret_budget_proxies.csv", sep=";",
                     dtype={"idDeputado": str}, low_memory=False)
    px["idDeputado"] = px["idDeputado"].astype(str)
    px_cols = ["d_rp9_solicitante", "share_pork_opaco", "share_rp9",
               "share_pix", "n_apoiamentos_opaco"]
    df = df.merge(px[["idDeputado", "idVotacao"] + px_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in px_cols:
        df[c] = df[c].fillna(0)

    log.info("[0.6] Attaching MDS")
    df = attach_pol_paper(df)

    # Reconstruir siglaPartido + d_centrao_party para uso em T5
    df = df.merge(pf[["idDeputado", "idVotacao", "siglaPartido"]],
                  on=["idDeputado", "idVotacao"], how="left")
    df["d_centrao_party"] = df["siglaPartido"].astype(str).str.upper().str.strip().isin(CENTRAO_PARTIES).astype(int)

    log.info(f"  Final panel: {len(df):,} × {len(df.columns)} cols")
    return df


def safe_pliv(df_l, controls, label, tag=""):
    log.info(f"  --> PLIV: {label}  (n={len(df_l):,}, clusters={df_l['idDeputado'].nunique()})")
    if len(df_l) < 5000:
        log.warning(f"     [WARN] too small")
        return None
    controls = list(dict.fromkeys(controls))
    bad = [c for c in controls if c in (
        "alinhamento", "emenda_M", "idDeputado", "y_centrao_orient",
        "voto", "ori_centrao_maj", "d_centrao_party", "siglaPartido",
    )]
    if bad:
        controls = [c for c in controls if c not in bad]
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


def save_incremental(rows, fname):
    if not rows: return
    pd.DataFrame(rows).to_csv(RESULTS / fname, sep=";", index=False)
    log.info(f"  >> saved {fname} ({len(rows)} rows)")


# ============================================================
# T3 OLS mediation Pix
# ============================================================
def run_t3(df):
    log.info("\n" + "="*70)
    log.info("T3 (Centrao orient): OLS mediation Pix")
    log.info("="*70)
    append("\n### T3 - Centrao orient (OLS mediation)\n")
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant

    rows = []
    for leg_label, leg in [("pooled", None), ("leg55", 55), ("leg56", 56)]:
        df_l = df.copy() if leg is None else df[df["idLegislatura"] == leg].copy()
        df_l = df_l.dropna(subset=["alinhamento", "emenda_M", "share_pix"])
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
        indirect = theta_TM * gamma_M
        prop = indirect / beta_T_total if beta_T_total != 0 else np.nan
        rows.append({"leg": leg_label, "theta_TM": round(theta_TM,4),
                     "beta_T_direct": round(beta_T_direct,4),
                     "gamma_M": round(gamma_M,4),
                     "beta_T_total": round(beta_T_total,4),
                     "indirect_effect": round(indirect,4),
                     "prop_mediated": round(prop,4), "n_obs": len(df_l)})
        log.info(f"  {leg_label}: total={beta_T_total:.4f} indirect={indirect:.4f} prop={prop:.2%}")
        append(f"- {leg_label}: total={beta_T_total:+.4f}, indirect={indirect:+.4f}, prop_med={prop*100:+.1f}%, n={len(df_l):,}")
        save_incremental(rows, "n3_centrao_orient_t3_mediation_pix.csv")


# ============================================================
# T5 Centrao sub-samples
# ============================================================
def run_t5(df):
    log.info("\n" + "="*70)
    log.info("T5 (Centrao orient): sub-samples")
    log.info("="*70)
    append("\n### T5 - sub-samples\n")
    df["data"] = pd.to_datetime(df["data"])
    ctrl_full = U2.get_clean_full_controls(df)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]

    rows = []
    samples = [
        ("leg55_full", df["idLegislatura"] == 55),
        ("leg56_full", df["idLegislatura"] == 56),
        ("leg56_pre_lira", (df["idLegislatura"] == 56) & (df["data"] < "2021-02-01")),
        ("leg56_post_lira", (df["idLegislatura"] == 56) & (df["data"] >= "2021-02-01")),
        ("leg56_post_lira_excl_centrao",
         (df["idLegislatura"] == 56) & (df["data"] >= "2021-02-01") & (df["d_centrao_party"] == 0)),
    ]
    for label, mask in samples:
        sub = df[mask].copy()
        res = safe_pliv(sub, ctrl, f"T5 {label}", tag="T5")
        if res:
            res["sample"] = label
            res["y_centrao_orient_mean"] = round(sub["alinhamento"].mean(), 4)
            rows.append(res)
            save_incremental(rows, "n3_centrao_orient_t5_subsamples.csv")


# ============================================================
# T2 Het RP-9 exposure
# ============================================================
def run_t2(df):
    log.info("\n" + "="*70)
    log.info("T2 (Centrao orient): Het RP-9 exposure, Leg 56")
    log.info("="*70)
    append("\n### T2 - RP-9 exposure (Leg 56)\n")
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
            save_incremental(rows, "n3_centrao_orient_t2_het.csv")


# ============================================================
# T4 Tercis MDS
# ============================================================
def run_t4(df):
    log.info("\n" + "="*70)
    log.info("T4 (Centrao orient): tercis MDS-Eucl/Weak/Strong by leg")
    log.info("="*70)
    append("\n### T4 - tercis MDS\n")
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
                df_l["tercil"] = pd.qcut(df_l[col], 3, labels=["low", "mid", "high"], duplicates="drop")
            except: continue
            for tlabel in ["low", "mid", "high"]:
                sub = df_l[df_l["tercil"] == tlabel]
                res = safe_pliv(sub, ctrl, f"T4 {mlabel} leg={leg} tercil={tlabel}", tag="T4")
                if res:
                    res.update({"measure": mlabel, "leg": leg, "tercil": tlabel,
                                "n_obs_tercil": len(sub)})
                    rows.append(res)
                    save_incremental(rows, "n3_centrao_orient_t4_tercis.csv")


# ============================================================
# T1 IV with proxies
# ============================================================
def run_t1(df):
    log.info("\n" + "="*70)
    log.info("T1 (Centrao orient): IV-DML base vs base+proxies")
    log.info("="*70)
    append("\n### T1 - IV with proxies\n")
    ctrl_full = U2.get_clean_full_controls(df)
    ctrl_base = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    rows = []
    for leg in [55, 56]:
        df_l = df[df["idLegislatura"] == leg].copy()
        res_b = safe_pliv(df_l, ctrl_base, f"T1 leg={leg} base_pure", tag="T1")
        if res_b:
            res_b.update({"spec": "base_pure", "leg": leg})
            rows.append(res_b)
            save_incremental(rows, "n3_centrao_orient_t1_iv.csv")
        ctrl_aug = list(dict.fromkeys(ctrl_base + EXTRA_PROXIES))
        res_a = safe_pliv(df_l, ctrl_aug, f"T1 leg={leg} base+proxies", tag="T1")
        if res_a:
            res_a.update({"spec": "base_plus_proxies", "leg": leg})
            rows.append(res_a)
            save_incremental(rows, "n3_centrao_orient_t1_iv.csv")


if __name__ == "__main__":
    init_progress()
    log.info("FULL FOLLOWUP CENTRAO ORIENT (ex-ante) — n_folds=3, n_reps=3")
    log.info(f"Start: {datetime.now().isoformat()}")
    t0 = time.time()

    df = load_panel_with_y_centrao_orient()

    log.info("\n[Phase 1: T3 OLS — fast]")
    run_t3(df)
    log.info("\n[Phase 2: T5 sub-samples — 5 PLIVs]")
    run_t5(df)
    log.info("\n[Phase 3: T2 het — 2 PLIVs]")
    run_t2(df)
    log.info("\n[Phase 4: T4 tercis — 18 PLIVs]")
    run_t4(df)
    log.info("\n[Phase 5: T1 IV with proxies — 4 PLIVs]")
    run_t1(df)

    elapsed = (time.time() - t0) / 3600
    log.info(f"\n\nDONE in {elapsed:.2f} hours")
    append(f"\n## End: {datetime.now().isoformat()} ({elapsed:.2f}h)")
