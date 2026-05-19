# -*- coding: utf-8 -*-
"""
09_audit_controls.py — Bad-controls audit
==========================================
Why does reduced (~29) vs full (~149) give such different results?

Strategy:
  1. For each control, compute correlation with IVs and treatment.
       - High |corr(C, Z)|: suspect of absorbing exogenous variation.
       - High |corr(C, T) | high|corr(C, Y) controlling for X|: suspect bad control.
  2. Group controls into buckets (orientations, themes, types, etc.)
  3. Re-run DML-PLIV (window=pre, leg=pooled) WITHOUT each bucket; observe
     impact on coefficient. The bucket whose removal moves coefficient most
     toward the reduced spec is the offender.
  4. Identify minimal set of "bad" controls to drop.

Outputs:
  results/audit_controls_correlations.csv
  results/audit_controls_buckets.csv          (DML coef per bucket-removed)
  results/audit_controls_recommendation.md   (what to drop in v2)
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U


def categorize_control(name: str) -> str:
    """Map control name to a high-level bucket."""
    if name.startswith("d_ori_gov"): return "01_d_ori_gov"
    if name.startswith("d_ori_part"): return "02_d_ori_part"
    if name.startswith("d_ori_mai"): return "03_d_ori_mai"
    if name.startswith("d_ori_min"): return "04_d_ori_min"
    if name.startswith("d_ori_op"): return "05_d_ori_op"
    if name.startswith("d_ori_bancada"): return "06_d_ori_bancada"
    if name.startswith("d_tipoVotacao_"): return "07_d_tipoVotacao"
    if name.startswith("d_tema_"): return "08_d_tema"
    if name.startswith("tipoAutor_"): return "09_tipoAutor"
    if name.startswith("d_prof_"): return "10_d_prof"
    if name.startswith("d_niv_esc_") or name == "indice_escolaridade": return "11_d_escolaridade"
    if name.startswith("d_reg_") or name.startswith("d_uf_"): return "12_d_uf_reg"
    if name.startswith("d_part_"): return "13_d_part"
    if name in ("d_homem","d_titular","d_proponente","d_autor","d_bloco_autor","d_independente","d_oposicao","d_coalizao"): return "14_d_demograficas"
    if name.startswith("d_mesa_") or name.startswith("d_lider_"): return "15_d_lider_mesa"
    if name.startswith("d_") and ("_part" in name or "_leg" in name): return "16_d_N_part_leg"
    if name in ("idade","idade2"): return "17_idade"
    if name == "y" or name == "yoy" or name == "y_random": return "18_year"
    if name in ("d_elec_federal","d_elec_municipal"): return "19_election"
    if name.startswith("n_"): return "20_n_aggregates"
    if name.startswith("pct_"): return "21_pct_aggregates"
    if name.startswith("tamanho_"): return "22_tamanho"
    if name in ("votosSim","votosNao","votosOutros","aprovacao"): return "23_vote_outcome"
    if name in ("pol_simple","pol_jaccard","pol_paper"): return "24_polarization"
    return "99_other"


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("09_audit")

    log.info("Loading panel (window=pre)")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    log.info("Final panel: %d rows", len(df))

    # All full controls
    ctrls = C.get_full_controls(df)
    log.info("Full control set: %d", len(ctrls))

    # Categorize
    buckets = {}
    for c in ctrls:
        b = categorize_control(c)
        buckets.setdefault(b, []).append(c)
    log.info("Buckets:")
    for b, cs in sorted(buckets.items()):
        log.info("  %s: %d cols", b, len(cs))

    # Compute correlations of each control with IVs and treatment
    iv_cols = ["iv_fiscal_q4", "iv_fiscal_pressure",
                "iv_q4_no_ytd", "iv_ytd_exec_pct"]
    rows_corr = []
    for c in ctrls:
        if c not in df.columns: continue
        corr_T = df[[c, C.TREATMENT]].corr().iloc[0, 1]
        corr_Y = df[[c, C.TARGET]].corr().iloc[0, 1]
        corrs_Z = {z: df[[c, z]].corr().iloc[0, 1] for z in iv_cols}
        max_corr_Z = max(abs(v) for v in corrs_Z.values())
        rows_corr.append({
            "bucket": categorize_control(c),
            "control": c,
            "corr_T": round(corr_T, 4),
            "corr_Y": round(corr_Y, 4),
            "max_abs_corr_Z": round(max_corr_Z, 4),
            **{f"corr_{z}": round(corrs_Z[z], 4) for z in iv_cols},
        })
    df_corr = pd.DataFrame(rows_corr).sort_values("max_abs_corr_Z", ascending=False)
    df_corr.to_csv(C.RESULTS / "audit_controls_correlations.csv",
                    sep=";", index=False)
    log.info("Saved audit_controls_correlations.csv")

    # Top-20 most correlated with IVs
    log.info("\n=== TOP-20 controls correlated with IVs ===")
    log.info("\n%s", df_corr.head(20)[["bucket","control","max_abs_corr_Z","corr_T","corr_Y"]].to_string(index=False))

    # Bucket aggregates
    bucket_summary = df_corr.groupby("bucket").agg(
        n_cols=("control","size"),
        max_corr_Z=("max_abs_corr_Z","max"),
        mean_corr_Z=("max_abs_corr_Z","mean"),
        max_corr_T=("corr_T",lambda x: x.abs().max()),
        max_corr_Y=("corr_Y",lambda x: x.abs().max()),
    ).round(4)
    log.info("\n=== BUCKET CORRELATION SUMMARY ===")
    log.info("\n%s", bucket_summary.to_string())
    bucket_summary.to_csv(C.RESULTS / "audit_controls_buckets_summary.csv", sep=";")

    # Now: re-run PLIV-backlog (pooled) removing each bucket, see impact
    log.info("\n=== LEAVE-ONE-BUCKET-OUT DML-PLIV-backlog (pooled) ===")
    bucket_results = []

    # Baseline (full)
    t0 = time.time()
    res = U.run_pliv(df, ivs=C.IV_SETS["backlog"], controls=ctrls,
                        n_folds=3, n_reps=1)
    row = U.extract_row(res, {"removed_bucket": "NONE_baseline_full",
                                  "n_controls": len(ctrls)})
    if row:
        bucket_results.append(row)
        log.info("  baseline FULL (%ds): pp/R$M=%+.3f%s n_ctrls=%d",
                 time.time()-t0, row["pp_per_unit"], row["stars"],
                 len(ctrls))

    # Reduced (for reference)
    t0 = time.time()
    ctrl_red = [c for c in C.CONTROLS_REDUCED if c in df.columns]
    res = U.run_pliv(df, ivs=C.IV_SETS["backlog"], controls=ctrl_red,
                        n_folds=3, n_reps=1)
    row = U.extract_row(res, {"removed_bucket": "REDUCED_reference",
                                  "n_controls": len(ctrl_red)})
    if row:
        bucket_results.append(row)
        log.info("  reduced ref (%ds): pp/R$M=%+.3f%s n_ctrls=%d",
                 time.time()-t0, row["pp_per_unit"], row["stars"],
                 len(ctrl_red))

    # Leave-one-bucket-out
    for bucket in sorted(buckets.keys()):
        bucket_cols = buckets[bucket]
        ctrl_minus = [c for c in ctrls if c not in bucket_cols]
        t0 = time.time()
        try:
            res = U.run_pliv(df, ivs=C.IV_SETS["backlog"], controls=ctrl_minus,
                                n_folds=3, n_reps=1)
            row = U.extract_row(res, {"removed_bucket": bucket,
                                          "n_controls": len(ctrl_minus),
                                          "removed_n": len(bucket_cols)})
            if row:
                bucket_results.append(row)
                log.info("  ─%s (%ds): pp/R$M=%+.3f%s n_ctrls=%d (removed %d)",
                         bucket, time.time()-t0, row["pp_per_unit"],
                         row["stars"], len(ctrl_minus), len(bucket_cols))
        except Exception as e:
            log.error("  ─%s failed: %s", bucket, e)

    df_buckets = pd.DataFrame(bucket_results)
    df_buckets.to_csv(C.RESULTS / "audit_controls_buckets.csv",
                       sep=";", index=False)
    log.info("\nSaved audit_controls_buckets.csv (%d rows)", len(df_buckets))

    # Find buckets whose removal moves the coef toward the reduced reference
    if len(df_buckets) > 2:
        baseline = df_buckets[df_buckets["removed_bucket"]=="NONE_baseline_full"]["pp_per_unit"].iloc[0]
        reduced = df_buckets[df_buckets["removed_bucket"]=="REDUCED_reference"]["pp_per_unit"].iloc[0]
        target_dir = np.sign(reduced - baseline)
        df_buckets_loo = df_buckets[~df_buckets["removed_bucket"].str.startswith(("NONE","REDUCED"))].copy()
        df_buckets_loo["delta_from_baseline"] = df_buckets_loo["pp_per_unit"] - baseline
        df_buckets_loo["moves_toward_reduced"] = (np.sign(df_buckets_loo["delta_from_baseline"]) == target_dir).astype(int)
        df_buckets_loo = df_buckets_loo.sort_values("delta_from_baseline",
                                                      key=abs, ascending=False)
        log.info("\n=== BUCKETS RANKED BY IMPACT ON COEFFICIENT ===")
        log.info("(positive delta means coef went UP when bucket removed)")
        log.info("\n%s", df_buckets_loo[["removed_bucket","n_controls","removed_n",
                                             "pp_per_unit","delta_from_baseline",
                                             "moves_toward_reduced","stars"]].to_string(index=False))


if __name__ == "__main__":
    main()
