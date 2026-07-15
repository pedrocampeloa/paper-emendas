"""
66_consolidate_proxies_extra.py
--------------------------------
Consolida as 6 proxies extras (Proxy 1-6) num unico painel para uso no paper.

Granularidades:
  Proxy 1 (lag_emp_pgto): nome_norm x ano       -> precisa de map nome->idDeputado
  Proxy 2 (conv_status):  nome_norm x ano       -> idem
  Proxy 3 (tesouro_uf):   siglaUf x ano x mes   -> map para painel via siglaUf+data
  Proxy 4 (rp9_pref):     idDeputado x ano      -> direto
  Proxy 5 (share_total):  ano                   -> direto (broadcast)
  Proxy 6 (cargos):       idDeputado x ano      -> direto

Output:
  dados/interim/panel/panel_proxies_extra.csv (idDeputado x ano x mes com TODAS proxies)
  results/eda_proxies_extra.csv (correlacoes + descritivas)
"""

import logging
import unicodedata
from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
PANEL = REPO / "dados" / "interim" / "panel"
RESULTS = REPO / "paper-emendas" / "results"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("consol")


def norm_name(s):
    if not isinstance(s, str): return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(s.upper().strip().split())


def main():
    log.info("CONSOLIDACAO: 6 proxies extras")

    log.info("[1] Loading painel base (id, UF, ano, mes)")
    pf = pd.read_csv(PANEL / "panel_features.csv", sep=";",
                     usecols=["idDeputado", "siglaUf", "idLegislatura", "data", "nome"],
                     dtype=str, low_memory=False)
    pf["idDeputado"] = pf["idDeputado"].astype(str)
    pf["data"] = pd.to_datetime(pf["data"], errors="coerce")
    pf["ano"] = pf["data"].dt.year
    pf["mes"] = pf["data"].dt.month
    pf["nome_norm"] = pf["nome"].apply(norm_name)
    base = pf[["idDeputado", "siglaUf", "idLegislatura", "ano", "mes", "nome_norm"]].drop_duplicates()
    log.info(f"    {len(base):,} cells base")

    # Map nome_norm -> idDeputado (para proxies 1-2)
    name_to_id = pf.dropna(subset=["nome_norm"]).drop_duplicates(["nome_norm", "idDeputado"])
    name_to_id = name_to_id[["nome_norm", "idDeputado"]]

    log.info("[2] Merging Proxy 1: lag_emp_pgto")
    p1 = pd.read_csv(PANEL / "panel_proxy_lag_emp_pgto.csv", sep=";")
    p1 = p1.merge(name_to_id, on="nome_norm", how="inner")
    p1["ano"] = p1["ano"].astype(int)
    p1_keys = p1[["idDeputado", "ano", "lag_medio_dias", "lag_mediano_dias",
                    "pct_executado_medio", "n_convenios", "vl_empenhado_total", "vl_pago_total"]]
    p1_keys = p1_keys.rename(columns={
        "n_convenios": "p1_n_convenios",
        "vl_empenhado_total": "p1_vl_empenhado",
        "vl_pago_total": "p1_vl_pago",
    })
    base["ano"] = base["ano"].astype("Int64")
    base = base.merge(p1_keys, on=["idDeputado", "ano"], how="left")
    log.info(f"    P1 cobertura: {base['lag_medio_dias'].notna().sum():,} / {len(base):,}")

    log.info("[3] Merging Proxy 2: conv_status")
    p2 = pd.read_csv(PANEL / "panel_proxy_conv_status.csv", sep=";")
    p2 = p2.merge(name_to_id, on="nome_norm", how="inner")
    p2["ano"] = p2["ano"].astype(int)
    p2 = p2[["idDeputado", "ano", "pct_concluido", "pct_em_execucao", "pct_problema",
              "pct_em_analise", "n_total"]].rename(columns={"n_total": "p2_n_conv"})
    base = base.merge(p2, on=["idDeputado", "ano"], how="left")
    log.info(f"    P2 cobertura: {base['pct_concluido'].notna().sum():,}")

    log.info("[4] Merging Proxy 3: tesouro UF mensal")
    p3 = pd.read_csv(PANEL / "panel_proxy_tesouro_uf_mensal.csv", sep=";")
    # Proxy 3 file has 'mes' (portuguese name) and 'mes_num' (int). Use mes_num.
    if "mes_num" in p3.columns:
        p3 = p3.drop(columns=["mes"]).rename(columns={"mes_num": "mes"})
    p3["ano"] = p3["ano"].astype(int)
    p3["mes"] = pd.to_numeric(p3["mes"], errors="coerce").astype("Int64")
    p3_keys = p3[["siglaUf", "ano", "mes", "vl_total", "vl_individual", "vl_bancada", "vl_pix"]]
    p3_keys = p3_keys.rename(columns={
        "vl_total": "p3_vl_uf_total",
        "vl_individual": "p3_vl_uf_indiv",
        "vl_bancada": "p3_vl_uf_banc",
        "vl_pix": "p3_vl_uf_pix",
    })
    base["mes"] = base["mes"].astype("Int64")
    base = base.merge(p3_keys, on=["siglaUf", "ano", "mes"], how="left")
    log.info(f"    P3 cobertura: {base['p3_vl_uf_total'].notna().sum():,}")

    log.info("[5] Merging Proxy 4: RP-9 imputado prefeito")
    p4 = pd.read_csv(PANEL / "panel_proxy_rp9_imputed_prefeito.csv", sep=";",
                     dtype={"idDeputado": str})
    p4["ano"] = p4["ano"].astype(int)
    p4 = p4[["idDeputado", "ano", "vl_rp9_imputed_prefeito"]]
    base = base.merge(p4, on=["idDeputado", "ano"], how="left")
    log.info(f"    P4 cobertura: {(base['vl_rp9_imputed_prefeito'] > 0).sum():,}")

    log.info("[6] Merging Proxy 5: share emendas total (broadcast por ano)")
    p5 = pd.read_csv(PANEL / "panel_proxy_share_emendas_total.csv", sep=";")
    p5 = p5[["ano", "share_emendas_empenhado", "share_individual", "share_bancada",
              "vl_empenhado_total"]].rename(columns={"vl_empenhado_total": "p5_orcamento_total"})
    p5["ano"] = p5["ano"].astype(int)
    base = base.merge(p5, on=["ano"], how="left")
    log.info(f"    P5 cobertura: {base['share_emendas_empenhado'].notna().sum():,}")

    log.info("[7] Merging Proxy 6: cargos")
    p6 = pd.read_csv(PANEL / "panel_proxy_cargos.csv", sep=";",
                     dtype={"idDeputado": str})
    p6["ano"] = p6["ano"].astype(int)
    p6 = p6[["idDeputado", "ano", "n_cargos", "n_tier1", "n_tier2", "n_tier3",
              "n_titular", "n_suplente", "n_relator", "has_mesa", "has_pres_comissao",
              "tier_max"]]
    base = base.merge(p6, on=["idDeputado", "ano"], how="left")
    log.info(f"    P6 cobertura: {base['n_cargos'].notna().sum():,}")

    log.info(f"\n[8] Painel final shape: {base.shape}")

    log.info("[9] Salvando")
    out_path = PANEL / "panel_proxies_extra.csv"
    base.to_csv(out_path, sep=";", index=False)
    log.info(f"    saved {out_path}")

    log.info("\n[10] EDA: cobertura por proxy & correlacoes")
    prox_cols = {
        "P1_lag_medio": "lag_medio_dias",
        "P1_pct_exec": "pct_executado_medio",
        "P2_pct_concluido": "pct_concluido",
        "P2_pct_problema": "pct_problema",
        "P3_vl_uf_total": "p3_vl_uf_total",
        "P3_vl_uf_pix": "p3_vl_uf_pix",
        "P4_rp9_prefeito": "vl_rp9_imputed_prefeito",
        "P5_share_individual": "share_individual",
        "P6_n_cargos": "n_cargos",
        "P6_tier2": "n_tier2",
        "P6_mesa": "has_mesa",
    }
    cov = []
    for lbl, col in prox_cols.items():
        if col not in base.columns:
            cov.append({"proxy": lbl, "n": 0, "pct": 0, "mean": None})
            continue
        s = base[col]
        n_nn = s.notna().sum()
        if pd.api.types.is_numeric_dtype(s):
            mean_pos = s[s > 0].mean() if (s > 0).any() else None
        else:
            mean_pos = None
        cov.append({"proxy": lbl, "n_not_null": int(n_nn),
                    "pct_coverage": round(100 * n_nn / len(base), 2),
                    "mean_positive": mean_pos})
    cov_df = pd.DataFrame(cov)
    print("\nCobertura por proxy:")
    print(cov_df.to_string(index=False))
    cov_df.to_csv(RESULTS / "eda_proxies_extra_coverage.csv", sep=";", index=False)

    # Correlacoes entre proxies numericas (Leg 56)
    log.info("\n[11] Correlacoes (Leg 56, 2019-2022)")
    sub = base[(base["idLegislatura"] == "56") &
                (base["ano"] >= 2019) & (base["ano"] <= 2022)].copy()
    sub_num = sub[[c for c in prox_cols.values() if c in sub.columns and
                    pd.api.types.is_numeric_dtype(sub[c])]]
    corr = sub_num.corr()
    print("\nCorrelacao Leg 56:")
    print(corr.round(2).to_string())
    corr.to_csv(RESULTS / "eda_proxies_extra_corr_leg56.csv", sep=";")

    log.info("\n[12] Painel pronto para uso no DML futuro")
    log.info(f"    Use: pd.read_csv('{out_path}', sep=';')")


if __name__ == "__main__":
    main()
