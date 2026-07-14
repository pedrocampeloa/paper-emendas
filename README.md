# When Pork Changes Hands

**Coalition Presidentialism, Legislative Capture, and the Price of Legislative Support in Brazil**

**Pedro C. Campelo Albuquerque, Daniel O. Cajueiro, Rafael T. Menezes** — University of Brasília

---

## Overview

This repository contains the source code, analysis scripts, and LaTeX manuscript for a paper that estimates the causal effect of parliamentary amendments on legislative alignment in Brazil's Chamber of Deputies, covering the 55th and 56th Legislatures (2015--2022). The identification strategy is an instrumental-variables Double Machine Learning (PLIV-DML) framework, with the ministry-execution backlog as the instrument.

## Main finding

The canonical pork-for-votes coefficient reverses sign between two consecutive legislatures once the outcome tracks the Executive:

| Legislature      | $\hat\theta$ (pp per R$1M) |
|------------------|----------------------------|
| 55 (Temer)       | $+1.73^{**}$               |
| 56 (Bolsonaro)   | $-0.94^{***}$              |

When the outcome is redefined to track the party of the *Chamber president* (rather than the Executive), the Bolsonaro-era coefficient turns positive under the Lira presidency ($+0.33$ pp per R$1M), robust to the exclusion of PP and absorbed entirely by the broader Centrão. We interpret the pattern as **legislative capture** of the pork channel: the bargain did not vanish, it changed institutional principal.

## Repository layout

```
paper-emendas/
├── docs/
│   ├── figs/                     # Figures used in the paper (PDF)
│   └── tex/
│       ├── paper.tex             # Main manuscript
│       ├── refs.bib              # Bibliography
│       └── paper.pdf             # Compiled output
├── source/                       # Analysis scripts (numbered by workflow stage)
│   ├── _config.py, _utils.py     # Shared configuration and utilities
│   ├── 01_*..29_*.py             # Feature engineering and dataset construction
│   ├── 30_*..79_*.py             # Estimation, robustness, and heterogeneity
│   ├── 80_*..93_*.py             # Figures and non-parametric robustness (Causal IV Forest)
│   └── ...
├── results/                      # Output CSVs and progress logs (regenerable)
├── SPEC.md                       # Econometric specification
├── METHODOLOGY_LOG.md            # Chronological log of estimation runs
└── README.md
```

## Data

The paper uses administrative records from three public sources:

- **Chamber of Deputies Open Data** (`dadosabertos.camara.leg.br`) — roll-call votes, party orientations, deputy identifiers, and legislative composition.
- **Portal da Transparência** (`portaldatransparencia.gov.br`) — parliamentary amendments and ministry-level execution data.
- **CEAP register** (Câmara dos Deputados) — deputy characteristics used as controls.

Data are not committed to this repository. The `dados/` directory is expected at the level above the repo root; see `_config.py` for the assumed paths. The scripts that download and clean the raw data live in the parent monorepo (`../shared/`).

## Reproducibility

**Environment.** Python 3.11 with `doubleml`, `pandas`, `numpy`, `scikit-learn`, `statsmodels`, `econml` (for the Causal IV Forest robustness in Appendix A). Full environment defined in `../environment.yml` at the monorepo root.

**Reproducing the main estimates.**

```bash
# From paper-emendas/
conda activate loclin
python source/30_pliv_main.py                    # Table 1: main coefficients
python source/32_pliv_chamber_pres.py            # Table 6: Chamber-president outcome
python source/80_table1_figure2_updated.py       # Figure 1 + Table 2
python source/81_fig_polarization_trajectory.py  # Figure 2
```

**Estimation configuration.** All PLIV-DML runs use cross-fitted ElasticNet nuisance functions with `n_folds=3` and `n_reps=3` (paper's preferred spec). The ministry-execution backlog instrument is defined in `_config.py` as `IV_SETS["backlog"] = ["iv_q4_no_ytd", "iv_ytd_exec_pct"]`.

**Manuscript.** The paper compiles with `tectonic`:

```bash
cd docs/tex && tectonic paper.tex
```

## Files not in the repository

- Raw and interim data (see `Data` above)
- Trained model artifacts (regenerable from `source/`)
- Local build artifacts (see `.gitignore`)

## Citation

If you use this work, please cite the paper. A Zenodo DOI will be added upon submission.

## License

Code is released under the MIT License.
