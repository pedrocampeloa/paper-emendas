"""
61_build_proxy_conv_status.py
------------------------------
PROXY 2: Status do convenio por deputado-ano.

Categorizar SIT_CONVENIO em 4 buckets:
  - 'concluido': prestacao aprovada / aprovada com ressalvas / em complementacao
  - 'em_execucao': em execucao / proposta aprovada / aguardando prestacao
  - 'problema': cancelado / anulado / rescindido / rejeitada
  - 'em_analise': prestacao em analise / enviada para analise

Para cada deputado-ano, calcular:
  - n_convenios
  - pct_concluido, pct_em_execucao, pct_problema, pct_em_analise
  - vl_concluido / vl_total

Hipotese: pork de qualidade (concluido) vs pork problematico (cancelado).
Deputados leais devem ter mais conv concluidos; oposicao mais cancelados.

Output:
  dados/interim/panel/panel_proxy_conv_status.csv
  results/eda_proxy_conv_status.csv
"""

import logging
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "dados" / "raw" / "orcamento" / "transferegov_bulk"
PANEL = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("convstatus")


def norm_name(s):
    import unicodedata
    if not isinstance(s, str): return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(s.upper().strip().split())


def categorize_status(s):
    if not isinstance(s, str):
        return "outro"
    s = s.lower()
    if any(k in s for k in ["concluida", "aprovada", "comprovada", "complementacao"]):
        return "concluido"
    if any(k in s for k in ["execucao", "aguardando", "aprovado"]):
        return "em_execucao"
    if any(k in s for k in ["cancelado", "anulado", "rescindido", "rejeitada"]):
        return "problema"
    if "analise" in s:
        return "em_analise"
    return "outro"


def main():
    log.info("PROXY 2: Status do convenio por deputado-ano")

    log.info("[1] Loading SICONV emenda")
    em = pd.read_csv(RAW / "siconv_emenda.csv", sep=";", encoding="utf-8",
                     dtype=str, low_memory=False)
    em.columns = [c.replace("﻿", "") for c in em.columns]
    em = em[em["NOME_PARLAMENTAR"].notna()]
    em = em[em["NOME_PARLAMENTAR"].str.upper().str.strip() != "RELATOR GERAL"]
    em["nome_norm"] = em["NOME_PARLAMENTAR"].apply(norm_name)
    em = em[em["nome_norm"] != ""]
    em = em[["ID_PROPOSTA", "nome_norm"]].drop_duplicates()
    log.info(f"    {len(em):,} pares")

    log.info("[2] Loading SICONV convenio + categorize status")
    conv = pd.read_csv(RAW / "siconv_convenio.csv", sep=";", encoding="utf-8",
                       dtype=str, low_memory=False,
                       usecols=["NR_CONVENIO", "ID_PROPOSTA", "DIA_ASSIN_CONV",
                                "VL_GLOBAL_CONV", "SIT_CONVENIO"])
    conv["VL_GLOBAL_CONV"] = pd.to_numeric(conv["VL_GLOBAL_CONV"], errors="coerce")
    conv["data_assinatura"] = pd.to_datetime(conv["DIA_ASSIN_CONV"],
                                                format="%d/%m/%Y", errors="coerce")
    conv["ano"] = conv["data_assinatura"].dt.year
    conv["status_cat"] = conv["SIT_CONVENIO"].apply(categorize_status)

    log.info(f"    Categorias: {conv['status_cat'].value_counts().to_dict()}")

    log.info("[3] Join emenda x convenio")
    cv = em.merge(conv, on="ID_PROPOSTA", how="inner")
    cv = cv.dropna(subset=["ano"])
    cv["ano"] = cv["ano"].astype(int)
    log.info(f"    {len(cv):,} pares")

    log.info("[4] Agregando por deputado-ano")
    # Counts por categoria
    out = cv.groupby(["nome_norm", "ano", "status_cat"]).size().unstack(fill_value=0)
    for cat in ["concluido", "em_execucao", "problema", "em_analise"]:
        if cat not in out.columns:
            out[cat] = 0
    out["n_total"] = out.sum(axis=1)
    out["pct_concluido"] = out["concluido"] / out["n_total"]
    out["pct_em_execucao"] = out["em_execucao"] / out["n_total"]
    out["pct_problema"] = out["problema"] / out["n_total"]
    out["pct_em_analise"] = out["em_analise"] / out["n_total"]
    out = out.reset_index()
    out.columns.name = None

    # Valores por categoria
    vl = cv.dropna(subset=["VL_GLOBAL_CONV"]).pivot_table(
        index=["nome_norm", "ano"], columns="status_cat",
        values="VL_GLOBAL_CONV", aggfunc="sum", fill_value=0
    ).reset_index()
    for cat in ["concluido", "em_execucao", "problema", "em_analise"]:
        if cat in vl.columns:
            vl = vl.rename(columns={cat: f"vl_{cat}"})
    out = out.merge(vl, on=["nome_norm", "ano"], how="left")

    log.info(f"    {len(out):,} (deputado, ano) cells")
    log.info(f"\n  Descritivas por ano:")
    desc = out.groupby("ano").agg(
        n_deputados=("nome_norm", "nunique"),
        n_conv=("n_total", "sum"),
        pct_concluido=("pct_concluido", "mean"),
        pct_problema=("pct_problema", "mean"),
    ).reset_index()
    print(desc.to_string(index=False))

    out_path = PANEL / "panel_proxy_conv_status.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"\n  saved {out_path}")

    desc.to_csv(RESULTS / "eda_proxy_conv_status.csv", sep=";", index=False)


if __name__ == "__main__":
    main()
