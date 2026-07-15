"""
64_build_proxy_share_emendas_total.py
--------------------------------------
PROXY 5: % de emendas / orçamento total (Tesouro despesas anuais).

Dados: dados/raw/orcamento/tesouro/despesas-e-transferencias-totais/base-despesas-YYYY.xlsx
  Sheet por ano contem 131k+ linhas de despesa por orgao/funcao/programa/acao.
  Campos: DESPESAS_EMPENHADAS, DESPESAS_LIQUIDADAS, DESPESAS_PAGAS, DOTACAO_INICIAL,
          DOTACAO_ATUALIZADA, PAGAMENTOS_TOTAIS.

Estrategia:
  1. Para cada ano (2008-2019), somar DOTACAO_INICIAL e DESPESAS_PAGAS totais.
  2. Identificar acoes/programas que sao emendas (PT 0001-9999 -> emendas individuais;
     0002, 0003 -> bancada/relator).
  3. Calcular share_emendas_dotacao = vl_emendas / vl_total_orcamento.
  4. Cruzar com vol de emendas por ano (do painel emendas) para ter
     share_individual / share_bancada etc.

Granularidade: ANO (uma linha por ano).

Output:
  dados/interim/panel/panel_proxy_share_emendas_total.csv (ano, vl_total_orc, vl_emendas,
                                                            share_emendas, share_individual, share_bancada)
  results/eda_proxy_share_emendas_total.csv
"""

import logging
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW_TES = REPO / "dados" / "raw" / "orcamento" / "tesouro" / "despesas-e-transferencias-totais"
RAW_EMD = REPO / "dados" / "raw" / "orcamento" / "tesouro" / "emendas-parlamentares-individuais-e-de-bancada"
PANEL = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("share")


def main():
    log.info("PROXY 5: share de emendas / orcamento total")

    log.info("[1] Loading despesas anuais Tesouro (2008-2019)")
    files = sorted(RAW_TES.glob("base-despesas-*.xlsx"))
    log.info(f"    {len(files)} anos disponiveis")

    rows = []
    for fp in files:
        ano = int(fp.stem.split("-")[-1])
        try:
            df = pd.read_excel(fp, sheet_name=str(ano))
        except Exception as e:
            log.warning(f"    {ano} falhou: {e}")
            continue
        # Total geral do orcamento federal
        vl_dotacao_inicial = pd.to_numeric(df["DOTACAO_INICIAL"], errors="coerce").sum()
        vl_dotacao_atualizada = pd.to_numeric(df["DOTACAO_ATUALIZADA"], errors="coerce").sum()
        vl_empenhado = pd.to_numeric(df["DESPESAS_EMPENHADAS"], errors="coerce").sum()
        vl_pago = pd.to_numeric(df["DESPESAS_PAGAS"], errors="coerce").sum()
        vl_pago_total = pd.to_numeric(df["PAGAMENTOS_TOTAIS"], errors="coerce").sum()

        rows.append({
            "ano": ano,
            "vl_dotacao_inicial": vl_dotacao_inicial,
            "vl_dotacao_atualizada": vl_dotacao_atualizada,
            "vl_empenhado_total": vl_empenhado,
            "vl_pago_total": vl_pago,
            "vl_pagamentos_totais": vl_pago_total,
        })
        log.info(f"    {ano}: empenhado R${vl_empenhado/1e9:.1f}bi, pago R${vl_pago/1e9:.1f}bi")

    desp = pd.DataFrame(rows)
    log.info(f"    {len(desp)} anos")

    log.info("[2] Loading emendas individuais Tesouro (volume anual)")
    em = pd.read_csv(RAW_EMD / "emendas-parlamentares.csv", sep=";", encoding="latin-1",
                     dtype=str, low_memory=False)
    em["Valor"] = pd.to_numeric(em["Valor"], errors="coerce")
    em["Ano"] = pd.to_numeric(em["Ano"], errors="coerce")
    em = em.dropna(subset=["Valor", "Ano"])

    em["is_individual"] = (em["Nome Emenda"] == "Emenda Individual").astype(int)
    em["is_bancada"] = (em["Nome Emenda"] == "Emenda de Bancada").astype(int)
    em["is_relator"] = (em["Nome Emenda"].str.contains("Relator", case=False, na=False)).astype(int)
    em["is_comissao"] = (em["Nome Emenda"].str.contains("Comiss", case=False, na=False)).astype(int)
    em["is_pix"] = (em["Transferência Especial"] == "Sim").astype(int)

    by_ano = em.groupby("Ano").agg(
        vl_emendas_total=("Valor", "sum"),
        vl_individual=("Valor", lambda x: x[em.loc[x.index, "is_individual"] == 1].sum()),
        vl_bancada=("Valor", lambda x: x[em.loc[x.index, "is_bancada"] == 1].sum()),
        vl_relator=("Valor", lambda x: x[em.loc[x.index, "is_relator"] == 1].sum()),
        vl_comissao=("Valor", lambda x: x[em.loc[x.index, "is_comissao"] == 1].sum()),
        vl_pix=("Valor", lambda x: x[em.loc[x.index, "is_pix"] == 1].sum()),
    ).reset_index().rename(columns={"Ano": "ano"})
    by_ano["ano"] = by_ano["ano"].astype(int)
    log.info(f"    {len(by_ano)} anos com emendas (range {by_ano['ano'].min()}-{by_ano['ano'].max()})")

    log.info("[3] Merge despesa total x emendas")
    out = desp.merge(by_ano, on="ano", how="left")
    out["share_emendas_empenhado"] = out["vl_emendas_total"] / out["vl_empenhado_total"]
    out["share_individual"] = out["vl_individual"] / out["vl_empenhado_total"]
    out["share_bancada"] = out["vl_bancada"] / out["vl_empenhado_total"]
    out["share_relator"] = out["vl_relator"] / out["vl_empenhado_total"]
    out["share_pix"] = out["vl_pix"] / out["vl_empenhado_total"]

    log.info("\n  Resumo:")
    print(out[["ano", "vl_empenhado_total", "vl_emendas_total", "share_emendas_empenhado",
                "share_individual", "share_bancada", "share_relator", "share_pix"]].to_string(index=False))

    out.to_csv(PANEL / "panel_proxy_share_emendas_total.csv", sep=";", index=False)
    log.info(f"\n  saved {PANEL / 'panel_proxy_share_emendas_total.csv'}")

    out.to_csv(RESULTS / "eda_proxy_share_emendas_total.csv", sep=";", index=False)


if __name__ == "__main__":
    main()
