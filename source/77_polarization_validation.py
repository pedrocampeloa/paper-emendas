"""
77_polarization_validation.py
------------------------------
Validate the polarization mechanism claimed in Section 6 of the paper by
running the antagonism-tercile decomposition on outcomes and sub-periods
that the current paper does NOT cover:

  (A) y_pres (Chamber-president outcome) x tercis of antagonism x
      three sub-periods:
        - Leg 55 (Maia only, 2016-07-14 to 2018)
        - Leg 56 pre-Lira (Maia sub, 2019-01 to 2021-01-31)
        - Leg 56 post-Lira (Lira, 2021-02-01 onward)

  (B) y_gov (Executive outcome) x tercis of antagonism x TWO sub-periods
      of Leg 56 (Maia sub and Lira sub); we already have Leg 55/56 pooled.

  Total: (3 sub-periods x 3 tercis) x 2 outcomes + (Leg 56 pooled we have)
       = 9 y_pres PLIVs + 6 y_gov PLIVs = 15 PLIVs
      (some sub-periods x tercis may be too small; those are skipped).

Config: n_folds=3, n_reps=3, seed=0.

Purpose:
  If polarization really mediates the pork-for-votes channel via a
  "credibility-cost" mechanism (Section 6), then:
    - For y_pres, the mid-tercile Lira sub-period coefficient should be
      POSITIVE (mirror of the Bolsonaro mid-tercile Executive coefficient
      of -1.87 in the current Table 8).
    - The pattern should hold across sub-periods, not just be a
      temporal artifact.
  If the pattern does not hold, we may need to drop or rewrite
  Section 6 and remove the credibility-cost narrative in Section 7.

Output: results/n3_pol_validation.csv
"""

import sys, time, warnings, logging, traceback
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

# Reuse the y_pres loader from script 55
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "_pres55",
    str(Path(__file__).parent / "55_n3_pres_camara_orient.py"))
_pres55 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pres55)

warnings.filterwarnings("ignore")

PANEL = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
POL_PAPER_DIR = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-polarization/data/processed")
N_FOLDS, N_REPS = 3, 3
CUT_LIRA = pd.Timestamp("2021-02-01")
CUT_MAIA_55 = pd.Timestamp("2016-07-14")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("pol_valid")


EXTRA_TREATMENT_VARS = [
    "T_rp6_pre60", "T_rp6_pre60_M",
    "T_rp6_pix_pre60", "T_rp6_pix_pre60_M",
    "T_rp7_pre60", "T_rp7_pre60_M",
    "T_rp8_pre60", "T_rp8_pre60_M",
    "T_rp9_pre60", "T_rp9_pre60_M",
    "T_rp9_imputed_pre60", "T_rp9_imputed_pre60_M",
    "d_rp9_solicitante", "share_pork_opaco", "share_rp9",
    "share_pix", "n_apoiamentos_opaco",
]

# Column name in the panel that holds the "Strong" / antagonism measure
POL_COL = "pol_paper_forte_mds"


def safe_pliv(df_l, controls, label):
    log.info(f"  PLIV: {label}  n={len(df_l):,}")
    if len(df_l) < 5000:
        log.warning(f"    too small ({len(df_l)})")
        return None
    bad_set = {"alinhamento", "emenda_M", "idDeputado", POL_COL,
               "y_pres", "voto", "ori_pres_camara", "partido_presidente",
               "partido_norm", "siglaPartido",
               "d_centrao_hist", "d_pp", "tercil"}
    controls = [c for c in controls if c in df_l.columns
                and df_l[c].notna().mean() > 0.5
                and df_l[c].nunique() > 1
                and c not in bad_set
                and not c.startswith("pol_")]
    np.random.seed(0)
    t0 = time.time()
    try:
        res = U2.run_pliv_main(df_l, controls=controls, iv_set="backlog",
                                n_folds=N_FOLDS, n_reps=N_REPS)
        if res is None:
            return None
        log.info(f"    theta={res['pp_per_unit']:+.4f} pp "
                  f"CI=[{res['ci95_lo_pp']:+.3f}, {res['ci95_hi_pp']:+.3f}] "
                  f"p={res['pval']:.4f} ({time.time()-t0:.0f}s)")
        return res
    except Exception as e:
        log.error(f"    FAIL: {e}")
        traceback.print_exc()
        return None


def attach_antagonism(df):
    """Attach pol_paper_forte_mds via merge with paper-polarization MDS files."""
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"])
    pol = pd.read_csv(POL_PAPER_DIR / "average_mds_distances_forte.csv")
    pol["period_start"] = pd.to_datetime(pol["period_start"])
    pol["period_end"] = pd.to_datetime(pol["period_end"])
    df[POL_COL] = np.nan
    for _, r in pol.iterrows():
        mask = (df["data"] >= r["period_start"]) & (df["data"] <= r["period_end"])
        df.loc[mask, POL_COL] = r["Euclidiana_MDS"]
    nn = df[POL_COL].notna().sum()
    log.info(f"  attached {POL_COL}: {nn:,}/{len(df):,} ({100*nn/len(df):.1f}%)")
    return df


