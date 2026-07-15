"""
51_build_y_centrao_orient.py
-----------------------------
Constroi y_centrao_orient (ex-ante, CORRIGIDO) e salva ao painel.

ERRO ANTERIOR: y_centrao construido via voto majoritario do bloco Centrao
(ex-post) tem endogeneidade — o proprio voto do deputado contribui para a
"maioria", e pork pode afetar tanto voto i quanto maioria do bloco.

VERSAO CORRIGIDA: y_centrao_orient usa as ORIENTACOES dos partidos do
Centrao, que sao anunciadas ANTES da votacao (ex-ante), espelhando como
y_gov funciona com d_ori_gov_*.

Definicao:
  Para cada votacao t, computar a maioria das orientacoes (sim/nao) dos 9
  partidos do Centrao. Empate (3-3 ou mais) classifica como "sem orientacao"
  → NaN.
  y_centrao_orient[i,t] = 1 se voto[i,t] == orientacao_centrao_majoritaria[t]
                          else 0
                          else NaN se orientacao = liberado / empate / vazia

Outputs:
  dados/interim/panel/panel_y_centrao_orient.csv  (idDeputado, idVotacao, y_centrao_orient)
  paper-emendas/results/eda_y_centrao_orient.csv  (descritivas)

Para usar nos modelos: como y_centrao no script 50_, mas com a coluna corrigida.
"""

import pandas as pd
import numpy as np
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PANEL = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"

CENTRAO_PARTIES = {"PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE",
                   "UNIAO", "PTB", "AVANTE", "PSD", "MDB"}


