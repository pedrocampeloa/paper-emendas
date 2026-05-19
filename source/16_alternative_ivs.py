# -*- coding: utf-8 -*-
"""
16_alternative_ivs.py — TIER 2.6 IVs alternativos
====================================================
Constrói IVs adicionais para fortalecer identificação:

(A) Ministry execution heterogeneity:
    Para cada deputado-ano, qual a fração das suas emendas que foi
    direcionada a UO ("Unidade Orçamentária", ~ministério) lenta na
    execução? Variação exógena cross-deputy gerada pela mistura de
    UO no portfólio do deputado, não por sua decisão de voto.

(B) Disaster-driven (saúde de emergência / calamidade):
    Em períodos de calamidade (COVID 2020-2021), emendas de função
    "Saúde" e "Defesa Civil" foram aceleradas mecanicamente. Variação
    cross-deputy: alguns deputados têm portfólio mais concentrado em
    Saúde, outros mais em Educação/Urbanismo. A composição não é
    voto-dependente.

Output:
  data_pipeline/outputs/iv_alternative.csv   (deputy × year level)
  results/tier2_alt_ivs_correlations.csv     (corr with T, Y, existing IVs)

Use no DML:
  Adicionar como over-id IVs em PLIV-backlog. Sargan compara: se
  tradicional (q4_no_ytd) e alternativo (ministry_slow) concordam,
  inferência mais robusta. Se discordam, sinal que existe violação.
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

# Path to raw emendas
EMENDAS_RAW = "/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/dados/raw/emendas/despesas/emendas_despesas_raw.csv"


def parse_brl_value(s: pd.Series) -> pd.Series:
    """Parse BRL strings like '79.013,00' or '-' to float."""
    return (s.astype(str).str.strip()
              .str.replace(".", "", regex=False)
              .str.replace(",", ".", regex=False)
              .replace({"-": "", "nan": ""})
              .pipe(pd.to_numeric, errors="coerce"))


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("16_alt_ivs")

    log.info("Loading raw emendas (large; takes ~30s)")
    em = pd.read_csv(EMENDAS_RAW, sep=",", encoding="latin-1",
                       on_bad_lines="skip", low_memory=False,
                       usecols=["data", "fase", "valor", "funcao", "uo",
                                  "codigoUo", "autor"])
    em = em[em["fase"] == "Empenho"].copy()
    em["data"] = pd.to_datetime(em["data"], errors="coerce", dayfirst=True)
    em["valor"] = parse_brl_value(em["valor"])
    em = em.dropna(subset=["data", "valor", "autor"])
    em["ano"] = em["data"].dt.year
    log.info("  empenhos: %d (range %s → %s)",
             len(em), em["data"].min().date(), em["data"].max().date())

    # Parse autor: "id - NOME"
    parts = em["autor"].astype(str).str.split(" - ", n=1, regex=False, expand=True)
    em["autor_id_legado"] = pd.to_numeric(parts[0], errors="coerce")
    em["autor_nome"] = parts[1].fillna(em["autor"]).str.strip().str.upper()

    # Filter parliamentary authors
    bad_words = "COMISSAO|COM\\.|BANCADA|Sem"
    em = em[~em["autor_nome"].str.contains(bad_words, na=False)]
    em = em[~em["autor_nome"].isin(["RELATOR GERAL", "C", "CFT", "CLP"])]

    log.info("  parliamentary empenhos: %d", len(em))

    # --- (A) Ministry execution speed ---------------------------------------
    # For each (UO, year), compute mean days from start-of-year to empenho.
    # UOs with high mean = "slow execution" UOs.
    log.info("\n[A] Ministry execution speed by (UO, year)")
    em["dia_no_ano"] = em["data"].dt.dayofyear
    uo_speed = em.groupby(["codigoUo", "ano"]).agg(
        n=("valor", "size"),
        mean_dia=("dia_no_ano", "mean"),
        valor_total=("valor", "sum"),
    ).reset_index()
    uo_speed["uo_slowness"] = uo_speed["mean_dia"]  # higher = slower
    log.info("  %d (UO, ano) cells; UO slowness range %d to %d days",
             len(uo_speed),
             int(uo_speed["mean_dia"].min()),
             int(uo_speed["mean_dia"].max()))

    # Per (autor, ano): weighted mean UO slowness
    em = em.merge(uo_speed[["codigoUo", "ano", "uo_slowness"]],
                    on=["codigoUo", "ano"], how="left")
    em["w_slow"] = em["valor"] * em["uo_slowness"]
    iv_a = em.groupby(["autor_id_legado", "autor_nome", "ano"]).agg(
        sum_valor=("valor", "sum"),
        sum_w_slow=("w_slow", "sum"),
    ).reset_index()
    iv_a["iv_uo_slowness_pondv"] = iv_a["sum_w_slow"] / iv_a["sum_valor"].replace(0, np.nan)
    iv_a = iv_a.dropna(subset=["iv_uo_slowness_pondv"])
    iv_a = iv_a[["autor_id_legado", "autor_nome", "ano", "iv_uo_slowness_pondv"]]
    log.info("  iv_uo_slowness_pondv: %d (deputy, year) cells",
             len(iv_a))

    # --- (B) Disaster/emergency function share ------------------------------
    log.info("\n[B] Disaster function share (Saúde + Defesa Civil)")
    em["funcao_str"] = em["funcao"].astype(str).str.upper()
    em["d_disaster"] = em["funcao_str"].str.contains(
        "SAUDE|SA?[ÚU]DE|DEFESA CIVIL|ASSIST", regex=True, na=False
    ).astype(int)
    iv_b = em.groupby(["autor_id_legado", "autor_nome", "ano"]).agg(
        sum_valor=("valor", "sum"),
        sum_disaster=("d_disaster", lambda s: (em.loc[s.index, "valor"] * s).sum()),
    ).reset_index()
    iv_b["iv_disaster_share"] = iv_b["sum_disaster"] / iv_b["sum_valor"].replace(0, np.nan)
    iv_b = iv_b[["autor_id_legado", "autor_nome", "ano", "iv_disaster_share"]]
    log.info("  iv_disaster_share: %d (deputy, year) cells; mean=%.3f",
             len(iv_b), iv_b["iv_disaster_share"].mean())

    # Combine
    iv_alt = iv_a.merge(iv_b, on=["autor_id_legado", "autor_nome", "ano"],
                            how="outer")
    out_path = C.PANEL / "iv_alternative.csv"
    iv_alt.to_csv(out_path, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out_path, len(iv_alt))

    # --- Match to deputy IDs (so we can join with panel) ----------------------
    log.info("\nMatching autor names to idDeputado")
    dep_info = pd.read_csv(C.INTERIM / "dep_info.csv", sep=";", low_memory=False,
                              usecols=["id", "nomeEleitoral"])
    from unidecode import unidecode
    dep_info["nome_norm"] = (dep_info["nomeEleitoral"].astype(str)
                                  .str.upper().str.strip().apply(unidecode))
    dep_info = dep_info.drop_duplicates("nome_norm", keep="last")
    iv_alt["nome_norm"] = (iv_alt["autor_nome"].astype(str)
                                .str.upper().str.strip().apply(unidecode))
    iv_alt = iv_alt.merge(dep_info[["id", "nome_norm"]], on="nome_norm",
                              how="left")
    iv_alt = iv_alt.rename(columns={"id": "idDeputado"})
    iv_alt = iv_alt.dropna(subset=["idDeputado"])
    iv_alt["idDeputado"] = iv_alt["idDeputado"].astype(int)
    log.info("  matched %d / %d", len(iv_alt), len(iv_a))

    iv_alt_named = iv_alt[["idDeputado", "ano",
                                "iv_uo_slowness_pondv", "iv_disaster_share"]] \
                          .drop_duplicates(["idDeputado", "ano"])
    out2 = C.PANEL / "iv_alternative_dep.csv"
    iv_alt_named.to_csv(out2, sep=";", index=False)
    log.info("✓ saved %s (%d deputy×year)", out2, len(iv_alt_named))

    # --- Correlation diagnostics --------------------------------------------
    log.info("\n[CORRS] Loading panel to test correlations")
    df = U.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["ano"] = pd.to_datetime(df["data"]).dt.year
    df = df.merge(iv_alt_named, on=["idDeputado", "ano"], how="left")

    new_ivs = ["iv_uo_slowness_pondv", "iv_disaster_share"]
    existing_ivs = ["iv_q4_no_ytd", "iv_ytd_exec_pct",
                       "iv_fiscal_q4", "iv_fiscal_pressure"]
    rows = []
    for col in new_ivs:
        if col not in df.columns: continue
        sub = df.dropna(subset=[col])
        if len(sub) < 1000: continue
        rT = sub[[col, C.TREATMENT]].corr().iloc[0, 1]
        rY = sub[[col, C.TARGET]].corr().iloc[0, 1]
        for old in existing_ivs:
            if old not in sub.columns: continue
            r_old = sub[[col, old]].corr().iloc[0, 1]
            rows.append({
                "iv_new": col,
                "iv_existing": old,
                "corr_with_existing": round(r_old, 4),
                "corr_with_T": round(rT, 4),
                "corr_with_Y": round(rY, 4),
                "n_obs": len(sub),
            })

    if rows:
        df_c = pd.DataFrame(rows)
        df_c.to_csv(C.RESULTS / "tier2_alt_ivs_correlations.csv",
                      sep=";", index=False)
        log.info("\n%s", df_c.to_string(index=False))


if __name__ == "__main__":
    main()
