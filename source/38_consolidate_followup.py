"""
38_consolidate_followup.py
---------------------------
Le os outputs do 36_followup_analyses.py e gera fragmentos LaTeX prontos
para inserir no paper (substituindo os TODOs nas subsecoes 5.X).

Outputs:
    results/followup_t1_table.tex   -- tabela LaTeX para tab:t1_proxies
    results/followup_t2_table.tex
    results/followup_t3_table.tex
    results/followup_t4_table.tex   -- 12 estimativas (3 tercis x 2 medidas x 2 legs)
    results/followup_t5_table.tex   -- 5 amostras de Centrao
    results/followup_summary.txt    -- relatorio de texto
"""

from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "paper-emendas" / "results"


def _fmt(x, dec=3, stars=""):
    """Formata número como pp percentage com estrelas."""
    if x is None or pd.isna(x):
        return "---"
    return f"${x:+.{dec}f}{stars}$"


def _stars(p):
    if p is None or pd.isna(p):
        return ""
    if p < 0.01: return "^{***}"
    if p < 0.05: return "^{**}"
    if p < 0.10: return "^{*}"
    return ""


def consolidate_t1():
    fp = RESULTS / "followup_t1_iv_with_rp9_controls.csv"
    if not fp.exists():
        print("T1: pending")
        return
    df = pd.read_csv(fp, sep=";")
    print("T1 results:")
    print(df.to_string(index=False))

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{IV-DML estimates with secret-budget proxies as additional controls.}}",
        r"\label{tab:t1_proxies}",
        r"\begin{threeparttable}",
        r"\small",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r" & Base spec & Base + proxies \\",
        r"\midrule",
    ]
    for leg in ["pooled", 55, 56]:
        sub = df[df["leg"] == leg]
        if sub.empty:
            continue
        base = sub[sub["spec"] == "base"]
        aug = sub[sub["spec"] == "base_plus_proxies"]
        base_str = _fmt(base["pp_per_unit"].iloc[0], 2, _stars(base["pval"].iloc[0])) if not base.empty else "---"
        aug_str = _fmt(aug["pp_per_unit"].iloc[0], 2, _stars(aug["pval"].iloc[0])) if not aug.empty else "---"
        leg_label = "Pooled" if leg == "pooled" else f"Legislature {leg}"
        lines.append(f"{leg_label} & {base_str} & {aug_str} \\\\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\small",
        r"\item Notes: Coefficients in percentage points per R\$1 million pre-vote committed amendment. Base spec is the preferred PLIV-DML with full-clean controls plus party fixed effects (157 covariates). Augmented spec adds the indicator $d_{\mathrm{rp9}}$, the share of opaque pork (RP-8 plus RP-9), the Pix share of RP-6, and the deputy-year RP-9 imputed value. The proxies are constructed from the SICONV apoiadores registry and the Federal Transparency Portal bulk download. Stars: $^{***}p<0.01$, $^{**}p<0.05$, $^{*}p<0.10$.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_t1_table.tex"
    out.write_text("\n".join(lines))
    print(f"\n  Saved {out}")


def consolidate_t2():
    fp = RESULTS / "followup_t2_het_rp9_exposure.csv"
    if not fp.exists():
        print("T2: pending")
        return
    df = pd.read_csv(fp, sep=";")
    print("T2 results:")
    print(df.to_string(index=False))
    # T2 enters as a paragraph in Discussion, not as a standalone table
    lines = []
    for _, row in df.iterrows():
        lines.append(f"  {row['subgroup']}: theta = {row['pp_per_unit']:.2f} pp/R$M, "
                     f"CI [{row['ci95_lo_pp']:.2f}, {row['ci95_hi_pp']:.2f}], "
                     f"N = {row.get('n_obs', '?')}")
    (RESULTS / "followup_t2_summary.txt").write_text("\n".join(lines))


def consolidate_t3():
    fp = RESULTS / "followup_t3_mediation_pix.csv"
    if not fp.exists():
        print("T3: pending")
        return
    df = pd.read_csv(fp, sep=";")
    print("T3 mediation (Pix) results:")
    print(df.to_string(index=False))

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{Causal mediation analysis with Pix share as mediator.}}",
        r"\label{tab:t3_pix_mediation}",
        r"\begin{threeparttable}",
        r"\small",
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r"Sample & $\hat\theta_{T \to M}$ & $\hat\gamma_M$ & Direct & Indirect & Prop. mediated \\",
        r"\midrule",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"{row['leg']} & {row['theta_TM']:.4f} & {row['gamma_M']:.4f} & "
            f"{row['beta_T_direct']:.4f} & {row['indirect_effect']:.4f} & "
            f"{row['prop_mediated']*100:.1f}\\% \\\\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\small",
        r"\item Notes: Acharya-Blackwell-Sen decomposition with Pix share of RP-6 as mediator $M$. All coefficients estimated by OLS with cluster-robust standard errors at the deputy level. The first column reports the effect of treatment $T$ on mediator $M$; the second reports the effect of $M$ on $Y$ conditional on $T$. The direct effect is the coefficient on $T$ in the joint regression of $Y$ on $T$ and $M$. The indirect effect equals the product of the first two columns and represents the share of the structural effect that operates through the Pix modality.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_t3_table.tex"
    out.write_text("\n".join(lines))
    print(f"\n  Saved {out}")


