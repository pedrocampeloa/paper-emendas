# SPEC — Paper 3: When Pork-Barrel Backfires (Public Choice)

> **Spec atualizado em Junho 2026** após defesa de qualificação (02/06/2026).
> Banca: Daniel Cajueiro, Bernardo Mueller, Rafael Terra.
> Alvo: **Public Choice** (decidido em 02/05/2026).

---

## ⚠️ Documentos de leitura prioritária

Em ordem:

1. **[`STATE_OF_PLAY.md`](STATE_OF_PLAY.md)** — documento mestre em português, atualizado constantemente. Mostra TODAS as bases, resultados, narrativas candidatas, dúvidas. **Esta é a fonte principal de verdade.**
2. **[`MUSTDO_v2.md`](MUSTDO_v2.md)** — feedback consolidado pós-defesa, itens de ação organizados por prioridade.
3. **[`METHODOLOGY_LOG.md`](METHODOLOGY_LOG.md)** — log vivo de tudo que foi rodado.

Documentos arquivados em `_archive/` (pré-defesa, não usar mais):
- `MUSTDO_pre_defesa.md` (anterior `MUSTDO.md`)
- `CHECKLIST_PROFS.md`
- `IV_VALIDATION.md`
- `METHODOLOGY_LOG_may.pdf`

---

## Pergunta de pesquisa (Junho 2026)

**Por que o efeito causal de emendas parlamentares sobre alinhamento legislativo mudou de sinal entre o governo Temer e Bolsonaro?**

Pereira-Mueller (2004) e a literatura subsequente documentaram que pork compra alinhamento sob coalition presidentialism brasileiro. Nossa estimativa IV-DML mostra:

- **Legislatura 55 (Temer)**: +1.73 pp por R$1M (canônico)
- **Legislatura 56 (Bolsonaro)**: −0.94 pp por R$1M (sign reversal)

O paper investiga mecanismos do sign reversal através de heterogeneidades, mediação e outcome alternativos. Resultado central candidato: **a polarização do tipo Weak Divergence (medida do Paper 2) discrimina o regime**, e a função distributiva do pork migrou parcialmente para o canal opaco RP-9 e para o controle de agenda pelo Centrão sob Lira.

---

## Status atual (18/06/2026)

### Pipeline rodando
Rodada definitiva `n_folds=3, n_reps=3` (idêntica ao main paper original), substituindo rodadas anteriores que usaram `n_reps=1` (com alta variância Monte Carlo). Script: `source/50_full_followup_n3.py`. Output incremental em `results/n3_progress.md`.

### Já rodado (confirmado)
- ✅ T3 OLS mediação Pix (6 amostras, gov + centrão)
- ✅ T5 PLIV Centrão sub-amostras (5 amostras): leg55_full +0.06, leg56_full −0.67**, pre_lira +0.87***, post_lira +0.40**, post_lira_excl_centrao +0.24
- ✅ T2 PLIV RP-9 exposure heterogeneity gov (2 amostras): exposed −0.31, not_exposed −0.99***
- ✅ T2 PLIV centrão (2 amostras): exposed −0.26, not_exposed −0.68**

### Em curso / fila
- 🟡 T4 PLIV tercis MDS por leg (36 PLIVs, ~3-5 dias)
- ⏳ T1 PLIV IV com proxies (8 PLIVs, ~1 dia)

---

## Bases de dados disponíveis

### Painel principal (`dados/interim/panel/`)

| Arquivo | Conteúdo | Cobertura |
|---|---|---|
| `panel_features.csv` | 1,3M (deputado×votação), 283 cols | 2015-02 a 2026-04 |
| `panel_features.csv` (filtrado) | **869.902** obs Leg 55 + Leg 56 | 2015-02 a 2022-12 |
| `panel_emendas_pre.csv` | + emenda 60d pré-voto (RP-6) | 2015-2022 |
| `iv_features.csv` | 4 IVs corrigidos | 2015-2022 |
| `coalizao_partido_data.csv` | (partido, data) → status | 2015-2022 |
| `polarizacao_votacao.csv` | índices intra-vote | 2015-2022 |

