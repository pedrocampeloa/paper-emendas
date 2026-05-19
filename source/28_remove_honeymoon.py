# -*- coding: utf-8 -*-
"""
28_remove_honeymoon.py — Robustez removendo períodos atípicos
================================================================
Pergunta: o efeito negativo na leg 56 sobrevive se removermos:
  (a) lua de mel (primeiros 6 meses de cada governo)
  (b) Q1 2020 (choque pandemia)
  (c) ano eleitoral (já testado, mas reforça)

Períodos definidos:
  honeymoon_55: 2016-05-12 → 2016-11-12 (6 meses pós-impeachment Dilma)
  honeymoon_56: 2019-01-01 → 2019-07-01 (6 meses pós-posse Bolsonaro)
  pandemic_2020Q1: 2020-01-01 → 2020-06-30 (1º semestre 2020)

Specs principais: full_clean + FE + cluster.

Output: results/honeymoon_robustness.csv
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
import _utils_v2 as U2


PERIODS = {
    "honeymoon_55": ("2016-05-12", "2016-11-12"),
    "honeymoon_56": ("2019-01-01", "2019-07-01"),
    "pandemic_q1_2020": ("2020-01-01", "2020-06-30"),
}


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("28_honeymoon")

    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["data"] = pd.to_datetime(df["data"])
    df["idLegislatura"] = df["idLegislatura"].astype(int)
    ctrl = U2.get_clean_full_controls(df)
    log.info("Panel: %d | clean ctrls: %d", len(df), len(ctrl))

    rows = []

    # ── Baseline (sem nenhuma exclusão) ─────────────────────────────────────
    log.info("\n=== Baseline (no exclusion) ===")
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else str(leg)
        df_l = df if leg is None else df[df["idLegislatura"] == leg]
        try:
            t0 = time.time()
            r = U2.run_pliv_main(df_l, controls=ctrl, n_reps=1)
            if r:
                r["scenario"] = "baseline"; r["legis"] = leg_label
                rows.append(r)
                log.info("  baseline leg%s (%ds): pp=%+.3f%s n=%d",
                         leg_label, int(time.time()-t0),
                         r["pp_per_unit"], r["stars"], r["n_obs"])
        except Exception as e:
            log.error("  baseline leg%s failed: %s", leg_label, e)

    # ── Remover honeymoon 55 ────────────────────────────────────────────────
    log.info("\n=== Remove honeymoon 55 ===")
    start, end = PERIODS["honeymoon_55"]
    df_no_h55 = df[~((df["data"] >= start) & (df["data"] <= end))]
    log.info("  removed %d rows (honeymoon 55)", len(df) - len(df_no_h55))
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else str(leg)
        df_l = df_no_h55 if leg is None else df_no_h55[df_no_h55["idLegislatura"] == leg]
        try:
            t0 = time.time()
            r = U2.run_pliv_main(df_l, controls=ctrl, n_reps=1)
            if r:
                r["scenario"] = "no_honeymoon_55"; r["legis"] = leg_label
                rows.append(r)
                log.info("  leg%s (%ds): pp=%+.3f%s",
                         leg_label, int(time.time()-t0),
                         r["pp_per_unit"], r["stars"])
        except Exception as e:
            log.error("  leg%s failed: %s", leg_label, e)

    # ── Remover honeymoon 56 ────────────────────────────────────────────────
    log.info("\n=== Remove honeymoon 56 ===")
    start, end = PERIODS["honeymoon_56"]
    df_no_h56 = df[~((df["data"] >= start) & (df["data"] <= end))]
    log.info("  removed %d rows (honeymoon 56)", len(df) - len(df_no_h56))
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else str(leg)
        df_l = df_no_h56 if leg is None else df_no_h56[df_no_h56["idLegislatura"] == leg]
        try:
            t0 = time.time()
            r = U2.run_pliv_main(df_l, controls=ctrl, n_reps=1)
            if r:
                r["scenario"] = "no_honeymoon_56"; r["legis"] = leg_label
                rows.append(r)
                log.info("  leg%s (%ds): pp=%+.3f%s",
                         leg_label, int(time.time()-t0),
                         r["pp_per_unit"], r["stars"])
        except Exception as e:
            log.error("  leg%s failed: %s", leg_label, e)

    # ── Remover pandemia ────────────────────────────────────────────────────
    log.info("\n=== Remove pandemic Q1-Q2 2020 ===")
    start, end = PERIODS["pandemic_q1_2020"]
    df_no_p = df[~((df["data"] >= start) & (df["data"] <= end))]
    log.info("  removed %d rows (pandemia)", len(df) - len(df_no_p))
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else str(leg)
        df_l = df_no_p if leg is None else df_no_p[df_no_p["idLegislatura"] == leg]
        try:
            t0 = time.time()
            r = U2.run_pliv_main(df_l, controls=ctrl, n_reps=1)
            if r:
                r["scenario"] = "no_pandemic"; r["legis"] = leg_label
                rows.append(r)
                log.info("  leg%s (%ds): pp=%+.3f%s",
                         leg_label, int(time.time()-t0),
                         r["pp_per_unit"], r["stars"])
        except Exception as e:
            log.error("  leg%s failed: %s", leg_label, e)

    # ── Remover TUDO atípico ────────────────────────────────────────────────
    log.info("\n=== Remove TODOS períodos atípicos ===")
    mask = pd.Series(True, index=df.index)
    for name, (s, e) in PERIODS.items():
        mask &= ~((df["data"] >= s) & (df["data"] <= e))
    df_clean = df[mask]
    log.info("  removed %d rows (all atypical)", len(df) - len(df_clean))
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else str(leg)
        df_l = df_clean if leg is None else df_clean[df_clean["idLegislatura"] == leg]
        try:
            t0 = time.time()
            r = U2.run_pliv_main(df_l, controls=ctrl, n_reps=1)
            if r:
                r["scenario"] = "no_atypical"; r["legis"] = leg_label
                rows.append(r)
                log.info("  leg%s (%ds): pp=%+.3f%s",
                         leg_label, int(time.time()-t0),
                         r["pp_per_unit"], r["stars"])
        except Exception as e:
            log.error("  leg%s failed: %s", leg_label, e)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "honeymoon_robustness.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))
    log.info("\n%s", df_out[["scenario","legis","pp_per_unit","ci95_lo_pp",
                                  "ci95_hi_pp","stars","n_obs"]].to_string(index=False))


if __name__ == "__main__":
    main()
