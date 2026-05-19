# -*- coding: utf-8 -*-
"""
01_run_dml.py — Main DML estimation
====================================
Reproduces the core PLR + PLIV results for the paper-emendas.

Outputs to results/:
  main_results.csv        Coefficient table (PLR + PLIV × leg × IV × spec)
  main_fstage.csv         First-stage F-stats
  main_sargan.csv         Sargan-Hansen J-tests (over-identified models)
  main_falsification.csv  Random-Y, post-vote placebo, vote-Sim placebo

Usage:
  python 01_run_dml.py            full run (~30-60 minutes)
  python 01_run_dml.py --fast     20% sample (smoke test, ~5 minutes)
  python 01_run_dml.py --legacy   also run with full 191 controls (legacy)

The output is two-tier by `spec`:
  - "reduced": ~30 controls, defensible for Public Choice
  - "full":     all available numeric controls (legacy replication)
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


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--fast", action="store_true",
                    help="20%% sample for smoke test")
    p.add_argument("--legacy", action="store_true",
                    help="Also run with full 191 controls (appendix spec)")
    p.add_argument("--reps", type=int, default=C.N_REPS,
                    help="Number of DML repetitions (default 3)")
    p.add_argument("--windows", default="pre,sym",
                    help="Comma-separated windows to run (pre, sym, post). "
                         "Default: pre,sym")
    return p.parse_args()


def run_full(df: pd.DataFrame,
              controls: list,
              spec_label: str,
              window_label: str,
              n_folds: int = C.N_FOLDS,
              n_reps: int = C.N_REPS,
              log: logging.Logger | None = None) -> tuple[list, list, list]:
    """Run PLR + PLIV (fiscal + backlog) per legislature + pooled."""
    log = log or logging.getLogger(__name__)
    rows_results = []
    rows_fstage = []
    rows_sargan = []

    extra = {"spec": spec_label, "window": window_label}

    for legis in (None, 55, 56):
        leg_label = "all" if legis is None else str(legis)
        df_l = df.copy() if legis is None else df[df["idLegislatura"] == legis].copy()
        if len(df_l) < 1000:
            log.warning("  skipping leg %s (n=%d < 1000)", leg_label, len(df_l))
            continue

        local_controls = [c for c in controls
                            if c in df_l.columns
                            and df_l[c].notna().mean() > 0.5
                            and df_l[c].nunique() > 1]
        log.info("--- [%s/%s] leg %s | n=%d | controls=%d ---",
                 spec_label, window_label, leg_label, len(df_l),
                 len(local_controls))

        # PLR
        t0 = time.time()
        try:
            res = U.run_plr(df_l, controls=local_controls,
                              n_folds=n_folds, n_reps=n_reps)
            row = U.extract_row(res, {**extra, "legis": leg_label,
                                         "model": "PLR", "iv_set": "none"})
            if row:
                rows_results.append(row)
                log.info("  PLR (%ds): pp_per_unit=%+.3f%s p=%.4f",
                         time.time() - t0, row["pp_per_unit"],
                         row["stars"], row["pval"])
        except Exception as e:
            log.error("  PLR failed: %s", e)

        # PLIV per IV set
        for iv_name, ivs in C.IV_SETS.items():
            avail = [z for z in ivs if z in df_l.columns
                       and df_l[z].std() > 0]
            if not avail:
                continue

            # First-stage F
            f = U.first_stage_F(df_l, C.TREATMENT, avail, local_controls)
            f.update({**extra, "legis": leg_label, "iv_set": iv_name})
            rows_fstage.append(f)
            log.info("  IV=%s: F=%.1f", iv_name, f["f_stat"])

            t0 = time.time()
            try:
                res = U.run_pliv(df_l, ivs=avail, controls=local_controls,
                                    n_folds=n_folds, n_reps=n_reps)
                row = U.extract_row(res, {**extra, "legis": leg_label,
                                             "model": "PLIV", "iv_set": iv_name})
                if row:
                    rows_results.append(row)
                    log.info("  PLIV %s (%ds): pp_per_unit=%+.3f%s p=%.4f",
                             iv_name, time.time() - t0,
                             row["pp_per_unit"], row["stars"], row["pval"])
            except Exception as e:
                log.error("  PLIV %s failed: %s", iv_name, e)

            # Sargan if overidentified
            if len(avail) > 1:
                try:
                    s = U.sargan_J(df_l, C.TREATMENT, avail, local_controls)
                    s.update({**extra, "legis": leg_label, "iv_set": iv_name})
                    rows_sargan.append(s)
                    log.info("  Sargan J=%.1f p=%.4f",
                             s.get("j_stat", np.nan), s.get("j_pval", np.nan))
                except Exception as e:
                    log.error("  Sargan failed: %s", e)

    return rows_results, rows_fstage, rows_sargan


def run_falsification(df: pd.DataFrame, controls: list,
                       log: logging.Logger,
                       n_folds: int = C.N_FOLDS,
                       n_reps: int = 1) -> list:
    """4 falsification tests: random Y, vote_Sim, PLIV→random, post-vote placebo."""
    log.info("\n=== FALSIFICATION TESTS ===")
    rows = []

    # 1. Random binary outcome
    log.info("[1] PLR with random Y")
    df1 = df.copy()
    df1["y_random"] = np.random.binomial(1, df1[C.TARGET].mean(), size=len(df1))
    res = U.run_plr(df1, outcome="y_random", controls=controls,
                      n_folds=n_folds, n_reps=n_reps)
    row = U.extract_row(res, {"test": "random_Y", "model": "PLR"})
    if row:
        rows.append(row)
        log.info("    pp_per_unit=%+.4f p=%.3f (should be ~0)",
                 row["pp_per_unit"], row["pval"])

    # 2. PLIV backlog → random Y
    log.info("[2] PLIV backlog with random Y")
    res = U.run_pliv(df1, ivs=C.IV_SETS["backlog"], outcome="y_random",
                       controls=controls, n_folds=n_folds, n_reps=n_reps)
    row = U.extract_row(res, {"test": "random_Y_PLIV", "model": "PLIV_backlog"})
    if row:
        rows.append(row)
        log.info("    pp_per_unit=%+.4f p=%.3f (should be ~0)",
                 row["pp_per_unit"], row["pval"])

    # 3. Vote Sim regardless of orientation
    if "voto" in df.columns:
        log.info("[3] PLR with y=vote_yes_regardless")
        df2 = df.copy()
        df2["y_sim"] = (df2["voto"] == "Sim").astype(int)
        res = U.run_plr(df2, outcome="y_sim", controls=controls,
                          n_folds=n_folds, n_reps=n_reps)
        row = U.extract_row(res, {"test": "vote_sim", "model": "PLR"})
        if row:
            rows.append(row)
            log.info("    pp_per_unit=%+.4f p=%.3f (should be ~0)",
                     row["pp_per_unit"], row["pval"])

    # 4. Post-vote placebo: load panel_emendas_post, swap T
    log.info("[4] PLR with post-vote treatment (placebo)")
    em_post = pd.read_csv(C.WINDOW_FILES["post"], sep=";", low_memory=False,
                            usecols=["idDeputado", "idVotacao",
                                      "emenda_valor"])
    em_post["emenda_M_post"] = em_post["emenda_valor"] / 1e6
    df3 = df.merge(em_post[["idDeputado", "idVotacao", "emenda_M_post"]],
                     on=["idDeputado", "idVotacao"], how="left")
    df3["emenda_M_post"] = df3["emenda_M_post"].fillna(0)
    res = U.run_plr(df3, treatment="emenda_M_post", controls=controls,
                      n_folds=n_folds, n_reps=n_reps)
    row = U.extract_row(res, {"test": "post_vote_placebo", "model": "PLR"})
    if row:
        rows.append(row)
        log.info("    pp_per_unit=%+.4f p=%.3f (should be << main est)",
                 row["pp_per_unit"], row["pval"])

    return rows


# ============================================================================
# Main
# ============================================================================

def main():
    args = parse_args()

    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("01_run_dml")

    windows = [w.strip() for w in args.windows.split(",") if w.strip()]
    log.info("Will run windows: %s", windows)

    all_results = []
    all_fstage = []
    all_sargan = []
    falsif_rows_all = []

    for window in windows:
        log.info("\n" + "#" * 70)
        log.info("# WINDOW: %s", window)
        log.info("#" * 70)

        log.info("Loading modeling panel (window=%s)", window)
        df = U.load_modeling_panel(window=window, legis=C.LEGISLATURAS, log=log)

        if args.fast:
            log.info("FAST mode: 20%% sample")
            df = df.sample(frac=0.20, random_state=42)

        log.info("Final panel: %d rows × %d cols", len(df), df.shape[1])

        # ── Reduced spec ───────────────────────────────────────────────────
        log.info("\n" + "=" * 70)
        log.info("SPEC: REDUCED CONTROLS (~30 vars) | window=%s", window)
        log.info("=" * 70)
        controls_red = [c for c in C.CONTROLS_REDUCED if c in df.columns]
        r, fs, sg = run_full(df, controls_red, "reduced", window,
                                n_folds=C.N_FOLDS, n_reps=args.reps, log=log)
        all_results.extend(r); all_fstage.extend(fs); all_sargan.extend(sg)

        # ── Full spec (optional) ───────────────────────────────────────────
        if args.legacy:
            log.info("\n" + "=" * 70)
            log.info("SPEC: FULL CONTROLS (~191 vars) | window=%s", window)
            log.info("=" * 70)
            controls_full = C.get_full_controls(df)
            r, fs, sg = run_full(df, controls_full, "full", window,
                                    n_folds=C.N_FOLDS, n_reps=args.reps, log=log)
            all_results.extend(r); all_fstage.extend(fs); all_sargan.extend(sg)

        # ── Falsification (only on first window) ────────────────────────────
        if window == windows[0]:
            falsif_rows = run_falsification(df, controls_red, log,
                                               n_folds=C.N_FOLDS, n_reps=1)
            for row in falsif_rows:
                row["window"] = window
            falsif_rows_all.extend(falsif_rows)

    # ── Save ───────────────────────────────────────────────────────────────
    out_dir = C.RESULTS
    pd.DataFrame(all_results).to_csv(out_dir / "main_results.csv",
                                        sep=";", index=False)
    pd.DataFrame(all_fstage).to_csv(out_dir / "main_fstage.csv",
                                       sep=";", index=False)
    pd.DataFrame(all_sargan).to_csv(out_dir / "main_sargan.csv",
                                       sep=";", index=False)
    pd.DataFrame(falsif_rows_all).to_csv(out_dir / "main_falsification.csv",
                                            sep=";", index=False)
    log.info("\n✓ saved to %s", out_dir)
    log.info("  main_results.csv (%d rows)", len(all_results))
    log.info("  main_fstage.csv (%d rows)", len(all_fstage))
    log.info("  main_sargan.csv (%d rows)", len(all_sargan))
    log.info("  main_falsification.csv (%d rows)", len(falsif_rows_all))


if __name__ == "__main__":
    main()