### Multi-RP (novo, junho 2026)

| Arquivo | Conteúdo | Granularidade |
|---|---|---|
| `panel_emendas_pre_multi_rp.csv` | T_rp6, T_rp6_pix, T_rp8, T_rp9_imputed por deputado×votação | 60d pré-voto |
| `panel_secret_budget_proxies.csv` | d_rp9_solicitante, share_pork_opaco, share_pix, n_apoiamentos_opaco | deputado×ano |

### Polarização (`paper-polarization/data/processed/`)

| Arquivo | Medida |
|---|---|
| `average_mds_distances_euclidean.csv` | MDS-Euclidean (estrutural) |
| `average_mds_distances_forte.csv` | MDS-Strong (axis-aligned) |
| `average_mds_distances_fraca.csv` | MDS-Weak (categórica dim-por-dim) ← Paper 2 |

### Discursos (`dados/interim/`)

| Arquivo | Conteúdo |
|---|---|
| `model_speech_sentiment.csv` | BERTimbau (33.517 discursos) |
| `model_xlm_sentiment.csv` | XLM-RoBERTa Cardiff |
| `model_anti_gov_nli.csv` | mDeBERTa anti-government NLI |

### Bases externas baixadas (`dados/raw/orcamento/`) — 1,1 GB

- Portal Transparência bulk 2014-2026 (93.715 emendas todas RPs)
- Tesouro CKAN (388.496 linhas mensais emendas, 19 XLSX anuais despesas União)
- SICONV completo (296k emendas + 291k apoiadores + 283k convênios)
- Câmara CMO PDFs (Atos Conjuntos RP-9 + Recibos comissões)
- GitHub gabinete RP-9 (empenhos imputado prefeito TSE)
- IFI/TB/CGU notas técnicas

---

## Estrutura de scripts (`source/`)

### Pipeline de modelagem original

| Script | Função |
|---|---|
| `01_run_dml.py` | DML PLR/PLIV original |
| `02_heterogeneities.py` | R2.1-R2.5 do MUSTDO |
| `03_decomposition.py` | R2.7-R2.9 (RP-9 imputado, polarização tercis, Oaxaca) |
| `04_counterfactual_price.py` | Preço político R$/pp |
| `20_main_results_v2.py` | Spec definitiva v2 |
| `22_decomposition_v2.py` | Decomposição final |
| `29_mediation_polarization.py` | Mediação ABS com MDS |
| `30_speech_integration.py` | Linkage com discursos |
| `31_event_study_stf.py` | Event study ADPF 854 |

### Pipeline pós-defesa (junho 2026)

| Script | Função |
|---|---|
| `32_eda_budget_data.py` | EDA das fontes baixadas |
| `33_build_multi_rp_panel.py` | Painel multi-RP por deputado×voto |
| `34_build_secret_budget_proxies.py` | Proxies de canal opaco |
| `35_eda_multi_rp_cross.py` | EDA cruzado RPs × alinhamento |
| `37_centrao_descriptives.py` | Descritivas Centrão pré/pós-Lira |
| `50_full_followup_n3.py` | **RODADA DEFINITIVA n_reps=3** (em curso) |

Scripts `36_`, `40_`-`45_` foram tentativas com `n_reps=1` (descartados; substituídos pelo `50_`).

---

## Especificação econométrica

### Outcome (Y)

- **`alinhamento`** (binário): 1 se voto coincide com orientação do governo (MAIN)
- **`y_centrao`** (binário, novo): 1 se voto coincide com maioria do Centrão na mesma votação

### Treatment (T)

- **`emenda_M`** = R$ milhões comprometidos em RP-6 individual nos **60 dias antes do voto** (MAIN)
- Tratamentos auxiliares (multi-RP): `T_rp6_pix_pre60_M`, `T_rp8_pre60_M`, `T_rp9_imputed_pre60_M`

### Controles

**`full_clean` ≈ 142-148 cols** (depende da legislatura): todos os numéricos exceto:
- IDs, treatment, target, IVs
- Bad controls (votosSim/Não/Outros, aprovacao)
- Leakage vars (pct_seg_ori_*, pct_traiu_ori_*, pct_votSim, etc.)

