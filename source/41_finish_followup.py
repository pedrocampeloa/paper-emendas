"""
41_finish_followup.py
----------------------
Finaliza o que faltou em 36_followup_analyses.py:
- T2: heterogeneidade RP-9 exposure (2 PLIVs em Leg 56)
- T4: tercis MDS por leg via attach_pol_paper (refaz com cols corretos)
- T1: leg 55 e leg 56 base + base+proxies (4 PLIVs)

Todos com safety checks e prints detalhados em cada etapa.

n_folds=2, n_reps=1 para velocidade.
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
log = logging.getLogger("finish")

POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
INTERIM = Path(C.PANEL)
RESULTS = Path(C.RESULTS)


# ============================================================================
# Safety check helpers
# ============================================================================

def check(name, cond, *details):
    """Assert with structured logging. Halts only on hard violations."""
    if cond:
        log.info(f"  [OK] {name}")
    else:
        log.error(f"  [FAIL] {name}")
        for d in details:
            log.error(f"         {d}")
        raise AssertionError(f"Safety check failed: {name}")


def warn(name, cond, *details):
    if not cond:
        log.warning(f"  [WARN] {name}")
        for d in details:
            log.warning(f"         {d}")


def describe_col(df, col, label=""):
    """Imprime perfil estatistico de uma coluna numerica."""
    if col not in df.columns:
        log.warning(f"  [{label}] col {col} MISSING")
        return
    s = df[col]
    log.info(f"  [{label}] col={col}: n={len(s)}, na={s.isna().sum()}, "
             f"n_unique={s.nunique()}, mean={s.mean():.4f}, "
             f"std={s.std():.4f}, min={s.min():.4f}, max={s.max():.4f}")


def attach_pol_paper(df):
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name in ["euclidean", "forte", "fraca"]:
        path = POL_PAPER_DIR / f"average_mds_distances_{name}.csv"
        check(f"MDS file exists: {name}", path.exists(),
              f"path = {path}")
        pol = pd.read_csv(path)
        check(f"MDS file has period cols: {name}",
              all(c in pol.columns for c in ["period_start", "period_end", "Euclidiana_MDS"]),
              f"cols = {pol.columns.tolist()}")
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        col = f"pol_paper_{name}_mds"
        df[col] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col] = r["Euclidiana_MDS"]
        n_non_null = df[col].notna().sum()
        log.info(f"  attached {col}: non-null={n_non_null:,} of {len(df):,} "
                 f"({100*n_non_null/len(df):.1f}%)")
        warn(f"{col} coverage >= 50%", n_non_null / len(df) >= 0.5,
             f"non_null = {n_non_null}, total = {len(df)}")
    return df


def load_augmented_panel():
    log.info("\n" + "="*70)
    log.info("STEP 0: Loading augmented panel")
    log.info("="*70)

    log.info("[0.1] Loading base panel via U.load_modeling_panel")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    check("base panel non-empty", len(df) > 0)
    check("base panel has idDeputado", "idDeputado" in df.columns)
    check("base panel has idVotacao", "idVotacao" in df.columns)
    check("base panel has alinhamento", "alinhamento" in df.columns)
    check("base panel has emenda_M", "emenda_M" in df.columns)
    check("base panel has idLegislatura", "idLegislatura" in df.columns)
    log.info(f"  base panel: {len(df):,} rows x {len(df.columns)} cols")

    log.info("\n[0.2] Loading multi-RP variables")
    mr_path = INTERIM / "panel_emendas_pre_multi_rp.csv"
    check("multi-RP file exists", mr_path.exists(), f"path={mr_path}")
    mr = pd.read_csv(mr_path, sep=";", dtype={"idDeputado": str}, low_memory=False)
    mr["idDeputado"] = mr["idDeputado"].astype(str)
    df["idDeputado"] = df["idDeputado"].astype(str)
    mr_cols = ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60", "T_rp9_imputed_pre60"]
    check("multi-RP has all expected cols", all(c in mr.columns for c in mr_cols),
          f"missing = {set(mr_cols) - set(mr.columns)}")
    log.info(f"  multi-RP: {len(mr):,} rows")

    n_before = len(df)
    df = df.merge(mr[["idDeputado", "idVotacao"] + mr_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    check("merge multi-RP preserves panel rows", len(df) == n_before,
          f"before = {n_before}, after = {len(df)}")
    for c in mr_cols:
        n_nonnull = df[c].notna().sum()
        df[c] = df[c].fillna(0)
        df[c + "_M"] = df[c] / 1e6
        log.info(f"  {c}: non-null after merge = {n_nonnull:,} of {len(df):,}")

    log.info("\n[0.3] Loading secret budget proxies")
    px_path = INTERIM / "panel_secret_budget_proxies.csv"
    check("proxies file exists", px_path.exists(), f"path={px_path}")
    px = pd.read_csv(px_path, sep=";", dtype={"idDeputado": str}, low_memory=False)
    px["idDeputado"] = px["idDeputado"].astype(str)
    px_cols = ["d_rp9_solicitante", "share_pork_opaco", "share_rp9",
               "share_pix", "n_apoiamentos_opaco"]
    check("proxies has all expected cols", all(c in px.columns for c in px_cols),
          f"missing = {set(px_cols) - set(px.columns)}")

    n_before = len(df)
    df = df.merge(px[["idDeputado", "idVotacao"] + px_cols],
                  on=["idDeputado", "idVotacao"], how="left")
    check("merge proxies preserves panel rows", len(df) == n_before)
    for c in px_cols:
        df[c] = df[c].fillna(0)
        describe_col(df, c, label="proxy")

    log.info("\n[0.4] Attaching MDS measures from paper-polarization")
    df = attach_pol_paper(df)
    for name in ["euclidean", "forte", "fraca"]:
        col = f"pol_paper_{name}_mds"
        check(f"MDS col exists post-attach: {col}", col in df.columns)

    log.info("\n[0.5] Final panel sanity checks")
    check("idLegislatura has both 55 and 56", set(df["idLegislatura"].dropna().unique()) >= {55, 56})
    check("alinhamento is binary", set(df["alinhamento"].dropna().unique()) <= {0, 1})
    check("no duplicate (idDeputado, idVotacao)",
          not df.duplicated(["idDeputado", "idVotacao"]).any())
    log.info(f"  final panel: {len(df):,} rows x {len(df.columns)} cols")

    return df


def safe_pliv(df_l, controls, label, iv_set="backlog", n_folds=2, n_reps=1):
    """Roda PLIV-DML com safety checks e error handling robusto."""
    log.info(f"\n  --> running PLIV: {label}")
    log.info(f"      n_obs = {len(df_l):,}, n_clusters = {df_l['idDeputado'].nunique()}")

    # Safety: minimo de observacoes
    if len(df_l) < 5000:
        log.warning(f"      [WARN] sample too small ({len(df_l)} < 5000), skipping")
        return None

    # Dedup controles (causa do bug original)
    controls = list(dict.fromkeys(controls))
    bad = [c for c in controls if c in ("alinhamento", "emenda_M", "idDeputado")]
    if bad:
        log.warning(f"      [WARN] removing target/treatment/cluster from controls: {bad}")
        controls = [c for c in controls if c not in bad]

    # Filtra colunas que existem e tem variabilidade
    valid_ctrl = []
    for c in controls:
        if c not in df_l.columns:
            continue
        if df_l[c].notna().mean() < 0.5:
            continue
        if df_l[c].nunique() < 2:
            continue
        valid_ctrl.append(c)
    log.info(f"      valid controls: {len(valid_ctrl)} of {len(controls)}")

    try:
        res = U2.run_pliv_main(df_l, controls=valid_ctrl, iv_set=iv_set,
                                n_folds=n_folds, n_reps=n_reps)
        if res is None:
            log.warning(f"      [WARN] PLIV returned None")
            return None
        log.info(f"      [OK] theta = {res.get('pp_per_unit', '?')} pp/R$M, "
                 f"pval = {res.get('pval', '?')}")
        return res
    except Exception as e:
        log.error(f"      [FAIL] PLIV raised exception: {e}")
        log.error(traceback.format_exc())
        return None


def t1_iv_with_proxies(df):
    log.info("\n" + "="*70)
    log.info("T1: IV-DML with secret-budget proxies as controls")
    log.info("="*70)
    ctrl_base = U2.get_clean_full_controls(df)
    log.info(f"[T1] ctrl_base: {len(ctrl_base)} cols")
    extra = ["d_rp9_solicitante", "share_pork_opaco", "share_pix",
             "T_rp9_imputed_pre60_M"]
    log.info(f"[T1] extra proxies: {extra}")

    rows = []
    for leg in [55, 56]:
        df_l = df[df["idLegislatura"] == leg].copy()
        log.info(f"\n[T1] Leg {leg}: n = {len(df_l):,}")
        res_base = safe_pliv(df_l, ctrl_base, f"T1 leg={leg} base")
        if res_base:
            res_base["spec"] = "base"
            res_base["leg"] = leg
            rows.append(res_base)

        ctrl_aug = ctrl_base + [c for c in extra if c not in ctrl_base]
        ctrl_aug = list(dict.fromkeys(ctrl_aug))
        log.info(f"[T1] ctrl_aug: {len(ctrl_aug)} cols (added {len(ctrl_aug)-len(ctrl_base)} proxies)")
        res_aug = safe_pliv(df_l, ctrl_aug, f"T1 leg={leg} base+proxies")
        if res_aug:
            res_aug["spec"] = "base_plus_proxies"
            res_aug["leg"] = leg
            rows.append(res_aug)

    if rows:
        out = pd.DataFrame(rows)
        out_path = RESULTS / "followup_t1_iv_with_rp9_controls.csv"
        out.to_csv(out_path, sep=";", index=False)
        log.info(f"\n[T1] saved {out_path}")
        print(out[["leg", "spec", "pp_per_unit", "ci95_lo_pp", "ci95_hi_pp", "pval"]].to_string(index=False))


def t2_het_rp9_exposure(df):
    log.info("\n" + "="*70)
    log.info("T2: Heterogeneity Leg 56 by RP-9 exposure")
    log.info("="*70)
    df_56 = df[df["idLegislatura"] == 56].copy()
    df_56["d_rp9_exposed"] = (df_56["d_rp9_solicitante"] == 1).astype(int)
    log.info(f"[T2] Leg 56 n={len(df_56):,}, "
             f"exposed={int(df_56['d_rp9_exposed'].sum()):,}")
    ctrl = U2.get_clean_full_controls(df_56)

    rows = []
    for label, mask in [
        ("rp9_exposed", df_56["d_rp9_exposed"] == 1),
        ("rp9_not_exposed", df_56["d_rp9_exposed"] == 0),
    ]:
        sub = df_56[mask].copy()
        log.info(f"\n[T2] {label}: n={len(sub):,}")
        res = safe_pliv(sub, ctrl, f"T2 {label}")
        if res:
            res["subgroup"] = label
            rows.append(res)

    if rows:
        out = pd.DataFrame(rows)
        out_path = RESULTS / "followup_t2_het_rp9_exposure.csv"
        out.to_csv(out_path, sep=";", index=False)
        log.info(f"\n[T2] saved {out_path}")
        print(out[["subgroup", "pp_per_unit", "ci95_lo_pp", "ci95_hi_pp", "pval"]].to_string(index=False))


def t4_tercis_by_leg(df):
    log.info("\n" + "="*70)
    log.info("T4: Polarization terciles SEPARATED by legislature (MDS)")
    log.info("="*70)
    ctrl = U2.get_clean_full_controls(df)
    ctrl = [c for c in ctrl if not c.startswith("pol_")]
    log.info(f"[T4] ctrl: {len(ctrl)} cols (excluded pol_*)")

    rows = []
    measures = [
        ("pol_paper_euclidean_mds", "MDS-Euclidean"),
        ("pol_paper_fraca_mds", "MDS-Weak"),
        ("pol_paper_forte_mds", "MDS-Strong"),
    ]
    for col, label in measures:
        log.info(f"\n[T4] measure = {label} ({col})")
        if col not in df.columns:
            log.warning(f"  [WARN] {col} missing, skipping")
            continue
        for leg in [55, 56]:
            df_l = df[df["idLegislatura"] == leg].copy()
            df_l = df_l.dropna(subset=[col])
            log.info(f"  leg {leg}: n with measure = {len(df_l):,}")
            if len(df_l) < 5000:
                continue
            try:
                df_l["tercil"] = pd.qcut(df_l[col], 3, labels=["low", "mid", "high"],
                                           duplicates="drop")
            except Exception as e:
                log.error(f"  [FAIL] qcut failed: {e}")
                continue
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
        out = pd.DataFrame(rows)
        out_path = RESULTS / "followup_t4_tercis_by_leg.csv"
        out.to_csv(out_path, sep=";", index=False)
        log.info(f"\n[T4] saved {out_path}")
        print(out[["measure", "leg", "tercil", "pp_per_unit", "ci95_lo_pp", "ci95_hi_pp", "pval"]].to_string(index=False))


if __name__ == "__main__":
    df = load_augmented_panel()

    # Ordem: T2 (rapida, ja temos panorama), T4 (substantiva), T1 (confirmatoria)
    log.info("\n\n[Running T2 - 2 modelos, ~20 min]")
    t2_het_rp9_exposure(df)

    log.info("\n\n[Running T4 - 18 modelos, ~3-4 h]")
    t4_tercis_by_leg(df)

    log.info("\n\n[Running T1 - 4 modelos, ~2-3 h]")
    t1_iv_with_proxies(df)

    log.info("\n\nAll finalization analyses complete.")
