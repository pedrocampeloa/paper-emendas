"""
33_build_multi_rp_panel.py
---------------------------
Constroi painel deputado x votacao com valores das emendas separados por
modalidade (RP-6, RP-6 Pix, RP-7, RP-8, RP-9, RP-9 imputed), em vez do
agregado emenda_valor unico.

Fontes:
    - Portal Transparencia bulk (EmendasParlamentares.csv): RP-6/7/8/9 com
      autor, ano, valores empenhado e pago. Para RP-9 o autor sera
      'Relator Geral', sem identificacao individual.
    - SICONV emenda (siconv_emenda.csv): mapping deputado -> emenda
      individual / bancada / comissao com ID_PROPOSTA + nome.
    - SICONV convenio (siconv_convenio.csv): ID_PROPOSTA -> ANO de assinatura
      (para obter o ano da emenda).
    - SICONV apoiadores (apoiadores_emendas_programas.csv): mapping deputado ->
      RP-8 via PARLAMENTAR_SOLICITANTE (43% de cobertura para RP-8) e
      tambem mapping minimo para RP-9 (137 linhas com solicitante identificado).

Estrategia de matching:
    - Normalizacao de nome (NFKD, upper, sem acentos, sem espacos extras).
    - Match nome do painel <-> nome do parlamentar nas fontes.
    - Distribuicao anual proporcional (60/365) sobre janela 60d pre-voto.
      Esta e' uma proxy que assume distribuicao uniforme da emenda no
      calendario; a janela exata exige granularidade mensal/diaria, que
      o painel anual nao suporta.

Outputs:
    dados/interim/panel/panel_emendas_pre_multi_rp.csv
    paper-emendas/results/eda_multi_rp_coverage.csv
"""

