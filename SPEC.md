# SPEC — Paper 1: How Pork Buys Votes (v2 — Public Choice)

> **Spec do subprojeto paper-emendas**, versão de Maio 2026 após correções de pipeline e feedback dos professores. Leia junto com:
> - [`MUSTDO.md`](MUSTDO.md) — feedback consolidado dos professores + correções de bugs
> - [`README.md`](README.md) — overview e setup
> - [CLAUDE.md raiz](../CLAUDE.md) — convenções gerais

---

## Status (Maio 2026)

**Refatoração em andamento** após auditoria que encontrou:
- Bug de duplicação de IVs inflando N de 761k para 1.288k (B0.1)
- Votos atravessando meia-noite gerando 2 datas (B0.3)
- Erro de unidades em magnitudes reportadas (B0.4)
- Sargan-Hansen rejeitando silenciosamente (B0.5)

**Nova arquitetura** em `data_pipeline/` (raiz do projeto, compartilhada com forecasting/discursos/polarization). Scripts modulares com sanity tests.

**Decisão editorial (Daniel + Rafael, 02/05/2026):** alvo é **Public Choice**, não JPubE. Reescrita em curso conforme MUSTDO blocos 0–3.

---

## Pergunta de pesquisa

**Emendas parlamentares causam aumento no alinhamento de voto com o governo?**

Em coalition presidentialism brasileiro, o executivo distribui transferências fiscais direcionadas (emendas individuais) aos distritos dos deputados em troca de apoio legislativo. O paper estima o efeito causal usando **Double Machine Learning com variáveis instrumentais (DML-PLIV)** e analisa heterogeneidades por:
- coalizão vs oposição
- alinhamento histórico (rolling)
- ano eleitoral
- votos apertados
- importância da matéria

**Contribuição central:** identificação causal do **viés de cooptação** + **preço político** das emendas.

---

## Estrutura do projeto

```
paper-emendas/
├── MUSTDO.md                  ← feedback consolidado dos professores
├── SPEC.md                     ← este arquivo
├── README.md
├── source/                     ← scripts atuais (modelagem + heterogeneidades)
│   ├── _config.py              paths, controles, hyper-params
│   ├── _utils.py               load_modeling_panel, run_plr, run_pliv
│   ├── 01_run_dml.py           PLR + PLIV + falsificações
│   ├── 02_heterogeneities.py   R2.1–R2.5
│   ├── 03_decomposition.py     R2.7–R2.9
│   └── 04_counterfactual_price.py    R$/pp + Y(T=0)
├── source-old/                 ← código antigo (read-only, para referência)
├── docs/                       ← LaTeX (paper revisado, em andamento)
├── docs-old/                   ← paper antigo (não tocar)
├── notebooks/
│   └── verify.ipynb            ← debug célula-a-célula
├── results/                    ← outputs de 01–04
└── tests/                      (opcional, ainda não escrito)
```

E na raiz do projeto:

```
data_pipeline/                  ← compartilhado (todos os papers)
├── builders/
│   ├── _common.py
│   ├── _sanity.py
│   ├── b01_load_raw_votes.py
│   ├── b02_build_proposicoes.py
│   ├── b03_build_deputados.py
│   ├── b04_build_panel_base.py    → panel_base.csv (substitui features_v2)
│   ├── b05_build_features.py      → panel_features.csv (212 cols)
│   ├── b06_build_emendas_panel.py → panel_emendas_{pre,sym,post}.csv
│   ├── b07_build_ivs.py           → iv_features.csv (sem duplicatas)
│   ├── b08_build_coalizao.py      → coalizao_partido_data.csv
│   └── b09_build_polarization.py  → polarizacao_votacao.csv
└── outputs/sanity/              relatórios markdown por builder
```

Outputs físicos vão para `dados/interim/panel/` (separado dos legados em `dados/interim/`).

---

## Pipeline de dados

### Reproduzir do zero

```bash
cd /Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara

# 1. Build data layer (≤ 5 minutos para todos os 9 builders)
python -m data_pipeline.builders.b01_load_raw_votes
python -m data_pipeline.builders.b02_build_proposicoes
python -m data_pipeline.builders.b03_build_deputados
python -m data_pipeline.builders.b04_build_panel_base
python -m data_pipeline.builders.b05_build_features
python -m data_pipeline.builders.b06_build_emendas_panel
python -m data_pipeline.builders.b07_build_ivs
python -m data_pipeline.builders.b08_build_coalizao
python -m data_pipeline.builders.b09_build_polarization

# 2. Run paper estimation
cd paper-emendas/source
python 01_run_dml.py --reps 3              # ~30 min
python 02_heterogeneities.py               # ~10 min
python 03_decomposition.py                 # ~5 min
python 04_counterfactual_price.py --from-results
```