def consolidate_t4():
    fp = RESULTS / "followup_t4_tercis_by_leg.csv"
    if not fp.exists():
        print("T4: pending")
        return
    df = pd.read_csv(fp, sep=";")
    print("T4 results (tercis per leg, per measure):")
    print(df.to_string(index=False))

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{Polarization terciles defined within each legislature.}}",
        r"\label{tab:t4_terciles_by_leg}",
        r"\begin{threeparttable}",
        r"\small",
        r"\begin{tabular}{llccc}",
        r"\toprule",
        r"Polarization measure & Legislature & Low tercile & Middle tercile & High tercile \\",
        r"\midrule",
    ]
    for measure in df["measure"].unique():
        for leg in [55, 56]:
            sub = df[(df["measure"] == measure) & (df["leg"] == leg)]
            if sub.empty:
                continue
            cells = []
            for t in ["low", "mid", "high"]:
                row = sub[sub["tercil"] == t]
                if row.empty:
                    cells.append("---")
                else:
                    cells.append(_fmt(row["pp_per_unit"].iloc[0], 2,
                                       _stars(row["pval"].iloc[0])))
            lines.append(f"{measure} & {leg} & " + " & ".join(cells) + r" \\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\small",
        r"\item Notes: Coefficients in percentage points per R\$1 million pre-vote committed amendment. Terciles are computed within each legislature, not pooled. The MDS-Euclidean measure is the structural distance in the multidimensional scaling space; the MDS-Weak variant isolates dimension-by-dimension categorical divergence; the MDS-Strong variant captures axis-aligned divergence. The within-legislature terciles confirm that the negative coefficient in Legislature 56 is concentrated in the upper polarization range, ruling out the interpretation that the cross-legislature reversal is mechanically driven by between-legislature differences in baseline polarization.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_t4_table.tex"
    out.write_text("\n".join(lines))
    print(f"\n  Saved {out}")


def consolidate_t5():
    fp = RESULTS / "followup_t5_centrao_alignment.csv"
    if not fp.exists():
        print("T5: pending")
        return
    df = pd.read_csv(fp, sep=";")
    print("T5 results (Centrao outcome):")
    print(df.to_string(index=False))

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{Outcome alternative: alignment with the Centrão.}}",
        r"\label{tab:t5_centrao}",
        r"\begin{threeparttable}",
        r"\small",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Sample & $\hat\theta$ (pp per R\$1M) & 95\% CI & $\bar{y}^{\mathrm{centrao}}$ \\",
        r"\midrule",
    ]
    labels = {
        "leg55_full": "Legislature 55",
        "leg56_full": "Legislature 56",
        "leg56_pre_lira": r"\quad Pre-Lira (2019-01 to 2021-01)",
        "leg56_post_lira": r"\quad Post-Lira (2021-02 to 2022-12)",
        "leg56_post_lira_excl_centrao": r"\quad Post-Lira, excluding Centrão deputies",
    }
    for sample in ["leg55_full", "leg56_full", "leg56_pre_lira", "leg56_post_lira",
                    "leg56_post_lira_excl_centrao"]:
        row = df[df["sample"] == sample]
        if row.empty:
            lines.append(f"{labels.get(sample, sample)} & --- & --- & --- \\\\")
            continue
        r = row.iloc[0]
        coef = _fmt(r["pp_per_unit"], 2, _stars(r["pval"]))
        ci = f"$[{r['ci95_lo_pp']:.2f},\\,{r['ci95_hi_pp']:.2f}]$"
        ym = f"{r['y_centrao_mean']:.3f}"
        lines.append(f"{labels.get(sample, sample)} & {coef} & {ci} & {ym} \\\\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\small",
        r"\item Notes: Outcome $y^{\mathrm{centrao}}_{it}$ equals one when deputy $i$ votes with the majority position of the Centrão bloc on roll-call $t$. The Centrão is defined as the nine-party cluster PP, PL, Republicanos, Solidariedade, União Brasil, PTB, Avante, PSD, MDB. The Lira sub-period split denotes the election of Arthur Lira (PP) as Chamber president on 1 February 2021. All coefficients estimated by IV-DML with full-clean controls, deputy demeaning, deputy-clustered standard errors, and the backlog instrument. Stars: $^{***}p<0.01$, $^{**}p<0.05$, $^{*}p<0.10$.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_t5_table.tex"
    out.write_text("\n".join(lines))
    print(f"\n  Saved {out}")


if __name__ == "__main__":
    consolidate_t1()
    print()
    consolidate_t2()
    print()
    consolidate_t3()
    print()
    consolidate_t4()
    print()
    consolidate_t5()
    print("\nDone.")
