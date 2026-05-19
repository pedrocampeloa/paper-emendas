# -*- coding: utf-8 -*-
"""
17_pliv_with_alt_iv.py — TIER 2.6 PLIV com IV alternativo
============================================================
Adiciona iv_uo_slowness_pondv (capacidade administrativa do ministério)
como IV adicional ao backlog. Testa se inferência fica mais robusta.

Especificações testadas:
  (a) Backlog only (baseline existente):   q4_no_ytd, ytd_exec_pct
  (b) UO-slowness only:                    iv_uo_slowness_pondv
  (c) Combined (over-id):                  backlog + uo_slowness

Aplicar Sargan: se (c) não rejeita, evidência de que ambos identificam
o mesmo LATE → fortalece identificação.

Output:
  results/tier2_pliv_alt_ivs.csv
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


def get_panel_with_alt_iv(log):
    """Load main panel and merge alt IV by (idDeputado, ano)."""
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["data"] = pd.to_datetime(df["data"])
    df["ano"] = df["data"].dt.year
    alt = pd.read_csv(C.PANEL / "iv_alternative_dep.csv", sep=";",
                        usecols=["idDeputado", "ano",
                                  "iv_uo_slowness_pondv", "iv_disaster_share"])
    df = df.merge(alt, on=["idDeputado", "ano"], how="left")
    df["iv_uo_slowness_pondv"] = df["iv_uo_slowness_pondv"].fillna(
        df["iv_uo_slowness_pondv"].median())
    df["iv_disaster_share"] = df["iv_disaster_share"].fillna(0)
    return df


BAD_CONTROLS = ["votosSim", "votosNao", "votosOutros", "aprovacao"]


def get_clean_full_controls(df):
    return [c for c in C.get_full_controls(df) if c not in BAD_CONTROLS]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--specs", default="reduced,full_clean")
    p.add_argument("--legs", default="all,55,56")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("17_pliv_alt")

    df = get_panel_with_alt_iv(log)
    log.info("Final panel with alt IV: %d rows", len(df))

    iv_sets_test = {
        "backlog": ["iv_q4_no_ytd", "iv_ytd_exec_pct"],
        "uo_slow": ["iv_uo_slowness_pondv"],
        "backlog_plus_uo": ["iv_q4_no_ytd", "iv_ytd_exec_pct",
                                 "iv_uo_slowness_pondv"],
    }

    specs_list = [s.strip() for s in args.specs.split(",")]
    legs_list = [s.strip() for s in args.legs.split(",")]

    rows = []
    for spec_name in specs_list:
        if spec_name == "reduced":
            ctrl_all = [c for c in C.CONTROLS_REDUCED if c in df.columns]
        else:
            ctrl_all = get_clean_full_controls(df)

        for leg_label in legs_list:
            df_l = df.copy() if leg_label == "all" else df[df["idLegislatura"] == int(leg_label)]
            if len(df_l) < 1000: continue
            local_ctrl = [c for c in ctrl_all if c in df_l.columns
                            and df_l[c].notna().mean() > 0.5
                            and df_l[c].nunique() > 1]

            for iv_name, ivs in iv_sets_test.items():
                avail = [z for z in ivs if z in df_l.columns
                           and df_l[z].std() > 0]
                if not avail: continue
                log.info("--- spec=%s leg=%s iv=%s n=%d ctrl=%d ---",
                         spec_name, leg_label, iv_name,
                         len(df_l), len(local_ctrl))

                # First-stage F
                fs = U.first_stage_F(df_l, C.TREATMENT, avail, local_ctrl)

                # PLIV
                try:
                    t0 = time.time()
                    res = U.run_pliv(df_l, ivs=avail, controls=local_ctrl,
                                        n_folds=3, n_reps=args.reps)
                    row = U.extract_row(res, {"spec": spec_name,
                                                  "legis": leg_label,
                                                  "iv_set": iv_name,
                                                  "model": "PLIV"})
                    if row:
                        row["f_stat"] = fs.get("f_stat", 0)
                        rows.append(row)
                        log.info("  PLIV-%s (%ds): pp/R$M=%+.3f%s F=%.0f",
                                 iv_name, int(time.time()-t0),
                                 row["pp_per_unit"], row["stars"], fs["f_stat"])
                except Exception as e:
                    log.error("  PLIV-%s failed: %s", iv_name, e)

                # Sargan if overidentified
                if len(avail) > 1:
                    try:
                        s = U.sargan_J(df_l, C.TREATMENT, avail, local_ctrl)
                        log.info("  Sargan J=%.2f p=%.4f df=%d",
                                 s["j_stat"], s["j_pval"], s["df"])
                    except Exception as e:
                        pass

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "tier2_pliv_alt_ivs.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s", out)
    log.info("\n%s", df_out[["spec","legis","iv_set","pp_per_unit",
                                  "stars","pval","f_stat","n_obs"]].to_string(index=False))


if __name__ == "__main__":
    main()
