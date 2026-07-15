"""
44_consolidate_dual_outcome.py
-------------------------------
Consolida resultados T2/T3/T4/T5 + T1 corrigido para ambos outcomes:
- y = alinhamento com governo
- y = alinhamento com Centrao

Gera tabelas LaTeX prontas para insercao no paper:
- followup_dual_t1.tex (T1 IV-DML com proxies, ambos outcomes)
- followup_dual_t2.tex (T2 het RP-9 exposure, ambos outcomes)
- followup_dual_t3.tex (T3 mediation Pix, ambos outcomes)
- followup_dual_t4.tex (T4 tercis MDS, ambos outcomes)
- followup_dual_t5.tex (T5 Centrao sub-samples — somente Centrao outcome)

E uma tabela mestre comparativa:
- followup_master_comparison.csv (todos resultados, lado a lado gov/centrao)
"""

from pathlib import Path
import pandas as pd
import numpy as np

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "paper-emendas" / "results"


def _stars(p):
    if pd.isna(p): return ""
    if p < 0.01: return "^{***}"
    if p < 0.05: return "^{**}"
    if p < 0.10: return "^{*}"
    return ""


def _coef(v, p, dec=2):
    if pd.isna(v): return "---"
    return f"${v:+.{dec}f}{_stars(p)}$"


def load_results():
    """Carrega todos os CSVs disponiveis."""
    bag = {}
    for fp in RESULTS.glob("followup*.csv"):
        if "_table" in fp.name:
            continue
        try:
            bag[fp.stem] = pd.read_csv(fp, sep=";")
        except Exception as e:
            print(f"  fail load {fp.name}: {e}")
    return bag


def build_t4_dual_table(bag):
    """Tabela T4 lado a lado: gov vs centrao."""
    g = bag.get("followup_t4_tercis_by_leg")
    c = bag.get("followup_centrao_t4_tercis_by_leg")
    if g is None or c is None:
        print("  T4 dual: missing data")
        return
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{Polarization terciles within each legislature, dual outcome.}}",
        r"\label{tab:t4_dual}",
        r"\begin{threeparttable}",
        r"\footnotesize",
        r"\begin{tabular}{llcccccc}",
        r"\toprule",
        r" & & \multicolumn{3}{c}{Government outcome} & \multicolumn{3}{c}{Centrão outcome} \\",
        r"\cmidrule(lr){3-5} \cmidrule(lr){6-8}",
        r"Measure & Leg & Low & Mid & High & Low & Mid & High \\",
        r"\midrule",
    ]
    for measure in ["MDS-Euclidean", "MDS-Weak", "MDS-Strong"]:
        for leg in [55, 56]:
            row = [measure if leg == 55 else "", str(leg)]
            for tlabel in ["low", "mid", "high"]:
                rg = g[(g["measure"] == measure) & (g["leg"] == leg) & (g["tercil"] == tlabel)]
                row.append(_coef(rg["pp_per_unit"].iloc[0], rg["pval"].iloc[0]) if not rg.empty else "---")
            for tlabel in ["low", "mid", "high"]:
                rc = c[(c["measure"] == measure) & (c["leg"] == leg) & (c["tercil"] == tlabel)]
                row.append(_coef(rc["pp_per_unit"].iloc[0], rc["pval"].iloc[0]) if not rc.empty else "---")
            lines.append(" & ".join(row) + r" \\")
        lines.append(r"\midrule" if measure != "MDS-Strong" else "")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\footnotesize",
        r"\item Notes: Each cell reports the IV-DML coefficient (pp per R\$1M) on the pre-vote committed amendment, estimated by PLIV-DML with full-clean controls, deputy demeaning, and deputy-clustered standard errors. Terciles are computed within each legislature. The MDS-Euclidean measure is the structural distance in multidimensional scaling space; MDS-Weak isolates dimension-by-dimension categorical divergence; MDS-Strong captures axis-aligned divergence. The government outcome equals one when the deputy votes with the executive's directional orientation; the Centrão outcome equals one when the deputy votes with the majority position of the Centrão bloc on the same roll-call. Stars: $^{***}p<0.01$, $^{**}p<0.05$, $^{*}p<0.10$.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_dual_t4.tex"
    out.write_text("\n".join(lines))
    print(f"  saved {out.name}")


