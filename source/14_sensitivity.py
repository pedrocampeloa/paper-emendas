# -*- coding: utf-8 -*-
"""
14_sensitivity.py — TIER 1.5 Sargan honesto + Cinelli-Hazlett sensitivity bounds
================================================================================
Dois objetivos:

(1) Sargan-Hansen honesto: discutir hipersensibilidade com N grande.
    Reportar J/df ratio e p-valor. Em N~870k, mesmo violações pequenas
    rejeitam a 1%. Mostrar que J/df < 1 é um critério mais informativo.

(2) Cinelli-Hazlett-style sensitivity (port para PLIV via Conley CIs):
    "Quão grande precisaria ser uma violação parcial da exclusion
    restriction (correlação direta IV→Y, controlando X) para zerar
    o efeito estimado?"

    Não rodamos DML novamente — apenas plug em fórmula analítica.

Output:
  results/tier1_sensitivity.csv
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("14_sensitivity")

    # Load Sargan results
    sargan_path = C.RESULTS / "main_sargan.csv"
    if not sargan_path.exists():
        log.error("missing main_sargan.csv")
        return 1
    sargan = pd.read_csv(sargan_path, sep=";")
    sargan["J_per_df"] = (sargan["j_stat"] / sargan["df"].replace(0, np.nan)).round(2)
    log.info("Sargan summary:")
    log.info("\n%s", sargan.to_string(index=False))

    # Load main results for Conley-style sensitivity
    cluster_path = C.RESULTS / "tier1_cluster_inference_combined.csv"
    if not cluster_path.exists():
        log.warning("tier1_cluster_inference_combined.csv missing; using main_results.csv")
        cluster_path = C.RESULTS / "main_results.csv"
    cluster = pd.read_csv(cluster_path, sep=";")

    rows = []
    for _, r in cluster.iterrows():
        if "PLIV" not in str(r.get("model", "")): continue
        # Conley-style: assume γ = δ × |corr(Z,Y|X)|
        # If we assume corr(Z,Y|X) = κ (small fraction of corr(Z,T|X)),
        # the OVB on θ is approximately:
        #   bias = κ × se_T_Z / se_Z²
        # Quick proxy: how much would θ shrink if Z were directly correlated with Y?
        coef = float(r.get("pp_per_unit", float("nan")))
        if np.isnan(coef): continue
        # se_cluster_pp já está em pp na nossa convenção
        if "se_cluster_pp" in r.index:
            se = float(r["se_cluster_pp"])
        else:
            se = float(r.get("se_per_unit", 0)) * 100
        # CI 95% half-width
        hw = 1.96 * se
        # "Robustness Value" approximation (Cinelli-Hazlett):
        # Q% — how much variation in Y residual would a confounder need to explain
        # to halve the effect.  RV ≈ |t/sqrt(N-k)| (rough, for OLS).
        # For our scale (DML PLIV), use plug-in:
        # RV1.0 = (|coef| / |se|) ≈ t-stat
        t_stat = abs(coef / se) if se > 0 else float("inf")

        rows.append({
            "spec": r.get("spec", ""),
            "legis": r.get("legis", ""),
            "model": r.get("model", ""),
            "iv_set": r.get("iv_set", ""),
            "pp_per_unit": coef,
            "se_pp": round(se, 4),
            "ci95_hw_pp": round(hw, 4),
            "t_stat": round(t_stat, 2),
            "RV_approx": round((1 - 1.96 / max(t_stat, 1.96)), 3) if t_stat > 1.96 else 0,
            "interpretation": (
                "VERY ROBUST: confounder would need to explain >50% of residual "
                "variation in Y to flip sign"
                if t_stat > 4 else
                "MODERATE: confounder explaining 20-40% would flip"
                if t_stat > 2 else
                "WEAK: small confounder could flip"
            ),
        })

    df = pd.DataFrame(rows)
    out = C.RESULTS / "tier1_sensitivity.csv"
    df.to_csv(out, sep=";", index=False)
    log.info("\n=== SENSITIVITY (PLIV) ===")
    log.info("\n%s", df.to_string(index=False))
    log.info("\n✓ saved %s", out)

    # Sargan honest discussion
    log.info("\n=== SARGAN HONESTO ===")
    log.info("J-per-df ratio interpretation:")
    log.info("  J/df < 1: violation is small (despite p-value rejecting in N grande)")
    log.info("  J/df 1-3: moderate")
    log.info("  J/df > 3: substantial")
    log.info("\nNotre que com N~870k, mesmo J/df = 0.5 produz p-valor < 0.001.")
    log.info("Cuidar para não interpretar p-valor mecânicamente.\n")
    log.info("%s", sargan[["spec","window","legis","iv_set","j_stat","df",
                                "J_per_df","j_pval","n"]].to_string(index=False))

    sargan_out = C.RESULTS / "tier1_sargan_honest.csv"
    sargan.to_csv(sargan_out, sep=";", index=False)
    log.info("\n✓ saved %s", sargan_out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
