"""
32_eda_budget_data.py
---------------------
EDA exploratório consolidado sobre todas as fontes de dados orçamentários
baixadas via `shared/download_budget_data.py`.

Objetivo: gerar uma tabela única de overview com:
    1. Por fonte de dado: número de linhas, cobertura temporal, granularidade
    2. Por tipo de emenda (RP-6/7/8/9): contagens e valores agregados por ano
    3. Cobertura cross-fonte (Portal Transparência vs Tesouro vs SICONV)
    4. Mapping deputado-emenda: quantos deputados aparecem em cada fonte
    5. Conexões com o painel principal do paper (panel_features.csv)

Outputs:
    results/eda_overview.csv          - tabela 1 (overview por fonte)
    results/eda_by_year_rp.csv        - tabela 2 (ano × RP × valor)
    results/eda_deputy_coverage.csv   - tabela 3 (deputado × fonte)
    docs/figs/eda_*.pdf               - figuras
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

REPO_ROOT = Path(__file__).resolve().parents[2]
DADOS = REPO_ROOT / "dados" / "raw" / "orcamento"
PANEL = REPO_ROOT / "dados" / "interim" / "panel" / "panel_features.csv"
OUT_RESULTS = REPO_ROOT / "paper-emendas" / "results"
OUT_FIGS = REPO_ROOT / "paper-emendas" / "docs" / "figs"
OUT_RESULTS.mkdir(parents=True, exist_ok=True)
OUT_FIGS.mkdir(parents=True, exist_ok=True)


def load_portal_transparencia():
    """Bulk Portal Transparência: 93k emendas com autor."""
    fp = DADOS / "portal_transparencia" / "EmendasParlamentares.csv"
    if not fp.exists():
        print(f"  MISSING: {fp}")
        return None
    df = pd.read_csv(fp, sep=";", encoding="latin-1", dtype=str, low_memory=False)
    # Tipos -> RP code
    rp_map = {
        "Emenda Individual - Transferências com Finalidade Definida": "RP6",
        "Emenda Individual - Transferências Especiais": "RP6_Pix",
        "Emenda de Bancada": "RP7",
        "Emenda de Comissão": "RP8",
        "Emenda de Relator": "RP9",
    }
    df["RP"] = df["Tipo de Emenda"].map(rp_map)
    for c in ["Valor Empenhado", "Valor Liquidado", "Valor Pago"]:
        df[c] = (df[c].fillna("0").str.replace(",", ".").astype(float))
    df["Ano"] = pd.to_numeric(df["Ano da Emenda"], errors="coerce")
    return df


def load_tesouro():
    """Tesouro Emendas Individuais e de Bancada: 388k linhas mensais."""
    fp = DADOS / "tesouro" / "emendas-parlamentares-individuais-e-de-bancada" / "emendas-parlamentares.csv"
    if not fp.exists():
        print(f"  MISSING: {fp}")
        return None
    df = pd.read_csv(fp, sep=";", encoding="latin-1", dtype=str, low_memory=False)
    df["Valor"] = pd.to_numeric(df["Valor"].str.replace(",", "."), errors="coerce")
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce")
    return df


def load_siconv_emenda():
    """SICONV emenda: 296k emendas com NOME_PARLAMENTAR."""
    fp = DADOS / "transferegov_bulk" / "siconv_emenda.csv"
    if not fp.exists():
        print(f"  MISSING: {fp}")
        return None
    df = pd.read_csv(fp, sep=";", encoding="latin-1", dtype=str, low_memory=False)
    df.columns = [c.replace("ï»¿", "") for c in df.columns]
    df["VALOR_REPASSE_EMENDA"] = pd.to_numeric(df["VALOR_REPASSE_EMENDA"], errors="coerce")
    df["NR_EMENDA_ANO"] = df["NR_EMENDA"].str[:4]
    return df


def load_siconv_apoiadores():
    """SICONV apoiadores: 291k mapeamentos parlamentar → emenda."""
    fp = DADOS / "transferegov_bulk" / "apoiadores_emendas_programas.csv"
    if not fp.exists():
        print(f"  MISSING: {fp}")
        return None
    df = pd.read_csv(fp, sep=";", encoding="latin-1", dtype=str, low_memory=False)
    df.columns = [c.replace("ï»¿", "").replace("_APOIADORES_EMENDAS", "") for c in df.columns]
    df["VALOR_REPASSE_PROPOSTA"] = pd.to_numeric(df["VALOR_REPASSE_PROPOSTA"], errors="coerce")
    return df


def load_siconv_convenio():
    """SICONV convênio: 283k convênios com datas, valores."""
    fp = DADOS / "transferegov_bulk" / "siconv_convenio.csv"
    if not fp.exists():
        print(f"  MISSING: {fp}")
        return None
    df = pd.read_csv(fp, sep=";", encoding="latin-1", dtype=str, low_memory=False)
    df.columns = [c.replace("ï»¿", "") for c in df.columns]
    for c in ["VL_GLOBAL_CONV", "VL_REPASSE_CONV", "VL_EMPENHADO_CONV", "VL_DESEMBOLSADO_CONV"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["DIA_ASSIN_CONV"] = pd.to_datetime(df["DIA_ASSIN_CONV"], format="%d/%m/%Y", errors="coerce")
    df["ANO_ASSIN"] = df["DIA_ASSIN_CONV"].dt.year
    return df


def load_github_rp9():
    """RP-9 GitHub gabinete-compartilhado: imputação via prefeitos TSE."""
    fp = DADOS / "github_rp9" / "processados" / "empenhos_2020-completo_RP9_FNDE_PTransp+Prefeitos-TSE.csv"
    if not fp.exists():
        print(f"  MISSING: {fp}")
        return None
    df_2020 = pd.read_csv(fp, low_memory=False)
    fp2 = DADOS / "github_rp9" / "processados" / "empenhos_2021-completo_RP9_FNDE_PTransp+Prefeitos-TSE.csv"
    df_2021 = pd.read_csv(fp2, low_memory=False) if fp2.exists() else pd.DataFrame()
    return pd.concat([df_2020, df_2021], ignore_index=True)


# -------------------------------------------------------------------------
# TABELA 1 — Overview por fonte
# -------------------------------------------------------------------------
def table_overview():
    """Por fonte de dado: linhas, cobertura, granularidade."""
    print("\n" + "=" * 60)
    print("TABELA 1 — Overview por fonte de dado")
    print("=" * 60)
    rows = []

    pt = load_portal_transparencia()
    if pt is not None:
        rows.append({
            "Fonte": "Portal Transparência (bulk)",
            "Arquivo": "EmendasParlamentares.csv",
            "Linhas": len(pt),
            "Cobertura": f"{int(pt['Ano'].min())}-{int(pt['Ano'].max())}",
            "Granularidade": "emenda × autor × localidade × função",
            "RPs": ", ".join(sorted(pt["RP"].dropna().unique())),
            "Autores únicos": pt[~pt["Nome do Autor da Emenda"].str.contains("Sem", na=False)]["Nome do Autor da Emenda"].nunique(),
            "Valor total (R$ bi)": pt["Valor Empenhado"].sum() / 1e9,
        })

    ts = load_tesouro()
    if ts is not None:
        rows.append({
            "Fonte": "Tesouro CKAN",
            "Arquivo": "emendas-parlamentares.csv",
            "Linhas": len(ts),
            "Cobertura": f"{int(ts['Ano'].min())}-{int(ts['Ano'].max())}",
            "Granularidade": "município × mês × emenda",
            "RPs": "RP-6 (com/sem Pix), RP-7",
            "Autores únicos": "—",  # Nao tem nome do autor
            "Valor total (R$ bi)": ts["Valor"].sum() / 1e9,
        })

    se = load_siconv_emenda()
    if se is not None:
        rows.append({
            "Fonte": "SICONV emenda",
            "Arquivo": "siconv_emenda.csv",
            "Linhas": len(se),
            "Cobertura": "2010-2026 (via NR_EMENDA)",
            "Granularidade": "emenda × parlamentar × beneficiário",
            "RPs": ", ".join(sorted(se["TIPO_PARLAMENTAR"].dropna().unique())),
            "Autores únicos": se["NOME_PARLAMENTAR"].nunique(),
            "Valor total (R$ bi)": se["VALOR_REPASSE_EMENDA"].sum() / 1e9,
        })

    sa = load_siconv_apoiadores()
    if sa is not None:
        rows.append({
            "Fonte": "SICONV apoiadores",
            "Arquivo": "apoiadores_emendas_programas.csv",
            "Linhas": len(sa),
            "Cobertura": "2010-2026",
            "Granularidade": "apoiador × emenda × proponente",
            "RPs": "INDIVIDUAL, COMISSAO, BANCADA, RG",
            "Autores únicos": sa["NOME_PARLAMENTAR"].nunique(),
            "Valor total (R$ bi)": sa["VALOR_REPASSE_PROPOSTA"].sum() / 1e9,
        })

    sc = load_siconv_convenio()
    if sc is not None:
        rows.append({
            "Fonte": "SICONV convênio",
            "Arquivo": "siconv_convenio.csv",
            "Linhas": len(sc),
            "Cobertura": f"{int(sc['ANO_ASSIN'].min()) if sc['ANO_ASSIN'].notna().any() else '?'}-{int(sc['ANO_ASSIN'].max()) if sc['ANO_ASSIN'].notna().any() else '?'}",
            "Granularidade": "convênio × conveniado × programa",
            "RPs": "—",
            "Autores únicos": "—",
            "Valor total (R$ bi)": sc["VL_REPASSE_CONV"].sum() / 1e9 if "VL_REPASSE_CONV" in sc else None,
        })

    rg = load_github_rp9()
    if rg is not None:
        rows.append({
            "Fonte": "GitHub gabinete RP-9",
            "Arquivo": "empenhos_*_RP9_*_PTransp+Prefeitos-TSE.csv",
            "Linhas": len(rg),
            "Cobertura": "2020-2021",
            "Granularidade": "empenho RP-9 × prefeito TSE 2020",
            "RPs": "RP-9 (somente FNDE + MDR)",
            "Autores únicos": rg["NM_CANDIDATO"].nunique() if "NM_CANDIDATO" in rg else "—",
            "Valor total (R$ bi)": "—",  # Valor é string com vírgula
        })

    df = pd.DataFrame(rows)
    out = OUT_RESULTS / "eda_overview.csv"
    df.to_csv(out, index=False, sep=";")
    print(f"\n✓ Saved: {out}")
    print(df.to_string(index=False))
    return df


# -------------------------------------------------------------------------
# TABELA 2 — Por ano × RP × valor
# -------------------------------------------------------------------------
def table_by_year_rp():
    """Volume de emendas por ano × tipo de RP."""
    print("\n" + "=" * 60)
    print("TABELA 2 — Volume por ano × RP")
    print("=" * 60)
    pt = load_portal_transparencia()
    if pt is None:
        return None
    agg = pt.groupby(["Ano", "RP"]).agg(
        n_emendas=("Código da Emenda", "count"),
        autores_unicos=("Nome do Autor da Emenda", lambda s: s[~s.str.contains("Sem", na=False)].nunique()),
        empenhado_bi=("Valor Empenhado", lambda s: s.sum() / 1e9),
        pago_bi=("Valor Pago", lambda s: s.sum() / 1e9),
    ).reset_index()
    out = OUT_RESULTS / "eda_by_year_rp.csv"
    agg.to_csv(out, index=False, sep=";")
    print(f"\n✓ Saved: {out}")
    print(agg.to_string(index=False))

    # Figura: empenho por RP × ano
    pivot = agg.pivot(index="Ano", columns="RP", values="empenhado_bi").fillna(0)
    fig, ax = plt.subplots(figsize=(11, 5))
    pivot.plot.area(ax=ax, stacked=True, alpha=0.75)
    ax.set_title("Volume empenhado por modalidade de emenda (R$ bi)")
    ax.set_xlabel("Ano")
    ax.set_ylabel("R$ bilhões")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"R$ {x:.0f} bi"))
    ax.legend(title="Resultado Primário", loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig_out = OUT_FIGS / "eda_empenho_by_rp.pdf"
    plt.savefig(fig_out, bbox_inches="tight")
    plt.close()
    print(f"✓ Figure saved: {fig_out}")

    # Figura: pct do total por ano
    pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(11, 5))
    pct.plot.area(ax=ax, stacked=True, alpha=0.85)
    ax.set_title("Composição percentual das emendas por modalidade")
    ax.set_xlabel("Ano")
    ax.set_ylabel("% do total empenhado")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.legend(title="RP", loc="upper left", bbox_to_anchor=(1, 1))
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig_out = OUT_FIGS / "eda_composicao_rp_pct.pdf"
    plt.savefig(fig_out, bbox_inches="tight")
    plt.close()
    print(f"✓ Figure saved: {fig_out}")
    return agg


# -------------------------------------------------------------------------
# TABELA 3 — Cobertura por deputado (cross-fonte)
# -------------------------------------------------------------------------
def table_deputy_coverage():
    """Quantos deputados aparecem em cada fonte; intersection."""
    print("\n" + "=" * 60)
    print("TABELA 3 — Cobertura por deputado")
    print("=" * 60)
    pt = load_portal_transparencia()
    se = load_siconv_emenda()
    sa = load_siconv_apoiadores()

    deps_pt = set()
    if pt is not None:
        deps_pt = set(pt[~pt["Nome do Autor da Emenda"].str.contains("Sem", na=False)]["Nome do Autor da Emenda"].str.upper().dropna().unique())
    deps_se = set()
    if se is not None:
        deps_se = set(se[se["NOME_PARLAMENTAR"].str.upper() != "RELATOR GERAL"]["NOME_PARLAMENTAR"].str.upper().dropna().unique())
    deps_sa = set()
    if sa is not None:
        deps_sa = set(sa["NOME_PARLAMENTAR"].str.upper().dropna().unique())

    print(f"Portal Transparência: {len(deps_pt):,} parlamentares únicos")
    print(f"SICONV emenda:        {len(deps_se):,}")
    print(f"SICONV apoiadores:    {len(deps_sa):,}")
    print(f"Interseção PT ∩ SE:   {len(deps_pt & deps_se):,}")
    print(f"Interseção PT ∩ SA:   {len(deps_pt & deps_sa):,}")
    print(f"Interseção SE ∩ SA:   {len(deps_se & deps_sa):,}")
    print(f"União das 3:          {len(deps_pt | deps_se | deps_sa):,}")

    out = OUT_RESULTS / "eda_deputy_coverage.csv"
    pd.DataFrame({
        "metric": [
            "portal_transparencia", "siconv_emenda", "siconv_apoiadores",
            "intersect_pt_se", "intersect_pt_sa", "intersect_se_sa", "union_all"
        ],
        "n_deputies": [
            len(deps_pt), len(deps_se), len(deps_sa),
            len(deps_pt & deps_se), len(deps_pt & deps_sa), len(deps_se & deps_sa),
            len(deps_pt | deps_se | deps_sa),
        ],
    }).to_csv(out, index=False, sep=";")
    print(f"✓ Saved: {out}")


# -------------------------------------------------------------------------
# TABELA 4 — Comparação com painel principal
# -------------------------------------------------------------------------
def table_panel_intersection():
    """Quantos dos deputados do painel principal aparecem em cada fonte?"""
    print("\n" + "=" * 60)
    print("TABELA 4 — Cobertura cross com painel principal")
    print("=" * 60)
    if not PANEL.exists():
        print(f"  PANEL not found: {PANEL}")
        return
    # Carregar só colunas necessárias
    panel = pd.read_csv(PANEL, sep=";", usecols=["idDeputado", "nome"], dtype=str, low_memory=False)
    deps_panel = set(panel["nome"].str.upper().dropna().unique())
    print(f"Painel principal: {len(deps_panel):,} parlamentares únicos")

    pt = load_portal_transparencia()
    se = load_siconv_emenda()
    sa = load_siconv_apoiadores()

    rows = []
    for name, df_, col in [
        ("Portal Transparência", pt, "Nome do Autor da Emenda"),
        ("SICONV emenda", se, "NOME_PARLAMENTAR"),
        ("SICONV apoiadores", sa, "NOME_PARLAMENTAR"),
    ]:
        if df_ is None:
            continue
        names = set(df_[col].str.upper().dropna().unique())
        inter = deps_panel & names
        rows.append({
            "Fonte": name,
            "Painel": len(deps_panel),
            "Fonte únicos": len(names),
            "Interseção": len(inter),
            "% painel coberto": len(inter) / len(deps_panel) * 100,
        })
    df = pd.DataFrame(rows)
    out = OUT_RESULTS / "eda_panel_intersection.csv"
    df.to_csv(out, index=False, sep=";")
    print(df.to_string(index=False))
    print(f"✓ Saved: {out}")


if __name__ == "__main__":
    table_overview()
    table_by_year_rp()
    table_deputy_coverage()
    table_panel_intersection()
    print("\n✓ EDA complete. Outputs in:")
    print(f"  {OUT_RESULTS}")
    print(f"  {OUT_FIGS}")