**`full_clean + party FE`** (157 cols pooled): adiciona 15 dummies de partido (top-16, 1 omitida). **SPEC PRINCIPAL DO PAPER.**

**Para T1 com proxies**: removemos manualmente `T_rp*` e `share_*` do `ctrl_base` para comparação base vs base+proxies fazer sentido. Lista em `50_full_followup_n3.py::EXTRA_TREATMENT_VARS`.

### Identificação

**PLIV-DML** com cross-fitting K=3 folds, R=3 repetições, ElasticNetCV, Deputy FE (within-demeaning), cluster-robust SE no nível deputado (CGM via DoubleMLClusterData).

**Instrumento** — ministry-execution backlog:
- `iv_q4_no_ytd`: Q4 × YTD execution < 10% (backlog pressure)
- `iv_ytd_exec_pct`: fração executada year-to-date antes do voto

Motivado pelo prazo do Art. 35 da Lei 4.320/1964 (dotações não empenhadas até 31/dez lapsam), mas a variação identificadora é heterogeneidade cross-ministério do backlog acumulado, não o calendário em si. Set `fiscal` (Q4 dummy + inverso de dias até 31/dez) foi descartado da main spec em jul/2026 por potencial de violação da restrição de exclusão via canais políticos não-orçamentários; ver `_config.py::IV_SETS` para referência histórica.

Reportamos AR-CI (Anderson-Rubin, robusto a IV fraco) e Cinelli-Hazlett $\mathrm{RV}_{q=1}$ além de cluster-robust CI.

### Magnitudes reportadas

| Coluna | Significado |
|---|---|
| `coef_sd` | output DML padronizado |
| **`pp_per_unit`** | **pontos percentuais por R$1M** ← reporting principal |
| `ci95_lo_pp`, `ci95_hi_pp` | CI 95% em pp/R$1M |
| `std_T` | desvio-padrão de T (R$M) |

---

## Achados centrais (a partir de n_reps=3)

| Análise | Leg 55 | Leg 56 | Sub-períodos Leg 56 |
|---|---|---|---|
| **Main spec (gov outcome)** | **+1.73 *** | **−0.94 *** | — |
| **Centrão outcome (T5)** | +0.06 (n.s.) | −0.67 ** | **pre-Lira +0.87 ****, post-Lira +0.40 *** |
| **T2 gov RP-9 exposure** | — | exp −0.31 (n.s.), not_exp **−0.99 *** | — |
| **T2 centrão RP-9 exposure** | — | exp −0.26 (n.s.), not_exp **−0.68 *** | — |

Esses são os números **definitivos** a usar no paper (em curso de complementar com T4 e T1).

---

## Decisões de design

- **Excluir Leg 57** (emendas só até 2024; pós-STF instável)
- **Excluir CMO** (instrumento fraco)
- **Painel `panel_emendas_pre` (60d antes)** como MAIN; ±45d sym + 60d post como robustez/placebo
- **`full_clean + party FE`** como especificação principal
- **`n_reps=3`** sempre (rodadas com `n_reps=1` descartadas)
- **Sargan-Hansen reportado** com nota de hipersensibilidade
- **AR-CI reportado** ao lado de cluster-robust
- **Cinelli-Hazlett RV** reportado em apêndice

---

## O que NÃO fazer

- Não usar `features_v2.csv` (use `panel_features.csv`)
- Não interpretar resultados follow-up com `n_reps=1` (descartados, substituir pelos `n3_*.csv`)
- Não incluir Leg 57
- Não incluir T_rp*/proxies em `ctrl_base` sem excluir manualmente (vira pseudo-bad-control)

---

## Próximos passos imediatos

1. Aguardar T4 + T1 do `50_full_followup_n3.py` (1-5 dias)
2. Consolidar tabelas LaTeX dual (gov × centrão) no paper
3. Reescrever §7 Discussion com narrativa final (a decidir após T4 completo)
4. Atualizar abstract, introdução, conclusão
5. Submissão Public Choice (target: 2026-07-31)