def build_tercis(df, sub_name, sub_mask):
    """Compute within-sub-sample terciles of antagonism (POL_COL).
    Uses rank-then-cut to handle sub-periods where the MDS series is
    bimestral (many observations share the same polarization value)."""
    sub = df[sub_mask].copy()
    if POL_COL not in sub.columns:
        log.error(f"  missing {POL_COL}")
        return None
    sub = sub.dropna(subset=[POL_COL])
    if len(sub) < 5000:
        log.warning(f"  {sub_name}: only {len(sub):,} obs after dropna(pol), skip")
        return None
    # Rank-based tercile assignment breaks ties uniformly, so it works
    # even when the underlying MDS series has many identical values
    # inside a short sub-period.
    r = sub[POL_COL].rank(method="first", pct=True)
    conds = [r <= 1/3, r <= 2/3]
    sub["tercil"] = np.select(conds, ["low", "mid"], default="high")
    counts = sub["tercil"].value_counts().to_dict()
    log.info(f"  {sub_name} tercile counts: {counts}")
    return sub


def run_tercis_on_outcome(df, outcome_name, subperiods):
    """For a given outcome, run tercis(antagonism) x each sub-period."""
    log.info(f"\n{'='*70}\nOutcome: {outcome_name}\n{'='*70}")
    df["data"] = pd.to_datetime(df["data"])
    ctrl_full = U2.get_clean_full_controls(df)
    _outcome_related = {"alinhamento", "emenda_M", "idDeputado", POL_COL,
                         "y_pres", "voto", "ori_pres_camara",
                         "partido_presidente", "partido_norm",
                         "siglaPartido", "d_centrao_hist", "d_pp", "tercil"}
    ctrl = [c for c in ctrl_full if c not in EXTRA_TREATMENT_VARS
             and not c.startswith("pol_")
             and c not in _outcome_related]
    log.info(f"  ctrl: {len(ctrl)} cols")

    rows = []
    for sub_name, sub_mask in subperiods:
        log.info(f"\n-- sub-period: {sub_name} (n={sub_mask.sum():,}) --")
        sub_df = build_tercis(df, sub_name, sub_mask)
        if sub_df is None:
            continue
        for tlabel in ["low", "mid", "high"]:
            t_sub = sub_df[sub_df["tercil"] == tlabel]
            label = f"{outcome_name}__{sub_name}__{tlabel}"
            res = safe_pliv(t_sub, ctrl, label)
            if res:
                res["outcome"] = outcome_name
                res["subperiod"] = sub_name
                res["tercil"] = tlabel
                rows.append(res)
                pd.DataFrame(rows).to_csv(
                    RESULTS / f"n3_pol_valid_{outcome_name}.csv",
                    sep=";", index=False)
    return rows


def main():
    t0 = time.time()

    # ============================================================
    # (A) y_pres outcome
    # ============================================================
    log.info("\n" + "#"*70)
    log.info("# (A) y_pres: alignment with Chamber-president party")
    log.info("#"*70)
    df_p = _pres55.load_panel_with_y_pres()
    df_p["data"] = pd.to_datetime(df_p["data"])
    df_p["partido_norm"] = df_p["siglaPartido"].astype(str).str.upper().str.strip()
    df_p = attach_antagonism(df_p)

    subperiods_pres = [
        ("leg55_maia",
         (df_p["idLegislatura"] == 55) & (df_p["data"] >= CUT_MAIA_55)),
        ("leg56_maia",
         (df_p["idLegislatura"] == 56) & (df_p["data"] < CUT_LIRA)),
        ("leg56_lira",
         (df_p["idLegislatura"] == 56) & (df_p["data"] >= CUT_LIRA)),
    ]
    rows_pres = run_tercis_on_outcome(df_p, "y_pres", subperiods_pres)
    del df_p

    # ============================================================
    # (B) y_gov outcome, Leg 56 split
    # ============================================================
    log.info("\n" + "#"*70)
    log.info("# (B) y_gov: alignment with Executive, Leg 56 sub-periods")
    log.info("#"*70)
    df_g = U.load_modeling_panel(window="pre", include_coalizao=True)
    df_g["idDeputado"] = df_g["idDeputado"].astype(str)
    df_g["data"] = pd.to_datetime(df_g["data"])
    df_g = attach_antagonism(df_g)

    subperiods_gov = [
        ("leg56_maia",
         (df_g["idLegislatura"] == 56) & (df_g["data"] < CUT_LIRA)),
        ("leg56_lira",
         (df_g["idLegislatura"] == 56) & (df_g["data"] >= CUT_LIRA)),
    ]
    rows_gov = run_tercis_on_outcome(df_g, "y_gov", subperiods_gov)

    # Consolidate
    all_rows = rows_pres + rows_gov
    out = pd.DataFrame(all_rows)
    out.to_csv(RESULTS / "n3_pol_validation.csv", sep=";", index=False)
    log.info(f"\n\nAll results ({len(out)} PLIVs):")
    if len(out):
        print(out[["outcome", "subperiod", "tercil", "pp_per_unit",
                    "ci95_lo_pp", "ci95_hi_pp", "pval", "stars", "n_obs"]]
              .to_string(index=False))
    elapsed = (time.time() - t0) / 60
    log.info(f"\nDONE in {elapsed:.1f} min")


if __name__ == "__main__":
    main()
