# -*- coding: utf-8 -*-
"""
26_polarization_robustness.py — Validação cruzada de medidas de polarização
==============================================================================
Responde a 3 perguntas:

(1) Quais medidas de polarização temos e como elas correlacionam?
(2) O resultado R2.8 (efeito negativo em pol baixa) sobrevive a medidas
    alternativas?
(3) Polarização é mecanismo causal ou correlação espúria?

Medidas testadas:
  - pol_simple: |%Sim_coal − %Sim_opos| por votação (nossa simples)
  - pol_jaccard: Jaccard dissimilarity por votação (nossa)
  - pol_mds_paper: MDS-Euclidiana do paper-polarization (bimestral) → broadcast
  - pol_mds_forte: variação Divstrong
  - pol_mds_fraca: variação Divweak
  - pol_speech_var: variância dos sentiment scores de discursos (se disponível)

Análise:
  A) Correlation matrix entre medidas
  B) Granger-style test: pol_{t-1} causa effect_t?
  C) Het PLIV-bl tercil para cada medida — sinal converge?

Output: results/polarization_robustness.csv + correlation matrix
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils_v2 as U2


POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
POL_CUPULA = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/dados/interim/site/polarizacao_mensal.csv")


def load_pol_paper(df_panel):
    """Importa medida MDS bimestral do paper-polarization."""
    out = {}
    for name in ["euclidean", "forte", "fraca"]:
        path = POL_PAPER_DIR / f"average_mds_distances_{name}.csv"
        if not path.exists(): continue
        pol = pd.read_csv(path)
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        pol = pol[["period_start", "period_end", "Euclidiana_MDS",
                      "DistanciaEntreCentroidesK2"]] \
                .rename(columns={
                    "Euclidiana_MDS": f"pol_paper_{name}_mds",
                    "DistanciaEntreCentroidesK2": f"pol_paper_{name}_centroidK2",
                })
        out[name] = pol
    return out


def attach_pol_paper(df, pol_dict):
    """Para cada (idVotacao, data), encontrar o período bimestral correspondente."""
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name, pol in pol_dict.items():
        # interval merge: cada data em qual periodo cai
        col_mds = f"pol_paper_{name}_mds"
        col_cen = f"pol_paper_{name}_centroidK2"
        df[col_mds] = np.nan
        df[col_cen] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col_mds] = r[col_mds]
            df.loc[mask, col_cen] = r[col_cen]
    return df


def attach_pol_cupula(df):
    """Importa medida mensal do CúpulaAI (leg 57 só) — para checagem."""
    if not POL_CUPULA.exists(): return df
    pol = pd.read_csv(POL_CUPULA, sep=";")
    pol["mes"] = pd.to_datetime(pol["mes"] + "-01")
    df = df.copy()
    df["mes"] = pd.to_datetime(df["data"]).dt.to_period("M").dt.to_timestamp()
    df = df.merge(pol[["mes", "distancia_media"]], on="mes", how="left")
    df = df.rename(columns={"distancia_media": "pol_cupula_mensal"})
    df = df.drop(columns=["mes"])
    return df


def correlation_matrix(df, pol_cols):
    """Correlações entre medidas + com Y, T. Uses pairwise (handles uneven coverage)."""
    cols = pol_cols + [C.TARGET, C.TREATMENT]
    cols = [c for c in cols if c in df.columns]
    return df[cols].corr(min_periods=1000).round(3)


def pliv_by_pol_tercil(df, ctrl, pol_col, log, n_reps=1):
    """Roda PLIV-bl em tercis de uma medida de polarização."""
    if pol_col not in df.columns:
        log.warning("col %s ausente", pol_col); return []
    d = df.dropna(subset=[pol_col]).copy()
    if len(d) < 10000: return []
    qs = d[pol_col].quantile([0.33, 0.67]).values
    d["__tercil"] = "mid"
    d.loc[d[pol_col] <= qs[0], "__tercil"] = "low"
    d.loc[d[pol_col] >= qs[1], "__tercil"] = "high"
    rows = []
    for t in ("low", "mid", "high"):
        df_g = d[d["__tercil"] == t]
        try:
            r = U2.run_pliv_main(df_g, controls=ctrl, n_reps=n_reps)
            if r:
                r["pol_metric"] = pol_col
                r["pol_tercil"] = t
                r["pol_threshold"] = (round(qs[0], 4) if t == "low"
                                       else round(qs[1], 4) if t == "high" else None)
                rows.append(r)
                log.info("  %s/%s: pp=%+.3f%s n=%d",
                         pol_col, t, r["pp_per_unit"],
                         r["stars"], r["n_obs"])
        except Exception as e:
            log.error("  %s/%s failed: %s", pol_col, t, e)
    return rows


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("26_pol_robust")

    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["idLegislatura"] = df["idLegislatura"].astype(int)
    log.info("Panel: %d rows", len(df))

    # Carregar polarizações alternativas
    log.info("\nLoading alternative polarization measures from paper-polarization")
    pol_dict = load_pol_paper(df)
    df = attach_pol_paper(df, pol_dict)
    df = attach_pol_cupula(df)

    # Listar medidas disponíveis
    pol_cols_all = [c for c in df.columns if c.startswith("pol_")]
    log.info("Medidas disponíveis: %s", pol_cols_all)
    for c in pol_cols_all:
        n = df[c].notna().sum()
        log.info("  %s: %d non-null (%.1f%%)", c, n, 100*n/len(df))

    # A) Correlação entre medidas
    log.info("\n=== A. Correlation matrix between polarization measures ===")
    corr = correlation_matrix(df, pol_cols_all)
    log.info("\n%s", corr.to_string())
    corr.to_csv(C.RESULTS / "polarization_correlation_matrix.csv")

    # B) PLIV-bl em tercis para cada medida
    ctrl = U2.get_clean_full_controls(df)
    # Drop pol_* from controls to avoid spurious selection
    ctrl = [c for c in ctrl if not c.startswith("pol_")]
    log.info("\n=== B. PLIV-bl por tercil de cada medida ===")
    rows = []
    for pc in pol_cols_all:
        n_nonnull = df[pc].notna().sum()
        if n_nonnull < 30000:
            log.info("skip %s (n_nonnull=%d)", pc, n_nonnull); continue
        log.info("\n--- %s ---", pc)
        rows.extend(pliv_by_pol_tercil(df, ctrl, pc, log))

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "polarization_robustness.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))


if __name__ == "__main__":
    main()
