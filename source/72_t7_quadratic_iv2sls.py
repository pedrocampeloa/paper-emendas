"""
72_t7_quadratic_iv2sls.py
--------------------------
A.5 (T quadratico) como ROBUSTEZ ao resultado principal Tabela 4.

Estrategia: substitui DoubleMLPLIV (que falhou com Gram matrix em multi-treatment)
por GMM/IV2SLS classico via linearmodels.iv.IV2SLS.

Modelo:
  alinhamento_it = alpha_i + theta1 * T_it + theta2 * T_it^2 + X_it * gamma + e_it

Identificacao: 2 endogenos (T, T^2) com 2 IVs:
  - iv_q4_no_ytd (fiscal calendar pressure + backlog)
  - iv_ytd_exec_pct (ministry execution percentage)
  - iv_q4_dummy + iv_days_to_dec31 como backup adicionais (overid)

Saida: ponto de inflexao T* = -theta1/(2*theta2) se theta2 estatisticamente significativo.

Outputs:
  results/n3_t7_quadratic_iv2sls.csv
  docs/figs/fig_quadratic_response.pdf (curva)
"""

import sys
import warnings
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils as U
import _utils_v2 as U2

warnings.filterwarnings("ignore")

PANEL = Path(C.PANEL)
RESULTS = Path(C.RESULTS)
FIGS = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-emendas/docs/figs")

mpl.rcParams.update({
    "font.family": "serif", "font.size": 10,
    "axes.spines.right": False, "axes.spines.top": False,
    "savefig.bbox": "tight",
})

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("a5")


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


def run_iv2sls_quadratic(df, leg_label):
    """Roda IV2SLS com T + T^2 endogenos e 2 IVs."""
    from linearmodels.iv import IV2SLS
    df = df.copy()
    df["T"] = df["emenda_M"]
    df["T2"] = df["T"] ** 2

    # IVs: usar 2-4 do conjunto disponivel
    iv_candidates = ["iv_q4_no_ytd", "iv_ytd_exec_pct", "iv_q4_dummy",
                      "iv_days_to_dec31"]
    iv_cols = [c for c in iv_candidates if c in df.columns
                and df[c].notna().mean() > 0.5
                and df[c].nunique() > 1]
    log.info(f"  IVs disponiveis: {iv_cols}")
    if len(iv_cols) < 2:
        log.error(f"  Apenas {len(iv_cols)} IV disponivel - precisa >=2")
        return None
    iv_cols = iv_cols[:3]  # use ate 3 (overid mais robusto)

    # Controles: usar conjunto REDUZIDO para A.5 (IV2SLS sem ML nuisance precisa
    # menos controles para preservar full rank). Foco em controles importantes:
    # comportamento pre-vote, ciclo eleitoral, ministerial.
    # Nomes corretos detectados no painel
    BASE_CTRL = [
        "pol_simple", "pol_jaccard", "pol_paper",
        "d_tipoVotacao_PEC",
    ]
    # Tentar controles dinamicos do conjunto clean (sem incluir IVs/treatments)
    candidates = U2.get_clean_full_controls(df)
    extra = [c for c in candidates if c not in iv_cols
              and c not in EXTRA_TREATMENT_VARS
              and c not in ("alinhamento", "emenda_M", "T", "T2", "idDeputado",
                            "idVotacao", "voto", "siglaPartido")
              and c.startswith(("pol_", "d_tipoVoto", "d_orient", "d_coal",
                                "d_oposi", "d_inde", "pct_", "abstencao",
                                "idade", "ano_"))]
    BASE_CTRL = list(dict.fromkeys(BASE_CTRL + extra[:30]))
    ctrl = [c for c in BASE_CTRL if c in df.columns
             and df[c].notna().mean() > 0.5
             and df[c].nunique() > 1]

    keep_cols = ["alinhamento", "T", "T2", "idDeputado"] + iv_cols + ctrl
    keep_cols = list(dict.fromkeys(keep_cols))
    sub = df[keep_cols].dropna().copy()
    if len(sub) < 5000:
        log.error(f"  {leg_label}: amostra pequena ({len(sub)})")
        return None

    # Within-deputy demeaning (FE)
    log.info(f"  {leg_label}: n={len(sub):,}, ctrl={len(ctrl)}, ivs={iv_cols}")
    for col in ["alinhamento", "T", "T2"] + iv_cols + ctrl:
        if col == "idDeputado": continue
        means = sub.groupby("idDeputado")[col].transform("mean")
        sub[col] = sub[col] - means

    # IV2SLS: dependent = alinhamento; exog = ctrl; endog = T,T2; instruments = iv_cols
    # No const apos demean (const fica zero)
    dep = sub["alinhamento"]
    endog = sub[["T", "T2"]]
    instruments = sub[iv_cols]
    # Drop colinear controles via SVD
    exog_raw = sub[ctrl].copy()
    # Filter: keep cols with std > 0 and pairwise corr < 0.99
    keep_ctrl = []
    seen = []
    for c in ctrl:
        if exog_raw[c].std() < 1e-8: continue
        ok = True
        for k in keep_ctrl:
            if abs(exog_raw[c].corr(exog_raw[k])) > 0.99:
                ok = False
                break
        if ok:
            keep_ctrl.append(c)
    log.info(f"  ctrls apos dedup pairwise: {len(keep_ctrl)} (de {len(ctrl)})")
    # QR-based rank detection: identifica colunas que sao combinacao linear
    full_mat = np.hstack([exog_raw[keep_ctrl].values, sub[["T", "T2"]].values])
    Q, R = np.linalg.qr(full_mat)
    diag_R = np.abs(np.diag(R))
    tol = max(full_mat.shape) * np.finfo(float).eps * diag_R[0]
    # mantem colunas com |R_ii| > tol; colunas de ctrl sao indices 0..len(keep_ctrl)-1
    rank_mask = diag_R > tol
    n_ctrl = len(keep_ctrl)
    # T e T2 sao ultimas 2 colunas; nao dropa
    drops = []
    for i in range(n_ctrl):
        if not rank_mask[i]:
            drops.append(keep_ctrl[i])
    if drops:
        log.info(f"  QR detectou rank-deficiency, dropando: {drops}")
        keep_ctrl = [c for c in keep_ctrl if c not in drops]
    log.info(f"  ctrls finais: {len(keep_ctrl)}")
    exog = exog_raw[keep_ctrl].copy()
    from linearmodels.iv import IV2SLS

    # Fit com cluster-robust SE
    model = IV2SLS(dep, exog, endog, instruments)
    res = model.fit(cov_type="clustered", clusters=sub["idDeputado"])
    log.info(f"  {leg_label}: theta_T={res.params['T']:+.4f} (se={res.std_errors['T']:.4f})")
    log.info(f"  {leg_label}: theta_T2={res.params['T2']:+.6f} (se={res.std_errors['T2']:.6f})")

    # First-stage F (Kleibergen-Paap proxy via standalone fits)
    first_stage = res.first_stage
    log.info(f"  first stage diagnostics:\n{first_stage}")

    theta_T = res.params["T"]
    theta_T2 = res.params["T2"]
    se_T = res.std_errors["T"]
    se_T2 = res.std_errors["T2"]
    p_T = res.pvalues["T"]
    p_T2 = res.pvalues["T2"]
    ci = res.conf_int()
    t_star = -theta_T / (2 * theta_T2) if theta_T2 != 0 else np.nan

    # Sargan-Hansen J
    j_stat = float(res.j_stat.stat) if hasattr(res, "j_stat") and res.j_stat is not None else np.nan
    j_p = float(res.j_stat.pval) if hasattr(res, "j_stat") and res.j_stat is not None else np.nan

    return {
        "leg": leg_label,
        "theta_T": round(float(theta_T), 6),
        "se_T": round(float(se_T), 6),
        "ci_T_lo": round(float(ci.loc["T", "lower"]), 6),
        "ci_T_hi": round(float(ci.loc["T", "upper"]), 6),
        "p_T": round(float(p_T), 6),
        "theta_T2": round(float(theta_T2), 6),
        "se_T2": round(float(se_T2), 6),
        "ci_T2_lo": round(float(ci.loc["T2", "lower"]), 6),
        "ci_T2_hi": round(float(ci.loc["T2", "upper"]), 6),
        "p_T2": round(float(p_T2), 6),
        "T_inflection_RM": round(float(t_star), 3) if not np.isnan(t_star) else None,
        "j_stat": round(j_stat, 4) if not np.isnan(j_stat) else None,
        "j_pval": round(j_p, 4) if not np.isnan(j_p) else None,
        "n_obs": len(sub),
        "n_ctrl": len(ctrl),
        "ivs": ",".join(iv_cols),
    }


