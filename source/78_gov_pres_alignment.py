"""
78_gov_pres_alignment.py
-------------------------
Descriptive statistic: for each roll-call in the sample, compute whether
the Executive's stated voting orientation coincides with the Chamber
president's party stated voting orientation. Report the coincidence rate
by sub-period (Maia leg55, Maia leg56, Lira leg56).

Hypothesis: post-Lira the Executive's orientation and Lira's orientation
converge much more than under Maia, consistent with the Bolsonaro-Centrão
implicit deal that transferred procedural control to Lira and made the two
principals de-facto coordinated.

Output: printed table + saved CSV results/gov_pres_orientation_coincidence.csv
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import _config as C

INTERIM = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
CUT_LIRA = pd.Timestamp("2021-02-01")
CUT_MAIA_55 = pd.Timestamp("2016-07-14")


def get_partido_presidente(data):
    """Return the party of the Chamber president as of the given date."""
    if data < pd.Timestamp("2016-07-14"):
        return "PMDB"   # Cunha
    if data < CUT_LIRA:
        return "DEM"    # Maia
    return "PP"         # Lira


def main():
    print("Loading panel_features to get vote orientations")
    pf = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                     usecols=["idVotacao", "siglaPartido",
                              "d_ori_gov_sim", "d_ori_gov_nao",
                              "d_ori_gov_obstrucao",
                              "d_ori_part_sim", "d_ori_part_nao",
                              "d_ori_part_obstrucao",
                              "d_ori_part_liberado",
                              "d_ori_part_abstencao"],
                     dtype=str, low_memory=False)
    for c in pf.columns:
        if c.startswith("d_"):
            pf[c] = pd.to_numeric(pf[c], errors="coerce")
    pf["partido_norm"] = pf["siglaPartido"].astype(str).str.upper().str.strip()

    # Executive orientation string
    def get_gov_str(row):
        if row["d_ori_gov_sim"] == 1: return "Sim"
        if row["d_ori_gov_nao"] == 1: return "Não"
        if row["d_ori_gov_obstrucao"] == 1: return "Obstrução"
        return None
    pf["ori_gov"] = pf.apply(get_gov_str, axis=1)

    # Party orientation string
    def get_part_str(row):
        if row["d_ori_part_sim"] == 1: return "Sim"
        if row["d_ori_part_nao"] == 1: return "Não"
        if row["d_ori_part_obstrucao"] == 1: return "Obstrução"
        if row["d_ori_part_liberado"] == 1: return "Liberado"
        if row["d_ori_part_abstencao"] == 1: return "Abstenção"
        return None
    pf["ori_part"] = pf.apply(get_part_str, axis=1)

    # Reduce to one row per vote
    votes = pf[["idVotacao", "ori_gov"]].drop_duplicates(subset="idVotacao")
    print(f"votes with Executive orientation: {votes['ori_gov'].notna().sum():,} / {len(votes):,}")

    # Load votes' dates
    print("Loading votes' dates from panel_features (unique votes)")
    dates = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                        usecols=["idVotacao", "data", "idLegislatura"],
                        dtype=str, low_memory=False)
    dates = dates.drop_duplicates(subset="idVotacao")
    dates["data"] = pd.to_datetime(dates["data"])
    dates["idLegislatura"] = pd.to_numeric(dates["idLegislatura"], errors="coerce")

    votes = votes.merge(dates, on="idVotacao", how="left")
    votes["partido_presidente"] = votes["data"].apply(get_partido_presidente)

    # For each vote, look up the Chamber-president party's orientation
    party_ori = pf[["idVotacao", "partido_norm", "ori_part"]].drop_duplicates(
        subset=["idVotacao", "partido_norm"])
    votes = votes.merge(party_ori,
                          left_on=["idVotacao", "partido_presidente"],
                          right_on=["idVotacao", "partido_norm"],
                          how="left").rename(columns={"ori_part": "ori_pres_camara"})

    # Filter: both orientations must be substantive (Sim / Não / Obstrução)
    valid = {"Sim", "Não", "Obstrução"}
    v = votes[votes["ori_gov"].isin(valid) & votes["ori_pres_camara"].isin(valid)].copy()
    v["coincide"] = (v["ori_gov"] == v["ori_pres_camara"]).astype(int)

    # Also test: are Yes/No both substantive but ignore Obstruction?
    v_yn = v[v["ori_gov"].isin({"Sim", "Não"}) & v["ori_pres_camara"].isin({"Sim", "Não"})].copy()
    v_yn["coincide_yn"] = (v_yn["ori_gov"] == v_yn["ori_pres_camara"]).astype(int)

    def summarize(df, sub_name, mask, col="coincide"):
        s = df[mask]
        if len(s) == 0:
            return None
        return {
            "sub_period": sub_name,
            "n_votes": len(s),
            "coincidence_pct": round(100 * s[col].mean(), 2),
        }

    rows = []
    for sub_name, mask_v in [
        ("Leg55_Maia (2016-07 to 2018)",
         (v["idLegislatura"] == 55) & (v["data"] >= CUT_MAIA_55)),
        ("Leg56_Maia (2019-01 to 2021-01)",
         (v["idLegislatura"] == 56) & (v["data"] < CUT_LIRA)),
        ("Leg56_Lira (2021-02 to 2022-12)",
         (v["idLegislatura"] == 56) & (v["data"] >= CUT_LIRA)),
    ]:
        r = summarize(v, sub_name, mask_v)
        if r:
            rows.append(r)

    out = pd.DataFrame(rows)
    print("\n=== Coincidence between Executive orientation and Chamber-president party orientation ===\n")
    print(out.to_string(index=False))
    out.to_csv(RESULTS / "gov_pres_orientation_coincidence.csv",
                sep=";", index=False)

    # Yes/No only variant for comparison
    print("\n=== Restricted to Yes/No orientations only ===\n")
    rows_yn = []
    for sub_name, mask_v in [
        ("Leg55_Maia (2016-07 to 2018)",
         (v_yn["idLegislatura"] == 55) & (v_yn["data"] >= CUT_MAIA_55)),
        ("Leg56_Maia (2019-01 to 2021-01)",
         (v_yn["idLegislatura"] == 56) & (v_yn["data"] < CUT_LIRA)),
        ("Leg56_Lira (2021-02 to 2022-12)",
         (v_yn["idLegislatura"] == 56) & (v_yn["data"] >= CUT_LIRA)),
    ]:
        r = summarize(v_yn, sub_name, mask_v, col="coincide_yn")
        if r:
            rows_yn.append(r)
    print(pd.DataFrame(rows_yn).to_string(index=False))


if __name__ == "__main__":
    main()
