"""
50_full_followup_n3.py
-----------------------
Rodada DEFINITIVA do follow-up: replica a configuracao EXATA do main paper
(`n_folds=3, n_reps=3`) para garantir reprodutibilidade dos resultados que
entram na versao final do paper.

Substitui as rodadas 36_, 41_, 42_, 43_ que usavam n_reps=1 (rapido mas com
variancia Monte Carlo alta).

Analises (cada uma escrita ASSIM QUE TERMINA):
T1. IV-DML com proxies (8 PLIVs)
T2. Heterogeneidade por exposicao RP-9 (4 PLIVs)
T3. Mediation Acharya-Blackwell-Sen com Pix (6 OLS, deterministic)
T4. Tercis MDS por leg (36 PLIVs)
T5. Centrao em sub-amostras (5 PLIVs)

Total: ~53 PLIV-DML com n_reps=3 + 6 OLS → 24-48 horas.

Safety checks completos por etapa:
- Volume (n_obs, n_clusters, n_controls)
- Colunas nulas (% non-null)
- Valores extremos (min/max/p99)
- Duplicatas
- Tipos
- Reprodutibilidade do panel base

Outputs (todos no diretorio results/ com prefixo n3_):
    n3_t1_iv_<outcome>.csv          (incremental, escrito por leg)
    n3_t2_het_<outcome>.csv         (incremental)
    n3_t3_mediation_pix_<outcome>.csv
    n3_t4_tercis_<outcome>.csv      (incremental)
    n3_t5_centrao_subsamples.csv    (incremental)
    n3_progress.md                  (markdown progressivo, atualizado a cada PLIV)
    n3_full.log                     (log persistente)

STATE_OF_PLAY.md tambem e' atualizado com cada novo resultado.
"""

import logging
import sys
import traceback
import warnings
import time
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")

POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
INTERIM = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
PROGRESS_MD = RESULTS / "n3_progress.md"
LOG_FILE = RESULTS / "n3_full.log"
STATE_MD = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-emendas/STATE_OF_PLAY.md")

CENTRAO_PARTIES = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE",
                   "UNIAO", "PTB", "AVANTE", "PSD", "MDB"}

# CONFIG IDENTICA AO MAIN PAPER
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


# ============================================================================
# Logging persistente
# ============================================================================

# Logger -> stdout E -> arquivo
log = logging.getLogger("n3")
log.setLevel(logging.INFO)
# Limpar handlers existentes
for h in list(log.handlers):
    log.removeHandler(h)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
sh = logging.StreamHandler(sys.stdout); sh.setFormatter(fmt); log.addHandler(sh)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
fh = logging.FileHandler(LOG_FILE, mode="a"); fh.setFormatter(fmt); log.addHandler(fh)


# ============================================================================
# Progress writer
# ============================================================================

def init_progress():
    PROGRESS_MD.write_text(
        f"# n3 follow-up progress\n\n"
        f"Started: {datetime.now().isoformat()}\n\n"
        f"Config: n_folds={N_FOLDS}, n_reps={N_REPS} (identico ao main paper)\n\n"
        f"## Resultados em ordem de conclusao\n\n"
    )


def append_progress(line):
    with open(PROGRESS_MD, "a") as f:
        f.write(line + "\n")


def append_result(analysis, label, theta, ci_lo, ci_hi, pval, n_obs, extra=""):
    stars = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.10 else ""
    line = (f"- **{datetime.now().strftime('%H:%M:%S')}** [{analysis}] {label}: "
            f"theta = {theta:+.4f} pp/R$M{stars} "
            f"CI [{ci_lo:+.3f}, {ci_hi:+.3f}] "
            f"p = {pval:.4f}, n = {n_obs:,}{extra}")
    append_progress(line)


def append_section(title):
    with open(PROGRESS_MD, "a") as f:
        f.write(f"\n### {title}\n\n")


# ============================================================================
# Safety check helpers
# ============================================================================

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


