"""
54_build_y_pres_camara_orient.py
---------------------------------
Constroi y_pres_camara_orient: voto alinhado com a orientacao formal do
partido do PRESIDENTE da Camara em cada momento.

Justificativa: queremos comparar "alinhamento com Executivo" (y_gov) vs
"alinhamento com Legislativo" (y_pres_camara). O presidente da Camara controla
a agenda, e seu partido orienta votos. A hipotese e' que pos-Lira, pork pode
estar comprando alinhamento com o PP (Lira's party), nao com o governo
Bolsonaro.

Definicao temporal:
  - 2015-02 a 2016-07: Cunha (PMDB) -> orientacao do PMDB
  - 2016-07-14 a 2021-02: Rodrigo Maia (DEM) -> orientacao do DEM
  - 2021-02-01 em diante: Arthur Lira (PP) -> orientacao do PP

Construcao:
  y_pres[i,t] = 1 se voto[i,t] == orientacao[partido_presidente(t), votacao t]
              = NaN se essa orientacao for "Liberado", "Abstencao", ou nao registrada

Outputs:
  dados/interim/panel/panel_y_pres_camara_orient.csv (idDeputado, idVotacao, y_pres, partido_presidente)
  results/eda_y_pres_camara_orient.csv (descritivas por sub-periodo)
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PANEL = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"


def get_partido_presidente(data: pd.Timestamp) -> str:
    """Retorna o partido do presidente da Camara naquela data."""
    if data < pd.Timestamp("2016-07-14"):
        return "PMDB"  # Cunha
    if data < pd.Timestamp("2021-02-01"):
        return "DEM"  # Maia (interino Maranhao foi 11 dias, ignoramos)
    return "PP"  # Lira


def main():
    print("[1] Loading panel_features")
    pf = pd.read_csv(PANEL / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "idVotacao", "siglaPartido", "voto",
                              "data", "idLegislatura",
                              "d_ori_part_sim", "d_ori_part_nao",
                              "d_ori_part_obstrucao", "d_ori_part_liberado",
                              "d_ori_part_abstencao"],
                     dtype=str, low_memory=False)
    print(f"    {len(pf):,} rows")
    for c in ["d_ori_part_sim", "d_ori_part_nao", "d_ori_part_obstrucao",
              "d_ori_part_liberado", "d_ori_part_abstencao"]:
        pf[c] = pd.to_numeric(pf[c], errors="coerce")
    pf["data"] = pd.to_datetime(pf["data"])
    pf["partido_norm"] = pf["siglaPartido"].astype(str).str.upper().str.strip()
    pf["idLegislatura"] = pd.to_numeric(pf["idLegislatura"])

    print("\n[2] Determinando partido do presidente da Camara por data")
    pf["partido_presidente"] = pf["data"].apply(get_partido_presidente)
    print("    Distribuicao:")
    print(pf["partido_presidente"].value_counts().to_string())

    print("\n[3] Extraindo orientacao do partido presidente por votacao")
    # Cada votacao tem 1 partido presidente. Pra cada (votacao, partido_pres),
    # pegar a orientacao deles
    def get_ori_str(row):
        if row["d_ori_part_sim"] == 1: return "Sim"
        if row["d_ori_part_nao"] == 1: return "Não"
        if row["d_ori_part_obstrucao"] == 1: return "Obstrução"
        if row["d_ori_part_liberado"] == 1: return "Liberado"
        if row["d_ori_part_abstencao"] == 1: return "Abstenção"
        return None

    # Filtrar linhas onde partido_norm == partido_presidente (so' essas vao ter
    # a orientacao do partido do presidente)
    pf["ori_partido_str"] = pf.apply(get_ori_str, axis=1)

    # Subconjunto: deputados do partido do presidente
    presidentes = pf[pf["partido_norm"] == pf["partido_presidente"]].copy()
    print(f"    Obs onde deputado e' do partido do presidente: {len(presidentes):,}")

    # Orientacao por (votacao, partido_pres) — pegar primeira (deve ser unica)
    ori_map = (presidentes.groupby(["idVotacao", "partido_presidente"])["ori_partido_str"]
                          .first().reset_index()
                          .rename(columns={"ori_partido_str": "ori_pres_camara"}))
    print(f"    {len(ori_map):,} (votacao, partido_pres) com orientacao")

    print("\n[4] Merge no painel principal e construcao y_pres_camara_orient")
    out = pf[["idDeputado", "idVotacao", "voto", "data", "idLegislatura",
              "partido_presidente"]].copy()
    out = out.merge(ori_map, on=["idVotacao", "partido_presidente"], how="left")

    # y = 1 se voto bate com orientacao
    # Liberado, Abstencao, NaN -> NaN
    out["y_pres_camara_orient"] = (out["voto"] == out["ori_pres_camara"]).astype(int)
    invalid = out["ori_pres_camara"].isin(["Liberado", "Abstenção"]) | out["ori_pres_camara"].isna()
    out.loc[invalid, "y_pres_camara_orient"] = np.nan

    print("\n[5] Cobertura por sub-periodo (presidente)")
    rows = []
    for partido in ["PMDB", "DEM", "PP"]:
        sub = out[out["partido_presidente"] == partido]
        n_total = len(sub)
        n_valid = sub["y_pres_camara_orient"].notna().sum()
        rows.append({
            "presidente_partido": partido,
            "presidente_nome": {"PMDB": "Cunha", "DEM": "Maia", "PP": "Lira"}[partido],
            "periodo": {
                "PMDB": "2015-02 a 2016-07",
                "DEM": "2016-07 a 2021-02",
                "PP": "2021-02 em diante"
            }[partido],
            "n_obs_total": n_total,
            "n_obs_com_outcome": int(n_valid),
            "pct_cobertura": round(100 * n_valid / n_total, 2) if n_total > 0 else 0,
            "mean_y_pres": round(sub["y_pres_camara_orient"].mean(), 4)
                          if n_valid > 0 else np.nan,
        })
    stats = pd.DataFrame(rows)
    print(stats.to_string(index=False))

    # Comparar com y_gov para ver correlacao
    print("\n[6] Correlacao com y_gov por sub-periodo")
    pf_gov = pd.read_csv(PANEL / "panel_features.csv", sep=";",
                          usecols=["idDeputado", "idVotacao", "alinhamento"], dtype=str)
    pf_gov["alinhamento"] = pd.to_numeric(pf_gov["alinhamento"], errors="coerce")
    out2 = out.merge(pf_gov, on=["idDeputado", "idVotacao"], how="left")

    for partido in ["PMDB", "DEM", "PP"]:
        sub = out2[(out2["partido_presidente"] == partido) &
                   out2["y_pres_camara_orient"].notna() &
                   out2["alinhamento"].notna()]
        if len(sub) == 0: continue
        corr = sub[["y_pres_camara_orient", "alinhamento"]].corr().iloc[0, 1]
        agreement = (sub["y_pres_camara_orient"] == sub["alinhamento"]).mean()
        print(f"  {partido} ({len(sub):,} obs): corr={corr:.4f}, agreement={100*agreement:.1f}%")

    print("\n[7] Saving")
    out_cols = ["idDeputado", "idVotacao", "partido_presidente", "ori_pres_camara",
                "y_pres_camara_orient"]
    out[out_cols].to_csv(PANEL / "panel_y_pres_camara_orient.csv", sep=";", index=False)
    print(f"  saved {PANEL / 'panel_y_pres_camara_orient.csv'}")
    stats.to_csv(RESULTS / "eda_y_pres_camara_orient.csv", sep=";", index=False)
    print(f"  saved {RESULTS / 'eda_y_pres_camara_orient.csv'}")


if __name__ == "__main__":
    main()
