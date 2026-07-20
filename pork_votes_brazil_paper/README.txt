When Pork Changes Hands: Coalition Presidentialism, Legislative Capture,
and the Price of Legislative Support in Brazil.

Pedro C. Campelo Albuquerque, Daniel O. Cajueiro, Rafael T. Menezes
University of Brasilia.

Self-contained manuscript package.

Contents
--------
paper.tex   Manuscript source (LaTeX, elsarticle class, natbib author-year).
refs.bib    Bibliography (BibTeX, natbib style plainnat).
paper.pdf   Compiled manuscript (36 pages).
figs/       Four PDF figures referenced by paper.tex.

Compile
-------
Any modern TeX distribution (TeX Live 2024+, MacTeX, MikTeX) or tectonic
should build the paper without external dependencies. Recommended:

    tectonic paper.tex

or

    pdflatex paper.tex && bibtex paper && pdflatex paper.tex && pdflatex paper.tex

The compilation writes paper.pdf next to paper.tex.

Replication code and data
-------------------------
Code, analysis scripts, and analysis-ready panel data are archived at:

    Zenodo:  https://doi.org/10.5281/zenodo.21378905
    GitHub:  https://github.com/pedrocampeloa/pork-votes-brazil
