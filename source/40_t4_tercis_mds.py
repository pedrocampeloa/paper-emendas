"""
40_t4_tercis_mds.py
--------------------
Refaz T4 (tercis polarizacao por legislatura) usando as medidas MDS
do paper-polarization, que sao montadas via attach_pol_paper().

Aplica n_folds=2, n_reps=1.

Output:
    results/followup_t4_tercis_by_leg.csv
"""

import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("t4")

POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
RESULTS = Path(C.RESULTS)


def attach_pol_paper(df):
    """Anexa as 3 medidas MDS (Euclidean, Strong, Weak) ao painel via janela."""
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    for name in ["euclidean", "forte", "fraca"]:
        path = POL_PAPER_DIR / f"average_mds_distances_{name}.csv"
        if not path.exists():
            log.warning(f"  missing {path}")
            continue
        pol = pd.read_csv(path)
        pol["period_start"] = pd.to_datetime(pol["period_start"])
        pol["period_end"] = pd.to_datetime(pol["period_end"])
        col = f"pol_paper_{name}_mds"
        df[col] = np.nan
        for _, r in pol.iterrows():
            mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
            df.loc[mask, col] = r["Euclidiana_MDS"]
        log.info(f"  attached {col}: non-null={df[col].notna().sum():,}")
    return df


def main():
    log.info("Loading panel + MDS measures")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df = attach_pol_paper(df)
    ctrl = U2.get_clean_full_controls(df)
    ctrl = [c for c in ctrl if not c.startswith("pol_")]
    log.info(f"  panel: {len(df):,} rows | ctrls: {len(ctrl)}")

    rows = []
    measures = [
        ("pol_paper_euclidean_mds", "MDS-Euclidean"),
        ("pol_paper_fraca_mds", "MDS-Weak"),
        ("pol_paper_forte_mds", "MDS-Strong"),
    ]
    for col, label in measures:
        if col not in df.columns:
            log.warning(f"  skip {col}")
            continue
        for leg in [55, 56]:
            df_l = df[df["idLegislatura"] == leg].copy()
            df_l = df_l.dropna(subset=[col])
            if len(df_l) < 5000:
                continue
            df_l["tercil"] = pd.qcut(df_l[col], 3, labels=["low", "mid", "high"],
                                       duplicates="drop")
            for tlabel in ["low", "mid", "high"]:
                sub = df_l[df_l["tercil"] == tlabel]
                if len(sub) < 2000:
                    continue
                res = U2.run_pliv_main(sub, controls=ctrl, iv_set="backlog",
                                         n_folds=2, n_reps=1)
                if res is not None:
                    res["measure"] = label
                    res["leg"] = leg
                    res["tercil"] = tlabel
                    res["n_obs_tercil"] = len(sub)
                    rows.append(res)
                log.info(f"  {label} leg={leg} tercil={tlabel} n={len(sub):,} done")

    if not rows:
        log.warning("No T4 results")
        return
    out = pd.DataFrame(rows)
    out_path = RESULTS / "followup_t4_tercis_by_leg.csv"
    out.to_csv(out_path, sep=";", index=False)
    log.info(f"  saved {out_path}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
