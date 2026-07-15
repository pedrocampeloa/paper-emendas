"""
65_build_proxy_cargos.py
-------------------------
PROXY 6: Cargos no Legislativo (lideranças, mesa, comissões).

Dados:
  dados/raw/orgaos/membros/orgaos_membros_raw.json -- key = idOrgao, value = list de
    membros com (id_deputado, titulo, codTitulo, dataInicio, dataFim, idLegislatura)
  dados/raw/orgaos/orgaos_meta.csv -- idOrgao -> nome, sigla, tipo

Cargos relevantes para pork-barrel / legislative capture:
  TIER 1 (alto poder): Presidente da Câmara, Mesa Diretora (1º/2º Secretário, etc.)
  TIER 2 (médio poder): Líderes partidários, Presidentes de comissões
  TIER 3 (baixo poder): Vice-Presidentes de comissões, Relatores
  TIER 4 (acesso): Titular de comissão (vs Suplente)

Por deputado-ano, calcular:
  - n_cargos_tier1, n_cargos_tier2, n_cargos_tier3
  - n_comissoes_titular, n_comissoes_suplente
  - n_relatorias
  - has_lideranca (binario)
  - has_mesa (binario)
  - tier_max (1-4)

Output:
  dados/interim/panel/panel_proxy_cargos.csv (idDeputado, ano, n_*, has_*)
  results/eda_proxy_cargos.csv
"""

import json
import logging
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "dados" / "raw" / "orgaos"
PANEL = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("cargos")


def tier_for(titulo, sigla_orgao, nome_orgao):
    """Classifica cargo em tier 1-4."""
    t = (titulo or "").lower()
    s = (sigla_orgao or "").upper()
    n = (nome_orgao or "").lower()

    if "presidente da câmara" in n or s == "PRESIDENCIA":
        return 1
    if "mesa" in n or s == "MESA":
        if "presidente" in t or "secret" in t:
            return 1
    if "líder" in t or "lider" in t:
        return 2
    if "líder" in n.lower() or "liderança" in n.lower() or s.startswith("LID"):
        if "titular" in t or "líder" in t:
            return 2
    if "presidente" in t and ("comiss" in n or s.startswith("C")):
        return 2
    if ("vice" in t or "relator" in t or "secretário" in t or "secretario" in t) and "comiss" in n:
        return 3
    if "titular" in t and "comiss" in n:
        return 4
    if "suplente" in t and "comiss" in n:
        return 5
    return None


