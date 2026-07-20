# -*- coding: utf-8 -*-
"""
100_twoway_clustering.py — Cajueiro comment #2/#3
=================================================
Re-run Table 1 (main-spec PLIV-DML) under two-way Cameron-Gelbach-Miller
(2011) cluster-robust SEs, on both dimensions of the panel:

    cluster_cols = [idDeputado, idVotacao]

The single-way (idDeputado only) column stays as the reference; a new
column reports two-way SEs and cluster-robust 95% CIs. All specs are the
canonical PLIV-DML with n_folds=3, n_reps=3, backlog IV, deputy FE
(within-transform), full-clean controls.

Outputs
-------
results/twoway_clustering/table1_twoway.csv
results/twoway_clustering/table1_twoway.md   (comparison table)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import _utils as U
import _utils_v2 as UV

OUT = Path(__file__).resolve().parent.parent / "results" / "twoway_clustering"
OUT.mkdir(parents=True, exist_ok=True)


def run_one(df, label, outcome, leg, cluster_col):
    """Run PLIV-DML on one cell (leg, outcome, cluster spec)."""
    sub = df[df["idLegislatura"] == leg].copy()
    if outcome != "alinhamento":
        # switch target
        sub["_target"] = sub[outcome]
        target_arg = "_target"
    else:
        target_arg = "alinhamento"
    t0 = time.time()
    res = UV.run_pliv_main(
        sub, iv_set="backlog", target=target_arg,
        cluster_col=cluster_col, n_folds=3, n_reps=3,
    )
    dt = time.time() - t0
    if res is None:
        print(f"  {label:20s} → returned None (t={dt:.1f}s)")
        return None
    print(f"  {label:20s} → pp={res['pp_per_unit']:+.3f} "
          f"[{res['ci95_lo_pp']:+.3f}, {res['ci95_hi_pp']:+.3f}] "
          f"SE={res['se_sd_cluster']:.4f} {res['stars']} "
          f"clusters={res['n_clusters_per_dim']} (t={dt:.1f}s)")
    return {
        "outcome": outcome,
        "leg": leg,
        "cluster_spec": (",".join(cluster_col)
                         if isinstance(cluster_col, list) else cluster_col),
        **res,
    }


def main():
    print("Loading modeling panel...")
    df = U.load_modeling_panel()
    print(f"panel: n={len(df):,}, deputies={df['idDeputado'].nunique()}, "
          f"votacoes={df['idVotacao'].nunique()}")

    # Outcomes: gov (canonical, Table 1 of the paper) — the coefficient
    # Cajueiro flagged. If the y_pres panel column has been built by
    # script 54_, include it too.
    outcomes = ["alinhamento"]
    if "y_pres_camara_orient" in df.columns:
        outcomes.append("y_pres_camara_orient")

    rows = []
    for outcome in outcomes:
        for leg in (55, 56):
            print(f"\n=== outcome={outcome} | leg={leg} ===")
            # single-way (reference)
            r1 = run_one(df, "1-way (deputy)", outcome, leg, "idDeputado")
            if r1: rows.append(r1)
            # two-way
            r2 = run_one(df, "2-way (dep×vote)", outcome, leg,
                         ["idDeputado", "idVotacao"])
            if r2: rows.append(r2)

    tab = pd.DataFrame(rows)
    csv_path = OUT / "table1_twoway.csv"
    tab.to_csv(csv_path, index=False)
    print(f"\nwrote {csv_path}")

    # Comparison table in markdown
    lines = ["# Table 1 under two-way clustering", "",
             "PLIV-DML, backlog IV, deputy FE, full-clean controls, "
             "n_folds=3, n_reps=3. Cluster spec compares single-way "
             "(idDeputado) with two-way CGM (idDeputado × idVotacao).",
             "",
             "| Outcome | Leg | Cluster | Coef (pp/R$M) | SE (sd) | 95% CI (pp) | p | Stars | Ratio (2w/1w SE) |",
             "|---|---|---|---|---|---|---|---|---|"]
    # build ratio table
    tab_sorted = tab.sort_values(["outcome", "leg", "cluster_spec"])
    for (out, leg), g in tab_sorted.groupby(["outcome", "leg"], sort=False):
        r1 = g[g["cluster_spec"] == "idDeputado"].iloc[0] if (g["cluster_spec"] == "idDeputado").any() else None
        r2 = g[g["cluster_spec"] == "idDeputado,idVotacao"].iloc[0] if (g["cluster_spec"] == "idDeputado,idVotacao").any() else None
        if r1 is not None:
            lines.append(
                f"| {out} | {leg} | 1-way | {r1['pp_per_unit']:+.3f} | "
                f"{r1['se_sd_cluster']:.4f} | [{r1['ci95_lo_pp']:+.3f}, {r1['ci95_hi_pp']:+.3f}] | "
                f"{r1['pval']:.4f} | {r1['stars']} | 1.00 |"
            )
        if r2 is not None:
            ratio = (r2["se_sd_cluster"] / r1["se_sd_cluster"]) if r1 is not None else float("nan")
            lines.append(
                f"| {out} | {leg} | 2-way | {r2['pp_per_unit']:+.3f} | "
                f"{r2['se_sd_cluster']:.4f} | [{r2['ci95_lo_pp']:+.3f}, {r2['ci95_hi_pp']:+.3f}] | "
                f"{r2['pval']:.4f} | {r2['stars']} | {ratio:.3f} |"
            )
    md_path = OUT / "table1_twoway.md"
    md_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
