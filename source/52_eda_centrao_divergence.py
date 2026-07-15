"""
52_eda_centrao_divergence.py
-----------------------------
Investiga divergencia entre orientacoes dos partidos do Centrao por votacao
e propoe variaveis explicativas alternativas para outcome ex-ante.

Pergunta 1: Com que frequencia os 9 partidos do Centrao divergem entre si?
  - Se quase sempre unanimes: usar maioria (ou qualquer partido)
  - Se divergem: precisamos discutir qual partido pivotal usar

Pergunta 2: Quais sao as alternativas naturais?
  a) Maioria simples (atual): >= 5 partidos com mesma orientacao
  b) Maioria qualificada: >= 6 partidos
  c) PP isolado (partido do Lira)
  d) PL isolado (maior partido do Centrao na Leg 56)
  e) Orientacao do partido do deputado (d_ori_part_*) condicionada a ser Centrao

Pergunta 3: Como cada metrica se compara em cobertura e correlacao com y_gov?

Outputs:
  results/eda_centrao_divergence.csv  — descritivas
  results/eda_centrao_alt_outcomes.csv — comparacao das 5 alternativas
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
    print("[1] Loading panel")
    pf = pd.read_csv(PANEL / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "idVotacao", "siglaPartido", "voto",
                              "d_ori_part_sim", "d_ori_part_nao",
                              "d_ori_part_obstrucao", "d_ori_part_liberado",
                              "d_ori_part_abstencao",
                              "d_ori_gov_sim", "d_ori_gov_nao",
                              "alinhamento", "idLegislatura"],
                     dtype=str, low_memory=False)
    for c in ["d_ori_part_sim", "d_ori_part_nao", "d_ori_part_obstrucao",
              "d_ori_part_liberado", "d_ori_part_abstencao",
              "d_ori_gov_sim", "d_ori_gov_nao", "alinhamento"]:
        pf[c] = pd.to_numeric(pf[c], errors="coerce")

    pf["partido_norm"] = pf["siglaPartido"].astype(str).str.upper().str.strip()
    pf["d_centrao"] = pf["partido_norm"].isin(CENTRAO_PARTIES).astype(int)
    pf["idLegislatura"] = pd.to_numeric(pf["idLegislatura"])

    # ============================================================
    # 1. Orientacao consolidada por (partido, votacao)
    # ============================================================
    print("\n[2] Orientacao por (partido, votacao)")

    # Para cada deputado, "orientacao" = qual a posicao oficial do seu partido na votacao
    # Vamos transformar em string para facilitar:
    def get_ori(row):
        if row["d_ori_part_sim"] == 1: return "Sim"
        if row["d_ori_part_nao"] == 1: return "Não"
        if row["d_ori_part_obstrucao"] == 1: return "Obstrução"
        if row["d_ori_part_liberado"] == 1: return "Liberado"
        if row["d_ori_part_abstencao"] == 1: return "Abstenção"
        return None
    pf["orientacao_partido"] = pf.apply(get_ori, axis=1)

    # Tabela (partido, votacao) -> orientacao
    cen_ori = (pf[pf["d_centrao"] == 1]
                .groupby(["idVotacao", "partido_norm"])["orientacao_partido"]
                .first().reset_index())
    print(f"    pares (partido, votacao): {len(cen_ori):,}")

    # ============================================================
    # 2. Quantos partidos divergem em cada votacao?
    # ============================================================
    print("\n[3] Divergencia entre partidos do Centrao")
    by_votacao = cen_ori.groupby("idVotacao").agg(
        n_partidos=("partido_norm", "count"),
        n_orientacoes_distintas=("orientacao_partido", lambda s: s.dropna().nunique()),
        n_sim=("orientacao_partido", lambda s: (s == "Sim").sum()),
        n_nao=("orientacao_partido", lambda s: (s == "Não").sum()),
        n_obs=("orientacao_partido", lambda s: (s == "Obstrução").sum()),
        n_lib=("orientacao_partido", lambda s: (s == "Liberado").sum()),
        n_abst=("orientacao_partido", lambda s: (s == "Abstenção").sum()),
        n_null=("orientacao_partido", lambda s: s.isna().sum()),
    ).reset_index()

    print(f"    Total votacoes com pelo menos 1 partido do Centrao: {len(by_votacao):,}")
    print()
    print("    Distribuição de orientações distintas entre partidos do Centrao:")
    print(by_votacao["n_orientacoes_distintas"].value_counts().sort_index().to_string())
    print()
    print("    Em quantas votações há divergência (>1 orientação válida)?")
    div = (by_votacao["n_orientacoes_distintas"] >= 2).sum()
    print(f"      {div:,} de {len(by_votacao):,} ({100*div/len(by_votacao):.1f}%)")

    # ============================================================
    # 3. Tipos de divergência
    # ============================================================
    print("\n[4] Tipos de divergencia")
    by_votacao["unanime_sim"] = (by_votacao["n_sim"] >= 6) & (by_votacao["n_nao"] == 0) & (by_votacao["n_obs"] == 0)
    by_votacao["unanime_nao"] = (by_votacao["n_nao"] >= 6) & (by_votacao["n_sim"] == 0) & (by_votacao["n_obs"] == 0)
    by_votacao["divergencia_sim_nao"] = (by_votacao["n_sim"] >= 1) & (by_votacao["n_nao"] >= 1)
    by_votacao["liberados_majoritarios"] = by_votacao["n_lib"] >= 5

    print(f"    Unânime Sim (≥6 sim, 0 não, 0 obstrução): {by_votacao['unanime_sim'].sum():,}")
    print(f"    Unânime Não (≥6 não, 0 sim, 0 obstrução): {by_votacao['unanime_nao'].sum():,}")
    print(f"    Divergência Sim/Não (algum sim E algum não): {by_votacao['divergencia_sim_nao'].sum():,}")
    print(f"    Liberados majoritários: {by_votacao['liberados_majoritarios'].sum():,}")

    by_votacao.to_csv(RESULTS / "eda_centrao_divergence.csv", sep=";", index=False)
    print(f"  saved {RESULTS / 'eda_centrao_divergence.csv'}")

    # ============================================================
    # 4. Alternativas de y_centrao
    # ============================================================
    print("\n[5] Construindo 5 alternativas de y_centrao")

    # (a) Maioria simples >=5 (atual)
    def maioria(row, threshold=5):
        if row["n_sim"] >= threshold: return "Sim"
        if row["n_nao"] >= threshold: return "Não"
        if row["n_obs"] >= threshold: return "Obstrução"
        return np.nan

    by_votacao["ori_centrao_maioria5"] = by_votacao.apply(lambda r: maioria(r, 5), axis=1)
    by_votacao["ori_centrao_maioria6"] = by_votacao.apply(lambda r: maioria(r, 6), axis=1)
    by_votacao["ori_centrao_maioria7"] = by_votacao.apply(lambda r: maioria(r, 7), axis=1)

    # (b/c/d) PP, PL, MDB isolados
    pp_ori = cen_ori[cen_ori["partido_norm"] == "PP"][["idVotacao", "orientacao_partido"]].rename(columns={"orientacao_partido": "ori_pp"})
    pl_ori = cen_ori[cen_ori["partido_norm"] == "PL"][["idVotacao", "orientacao_partido"]].rename(columns={"orientacao_partido": "ori_pl"})
    mdb_ori = cen_ori[cen_ori["partido_norm"] == "MDB"][["idVotacao", "orientacao_partido"]].rename(columns={"orientacao_partido": "ori_mdb"})

    by_votacao = by_votacao.merge(pp_ori, on="idVotacao", how="left")
    by_votacao = by_votacao.merge(pl_ori, on="idVotacao", how="left")
    by_votacao = by_votacao.merge(mdb_ori, on="idVotacao", how="left")

    # Merge no painel principal
    pf2 = pf[["idDeputado", "idVotacao", "voto", "alinhamento", "idLegislatura"]].copy()
    pf2 = pf2.merge(by_votacao[["idVotacao", "ori_centrao_maioria5", "ori_centrao_maioria6",
                                  "ori_centrao_maioria7", "ori_pp", "ori_pl", "ori_mdb"]],
                    on="idVotacao", how="left")

    # Construir outcomes
    alternatives = {
        "y_cent_m5": "ori_centrao_maioria5",
        "y_cent_m6": "ori_centrao_maioria6",
        "y_cent_m7": "ori_centrao_maioria7",
        "y_cent_pp": "ori_pp",
        "y_cent_pl": "ori_pl",
        "y_cent_mdb": "ori_mdb",
    }
    for outcome, ori_col in alternatives.items():
        pf2[outcome] = (pf2["voto"] == pf2[ori_col]).astype(int)
        pf2.loc[pf2[ori_col].isna() | pf2[ori_col].isin(["Liberado", "Abstenção"]), outcome] = np.nan

    # ============================================================
    # 5. Tabela comparativa
    # ============================================================
    print("\n[6] Tabela comparativa das alternativas")
    rows = []
    for outcome, ori_col in alternatives.items():
        for leg in [55, 56]:
            sub = pf2[pf2["idLegislatura"] == leg]
            n_total = len(sub)
            n_with = sub[outcome].notna().sum()
            mean_y = sub[outcome].mean()
            corr_with_gov = sub[[outcome, "alinhamento"]].corr().iloc[0, 1]
            rows.append({
                "outcome": outcome,
                "definicao": ori_col,
                "leg": leg,
                "n_total": n_total,
                "n_with_outcome": int(n_with),
                "pct_cobertura": round(100 * n_with / n_total, 2),
                "mean_outcome": round(mean_y, 4),
                "corr_y_gov": round(corr_with_gov, 4),
            })

    comp = pd.DataFrame(rows)
    comp.to_csv(RESULTS / "eda_centrao_alt_outcomes.csv", sep=";", index=False)
    print(f"  saved {RESULTS / 'eda_centrao_alt_outcomes.csv'}")
    print()
    print(comp.to_string(index=False))


if __name__ == "__main__":
    main()
