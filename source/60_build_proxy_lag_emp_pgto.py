"""
60_build_proxy_lag_emp_pgto.py
-------------------------------
PROXY 1: Lag empenho -> pagamento por deputado-ano.

Cadeia de joins:
  siconv_emenda (parlamentar + ID_PROPOSTA)
    -> siconv_convenio (ID_PROPOSTA -> NR_CONVENIO)
      -> siconv_empenho (NR_CONVENIO + DATA_EMISSAO + VALOR_EMPENHO)
      -> siconv_pagamento (NR_CONVENIO + DATA_PAG + VL_PAGO)

Calcula por deputado-ano:
  - lag_medio_dias: media de (DATA_PAG - DATA_EMPENHO) ponderada por valor
  - lag_mediano_dias: mediana
  - pct_pago_ate_q4: % do empenhado pago ate 31/dez do mesmo ano
  - pct_pago_total: % do empenhado pago em qualquer momento ate hoje

Hipotese: pagamento rapido = pork "ativo" / pagamento lento = pork "represado"
(possivel dimensao punitiva).

Output:
  dados/interim/panel/panel_proxy_lag_emp_pgto.csv (idDeputado, ano, lag_*, pct_pago_*)
  results/eda_proxy_lag_emp_pgto.csv (descritivas)
"""

import sys
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
log = logging.getLogger("lag")


def norm_name(s):
    import unicodedata
    if not isinstance(s, str): return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(s.upper().strip().split())