def plot_response_curve(rows):
    """Curva resposta dY/dT = theta_T + 2*theta_T2*T."""
    fig, ax = plt.subplots(figsize=(7, 4))
    T_grid = np.linspace(0, 5, 200)  # R$M
    colors = {"pooled": "#888888", "leg55": "#1f3a68", "leg56": "#a02020"}
    for r in rows:
        marginal = r["theta_T"] + 2 * r["theta_T2"] * T_grid
        # convert standardized coef (scale-free) to pp/R$M: theta is already in pp/R$M
        ax.plot(T_grid, marginal * 100, color=colors.get(r["leg"], "#444444"),
                label=f"{r['leg']}", linewidth=1.8)
    ax.axhline(0, color="black", linewidth=0.5, linestyle=":", alpha=0.5)
    ax.set_xlabel("Pre-vote committed amendment $T$ (R\\$ million)")
    ax.set_ylabel(r"Marginal effect $\partial Y/\partial T$ (pp)")
    ax.set_title("Quadratic response: marginal pork-for-votes effect by $T$")
    ax.legend(loc="best", frameon=False)
    ax.grid(axis="y", alpha=0.2)
    out = FIGS / "fig_quadratic_response.pdf"
    fig.savefig(out)
    log.info(f"  saved {out}")


def main():
    log.info("A.5: Tratamento quadratico via IV2SLS (robustez)")
    log.info("Loading modeling panel via U.load_modeling_panel(window='pre')")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    log.info(f"  panel: {len(df):,} rows")

    rows = []
    for leg_label, mask in [
        ("pooled", df["idLegislatura"].isin([55, 56])),
        ("leg55", df["idLegislatura"] == 55),
        ("leg56", df["idLegislatura"] == 56),
    ]:
        log.info(f"\n==> {leg_label}")
        sub = df[mask].copy()
        sub = sub.dropna(subset=["alinhamento", "emenda_M"])
        r = run_iv2sls_quadratic(sub, leg_label)
        if r: rows.append(r)

    if rows:
        out = pd.DataFrame(rows)
        out.to_csv(RESULTS / "n3_t7_quadratic_iv2sls.csv", sep=";", index=False)
        log.info(f"\n  saved {RESULTS / 'n3_t7_quadratic_iv2sls.csv'}")
        print(out.to_string(index=False))
        plot_response_curve(rows)


if __name__ == "__main__":
    main()
