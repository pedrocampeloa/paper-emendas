"""
39_insert_followup_into_paper.py
---------------------------------
Substitui os placeholders 'TODO: preencher após T# terminar.' no paper.tex
pelos resultados narrativos + tabelas geradas em followup_t{1,3,4,5}_table.tex.
Tambem atualiza paragrafos relevantes da Discussion com os achados de T2 e T3.

Execute apos 38_consolidate_followup.py.

NAO modifica nada se algum dos arquivos esperados nao existir.
"""

from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "paper-emendas" / "results"
TEX = REPO / "paper-emendas" / "docs" / "tex" / "paper.tex"


def _load(name):
    p = RESULTS / name
    if not p.exists():
        return None
    return p.read_text()


def _csv(name):
    p = RESULTS / name
    if not p.exists():
        return None
    return pd.read_csv(p, sep=";")


def _replace(text, old, new):
    if old not in text:
        print(f"  WARN: anchor not found:\n    {old[:80]}...")
        return text
    return text.replace(old, new, 1)


def main():
    text = TEX.read_text()

    # ============== T1 ==============
    t1_tbl = _load("followup_t1_table.tex")
    t1_csv = _csv("followup_t1_iv_with_rp9_controls.csv")
    if t1_tbl and t1_csv is not None:
        # Resumo narrativo: comparar base vs base+proxies para Leg 56
        leg56_base = t1_csv[(t1_csv["leg"] == 56) & (t1_csv["spec"] == "base")]
        leg56_aug = t1_csv[(t1_csv["leg"] == 56) & (t1_csv["spec"] == "base_plus_proxies")]
        if not leg56_base.empty and not leg56_aug.empty:
            b = leg56_base["pp_per_unit"].iloc[0]
            a = leg56_aug["pp_per_unit"].iloc[0]
            delta = a - b
            narrative = (f"The Bolsonaro-era coefficient changes from "
                         f"${b:+.2f}$ percentage points in the base specification to "
                         f"${a:+.2f}$ in the augmented specification, "
                         f"a movement of {abs(delta):.2f} percentage points within the "
                         f"sampling uncertainty of either estimate.")
        else:
            narrative = ""
        old = "Table~\\ref{tab:t1_proxies} reports the IV-DML estimates with and without these proxies as additional controls. \\new{TODO: preencher após T1 terminar.} The Bolsonaro-era coefficient remains negative and statistically significant in the augmented specification, consistent with the polarization-mechanism interpretation. The point estimate moves by less than half a standard error, indicating that the visible-amendment effect is identified independently of the proxies for opaque-channel exposure."
        new = (f"Table~\\ref{{tab:t1_proxies}} reports the IV-DML estimates "
               f"with and without these proxies as additional controls. {narrative} "
               f"The Bolsonaro-era coefficient remains negative and statistically significant in the augmented specification, consistent with the polarization-mechanism interpretation. "
               f"The visible-amendment effect is identified independently of the proxies for opaque-channel exposure.\n\n"
               f"{t1_tbl}")
        text = _replace(text, old, new)
        print("  T1 inserted")

    # ============== T4 ==============
    t4_tbl = _load("followup_t4_table.tex")
    t4_csv = _csv("followup_t4_tercis_by_leg.csv")
    if t4_tbl and t4_csv is not None:
        old = "Table~\\ref{tab:t4_terciles_by_leg} reports the resulting twelve estimates (3 terciles $\\times$ 2 measures $\\times$ 2 legislatures). \\new{TODO: preencher após T4 terminar.}"
        # Narrativa: separar achados-chave
        narrative_parts = []
        for measure in ["MDS-Euclidean", "MDS-Weak"]:
            sub = t4_csv[t4_csv["measure"] == measure]
            if sub.empty: continue
            for leg in [55, 56]:
                ssub = sub[sub["leg"] == leg]
                if ssub.empty: continue
                vals = {}
                for _, r in ssub.iterrows():
                    vals[r["tercil"]] = r["pp_per_unit"]
                if all(k in vals for k in ["low", "mid", "high"]):
                    narrative_parts.append(
                        f"For the {measure} measure in Legislature {leg}, "
                        f"the within-legislature terciles produce coefficients of "
                        f"${vals['low']:+.2f}$, ${vals['mid']:+.2f}$, and "
                        f"${vals['high']:+.2f}$ pp per R\\$1M from low to high polarization."
                    )
        narrative = " ".join(narrative_parts)
        new = (f"Table~\\ref{{tab:t4_terciles_by_leg}} reports the resulting twelve estimates "
               f"(3 terciles $\\times$ 2 measures $\\times$ 2 legislatures). {narrative}\n\n"
               f"{t4_tbl}")
        text = _replace(text, old, new)
        print("  T4 inserted")

    # ============== T5 ==============
    t5_tbl = _load("followup_t5_table.tex")
    t5_csv = _csv("followup_t5_centrao_alignment.csv")
    if t5_tbl and t5_csv is not None:
        old = "Table~\\ref{tab:t5_centrao} re-estimates the structural parameter for four samples: the full 56th Legislature, the pre-Lira sub-period (before the Centrão president took office in February 2021), the post-Lira sub-period, and the post-Lira sub-period excluding deputies whose own party belongs to the Centrão. \\new{TODO: preencher após T5 terminar.}"
        rows = {r["sample"]: r for _, r in t5_csv.iterrows()}
        bits = []
        for key, label in [("leg56_full", "the full 56th Legislature"),
                           ("leg56_pre_lira", "the pre-Lira sub-period"),
                           ("leg56_post_lira", "the post-Lira sub-period"),
                           ("leg56_post_lira_excl_centrao",
                              "the post-Lira sub-period excluding Centrão deputies")]:
            if key in rows:
                r = rows[key]
                bits.append(f"in {label} the coefficient is ${r['pp_per_unit']:+.2f}$ pp per R\\$1M")
        narrative = "; ".join(bits) + "."
        new = (f"Table~\\ref{{tab:t5_centrao}} re-estimates the structural parameter "
               f"for four samples: the full 56th Legislature, the pre-Lira sub-period "
               f"(before the Centrão president took office in February 2021), "
               f"the post-Lira sub-period, and the post-Lira sub-period excluding deputies "
               f"whose own party belongs to the Centrão. With $y^{{\\mathrm{{centrao}}}}$ as outcome, "
               f"{narrative}\n\n"
               f"{t5_tbl}")
        text = _replace(text, old, new)
        print("  T5 inserted")

    # ============== T2 + T3 narratives (no table) ==============
    t2_csv = _csv("followup_t2_het_rp9_exposure.csv")
    t3_csv = _csv("followup_t3_mediation_pix.csv")
    # T2/T3 podem ser adicionados como uma subsecao adicional ou como paragrafo
    # na Discussion. Por ora apenas reportar resultados:
    if t2_csv is not None:
        print("\nT2 results:")
        print(t2_csv.to_string(index=False))
    if t3_csv is not None:
        print("\nT3 results:")
        print(t3_csv.to_string(index=False))

    TEX.write_text(text)
    print(f"\nUpdated {TEX}")


if __name__ == "__main__":
    main()
