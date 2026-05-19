# -*- coding: utf-8 -*-
"""
02_heterogeneities.py — Heterogeneity exercises (MUSTDO R2.1–R2.5)
====================================================================
Heterogeneity analyses requested by the professors (May 2026):

  R2.1 Effect by opposition vs coalition status
  R2.2 Effect by historical alignment (rolling, deputy-level)
  R2.3 Effect by election year (federal vs municipal)
  R2.4 Effect by vote tightness (close votes)
  R2.5 Effect by bill type (PEC, MPV vs ordinary)

Strategy: estimate stratified PLIV-backlog (the main spec) within each
subgroup, then test for difference. Standardised effects in pp/R$M.

Outputs:
  results/heterogeneity_R2_1_oposicao.csv
  results/heterogeneity_R2_2_alignment_hist.csv
  results/heterogeneity_R2_3_election.csv
  results/heterogeneity_R2_4_tight.csv
  results/heterogeneity_R2_5_bill_type.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U


# ============================================================================
# Helpers
# ============================================================================

def stratified_pliv(df: pd.DataFrame, groups: list[tuple[str, pd.Series]],
                      controls: list, ivs: list,
                      n_folds: int = C.N_FOLDS, n_reps: int = 1,
                      log: logging.Logger | None = None) -> pd.DataFrame:
    """
    Run PLIV-backlog within each (label, mask) group; return summary table.
    """
    log = log or logging.getLogger(__name__)
    rows = []
    for label, mask in groups:
        df_g = df[mask].copy()
        if len(df_g) < 1000:
            log.warning("  group %s n=%d <1000 — skipped", label, len(df_g))
            continue
        local_controls = [c for c in controls if c in df_g.columns
                            and df_g[c].notna().mean() > 0.5
                            and df_g[c].nunique() > 1]
        # Drop the variable used for stratification from controls if applicable
        log.info("  %s | n=%d | controls=%d", label, len(df_g), len(local_controls))
        try:
            # PLR
            t0 = time.time()
            res_plr = U.run_plr(df_g, controls=local_controls,
                                  n_folds=n_folds, n_reps=n_reps)
            row_plr = U.extract_row(res_plr, {"group": label, "model": "PLR",
                                                  "iv_set": "none"})
            if row_plr:
                rows.append(row_plr)
                log.info("    PLR (%ds): pp_per_unit=%+.3f%s",
                         time.time() - t0, row_plr["pp_per_unit"],
                         row_plr["stars"])

            # PLIV backlog
            t0 = time.time()
            avail = [z for z in ivs if z in df_g.columns
                       and df_g[z].std() > 0]
            if avail:
                res_iv = U.run_pliv(df_g, ivs=avail, controls=local_controls,
                                       n_folds=n_folds, n_reps=n_reps)
                row_iv = U.extract_row(res_iv, {"group": label,
                                                    "model": "PLIV",
                                                    "iv_set": "backlog"})
                if row_iv:
                    rows.append(row_iv)
                    log.info("    PLIV-backlog (%ds): pp_per_unit=%+.3f%s",
                             time.time() - t0, row_iv["pp_per_unit"],
                             row_iv["stars"])
        except Exception as e:
            log.error("  group %s failed: %s", label, e)
    return pd.DataFrame(rows)


def add_alignment_history(df: pd.DataFrame, lag_days: int = 180,
                            log: logging.Logger | None = None) -> pd.DataFrame:
    """
    Add `align_hist_pre`: rolling mean of alinhamento for the deputy in the
    `lag_days` BEFORE the current vote. Strictly excludes the current vote.

    Returns df with new column.
    """
    log = log or logging.getLogger(__name__)
    log.info("computing align_hist_pre with %d-day rolling window", lag_days)
    df = df.sort_values(["idDeputado", "data"]).reset_index(drop=True)

    # For each (idDeputado), rolling mean of alinhamento with strict shift(1)
    # Use groupby + rolling.
    df["align_hist_pre"] = (
        df.groupby("idDeputado")["alinhamento"]
            .transform(lambda x: x.shift(1).rolling(window=20, min_periods=5).mean())
    )

    # Discretize to terciles for heterogeneity
    df["align_hist_pre"] = df["align_hist_pre"].fillna(df["alinhamento"].mean())
    qs = df["align_hist_pre"].quantile([0.33, 0.67]).values
    df["align_hist_tercil"] = "mid"
    df.loc[df["align_hist_pre"] <= qs[0], "align_hist_tercil"] = "low"
    df.loc[df["align_hist_pre"] >= qs[1], "align_hist_tercil"] = "high"
    log.info("  terciles: %s", df["align_hist_tercil"].value_counts().to_dict())
    return df


def add_vote_tightness(df: pd.DataFrame,
                          log: logging.Logger | None = None) -> pd.DataFrame:
    """Add d_close: 1 if margin |Sim - Não| / total < 0.10."""
    log = log or logging.getLogger(__name__)
    if "votosSim" in df.columns and "votosNao" in df.columns:
        total = df["votosSim"].fillna(0) + df["votosNao"].fillna(0) + df["votosOutros"].fillna(0)
        margin = (df["votosSim"].fillna(0) - df["votosNao"].fillna(0)).abs()
        df["margin_abs"] = (margin / total.replace(0, np.nan)).fillna(0)
        df["d_close"] = (df["margin_abs"] < 0.10).astype(int)
        df["d_moderate"] = ((df["margin_abs"] >= 0.10)
                                  & (df["margin_abs"] < 0.30)).astype(int)
        df["d_lopsided"] = (df["margin_abs"] >= 0.30).astype(int)
        log.info("  vote tightness: close=%.1f%% moderate=%.1f%% lopsided=%.1f%%",
                 100 * df["d_close"].mean(),
                 100 * df["d_moderate"].mean(),
                 100 * df["d_lopsided"].mean())
    else:
        log.warning("  votosSim/votosNao not in panel — d_close set to 0")
        df["d_close"] = 0
        df["d_moderate"] = 0
        df["d_lopsided"] = 0
    return df


# ============================================================================
# R2.1 — Coalizão vs Oposição
# ============================================================================

def het_coalizao(df: pd.DataFrame, controls: list, log: logging.Logger,
                   n_reps: int) -> pd.DataFrame:
    log.info("\n=== R2.1 — coalizão vs oposição ===")
    groups = [
        ("oposicao", df["d_oposicao"] == 1),
        ("coalizao", df["d_coalizao"] == 1),
        ("independente", df["d_independente"] == 1),
    ]
    # Drop the stratifier from controls
    ctrl = [c for c in controls if c not in ("d_oposicao", "d_coalizao",
                                                  "d_independente")]
    return stratified_pliv(df, groups, ctrl, C.IV_SETS["backlog"],
                              n_reps=n_reps, log=log)


# ============================================================================
# R2.3 — Election year
# ============================================================================

def het_election(df: pd.DataFrame, controls: list, log: logging.Logger,
                   n_reps: int) -> pd.DataFrame:
    log.info("\n=== R2.3 — election year ===")
    groups = [
        ("federal_election", df["d_elec_federal"] == 1),
        ("non_federal", df["d_elec_federal"] == 0),
        ("municipal_election", df["d_elec_municipal"] == 1),
        ("non_municipal", df["d_elec_municipal"] == 0),
    ]
    ctrl = [c for c in controls if c not in ("d_elec_federal", "d_elec_municipal")]
    return stratified_pliv(df, groups, ctrl, C.IV_SETS["backlog"],
                              n_reps=n_reps, log=log)


# ============================================================================
# R2.4 — Tight votes
# ============================================================================

def het_tight(df: pd.DataFrame, controls: list, log: logging.Logger,
                n_reps: int) -> pd.DataFrame:
    log.info("\n=== R2.4 — vote tightness ===")
    df = add_vote_tightness(df, log=log)
    groups = [
        ("close (<10%)", df["d_close"] == 1),
        ("moderate (10-30%)", df["d_moderate"] == 1),
        ("lopsided (>=30%)", df["d_lopsided"] == 1),
    ]
    return stratified_pliv(df, groups, controls, C.IV_SETS["backlog"],
                              n_reps=n_reps, log=log)


# ============================================================================
# R2.5 — Bill importance / type
# ============================================================================

def het_bill_type(df: pd.DataFrame, controls: list, log: logging.Logger,
                    n_reps: int) -> pd.DataFrame:
    log.info("\n=== R2.5 — bill type ===")
    groups = []
    for col, label in [("d_tipoVotacao_PEC", "PEC"),
                          ("d_tipoVotacao_MPV", "MPV"),
                          ("d_tipoVotacao_PLP", "PLP"),
                          ("d_tipoVotacao_PL", "PL"),
                          ("d_tipoVotacao_MSC", "MSC")]:
        if col in df.columns:
            groups.append((label, df[col] == 1))
    ctrl = [c for c in controls if not c.startswith("d_tipoVotacao_")]
    return stratified_pliv(df, groups, ctrl, C.IV_SETS["backlog"],
                              n_reps=n_reps, log=log)


# ============================================================================
# R2.2 — Alignment history (rolling)
# ============================================================================

def het_alignment_history(df: pd.DataFrame, controls: list,
                              log: logging.Logger,
                              n_reps: int) -> pd.DataFrame:
    log.info("\n=== R2.2 — alignment history ===")
    df = add_alignment_history(df, log=log)
    groups = [
        ("hist_low", df["align_hist_tercil"] == "low"),
        ("hist_mid", df["align_hist_tercil"] == "mid"),
        ("hist_high", df["align_hist_tercil"] == "high"),
    ]
    return stratified_pliv(df, groups, controls, C.IV_SETS["backlog"],
                              n_reps=n_reps, log=log)


# ============================================================================
# Main
# ============================================================================

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--fast", action="store_true")
    p.add_argument("--reps", type=int, default=1)
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("02_heterogeneities")

    df = U.load_modeling_panel(window=C.MAIN_WINDOW, legis=C.LEGISLATURAS,
                                  log=log)

    if args.fast:
        log.info("FAST mode: 20%% sample")
        df = df.sample(frac=0.20, random_state=42)

    controls = [c for c in C.CONTROLS_REDUCED if c in df.columns]

    out_dir = C.RESULTS

    # R2.1
    df_r1 = het_coalizao(df, controls, log, args.reps)
    df_r1.to_csv(out_dir / "heterogeneity_R2_1_oposicao.csv",
                  sep=";", index=False)

    # R2.2 (rolling history)
    df_r2 = het_alignment_history(df, controls, log, args.reps)
    df_r2.to_csv(out_dir / "heterogeneity_R2_2_alignment_hist.csv",
                  sep=";", index=False)

    # R2.3
    df_r3 = het_election(df, controls, log, args.reps)
    df_r3.to_csv(out_dir / "heterogeneity_R2_3_election.csv",
                  sep=";", index=False)

    # R2.4
    df_r4 = het_tight(df, controls, log, args.reps)
    df_r4.to_csv(out_dir / "heterogeneity_R2_4_tight.csv",
                  sep=";", index=False)

    # R2.5
    df_r5 = het_bill_type(df, controls, log, args.reps)
    df_r5.to_csv(out_dir / "heterogeneity_R2_5_bill_type.csv",
                  sep=";", index=False)

    log.info("\n✓ saved %d heterogeneity files to %s",
             5, out_dir)


if __name__ == "__main__":
    main()