def main():
    log.info("PROXY 6: Cargos no Legislativo")

    log.info("[1] Loading orgaos meta (idOrgao -> tipo/nome)")
    meta = pd.read_csv(RAW / "orgaos_meta.csv", sep=";", dtype=str, low_memory=False)
    log.info(f"    {len(meta):,} orgaos no meta")
    log.info(f"    cols: {list(meta.columns)}")
    meta = meta[["id", "sigla", "nome", "tipoOrgao", "codTipoOrgao"]].rename(columns={"id": "idOrgao"})

    log.info("[2] Loading orgaos_membros_raw.json")
    with open(RAW / "membros" / "orgaos_membros_raw.json") as f:
        data = json.load(f)
    log.info(f"    {len(data)} orgaos com membros")

    log.info("[3] Flatten")
    rows = []
    for idOrgao, membros in data.items():
        for m in membros:
            rows.append({
                "idOrgao": str(idOrgao),
                "idDeputado": str(m.get("id")),
                "titulo": m.get("titulo"),
                "codTitulo": m.get("codTitulo"),
                "siglaPartido": m.get("siglaPartido"),
                "siglaUf": m.get("siglaUf"),
                "idLegislatura": m.get("idLegislatura"),
                "dataInicio": m.get("dataInicio"),
                "dataFim": m.get("dataFim"),
            })
    df = pd.DataFrame(rows)
    log.info(f"    {len(df):,} membros total")

    log.info("[4] Merge com meta")
    df = df.merge(meta, on="idOrgao", how="left")

    df["dataInicio"] = pd.to_datetime(df["dataInicio"], errors="coerce")
    df["dataFim"] = pd.to_datetime(df["dataFim"], errors="coerce")
    df["ano_inicio"] = df["dataInicio"].dt.year
    df["ano_fim"] = df["dataFim"].dt.year

    log.info(f"    tipos orgao: {df['tipoOrgao'].value_counts().head(10).to_dict()}")
    log.info(f"    titulos top: {df['titulo'].value_counts().head(10).to_dict()}")

    log.info("[5] Tier assignment")
    df["tier"] = df.apply(lambda r: tier_for(r["titulo"], r["sigla"], r["nome"]), axis=1)
    log.info(f"    distribuicao tier: {df['tier'].value_counts(dropna=False).to_dict()}")

    log.info("[6] Expandir para deputado x ano (intervalo [ano_inicio, ano_fim])")
    # Para cada cargo, expandir entre anos_inicio e ano_fim
    df_valid = df.dropna(subset=["idDeputado", "ano_inicio"]).copy()
    df_valid["ano_fim"] = df_valid["ano_fim"].fillna(2026)  # ainda no cargo

    rows_dyear = []
    for _, r in df_valid.iterrows():
        ano_i = int(r["ano_inicio"])
        ano_f = int(r["ano_fim"])
        if ano_f < ano_i: continue
        for ano in range(ano_i, ano_f + 1):
            rows_dyear.append({
                "idDeputado": r["idDeputado"],
                "ano": ano,
                "tier": r["tier"],
                "titulo": r["titulo"],
                "tipoOrgao": r["tipoOrgao"],
                "is_lideranca": "lider" in str(r["titulo"]).lower() or "líder" in str(r["nome"]).lower(),
                "is_mesa": "mesa" in str(r["nome"]).lower(),
                "is_presidente_comissao": ("presidente" in str(r["titulo"]).lower() and
                                              "comissao" in str(r["tipoOrgao"]).lower()),
                "is_relator": "relator" in str(r["titulo"]).lower(),
                "is_titular": r["titulo"] == "Titular",
                "is_suplente": r["titulo"] == "Suplente",
            })
    dy = pd.DataFrame(rows_dyear)
    log.info(f"    {len(dy):,} (deputado, ano, cargo) expansoes")

    log.info("[7] Agregando por deputado-ano")
    agg = dy.groupby(["idDeputado", "ano"]).agg(
        n_cargos=("titulo", "count"),
        n_tier1=("tier", lambda x: (x == 1).sum()),
        n_tier2=("tier", lambda x: (x == 2).sum()),
        n_tier3=("tier", lambda x: (x == 3).sum()),
        n_titular=("is_titular", "sum"),
        n_suplente=("is_suplente", "sum"),
        n_relator=("is_relator", "sum"),
        has_lideranca=("is_lideranca", "max"),
        has_mesa=("is_mesa", "max"),
        has_pres_comissao=("is_presidente_comissao", "max"),
        tier_max=("tier", "min"),  # menor = maior poder
    ).reset_index()

    log.info(f"    {len(agg):,} (deputado, ano) cells")
    log.info(f"    Tier 1+: {(agg['n_tier1'] > 0).sum():,}")
    log.info(f"    Tier 2+: {(agg['n_tier2'] > 0).sum():,}")
    log.info(f"    Liderança: {agg['has_lideranca'].sum():,}")
    log.info(f"    Mesa: {agg['has_mesa'].sum():,}")

    agg.to_csv(PANEL / "panel_proxy_cargos.csv", sep=";", index=False)
    log.info(f"\n  saved {PANEL / 'panel_proxy_cargos.csv'}")

    eda = agg.groupby("ano").agg(
        n_deputados=("idDeputado", "nunique"),
        media_n_cargos=("n_cargos", "mean"),
        pct_lideranca=("has_lideranca", "mean"),
        pct_mesa=("has_mesa", "mean"),
        pct_pres_comissao=("has_pres_comissao", "mean"),
    ).reset_index()
    eda.to_csv(RESULTS / "eda_proxy_cargos.csv", sep=";", index=False)
    print(eda.to_string(index=False))


if __name__ == "__main__":
    main()
