# -*- coding: utf-8 -*-
"""102_leg56_only.py — Runs only Leg 56 gov outcome with n_reps=1
to complete the two-way table after the n_reps=3 run stalled."""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import _utils as U
import _config as C
import _utils_v2 as UV

import importlib.util
spec = importlib.util.spec_from_file_location("s101", HERE / "101_twoway_posthoc.py")
s101 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s101)

print("Loading modeling panel...", flush=True)
df = U.load_modeling_panel()
print(f"panel: n={len(df):,}", flush=True)

r = s101.run_one_custom(df, "gov", 56, n_folds=3, n_reps=1) if hasattr(s101, "run_one_custom") else None

if r is None:
    # inline the logic with n_reps=1
    sub = df[df["idLegislatura"] == 56].copy()
    target = "alinhamento"
    print(f"\n=== outcome=gov | leg=56 | n_reps=1 ===", flush=True)
    t0 = time.time()
    pliv, work, sc_t = s101.fit_pliv_and_extract_scores(sub, target, n_folds=3, n_reps=1)
    print(f"PLIV fit done in {time.time()-t0:.1f}s", flush=True)

    coef = float(pliv.coef[0])
    std_t = float(sc_t.scale_[0])
    ses = s101.se_from_pliv(pliv, work, sc_t)
    pp = 100 * coef / std_t
    ci_lo_1w = 100 * (coef - 1.96 * ses["se_sd_1way"]) / std_t
    ci_hi_1w = 100 * (coef + 1.96 * ses["se_sd_1way"]) / std_t
    ci_lo_2w = 100 * (coef - 1.96 * ses["se_sd_2way"]) / std_t
    ci_hi_2w = 100 * (coef + 1.96 * ses["se_sd_2way"]) / std_t
    from scipy.stats import norm
    z_1w = coef / ses["se_sd_1way"]
    z_2w = coef / ses["se_sd_2way"]
    p_1w = 2 * (1 - norm.cdf(abs(z_1w)))
    p_2w = 2 * (1 - norm.cdf(abs(z_2w)))
    st = lambda p: ("***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else "")

    print(f"  1-way : pp={pp:+.3f} SE={ses['se_sd_1way']:.4f} "
          f"CI=[{ci_lo_1w:+.3f},{ci_hi_1w:+.3f}] p={p_1w:.4f} {st(p_1w)}", flush=True)
    print(f"  2-way : pp={pp:+.3f} SE={ses['se_sd_2way']:.4f} "
          f"CI=[{ci_lo_2w:+.3f},{ci_hi_2w:+.3f}] p={p_2w:.4f} {st(p_2w)}", flush=True)
    print(f"  SE ratio 2w/1w = {ses['se_ratio_2w_1w']:.3f}", flush=True)

    out = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-emendas/results/twoway_clustering")
    out.mkdir(parents=True, exist_ok=True)
    row = dict(outcome="gov", leg=56, coef_sd=coef, pp_per_unit=pp,
               se_1way=ses["se_sd_1way"], se_2way=ses["se_sd_2way"],
               se_ratio=ses["se_ratio_2w_1w"],
               ci95_1way_lo=ci_lo_1w, ci95_1way_hi=ci_hi_1w,
               ci95_2way_lo=ci_lo_2w, ci95_2way_hi=ci_hi_2w,
               pval_1way=p_1w, pval_2way=p_2w,
               stars_1way=st(p_1w), stars_2way=st(p_2w),
               n_obs=ses["n_obs"], n_deputies=ses["n_deputies"],
               n_votes=ses["n_votes"])
    pd.DataFrame([row]).to_csv(out / "leg56_gov_twoway.csv", index=False)
    print(f"\nwrote {out}/leg56_gov_twoway.csv", flush=True)