def diagnose_col(df, col, label=""):
    """Diagnostica uma coluna: tipo, nulls, unique, distribuicao."""
    if col not in df.columns:
        log.warning(f"  [{label}] {col}: MISSING")
        return
    s = df[col]
    n_na = s.isna().sum()
    pct_na = 100 * n_na / len(s) if len(s) > 0 else 0
    try:
        log.info(f"  [{label}] {col}: dtype={s.dtype}, n={len(s):,}, na={n_na:,} ({pct_na:.1f}%), "
                 f"nunique={s.nunique()}, mean={s.mean():.4f}, "
                 f"min={s.min():.4f}, p99={s.quantile(0.99):.4f}, max={s.max():.4f}")
    except Exception:
        log.info(f"  [{label}] {col}: dtype={s.dtype}, n={len(s):,}, na={n_na:,} ({pct_na:.1f}%), nunique={s.nunique()}")


def diagnose_panel(df, name=""):
    """Diagnostico completo do painel."""
    log.info(f"\n--- Diagnostico panel: {name} ---")
    log.info(f"  shape: {df.shape}")
    log.info(f"  memoria: {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")

    # Colunas core
    for col in ["alinhamento", "emenda_M", "idLegislatura", "idDeputado"]:
        diagnose_col(df, col, "core")

    # T_rp* multi-RP
    for col in ["T_rp6_pre60_M", "T_rp6_pix_pre60_M", "T_rp8_pre60_M",
                "T_rp9_imputed_pre60_M"]:
        diagnose_col(df, col, "multi-RP")

    # Proxies
    for col in ["d_rp9_solicitante", "share_pix", "share_pork_opaco"]:
        diagnose_col(df, col, "proxy")

    # MDS
    for col in ["pol_paper_euclidean_mds", "pol_paper_forte_mds", "pol_paper_fraca_mds"]:
        diagnose_col(df, col, "MDS")

    # Sample por leg
    log.info("  por legislatura:")
    for leg in [55, 56]:
        sub = df[df["idLegislatura"] == leg]
        n_aligned = sub["alinhamento"].notna().sum() if "alinhamento" in sub.columns else 0
        log.info(f"    Leg {leg}: n={len(sub):,}, aligned_non_null={n_aligned:,}")

    # Duplicatas
    n_dup = df.duplicated(["idDeputado", "idVotacao"]).sum() if "idVotacao" in df.columns else 0
    log.info(f"  duplicatas (idDeputado, idVotacao): {n_dup}")
    check("sem duplicatas", n_dup == 0)


def attach_pol_paper(df):
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name in ["euclidean", "forte", "fraca"]:
        path = POL_PAPER_DIR / f"average_mds_distances_{name}.csv"
        check(f"MDS file exists: {name}", path.exists(), f"path={path}")
        pol = pd.read_csv(path)
        check(f"MDS {name} has period/Eucl cols",
              all(c in pol.columns for c in ["period_start", "period_end", "Euclidiana_MDS"]))
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        col = f"pol_paper_{name}_mds"
        df[col] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col] = r["Euclidiana_MDS"]
        nn = df[col].notna().sum()
        log.info(f"  attached {col}: {nn:,}/{len(df):,} ({100*nn/len(df):.1f}%)")
        check(f"MDS {name} coverage >= 95%", nn / len(df) >= 0.95)
    return df


# ============================================================================
# Panel loaders
# ============================================================================

