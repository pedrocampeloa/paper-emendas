# -*- coding: utf-8 -*-
"""
25_heterogeneity_extensive.py — Heterogeneidade EXTENSIVA
==============================================================
Vasculha dezenas de cortes para descobrir onde o sinal é positivo,
onde é negativo, e por quê.

Cortes testados:
  A. Por UF (top 12 UFs por n)
  B. Por região (5 regiões)
  C. Por partido (top 15 partidos)
  D. Por bloco coalizão/oposição × ano eleitoral × leg
  E. Por idade do deputado (terciles)
  F. Por sexo do deputado
  G. Por escolaridade
  H. Por tipo de proposta × ano
  I. Por orientação do governo × leg
  J. Por margem da votação × leg
  K. Por mês/trimestre do ano
  L. Por ano calendário
  M. Por (leg × ano)
  N. Por (tipo prop × leg)
  O. Por número de mandatos (senioridade)
  P. Por região × leg (interação)
  Q. Por mesa diretora (sim/não)
  R. Por tamanho do partido

Todos com spec principal: full_clean + Deputy FE + cluster-SE.

Output: results/heterogeneity_extensive.csv
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


def run_group_safe(df_g, ctrl, label, log, n_reps=1):
    """Roda PLIV-bl com FE+cluster; retorna dict ou None."""
    if len(df_g) < 5000:
        log.info("  skip %s (n=%d)", label, len(df_g))
        return None
    if df_g["idDeputado"].nunique() < 40:
        log.info("  skip %s (clusters=%d)", label, df_g["idDeputado"].nunique())
        return None
    try:
        t0 = time.time()
        r = U2.run_pliv_main(df_g, controls=ctrl, n_reps=n_reps)
        if r:
            r["group"] = label
            log.info("  %s (%ds): pp=%+.3f%s n=%d c=%d",
                     label, int(time.time()-t0), r["pp_per_unit"],
                     r["stars"], r["n_obs"], r["n_clusters"])
        return r
    except Exception as e:
        log.error("  %s failed: %s", label, e)
        return None


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("25_het_ext")

    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["data"] = pd.to_datetime(df["data"])
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    df["trimestre"] = ((df["mes"] - 1) // 3) + 1
    df["idLegislatura"] = df["idLegislatura"].astype(int)
    ctrl = U2.get_clean_full_controls(df)
    log.info("Panel: %d | full_clean ctrls: %d", len(df), len(ctrl))

    rows = []

    # ── A. Por UF ────────────────────────────────────────────────────────
    log.info("\n=== A. Por UF (todas com n>5000) ===")
    uf_counts = df["siglaUf"].value_counts()
    big_ufs = uf_counts[uf_counts > 5000].index.tolist()
    for uf in big_ufs:
        for leg in (None, 55, 56):
            df_g = df[df["siglaUf"] == uf]
            if leg is not None:
                df_g = df_g[df_g["idLegislatura"] == leg]
            label = f"UF_{uf}_leg{leg if leg else 'all'}"
            r = run_group_safe(df_g, ctrl, label, log)
            if r:
                r["category"] = "A_UF"; rows.append(r)

    # ── B. Por região (já temos d_reg_*) ─────────────────────────────────
    log.info("\n=== B. Por região × leg ===")
    for reg in ("N", "NE", "SE", "S", "CO"):
        col = f"d_reg_{reg}"
        if col not in df.columns: continue
        for leg in (None, 55, 56):
            df_g = df[df[col] == 1]
            if leg is not None:
                df_g = df_g[df_g["idLegislatura"] == leg]
            label = f"reg_{reg}_leg{leg if leg else 'all'}"
            r = run_group_safe(df_g, ctrl, label, log)
            if r:
                r["category"] = "B_Region"; rows.append(r)

    # ── C. Por partido top 10 ────────────────────────────────────────────
    log.info("\n=== C. Por partido (top 10 by n) × leg ===")
    party_counts = df["siglaPartido"].value_counts().head(10)
    for party in party_counts.index:
        for leg in (None, 55, 56):
            df_g = df[df["siglaPartido"] == party]
            if leg is not None:
                df_g = df_g[df_g["idLegislatura"] == leg]
            label = f"party_{party}_leg{leg if leg else 'all'}"
            r = run_group_safe(df_g, ctrl, label, log)
            if r:
                r["category"] = "C_Party"; rows.append(r)

    # ── D. Por sexo do deputado ───────────────────────────────────────────
    log.info("\n=== D. Por sexo × leg ===")
    if "d_homem" in df.columns:
        for sex_val, sex_label in [(1, "homem"), (0, "mulher")]:
            for leg in (None, 55, 56):
                df_g = df[df["d_homem"] == sex_val]
                if leg is not None:
                    df_g = df_g[df_g["idLegislatura"] == leg]
                label = f"sex_{sex_label}_leg{leg if leg else 'all'}"
                r = run_group_safe(df_g, ctrl, label, log)
                if r:
                    r["category"] = "D_Sex"; rows.append(r)

    # ── E. Por idade tercil ──────────────────────────────────────────────
    log.info("\n=== E. Por idade tercil × leg ===")
    if "idade" in df.columns:
        df_ = df.dropna(subset=["idade"]).copy()
        qs = df_["idade"].quantile([0.33, 0.67]).values
        df["age_tercil"] = "mid"
        df.loc[df["idade"] <= qs[0], "age_tercil"] = "young"
        df.loc[df["idade"] >= qs[1], "age_tercil"] = "old"
        for tercil in ("young", "mid", "old"):
            for leg in (None, 55, 56):
                df_g = df[df["age_tercil"] == tercil]
                if leg is not None:
                    df_g = df_g[df_g["idLegislatura"] == leg]
                label = f"age_{tercil}_leg{leg if leg else 'all'}"
                r = run_group_safe(df_g, ctrl, label, log)
                if r:
                    r["category"] = "E_Age"; rows.append(r)

    # ── F. Por nível de escolaridade ─────────────────────────────────────
    log.info("\n=== F. Por escolaridade × leg ===")
    if "indice_escolaridade" in df.columns:
        for nivel in (1, 2, 3, 4, 5):
            for leg in (None, 55, 56):
                df_g = df[df["indice_escolaridade"] == nivel]
                if leg is not None:
                    df_g = df_g[df_g["idLegislatura"] == leg]
                label = f"esc_{nivel}_leg{leg if leg else 'all'}"
                r = run_group_safe(df_g, ctrl, label, log)
                if r:
                    r["category"] = "F_Education"; rows.append(r)

    # ── G. Por trimestre × leg ───────────────────────────────────────────
    log.info("\n=== G. Por trimestre × leg ===")
    for q in (1, 2, 3, 4):
        for leg in (None, 55, 56):
            df_g = df[df["trimestre"] == q]
            if leg is not None:
                df_g = df_g[df_g["idLegislatura"] == leg]
            label = f"Q{q}_leg{leg if leg else 'all'}"
            r = run_group_safe(df_g, ctrl, label, log)
            if r:
                r["category"] = "G_Quarter"; rows.append(r)

    # ── H. Por mandatos n_legis ──────────────────────────────────────────
    log.info("\n=== H. Por senioridade (n_legis) × leg ===")
    if "n_legis" in df.columns:
        for sen_label, sen_filter in [
            ("freshman_1leg", lambda d: d["n_legis"] <= 1),
            ("mid_2-3leg", lambda d: (d["n_legis"] >= 2) & (d["n_legis"] <= 3)),
            ("senior_4plus", lambda d: d["n_legis"] >= 4),
        ]:
            for leg in (None, 55, 56):
                df_g = df[sen_filter(df)]
                if leg is not None:
                    df_g = df_g[df_g["idLegislatura"] == leg]
                label = f"{sen_label}_leg{leg if leg else 'all'}"
                r = run_group_safe(df_g, ctrl, label, log)
                if r:
                    r["category"] = "H_Seniority"; rows.append(r)

    # ── I. Mesa diretora ─────────────────────────────────────────────────
    log.info("\n=== I. Mesa diretora × leg ===")
    mesa_cols = [c for c in df.columns if c.startswith("d_mesa_")]
    if mesa_cols:
        df["em_mesa"] = (df[mesa_cols].sum(axis=1) > 0).astype(int)
        for mesa_val, mesa_label in [(1, "mesa_yes"), (0, "mesa_no")]:
            for leg in (None, 55, 56):
                df_g = df[df["em_mesa"] == mesa_val]
                if leg is not None:
                    df_g = df_g[df_g["idLegislatura"] == leg]
                label = f"{mesa_label}_leg{leg if leg else 'all'}"
                r = run_group_safe(df_g, ctrl, label, log)
                if r:
                    r["category"] = "I_Mesa"; rows.append(r)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "heterogeneity_extensive.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))

    if len(df_out) > 0:
        sub = df_out.sort_values("pp_per_unit")
        log.info("\n=== TOP-10 MAIS POSITIVOS ===")
        log.info("\n%s", sub.tail(10)[["category","group","pp_per_unit",
                                            "ci95_lo_pp","ci95_hi_pp","stars",
                                            "n_obs"]].to_string(index=False))
        log.info("\n=== TOP-10 MAIS NEGATIVOS ===")
        log.info("\n%s", sub.head(10)[["category","group","pp_per_unit",
                                            "ci95_lo_pp","ci95_hi_pp","stars",
                                            "n_obs"]].to_string(index=False))


if __name__ == "__main__":
    main()