import sys
import unicodedata
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "dados" / "raw" / "orcamento"
INTERIM = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def norm_name(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    s = s.upper().strip()
    s = " ".join(s.split())
    return s


def load_panel():
    print("\n[1] Loading panel_features.csv")
    df = pd.read_csv(INTERIM / "panel_features.csv", sep=";", dtype={"idDeputado": str},
                     usecols=["idDeputado", "nome", "data", "idVotacao", "idLegislatura"],
                     low_memory=False)
    df["data"] = pd.to_datetime(df["data"])
    df["nome_norm"] = df["nome"].apply(norm_name)
    print(f"    {len(df):,} rows, {df['idDeputado'].nunique()} deputies, "
          f"{df['nome_norm'].nunique()} unique norm names")
    return df


def load_portal_transparencia():
    """Bulk Portal Transparencia: RP-6/7/8/9 (mas RP-9 = Relator Geral, ignorado)."""
    print("\n[2] Loading Portal Transparencia bulk (UTF-8, but file uses cp1252 declared in header)")
    fp = RAW / "portal_transparencia" / "EmendasParlamentares.csv"
    # Arquivo tem header em utf-8 mas conteudo em cp1252
    df = pd.read_csv(fp, sep=";", encoding="cp1252", dtype=str, low_memory=False)
    rp_map = {
        "Emenda Individual - Transferências com Finalidade Definida": "RP6",
        "Emenda Individual - Transferências Especiais": "RP6_Pix",
        "Emenda de Bancada": "RP7",
        "Emenda de Comissão": "RP8",
        "Emenda de Relator": "RP9",
    }
    df["RP"] = df["Tipo de Emenda"].map(rp_map)
    df["nome_norm"] = df["Nome do Autor da Emenda"].apply(norm_name)
    df = df[~df["nome_norm"].isin(["", "SEM INFORMACAO", "RELATOR GERAL"])]
    df["ano"] = pd.to_numeric(df["Ano da Emenda"], errors="coerce").astype("Int64")
    df["valor"] = (df["Valor Empenhado"].fillna("0").str.replace(",", ".").astype(float))
    df = df.dropna(subset=["RP", "ano"])
    print(f"    {len(df):,} rows with identified author")
    print(f"    RP breakdown: {df['RP'].value_counts().to_dict()}")
    return df[["nome_norm", "ano", "RP", "valor"]]


def load_siconv_emenda_with_year():
    """SICONV emenda + convenio: deputado, ano (de DIA_ASSIN_CONV), RP, valor."""
    print("\n[3] Loading SICONV emenda + convenio (for year lookup)")
    em = pd.read_csv(RAW / "transferegov_bulk" / "siconv_emenda.csv",
                     sep=";", encoding="utf-8", dtype=str, low_memory=False)
    em.columns = [c.replace("﻿", "") for c in em.columns]
    em["VALOR_REPASSE_EMENDA"] = pd.to_numeric(em["VALOR_REPASSE_EMENDA"], errors="coerce")
    em = em[em["NOME_PARLAMENTAR"].notna()]
    em = em[em["NOME_PARLAMENTAR"].str.upper().str.strip() != "RELATOR GERAL"]
    em["nome_norm"] = em["NOME_PARLAMENTAR"].apply(norm_name)
    em = em[em["nome_norm"] != ""]
    rp_map = {"INDIVIDUAL": "RP6", "BANCADA": "RP7", "COMISSAO": "RP8"}
    em["RP"] = em["TIPO_PARLAMENTAR"].map(rp_map)
    em = em.dropna(subset=["RP"])

    # Lookup ano via convenio
    conv = pd.read_csv(RAW / "transferegov_bulk" / "siconv_convenio.csv",
                       sep=";", encoding="utf-8", dtype=str,
                       usecols=["ID_PROPOSTA", "ANO"], low_memory=False)
    conv["ano"] = pd.to_numeric(conv["ANO"], errors="coerce").astype("Int64")
    conv = conv.dropna(subset=["ano"]).drop_duplicates("ID_PROPOSTA")

    em = em.merge(conv, on="ID_PROPOSTA", how="left")
    n_with_ano = em["ano"].notna().sum()
    print(f"    {len(em):,} emendas, {n_with_ano:,} with year from convenio "
          f"({100*n_with_ano/len(em):.1f}%)")
    em = em.dropna(subset=["ano"])
    print(f"    RP breakdown (matched year): {em['RP'].value_counts().to_dict()}")
    return em[["nome_norm", "ano", "RP", "VALOR_REPASSE_EMENDA"]].rename(
        columns={"VALOR_REPASSE_EMENDA": "valor"}).dropna(subset=["valor"])


def load_siconv_apoiadores_with_year():
    """SICONV apoiadores: usa PARLAMENTAR_SOLICITANTE para RP-7/RP-8/RP-9.

    Para RP-7 (Bancada) e RP-8 (Comissao), NOME_PARLAMENTAR e' o coletivo;
    PARLAMENTAR_SOLICITANTE e' o deputado individual.
    Para RP-9 (Relator Geral), idem.

    O ano vem do programa via ID_PROGRAMA -> ID_PROPOSTA -> convenio.
    Para apoiadores que nao tem link claro ao convenio, atribuimos faixa de anos
    com base no padrao: RP-9 = 2020-2022; RP-8/RP-7 = ano do programa.
    """
    print("\n[4] Loading SICONV apoiadores")
    ap = pd.read_csv(RAW / "transferegov_bulk" / "apoiadores_emendas_programas.csv",
                     sep=";", encoding="utf-8", dtype=str, low_memory=False)
    ap.columns = [c.replace("﻿", "").replace("_APOIADORES_EMENDAS", "") for c in ap.columns]
    ap["valor"] = pd.to_numeric(ap["VALOR_REPASSE_PROPOSTA"], errors="coerce")

    is_com = ap["NOME_PARLAMENTAR"].str.contains("Com|COMISS", na=False, case=False, regex=True)
    is_bancada = ap["NOME_PARLAMENTAR"].str.contains("Bancada|BANCADA", na=False, case=False, regex=True)
    is_rg = ap["NOME_PARLAMENTAR"].str.upper().str.strip() == "RELATOR GERAL"

    # Bancada RP-7
    bancada = ap[is_bancada & ap["PARLAMENTAR_SOLICITANTE"].notna()].copy()
    bancada["nome_norm"] = bancada["PARLAMENTAR_SOLICITANTE"].apply(norm_name)
    bancada["RP"] = "RP7"

    # Comissao RP-8
    com = ap[is_com & ap["PARLAMENTAR_SOLICITANTE"].notna()].copy()
    com["nome_norm"] = com["PARLAMENTAR_SOLICITANTE"].apply(norm_name)
    com["RP"] = "RP8"

    # Relator Geral RP-9
    rp9 = ap[is_rg & ap["PARLAMENTAR_SOLICITANTE"].notna()].copy()
    rp9["nome_norm"] = rp9["PARLAMENTAR_SOLICITANTE"].apply(norm_name)
    rp9["RP"] = "RP9_imputed"

    out = pd.concat([bancada, com, rp9], ignore_index=True)
    out = out[out["nome_norm"] != ""]
    out = out.dropna(subset=["valor"])

    # Lookup ano via ID_PROGRAMA -> programa (siconv_programa nao tem ANO direto,
    # mas o ID_CNPJ_PROGRAMA_EMENDA cresce com o tempo). Usar mapping aproximado:
    # NUMERO_EMENDA = primeiros 2 digitos = ano fiscal (eg "60040004" -> ?)
    # Verificamos amostralmente: 70000xx, 80000xx etc -> usa ID_PROGRAMA para ano.
    #
    # Atalho mais simples: usar siconv_programa para mapear ID_PROGRAMA -> ano
    prog = pd.read_csv(RAW / "transferegov_bulk" / "siconv_programa.csv",
                       sep=";", encoding="utf-8", dtype=str,
                       usecols=["ID_PROGRAMA", "ANO_DISPONIBILIZACAO"],
                       low_memory=False)
    prog["ano"] = pd.to_numeric(prog["ANO_DISPONIBILIZACAO"],
                                  errors="coerce").astype("Int64")
    prog = prog.dropna(subset=["ano"]).drop_duplicates("ID_PROGRAMA")
    out = out.merge(prog[["ID_PROGRAMA", "ano"]], on="ID_PROGRAMA", how="left")

    print(f"    Apoiadores breakdown:")
    print(f"      Bancada (RP7): {len(bancada):,}, with ano: {bancada.merge(prog, on='ID_PROGRAMA')['ano'].notna().sum():,}")
    print(f"      Comissao (RP8): {len(com):,}, with ano: {com.merge(prog, on='ID_PROGRAMA')['ano'].notna().sum():,}")
    print(f"      Relator Geral (RP9_imputed): {len(rp9):,}")

    # Para RP-9 imputed: fallback ano=2021 (mediana 2020-2022) onde nao temos
    out.loc[(out["RP"] == "RP9_imputed") & out["ano"].isna(), "ano"] = 2021

    out = out.dropna(subset=["ano"])
    out["ano"] = out["ano"].astype("Int64")
    print(f"    Total apoiadores with year: {len(out):,}")
    return out[["nome_norm", "ano", "RP", "valor"]]


def consolidate_yearly(panel_deps, sources):
    """Consolida fontes em uma tabela longa (nome_norm, ano, RP, valor_total)."""
    print("\n[5] Consolidating yearly data per (deputy, year, RP)")
    panel_names = set(panel_deps["nome_norm"].unique())
    print(f"    Panel has {len(panel_names)} unique normalized names")

    all_data = []
    for name, df in sources.items():
        matched = df[df["nome_norm"].isin(panel_names)].copy()
        matched["source"] = name
        all_data.append(matched[["nome_norm", "ano", "RP", "valor", "source"]])
        print(f"    {name}: {len(df):,} total, {len(matched):,} match panel "
              f"({100*len(matched)/max(len(df),1):.1f}%)")

    long = pd.concat(all_data, ignore_index=True)
    long["ano"] = long["ano"].astype("Int64")
    long = long.dropna(subset=["ano"])
    yearly = (long.groupby(["nome_norm", "ano", "RP"], dropna=False, observed=True)["valor"]
              .sum().reset_index())
    yearly = yearly[yearly["valor"] > 0]
    print(f"    Yearly aggregate: {len(yearly):,} (deputy, year, RP) cells")
    print(f"    RP breakdown: {yearly['RP'].value_counts().to_dict()}")
    return yearly


def build_60d_window(panel, yearly):
    """Aplica janela proxy 60/365 ao valor anual por RP, deputado, ano."""
    print("\n[6] Mapping panel deputies <-> sources")
    panel_deps_set = set(panel["nome_norm"].unique())
    sources_deps = set(yearly["nome_norm"].unique())
    inter = panel_deps_set & sources_deps
    print(f"    Panel: {len(panel_deps_set)} names; Sources: {len(sources_deps)} names")
    print(f"    Intersection: {len(inter)} ({100*len(inter)/len(panel_deps_set):.1f}% of panel)")

    print("\n[7] Pivoting yearly to (nome_norm, ano) -> RP value")
    pivot = yearly.pivot_table(
        index=["nome_norm", "ano"], columns="RP", values="valor",
        aggfunc="sum", fill_value=0).reset_index()
    for rp in ["RP6", "RP6_Pix", "RP7", "RP8", "RP9", "RP9_imputed"]:
        if rp not in pivot.columns:
            pivot[rp] = 0.0
    pivot["ano"] = pivot["ano"].astype("Int64")

    panel["ano"] = panel["data"].dt.year.astype("Int64")
    merged = panel.merge(pivot, on=["nome_norm", "ano"], how="left")
    for rp in ["RP6", "RP6_Pix", "RP7", "RP8", "RP9", "RP9_imputed"]:
        merged[rp] = merged[rp].fillna(0.0)

    PROP = 60.0 / 365.0
    for rp in ["RP6", "RP6_Pix", "RP7", "RP8", "RP9", "RP9_imputed"]:
        merged[f"T_{rp.lower()}_pre60"] = merged[rp] * PROP

    return merged[["idDeputado", "idVotacao", "data", "idLegislatura",
                   "T_rp6_pre60", "T_rp6_pix_pre60", "T_rp7_pre60",
                   "T_rp8_pre60", "T_rp9_pre60", "T_rp9_imputed_pre60"]]


def save_outputs(merged):
    print("\n[8] Saving outputs")
    out_path = INTERIM / "panel_emendas_pre_multi_rp.csv"
    merged.to_csv(out_path, sep=";", index=False)
    print(f"    {out_path}: {len(merged):,} rows")

    rows = []
    for leg in [55, 56]:
        sub = merged[merged["idLegislatura"] == leg]
        for col in ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp7_pre60",
                    "T_rp8_pre60", "T_rp9_pre60", "T_rp9_imputed_pre60"]:
            pos = sub[col] > 0
            rows.append({
                "legis": leg,
                "rp": col.replace("T_", "").replace("_pre60", ""),
                "n_obs": len(sub),
                "n_positive": int(pos.sum()),
                "pct_positive": round(100 * pos.mean(), 2),
                "mean_when_positive_R$M": round(sub.loc[pos, col].mean() / 1e6, 3) if pos.any() else 0,
                "p50_when_positive_R$M": round(sub.loc[pos, col].median() / 1e6, 3) if pos.any() else 0,
                "max_R$M": round(sub[col].max() / 1e6, 3),
                "total_R$bi": round(sub[col].sum() / 1e9, 3),
            })
    eda = pd.DataFrame(rows)
    eda_path = RESULTS / "eda_multi_rp_coverage.csv"
    eda.to_csv(eda_path, sep=";", index=False)
    print(f"    {eda_path}: {len(eda)} rows")
    print()
    print(eda.to_string(index=False))


if __name__ == "__main__":
    panel = load_panel()
    pt = load_portal_transparencia()
    se = load_siconv_emenda_with_year()
    sa = load_siconv_apoiadores_with_year()

    yearly = consolidate_yearly(
        panel, {"portal_transparencia": pt, "siconv_emenda": se, "siconv_apoiadores": sa}
    )
    merged = build_60d_window(panel, yearly)
    save_outputs(merged)
    print("\nDone.")
