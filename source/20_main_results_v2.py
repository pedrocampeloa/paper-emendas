# -*- coding: utf-8 -*-
"""
20_main_results_v2.py — Main results na spec definitiva
========================================================
Roda PLR + PLIV-backlog + PLIV-fiscal por (leg, spec) com Deputy FE +
cluster-SE. Substitui o 01_run_dml.py para a versão final do paper.

Output:
  results/main_results_v2.csv  → tabela principal do paper
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils_v2 as U2


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
    log = logging.getLogger("20_main_v2")

    log.info("Loading panel (window=pre)")
    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["idLegislatura"] = df["idLegislatura"].astype(int)
    log.info("Final panel: %d rows", len(df))

    specs_list = [s.strip() for s in args.specs.split(",")]
    legs_list = [s.strip() for s in args.legs.split(",")]

    rows = []
    for spec_name in specs_list:
        if spec_name == "reduced":
            ctrl = [c for c in C.CONTROLS_REDUCED if c in df.columns]
        elif spec_name == "full_clean":
            ctrl = U2.get_clean_full_controls(df)
        else:
            log.warning("unknown spec: %s — skipping", spec_name); continue

        for leg_label in legs_list:
            df_l = df.copy() if leg_label == "all" else df[df["idLegislatura"] == int(leg_label)]
            log.info("\n=== %s | leg=%s | n=%d ===",
                     spec_name, leg_label, len(df_l))

            # PLR
            try:
                t0 = time.time()
                row = U2.run_plr_main(df_l, controls=ctrl, n_reps=args.reps)
                if row:
                    row.update({"spec": spec_name, "legis": leg_label,
                                  "iv_set": "none"})
                    rows.append(row)
                    log.info("  PLR (%ds): pp/R$M=%+.3f%s CI=[%+.3f,%+.3f]",
                             int(time.time()-t0), row["pp_per_unit"],
                             row["stars"], row["ci95_lo_pp"], row["ci95_hi_pp"])
            except Exception as e:
                log.error("  PLR failed: %s", e)

            # PLIV-backlog
            try:
                t0 = time.time()
                row = U2.run_pliv_main(df_l, controls=ctrl,
                                            iv_set="backlog", n_reps=args.reps)
                if row:
                    row.update({"spec": spec_name, "legis": leg_label})
                    rows.append(row)
                    log.info("  PLIV-bl (%ds): pp/R$M=%+.3f%s CI=[%+.3f,%+.3f]",
                             int(time.time()-t0), row["pp_per_unit"],
                             row["stars"], row["ci95_lo_pp"], row["ci95_hi_pp"])
            except Exception as e:
                log.error("  PLIV-bl failed: %s", e)

            # PLIV-fiscal (for comparison)
            try:
                t0 = time.time()
                row = U2.run_pliv_main(df_l, controls=ctrl,
                                            iv_set="fiscal", n_reps=args.reps)
                if row:
                    row.update({"spec": spec_name, "legis": leg_label})
                    rows.append(row)
                    log.info("  PLIV-fiscal (%ds): pp/R$M=%+.3f%s",
                             int(time.time()-t0), row["pp_per_unit"],
                             row["stars"])
            except Exception as e:
                log.error("  PLIV-fiscal failed: %s", e)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "main_results_v2.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))
    log.info("\n%s", df_out[["spec","legis","model","iv_set","pp_per_unit",
                                  "ci95_lo_pp","ci95_hi_pp","stars","n_obs",
                                  "n_clusters"]].to_string(index=False))


if __name__ == "__main__":
    main()
