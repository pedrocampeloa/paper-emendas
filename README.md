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
.
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

Analysis-ready panel files (approximately 1.4 GB) are archived on Zenodo alongside the release of this repository. Raw dumps are not archived: they are freely downloadable from the public APIs above, and the scripts that build the panels from those dumps live in the parent monorepo (`../shared/` and `../data_pipeline/`). See the *Reproducibility* section below for details.

## Reproducibility

**Replication package DOI:** [10.5281/zenodo.21378905](https://doi.org/10.5281/zenodo.21378905)

**Environment.** Python 3.11 with `doubleml`, `pandas`, `numpy`, `scikit-learn`, `statsmodels`, and `econml` (for the Causal IV Forest robustness in Appendix A). See `environment.yml` for pinned versions.

**Analysis-ready data.** The panel files consumed by the estimation scripts (`panel_features.csv`, `panel_base.csv`, `panel_emendas_pre.csv`, `iv_features.csv`, and the auxiliary proxy panels) are archived on Zenodo alongside the frozen release of this repository. They total roughly 1.4 GB and are the direct inputs to the PLIV-DML runs. To reproduce all estimates without regenerating the panels from raw sources:

```bash
# 1. Clone this repository at the tagged release
git clone https://github.com/pedrocampeloa/pork-votes-brazil.git
cd pork-votes-brazil

# 2. Download the panel bundle from Zenodo and unpack under dados/interim/panel/
mkdir -p ../dados/interim/panel
curl -L -o panel_bundle.tar.gz \
  https://zenodo.org/records/21379015/files/panel_bundle.tar.gz
tar -xzf panel_bundle.tar.gz -C ../dados/interim/panel

# 3. Run any of the numbered scripts under source/
conda activate loclin
python source/30_pliv_main.py                    # Table 1
python source/32_pliv_chamber_pres.py            # Table 6
python source/80_table1_figure2_updated.py       # Figure 1 + Table 2
python source/81_fig_polarization_trajectory.py  # Figure 2
```

**Estimation configuration.** All PLIV-DML runs use cross-fitted ElasticNet nuisance functions with `n_folds=3` and `n_reps=3` (paper's preferred spec). The ministry-execution backlog instrument is defined in `_config.py` as `IV_SETS["backlog"] = ["iv_q4_no_ytd", "iv_ytd_exec_pct"]`. Point estimates and confidence intervals are written to `results/*.csv` and can be diffed against the archived CSVs to confirm exact replication.

**Feature engineering.** The scripts that build the panel files from the raw Câmara and Portal da Transparência dumps live in the parent monorepo (`../shared/` and `../data_pipeline/`) and are not archived on Zenodo. Regenerating the panel from raw sources requires those scripts plus the raw dumps (~10 GB), which are downloadable from the public APIs cited in the paper.

**Manuscript.** The paper compiles with `tectonic`:

```bash
cd docs/tex && tectonic paper.tex
```

## Files not in the repository

- Raw and interim data (see `Data` above)
- Trained model artifacts (regenerable from `source/`)
- Local build artifacts (see `.gitignore`)

## Citation

If you use this code, the archived panels, or the paper, please cite as:

```bibtex
@misc{campelo_cajueiro_menezes_2026,
  author       = {Campelo Albuquerque, Pedro Caiua and Cajueiro, Daniel Oliveira and Terra de Menezes, Rafael},
  title        = {When Pork Changes Hands: Coalition Presidentialism, Legislative Capture, and the Price of Legislative Support in Brazil},
  year         = 2026,
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.21378905},
  url          = {https://doi.org/10.5281/zenodo.21378905}
}
```

## License

Code is released under the MIT License (see `LICENSE`). The manuscript itself is subject to the copyright terms of the publishing journal.
