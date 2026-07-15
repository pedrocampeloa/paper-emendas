"""
34_build_secret_budget_proxies.py
----------------------------------
Constroi proxies de exposicao ao orcamento secreto (RP-9) por
deputado-votacao. Como o RP-9 individual-level data esta disponivel apenas
parcialmente (137 observacoes via PARLAMENTAR_SOLICITANTE + imputacao via
prefeitos TSE), usamos proxies adicionais:

    1. d_rp9_solicitante: dummy = 1 se deputado aparece como
       PARLAMENTAR_SOLICITANTE em qualquer RP-9 do ano.

    2. n_apoiamentos_opaco: contagem total de apoiamentos (RP-8 + RP-9)
       por deputado-ano. Proxy de interacao com o canal opaco.

    3. share_pork_opaco: razao RP-9 / (RP-6 + RP-8 + RP-9) por deputado-ano.
       Mede a fracao do "pork" total que vem do canal opaco.

    4. share_pix: razao Pix / (Pix + RP-6 nao-Pix) por deputado-ano.
       Mede preferencia por canal sem rastreabilidade.

    5. rp9_share_uf: share UF-nivel de RP-9 sobre RP-6+RP-8+RP-9 (agregado
       estadual; serve como controle do contexto regional opaco).

Output:
    dados/interim/panel/panel_secret_budget_proxies.csv
    paper-emendas/results/eda_proxies_overview.csv
"""

import unicodedata
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "dados" / "raw" / "orcamento"
INTERIM = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"


def norm_name(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(s.upper().strip().split())


def load_panel():
    print("\n[1] Loading panel")
    df = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "nome", "siglaUf", "data",
                              "idVotacao", "idLegislatura"], dtype=str, low_memory=False)
    df["data"] = pd.to_datetime(df["data"])
    df["nome_norm"] = df["nome"].apply(norm_name)
    df["ano"] = df["data"].dt.year.astype(int)
    df["idLegislatura"] = pd.to_numeric(df["idLegislatura"], errors="coerce").astype("Int64")
    return df


def load_apoiadores():
    print("\n[2] Loading apoiadores")
    ap = pd.read_csv(RAW / "transferegov_bulk" / "apoiadores_emendas_programas.csv",
                     sep=";", encoding="utf-8", dtype=str, low_memory=False)
    ap.columns = [c.replace("﻿", "").replace("_APOIADORES_EMENDAS", "") for c in ap.columns]
    ap["valor"] = pd.to_numeric(ap["VALOR_REPASSE_PROPOSTA"], errors="coerce")

    is_rg = ap["NOME_PARLAMENTAR"].str.upper().str.strip() == "RELATOR GERAL"
    is_com = ap["NOME_PARLAMENTAR"].str.contains("Com|COMISS", na=False, case=False, regex=True)

    # Lookup ano via programa
    prog = pd.read_csv(RAW / "transferegov_bulk" / "siconv_programa.csv",
                       sep=";", encoding="utf-8", dtype=str,
                       usecols=["ID_PROGRAMA", "ANO_DISPONIBILIZACAO"], low_memory=False)
    prog["ano"] = pd.to_numeric(prog["ANO_DISPONIBILIZACAO"], errors="coerce").astype("Int64")
    prog = prog.dropna(subset=["ano"]).drop_duplicates("ID_PROGRAMA")
    ap = ap.merge(prog[["ID_PROGRAMA", "ano"]], on="ID_PROGRAMA", how="left")
    # Fallback para RP-9 sem ano: usar 2021
    ap.loc[is_rg & ap["ano"].isna(), "ano"] = 2021
    ap["ano"] = pd.to_numeric(ap["ano"], errors="coerce").astype("Int64")

    # Classificar por categoria
    ap["RP"] = np.select(
        [is_rg, is_com, ~is_rg & ~is_com],
        ["RP9", "RP8", "RP6"],
        default="UNK"
    )
    ap["nome_norm_solicitante"] = ap["PARLAMENTAR_SOLICITANTE"].apply(norm_name)
    ap["nome_norm_principal"] = ap["NOME_PARLAMENTAR"].apply(norm_name)

    print(f"    Total: {len(ap):,}")
    print(f"    With year: {ap['ano'].notna().sum():,}")
    print(f"    RP breakdown: {ap['RP'].value_counts().to_dict()}")
    return ap