def load_base_panel():
    log.info("="*70)
    log.info("STEP 0: Loading base panel + multi-RP + proxies + MDS")
    log.info("="*70)

    log.info("[0.1] Base panel via U.load_modeling_panel")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    check("base panel non-empty", len(df) > 0)
    for c in ["idDeputado", "idVotacao", "alinhamento", "emenda_M", "idLegislatura", "data"]:
        check(f"col {c} present", c in df.columns)
    df["idDeputado"] = df["idDeputado"].astype(str)

    log.info("[0.2] Merging voto/siglaPartido (para y_centrao)")
    pf = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "idVotacao", "voto", "siglaPartido"],
                     dtype=str, low_memory=False)
    pf["idDeputado"] = pf["idDeputado"].astype(str)
    for c in ["voto", "siglaPartido"]:
        if c in df.columns:
            df = df.drop(columns=[c])
    n_before = len(df)
    df = df.merge(pf, on=["idDeputado", "idVotacao"], how="left")
    check("voto/partido merge preserves rows", len(df) == n_before)
    diagnose_col(df, "voto", "voto/partido")
    diagnose_col(df, "siglaPartido", "voto/partido")

    log.info("[0.3] Merging multi-RP")
    mr_path = INTERIM / "panel_emendas_pre_multi_rp.csv"
    check("multi-RP file exists", mr_path.exists())
    mr = pd.read_csv(mr_path, sep=";", dtype={"idDeputado": str}, low_memory=False)
    mr["idDeputado"] = mr["idDeputado"].astype(str)
    mr_cols = ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60", "T_rp9_imputed_pre60"]
    for c in mr_cols:
        check(f"mr col {c} present", c in mr.columns)
    n_before = len(df)
    df = df.merge(mr[["idDeputado", "idVotacao"] + mr_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    check("multi-RP merge preserves rows", len(df) == n_before)
    for c in mr_cols:
        df[c] = df[c].fillna(0)
        df[c + "_M"] = df[c] / 1e6

    log.info("[0.4] Merging proxies")
    px_path = INTERIM / "panel_secret_budget_proxies.csv"
    check("proxies file exists", px_path.exists())
    px = pd.read_csv(px_path, sep=";", dtype={"idDeputado": str}, low_memory=False)
    px["idDeputado"] = px["idDeputado"].astype(str)
    px_cols = ["d_rp9_solicitante", "share_pork_opaco", "share_rp9",
               "share_pix", "n_apoiamentos_opaco"]
    for c in px_cols:
        check(f"px col {c} present", c in px.columns)
    n_before = len(df)
    df = df.merge(px[["idDeputado", "idVotacao"] + px_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    check("proxies merge preserves rows", len(df) == n_before)
    for c in px_cols:
        df[c] = df[c].fillna(0)

    log.info("[0.5] Attaching MDS measures")
    df = attach_pol_paper(df)

    log.info("[0.6] Diagnostico final do painel")
    diagnose_panel(df, "base panel after all merges")

    return df


def add_y_centrao(df):
    log.info("\n" + "="*70)
    log.info("STEP 0.7: Building y_centrao")
    log.info("="*70)
    df = df.copy()
    df["d_centrao_party"] = df["siglaPartido"].astype(str).str.upper().str.strip().isin(CENTRAO_PARTIES).astype(int)
    n_centrao = (df["d_centrao_party"] == 1).sum()
    log.info(f"  Centrao deputies in panel: {n_centrao:,} ({100*n_centrao/len(df):.1f}%)")

    cen = df[df["d_centrao_party"] == 1]
    cen_major = cen.groupby("idVotacao")["voto"].apply(
        lambda s: s.value_counts().index[0] if not s.value_counts().empty else np.nan
    ).reset_index().rename(columns={"voto": "voto_centrao_major"})
    log.info(f"  Centrao majority computed for {len(cen_major):,} votacoes")

    df = df.merge(cen_major, on="idVotacao", how="left")
    df["y_centrao"] = (df["voto"] == df["voto_centrao_major"]).astype(int)
    df.loc[df["voto_centrao_major"].isna(), "y_centrao"] = np.nan

    diagnose_col(df, "y_centrao", "outcome")
    nn = df["y_centrao"].notna().sum()
    log.info(f"  Leg 55 y_centrao mean: {df[df['idLegislatura']==55]['y_centrao'].mean():.4f}")
    log.info(f"  Leg 56 y_centrao mean: {df[df['idLegislatura']==56]['y_centrao'].mean():.4f}")
    return df


def get_outcome_df(df, outcome):
    df = df.copy()
    if outcome == "gov":
        log.info(f"  [outcome=gov] using original alinhamento, n={len(df):,}")
    elif outcome == "centrao":
        n_before = len(df)
        df = df.dropna(subset=["y_centrao"])
        df["alinhamento"] = df["y_centrao"].astype(int)
        log.info(f"  [outcome=centrao] dropped {n_before - len(df):,} rows with NaN y_centrao; "
                 f"n={len(df):,}, alinhamento mean = {df['alinhamento'].mean():.4f}")
    else:
        raise ValueError(f"unknown outcome: {outcome}")
    return df


# ============================================================================
# PLIV wrapper
# ============================================================================

def safe_pliv(df_l, controls, label, analysis_tag=""):
    log.info(f"  --> PLIV: {label}")
    log.info(f"     n={len(df_l):,}, clusters={df_l['idDeputado'].nunique()}")
    if len(df_l) < 5000:
        log.warning(f"     [WARN] too small ({len(df_l)})")
        return None
    controls = list(dict.fromkeys(controls))
    bad = [c for c in controls if c in (
        "alinhamento", "emenda_M", "idDeputado", "y_centrao",
        "voto", "voto_centrao_major", "d_centrao_party",
    )]
    if bad:
        controls = [c for c in controls if c not in bad]
    valid_ctrl = [c for c in controls if c in df_l.columns
                  and df_l[c].notna().mean() > 0.5
                  and df_l[c].nunique() > 1]
    log.info(f"     valid ctrls: {len(valid_ctrl)} (of {len(controls)})")
    t0 = time.time()
    try:
        res = U2.run_pliv_main(df_l, controls=valid_ctrl, iv_set="backlog",
                                n_folds=N_FOLDS, n_reps=N_REPS)
        elapsed = time.time() - t0
        if res is None:
            log.warning("     [WARN] PLIV returned None")
            return None
        log.info(f"     [OK] theta={res['pp_per_unit']:+.4f} pp, p={res['pval']:.4f} ({elapsed:.1f}s)")
        # Append imediato no progress
        if analysis_tag:
            append_result(analysis_tag, label,
                          res['pp_per_unit'], res['ci95_lo_pp'], res['ci95_hi_pp'],
                          res['pval'], res['n_obs'])
        return res
    except Exception as e:
        log.error(f"     [FAIL] {e}\n{traceback.format_exc()}")
        return None


def save_incremental(rows, fname, cols_display=None):
    """Salva CSV incremental e printa resumo."""
    if not rows: return
    out = pd.DataFrame(rows)
    path = RESULTS / fname
    out.to_csv(path, sep=";", index=False)
    log.info(f"  >> saved {fname} ({len(out)} rows)")
    if cols_display:
        print(out[cols_display].to_string(index=False))


# ============================================================================
# T1 — IV-DML com proxies
# ============================================================================

def run_t1(df, outcome):
    log.info("\n" + "="*70)
    log.info(f"T1 ({outcome}): IV-DML base vs base+proxies")
    log.info("="*70)
    append_section(f"T1 - {outcome}")
    df_o = get_outcome_df(df, outcome)
    ctrl_full = U2.get_clean_full_controls(df_o)
    ctrl_base = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    excluded = [c for c in ctrl_full if c in EXTRA_TREATMENT_VARS]
    log.info(f"  ctrl_full={len(ctrl_full)}, ctrl_base={len(ctrl_base)}")
    log.info(f"  excluded: {excluded}")

    rows = []
    for leg in [55, 56]:
        df_l = df_o[df_o["idLegislatura"] == leg].copy()
        log.info(f"\n[T1 {outcome} Leg {leg}] n={len(df_l):,}")

        res_base = safe_pliv(df_l, ctrl_base, f"T1 {outcome} leg={leg} base_pure",
                              analysis_tag=f"T1-{outcome}")
        if res_base:
            res_base.update({"spec": "base_pure", "leg": leg, "outcome": outcome})
            rows.append(res_base)
            save_incremental(rows, f"n3_t1_iv_{outcome}.csv")

        ctrl_aug = list(dict.fromkeys(ctrl_base + EXTRA_PROXIES))
        res_aug = safe_pliv(df_l, ctrl_aug, f"T1 {outcome} leg={leg} base+proxies",
                             analysis_tag=f"T1-{outcome}")
        if res_aug:
            res_aug.update({"spec": "base_plus_proxies", "leg": leg, "outcome": outcome})
            rows.append(res_aug)
            save_incremental(rows, f"n3_t1_iv_{outcome}.csv")


# ============================================================================
# T2 — Heterogeneidade RP-9
# ============================================================================

def run_t2(df, outcome):
    log.info("\n" + "="*70)
    log.info(f"T2 ({outcome}): Het Leg 56 by RP-9 exposure")
    log.info("="*70)
    append_section(f"T2 - {outcome}")
    df_o = get_outcome_df(df, outcome)
    df_56 = df_o[df_o["idLegislatura"] == 56].copy()
    df_56["d_rp9_exposed"] = (df_56["d_rp9_solicitante"] == 1).astype(int)
    ctrl_full = U2.get_clean_full_controls(df_56)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    n_exp = int(df_56["d_rp9_exposed"].sum())
    log.info(f"  n_exposed={n_exp:,} of {len(df_56):,} ({100*n_exp/len(df_56):.2f}%)")
    log.info(f"  ctrl: {len(ctrl)} cols")

    rows = []
    for label, mask in [
        ("rp9_exposed", df_56["d_rp9_exposed"] == 1),
        ("rp9_not_exposed", df_56["d_rp9_exposed"] == 0),
    ]:
        sub = df_56[mask].copy()
        res = safe_pliv(sub, ctrl, f"T2 {outcome} {label}",
                         analysis_tag=f"T2-{outcome}")
        if res:
            res.update({"subgroup": label, "outcome": outcome})
            rows.append(res)
            save_incremental(rows, f"n3_t2_het_{outcome}.csv")


# ============================================================================
# T3 — Mediation com Pix
# ============================================================================

def run_t3(df, outcome):
    log.info("\n" + "="*70)
    log.info(f"T3 ({outcome}): ABS mediation with share_pix (OLS, deterministic)")
    log.info("="*70)
    append_section(f"T3 - {outcome} (OLS mediation)")
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant

    df_o = get_outcome_df(df, outcome)
    rows = []
    for leg_label, leg in [("pooled", None), ("leg55", 55), ("leg56", 56)]:
        df_l = df_o.copy() if leg is None else df_o[df_o["idLegislatura"] == leg].copy()
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
            "outcome": outcome, "leg": leg_label,
            "theta_TM": round(theta_TM, 4),
            "beta_T_direct": round(beta_T_direct, 4),
            "gamma_M": round(gamma_M, 4),
            "beta_T_total": round(beta_T_total, 4),
            "indirect_effect": round(indirect, 4),
            "prop_mediated": round(prop_med, 4),
            "n_obs": len(df_l),
        })
        log.info(f"  {leg_label}: total={beta_T_total:.4f}, indirect={indirect:.4f}, prop={prop_med:.2%}")
        append_progress(
            f"- **T3-{outcome}** {leg_label}: total={beta_T_total:+.4f}, "
            f"indirect={indirect:+.4f}, prop_mediated={prop_med*100:+.1f}%, n={len(df_l):,}"
        )
        save_incremental(rows, f"n3_t3_mediation_pix_{outcome}.csv")


# ============================================================================
# T4 — Tercis MDS por leg
# ============================================================================

def run_t4(df, outcome):
    log.info("\n" + "="*70)
    log.info(f"T4 ({outcome}): tercis MDS-Eucl/Weak/Strong by leg")
    log.info("="*70)
    append_section(f"T4 - {outcome}")
    df_o = get_outcome_df(df, outcome)
    ctrl_full = U2.get_clean_full_controls(df_o)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    ctrl = [c for c in ctrl if not c.startswith("pol_")]
    log.info(f"  ctrl: {len(ctrl)} cols (excluded pol_*)")

    rows = []
    for col, label in [
        ("pol_paper_euclidean_mds", "MDS-Euclidean"),
        ("pol_paper_fraca_mds", "MDS-Weak"),
        ("pol_paper_forte_mds", "MDS-Strong"),
    ]:
        if col not in df_o.columns:
            log.warning(f"  skip {col}")
            continue
        for leg in [55, 56]:
            df_l = df_o[df_o["idLegislatura"] == leg].copy()
            df_l = df_l.dropna(subset=[col])
            if len(df_l) < 5000:
                continue
            try:
                df_l["tercil"] = pd.qcut(df_l[col], 3, labels=["low", "mid", "high"],
                                           duplicates="drop")
            except Exception as e:
                log.error(f"  qcut failed: {e}")
                continue
            for tlabel in ["low", "mid", "high"]:
                sub = df_l[df_l["tercil"] == tlabel]
                res = safe_pliv(sub, ctrl, f"T4 {outcome} {label} leg={leg} tercil={tlabel}",
                                 analysis_tag=f"T4-{outcome}")
                if res:
                    res.update({"measure": label, "leg": leg, "tercil": tlabel,
                                "n_obs_tercil": len(sub), "outcome": outcome})
                    rows.append(res)
                    save_incremental(rows, f"n3_t4_tercis_{outcome}.csv")


# ============================================================================
# T5 — Centrao sub-amostras
# ============================================================================

def run_t5(df):
    log.info("\n" + "="*70)
    log.info("T5: Centrao outcome sub-samples")
    log.info("="*70)
    append_section("T5 - centrao sub-samples")
    df_o = get_outcome_df(df, "centrao")
    df_o["d_centrao_party"] = df_o["siglaPartido"].astype(str).str.upper().str.strip().isin(CENTRAO_PARTIES).astype(int)
    df_o["data"] = pd.to_datetime(df_o["data"])
    ctrl_full = U2.get_clean_full_controls(df_o)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]

    rows = []
    samples = [
        ("leg55_full", df_o["idLegislatura"] == 55),
        ("leg56_full", df_o["idLegislatura"] == 56),
        ("leg56_pre_lira", (df_o["idLegislatura"] == 56) & (df_o["data"] < "2021-02-01")),
        ("leg56_post_lira", (df_o["idLegislatura"] == 56) & (df_o["data"] >= "2021-02-01")),
        ("leg56_post_lira_excl_centrao",
         (df_o["idLegislatura"] == 56) & (df_o["data"] >= "2021-02-01") & (df_o["d_centrao_party"] == 0)),
    ]
    for label, mask in samples:
        sub = df_o[mask].copy()
        res = safe_pliv(sub, ctrl, f"T5 {label}", analysis_tag="T5")
        if res:
            res["sample"] = label
            res["y_centrao_mean"] = round(sub["alinhamento"].mean(), 4)
            rows.append(res)
            save_incremental(rows, "n3_t5_centrao_subsamples.csv")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    init_progress()
    log.info("="*70)
    log.info(f"FULL FOLLOWUP n_folds={N_FOLDS} n_reps={N_REPS}")
    log.info("="*70)
    log.info(f"Start: {datetime.now().isoformat()}")
    log.info(f"Logs: {LOG_FILE}")
    log.info(f"Progress: {PROGRESS_MD}")

    t_start = time.time()
    df = load_base_panel()
    df = add_y_centrao(df)

    log.info("\n[Phase 1: T3 OLS mediation — fast, deterministic]")
    run_t3(df, "gov")
    run_t3(df, "centrao")

    log.info("\n[Phase 2: T5 Centrao sub-samples — 5 PLIVs]")
    run_t5(df)

    log.info("\n[Phase 3: T2 RP-9 exposure heterogeneity — 4 PLIVs]")
    run_t2(df, "gov")
    run_t2(df, "centrao")

    log.info("\n[Phase 4: T4 tercis MDS — 36 PLIVs (18 each outcome)]")
    run_t4(df, "gov")
    run_t4(df, "centrao")

    log.info("\n[Phase 5: T1 IV with proxies — 8 PLIVs (4 each outcome)]")
    run_t1(df, "gov")
    run_t1(df, "centrao")

    elapsed_h = (time.time() - t_start) / 3600
    log.info("\n\n" + "="*70)
    log.info(f"ALL FOLLOWUP n3 COMPLETE in {elapsed_h:.2f} hours")
    log.info(f"End: {datetime.now().isoformat()}")
    log.info("="*70)
    append_progress(f"\n## End: {datetime.now().isoformat()} ({elapsed_h:.2f} hours)")
