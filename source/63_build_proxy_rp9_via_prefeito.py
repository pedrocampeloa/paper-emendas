"""
63_build_proxy_rp9_via_prefeito.py
-----------------------------------
PROXY 4: RP-9 imputado via prefeito TSE 2020 (GitHub gabinete-compartilhado).

Dados: empenhos RP-9 (FNDE + MDR) em 2020-2021, com mapping municipio -> prefeito eleito
em 2020 + partido. Total: ~15k empenhos.

Heuristica de imputacao deputado:
  Para cada empenho RP-9 em municipio M, atribuir ao(s) deputado(s) Federal(is)
  da mesma UF e MESMO PARTIDO do prefeito de M.
  Isso e' uma proxy: assume que o prefeito de M, se do partido X, articulou via
  deputados do partido X da mesma UF.

Granularidade: deputado x ano.

Cobertura esperada: ~30% das obs Leg 56 (vs 3.2% do oficial).

Output:
  dados/interim/panel/panel_proxy_rp9_imputed_prefeito.csv (idDeputado, ano, vl_rp9_imputed_prefeito)
  results/eda_proxy_rp9_imputed_prefeito.csv
"""

import logging
import unicodedata
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "dados" / "raw" / "orcamento" / "github_rp9" / "processados"
PANEL = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("rp9pref")


def norm_partido(s):
    if not isinstance(s, str): return ""
    s = s.upper().strip()
    # Normalizacoes conhecidas: DEM era UNIAO depois fusao 2022
    return s


def parse_valor(s):
    """'541.663,72' -> 541663.72"""
    if not isinstance(s, str): return np.nan
    s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except: return np.nan


def main():
    log.info("PROXY 4: RP-9 imputado via prefeito TSE 2020")

    log.info("[1] Loading empenhos RP-9 (FNDE + MDR, 2020-2021)")
    files = list(RAW.glob("empenhos_*.csv"))
    log.info(f"    {len(files)} arquivos encontrados")
    dfs = []
    for fp in files:
        df = pd.read_csv(fp, dtype=str, low_memory=False)
        df["source"] = fp.name
        dfs.append(df)
    rp9 = pd.concat(dfs, ignore_index=True)
    log.info(f"    {len(rp9):,} empenhos totais")

    rp9["VALOR_num"] = rp9["VALOR"].apply(parse_valor)
    rp9["DATA"] = pd.to_datetime(rp9["DATA"], format="%d/%m/%Y", errors="coerce")
    rp9["ano"] = rp9["DATA"].dt.year
    rp9["SG_PARTIDO_norm"] = rp9["SG_PARTIDO"].apply(norm_partido)
    rp9 = rp9.dropna(subset=["VALOR_num", "ano", "SG_PARTIDO_norm", "UF"])
    rp9 = rp9[rp9["SG_PARTIDO_norm"] != ""]
    log.info(f"    {len(rp9):,} empenhos com prefeito identificado")

    # Agregar empenhos por (UF, partido_prefeito, ano) - quanto foi para municipios
    # daquele partido naquela UF
    log.info("[2] Agregando por (UF, partido_prefeito, ano)")
    by_uf_part = rp9.groupby(["UF", "SG_PARTIDO_norm", "ano"]).agg(
        vl_rp9_uf_part=("VALOR_num", "sum"),
        n_empenhos=("VALOR_num", "count"),
        n_municipios=("NOME MUNICÍPIO", "nunique"),
    ).reset_index()
    by_uf_part["ano"] = by_uf_part["ano"].astype(int)

    log.info(f"    {len(by_uf_part):,} cells (UF, partido, ano)")

    log.info("[3] Loading painel principal para identificar deputados (id, UF, partido)")
    pf = pd.read_csv(PANEL / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "siglaUf", "siglaPartido", "idLegislatura", "data"],
                     dtype=str, low_memory=False)
    pf["partido_norm"] = pf["siglaPartido"].astype(str).str.upper().str.strip()
    pf["data"] = pd.to_datetime(pf["data"], errors="coerce")
    pf["ano"] = pf["data"].dt.year.astype("Int64")
    # Unico por (deputado, UF, partido, ano) - representa filiacao
    dep_year = pf[["idDeputado", "siglaUf", "partido_norm", "ano"]].dropna().drop_duplicates()
    log.info(f"    {len(dep_year):,} pares (deputado, UF, partido, ano) unicos")

    log.info("[4] Imputando RP-9 a deputados via (UF, partido_prefeito, ano)")
    # Cada (UF, partido, ano) tem n deputados; o RP-9 e' dividido entre eles
    n_deputados = dep_year.groupby(["siglaUf", "partido_norm", "ano"]).size().reset_index(name="n_deps_uf_part")
    by_uf_part = by_uf_part.merge(n_deputados,
                                    left_on=["UF", "SG_PARTIDO_norm", "ano"],
                                    right_on=["siglaUf", "partido_norm", "ano"],
                                    how="inner")
    by_uf_part["vl_rp9_por_dep"] = by_uf_part["vl_rp9_uf_part"] / by_uf_part["n_deps_uf_part"]

    # Merge no dep_year: cada deputado recebe sua share por ano
    imp = dep_year.merge(by_uf_part[["siglaUf", "partido_norm", "ano", "vl_rp9_por_dep",
                                      "vl_rp9_uf_part", "n_empenhos", "n_municipios"]],
                          on=["siglaUf", "partido_norm", "ano"], how="left")
    imp["vl_rp9_imputed"] = imp["vl_rp9_por_dep"].fillna(0)

    out = imp.groupby(["idDeputado", "ano"]).agg(
        vl_rp9_imputed_prefeito=("vl_rp9_imputed", "sum"),
        siglaUf=("siglaUf", "first"),
        partido_norm=("partido_norm", "first"),
    ).reset_index()
    out["ano"] = out["ano"].astype(int)

    log.info(f"    {len(out):,} (deputado, ano) cells")
    log.info(f"    Com imputed > 0: {(out['vl_rp9_imputed_prefeito'] > 0).sum():,} ({100*(out['vl_rp9_imputed_prefeito'] > 0).mean():.1f}%)")
    log.info(f"    Mean (positivos): R${out[out['vl_rp9_imputed_prefeito']>0]['vl_rp9_imputed_prefeito'].mean()/1e6:.3f}M")

    out.to_csv(PANEL / "panel_proxy_rp9_imputed_prefeito.csv", sep=";", index=False)
    log.info(f"\n  saved {PANEL / 'panel_proxy_rp9_imputed_prefeito.csv'}")

    eda = out.groupby("ano").agg(
        n_deputados=("idDeputado", "nunique"),
        n_with_imputed=("vl_rp9_imputed_prefeito", lambda x: (x > 0).sum()),
        pct_with_imputed=("vl_rp9_imputed_prefeito", lambda x: 100 * (x > 0).mean()),
        mean_R_M_positivos=("vl_rp9_imputed_prefeito", lambda x: x[x > 0].mean() / 1e6 if (x > 0).any() else 0),
        total_R_bi=("vl_rp9_imputed_prefeito", lambda x: x.sum() / 1e9),
    ).reset_index()
    eda.to_csv(RESULTS / "eda_proxy_rp9_imputed_prefeito.csv", sep=";", index=False)
    print(eda.to_string(index=False))


if __name__ == "__main__":
    main()
