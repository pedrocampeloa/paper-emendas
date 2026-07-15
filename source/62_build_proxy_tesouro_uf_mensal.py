"""
62_build_proxy_tesouro_uf_mensal.py
------------------------------------
PROXY 3: Volume Tesouro mensal por UF do deputado.

Dados: Tesouro CKAN tem 388k pagamentos mensais (mun x mes x emenda x CNPJ favorecido).
Para cada UF-mes-ano, agregar:
  - vl_total: soma de Valor
  - vl_individual: soma de "Emenda Individual"
  - vl_bancada: soma de "Emenda de Bancada"
  - vl_pix: soma com Transferencia Especial=Sim

Depois propaga para deputado×mes-ano via UF do deputado (siglaUf no painel).

Hipotese: deputados de UFs com mais volume de pork (no agregado) sao recipientes
indiretos do pork "geral" da UF.

Output:
  dados/interim/panel/panel_proxy_tesouro_uf_mensal.csv (siglaUf, ano, mes, vl_*)
  results/eda_proxy_tesouro_uf_mensal.csv
"""

import logging
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "dados" / "raw" / "orcamento" / "tesouro" / "emendas-parlamentares-individuais-e-de-bancada"
PANEL = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("tesuf")


def main():
    log.info("PROXY 3: Volume Tesouro mensal por UF")

    log.info("[1] Loading Tesouro emendas mensal (CSV 68MB, 388k linhas)")
    df = pd.read_csv(RAW / "emendas-parlamentares.csv", sep=";", encoding="latin-1",
                     dtype=str, low_memory=False)
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce")
    df = df.dropna(subset=["UF", "Ano", "Mês", "Valor"])
    log.info(f"    {len(df):,} linhas")

    log.info("[2] Agregando por UF × ano × mes")
    df["is_individual"] = (df["Nome Emenda"] == "Emenda Individual").astype(int)
    df["is_bancada"] = (df["Nome Emenda"] == "Emenda de Bancada").astype(int)
    df["is_pix"] = (df["Transferência Especial"] == "Sim").astype(int)

    # Pre-multiplicar para depois somar
    df["vl_individual"] = df["Valor"] * df["is_individual"]
    df["vl_bancada"] = df["Valor"] * df["is_bancada"]
    df["vl_pix"] = df["Valor"] * df["is_pix"]

    by_uf_mo = df.groupby(["UF", "Ano", "Mês"]).agg(
        vl_total=("Valor", "sum"),
        vl_individual=("vl_individual", "sum"),
        vl_bancada=("vl_bancada", "sum"),
        vl_pix=("vl_pix", "sum"),
        n_pagamentos=("Valor", "count"),
    ).reset_index()
    by_uf_mo["Ano"] = by_uf_mo["Ano"].astype(int)
    by_uf_mo = by_uf_mo.rename(columns={"UF": "siglaUf", "Ano": "ano", "Mês": "mes"})

    # Mes em portugues -> int
    meses_map = {"janeiro":1, "fevereiro":2, "março":3, "abril":4, "maio":5, "junho":6,
                 "julho":7, "agosto":8, "setembro":9, "outubro":10, "novembro":11, "dezembro":12}
    by_uf_mo["mes_num"] = by_uf_mo["mes"].str.lower().map(meses_map)

    log.info(f"    {len(by_uf_mo):,} cells (UF, ano, mes)")
    log.info(f"    UFs: {by_uf_mo['siglaUf'].nunique()}")
    log.info(f"    Anos: {sorted(by_uf_mo['ano'].unique())}")

    log.info("[3] Descritivas")
    desc = by_uf_mo.groupby("ano").agg(
        n_uf_mo=("siglaUf", "count"),
        vl_total_bi=("vl_total", lambda x: x.sum() / 1e9),
        vl_pix_bi=("vl_pix", lambda x: x.sum() / 1e9),
    ).reset_index()
    print(desc.to_string(index=False))

    out_path = PANEL / "panel_proxy_tesouro_uf_mensal.csv"
    by_uf_mo.to_csv(out_path, sep=";", index=False)
    log.info(f"\n  saved {out_path}")
    desc.to_csv(RESULTS / "eda_proxy_tesouro_uf_mensal.csv", sep=";", index=False)


if __name__ == "__main__":
    main()
