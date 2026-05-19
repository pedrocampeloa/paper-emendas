# How Pork Buys Votes — Public Choice version

**Pedro Campelo Albuquerque, Daniel O. Cajueiro, Rafael Terra** — University of Brasilia

> Causal estimates of the effect of parliamentary amendments (emendas) on legislative alignment in Brazil's Chamber of Deputies, using Double Machine Learning with Instrumental Variables (DML-PLIV).
>
> Status: **rewriting for Public Choice** (May 2026). Pipeline rebuilt from raw to fix bugs in the previous version.

## TL;DR (preliminary, full DML still running)

- Per Public Choice feedback: main spec is **60d pre-vote window**; ±45d sym + 60d post-vote serve as robustness/placebo.
- Reduced control set (~30 vars) is the main spec; full ~191 vars is replication appendix.
- Bug-corrected pipeline now uses `dados/interim/panel/panel_features.csv` (NOT the old `features_v2.csv`).

## Quick start

```bash
# 1. Build data layer (≤5 min total for all 9 builders)
cd /Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara
for b in b01_load_raw_votes b02_build_proposicoes b03_build_deputados \
         b04_build_panel_base b05_build_features b06_build_emendas_panel \
         b07_build_ivs b08_build_coalizao b09_build_polarization; do
    python -m data_pipeline.builders.$b
done

# 2. Run paper estimation
cd paper-emendas/source
python 01_run_dml.py --reps 3                    # ~30 min
python 02_heterogeneities.py                     # ~10 min
python 03_decomposition.py                       # ~5 min
python 04_counterfactual_price.py --from-results # seconds

# 3. Verify cell-by-cell
jupyter notebook ../notebooks/verify.ipynb
```

## What's in `source/`

| Script | Output | Purpose |
|---|---|---|
| `_config.py` | — | Paths, control specs (REDUCED + FULL), hyper-params |
| `_utils.py` | — | `load_modeling_panel`, `run_plr`, `run_pliv`, `extract_row` |
| `01_run_dml.py` | `main_results.csv`, `main_fstage.csv`, `main_sargan.csv`, `main_falsification.csv` | PLR + PLIV per leg/IV/spec, plus 4 falsifications |
| `02_heterogeneities.py` | `heterogeneity_R2_1_*.csv` … `R2_5_*.csv` | Coalizão vs oposição, alinhamento histórico, ano eleitoral, votos apertados, tipo de bill |
| `03_decomposition.py` | `decomp_R2_7_*.csv` … `R2_9_*.csv` | RP-9 scenario, polarização, Oaxaca-Blinder gap |
| `04_counterfactual_price.py` | `price_legislative_support.csv`, `counterfactual_alignment.csv` | R$/pp + Y(T=0) |

## What's in `data_pipeline/` (root level)

Single shared pipeline across the four research papers. Replaces the old monolithic `build_features.py`. See `data_pipeline/README.md`.

| Output | Used by |
|---|---|
| `panel_base.csv` | all papers (replaces `features_v2.csv`) |
| `panel_features.csv` | all (the paper's controls) |
| `panel_emendas_pre.csv` | emendas, discursos |
| `iv_features.csv` | emendas |
| `coalizao_partido_data.csv` | emendas (heterogeneidades) |
| `polarizacao_votacao.csv` | emendas (R2.8) |

## Bugs fixed vs. previous version

See [`MUSTDO.md`](MUSTDO.md) for the full list. Highlights:

- **B0.1**: 542k duplicate rows in `iv_features.csv` → now 0 duplicates by construction (`b07`).
- **B0.3**: 11 idVotacao with 2 dates (votes spanning midnight) → now 1 canonical date per votação (`b01` uses `votacoes_file_.csv`).
- **B0.4**: unit interpretation issue (`+0.52 pp/R$M` was misreported) → now `pp_per_unit` column makes units explicit.
- **B0.5**: Sargan-Hansen rejecting silently → now reported with N-large discussion.

## What changed from the old paper

- **Sample size**: corrected panel has 869,902 (deputado × votação) rows for legs 55+56, vs the old paper's 1,288,167 (which was inflated by ~70% via merge bug).
- **Magnitudes**: in pp per R$1M (interpretable), not in standardized SD units (which the old paper conflated with pp).
- **Window**: main spec is now 60d pre-vote (Public Choice direction); old was ±45d.

## Documentation

- [`SPEC.md`](SPEC.md) — econometric specification, identification, units convention
- [`MUSTDO.md`](MUSTDO.md) — feedback dos professores e correções de bugs
- `notebooks/verify.ipynb` — cell-by-cell verification
- `data_pipeline/outputs/sanity/` — markdown sanity reports per builder
