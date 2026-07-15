"""
56_centrao_only_subsamples.py
------------------------------
Ad-hoc run: PLIV-DML on THREE Centrão-only sub-samples that were not in the
original T5:

  (a) y_pres, leg56_lira_only_centrao
      Lira sub-period, Centrão-only deputies -> alignment with PP (Lira).
      Question: within the Centrão, how strong is the alignment-with-Lira
      coefficient? Legislative capture prediction: at least as large as
      the full-sample coefficient (+0.33).

  (b) y_gov, leg56_lira_only_centrao
      Lira sub-period, Centrão-only -> alignment with the Executive.
      Question: is the negative Executive backfire (-0.94) driven by
      non-Centrão rank-and-file, or does it also hold within the Centrão?

  (c) y_gov, leg56_only_centrao (all Leg 56, Centrão-only)
      Question: broader picture of the Executive coefficient inside
      the pivotal bloc across the whole Bolsonaro window.

Reuses n_folds=3, n_reps=3.

Output: results/n3_centrao_only.csv
"""

import sys, warnings, logging, time, traceback
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as _CFG
import _utils as U
import _utils_v2 as U2

# Reuse the y_pres loader from script 55 (complex; not worth re-implementing).
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "_pres55",
    str(Path(__file__).parent / "55_n3_pres_camara_orient.py"))
_pres55 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pres55)

warnings.filterwarnings("ignore")

PANEL = Path(_CFG.PANEL)
RESULTS = Path(_CFG.RESULTS)
N_FOLDS, N_REPS = 3, 3

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("centrao_only")


CENTRAO = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE", "UNIAO", "PTB",
           "AVANTE", "PSD", "MDB"}

EXTRA_TREATMENT_VARS = [
    "T_rp6_pre60", "T_rp6_pre60_M",
    "T_rp6_pix_pre60", "T_rp6_pix_pre60_M",
    "T_rp7_pre60", "T_rp7_pre60_M",
    "T_rp8_pre60", "T_rp8_pre60_M",
    "T_rp9_pre60", "T_rp9_pre60_M",
    "T_rp9_imputed_pre60", "T_rp9_imputed_pre60_M",
    "d_rp9_solicitante", "share_pork_opaco", "share_rp9",
]


def safe_pliv(df_l, controls, label):
    log.info(f"  PLIV: {label}  n={len(df_l):,}")
    if len(df_l) < 5000:
        log.warning(f"    too small ({len(df_l)})")
        return None
    controls = [c for c in controls if c in df_l.columns
                and df_l[c].notna().mean() > 0.5
                and df_l[c].nunique() > 1
                and c not in ("alinhamento", "emenda_M", "idDeputado")]
    t0 = time.time()
    try:
        res = U2.run_pliv_main(df_l, controls=controls, iv_set="backlog",
                                n_folds=N_FOLDS, n_reps=N_REPS)
        if res is None:
            return None
        log.info(f"    theta={res['pp_per_unit']:+.4f} pp "
                  f"CI=[{res['ci95_lo_pp']:+.3f}, {res['ci95_hi_pp']:+.3f}] "
                  f"p={res['pval']:.4f} n={res['n_obs']:,} "
                  f"({time.time()-t0:.0f}s)")
        return res
    except Exception as e:
        log.error(f"    FAIL: {e}")
        traceback.print_exc()
        return None


def main():
    t0 = time.time()
    CUT_LIRA_START = pd.Timestamp("2021-02-01")
    rows = []

    # ============================================================
    # (a) y_pres, Lira sub-period, Centrão-only
    # ============================================================
    log.info("\n" + "="*60)
    log.info("(a) y_pres, leg56_lira_only_centrao")
    log.info("="*60)
    df_p = _pres55.load_panel_with_y_pres()
    df_p["data"] = pd.to_datetime(df_p["data"])
    df_p["partido_norm"] = df_p["siglaPartido"].astype(str).str.upper().str.strip()
    ctrl_full = U2.get_clean_full_controls(df_p)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]

    mask = ((df_p["idLegislatura"] == 56)
             & (df_p["data"] >= CUT_LIRA_START)
             & (df_p["partido_norm"].isin(CENTRAO)))
    sub = df_p[mask].copy()
    log.info(f"  n={len(sub):,}, y_pres mean = {sub['alinhamento'].mean():.4f}")
    res = safe_pliv(sub, ctrl, "y_pres leg56_lira_only_centrao")
    if res:
        res["sample"] = "leg56_lira_only_centrao"
        res["outcome"] = "y_pres"
        res["y_mean"] = round(sub["alinhamento"].mean(), 4)
        rows.append(res)
    del df_p

    # ============================================================
    # (b) y_gov, Lira sub-period, Centrão-only
    # (c) y_gov, whole Leg 56, Centrão-only
    # ============================================================
    log.info("\n" + "="*60)
    log.info("(b, c) y_gov, Centrão-only sub-samples")
    log.info("="*60)
    df_g = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df_g["idDeputado"] = df_g["idDeputado"].astype(str)
    df_g["data"] = pd.to_datetime(df_g["data"])
    df_g["partido_norm"] = df_g["siglaPartido"].astype(str).str.upper().str.strip()
    log.info(f"  gov panel: {len(df_g):,} rows")
    ctrl_full = U2.get_clean_full_controls(df_g)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]

    # (b)
    mask = ((df_g["idLegislatura"] == 56)
             & (df_g["data"] >= CUT_LIRA_START)
             & (df_g["partido_norm"].isin(CENTRAO)))
    sub = df_g[mask].copy()
    log.info(f"  (b) n={len(sub):,}, y_gov mean = {sub['alinhamento'].mean():.4f}")
    res = safe_pliv(sub, ctrl, "y_gov leg56_lira_only_centrao")
    if res:
        res["sample"] = "leg56_lira_only_centrao"
        res["outcome"] = "y_gov"
        res["y_mean"] = round(sub["alinhamento"].mean(), 4)
        rows.append(res)

    # (c)
    mask = ((df_g["idLegislatura"] == 56)
             & (df_g["partido_norm"].isin(CENTRAO)))
    sub = df_g[mask].copy()
    log.info(f"  (c) n={len(sub):,}, y_gov mean = {sub['alinhamento'].mean():.4f}")
    res = safe_pliv(sub, ctrl, "y_gov leg56_only_centrao")
    if res:
        res["sample"] = "leg56_only_centrao"
        res["outcome"] = "y_gov"
        res["y_mean"] = round(sub["alinhamento"].mean(), 4)
        rows.append(res)

    out = pd.DataFrame(rows)
    out_path = RESULTS / "n3_centrao_only.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"\nsaved {out_path}")
    print(out.to_string())
    elapsed = (time.time() - t0) / 60
    log.info(f"\nDONE in {elapsed:.1f} min")


if __name__ == "__main__":
    main()
