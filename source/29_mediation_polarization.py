# -*- coding: utf-8 -*-
"""
29_mediation_polarization.py — Análise de mediação: polarização explica o efeito?
====================================================================================
Pergunta: a relação emenda → alinhamento é mediada por polarização?

Análise causal de mediação (Acharya-Blackwell-Sen 2016, "Explaining
Causal Findings without Bias"):

  Y = α + β·T + γ·M + δ·(T×M) + g(X) + ε,
  M = θ·T + h(X) + η,   (mediador é polarização)

  Efeito total      = β + γ·E[M]
  Efeito direto     = β  (mantendo M fixo)
  Efeito indireto   = γ·θ  (via M)

Para nós:
  T = emenda_M
  M = pol_simple, pol_jaccard, pol_paper_*
  Y = alinhamento

Procedimento:
  1. Stage 1: M ~ T (efeito de emenda sobre polarização)
  2. Stage 2: Y ~ T + M (efeito conjunto)
  3. Decomposição

Análise complementar:
  - Granger-style: pol_{t-1} prediz alinhamento atual? lag exógeno?
  - Sub-grupos por terciles de polarização (mas com TODAS as medidas)

Output: results/mediation_polarization.csv
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils_v2 as U2

POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")


def attach_pol_paper(df):
    """Attach MDS-Euclidean polarization from paper-polarization."""
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name in ["euclidean", "forte", "fraca"]:
        path = POL_PAPER_DIR / f"average_mds_distances_{name}.csv"
        if not path.exists(): continue
        pol = pd.read_csv(path)
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        col = f"pol_paper_{name}_mds"
        df[col] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col] = r["Euclidiana_MDS"]
    return df


def mediation_analysis(df, ctrl, mediator_col, log, label):
    """Análise de mediação OLS-based + IV-based."""
    # Drop NaN
    cols = [C.TARGET, C.TREATMENT, mediator_col] + ctrl
    cols = list(dict.fromkeys(cols))  # dedup preserve order
    work = df[cols + ["idDeputado"]].dropna()
    if len(work) < 5000: return None

    Y = work[C.TARGET].values
    T = work[C.TREATMENT].values
    M = work[mediator_col].values
    X = sm.add_constant(work[ctrl].values)

    # Stage 1: M ~ T + X (efeito de T sobre M)
    X1 = sm.add_constant(np.column_stack([T, work[ctrl].values]))
    m1 = sm.OLS(M, X1).fit(cov_type="cluster",
                              cov_kwds={"groups": work["idDeputado"].values})
    theta_TM = float(m1.params[1])
    se_theta_TM = float(m1.bse[1])

    # Stage 2: Y ~ T + M + X (efeito direto T → Y e indireto via M)
    X2 = sm.add_constant(np.column_stack([T, M, work[ctrl].values]))
    m2 = sm.OLS(Y, X2).fit(cov_type="cluster",
                              cov_kwds={"groups": work["idDeputado"].values})
    beta_T_direct = float(m2.params[1])
    gamma_M = float(m2.params[2])

    # Stage 3: Y ~ T + X (efeito total para comparação)
    X3 = sm.add_constant(np.column_stack([T, work[ctrl].values]))
    m3 = sm.OLS(Y, X3).fit(cov_type="cluster",
                              cov_kwds={"groups": work["idDeputado"].values})
    beta_T_total = float(m3.params[1])

    # Indirect effect = theta_TM × gamma_M
    indirect = theta_TM * gamma_M
    direct = beta_T_direct
    total = beta_T_total
    prop_mediated = indirect / total if total != 0 else None

    log.info("  %s:", label)
    log.info("    T → M (theta): %+.6f (SE %.6f)", theta_TM, se_theta_TM)
    log.info("    T → Y direct (beta): %+.6f", beta_T_direct)
    log.info("    M → Y (gamma): %+.6f", gamma_M)
    log.info("    Indirect (theta × gamma): %+.6f", indirect)
    log.info("    Total: %+.6f", total)
    log.info("    %% mediated: %.1f%%",
             100 * prop_mediated if prop_mediated else float('nan'))

    return {
        "mediator": mediator_col,
        "label": label,
        "theta_TM": round(theta_TM, 6),
        "se_theta_TM": round(se_theta_TM, 6),
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
    log = logging.getLogger("29_mediation")

    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df["idLegislatura"] = df["idLegislatura"].astype(int)
    df = attach_pol_paper(df)
    ctrl = U2.get_clean_full_controls(df)
    # Drop pol_* from controls
    ctrl = [c for c in ctrl if not c.startswith("pol_")]
    log.info("Panel: %d | ctrls: %d", len(df), len(ctrl))

    rows = []
    mediators = [
        "pol_simple", "pol_jaccard",
        "pol_paper_euclidean_mds", "pol_paper_forte_mds", "pol_paper_fraca_mds",
    ]

    # Pooled + per-leg
    for leg, leg_label in [(None, "pooled"), (55, "leg55"), (56, "leg56")]:
        df_l = df if leg is None else df[df["idLegislatura"] == leg]
        log.info("\n=== %s (n=%d) ===", leg_label, len(df_l))
        for m in mediators:
            if m not in df_l.columns:
                log.info("  skip %s (col missing)", m); continue
            if df_l[m].notna().sum() < 5000:
                log.info("  skip %s (too few non-null)", m); continue
            try:
                r = mediation_analysis(df_l, ctrl, m, log,
                                            f"{leg_label}_{m}")
                if r:
                    r["legis"] = leg_label
                    rows.append(r)
            except Exception as e:
                log.error("  %s/%s failed: %s", leg_label, m, e)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "mediation_polarization.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d rows)", out, len(df_out))


if __name__ == "__main__":
    main()
