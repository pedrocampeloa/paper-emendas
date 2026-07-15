"""
35_eda_multi_rp_cross.py
-------------------------
EDA descritivo cruzado entre as variaveis novas (RP-6, RP-6 Pix, RP-8,
RP-9 imputed) e os proxies de orcamento secreto, em relacao ao painel
principal (alinhamento, partidos, coalizao).

Outputs:
    paper-emendas/results/eda_corr_rps_alignment.csv  -- correlacoes
    paper-emendas/results/eda_distrib_rps_partido.csv -- distribuicao por partido
    paper-emendas/results/eda_overlap_rp6_rp9.csv     -- sobreposicao
    paper-emendas/docs/figs/eda_corr_matrix.pdf
    paper-emendas/docs/figs/eda_distrib_partidos.pdf
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

REPO = Path(__file__).resolve().parents[2]
INTERIM = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"
FIGS = REPO / "paper-emendas" / "docs" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)


def main():
    print("\n[1] Loading panel and multi-RP files")
    pf = pd.read_csv(INTERIM / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "idVotacao", "siglaPartido",
                              "siglaUf", "idLegislatura", "alinhamento", "y"],
                     dtype=str, low_memory=False)
    pf["alinhamento"] = pd.to_numeric(pf["alinhamento"], errors="coerce")
    pf["idLegislatura"] = pd.to_numeric(pf["idLegislatura"], errors="coerce").astype("Int64")
    pf["ano"] = pd.to_numeric(pf["y"], errors="coerce").astype("Int64")

    mr = pd.read_csv(INTERIM / "panel_emendas_pre_multi_rp.csv", sep=";", low_memory=False)
    mr["idDeputado"] = mr["idDeputado"].astype(str)

    px = pd.read_csv(INTERIM / "panel_secret_budget_proxies.csv", sep=";", low_memory=False)
    px["idDeputado"] = px["idDeputado"].astype(str)

    df = pf.merge(mr.drop(columns=["data", "idLegislatura"], errors="ignore"),
                  on=["idDeputado", "idVotacao"], how="inner")
    df = df.merge(px.drop(columns=["data", "idLegislatura"], errors="ignore"),
                  on=["idDeputado", "idVotacao"], how="inner")
    df = df.dropna(subset=["alinhamento"])
    print(f"    Merged panel: {len(df):,} rows")

    # ---------------------------------------------------------------
    # TABLE 1 -- correlations between RPs, proxies, and alignment
    # ---------------------------------------------------------------
    print("\n[2] Computing correlations")
    rp_cols = ["T_rp6_pre60", "T_rp6_pix_pre60", "T_rp8_pre60", "T_rp9_imputed_pre60"]
    proxy_cols = ["share_pork_opaco", "share_rp9", "share_pix",
                  "d_rp9_solicitante", "n_apoiamentos_opaco"]
    target = "alinhamento"

    rows = []
    for leg in [55, 56]:
        sub = df[df["idLegislatura"] == leg]
        for col in rp_cols + proxy_cols:
            if col not in sub.columns:
                continue
            valid = sub.dropna(subset=[col, target])
            if len(valid) == 0:
                continue
            corr = valid[[col, target]].corr().iloc[0, 1]
            rows.append({
                "legis": leg, "metric": col,
                "corr_with_alinhamento": round(corr, 4),
                "mean": round(valid[col].mean(), 4),
                "mean_when_aligned": round(valid[valid[target] == 1][col].mean(), 4),
                "mean_when_unaligned": round(valid[valid[target] == 0][col].mean(), 4),
                "n_obs": len(valid),
            })
    corr_df = pd.DataFrame(rows)
    out1 = RESULTS / "eda_corr_rps_alignment.csv"
    corr_df.to_csv(out1, sep=";", index=False)
    print(f"    {out1}")
    print(corr_df.to_string(index=False))

    # ---------------------------------------------------------------
    # TABLE 2 -- distribution by partido (top 15)
    # ---------------------------------------------------------------
    print("\n[3] Distribution by party")
    top_partidos = df["siglaPartido"].value_counts().head(15).index.tolist()
    rows = []
    for leg in [55, 56]:
        sub = df[df["idLegislatura"] == leg]
        for partido in top_partidos:
            ssub = sub[sub["siglaPartido"] == partido]
            if len(ssub) < 100:
                continue
            for col in rp_cols + ["d_rp9_solicitante", "share_pork_opaco"]:
                rows.append({
                    "legis": leg, "partido": partido,
                    "metric": col,
                    "n_dep_obs": len(ssub),
                    "mean_value_M": round(ssub[col].mean() / 1e6, 3) if "T_" in col else round(ssub[col].mean(), 4),
                    "pct_positive": round(100 * (ssub[col] > 0).mean(), 2),
                    "mean_alinhamento": round(ssub["alinhamento"].mean(), 3),
                })
    dist_df = pd.DataFrame(rows)
    out2 = RESULTS / "eda_distrib_rps_partido.csv"
    dist_df.to_csv(out2, sep=";", index=False)
    print(f"    {out2}: {len(dist_df)} rows")

    # ---------------------------------------------------------------
    # TABLE 3 -- overlap RP6 x RP9_imputed (focal interest)
    # ---------------------------------------------------------------
    print("\n[4] Overlap RP6 x RP9_imputed")
    sub56 = df[df["idLegislatura"] == 56].copy()
    sub56["has_rp6"] = (sub56["T_rp6_pre60"] > 0).astype(int)
    sub56["has_rp9"] = (sub56["d_rp9_solicitante"] == 1).astype(int)
    crosstab = pd.crosstab(sub56["has_rp6"], sub56["has_rp9"], margins=True, normalize="all") * 100
    print("Cross-tab RP-6 x RP-9 (% of Leg 56 deputy-votes):")
    print(crosstab.round(2))

    # Alinhamento medio por celula
    align_table = pd.pivot_table(
        sub56, values="alinhamento",
        index="has_rp6", columns="has_rp9",
        aggfunc=["mean", "count"]
    ).round(4)
    print("\nMean alignment by RP-6 x RP-9 cell:")
    print(align_table)

    # Salvar
    overlap_rows = []
    for r in [0, 1]:
        for c in [0, 1]:
            cell = sub56[(sub56["has_rp6"] == r) & (sub56["has_rp9"] == c)]
            overlap_rows.append({
                "has_rp6": r, "has_rp9_imputed": c,
                "n_obs": len(cell),
                "pct_of_leg56": round(100 * len(cell) / len(sub56), 2),
                "mean_alinhamento": round(cell["alinhamento"].mean(), 4) if len(cell) > 0 else None,
                "mean_T_rp6_M": round(cell["T_rp6_pre60"].mean() / 1e6, 3),
            })
    overlap_df = pd.DataFrame(overlap_rows)
    out3 = RESULTS / "eda_overlap_rp6_rp9.csv"
    overlap_df.to_csv(out3, sep=";", index=False)
    print(f"\n    {out3}")
    print(overlap_df.to_string(index=False))

    # ---------------------------------------------------------------
    # FIGURE 1 -- correlation matrix
    # ---------------------------------------------------------------
    print("\n[5] Plotting correlation matrix")
    sub = df.copy()
    sub["T_rp6_M"] = sub["T_rp6_pre60"] / 1e6
    sub["T_rp6_pix_M"] = sub["T_rp6_pix_pre60"] / 1e6
    sub["T_rp8_M"] = sub["T_rp8_pre60"] / 1e6
    sub["T_rp9_M"] = sub["T_rp9_imputed_pre60"] / 1e6
    cols = ["T_rp6_M", "T_rp6_pix_M", "T_rp8_M", "T_rp9_M",
            "share_pork_opaco", "share_pix",
            "n_apoiamentos_opaco", "alinhamento"]
    corr = sub[cols].corr()
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-0.5, vmax=0.5)
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(cols)
    for i in range(len(cols)):
        for j in range(len(cols)):
            v = corr.iloc[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color="white" if abs(v) > 0.3 else "black", fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Correlation matrix: amendment modalities, proxies, alignment")
    plt.tight_layout()
    fig_path = FIGS / "eda_corr_matrix.pdf"
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"    {fig_path}")

    # ---------------------------------------------------------------
    # FIGURE 2 -- mean values by partido (Leg 56)
    # ---------------------------------------------------------------
    print("\n[6] Plotting partido distribution (Leg 56)")
    sub56 = df[df["idLegislatura"] == 56]
    by_party = sub56.groupby("siglaPartido").agg(
        n_obs=("idDeputado", "count"),
        T_rp6_M=("T_rp6_pre60", lambda x: x.mean() / 1e6),
        T_rp6_pix_M=("T_rp6_pix_pre60", lambda x: x.mean() / 1e6),
        T_rp8_M=("T_rp8_pre60", lambda x: x.mean() / 1e6),
        T_rp9_M=("T_rp9_imputed_pre60", lambda x: x.mean() / 1e6),
        share_pork_opaco=("share_pork_opaco", "mean"),
        alinhamento=("alinhamento", "mean"),
    ).query("n_obs > 1000").sort_values("T_rp6_M", ascending=False).head(20)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    by_party[["T_rp6_M", "T_rp6_pix_M", "T_rp8_M", "T_rp9_M"]].plot.bar(
        ax=axes[0], stacked=True, alpha=0.85)
    axes[0].set_title("Mean amendment value per deputy-vote, by party (Leg 56)")
    axes[0].set_ylabel("R\\$ millions (60-day pre-vote window)")
    axes[0].set_xlabel("")
    axes[0].legend(["RP-6", "RP-6 Pix", "RP-8", "RP-9 imputed"], loc="upper right")
    axes[0].grid(True, alpha=0.3)

    by_party["share_pork_opaco"].plot.bar(ax=axes[1], color="C3")
    axes[1].set_title("Share of opaque pork (RP-8 + RP-9) by party (Leg 56)")
    axes[1].set_ylabel("Share")
    axes[1].set_xlabel("")
    axes[1].yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    fig_path = FIGS / "eda_distrib_partidos.pdf"
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()
    print(f"    {fig_path}")


if __name__ == "__main__":
    main()
    print("\nDone.")
