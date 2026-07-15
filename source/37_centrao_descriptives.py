"""
37_centrao_descriptives.py
---------------------------
Tabelas descritivas para a discussao sobre Centrão pos-Lira no paper:
- Alinhamento medio por grupo (Centrão vs não-Centrão) × período (pre/pos Lira)
- Alocacao de emendas (RP-6, Pix, RP-8, RP-9) por grupo × período
- Composição do Centrão pre-2020 vs pos-2020 (filiações)

Outputs:
    results/eda_centrao_alignment.csv
    results/eda_centrao_pork_allocation.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INTERIM = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"

CENTRAO = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE",
           "UNIAO", "PTB", "AVANTE", "PSD", "MDB"}


def main():
    pf = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "siglaPartido", "idLegislatura",
                              "alinhamento", "data", "idVotacao"], dtype=str)
    pf["alinhamento"] = pd.to_numeric(pf["alinhamento"], errors="coerce")
    pf["idLegislatura"] = pd.to_numeric(pf["idLegislatura"])
    pf["data"] = pd.to_datetime(pf["data"])
    pf["idDeputado"] = pf["idDeputado"].astype(str)

    mr = pd.read_csv(INTERIM / "panel_emendas_pre_multi_rp.csv", sep=";",
                     dtype={"idDeputado": str})
    mr["idDeputado"] = mr["idDeputado"].astype(str)
    df = pf.merge(mr[["idDeputado", "idVotacao", "T_rp6_pre60",
                       "T_rp6_pix_pre60", "T_rp8_pre60",
                       "T_rp9_imputed_pre60"]],
                  on=["idDeputado", "idVotacao"], how="left")
    for c in ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60",
              "T_rp9_imputed_pre60"]:
        df[c] = df[c].fillna(0) / 1e6  # R$M

    df["d_centrao"] = df["siglaPartido"].str.upper().str.strip().isin(CENTRAO).astype(int)
    df["pos_lira"] = (df["data"] >= "2021-02-01").astype(int)

    # TABELA 1: alinhamento × grupo × periodo (Leg 56)
    rows = []
    sub = df[df["idLegislatura"] == 56]
    for cen in [0, 1]:
        for pos in [0, 1]:
            cell = sub[(sub["d_centrao"] == cen) & (sub["pos_lira"] == pos)]
            rows.append({
                "centrao": cen,
                "pos_lira": pos,
                "n_obs": len(cell),
                "mean_alinhamento": round(cell["alinhamento"].mean(), 4),
                "T_rp6_M_mean": round(cell["T_rp6_pre60"].mean(), 4),
                "T_pix_M_mean": round(cell["T_rp6_pix_pre60"].mean(), 4),
                "T_rp8_M_mean": round(cell["T_rp8_pre60"].mean(), 4),
                "T_rp9_M_mean": round(cell["T_rp9_imputed_pre60"].mean(), 4),
                "pix_share_of_rp6": round(
                    cell["T_rp6_pix_pre60"].sum() /
                    max(cell["T_rp6_pre60"].sum() + cell["T_rp6_pix_pre60"].sum(), 1e-9),
                    4
                ),
            })
    out = pd.DataFrame(rows)
    out_path = RESULTS / "eda_centrao_alignment.csv"
    out.to_csv(out_path, sep=";", index=False)
    print(f"Saved {out_path}")
    print(out.to_string(index=False))

    # TABELA 2: alinhamento por partido (Centrão) pos-Lira
    print("\n=== Alinhamento por partido Centrão pos-Lira ===")
    cen_post = df[(df["idLegislatura"] == 56) & (df["d_centrao"] == 1) & (df["pos_lira"] == 1)]
    by_party = cen_post.groupby("siglaPartido").agg(
        n_obs=("idDeputado", "count"),
        mean_alinhamento=("alinhamento", "mean"),
        T_rp6_M=("T_rp6_pre60", "mean"),
        T_pix_M=("T_rp6_pix_pre60", "mean"),
        T_rp9_M=("T_rp9_imputed_pre60", "mean"),
    ).round(4).sort_values("n_obs", ascending=False)
    out_path2 = RESULTS / "eda_centrao_by_party.csv"
    by_party.to_csv(out_path2, sep=";")
    print(by_party.to_string())
    print(f"\nSaved {out_path2}")


if __name__ == "__main__":
    main()