def build_proxies(panel, ap):
    """Constroi proxies em duas etapas: por deputado-ano, depois por deputado-voto."""
    print("\n[3] Building per-deputy-year proxies")
    panel_names = set(panel["nome_norm"].unique())

    # Proxy 1: d_rp9_solicitante (dummy: deputado aparece como solicitante de RP-9)
    rp9_sol = ap[(ap["RP"] == "RP9") & ap["nome_norm_solicitante"].isin(panel_names)
                 & ap["ano"].notna()]
    rp9_sol_yearly = rp9_sol.groupby(["nome_norm_solicitante", "ano"]).size().reset_index(name="n_rp9_sol")
    rp9_sol_yearly = rp9_sol_yearly.rename(columns={"nome_norm_solicitante": "nome_norm"})
    print(f"    RP-9 solicitante: {len(rp9_sol_yearly):,} (deputy,year) cells")

    # Proxy 2: n_apoiamentos_opaco (contagem RP-8 + RP-9)
    opaco = ap[ap["RP"].isin(["RP8", "RP9"])].copy()
    # Quem e' o "responsavel": para RP-8 e' SOLICITANTE; para RP-9 e' SOLICITANTE tambem
    opaco["nome_resp"] = opaco["nome_norm_solicitante"]
    opaco = opaco[opaco["nome_resp"].isin(panel_names) & opaco["ano"].notna()]
    n_opaco = opaco.groupby(["nome_resp", "ano"]).size().reset_index(name="n_apoiamentos_opaco")
    n_opaco = n_opaco.rename(columns={"nome_resp": "nome_norm"})
    print(f"    Apoiamentos opacos: {len(n_opaco):,} (deputy,year) cells")

    # Proxy 3: share_pork_opaco
    # Precisa valores RP-6 (individual) + RP-8 + RP-9
    val_rp6 = ap[(ap["RP"] == "RP6") & ap["nome_norm_principal"].isin(panel_names)
                 & ap["ano"].notna()]
    val_rp6_yearly = val_rp6.groupby(["nome_norm_principal", "ano"])["valor"].sum().reset_index()
    val_rp6_yearly = val_rp6_yearly.rename(columns={"nome_norm_principal": "nome_norm", "valor": "val_rp6"})

    val_rp8 = ap[(ap["RP"] == "RP8") & ap["nome_norm_solicitante"].isin(panel_names)
                 & ap["ano"].notna()]
    val_rp8_yearly = val_rp8.groupby(["nome_norm_solicitante", "ano"])["valor"].sum().reset_index()
    val_rp8_yearly = val_rp8_yearly.rename(columns={"nome_norm_solicitante": "nome_norm", "valor": "val_rp8"})

    val_rp9 = ap[(ap["RP"] == "RP9") & ap["nome_norm_solicitante"].isin(panel_names)
                 & ap["ano"].notna()]
    val_rp9_yearly = val_rp9.groupby(["nome_norm_solicitante", "ano"])["valor"].sum().reset_index()
    val_rp9_yearly = val_rp9_yearly.rename(columns={"nome_norm_solicitante": "nome_norm", "valor": "val_rp9"})

    yearly = (val_rp6_yearly.merge(val_rp8_yearly, on=["nome_norm", "ano"], how="outer")
                            .merge(val_rp9_yearly, on=["nome_norm", "ano"], how="outer"))
    yearly = yearly.fillna(0)
    yearly["total_pork"] = yearly["val_rp6"] + yearly["val_rp8"] + yearly["val_rp9"]
    yearly["share_pork_opaco"] = np.where(
        yearly["total_pork"] > 0,
        (yearly["val_rp8"] + yearly["val_rp9"]) / yearly["total_pork"], 0)
    yearly["share_rp9"] = np.where(
        yearly["total_pork"] > 0, yearly["val_rp9"] / yearly["total_pork"], 0)
    print(f"    Share pork opaco: {len(yearly):,} (deputy,year) cells")

    # Proxy 4: share_pix (precisa do Portal Transparencia ja que apoiadores nao separa Pix)
    print("\n[4] Loading Portal Transparencia for Pix share")
    pt = pd.read_csv(RAW / "portal_transparencia" / "EmendasParlamentares.csv",
                     sep=";", encoding="cp1252", dtype=str, low_memory=False)
    pt["nome_norm"] = pt["Nome do Autor da Emenda"].apply(norm_name)
    pt = pt[pt["nome_norm"].isin(panel_names) & (pt["nome_norm"] != "")]
    pt["ano"] = pd.to_numeric(pt["Ano da Emenda"], errors="coerce").astype("Int64")
    pt["valor"] = pt["Valor Empenhado"].fillna("0").str.replace(",", ".").astype(float)
    pt["is_pix"] = (pt["Tipo de Emenda"] == "Emenda Individual - Transferências Especiais").astype(int)
    pt = pt.dropna(subset=["ano"])

    pix_yearly = pt[pt["is_pix"] == 1].groupby(["nome_norm", "ano"])["valor"].sum().reset_index()
    pix_yearly = pix_yearly.rename(columns={"valor": "val_pix"})
    rp6_pt_yearly = pt[(pt["Tipo de Emenda"] == "Emenda Individual - Transferências com Finalidade Definida")].groupby(["nome_norm", "ano"])["valor"].sum().reset_index()
    rp6_pt_yearly = rp6_pt_yearly.rename(columns={"valor": "val_rp6_conv"})
    pix_share = pix_yearly.merge(rp6_pt_yearly, on=["nome_norm", "ano"], how="outer").fillna(0)
    pix_share["total_rp6"] = pix_share["val_pix"] + pix_share["val_rp6_conv"]
    pix_share["share_pix"] = np.where(pix_share["total_rp6"] > 0,
                                       pix_share["val_pix"] / pix_share["total_rp6"], 0)
    print(f"    Pix share: {len(pix_share):,} (deputy,year) cells")

    print("\n[5] Joining all proxies into single per-(deputy,year) frame")
    proxies = (yearly[["nome_norm", "ano", "val_rp6", "val_rp8", "val_rp9",
                       "total_pork", "share_pork_opaco", "share_rp9"]]
               .merge(rp9_sol_yearly, on=["nome_norm", "ano"], how="outer")
               .merge(n_opaco, on=["nome_norm", "ano"], how="outer")
               .merge(pix_share[["nome_norm", "ano", "val_pix", "share_pix"]],
                      on=["nome_norm", "ano"], how="outer"))
    proxies = proxies.fillna(0)
    proxies["ano"] = proxies["ano"].astype("Int64")
    proxies["d_rp9_solicitante"] = (proxies["n_rp9_sol"] > 0).astype(int)
    print(f"    Per-deputy-year: {len(proxies):,} cells, "
          f"{(proxies['d_rp9_solicitante']==1).sum():,} with d_rp9_solicitante=1")

    print("\n[6] Joining proxies to panel (deputy x vote level)")
    panel["ano"] = panel["data"].dt.year.astype("Int64")
    out = panel.merge(proxies, on=["nome_norm", "ano"], how="left")
    proxy_cols = ["val_rp6", "val_rp8", "val_rp9", "total_pork", "share_pork_opaco",
                  "share_rp9", "n_rp9_sol", "n_apoiamentos_opaco", "val_pix", "share_pix",
                  "d_rp9_solicitante"]
    for c in proxy_cols:
        out[c] = out[c].fillna(0)
    return out[["idDeputado", "idVotacao", "data", "idLegislatura"] + proxy_cols]


