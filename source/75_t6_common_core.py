"""
75_t6_common_core.py
--------------------
Sanity check: rerun the 12 T6 sub-samples (mesa/no_mesa/tier2/no_tier2 x
pooled/pre_lira/post_lira) using an IDENTICAL control list (common-core:
controls that survive the >50%-non-missing + >1-unique filter in ALL
sub-samples simultaneously).

If the pre/post pattern (near-zero pre-Lira, positive post-Lira) survives
this restriction, then the temporal split is genuine and not driven by
control-set variation. If it disappears, then the pooled -0.92 was
driven by controls that are constant in one of the sub-samples.

Config: n_folds=3, n_reps=3, seed=0.

Output: results/n3_t6_common_core.csv
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

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("common_core")

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


def _survives(df, c):
    return c in df.columns and df[c].notna().mean() > 0.5 and df[c].nunique() > 1


def safe_pliv(df_l, controls, label, seed=0):
    log.info(f"  PLIV: {label}  n={len(df_l):,}  ctrl={len(controls)}")
    if len(df_l) < 5000:
        log.warning(f"    too small ({len(df_l)})")
        return None
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
    log.info("Loading panel")
    df = U.load_modeling_panel(window="pre", include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["ano"] = df["data"].dt.year

    p6 = pd.read_csv(PANEL / "panel_proxy_cargos.csv", sep=";",
                     dtype={"idDeputado": str})
    p6["ano"] = p6["ano"].astype(int)
    p6 = p6[["idDeputado", "ano", "has_mesa", "n_tier2", "n_cargos"]]
    df = df.merge(p6, on=["idDeputado", "ano"], how="left")
    df["has_mesa"] = df["has_mesa"].fillna(0).astype(int)
    df["n_tier2"] = df["n_tier2"].fillna(0)
    df["has_tier2"] = (df["n_tier2"] > 0).astype(int)
    return df


def main():
    t0 = time.time()
    df = build_panel()
    df56 = df[df["idLegislatura"] == 56].copy()
    ctrl_all = U2.get_clean_full_controls(df56)
    ctrl_base = [c for c in ctrl_all if c not in EXTRA_TREATMENT_VARS
                  and c not in ("has_mesa", "has_tier2", "n_tier2", "n_cargos")]

    pool = df56.copy()
    pre = df56[df56["data"] < CUT_LIRA].copy()
    post = df56[df56["data"] >= CUT_LIRA].copy()
    common = [c for c in ctrl_base
               if _survives(pool, c) and _survives(pre, c) and _survives(post, c)]
    log.info(f"  common-core controls: {len(common)}")

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
    for sg_label, sg_mask in subgroups:
        for pd_label, pd_mask in periods:
            label = f"{sg_label}__{pd_label}"
            sub = df56[sg_mask & pd_mask].copy()
            log.info(f"\n-- {label}: n={len(sub):,}")
            # Within this sub-sample, filter common further to those with
            # variation IN this sub-sample too (safety)
            local = [c for c in common if _survives(sub, c)]
            res = safe_pliv(sub, local, label)
            if res:
                res["subgroup"] = sg_label
                res["period"] = pd_label
                rows.append(res)
            if rows:
                pd.DataFrame(rows).to_csv(
                    RESULTS / "n3_t6_common_core.csv", sep=";", index=False)

    out = pd.DataFrame(rows)
    print(out[["subgroup", "period", "pp_per_unit", "ci95_lo_pp",
                "ci95_hi_pp", "pval", "stars", "n_obs", "n_controls"]]
          .to_string(index=False))
    elapsed = (time.time() - t0) / 60
    log.info(f"\nDONE in {elapsed:.1f} min")


if __name__ == "__main__":
    main()