def main():
    print("[1] Loading panel_features (apenas cols necessarias)")
    pf = pd.read_csv(PANEL / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "idVotacao", "siglaPartido", "voto",
                              "d_ori_part_sim", "d_ori_part_nao",
                              "d_ori_part_obstrucao", "d_ori_part_liberado",
                              "d_ori_part_abstencao", "idLegislatura"],
                     dtype=str, low_memory=False)
    print(f"    {len(pf):,} rows")
    for c in ["d_ori_part_sim", "d_ori_part_nao",
              "d_ori_part_obstrucao", "d_ori_part_liberado",
              "d_ori_part_abstencao"]:
        pf[c] = pd.to_numeric(pf[c], errors="coerce")

    pf["partido_norm"] = pf["siglaPartido"].astype(str).str.upper().str.strip()
    pf["d_centrao"] = pf["partido_norm"].isin(CENTRAO_PARTIES).astype(int)

    print("\n[2] Extraindo orientacao unica por (partido, votacao)")
    # Para cada partido x votacao, a orientacao e' unica (validado em §1).
    # Pegar o primeiro registro (qualquer deputado do partido na votacao serve).
    cen = pf[pf["d_centrao"] == 1].copy()
    ori_centrao = (cen.groupby(["idVotacao", "partido_norm"])
                      .agg({"d_ori_part_sim": "first",
                            "d_ori_part_nao": "first",
                            "d_ori_part_obstrucao": "first",
                            "d_ori_part_liberado": "first",
                            "d_ori_part_abstencao": "first"})
                      .reset_index())
    print(f"    {len(ori_centrao):,} pares (partido, votacao) do Centrao")

    print("\n[3] Maioria das orientacoes dos partidos do Centrao por votacao")
    # Para cada votacao, contar quantos partidos do Centrao orientaram Sim/Nao/Obstrucao
    # Se tiver liberado ou abstencao majoritaria, o paper interpreta como "sem orientacao"
    votacao_summary = (ori_centrao.groupby("idVotacao")
                        .agg(n_partidos=("partido_norm", "count"),
                             n_sim=("d_ori_part_sim", "sum"),
                             n_nao=("d_ori_part_nao", "sum"),
                             n_obstrucao=("d_ori_part_obstrucao", "sum"),
                             n_liberado=("d_ori_part_liberado", "sum"),
                             n_abstencao=("d_ori_part_abstencao", "sum"))
                        .reset_index())

    # Definir orientacao consolidada: maioria dos partidos do Centrao
    # Estrategia: maior contagem entre {sim, nao, obstrucao}
    def consolida(row):
        sim, nao, obs = row["n_sim"], row["n_nao"], row["n_obstrucao"]
        max_count = max(sim, nao, obs)
        if max_count == 0:
            return np.nan
        # Empate -> NaN
        equals = (sim == max_count) + (nao == max_count) + (obs == max_count)
        if equals > 1:
            return np.nan
        if sim == max_count:
            return "Sim"
        if nao == max_count:
            return "Não"
        return "Obstrução"

    votacao_summary["orientacao_centrao"] = votacao_summary.apply(consolida, axis=1)
    print(f"    Votacoes com orientacao Centrao: {votacao_summary['orientacao_centrao'].notna().sum():,} / {len(votacao_summary):,}")
    print(f"    Distribuicao: {votacao_summary['orientacao_centrao'].value_counts(dropna=False).to_dict()}")

    print("\n[4] Merge com painel principal e construcao do outcome")
    out = pf[["idDeputado", "idVotacao", "voto", "idLegislatura"]].merge(
        votacao_summary[["idVotacao", "orientacao_centrao"]],
        on="idVotacao", how="left"
    )
    out["y_centrao_orient"] = (out["voto"] == out["orientacao_centrao"]).astype(int)
    out.loc[out["orientacao_centrao"].isna(), "y_centrao_orient"] = np.nan

    print(f"    Outcome non-null: {out['y_centrao_orient'].notna().sum():,} / {len(out):,}")
    print(f"    Leg 55: mean = {out[out['idLegislatura']=='55']['y_centrao_orient'].mean():.4f}")
    print(f"    Leg 56: mean = {out[out['idLegislatura']=='56']['y_centrao_orient'].mean():.4f}")

    # Comparar com y_gov para sanity
    pf_short = pd.read_csv(PANEL / "panel_features.csv", sep=";",
                            usecols=["idDeputado", "idVotacao", "alinhamento"],
                            dtype=str, low_memory=False)
    pf_short["alinhamento"] = pd.to_numeric(pf_short["alinhamento"], errors="coerce")
    out2 = out.merge(pf_short, on=["idDeputado", "idVotacao"], how="left")
    print(f"\n[5] Correlacao com y_gov: {out2[['y_centrao_orient','alinhamento']].corr().iloc[0,1]:.4f}")

    cross = pd.crosstab(out2['alinhamento'], out2['y_centrao_orient'], margins=True)
    print(f"\nCross-tab y_gov × y_centrao_orient:")
    print(cross.to_string())

    print("\n[6] Salvando")
    out_path = PANEL / "panel_y_centrao_orient.csv"
    out[["idDeputado", "idVotacao", "y_centrao_orient", "orientacao_centrao"]].to_csv(
        out_path, sep=";", index=False)
    print(f"  {out_path}")

    # Estatisticas para o STATE_OF_PLAY
    stats = []
    for leg in [55, 56]:
        sub = out[out["idLegislatura"] == str(leg)]
        stats.append({
            "leg": leg,
            "n_obs_total": len(sub),
            "n_with_y_centrao_orient": int(sub["y_centrao_orient"].notna().sum()),
            "pct_with_orient": round(100 * sub["y_centrao_orient"].notna().mean(), 1),
            "mean_y_centrao_orient": round(sub["y_centrao_orient"].mean(), 4),
        })
    stats_df = pd.DataFrame(stats)
    stats_df.to_csv(RESULTS / "eda_y_centrao_orient.csv", sep=";", index=False)
    print(f"  {RESULTS / 'eda_y_centrao_orient.csv'}")
    print()
    print(stats_df.to_string(index=False))


if __name__ == "__main__":
    main()
