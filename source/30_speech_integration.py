# -*- coding: utf-8 -*-
"""
30_speech_integration.py — Integração com paper-discursos
==============================================================
Usa sentiment scores de discursos para construir 3 análises:

(A) Heterogeneidade por anti-gov stance:
    Para cada deputado, calcular média rolling de anti_gov_score nos
    últimos 90 dias antes do voto. Dividir em terciles. Efeito de emenda
    é diferente entre quem fala mal vs bem do governo?

(B) Polarização retórica por mês:
    Variância dos sentiment scores entre coalizão e oposição por mês.
    Comparar com polarização de voto (R2.8).

(C) Mediação retórica:
    A relação emenda → voto é mediada por "tom retórico" do deputado?

Output:
  results/speech_integration.csv
  data_pipeline/outputs/panel/speech_features.csv (intermediário)
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils_v2 as U2


SPEECH_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/dados/interim")


def build_speech_features(panel: pd.DataFrame, log) -> pd.DataFrame:
    """
    Para cada (deputado, data), calcular médias rolling de:
      - anti_gov_score (últimos 90d antes do voto)
      - pt_score (sentiment BERTimbau)
      - xlm_score (sentiment XLM-RoBERTa)
    """
    log.info("loading speech NLI scores")
    nli = pd.read_csv(SPEECH_DIR / "model_anti_gov_nli.csv", sep=";",
                        usecols=["id_deputado", "dataHoraInicio",
                                  "anti_gov_score", "pro_gov_score",
                                  "neutral_gov_score"])
    nli["dataHoraInicio"] = pd.to_datetime(nli["dataHoraInicio"],
                                              errors="coerce")
    nli = nli.dropna(subset=["dataHoraInicio", "id_deputado"])
    nli["id_deputado"] = nli["id_deputado"].astype(int)
    log.info("  NLI: %d speeches", len(nli))

    log.info("loading speech sentiment (pt + xlm)")
    pt = pd.read_csv(SPEECH_DIR / "model_speech_sentiment.csv", sep=";",
                       usecols=["id_deputado", "dataHoraInicio", "pt_score"])
    pt["dataHoraInicio"] = pd.to_datetime(pt["dataHoraInicio"], errors="coerce")
    pt = pt.dropna(subset=["dataHoraInicio", "id_deputado", "pt_score"])
    pt["id_deputado"] = pt["id_deputado"].astype(int)

    xlm = pd.read_csv(SPEECH_DIR / "model_xlm_sentiment.csv", sep=";",
                        usecols=["id_deputado", "dataHoraInicio", "xlm_score"])
    xlm["dataHoraInicio"] = pd.to_datetime(xlm["dataHoraInicio"], errors="coerce")
    xlm = xlm.dropna(subset=["dataHoraInicio", "id_deputado", "xlm_score"])
    xlm["id_deputado"] = xlm["id_deputado"].astype(int)

    # Merge into single speeches table
    speeches = nli.merge(pt, on=["id_deputado", "dataHoraInicio"], how="outer")
    speeches = speeches.merge(xlm, on=["id_deputado", "dataHoraInicio"], how="outer")
    log.info("  speeches combined: %d rows", len(speeches))

    # For each vote in panel, get 90-day pre-vote average of each score
    log.info("computing rolling 90-day average per (deputy, vote_date)")
    panel_keys = panel[["idDeputado", "data"]].drop_duplicates()
    panel_keys["data"] = pd.to_datetime(panel_keys["data"])
    panel_keys = panel_keys.rename(columns={"idDeputado": "id_deputado"})

    # Sort
    speeches = speeches.sort_values(["id_deputado", "dataHoraInicio"])
    panel_keys = panel_keys.sort_values(["id_deputado", "data"])

    results = []
    grouped = speeches.groupby("id_deputado")
    n = 0
    for (dep, dt) in panel_keys.itertuples(index=False, name=None):
        if dep in grouped.groups:
            spc = grouped.get_group(dep)
            window_start = dt - pd.Timedelta(days=90)
            mask = ((spc["dataHoraInicio"] >= window_start)
                       & (spc["dataHoraInicio"] < dt))
            sub = spc[mask]
            results.append({
                "idDeputado": dep,
                "data": dt,
                "speech_anti_gov_90d": sub["anti_gov_score"].mean() if len(sub) else np.nan,
                "speech_pro_gov_90d": sub["pro_gov_score"].mean() if len(sub) else np.nan,
                "speech_pt_score_90d": sub["pt_score"].mean() if len(sub) else np.nan,
                "speech_xlm_score_90d": sub["xlm_score"].mean() if len(sub) else np.nan,
                "speech_n_90d": int(len(sub)),
            })
        else:
            results.append({
                "idDeputado": dep,
                "data": dt,
                "speech_anti_gov_90d": np.nan,
                "speech_pro_gov_90d": np.nan,
                "speech_pt_score_90d": np.nan,
                "speech_xlm_score_90d": np.nan,
                "speech_n_90d": 0,
            })
        n += 1
        if n % 50000 == 0:
            log.info("  processed %d/%d (%d%%)", n, len(panel_keys),
                     100*n//len(panel_keys))

    out = pd.DataFrame(results)
    log.info("  ✓ speech features: %d rows", len(out))
    return out


def run_subgroup_tercil(df, ctrl, score_col, log, n_reps=1):
    """Roda PLIV-bl por tercil de score_col."""
    d = df.dropna(subset=[score_col]).copy()
    if len(d) < 10000: return []
    qs = d[score_col].quantile([0.33, 0.67]).values
    d["_tercil"] = "mid"
    d.loc[d[score_col] <= qs[0], "_tercil"] = "low"
    d.loc[d[score_col] >= qs[1], "_tercil"] = "high"
    rows = []
    for t in ("low", "mid", "high"):
        df_g = d[d["_tercil"] == t]
        try:
            r = U2.run_pliv_main(df_g, controls=ctrl, n_reps=n_reps)
            if r:
                r["speech_metric"] = score_col
                r["tercil"] = t
                rows.append(r)
                log.info("  %s/%s: pp=%+.3f%s n=%d",
                         score_col, t, r["pp_per_unit"],
                         r["stars"], r["n_obs"])
        except Exception as e:
            log.error("  %s/%s failed: %s", score_col, t, e)
    return rows


def mediation_speech(df, ctrl, mediator_col, log, label):
    """Acharya-Blackwell-Sen mediation via speech tone.
    Y=alinhamento, T=emenda_M, M=mediator_col.
    """
    cols = [C.TARGET, C.TREATMENT, mediator_col] + ctrl
    cols = list(dict.fromkeys(cols))
    work = df[cols + ["idDeputado"]].dropna()
    if len(work) < 5000:
        return None
    Y = work[C.TARGET].values
    T = work[C.TREATMENT].values
    M = work[mediator_col].values
    X1 = sm.add_constant(np.column_stack([T, work[ctrl].values]))
    m1 = sm.OLS(M, X1).fit(cov_type="cluster",
                              cov_kwds={"groups": work["idDeputado"].values})
    theta_TM = float(m1.params[1])
    X2 = sm.add_constant(np.column_stack([T, M, work[ctrl].values]))
    m2 = sm.OLS(Y, X2).fit(cov_type="cluster",
                              cov_kwds={"groups": work["idDeputado"].values})
    beta_T_direct = float(m2.params[1])
    gamma_M = float(m2.params[2])
    X3 = sm.add_constant(np.column_stack([T, work[ctrl].values]))
    m3 = sm.OLS(Y, X3).fit(cov_type="cluster",
                              cov_kwds={"groups": work["idDeputado"].values})
    beta_T_total = float(m3.params[1])
    indirect = theta_TM * gamma_M
    prop_mediated = indirect / beta_T_total if beta_T_total != 0 else None
    log.info("  %s: theta=%+.6f beta_dir=%+.6f gamma=%+.6f indir=%+.6f total=%+.6f prop=%s",
             label, theta_TM, beta_T_direct, gamma_M, indirect, beta_T_total,
             f"{100*prop_mediated:.1f}%" if prop_mediated else "n/a")
    return {
        "mediator": mediator_col,
        "label": label,
        "theta_TM": round(theta_TM, 6),
        "beta_T_direct": round(beta_T_direct, 6),
        "gamma_M": round(gamma_M, 6),
        "beta_T_total": round(beta_T_total, 6),
        "indirect_effect": round(indirect, 6),
        "prop_mediated": round(prop_mediated, 4) if prop_mediated else None,
        "n_obs": len(work),
    }


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("30_speech")

    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["idLegislatura"] = df["idLegislatura"].astype(int)

    # Cache speech features
    speech_path = C.PANEL / "speech_features.csv"
    if speech_path.exists():
        log.info("loading cached speech_features.csv")
        speech_feat = pd.read_csv(speech_path, sep=";")
        speech_feat["data"] = pd.to_datetime(speech_feat["data"])
    else:
        speech_feat = build_speech_features(df, log)
        speech_feat.to_csv(speech_path, sep=";", index=False)
        log.info("✓ saved speech_features.csv")

    df["data"] = pd.to_datetime(df["data"])
    df = df.merge(speech_feat, on=["idDeputado", "data"], how="left")
    log.info("Panel + speech: %d rows", len(df))
    for c in ["speech_anti_gov_90d", "speech_pt_score_90d",
                 "speech_xlm_score_90d", "speech_n_90d"]:
        log.info("  %s non-null: %.1f%%", c, 100*df[c].notna().mean())

    ctrl = U2.get_clean_full_controls(df)
    # Drop speech cols from controls
    ctrl = [c for c in ctrl if not c.startswith("speech_")]
    log.info("Controls: %d", len(ctrl))

    rows = []

    # ── Heterogeneidade por anti-gov stance × leg ───────────────────────────
    log.info("\n=== Heterogeneidade por anti-gov stance × leg ===")
    for leg, leg_label in [(None, "pooled"), (55, "leg55"), (56, "leg56")]:
        df_l = df if leg is None else df[df["idLegislatura"] == leg]
        log.info("--- %s ---", leg_label)
        for col in ["speech_anti_gov_90d", "speech_pt_score_90d"]:
            if df_l[col].notna().sum() < 10000:
                log.info("  skip %s (too few non-null)", col); continue
            r_list = run_subgroup_tercil(df_l, ctrl, col, log)
            for r in r_list:
                r["legis"] = leg_label
            rows.extend(r_list)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "speech_integration.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))

    # ── Mediação retórica: emenda → speech_tone → alinhamento ───────────────
    log.info("\n=== Mediação retórica (Acharya-Blackwell-Sen) ===")
    med_rows = []
    for leg, leg_label in [(None, "pooled"), (55, "leg55"), (56, "leg56")]:
        df_l = df if leg is None else df[df["idLegislatura"] == leg]
        for med_col in ["speech_anti_gov_90d", "speech_pt_score_90d",
                            "speech_xlm_score_90d"]:
            if df_l[med_col].notna().sum() < 5000:
                log.info("  skip %s/%s (too few non-null)", leg_label, med_col)
                continue
            try:
                r = mediation_speech(df_l, ctrl, med_col, log,
                                          f"{leg_label}_{med_col}")
                if r:
                    r["legis"] = leg_label
                    med_rows.append(r)
            except Exception as e:
                log.error("  %s/%s failed: %s", leg_label, med_col, e)

    df_med = pd.DataFrame(med_rows)
    out_med = C.RESULTS / "speech_mediation.csv"
    df_med.to_csv(out_med, sep=";", index=False)
    log.info("✓ saved %s (%d rows)", out_med, len(df_med))


if __name__ == "__main__":
    main()
