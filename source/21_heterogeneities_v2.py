# -*- coding: utf-8 -*-
"""
21_heterogeneities_v2.py — R2.1 a R2.5 na spec definitiva
============================================================
Re-roda heterogeneidades pedidas pelos professores (R2.1-R2.5) com
spec principal: full_clean + Deputy FE + cluster-SE.

R2.1: oposição vs coalizão (já em fine_heterogeneity_v2)
R2.2: alinhamento histórico (terciles)
R2.3: ano eleitoral (já em fine_heterogeneity_v2)
R2.4: margem da votação (apertado/moderado/lopsided)
R2.5: tipo da proposta (já em fine_heterogeneity_v2)

Output: results/heterogeneities_v2.csv (consolida tudo)
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
import _utils_v2 as U2


def add_alignment_history(df, lag_window=20):
    """% alinhamento nas últimas N votações do deputado (rolling, strict shift)."""
    df = df.sort_values(["idDeputado", "data"]).reset_index(drop=True)
    df["align_hist_pre"] = (
        df.groupby("idDeputado")["alinhamento"]
            .transform(lambda x: x.shift(1).rolling(window=lag_window,
                                                          min_periods=5).mean())
    )
    df["align_hist_pre"] = df["align_hist_pre"].fillna(df["alinhamento"].mean())
    qs = df["align_hist_pre"].quantile([0.33, 0.67]).values
    df["align_hist_tercil"] = pd.cut(
        df["align_hist_pre"],
        bins=[-1, qs[0], qs[1], 2],
        labels=["low", "mid", "high"],
    )
    return df


def add_vote_margin(df):
    """Margem |votosSim - votosNao| / total. Cuts em apertado/moderado/lopsided."""
    if "votosSim" in df.columns:
        total = (df["votosSim"].fillna(0) + df["votosNao"].fillna(0) +
                    df["votosOutros"].fillna(0))
        margin = (df["votosSim"].fillna(0) - df["votosNao"].fillna(0)).abs()
        df["margin_abs"] = (margin / total.replace(0, np.nan)).fillna(0)
        df["margin_band"] = "lopsided"
        df.loc[df["margin_abs"] < 0.30, "margin_band"] = "moderate"
        df.loc[df["margin_abs"] < 0.10, "margin_band"] = "close"
    else:
        df["margin_band"] = "unknown"
    return df


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=1)
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("21_het_v2")

    log.info("Loading panel (window=pre)")
    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["data"] = pd.to_datetime(df["data"])
    df["idLegislatura"] = df["idLegislatura"].astype(int)

    df = add_alignment_history(df)
    df = add_vote_margin(df)

    rows = []
    ctrl = U2.get_clean_full_controls(df)

    # R2.2 — alinhamento histórico (não estava no fine_heterogeneity_v2)
    log.info("\n=== R2.2 — alinhamento histórico ===")
    for tercil in ("low", "mid", "high"):
        df_g = df[df["align_hist_tercil"] == tercil].copy()
        log.info("--- align_hist=%s | n=%d ---", tercil, len(df_g))
        try:
            r = U2.run_pliv_main(df_g, controls=ctrl, n_reps=args.reps)
            if r:
                r.update({"category": "R2.2_align_hist", "group": f"hist_{tercil}"})
                rows.append(r)
                log.info("  PLIV-bl: pp/R$M=%+.3f%s CI=[%+.3f,%+.3f]",
                         r["pp_per_unit"], r["stars"],
                         r["ci95_lo_pp"], r["ci95_hi_pp"])
        except Exception as e:
            log.error("  failed: %s", e)

    # R2.4 — margem
    log.info("\n=== R2.4 — margem da votação ===")
    for band in ("close", "moderate", "lopsided"):
        df_g = df[df["margin_band"] == band].copy()
        log.info("--- margin=%s | n=%d ---", band, len(df_g))
        try:
            r = U2.run_pliv_main(df_g, controls=ctrl, n_reps=args.reps)
            if r:
                r.update({"category": "R2.4_margin", "group": f"margin_{band}"})
                rows.append(r)
                log.info("  PLIV-bl: pp/R$M=%+.3f%s",
                         r["pp_per_unit"], r["stars"])
        except Exception as e:
            log.error("  failed: %s", e)

    # R2.4 × leg
    for leg in (55, 56):
        df_l = df[df["idLegislatura"] == leg]
        for band in ("close", "moderate", "lopsided"):
            df_g = df_l[df_l["margin_band"] == band].copy()
            label = f"leg{leg}_margin_{band}"
            log.info("--- %s | n=%d ---", label, len(df_g))
            try:
                r = U2.run_pliv_main(df_g, controls=ctrl, n_reps=args.reps)
                if r:
                    r.update({"category": "R2.4_margin", "group": label})
                    rows.append(r)
                    log.info("  PLIV-bl: pp/R$M=%+.3f%s",
                             r["pp_per_unit"], r["stars"])
            except Exception as e:
                log.error("  failed: %s", e)

    # R2.2 × leg
    log.info("\n=== R2.2 × leg ===")
    for leg in (55, 56):
        df_l = df[df["idLegislatura"] == leg]
        for tercil in ("low", "mid", "high"):
            df_g = df_l[df_l["align_hist_tercil"] == tercil].copy()
            label = f"leg{leg}_hist_{tercil}"
            log.info("--- %s | n=%d ---", label, len(df_g))
            try:
                r = U2.run_pliv_main(df_g, controls=ctrl, n_reps=args.reps)
                if r:
                    r.update({"category": "R2.2_align_hist", "group": label})
                    rows.append(r)
                    log.info("  PLIV-bl: pp/R$M=%+.3f%s",
                             r["pp_per_unit"], r["stars"])
            except Exception as e:
                log.error("  failed: %s", e)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "heterogeneities_v2.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))


if __name__ == "__main__":
    main()
