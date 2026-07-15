"""
74_diag_controls_split.py
-------------------------
Diagnostic script for the pre/post-Lira split in T6:

  - Compare which controls survive the >50% non-missing + >1 unique filter
    in the pooled, pre-Lira, and post-Lira sub-samples of Leg 56.
  - Cross-check with the pooled-derived control list used in the main
    Table 7 estimation.

No PLIV runs; just data inspection.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

PANEL = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
CUT_LIRA = pd.Timestamp("2021-02-01")

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


def _survives(df, c):
    return c in df.columns and df[c].notna().mean() > 0.5 and df[c].nunique() > 1


def main():
    df = U.load_modeling_panel(window="pre", include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    df56 = df[df["idLegislatura"] == 56].copy()
    ctrl_all = U2.get_clean_full_controls(df56)
    ctrl_base = [c for c in ctrl_all if c not in EXTRA_TREATMENT_VARS
                 and c not in ("has_mesa", "has_tier2", "n_tier2", "n_cargos")]

    print(f"Base controls (pooled Leg 56): {len(ctrl_base)}")
    pool = df56.copy()
    pre = df56[df56["data"] < CUT_LIRA].copy()
    post = df56[df56["data"] >= CUT_LIRA].copy()
    print(f"  n pooled={len(pool):,}, pre={len(pre):,}, post={len(post):,}")

    # Which controls survive per sub-sample?
    print("\nControls that DROP in pre-Lira but survive in pooled:")
    dropped_pre = [c for c in ctrl_base
                    if _survives(pool, c) and not _survives(pre, c)]
    for c in dropped_pre:
        n_miss = pre[c].isna().mean() if c in pre.columns else 1.0
        n_unique = pre[c].nunique() if c in pre.columns else 0
        print(f"  {c}: missing={n_miss:.3f}, unique={n_unique}")

    print("\nControls that DROP in post-Lira but survive in pooled:")
    dropped_post = [c for c in ctrl_base
                     if _survives(pool, c) and not _survives(post, c)]
    for c in dropped_post:
        n_miss = post[c].isna().mean() if c in post.columns else 1.0
        n_unique = post[c].nunique() if c in post.columns else 0
        print(f"  {c}: missing={n_miss:.3f}, unique={n_unique}")

    # Common core across all three
    common = [c for c in ctrl_base
               if _survives(pool, c) and _survives(pre, c) and _survives(post, c)]
    print(f"\nCommon core (survives everywhere): {len(common)}")

    # Save diagnostic table
    out_rows = []
    for c in ctrl_base:
        out_rows.append({
            "control": c,
            "pooled_pass": _survives(pool, c),
            "pre_pass": _survives(pre, c),
            "post_pass": _survives(post, c),
            "pooled_miss": pool[c].isna().mean() if c in pool.columns else 1.0,
            "pre_miss": pre[c].isna().mean() if c in pre.columns else 1.0,
            "post_miss": post[c].isna().mean() if c in post.columns else 1.0,
            "pre_unique": pre[c].nunique() if c in pre.columns else 0,
            "post_unique": post[c].nunique() if c in post.columns else 0,
        })
    out = pd.DataFrame(out_rows)
    out_path = RESULTS / "n3_t6_controls_diag.csv"
    out.to_csv(out_path, sep=";", index=False)
    print(f"\nsaved {out_path}")


if __name__ == "__main__":
    main()
