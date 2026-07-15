"""
82_gov_by_subperiod.py
------------------------
Rerun the main PLIV-DML on the EXACT same sub-periods used in n3_pres_t5_subsamples
(leg55_maia, leg56_maia, leg56_lira, leg56_lira_excl_pp, leg56_lira_excl_centrao)
but with GOVERNMENT alignment as outcome instead of Chamber-president alignment.

This builds the data for Table 7 (gov vs Chamber-pres side-by-side).

Config: n_folds=3, n_reps=3 (replication of the main paper).

Output: results/n3_gov_t5_subsamples.csv
"""

import sys, time, warnings, logging, traceback
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as _CFG
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")

PANEL = Path(_CFG.PANEL)
RESULTS = Path(_CFG.RESULTS)
N_FOLDS, N_REPS = 3, 3

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("gov_sub")


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
    "share_pix", "n_apoiamentos_opaco",
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
        if res is None: return None
        log.info(f"    theta={res['pp_per_unit']:+.4f} pp se={res['se_sd_cluster']:.4f} "
                 f"p={res['pval']:.4f} ({time.time()-t0:.0f}s)")
        return res
    except Exception as e:
        log.error(f"    FAIL: {e}")
        traceback.print_exc()
        return None


def main():
    log.info("Loading modeling panel")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["partido_norm"] = df["siglaPartido"].astype(str).str.upper().str.strip()
    log.info(f"  panel: {len(df):,} rows")

    # Define sub-samples matching n3_pres_t5 (same temporal cuts)
    # Maia presidency: 2016-07-14 to 2021-01-31; Lira: 2021-02-01 onward
    CUT_MAIA_END = pd.Timestamp("2021-02-01")
    CUT_LIRA_START = pd.Timestamp("2021-02-01")

    samples = {
        "leg55_maia": (df["idLegislatura"] == 55) &
                       (df["data"] >= pd.Timestamp("2016-07-14")),
        "leg56_maia": (df["idLegislatura"] == 56) &
                       (df["data"] < CUT_MAIA_END),
        "leg56_lira": (df["idLegislatura"] == 56) &
                       (df["data"] >= CUT_LIRA_START),
        "leg56_lira_excl_pp": (df["idLegislatura"] == 56) &
                                (df["data"] >= CUT_LIRA_START) &
                                (df["partido_norm"] != "PP"),
        "leg56_lira_excl_centrao": (df["idLegislatura"] == 56) &
                                     (df["data"] >= CUT_LIRA_START) &
                                     (~df["partido_norm"].isin(CENTRAO)),
        "leg56_lira_only_centrao": (df["idLegislatura"] == 56) &
                                     (df["data"] >= CUT_LIRA_START) &
                                     (df["partido_norm"].isin(CENTRAO)),
        "leg56_only_centrao":       (df["idLegislatura"] == 56) &
                                     (df["partido_norm"].isin(CENTRAO)),
    }

    ctrl_full = U2.get_clean_full_controls(df)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    log.info(f"  base ctrl: {len(ctrl)} cols")

    rows = []
    for name, mask in samples.items():
        sub = df[mask].copy()
        log.info(f"\n  === {name} ===")
        log.info(f"  n={len(sub):,}, alinhamento mean = {sub['alinhamento'].mean():.4f}")
        res = safe_pliv(sub, ctrl, name)
        if res:
            res.update({"sample": name,
                        "y_gov_mean": round(float(sub['alinhamento'].mean()), 4)})
            rows.append(res)
            out = pd.DataFrame(rows)
            out.to_csv(RESULTS / "n3_gov_t5_subsamples.csv", sep=";", index=False)
            log.info(f"  saved incremental {RESULTS / 'n3_gov_t5_subsamples.csv'}")

    print()
    print(pd.DataFrame(rows)[['sample','pp_per_unit','ci95_lo_pp','ci95_hi_pp',
                                'pval','stars','n_obs','y_gov_mean']].to_string(index=False))


if __name__ == "__main__":
    main()