def build_t2_dual_table(bag):
    g = bag.get("followup_t2_het_rp9_exposure")
    c = bag.get("followup_centrao_t2_het_rp9_exposure")
    if g is None or c is None: return
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{Heterogeneity by RP-9 exposure in Legislature 56, dual outcome.}}",
        r"\label{tab:t2_dual}",
        r"\begin{threeparttable}",
        r"\small",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Subgroup & Gov. outcome & Centrão outcome \\",
        r"\midrule",
    ]
    for subgroup, label in [("rp9_exposed", "RP-9 supporters ($d_{rp9}=1$)"),
                            ("rp9_not_exposed", "Non-supporters ($d_{rp9}=0$)")]:
        rg = g[g["subgroup"] == subgroup]
        rc = c[c["subgroup"] == subgroup]
        gov_str = _coef(rg["pp_per_unit"].iloc[0], rg["pval"].iloc[0]) if not rg.empty else "---"
        cen_str = _coef(rc["pp_per_unit"].iloc[0], rc["pval"].iloc[0]) if not rc.empty else "---"
        lines.append(f"{label} & {gov_str} & {cen_str} \\\\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\small",
        r"\item Notes: IV-DML estimates of the pork-for-votes effect (pp per R\$1M) in Legislature 56, split by RP-9 supporter status. A deputy is classified as RP-9 supporter if she appears as \emph{parlamentar solicitante} of at least one rapporteur transfer in 2020--2022 in the disclosure files released under ADPF 854 (3.2\% of deputy-vote observations). The estimates show that the visible-amendment backfire concentrates in the non-supporters; the effect is statistically indistinguishable from zero among supporters, consistent with substitution between visible (RP-6) and opaque (RP-9) channels.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_dual_t2.tex"
    out.write_text("\n".join(lines))
    print(f"  saved {out.name}")


def build_t3_dual_table(bag):
    g = bag.get("followup_t3_mediation_pix")
    c = bag.get("followup_centrao_t3_mediation_pix")
    if g is None or c is None: return
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{ABS mediation with Pix share as mediator, dual outcome.}}",
        r"\label{tab:t3_dual}",
        r"\begin{threeparttable}",
        r"\small",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"Sample & \multicolumn{2}{c}{Gov. outcome} & \multicolumn{2}{c}{Centrão outcome} \\",
        r"\cmidrule(lr){2-3} \cmidrule(lr){4-5}",
        r" & Total & Prop. mediated & Total & Prop. mediated \\",
        r"\midrule",
    ]
    for leg, label in [("pooled", "Pooled"), ("leg55", "Leg 55"), ("leg56", "Leg 56")]:
        rg = g[g["leg"] == leg]
        rc = c[c["leg"] == leg]
        gt = f"{rg['beta_T_total'].iloc[0]:+.4f}" if not rg.empty else "---"
        gp = f"{rg['prop_mediated'].iloc[0]*100:+.1f}\\%" if not rg.empty else "---"
        ct = f"{rc['beta_T_total'].iloc[0]:+.4f}" if not rc.empty else "---"
        cp = f"{rc['prop_mediated'].iloc[0]*100:+.1f}\\%" if not rc.empty else "---"
        lines.append(f"{label} & {gt} & {gp} & {ct} & {cp} \\\\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\small",
        r"\item Notes: Acharya-Blackwell-Sen decomposition with Pix share of RP-6 as the mediator. Coefficients estimated by OLS with cluster-robust standard errors at the deputy level. The total effect is the OLS regression of outcome on treatment; the proportion mediated is the share of the total effect that flows through the mediator. The near-zero indirect share within each legislature indicates that Pix does not operate as a structural mediator of the pork-for-votes relationship; the larger pooled value is mechanically driven by the small total effect in the pooled regression (which averages opposite-signed legislature effects) rather than by a substantive role for the Pix modality.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_dual_t3.tex"
    out.write_text("\n".join(lines))
    print(f"  saved {out.name}")


def build_t5_table(bag):
    """T5 e' so' do outcome Centrao (nao tem versao gov)."""
    df = bag.get("followup_t5_centrao_alignment")
    if df is None: return
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{Outcome alternative: alignment with the Centrão bloc.}}",
        r"\label{tab:t5_centrao}",
        r"\begin{threeparttable}",
        r"\small",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Sample & $\hat\theta$ (pp/R\$1M) & 95\% CI & $\bar{y}^{\mathrm{centrao}}$ \\",
        r"\midrule",
    ]
    labels = {
        "leg55_full": "Legislature 55",
        "leg56_full": "Legislature 56",
        "leg56_pre_lira": r"\quad Pre-Lira (Jan 2019 -- Jan 2021)",
        "leg56_post_lira": r"\quad Post-Lira (Feb 2021 -- Dec 2022)",
        "leg56_post_lira_excl_centrao": r"\quad Post-Lira, excluding Centrão deputies",
    }
    for s in ["leg55_full", "leg56_full", "leg56_pre_lira", "leg56_post_lira",
              "leg56_post_lira_excl_centrao"]:
        r = df[df["sample"] == s]
        if r.empty: continue
        r = r.iloc[0]
        coef = _coef(r["pp_per_unit"], r["pval"])
        ci = f"$[{r['ci95_lo_pp']:+.2f},\\,{r['ci95_hi_pp']:+.2f}]$"
        ym = f"{r['y_centrao_mean']:.3f}"
        lines.append(f"{labels.get(s, s)} & {coef} & {ci} & {ym} \\\\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\small",
        r"\item Notes: IV-DML estimates of the pork-for-votes effect (pp per R\$1M) when the outcome is alignment with the Centrão bloc majority on the same roll-call. The Centrão is defined as PP, PL, Republicanos, Solidariedade, União Brasil, PTB, Avante, PSD, and MDB. The Lira sub-period split denotes the election of Arthur Lira (PP) as Chamber president on 1 February 2021. Stars: $^{***}p<0.01$, $^{**}p<0.05$, $^{*}p<0.10$.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_dual_t5.tex"
    out.write_text("\n".join(lines))
    print(f"  saved {out.name}")


def build_master_csv(bag):
    """Tabela CSV mestre comparando gov vs centrao em todas as analises."""
    rows = []
    pairs = [
        ("followup_t2_het_rp9_exposure", "followup_centrao_t2_het_rp9_exposure", "T2_het", ["subgroup"]),
        ("followup_t4_tercis_by_leg", "followup_centrao_t4_tercis_by_leg", "T4_tercis", ["measure", "leg", "tercil"]),
    ]
    for gn, cn, label, keys in pairs:
        g = bag.get(gn)
        c = bag.get(cn)
        if g is None or c is None: continue
        merged = g[keys + ["pp_per_unit", "pval"]].merge(
            c[keys + ["pp_per_unit", "pval"]],
            on=keys, suffixes=("_gov", "_centrao"))
        merged["analysis"] = label
        rows.append(merged)
    if rows:
        master = pd.concat(rows, ignore_index=True)
        out = RESULTS / "followup_master_comparison.csv"
        master.to_csv(out, sep=";", index=False)
        print(f"  saved {out.name} ({len(master)} rows)")
        print(master.to_string(index=False))


def build_t1_dual_table(bag):
    """T1 corrigido lado a lado: gov vs centrao."""
    g = bag.get("followup_t1_iv_corrected_gov")
    c = bag.get("followup_t1_iv_corrected_centrao")
    if g is None or c is None:
        print("  T1 dual: missing corrected data")
        return
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\new{IV-DML estimates with and without controls for opaque-channel exposure, dual outcome.}}",
        r"\label{tab:t1_dual}",
        r"\begin{threeparttable}",
        r"\small",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Specification & Gov. outcome & Centrão outcome \\",
        r"\midrule",
    ]
    for leg in [55, 56]:
        for spec, slabel in [("base_pure", "Base spec"),
                              ("base_plus_proxies", "Base + proxies")]:
            rg = g[(g["leg"] == leg) & (g["spec"] == spec)]
            rc = c[(c["leg"] == leg) & (c["spec"] == spec)]
            label = f"Leg {leg} {slabel}"
            gstr = _coef(rg["pp_per_unit"].iloc[0], rg["pval"].iloc[0]) if not rg.empty else "---"
            cstr = _coef(rc["pp_per_unit"].iloc[0], rc["pval"].iloc[0], dec=4) if not rc.empty else "---"
            lines.append(f"{label} & {gstr} & {cstr} \\\\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\begin{tablenotes}",
        r"\small",
        r"\item Notes: Coefficients in percentage points per R\$1M of pre-vote committed amendment (Centrão column reported with four decimals because magnitudes are an order smaller). Base spec is the preferred PLIV-DML with full-clean controls plus party fixed effects, after explicit exclusion of the multi-RP variables and the secret-budget proxies from the control set. Augmented spec adds $d_{\mathrm{rp9}}$ and $\mathrm{share}_{\mathrm{pix}}$ as additional controls. The Bolsonaro-era coefficient with the government outcome is unchanged by the augmentation, indicating that the visible-amendment backfire is identified independently of direct controls for opaque-channel exposure. The Centrão outcome estimates are an order of magnitude smaller; under either specification, visible amendments produce essentially no movement in alignment with the Centrão bloc.",
        r"\end{tablenotes}",
        r"\end{threeparttable}",
        r"\end{table}",
    ]
    out = RESULTS / "followup_dual_t1.tex"
    out.write_text("\n".join(lines))
    print(f"  saved {out.name}")


if __name__ == "__main__":
    bag = load_results()
    print(f"Loaded {len(bag)} result files:")
    for k in sorted(bag.keys()):
        print(f"  {k}: {len(bag[k])} rows")
    print()

    build_t1_dual_table(bag)
    build_t2_dual_table(bag)
    build_t3_dual_table(bag)
    build_t4_dual_table(bag)
    build_t5_table(bag)
    build_master_csv(bag)
    print("\nDone.")