def main():
    log.info("="*70)
    log.info("PROXY 1: Lag empenho->pagamento por deputado-ano")
    log.info("="*70)

    log.info("[1] Loading SICONV emenda (parlamentar + ID_PROPOSTA)")
    em = pd.read_csv(RAW / "siconv_emenda.csv", sep=";", encoding="utf-8",
                     dtype=str, low_memory=False)
    em.columns = [c.replace("﻿", "") for c in em.columns]
    em = em[em["NOME_PARLAMENTAR"].notna()]
    em = em[em["NOME_PARLAMENTAR"].str.upper().str.strip() != "RELATOR GERAL"]
    em["nome_norm"] = em["NOME_PARLAMENTAR"].apply(norm_name)
    em = em[em["nome_norm"] != ""]
    em = em[["ID_PROPOSTA", "nome_norm", "TIPO_PARLAMENTAR"]].drop_duplicates(
        subset=["ID_PROPOSTA", "nome_norm"])
    log.info(f"    {len(em):,} (proposta, parlamentar) pares")

    log.info("[2] Loading SICONV convenio (NR_CONVENIO <-> ID_PROPOSTA + datas)")
    conv = pd.read_csv(RAW / "siconv_convenio.csv", sep=";", encoding="utf-8",
                       dtype=str, low_memory=False,
                       usecols=["NR_CONVENIO", "ID_PROPOSTA", "DIA_ASSIN_CONV",
                                "VL_EMPENHADO_CONV", "VL_DESEMBOLSADO_CONV",
                                "SIT_CONVENIO"])
    conv["VL_EMPENHADO_CONV"] = pd.to_numeric(conv["VL_EMPENHADO_CONV"], errors="coerce")
    conv["VL_DESEMBOLSADO_CONV"] = pd.to_numeric(conv["VL_DESEMBOLSADO_CONV"], errors="coerce")
    conv["data_assinatura"] = pd.to_datetime(conv["DIA_ASSIN_CONV"],
                                                format="%d/%m/%Y", errors="coerce")
    conv = conv.dropna(subset=["NR_CONVENIO", "ID_PROPOSTA"])
    log.info(f"    {len(conv):,} convenios")

    log.info("[3] Join emenda x convenio (linka parlamentar a NR_CONVENIO)")
    em_conv = em.merge(conv, on="ID_PROPOSTA", how="inner")
    log.info(f"    {len(em_conv):,} pares (parlamentar, convenio)")

    log.info("[4] Loading SICONV empenho")
    emp = pd.read_csv(RAW / "siconv_empenho.csv", sep=";", encoding="utf-8",
                      dtype=str, low_memory=False,
                      usecols=["NR_CONVENIO", "DATA_EMISSAO", "VALOR_EMPENHO"])
    emp["VALOR_EMPENHO"] = pd.to_numeric(emp["VALOR_EMPENHO"], errors="coerce")
    emp["data_empenho"] = pd.to_datetime(emp["DATA_EMISSAO"],
                                            format="%d/%m/%Y", errors="coerce")
    emp = emp.dropna(subset=["NR_CONVENIO", "data_empenho", "VALOR_EMPENHO"])
    log.info(f"    {len(emp):,} empenhos")

    log.info("[5] Loading SICONV pagamento (1 GB — pode demorar)")
    pgto = pd.read_csv(RAW / "siconv_pagamento.csv", sep=";", encoding="utf-8",
                       dtype=str, low_memory=False,
                       usecols=["NR_CONVENIO", "DATA_PAG", "VL_PAGO"])
    pgto["VL_PAGO"] = pd.to_numeric(pgto["VL_PAGO"], errors="coerce")
    pgto["data_pgto"] = pd.to_datetime(pgto["DATA_PAG"],
                                          format="%d/%m/%Y", errors="coerce")
    pgto = pgto.dropna(subset=["NR_CONVENIO", "data_pgto", "VL_PAGO"])
    log.info(f"    {len(pgto):,} pagamentos")

    # Agregar pagamentos por convenio: total pago + data primeiro/ultimo pagto
    log.info("[6] Agregando pagamentos por convenio")
    pgto_agg = pgto.groupby("NR_CONVENIO").agg(
        data_primeiro_pgto=("data_pgto", "min"),
        data_ultimo_pgto=("data_pgto", "max"),
        vl_pago_total=("VL_PAGO", "sum"),
        n_pagamentos=("VL_PAGO", "count")
    ).reset_index()

    # Por empenho: data + valor. Vamos agregar empenhos por convenio também
    log.info("[7] Agregando empenhos por convenio")
    emp_agg = emp.groupby("NR_CONVENIO").agg(
        data_primeiro_empenho=("data_empenho", "min"),
        data_ultimo_empenho=("data_empenho", "max"),
        vl_empenhado_total=("VALOR_EMPENHO", "sum"),
        n_empenhos=("VALOR_EMPENHO", "count")
    ).reset_index()

    log.info("[8] Merge: convenio + empenho + pagamento")
    cv = em_conv.merge(emp_agg, on="NR_CONVENIO", how="left")
    cv = cv.merge(pgto_agg, on="NR_CONVENIO", how="left")

    # Lag dias = data_primeiro_pgto - data_primeiro_empenho (positivo: pgto depois)
    cv["lag_emp_pgto_dias"] = (cv["data_primeiro_pgto"] - cv["data_primeiro_empenho"]).dt.days
    cv["lag_emp_pgto_dias"] = cv["lag_emp_pgto_dias"].where(cv["lag_emp_pgto_dias"] >= 0)

    # % executado = pago / empenhado
    cv["pct_executado"] = cv["vl_pago_total"] / cv["vl_empenhado_total"]
    cv["pct_executado"] = cv["pct_executado"].clip(0, 1.5)  # cap em 1.5 para outliers

    # Ano do convenio = ano do primeiro empenho
    cv["ano"] = cv["data_primeiro_empenho"].dt.year

    log.info(f"    {len(cv):,} (parlamentar, convenio) com dados de execucao")
    log.info(f"    com lag valido: {cv['lag_emp_pgto_dias'].notna().sum():,}")

    log.info("[9] Agregando por deputado-ano")
    out = cv.dropna(subset=["ano"]).groupby(["nome_norm", "ano"]).agg(
        n_convenios=("NR_CONVENIO", "count"),
        n_empenhos_total=("n_empenhos", "sum"),
        vl_empenhado_total=("vl_empenhado_total", "sum"),
        vl_pago_total=("vl_pago_total", "sum"),
        lag_medio_dias=("lag_emp_pgto_dias", "mean"),
        lag_mediano_dias=("lag_emp_pgto_dias", "median"),
        pct_executado_medio=("pct_executado", "mean"),
    ).reset_index()
    out["ano"] = out["ano"].astype(int)

    log.info(f"    {len(out):,} (deputado, ano) cells")
    log.info(f"    Por ano:")
    log.info(out.groupby("ano")["n_convenios"].sum().to_string())

    log.info("\n[10] Descritivas")
    log.info(f"  lag_medio_dias: media={out['lag_medio_dias'].mean():.1f}, "
             f"mediana={out['lag_medio_dias'].median():.1f}")
    log.info(f"  pct_executado_medio: media={out['pct_executado_medio'].mean():.4f}")

    # Salvar
    out_path = PANEL / "panel_proxy_lag_emp_pgto.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"\n  saved {out_path}")

    eda = out.groupby("ano").agg(
        n_deputados=("nome_norm", "nunique"),
        n_convenios=("n_convenios", "sum"),
        lag_medio_dias=("lag_medio_dias", "mean"),
        lag_mediano_dias=("lag_mediano_dias", "mean"),
        pct_exec_medio=("pct_executado_medio", "mean"),
    ).reset_index()
    eda.to_csv(RESULTS / "eda_proxy_lag_emp_pgto.csv", sep=";", index=False)
    print(eda.to_string(index=False))


if __name__ == "__main__":
    main()
