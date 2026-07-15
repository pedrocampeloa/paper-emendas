"""
74_a9_dual_mediation.py
------------------------
A.9: Mediacao dupla com 2 mediadores simultaneos (Strong + Weak Divergence).

Acharya-Blackwell-Sen com 2 mediadores:
  M1 (Strong) = pol_paper_forte_mds  (conflito ideologico)
  M2 (Weak)   = pol_paper_fraca_mds  (fragmentacao tatica)

Estrutura:
  Eq1: M1 = a_M1 + theta_TM1 * T + e1
  Eq2: M2 = a_M2 + theta_TM2 * T + e2
  Eq3: Y  = a_Y + beta_T_direct * T + gamma_M1 * M1 + gamma_M2 * M2 + eY
  Eq4: Y  = a_Y2 + beta_T_total * T + eY2   (sanity)

Efeitos:
  indirect_M1 = theta_TM1 * gamma_M1
  indirect_M2 = theta_TM2 * gamma_M2
  prop_mediated_M1 = indirect_M1 / beta_T_total
  prop_mediated_M2 = indirect_M2 / beta_T_total

Para gov outcome, por leg (pooled, 55, 56).

Output:
  results/n3_a9_dual_mediation.csv
"""

import sys, logging, warnings
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as _CFG
import _utils as U

warnings.filterwarnings("ignore")

PANEL = Path(_CFG.PANEL)
RESULTS = Path(_CFG.RESULTS)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("a9")


def attach_pol_paper(df):
    """Attaches pol_paper_forte_mds and pol_paper_fraca_mds via period_start join."""
    POL_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name in ["forte", "fraca"]:
        p = POL_DIR / f"average_mds_distances_{name}.csv"
        if not p.exists():
            log.warning(f"  {p} missing")
            continue
        pol = pd.read_csv(p)
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        col = f"pol_paper_{name}_mds"
        df[col] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col] = r["Euclidiana_MDS"]
    return df


def run_dual_mediation(df, label):
    """Estima sistema de mediacao dupla via OLS (deterministico)."""
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant

    df = df.dropna(subset=["alinhamento", "emenda_M",
                            "pol_paper_forte_mds", "pol_paper_fraca_mds"]).copy()
    if len(df) < 5000:
        log.warning(f"  {label}: amostra pequena ({len(df)})")
        return None

    T = df["emenda_M"]
    M1 = df["pol_paper_forte_mds"]  # Strong
    M2 = df["pol_paper_fraca_mds"]  # Weak
    Y = df["alinhamento"]
    cluster = df["idDeputado"]

    # Eq1: M1 ~ T
    X1 = add_constant(T)
    m1 = OLS(M1, X1).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    theta_TM1 = m1.params.iloc[1]
    se_TM1 = m1.bse.iloc[1]

    # Eq2: M2 ~ T
    m2 = OLS(M2, X1).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    theta_TM2 = m2.params.iloc[1]
    se_TM2 = m2.bse.iloc[1]

    # Eq3: Y ~ T + M1 + M2 (direct + 2 mediators)
    X3 = add_constant(pd.DataFrame({"T": T, "M1_Strong": M1, "M2_Weak": M2}))
    m3 = OLS(Y, X3).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    beta_T_direct = m3.params["T"]
    gamma_M1 = m3.params["M1_Strong"]
    gamma_M2 = m3.params["M2_Weak"]

    # Eq4: Y ~ T (total effect)
    m4 = OLS(Y, X1).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    beta_T_total = m4.params.iloc[1]

    # Efeitos indiretos
    indirect_M1 = theta_TM1 * gamma_M1
    indirect_M2 = theta_TM2 * gamma_M2
    indirect_total = indirect_M1 + indirect_M2
    prop_M1 = indirect_M1 / beta_T_total if beta_T_total != 0 else np.nan
    prop_M2 = indirect_M2 / beta_T_total if beta_T_total != 0 else np.nan
    prop_total = indirect_total / beta_T_total if beta_T_total != 0 else np.nan

    return {
        "sample": label,
        "n_obs": len(df),
        "theta_TM1_strong": round(float(theta_TM1), 5),
        "theta_TM2_weak":   round(float(theta_TM2), 5),
        "gamma_M1_strong":  round(float(gamma_M1), 5),
        "gamma_M2_weak":    round(float(gamma_M2), 5),
        "beta_T_direct":    round(float(beta_T_direct), 5),
        "beta_T_total":     round(float(beta_T_total), 5),
        "indirect_M1":      round(float(indirect_M1), 5),
        "indirect_M2":      round(float(indirect_M2), 5),
        "indirect_total":   round(float(indirect_total), 5),
        "prop_med_M1":      round(float(prop_M1), 4),
        "prop_med_M2":      round(float(prop_M2), 4),
        "prop_med_total":   round(float(prop_total), 4),
    }


def main():
    log.info("A.9: Mediacao dupla Weak x Strong")
    log.info("Loading modeling panel")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df = attach_pol_paper(df)
    log.info(f"  panel: {len(df):,} rows; "
             f"forte non-null={df['pol_paper_forte_mds'].notna().mean()*100:.1f}%; "
             f"fraca non-null={df['pol_paper_fraca_mds'].notna().mean()*100:.1f}%")

    rows = []
    for lbl, sub in [
        ("pooled", df),
        ("leg55", df[df["idLegislatura"] == 55]),
        ("leg56", df[df["idLegislatura"] == 56]),
    ]:
        log.info(f"==> {lbl}")
        r = run_dual_mediation(sub, lbl)
        if r:
            rows.append(r)
            log.info(f"   beta_T_total={r['beta_T_total']:+.5f}, "
                     f"indirect_M1={r['indirect_M1']:+.5f} ({r['prop_med_M1']*100:+.1f}%), "
                     f"indirect_M2={r['indirect_M2']:+.5f} ({r['prop_med_M2']*100:+.1f}%)")

    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "n3_a9_dual_mediation.csv", sep=";", index=False)
    log.info(f"  saved {RESULTS / 'n3_a9_dual_mediation.csv'}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
