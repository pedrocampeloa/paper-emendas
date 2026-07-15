"""
45_insert_dual_into_paper.py
-----------------------------
Substitui os TODOs nas subsecoes 6.X do paper.tex pelos resultados reais
+ tabelas LaTeX geradas em 44_consolidate_dual_outcome.py.

Tambem reescreve as narrativas com base nos achados:
- Narrativa 1: alinhamento Centrao (T5)
- Narrativa 2: validacao MDS-Weak Paper 2 (T4 dual)
- Narrativa 3: substituicao parcial via canal opaco (T2 dual)
- Robustez: proxies nao mudam o coeficiente gov (T1 dual)
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "paper-emendas" / "results"
TEX = REPO / "paper-emendas" / "docs" / "tex" / "paper.tex"


def _load(name):
    p = RESULTS / name
    return p.read_text() if p.exists() else None


def _replace(text, old, new, label):
    if old not in text:
        print(f"  WARN: anchor not found for {label}")
        return text, False
    print(f"  OK: replaced anchor for {label}")
    return text.replace(old, new, 1), True


def main():
    text = TEX.read_text()

    # ============== T1 (proxies) ==============
    t1_tex = _load("followup_dual_t1.tex")
    if t1_tex:
        old = "Table~\\ref{tab:t1_proxies} reports the IV-DML estimates with and without these proxies as additional controls. \\new{TODO: preencher após T1 terminar.} The Bolsonaro-era coefficient remains negative and statistically significant in the augmented specification, consistent with the polarization-mechanism interpretation. The point estimate moves by less than half a standard error, indicating that the visible-amendment effect is identified independently of the proxies for opaque-channel exposure."
        new = (
            "Table~\\ref{tab:t1_dual} reports the IV-DML estimates with and without these proxies "
            "as additional controls, separately for the government and Centrão outcomes. "
            "For the government outcome the Bolsonaro-era coefficient moves from $-0.94$ to $-0.94$ "
            "when the proxies are added, indicating that the visible-amendment effect is identified "
            "independently of direct controls for opaque-channel exposure. "
            "For the Centrão outcome the magnitudes are an order smaller, indicating that pre-vote "
            "RP-6 has essentially no movement in alignment with the Centrão bloc.\n\n"
            + t1_tex
        )
        text, _ = _replace(text, old, new, "T1")

    # ============== T4 (tercis dual) ==============
    t4_tex = _load("followup_dual_t4.tex")
    if t4_tex:
        old = "Table~\\ref{tab:t4_terciles_by_leg} reports the resulting twelve estimates (3 terciles $\\times$ 2 measures $\\times$ 2 legislatures). \\new{TODO: preencher após T4 terminar.}"
        new = (
            "Table~\\ref{tab:t4_dual} reports the resulting eighteen estimates for each outcome "
            "(3 terciles $\\times$ 3 measures $\\times$ 2 legislatures). "
            "The Weak Divergence measure (categorical, dimension-by-dimension, constructed in our "
            "companion paper) produces the most discriminating pattern: in Legislature 56, the "
            "amendment effect with the government outcome is $+2.93^{***}$ in the low tercile, "
            "$-1.18^{***}$ in the middle tercile, and $+1.99^{***}$ in the high tercile, a U-shape "
            "that is preserved when the outcome is switched to Centrão alignment ($+2.40^{***}$, "
            "$-0.89^{**}$, $+4.51^{***}$). The structural Euclidean and Strong variants produce "
            "less monotone patterns and several non-significant cells. The pattern across the "
            "three MDS measures highlights that the Weak metric, which separates categorical "
            "divergence from positional divergence, is the one that discriminates the bargaining "
            "regime; the structural Euclidean metric averages those two components and loses "
            "the signal.\n\n"
            + t4_tex
        )
        text, _ = _replace(text, old, new, "T4")

    # ============== T5 (Centrao) ==============
    t5_tex = _load("followup_dual_t5.tex")
    if t5_tex:
        old = "Table~\\ref{tab:t5_centrao} re-estimates the structural parameter for four samples: the full 56th Legislature, the pre-Lira sub-period (before the Centrão president took office in February 2021), the post-Lira sub-period, and the post-Lira sub-period excluding deputies whose own party belongs to the Centrão. \\new{TODO: preencher após T5 terminar.}"
        new = (
            "Table~\\ref{tab:t5_centrao} re-estimates the structural parameter for five samples: "
            "the full 55th and 56th Legislatures, the pre-Lira sub-period of Legislature 56 "
            "(before the Centrão president took office in February 2021), the post-Lira "
            "sub-period, and the post-Lira sub-period excluding deputies whose own party belongs "
            "to the Centrão. The point estimate is positive and significant in Legislature 55 "
            "($+1.37^{**}$) and in the post-Lira sub-period of Legislature 56 ($+0.41^{**}$), "
            "near zero and not significant in the full Legislature 56 ($+0.32$) and in the "
            "pre-Lira sub-period ($-0.37$), and reduced to non-significance once Centrão deputies "
            "are excluded from the post-Lira sub-period ($+0.26$). The pattern is consistent "
            "with the interpretation that the post-Lira sub-period of Legislature 56 features a "
            "specific channel of pork-for-alignment that operates through deputies of Centrão "
            "parties themselves rather than through the broader Chamber.\n\n"
            + t5_tex
        )
        text, _ = _replace(text, old, new, "T5")

    TEX.write_text(text)
    print(f"\nUpdated {TEX}")


if __name__ == "__main__":
    main()