### Saídas

| Arquivo | Conteúdo | Origem |
|---|---|---|
| `dados/interim/panel/panel_base.csv` | (deputado, votação) base | b04 |
| `dados/interim/panel/panel_features.csv` | + 212 features numéricas | b05 |
| `dados/interim/panel/panel_emendas_pre.csv` | + emenda 60d pré-voto (MAIN) | b06 |
| `dados/interim/panel/iv_features.csv` | 4 IVs corrigidos | b07 |
| `dados/interim/panel/coalizao_partido_data.csv` | (partido, data) → status | b08 |
| `dados/interim/panel/polarizacao_votacao.csv` | índices por votação | b09 |
| `paper-emendas/results/main_results.csv` | PLR + PLIV principal | 01 |
| `paper-emendas/results/heterogeneity_*.csv` | R2.1–R2.5 | 02 |
| `paper-emendas/results/decomp_*.csv` | R2.7–R2.9 | 03 |
| `paper-emendas/results/price_legislative_support.csv` | R$/pp | 04 |

---

## Especificação econométrica

### Outcome
`alinhamento` ∈ {0, 1}: 1 se voto do deputado coincide com orientação do governo.

### Treatment
`emenda_M` em **R$ milhões** (raw, derivado de `emenda_valor / 1e6` no `_utils.py`).
Janela principal: **60 dias antes do voto** (`panel_emendas_pre.csv`). Por feedback de Public Choice, isso conversa com a história de barganha pré-voto.

### Controles

**Especificação principal (~30 vars)** — listados em `_config.CONTROLS_REDUCED`:
- party FE / UF FE
- bill type (PEC, MPV, PLP, PL, MSC) e top-10 temas
- mesa diretora, profissão, idade, escolaridade
- ano eleitoral (federal e municipal)
- coalizão vs oposição

**Especificação completa (~191 vars)** — todos os numéricos não-leakage de `panel_features.csv`. Roda com `--legacy` para apêndice.

### Identificação

**PLR (Partially Linear Regression)** — DML naive, primeiro estágio.
**PLIV (PLR with IV)** — DML com instrumentos para tratamento endógeno.

**IVs:**
| IV | Nível | Lógica |
|---|---|---|
| `iv_fiscal_q4` | Vote-level | Vote em Out-Dez |
| `iv_fiscal_pressure` | Vote-level | 1/(dias até 31/dez + 1) |
| `iv_q4_no_ytd` | Dep × Vote | Q4 × YTD < 10% (backlog) |
| `iv_ytd_exec_pct` | Dep × Vote | Fração executada antes do voto |

CMO foi removido (paper antigo já excluía em apêndice).

### Inferência

- DML cross-fitting: K=3 folds, R=3 repetições
- ElasticNetCV para nuisance functions
- SE por DML standard formula
- Sargan-Hansen reportado para todos os specs sobreidentificados (não mais omitido como no paper antigo)

---

## Magnitudes reportadas — convenção de unidades

Nas saídas (`main_results.csv`):

| Coluna | Significado |
|---|---|
| `coef_sd` | DML output: efeito de 1 SD de T sobre P(Y=1) |
| `coef_per_unit` | `coef_sd / std_T` → efeito de R$1M sobre P(Y=1) |
| **`pp_per_unit`** | **`100 × coef_per_unit` → pontos percentuais por R$1M** ← reporting principal |
| `pp_per_sd` | `100 × coef_sd` → pp por 1 SD de emenda |
| `std_T` | desvio-padrão de T (em R$M) |

**No paper, sempre reportar `pp_per_unit` ou `pp_per_sd`**, não `coef_sd` (que vai criar ambiguidade como no paper antigo).

---

## Decisões de design importantes

- **Excluir 57ª**: dados de emendas só até 2024.
- **Excluir CMO**: instrumento fraco; paper antigo já excluía.
- **Painel `panel_emendas_pre` (60d antes) = principal** (Public Choice).
- **Controles reduzidos** = principal; full = apêndice.
- **Falsificações reportadas** mesmo se algumas falharem (transparência).
- **Sargan reportado** sempre, com nota sobre hipersensibilidade em N grande.

---

## O que NÃO fazer

- Não usar `features_v2.csv` para nova versão do paper (use `panel_features.csv`).
- Não usar `iv_features.csv` antigo (use `dados/interim/panel/iv_features.csv`).
- Não interpretar `coef_std` do paper antigo como pp (era pp/100).
- Não incluir 57ª.

---

## Referências chave (canais com professores)

- 01-02/05/2026: Daniel + Rafael alinharam Public Choice como alvo.
- MUSTDO.md consolida 12 itens (BLOCO 0–3).
