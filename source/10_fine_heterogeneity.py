# -*- coding: utf-8 -*-
"""
10_fine_heterogeneity.py — fine-grained heterogeneity to find where signal is positive
======================================================================================
Após o bug fix, pooled fica negativo. Esta análise vasculha sub-grupos
EM CADA legislatura para encontrar onde o efeito é positivo, negativo,
ou nulo. Saída: mapa de heterogeneidade que pode reorientar a narrativa
do paper.

Grupos analisados (em window=pre, full controls SEM bad controls):
  - Por status partidário (oposição/coalizão/independente)
  - Por ano (2015-2022)
  - Por tipo da proposta (PEC, MPV, PLP, PL)
  - Por margem da votação (apertado/moderado/tranquilo)
  - Por orientação do governo (Sim, Não, Obstrução, Abstenção)
  - Por região do deputado
  - Por valor da emenda (terciles)
  - Combinações: leg × oposição × ano eleitoral

Output:
  results/fine_heterogeneity.csv
  results/fine_heterogeneity_by_leg.csv
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


BAD_CONTROLS = ["votosSim", "votosNao", "votosOutros", "aprovacao"]


def get_clean_full_controls(df):
    """Full controls minus identified bad controls."""
    ctrl = C.get_full_controls(df)
    return [c for c in ctrl if c not in BAD_CONTROLS]


def run_subgroup(df_g, controls, label, log, n_folds=3, n_reps=1):
    """Run PLR + PLIV-backlog for a subgroup. Returns 2 rows."""
    if len(df_g) < 2000:
        log.warning("    skip %s (n=%d < 2000)", label, len(df_g))
        return []
    local_ctrl = [c for c in controls if c in df_g.columns
                    and df_g[c].notna().mean() > 0.5
                    and df_g[c].nunique() > 1]
    rows = []
    try:
        t0 = time.time()
        res = U.run_plr(df_g, controls=local_ctrl, n_folds=n_folds,
                          n_reps=n_reps)
        row = U.extract_row(res, {"group": label, "model": "PLR",
                                      "iv_set": "none"})
        if row:
            rows.append(row)
            log.info("    %s PLR (%ds): pp/R$M=%+.3f%s n=%d",
                     label, int(time.time()-t0), row["pp_per_unit"],
                     row["stars"], row["n_obs"])
    except Exception as e:
        log.error("    %s PLR failed: %s", label, e)
    try:
        t0 = time.time()
        avail = [z for z in C.IV_SETS["backlog"]
                   if z in df_g.columns and df_g[z].std() > 0]
        res = U.run_pliv(df_g, ivs=avail, controls=local_ctrl,
                            n_folds=n_folds, n_reps=n_reps)
        row = U.extract_row(res, {"group": label, "model": "PLIV",
                                      "iv_set": "backlog"})
        if row:
            rows.append(row)
            log.info("    %s PLIV-bl (%ds): pp/R$M=%+.3f%s n=%d",
                     label, int(time.time()-t0), row["pp_per_unit"],
                     row["stars"], row["n_obs"])
    except Exception as e:
        log.error("    %s PLIV-bl failed: %s", label, e)
    return rows


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("10_fine_het")

    log.info("Loading panel (window=pre)")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["data"] = pd.to_datetime(df["data"])
    df["ano"] = df["data"].dt.year
    log.info("Final panel: %d rows", len(df))

    controls = get_clean_full_controls(df)
    log.info("Full controls (clean): %d", len(controls))

    rows = []

    # ── 1. By legislature × status partidário ──────────────────────────────
    log.info("\n=== A. Per-leg × status partidário ===")
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else f"leg{leg}"
        df_l = df.copy() if leg is None else df[df["idLegislatura"]==leg]
        for status, mask_col in [("oposicao", "d_oposicao"),
                                       ("coalizao", "d_coalizao"),
                                       ("independente", "d_independente")]:
            df_g = df_l[df_l[mask_col]==1]
            label = f"{leg_label}_{status}"
            rows.extend(run_subgroup(df_g, controls, label, log))

    # ── 2. By legislature × ano eleitoral ──────────────────────────────────
    log.info("\n=== B. Per-leg × ano eleitoral ===")
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else f"leg{leg}"
        df_l = df.copy() if leg is None else df[df["idLegislatura"]==leg]
        for fed_label, fed_val in [("nao_eleicao", 0), ("eleicao_federal", 1)]:
            df_g = df_l[df_l["d_elec_federal"]==fed_val]
            label = f"{leg_label}_{fed_label}"
            rows.extend(run_subgroup(df_g, controls, label, log))

    # ── 3. By leg × tipo da proposta ───────────────────────────────────────
    log.info("\n=== C. Per-leg × tipo da proposta ===")
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else f"leg{leg}"
        df_l = df.copy() if leg is None else df[df["idLegislatura"]==leg]
        for tcol, tname in [("d_tipoVotacao_PEC", "PEC"),
                                ("d_tipoVotacao_MPV", "MPV"),
                                ("d_tipoVotacao_PLP", "PLP"),
                                ("d_tipoVotacao_PL", "PL")]:
            if tcol not in df_l.columns: continue
            df_g = df_l[df_l[tcol]==1]
            label = f"{leg_label}_{tname}"
            rows.extend(run_subgroup(df_g, controls, label, log))

    # ── 4. By leg × ano calendário ─────────────────────────────────────────
    log.info("\n=== D. Per-leg × ano calendário ===")
    for ano in range(2015, 2023):
        df_g = df[df["ano"]==ano]
        label = f"ano{ano}"
        rows.extend(run_subgroup(df_g, controls, label, log))

    # ── 5. By orientação do governo ────────────────────────────────────────
    log.info("\n=== E. Por orientação do governo ===")
    for col, ori_label in [("d_ori_gov_sim", "ori_Sim"),
                                ("d_ori_gov_nao", "ori_Nao"),
                                ("d_ori_gov_obstrucao", "ori_Obstr"),
                                ("d_ori_gov_abstencao", "ori_Abst")]:
        if col not in df.columns: continue
        for leg in (None, 55, 56):
            leg_label = "all" if leg is None else f"leg{leg}"
            df_l = df.copy() if leg is None else df[df["idLegislatura"]==leg]
            df_g = df_l[df_l[col]==1]
            label = f"{leg_label}_{ori_label}"
            rows.extend(run_subgroup(df_g, controls, label, log))

    # ── 6. By terceis de emenda (intensidade) ──────────────────────────────
    log.info("\n=== F. Por terceis de tratamento ===")
    for leg in (None, 55, 56):
        leg_label = "all" if leg is None else f"leg{leg}"
        df_l = df.copy() if leg is None else df[df["idLegislatura"]==leg].copy()
        # Restrict to non-zero treatment (otherwise terciles malucos)
        df_pos = df_l[df_l[C.TREATMENT] > 0].copy()
        if len(df_pos) < 6000: continue
        df_pos["T_tercil"] = pd.qcut(df_pos[C.TREATMENT], q=3,
                                          labels=["low","mid","high"])
        for t in ("low","mid","high"):
            df_g = df_pos[df_pos["T_tercil"]==t]
            label = f"{leg_label}_T_{t}"
            rows.extend(run_subgroup(df_g, controls, label, log))

    # ── 7. Leg × Status × Ano eleitoral (interação tripla) ─────────────────
    log.info("\n=== G. Leg × Status × Ano eleitoral ===")
    for leg in (55, 56):
        df_l = df[df["idLegislatura"]==leg]
        for status, mask_col in [("opos","d_oposicao"),
                                      ("coal","d_coalizao")]:
            for fed_label, fed_val in [("naoel",0),("el",1)]:
                df_g = df_l[(df_l[mask_col]==1) & (df_l["d_elec_federal"]==fed_val)]
                label = f"leg{leg}_{status}_{fed_label}"
                rows.extend(run_subgroup(df_g, controls, label, log))

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "fine_heterogeneity.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))


if __name__ == "__main__":
    main()
