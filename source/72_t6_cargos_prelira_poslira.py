"""
72_t6_cargos_prelira_poslira.py
--------------------------------
Extend T6 (heterogeneity by legislative office) with a Lira-cutoff split.

Motivation: the legislative-capture narrative posits that the pork channel
migrated to the Chamber leadership *after* the Lira presidency began on
Feb 1, 2021. Under this hypothesis, the shielding effect of Tier-2 office
against the rank-and-file backfire should be a Lira-era phenomenon, not
symmetric across the Bolsonaro window. This script tests that prediction
by re-running the four T6 sub-samples (mesa, no_mesa, tier2, no_tier2)
separately for the pre-Lira and post-Lira sub-periods of Legislature 56.

Config: n_folds=3, n_reps=1 (same rapid config as 71_t6_cargos_quad;
Monte Carlo variance is tolerable at this exploratory stage).

Output: results/n3_t6_cargos_prelira_poslira.csv
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
N_FOLDS, N_REPS = 3, 1

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("t6_prepost")


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


def safe_pliv(df_l, controls, label):
    log.info(f"  PLIV: {label}  n={len(df_l):,}")
    if len(df_l) < 5000:
        log.warning(f"    too small ({len(df_l)})")
        return None
    controls = [c for c in controls if c in df_l.columns
                and df_l[c].notna().mean() > 0.5
                and df_l[c].nunique() > 1
                and c not in ("alinhamento", "emenda_M", "idDeputado",
                              "has_mesa", "has_tier2", "n_tier2", "n_cargos")]
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
    log.info(f"  has_mesa mean = {df['has_mesa'].mean():.4f}")
    log.info(f"  has_tier2 mean = {df['has_tier2'].mean():.4f}")
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
        ("pre_lira",  df56["data"] < CUT_LIRA),
        ("post_lira", df56["data"] >= CUT_LIRA),
    ]

    rows = []
    for sg_label, sg_mask in subgroups:
        for pd_label, pd_mask in periods:
            label = f"{sg_label}__{pd_label}"
            sub = df56[sg_mask & pd_mask].copy()
            log.info(f"\n-- {label}: n={len(sub):,}")
            res = safe_pliv(sub, ctrl, label)
            if res:
                res["subgroup"] = sg_label
                res["period"] = pd_label
                rows.append(res)

    out = pd.DataFrame(rows)
    out_path = RESULTS / "n3_t6_cargos_prelira_poslira.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"\nsaved {out_path}")
    if len(out):
        print(out[["subgroup", "period", "pp_per_unit", "ci95_lo_pp",
                    "ci95_hi_pp", "pval", "stars", "n_obs", "n_clusters"]]
              .to_string(index=False))
    elapsed = (time.time() - t0) / 60
    log.info(f"\nDONE in {elapsed:.1f} min")


if __name__ == "__main__":
    main()
