"""
76_main_leg56_prepost.py
-------------------------
Rerun the MAIN PLIV-DML specification (all deputies, no cargo split) on
Legislature 56 split by the Lira cutoff (Feb 1, 2021). Two PLIVs:

  (a) Leg 56 pre-Lira: idLegislatura==56 & data < 2021-02-01
  (b) Leg 56 post-Lira: idLegislatura==56 & data >= 2021-02-01

Same spec as the main Table 1 estimate (backlog IV, n_folds=3, n_reps=3,
paper's preferred control set). Run twice with seeds 0 and 42 to
measure Monte Carlo variance.

Purpose: reconcile the -0.94 pooled Leg 56 coefficient with the near-
zero/positive pre-post-Lira sub-sample coefficients from Table 7. If
the main coefficient itself flips from pooled -0.94 to (pre ≈ 0,
post ≈ +0.3), the Bolsonaro-era result changes interpretation from
"backfire" to "coordination vacuum followed by restoration".

Output: results/n3_main_leg56_prepost.csv
"""

import sys, time, warnings, logging, traceback
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")

PANEL = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
N_FOLDS, N_REPS = 3, 3
CUT_LIRA = pd.Timestamp("2021-02-01")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("main_prepost")


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


def safe_pliv(df_l, controls, label, seed):
    log.info(f"  PLIV: {label} [seed={seed}]  n={len(df_l):,}")
    if len(df_l) < 5000:
        log.warning(f"    too small ({len(df_l)})")
        return None
    controls = [c for c in controls if c in df_l.columns
                and df_l[c].notna().mean() > 0.5
                and df_l[c].nunique() > 1
                and c not in ("alinhamento", "emenda_M", "idDeputado")]
    np.random.seed(seed)
    t0 = time.time()
    try:
        res = U2.run_pliv_main(df_l, controls=controls, iv_set="backlog",
                                n_folds=N_FOLDS, n_reps=N_REPS)
        if res is None:
            return None
        log.info(f"    theta={res['pp_per_unit']:+.4f} pp "
                  f"CI=[{res['ci95_lo_pp']:+.3f}, {res['ci95_hi_pp']:+.3f}] "
                  f"p={res['pval']:.4f} n_ctrl={res['n_controls']} "
                  f"({time.time()-t0:.0f}s)")
        return res
    except Exception as e:
        log.error(f"    FAIL: {e}")
        traceback.print_exc()
        return None


def main():
    t0 = time.time()
    log.info("Loading panel")
    df = U.load_modeling_panel(window="pre", include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    df56 = df[df["idLegislatura"] == 56].copy()
    ctrl_full = U2.get_clean_full_controls(df56)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS]
    log.info(f"  Leg 56 n={len(df56):,}, ctrl={len(ctrl)}")

    rows = []
    for seed in [0, 42]:
        for period_label, mask in [
            ("pre_lira",  df56["data"] < CUT_LIRA),
            ("post_lira", df56["data"] >= CUT_LIRA),
        ]:
            sub = df56[mask].copy()
            log.info(f"\n-- {period_label} [seed={seed}]: n={len(sub):,}")
            res = safe_pliv(sub, ctrl, period_label, seed)
            if res:
                res["period"] = period_label
                res["seed"] = seed
                rows.append(res)
                pd.DataFrame(rows).to_csv(
                    RESULTS / "n3_main_leg56_prepost.csv",
                    sep=";", index=False)

    out = pd.DataFrame(rows)
    print(out[["period", "seed", "pp_per_unit", "ci95_lo_pp", "ci95_hi_pp",
                "pval", "stars", "n_obs", "n_controls"]]
          .to_string(index=False))
    elapsed = (time.time() - t0) / 60
    log.info(f"\nDONE in {elapsed:.1f} min")


if __name__ == "__main__":
    main()
