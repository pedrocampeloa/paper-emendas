"""
73_t6_robust_prepost.py
------------------------
ROBUST rerun of T6 (heterogeneity by legislative office) with:

  (i)  12 sub-samples: 4 pooled Leg 56 (mesa, no_mesa, tier2, no_tier2)
       + 8 with Lira split (each subgroup x pre_lira/post_lira).
  (ii) n_folds=3, n_reps=3 (main-paper spec).
  (iii) Replicated TWO times with different global numpy seeds
        (0 and 42) so we can measure Monte Carlo variance directly.
        Total: 24 PLIVs.

Motivation: exploratory rerun of T6 with n_reps=1 (script 72) produced
coefficients whose implied pooled would sum to +0.14, while the published
table 7 (script 71) reports -0.92 / -1.03 for no_mesa / no_tier2. Since
both used n_reps=1 the difference is Monte Carlo variance across cross-
fitting seeds. Before publishing the pre/post split we need to know
which value is closer to the population estimate; running twice at
n_reps=3 answers that.

Output: results/n3_t6_robust_prepost.csv
"""

import sys, time, warnings, logging, traceback, os
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

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("t6_robust")


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

CUT_LIRA = pd.Timestamp("2021-02-01")


def safe_pliv(df_l, controls, label, seed):
    log.info(f"  PLIV: {label} [seed={seed}]  n={len(df_l):,}")
    if len(df_l) < 5000:
        log.warning(f"    too small ({len(df_l)})")
        return None
    controls = [c for c in controls if c in df_l.columns
                and df_l[c].notna().mean() > 0.5
                and df_l[c].nunique() > 1
                and c not in ("alinhamento", "emenda_M", "idDeputado",
                              "has_mesa", "has_tier2", "n_tier2", "n_cargos")]
    # Reset global numpy seed before each fit to get controlled reproducibility
    np.random.seed(seed)
    t0 = time.time()
    try:
        res = U2.run_pliv_main(df_l, controls=controls, iv_set="backlog",
                                n_folds=N_FOLDS, n_reps=N_REPS)
        if res is None:
            return None
        log.info(f"    theta={res['pp_per_unit']:+.4f} pp "
                  f"CI=[{res['ci95_lo_pp']:+.3f}, {res['ci95_hi_pp']:+.3f}] "
                  f"p={res['pval']:.4f} ({time.time()-t0:.0f}s)")
        return res
    except Exception as e:
        log.error(f"    FAIL: {e}")
        traceback.print_exc()
        return None


def build_panel():
    log.info("Loading modeling panel via U.load_modeling_panel(window='pre')")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["ano"] = df["data"].dt.year

    log.info("Loading panel_proxy_cargos for has_mesa / n_tier2")
    p6 = pd.read_csv(PANEL / "panel_proxy_cargos.csv", sep=";",
                     dtype={"idDeputado": str})
    p6["ano"] = p6["ano"].astype(int)
    p6 = p6[["idDeputado", "ano", "has_mesa", "n_tier2", "n_cargos"]]
    df = df.merge(p6, on=["idDeputado", "ano"], how="left")
    df["has_mesa"] = df["has_mesa"].fillna(0).astype(int)
    df["n_tier2"] = df["n_tier2"].fillna(0)
    df["has_tier2"] = (df["n_tier2"] > 0).astype(int)
    log.info(f"  panel: {len(df):,} rows")
    return df


def main():
    t0 = time.time()
    df = build_panel()
    df56 = df[df["idLegislatura"] == 56].copy()
    ctrl_full = U2.get_clean_full_controls(df56)
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS
             and c not in ("has_mesa", "has_tier2", "n_tier2", "n_cargos")]
    log.info(f"  Leg 56 n={len(df56):,}, ctrl={len(ctrl)} cols")

    subgroups = [
        ("mesa",     df56["has_mesa"] == 1),
        ("no_mesa",  df56["has_mesa"] == 0),
        ("tier2",    df56["has_tier2"] == 1),
        ("no_tier2", df56["has_tier2"] == 0),
    ]
    periods = [
        ("pooled",    pd.Series(True, index=df56.index)),
        ("pre_lira",  df56["data"] < CUT_LIRA),
        ("post_lira", df56["data"] >= CUT_LIRA),
    ]

    rows = []
    seeds = [0, 42]
    for seed in seeds:
        log.info(f"\n{'#'*70}\n# SEED = {seed}\n{'#'*70}")
        for sg_label, sg_mask in subgroups:
            for pd_label, pd_mask in periods:
                label = f"{sg_label}__{pd_label}"
                sub = df56[sg_mask & pd_mask].copy()
                log.info(f"\n-- {label} [seed={seed}]: n={len(sub):,}")
                res = safe_pliv(sub, ctrl, label, seed)
                if res:
                    res["subgroup"] = sg_label
                    res["period"] = pd_label
                    res["seed"] = seed
                    rows.append(res)
                # Save incrementally in case of crash
                if rows:
                    pd.DataFrame(rows).to_csv(
                        RESULTS / "n3_t6_robust_prepost.csv",
                        sep=";", index=False)

    out = pd.DataFrame(rows)
    log.info(f"\n\nFinal results ({len(out)} PLIVs):")
    if len(out):
        print(out[["subgroup", "period", "seed", "pp_per_unit", "ci95_lo_pp",
                    "ci95_hi_pp", "pval", "stars", "n_obs"]]
              .to_string(index=False))
    elapsed = (time.time() - t0) / 60
    log.info(f"\nDONE in {elapsed:.1f} min")


if __name__ == "__main__":
    main()