def save_outputs(panel_with_proxies):
    print("\n[7] Saving outputs")
    out_path = INTERIM / "panel_secret_budget_proxies.csv"
    panel_with_proxies.to_csv(out_path, sep=";", index=False)
    print(f"    {out_path}: {len(panel_with_proxies):,} rows")

    rows = []
    for leg in [55, 56]:
        sub = panel_with_proxies[panel_with_proxies["idLegislatura"] == leg]
        rows.append({
            "legis": leg, "metric": "d_rp9_solicitante",
            "n_obs": len(sub), "n_positive": int((sub["d_rp9_solicitante"] == 1).sum()),
            "pct_positive": round(100 * (sub["d_rp9_solicitante"] == 1).mean(), 2),
        })
        for c in ["n_apoiamentos_opaco", "share_pork_opaco", "share_rp9", "share_pix"]:
            rows.append({
                "legis": leg, "metric": c, "n_obs": len(sub),
                "n_positive": int((sub[c] > 0).sum()),
                "pct_positive": round(100 * (sub[c] > 0).mean(), 2),
                "mean_when_positive": round(sub.loc[sub[c] > 0, c].mean(), 4) if (sub[c] > 0).any() else 0,
            })
    eda = pd.DataFrame(rows)
    eda_path = RESULTS / "eda_proxies_overview.csv"
    eda.to_csv(eda_path, sep=";", index=False)
    print(f"    {eda_path}")
    print()
    print(eda.to_string(index=False))


if __name__ == "__main__":
    panel = load_panel()
    ap = load_apoiadores()
    out = build_proxies(panel, ap)
    save_outputs(out)
    print("\nDone.")
