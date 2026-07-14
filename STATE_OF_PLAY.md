# Paper-Emendas — Estado de Jogo (Junho 2026)

> Documento de referência em português consolidando **TUDO** que temos:
> bases de dados, períodos de cobertura, resultados rodados, achados,
> dúvidas pendentes, narrativas candidatas. Atualizar a cada rodada.
>
> **Não é o paper** — é o backstage para decidir qual será o discurso final.

---

## 1. Bases de dados disponíveis

### 1.1 Painel principal (núcleo do paper)

**Granularidade**: `deputado × votação`. Cada linha = um deputado votando em uma proposição.

| Base | Origem | Período | Linhas | Granularidade |
|---|---|---|---|---|
| `panel_features.csv` | API Câmara + merges | 2015-02 a 2026-04 | 1.344.530 (raw) | deputado × votação |
| `panel_features.csv` (filtrado Leg 55+56, alinhamento ∈ {0,1}) | idem | 2015-02 a 2022-12 | **869.902** | deputado × votação |
| `panel_emendas_pre.csv` | Portal Transparência via SIAFI | 2015-2022 | 869k | deputado × votação (janela 60d pré-voto) |
| `iv_features.csv` | construído | 2015-2022 | 869k | instrumentos por deputado × votação |
| `coalizao_partido_data.csv` | manual | 2015-2022 | partido × data | status coalizão/oposição |
| `polarizacao_votacao.csv` | derivado | 2015-2022 | votação | `pol_simple`, `pol_jaccard`, `pol_paper` |

**Outcome principal**: `alinhamento` = 1 se voto do deputado bate com orientação de governo. Média Leg 55 = 0.71, Leg 56 = 0.74.

**Tratamento principal**: `emenda_M` = R$ comprometido em emendas RP-6 individuais nos 60 dias antes do voto (em milhões R$). Média 0.84, std 2.41, 57.7% positivo.

**Sample**: 869.902 obs, 931 deputados únicos, 226.308 Leg 55 + 643.594 Leg 56.

### 1.2 Polarização (do Paper 2)

**Granularidade da fonte**: `janela bimestral × dimensão` (matriz MDS).
**Granularidade após `attach_pol_paper()`**: `deputado × votação` (cada votação recebe o valor da janela bimestral correspondente à sua data).

| Arquivo | Medida | Período de janela | Granularidade |
|---|---|---|---|
| `average_mds_distances_euclidean.csv` | MDS-Euclidean (distância estrutural) | bimestral | janela × dimensão |
| `average_mds_distances_forte.csv` | MDS-Strong (axis-aligned) | bimestral | janela × dimensão |
| `average_mds_distances_fraca.csv` | MDS-Weak (categórica dim-por-dim) | bimestral | janela × dimensão |

**Como entra no painel**: via `attach_pol_paper(df)` que mapeia `data` da votação ao intervalo bimestral correspondente. Cobertura: 100% das 869k obs.

### 1.3 Multi-RP panel (recém-construído, junho 2026)

**Granularidade**: `deputado × votação`, com tratamento agregado em janela 60 dias pré-voto. Mesma estrutura que o painel principal.

| Variável | Cobertura Leg 55 | Cobertura Leg 56 | Origem |
|---|---|---|---|
| `T_rp6_pre60` | 82% pos | 88% pos | Portal Transparência + SICONV |
| `T_rp6_pix_pre60` | 0% (não existia) | 50% pos | EC 105/2019 |
| `T_rp7_pre60` | 0% | 0% (sem mapping deputado) | — |
| `T_rp8_pre60` | 0% | 0.3% pos | SICONV apoiadores (43% match) |
| `T_rp9_pre60` | 0% | 0% (autor=Relator Geral) | — |
| `T_rp9_imputed_pre60` | 0% | 3.2% pos | SICONV apoiadores (137 obs) |

**Limitação**: o painel original (`emenda_M`) é o **mesmo** que `T_rp6_pre60` em essência (correlação 0.25 — ver §3 sobre validação). As novas vars não substituem o tratamento principal, são complementares.

### 1.4 Proxies de Orçamento Secreto

**Granularidade**: `deputado × ano` (depois propagada para `deputado × votação` mantendo valor constante dentro do ano).

| Variável | Tipo | Cobertura Leg 56 | Construção |
|---|---|---|---|
| `d_rp9_solicitante` | dummy | 3.2% pos | =1 se deputado aparece como solicitante em algum RP-9 no ano |
| `share_pork_opaco` | contínua [0,1] | 3.5% pos | (RP-8+RP-9) / total pork por deputado-ano |
| `share_rp9` | contínua [0,1] | 3.2% pos | RP-9 / total pork por deputado-ano |
| `share_pix` | contínua [0,1] | 50% pos | Pix / RP-6 total por deputado-ano |
| `n_apoiamentos_opaco` | inteiro [0,8] | 3.5% pos | qty de apoiamentos RP-8/RP-9 por deputado-ano |

### 1.5 Bases externas baixadas — granularidade real e diagnóstico de uso

**Por que muitas não estão integradas ao painel**:

O painel principal é **deputado × votação**. Para uma base externa entrar como tratamento ou controle, ela precisa ser agregada para esse nível. As bases não-integradas têm um dos seguintes problemas:
1. **Sem identificação direta de deputado** (Tesouro mensal usa CNPJ do favorecido; SICONV pagamento usa ID_FORNECEDOR)
2. **Sem datas** (PDFs Câmara CMO, listas estáticas)
3. **Cobertura temporal estreita** (Codevasf, GitHub gabinete só 2020-2021)
4. **Redundância parcial** (Portal Transparência bulk reproduz o que já temos via API + foi a fonte do multi-RP)

Tabela com granularidade real e viabilidade como proxy:

| Fonte | Granularidade real | Período | Status no painel | Como pode virar proxy |
|---|---|---|---|---|
| **Portal Transparência bulk** | emenda × ano × **autor (nome)** × localidade | 2014-2026 | **JÁ USADA** (fonte do multi-RP) | — |
| **Tesouro CKAN emendas mensal** | **município × mês × CNPJ favorecido** | 2015-2026 (388k) | NÃO | **ALTO**: (i) série mensal de pork por UF do deputado; (ii) timing de execução; (iii) distinção Pix vs convênio em granularidade temporal fina. |
| **Tesouro CKAN despesas totais** | função × subfunção × ano (XLSX agregados) | 2008-2026 | NÃO | MÉDIO: controle macro do orçamento total. Útil como denominador "% emendas / total". |
| **SICONV emenda** | emenda × ID_PROPOSTA × **nome parlamentar** | 2010-2026 (296k) | **JÁ USADA** (multi-RP) | — |
| **SICONV apoiadores** | apoiamento × programa × **parlamentar** | 2010-2026 (291k) | **JÁ USADA** (proxies opacas) | — |
| **SICONV convênio** | convênio × ID_PROPOSTA × **data assinatura** + 30 cols (vl_global, empenhado, desembolsado, vigência, situação) | 2008-2026 (283k) | parcial (lookup de ano) | **ALTO**: (i) lag empenho→pagamento por deputado-ano (via SICONV emenda); (ii) status do convênio (em vigor / cancelado / concluído) como indicador de qualidade; (iii) duração de vigência. |
| **SICONV empenho** | empenho × convênio × **data emissão** + RESULTADO_PRIMARIO | 2008-2026 | NÃO | **ALTO**: timing exato dos empenhos. Linka via convênio → emenda → deputado. Permite reconstruir backlog em granularidade diária. 96 MB. |
| **SICONV pagamento** | pagamento × convênio × **data pagamento** + fornecedor | 2008-2026 | NÃO | **ALTO**: timing de pagamento (vs empenho). Crítico para o IV de backlog em alta granularidade. 1 GB. |
| **SICONV proposta** | proposta × proponente × **UF × município × ano** | 2008-2026 | NÃO | MÉDIO: características do beneficiário. 750 MB. |
| **SICONV programa** | programa × ano × natureza × UF | 2008-2026 | **JÁ USADA** (lookup de ano dos apoiamentos) | — |
| **SICONV proponentes** | proponente × UF × município (cadastral) | 2008-2026 | NÃO | BAIXO: lista estática. |
| **Câmara CMO Atos Conjuntos** | PDFs (15 arquivos) | 2021 | NÃO | BAIXO: precisa OCR. RP-9 2021 oficial. |
| **Câmara CMO Recibos** | PDFs (11 arquivos) | 2021-2024 | NÃO | BAIXO: precisa OCR. Lista deputado × comissão. |
| **GitHub gabinete RP-9** | empenho × **prefeito TSE × deputado-imputado-via-partido** | 2020-2021 (15k linhas) | parcial (137 obs) | **ALTO**: mapping deputado-município via prefeito eleito 2020 + partido. Pode aumentar cobertura RP-9 de 3.2% (atual, oficial) para ~30%+ (via heurística). |
| IFI NT 57 / TB+TI NT / CGU RP-8 | PDF | 2024-2025 | NÃO | BAIXO: referência/citação no paper. |

**Total**: ~1,1 GB em 115+ arquivos.

### 1.5.bis Proxies adicionais possíveis (a discutir após rodada n3 terminar)

Itens marcados **ALTO** acima são candidatos a virar proxies novas no painel. Estimativa de esforço:

1. **Lag empenho → pagamento por deputado-ano** (SICONV empenho + pagamento + apoiamentos): hipótese — pagamento rápido = pork "ativo", pagamento lento = pork "represado" (dimensão punitiva). Esforço: 1-2 dias (precisa joins entre 3 tabelas grandes).

2. **Status do convênio** (vigente / cancelado / concluído) por deputado-ano: indicador de qualidade do pork. Esforço: ~half-day.

3. **Volume Tesouro mensal por UF → deputado da UF**: complementa o RP-6 em dimensão geográfica/temporal. Esforço: 1 dia.

4. **RP-9 imputado via prefeito TSE 2020** (GitHub gabinete): expandir cobertura RP-9 de 3.2% para ~30% via heurística partido-UF-município. Esforço: 1 dia (matching nominal).

5. **% emendas / orçamento total** (Tesouro despesas anuais): controle macro de peso institucional do pork. Esforço: 2 horas (XLSX → série anual).

6. **Distribuição de cargos no Executivo e no Legislativo por deputado** (pork não-monetário): mapear, por deputado-data, se ele/ela ocupa ou indicou parente próximo para cargos. Hipótese: cargos são moeda paralela ao RP-6 e podem explicar parte do backfire (deputados leais recebem cargo em vez de pork visível). Fontes:
   - **Cargos legislativos** (já temos no painel via API Câmara): presidência/relatoria de comissões (`d_mesa_*`), liderança de partido/bloco (`d_lider_*`). Usar como heterogeneidade (interação `T × d_lider`) ou como controle adicional.
   - **Cargos no Executivo** (precisa coleta nova): Portal Transparência `/cargos-comissionados` (CC, DAS, FCPE). Matching deputado→cargo é difícil porque vai majoritariamente para parentes/indicados; precisa de matching nominal/familial. Esforço: 1 semana (coleta + matching nominal).
   - **Indicações em estatais** (Petrobras, BB, Caixa, BNDES, Codevasf, etc.): listas públicas via API LeXML e Diário Oficial. Esforço: dias.
   - **Frentes parlamentares**: já temos `n_frentes`, `pct_frentes` no painel. Pode virar interação `T × pct_frentes` para testar se deputados em mais frentes têm pork-effect diferente.
   - Output esperado: variável `d_dep_com_cargo_t` (dummy) + `valor_estimado_cargo_t` (R$/mês equivalente). Spec robustez: heterogeneidade Leg 56 entre "deputados com cargo" vs "sem cargo".
   - Limitação: cargos comissionados raramente vão direto ao deputado; vão para parentes. Requer matching nominal/familial caro.

**Decisão**: implementar **APÓS** rodada n3 terminar (não interromper o que já está rodando). Já anotado em MUSTDO_v2 (§A.9.5) e aqui em §7.

### 1.5.bis.STATUS — Proxies extras CONCLUÍDAS (20/06/2026)

Implementadas todas as 6 proxies. Outputs em `dados/interim/panel/`:

| # | Script | Output | Granularidade | Cobertura |
|---|---|---|---|---|
| P1 | `60_build_proxy_lag_emp_pgto.py` | `panel_proxy_lag_emp_pgto.csv` | deputado × ano | 45.6% (49,132 cells) |
| P2 | `61_build_proxy_conv_status.py` | `panel_proxy_conv_status.csv` | deputado × ano | 52.2% (56,202) |
| P3 | `62_build_proxy_tesouro_uf_mensal.py` | `panel_proxy_tesouro_uf_mensal.csv` | UF × ano × mês | 45.4% (48,893) |
| P4 | `63_build_proxy_rp9_via_prefeito.py` | `panel_proxy_rp9_imputed_prefeito.csv` | deputado × ano | 100% (8,860 com valor > 0, apenas 2020-2021) |
| P5 | `64_build_proxy_share_emendas_total.py` | `panel_proxy_share_emendas_total.csv` | ano | 23.7% (2008-2019) |
| P6 | `65_build_proxy_cargos.py` | `panel_proxy_cargos.csv` | deputado × ano | 99.5% (107,180) |
| **Final** | `66_consolidate_proxies_extra.py` | `panel_proxies_extra.csv` | deputado × ano × mês | 107,688 linhas, 36 colunas |

**Achados descritivos**:
- **P1 (lag empenho→pgto)**: lag médio caiu de 745d (2015) para 328d (2024). Pagamento mais rápido = pork "ativo".
- **P2 (status convênio)**: % concluído médio = 33.7%, % problema (cancelado/anulado/rescindido) = 21.5%.
- **P3 (Tesouro UF mensal)**: volume agregado cresceu de R$1.6bi (2015) para R$26.9bi (2025).
- **P4 (RP-9 via prefeito)**: cobertura saltou de 3.2% (oficial) para 82-84% (imputado) em 2020-2021. Mean por deputado-ano: R$2.25M (2020) → R$4.09M (2021).
- **P5 (share emendas/orçamento)**: 0.07% (2015) → 0.29% (2018) → 0.26% (2019). Cresceu **4x** em 4 anos.
- **P6 (cargos)**: Tier 2 (líderes/pres comissão) presente em 4,405 deputado-anos; Mesa Diretora em 437. Liderança partidária binária = 0 (classificador não captura — investigar futuramente).

**Correlações entre proxies (Leg 56, 2019-2022)**: a maioria entre |0.0| e |0.2| — sinais ortogonais, podem entrar como controles distintos sem multicolinearidade severa. Única forte: `n_cargos × n_tier2 = 0.36` (esperado, sub-componente).

**Próximos passos**:
1. Usar P4 (RP-9 via prefeito) como **proxy do orçamento secreto** em DML alternativo para 2020-2021. Comparar com `T_rp9_pre60_M_dep_solicitante` oficial — pode revelar parte do pork "escondido".
2. Usar P6 (`has_mesa`, `n_tier2`) como **heterogeneidade** (interação `T × has_mesa`) para testar narrativa F (Legislative Capture).
3. Usar P1 (`lag_medio_dias`) como **outcome alternativo** para testar dimensão punitiva (pork represado vs ativo).
4. P5 (share emendas/orçamento total) entra apenas como **estatística descritiva** no paper (não DML).

### 1.6 Discursos parlamentares (do Paper 2/Paper 1)

**Granularidade da fonte**: `discurso × deputado × data`.
**Granularidade após agregação para o painel**: `deputado × janela 90 dias rolling pré-voto` (média dos scores no período); depois mergeada em `deputado × votação`. Vide `30_speech_integration.py`.

| Base | Conteúdo | Cobertura | Granularidade |
|---|---|---|---|
| `discurso_speech_corpus.csv` | textos de discursos | 2015-2026 | discurso |
| `model_speech_sentiment.csv` | BERTimbau sentiment scores | 33.517 discursos | discurso × score |
| `model_xlm_sentiment.csv` | XLM-RoBERTa Cardiff scores | 33.517 | discurso × score |
| `model_anti_gov_nli.csv` | mDeBERTa anti-government NLI | 33.517 | discurso × score |

Já integrado parcialmente em `speech_integration.csv` (tercis 90d rolling).

---

## 2. Resultados rodados (chronological)

### 2.1 Main spec original (pré-defesa, em `main_results_v3.csv`)

| Sample | $\hat\theta$ pp/R\$M | CI 95% | p |
|---|---|---|---|
| Pooled | **−2.82** | [−3.74, −1.90] | <0.001 |
| Leg 55 | **+1.73** | [+0.26, +3.20] | 0.022 ** |
| Leg 56 | **−0.94** | [−1.37, −0.51] | <0.001 *** |

Esse é o **resultado-âncora** do paper. Confirmado por todas as variações que rodamos depois.

### 2.2 Tercis de polarização pooled (em `decomposition_v2.csv`)

| Tercil MDS-Eucl | $\hat\theta$ |
|---|---|
| Low | +4.21 |
| Mid | −2.27 |
| High | ~0 (n.s.) |

Esse era o resultado que sustentava a narrativa "polarização causa backfire". **Mas estava em sample POOLED**.

### 2.3 Tercis SEPARADOS por legislatura (follow-up junho 2026, em `followup_t4_tercis_by_leg.csv`)

**Gov outcome**:

| Medida | Leg | Low | Mid | High |
|---|---|---|---|---|
| MDS-Eucl | 55 | −3.41 (n.s.) | −0.77 (n.s.) | +1.13 (*) |
| MDS-Eucl | 56 | **−1.58 (*)** | +18.17 (n.s., outlier) | +0.01 (n.s.) |
| **MDS-Weak** | 55 | −0.01 (n.s.) | **+1.87 (**)** | +4.32 (n.s.) |
| **MDS-Weak** | 56 | **+2.93 (***)** | **−1.18 (***)** | **+1.99 (***)** |
| MDS-Strong | 55 | −0.86 (n.s.) | **+2.83 (***)** | −2.04 (*) |
| MDS-Strong | 56 | **+3.09 (*)** | **+6.18 (*)** outlier | −0.04 (n.s.) |

**Achado central**: a única medida que produz padrão **monotônico/U-shape consistente** em ambas legs é **MDS-Weak** (a métrica do Paper 2). MDS-Eucl tem outliers no mid; MDS-Strong é ruidosa.

**Centrão outcome** (T5 mostra que pork compra alinhamento Centrão em sub-amostras específicas):

| Medida | Leg | Low | Mid | High |
|---|---|---|---|---|
| MDS-Eucl | 55 | −3.95 (n.s.) | −0.61 (n.s.) | +0.27 (n.s.) |
| MDS-Eucl | 56 | **−2.03 (**)** | +31.93 (n.s., outlier) | +0.13 (n.s.) |
| **MDS-Weak** | 55 | −0.09 (n.s.) | **+4.22 (***)** | +2.81 (n.s.) |
| **MDS-Weak** | 56 | **+2.40 (***)** | **−0.89 (**)** | **+4.51 (***)** |
| MDS-Strong | 55 | **+3.87 (***)** | **+2.38 (***)** | −1.65 (n.s.) |
| MDS-Strong | 56 | +2.53 (n.s.) | **+14.48 (***)** | **+0.40 (**)** |

**Mesmo padrão U-shape no MDS-Weak Leg 56** (gov: +2.93/−1.18/+1.99 ↔ centrão: +2.40/−0.89/+4.51). Robustez forte.

### 2.5 RODADA DEFINITIVA n_reps=3 (concluída 19/06/2026)

Pipelines `50_full_followup_n3.py` (gov outcome) e `55_n3_pres_camara_orient.py` (y_pres outcome) executados com `n_folds=3, n_reps=3`.

**Outcomes**:
- `y_gov` = orientação do governo (mainstream do paper)
- `y_pres_camara_orient` = orientação do partido do presidente da Câmara (Maia/DEM antes de 2021-02, Lira/PP depois; período Cunha/PMDB descartado por baixa cobertura)

#### 2.5.1 T1 — Main spec por legislatura

| Sample | Spec | y_gov | y_pres |
|---|---|---|---|
| Leg 55 | base_pure | **+1.89 *** | **−2.92 *** |
| Leg 55 | base+proxies | **+2.02 *** | **−3.04 *** |
| Leg 56 | base_pure | **−0.94 *** | **−1.30 *** |
| Leg 56 | base+proxies | **−0.94 *** | **−1.32 *** |

**Achados**:
- Proxies (RP-9, Pix) **não absorvem** o efeito em nenhum outcome.
- Em Leg 55, sinal **inverte** entre gov (+1.89) e y_pres (−2.92): Maia (DEM) era oposição a Temer.
- Em Leg 56 inteira, ambos negativos, mas y_pres tem magnitude maior.

#### 2.5.2 T2 — Heterogeneidade por exposição RP-9 (Leg 56)

| Subgrupo | y_gov | y_pres |
|---|---|---|
| RP-9 supporters (3.2%) | −0.31 (n.s.) | −0.26 (n.s.) |
| Non-supporters (96.8%) | **−0.99 *** | **−1.27 *** |

**Achado**: backfire concentra **nos não-expostos** em ambos outcomes. Canal opaco RP-9 substitui RP-6 para os expostos.

#### 2.5.3 T3 — Mediação Pix (OLS)

| Sample | y_gov prop_mediated | y_pres prop_mediated |
|---|---|---|
| Pooled | +27% | −9% |
| Leg 55 | 0% | 0% |
| Leg 56 | −3% | −10% |

**Achado**: Pix **não medeia o efeito dentro de cada legislatura** em nenhum outcome. Os números pooled são artefato matemático.

#### 2.5.4 T4 — Tercis MDS por legislatura

**MDS-Euclidean**:
| Leg | Tercil | y_gov | y_pres |
|---|---|---|---|
| 55 | Low | −4.37 (n.s.) | **+11.43 *** |
| 55 | Mid | +0.11 (n.s.) | **+14.81 *** |
| 55 | High | +0.30 (n.s.) | **−1.32 *** |
| 56 | Low | **−1.38 *** | **−1.85 *** |
| 56 | Mid | +18.80 (n.s., outlier) | +20.42 (n.s., outlier) |
| 56 | High | **−0.32 *** | +0.22 (n.s.) |

**MDS-Weak (do Paper 2)**:
| Leg | Tercil | y_gov | y_pres |
|---|---|---|---|
| 55 | Low | −1.13 (n.s.) | **+11.52 *** |
| 55 | Mid | **+6.91 *** | **−1.87 *** |
| 55 | High | **+5.13 *** | **−8.68 *** |
| 56 | Low | +14.85 (n.s., outlier) | +14.39 (n.s., outlier) |
| 56 | Mid | **−1.10 *** | **−1.22 *** |
| 56 | High | **+1.96 *** | **+3.72 *** |

**MDS-Strong**:
| Leg | Tercil | y_gov | y_pres |
|---|---|---|---|
| 55 | Low | −0.81 (n.s.) | **−4.93 *** |
| 55 | Mid | **+3.11 *** | **−4.06 *** |
| 55 | High | −1.86 (n.s.) | +0.08 (n.s.) |
| 56 | Low | +8.99 (n.s.) | +2.82 (n.s.) |
| 56 | Mid | **−1.87 *** | **−3.27 *** |
| 56 | High | −0.08 (n.s.) | **+0.41 *** |

**Achados-chave T4**:
- **MDS-Eucl Leg 56 mid é outlier estrutural** em todos os outcomes (provável IV fraco)
- **MDS-Weak Leg 56 (do Paper 2) é a métrica mais discriminante**: padrão U-shape preservado em ambos outcomes (low instável, mid negativo, high positivo)
- **Leg 55**: sinais frequentemente **opostos** entre gov e y_pres (Maia oposição a Temer)
- **Leg 56**: sinais geralmente **consistentes** entre gov e y_pres no mid e high

#### 2.5.5 T5 — Sub-amostras por presidente (y_pres apenas)

| Sub-amostra | Presidente | Partido | n obs | theta | p |
|---|---|---|---|---|---|
| leg55_maia | Maia | DEM (oposição Temer) | 119k | **−2.76** | 0.008 *** |
| leg56_maia | Maia | DEM (DEM neutro/saída base) | 220k | +0.04 | 0.85 (n.s.) |
| **leg56_lira** | **Lira** | **PP (aliado Bolsonaro)** | 396k | **+0.33** | 0.04 ** |
| leg56_lira_excl_pp | Lira | (sem dep PP) | 363k | +0.32 | 0.08 * |
| **leg56_lira_excl_centrao** | **Lira** | **(sem Centrão histórico)** | 181k | **−0.06** | 0.81 (n.s.) |

**Achados centrais T5**:
1. **Sob Lira, pork compra alinhamento com o presidente da Câmara (+0.33**)**.
2. **Sem PP**: efeito quase idêntico (+0.32*) — **não é auto-reforço do PP**.
3. **Sem Centrão histórico**: efeito **desaparece** (−0.06) — efeito vem do **mercado interno do Centrão amplo**.
4. **Maia oposição a Temer (Leg 55)**: pork **DESALINHA** com Maia (−2.76***).
5. **Maia neutro/sai base Bolsonaro (Leg 56 pre-Lira)**: nulo.
6. **Comparação Maia oposição vs Lira aliado**: diferença de 3.1 pp/R$M.

### 2.4-bis T5 COM `n_reps=3` (definitivo, em curso 18/06) — `n3_t5_centrao_subsamples.csv` [DESCARTADO — ver §2.5.5 acima]

Resultados DEFINITIVOS (config idêntica ao main paper):

| Sample | $\hat\theta$ pp/R\$M | CI 95% | p | n |
|---|---|---|---|---|
| **leg55_full** | **+0.06** | [−1.47, +1.60] | 0.937 | 226.308 |
| **leg56_full** | **−0.67** | [−1.30, −0.04] | **0.036 **** | 643.594 |
| **leg56_pre_lira** | **+0.87** | [+0.31, +1.44] | **0.003 ****** | 236.945 |
| **leg56_post_lira** | **+0.40** | [+0.07, +0.73] | **0.018 **** | 406.649 |
| leg56_post_lira_excl_centrao | +0.24 | [−0.28, +0.76] | 0.364 | 228.657 |

**T5 completo (n_reps=3)**. Conclusões consolidadas:

1. **Pré-Lira > Post-Lira**: pork compra alinhamento Centrão **mais fortemente** antes de Lira (+0.87) do que depois (+0.40). Sob Lira, Centrão é alinhado por design, então pork tem menos margem.
2. **Post-Lira sem Centrão = nulo** (+0.24 n.s.): o efeito post-Lira vem **dos próprios deputados Centrão**.
3. **Leg 56 full é negativo (−0.67)** apesar de pre-Lira/post-Lira serem positivos: provavelmente porque há heterogeneidade temporal não capturada nos cortes simples. Vale investigar (talvez 2020 ano da pandemia atua como break).

**Achados que invalidam interpretações anteriores**:

1. **Leg 55 full Centrão: +0.06 (n.s.)** — `n_reps=1` deu +1.37**. **O +1.37 era ruído Monte Carlo**. Pork NÃO compra alinhamento Centrão na Leg 55.

2. **Leg 56 full Centrão: −0.67 (**)** — `n_reps=1` deu +0.32 ou −0.0006 (inconsistente entre rodadas). **O verdadeiro é negativo**: pork **também backfira** com Centrão na Leg 56. Magnitude menor que gov (−0.94) mas significativa.

3. **Leg 56 pre-Lira Centrão: +0.87 (***)** — Pork compra alinhamento Centrão **ANTES** de Lira tomar a Câmara. Faz sentido: nesse período Centrão era ainda parte da coalizão pró-Bolsonaro normal, e pork operava no canal canônico.

4. Pós-Lira em curso — esse vai ser o teste definitivo da Narrativa 1.

### 2.4 T5: Outcome alternativo "alinhamento Centrão" — sub-amostras (`followup_t5_centrao_alignment.csv`)

| Sample | $\hat\theta$ pp/R\$M | CI 95% | p | ȳ Centrão |
|---|---|---|---|---|
| Leg 55 full | **+1.37** | [+0.14, +2.59] | 0.028 ** | 0.737 |
| Leg 56 full | +0.32 | [−0.18, +0.82] | 0.21 (n.s.) | 0.766 |
| Leg 56 pre-Lira | −0.37 | [−1.75, +1.00] | 0.60 (n.s.) | 0.771 |
| **Leg 56 post-Lira** | **+0.41** | [+0.07, +0.74] | **0.018 **** | 0.763 |
| Leg 56 post-Lira excl Centrão | +0.26 | [−0.24, +0.77] | 0.31 (n.s.) | 0.633 |

**Achados**:
- Pork compra alinhamento Centrão **sob Temer** (+1.37**) — surpreendente, Temer já se apoiava no Centrão.
- **Sob Lira (pós-fev/2021)**: +0.41** — auto-reforço.
- Excluindo deputados do próprio Centrão pós-Lira: efeito cai a +0.26 (n.s.). **O efeito vem dos próprios Centrão**.

### 2.5 T1 IV-DML com proxies de canal opaco (corrigido em `followup_t1_iv_corrected_*.csv`)

| Outcome | Leg | Spec | $\hat\theta$ pp/R\$M | p |
|---|---|---|---|---|
| **GOV** | 55 | base_pure | **+1.89** | 0.01 ** |
| **GOV** | 55 | base+proxies | **+2.02** | 0.007 *** |
| **GOV** | 56 | base_pure | **−0.94** | <0.001 *** |
| **GOV** | 56 | base+proxies | **−0.94** | <0.001 *** |
| **Centrão** | 55 | base_pure | +0.001 | 0.27 (n.s.) |
| **Centrão** | 55 | base+proxies | +0.001 | 0.20 (n.s.) |
| **Centrão** | 56 | base_pure | −0.0006 | 0.04 ** |
| **Centrão** | 56 | base+proxies | −0.0004 | 0.16 (n.s.) |

**Achados**:
- **Backfire gov Leg 56 (−0.94***) é robusto** a controles diretos por canal opaco (RP-9 dummy + Pix share).
- **Centrão outcome tem magnitudes ordens de grandeza menores** (~10⁻³ vs 10⁰ do gov). Significância só por sample gigante.

### 2.6 T2 Heterogeneidade Leg 56 por exposição RP-9 (`followup_t2_het_rp9_exposure.csv` + centrão)

| Subgrupo | Gov $\hat\theta$ | Centrão $\hat\theta$ |
|---|---|---|
| RP-9 supporters (3.2%) | −0.48 (n.s.) | −0.07 (n.s.) |
| Non-supporters (96.8%) | **−2.27 (***)** | **−0.93 (**)** |

**Achado**: o backfire visível-RP-6 **concentra nos não-expostos** ao RP-9. Sugere que o RP-9 paralelo "compensa" o pork RP-6 para os 3% que recebem ambos.

### 2.7 T3 Mediação Pix (Acharya-Blackwell-Sen, em `followup_t3_mediation_pix.csv`)

| Sample | Gov: total / indirect / %med | Centrão: total / indirect / %med |
|---|---|---|
| Pooled | 0.0009 / 0.0002 / 27% | 0.0004 / 0.0004 / 102% |
| Leg 55 | 0.0111 / 0.0000 / 0% | 0.0066 / 0.0000 / 0% |
| Leg 56 | −0.0030 / 0.0001 / −3% | −0.0023 / 0.0002 / −10% |

**Achado**: Pix **NÃO é mediador** dentro de cada legislatura. Os 27%/102% pooled são artefato matemático (denominador quase-zero porque legs cancelam). **Pix não é o canal causal**.

### 2.8 Sub-análises Centrão descritivas (`eda_centrao_alignment.csv`)

| Grupo | Pre-Lira | Post-Lira |
|---|---|---|
| **Não-Centrão alinhamento** | 0.655 | 0.610 |
| **Centrão alinhamento** | 0.912 | 0.898 |
| Pix share não-Centrão | 0.037 | 0.207 |
| Pix share Centrão | 0.040 | **0.245** |

**Achado**: Centrão é 89-91% alinhado (estável). Não-Centrão cai 4.5pp pós-Lira. Pix share dispara em ambos, **maior no Centrão**.

---

## 3. Discrepâncias a investigar

### 3.1 T5 Leg55_full (+1.37**) vs T1 Centrão 43_ Leg 55 (+0.001 n.s.) — **DIAGNOSTICADA**

**Causa identificada (17/06)**: **variância de Monte Carlo do estimador IV-DML com `n_reps=1`**.

Testes de reprodutibilidade (mesma config T5, 3 seeds diferentes, Leg 55 Centrão):
- rep 0: theta = **+1.87** pp/R$M, p=0.001
- rep 1: theta = **+1.54** pp/R$M, p=0.008
- rep 2: theta = **+1.51** pp/R$M, p=0.010

Variação 0.36 pp entre rodadas. O T5 original ($+1.37$) e o 43_ corrigido ($+0.001$) são realizações **independentes** com **alta variância** do mesmo estimador. Com `n_reps=1` (default original era 3), o cross-fitting do ElasticNet pode produzir diferenças sistemáticas dependendo do seed inicial. **Implicação**: TODOS os resultados follow-up com `n_reps=1` têm SEs subestimadas e CI menos confiáveis que o reportado.

**Solução adotada (a partir de junho 18)**: rodar com **`n_reps=3`** (default original) para reduzir Monte Carlo. Isso triplica o tempo mas estabiliza os números.

### 3.2 T5 Leg56_full (+0.32 n.s.) vs T1 Centrão 43_ Leg 56 (−0.0006**)

Mesma causa raiz: variância Monte Carlo. Não dá pra confiar nos números pontuais com `n_reps=1`. Mesmo o T5 com sample 643k tem variabilidade.

### 3.3 Outliers no tercil mid da Leg 56 (MDS-Eucl e MDS-Strong)

- MDS-Eucl mid gov: +18.17 (n.s.), centrão +31.93 (n.s.)
- MDS-Strong mid gov: +6.18 (*), centrão +14.48 (***)

São magnitudes implausíveis. Possíveis causas:
- Variância Monte Carlo amplificada em sub-grupos com IV fraco
- Sample do tercil mid pode ter alta variância em treatment
- Primeiro estágio pode perder força

**Plano**: rodar com `n_reps=3` para ver se outliers permanecem.

### 3.2 T5 Leg56_full (+0.32 n.s.) vs T1 Centrão 43_ Leg 56 (−0.0006**)

Diferença menos dramática mas existe. Mesmas hipóteses.

### 3.3 Outliers no tercil mid da Leg 56 (MDS-Eucl e MDS-Strong)

- MDS-Eucl mid: gov +18.17, centrão +31.93 (n.s.)
- MDS-Strong mid: gov +6.18*, centrão +14.48*** (n=240k)

São magnitudes implausíveis. Possíveis causas:
- Sample do tercil mid pode ter alta variância em treatment
- Identificação fraca em sub-grupos médios (instrumento pode perder força)

**Plano**: checar primeiro estágio (F-stat) e std_T em cada tercil.

---

## 4. Narrativas candidatas

### Narrativa A: "Polarização causa backfire" (versão atual do paper)

> "Sob baixa polarização, pork compra alinhamento (canônico Pereira-Mueller). Sob alta polarização (Bolsonaro), o canal visível **backfira** porque o eleitorado polarizado pune trocas transacionais."

**Suportada por**: tercis pooled (+4.21 → −2.27), mediação MDS-Euclidean 63.8% Leg 55 → 0% Leg 56, sign reversal Leg 55→56.

**Desafiada por**:
- Tercis por leg mostram que padrão é **não-monotônico** (U-shape Leg 56 MDS-Weak).
- Backfire é só do **gov outcome**; Centrão estável.
- T5 mostra que pork **ainda compra** alinhamento Centrão pós-Lira.

### Narrativa B: "Mudança de chefe — pork passou do executivo ao legislativo"

> "Sob coalition presidentialism clássico (Temer), pork compra alinhamento ao executivo. Sob Bolsonaro + Lira (Centrão presidindo Câmara), pork passou a comprar alinhamento ao **bloco controlador do legislativo**. O sign reversal gov-outcome é uma artefato da redefinição de quem é o cliente do pork."

**Suportada por**:
- T5 post-Lira Centrão: +0.41**
- T5 excl Centrão pós-Lira: efeito cai a +0.26 (n.s.) — confirma auto-reforço
- Descritivas: Centrão 89-91% alinhado, Pix share maior em Centrão pós-Lira

**Desafiada por**:
- T1 corrigido Centrão Leg 56: −0.0006 (~zero). Pork não move alinhamento Centrão na full Leg 56.
- T5 Leg 55 Centrão: +1.37** já. Não é fenômeno só pós-Lira.

### Narrativa C: "Validação da medida Weak Divergence"

> "O Paper 2 propõe três métricas de polarização. Apenas a Weak Divergence (categórica, dimensão-por-dimensão) discrimina o efeito do pork de forma robusta. MDS-Eucl tem outliers; MDS-Strong é ruidosa. Isso valida a contribuição metodológica do Paper 2."

**Suportada por**:
- MDS-Weak Leg 56 todos significativos (gov: +2.93/−1.18/+1.99; centrão: +2.40/−0.89/+4.51)
- MDS-Eucl tem outliers gigantes no mid
- MDS-Strong tem padrões diferentes entre gov e centrão (instável)

**Limitação**: é um argumento metodológico, não substantivo. Pode entrar como apêndice ou como discussão metodológica.

### Narrativa D: "Substituição parcial via canal opaco"

> "Visível (RP-6) e opaco (RP-9) são canais substitutos. Onde o RP-9 está disponível, o RP-6 perde força. Onde não, o RP-6 backfira porque é o único canal visível e carrega o custo de credibilidade."

**Suportada por**:
- T2 não-expostos: −2.27*** | expostos: −0.48 (n.s.)
- Descritivas: deputados com RP-9 também recebem RP-6 (não populações distintas)

**Desafiada por**:
- T1 com proxies não muda o coef gov. Se fosse substituição "limpa", controlar pela proxy deveria zerar o backfire.

### Narrativa F (NOVA, jun/2026, baseada em n3 completo): "Captura legislativa do orçamento"

**Tese central**: A captura do orçamento pelo Congresso (via RP-9 e depois RP-8/Pix) mudou o **destinatário** do pork. Sob Lira (PP, aliado a Bolsonaro), pork visível RP-6 **continua comprando alinhamento, mas com o presidente da Câmara, não com o Executivo**. O sign reversal observado no `y_gov` é a manifestação observável dessa mudança de regime institucional.

**Evidências centrais**:

1. **Lira aliado → pork compra alinhamento com Lira** (T5 leg56_lira: +0.33**), enquanto **gov no mesmo período tem efeito negativo** (−0.94***). **Inversão de sinal entre outcomes no mesmo período** = mudança de destinatário do pork.

2. **Efeito vem do Centrão amplo**: excluindo Centrão histórico, efeito Lira desaparece (−0.06 n.s.). Mercado interno do bloco.

3. **NÃO é auto-reforço do PP**: excluindo PP, efeito quase idêntico (+0.32*). Lira "compra" deputados de outros partidos do Centrão.

4. **Posição institucional importa, não o partido per se**: Maia oposição a Temer (Leg 55) → pork DESALINHA com Maia (−2.76***); Maia neutro (Leg 56 pre-Lira) → nulo; Lira aliado → positivo. A direção do efeito depende de **se o presidente da Câmara está alinhado ou em oposição ao governo**.

**Narrativa A (Polarização) — fortalecida como mecanismo moderador**:
- MDS-Weak (do Paper 2) **discrimina padrão consistente em ambos outcomes** na Leg 56 (mid negativo, high positivo). Estrutural, não específico do destinatário.
- MDS-Eucl é mais ruidosa; MDS-Strong tem comportamentos diferentes entre outcomes.

**Narrativa D (RP-9 substitui RP-6) — mantida como mecanismo complementar**:
- Backfire concentra **só nos não-expostos a RP-9** em ambos outcomes (T2).

**Combinação para o paper**:
- Achado principal (§5 Results): sign reversal gov outcome (+1.73 → −0.94)
- Mecanismo institucional (§6/§7): captura legislativa = inversão entre outcomes
- Mecanismo moderador (§6): polarização Weak Divergence (Paper 2)
- Mecanismo complementar (§7): substituição RP-6 ↔ RP-9 para os expostos

### Narrativa E: "Combinação A+B+D" (atual hipótese de trabalho)

> "Três forças operando juntas:
> 1. Polarização Weak (não Euclidean) discrimina o regime.
> 2. Sob alta polarização Bolsonaro, gov outcome backfira porque o canal visível carrega custo de credibilidade, e o canal opaco (RP-9) só está disponível para um subgrupo.
> 3. Pós-Lira, o pork passa parcialmente para comprar alinhamento Centrão (auto-reforço do bloco), reforçando a interpretação de mudança de chefe."

---

## 5. Dúvidas pendentes (a discutir)

1. **A discrepância T5 vs T1 corrigido** precisa ser resolvida antes de decidir a narrativa. Vou re-rodar T5 com config exata do 43_.

2. **Por que MDS-Eucl tem outliers no mid?** Precisa olhar o primeiro estágio do IV nesses sub-grupos.

3. **Centrão Leg 55 +1.37**: o que isso significa?** Temer já recebia apoio do Centrão. O coef positivo aqui é canônico (pork → Centrão alinhado). Não é exclusividade do Lira.

4. **O canal RP-9 imputado** captura só 3% das obs. Será que isso é representativo? Ou é viés de seleção (só os "apoiadores formais" identificados)?

5. **Cargos no Executivo / Comissões**: documentado em MUSTDO_v2 §A.9.5. Vale fazer essa coleta agora para a versão atual?

6. **A questão do canal opaco**: nosso paper identifica que existe substituição parcial, mas não consegue medir o canal opaco causalmente. Honestamente assumir limitação no paper.

---

## 6. Status dos scripts e arquivos

### Scripts em `paper-emendas/source/`

| Script | O que faz | Status |
|---|---|---|
| 01-31 | Specs do paper original | Estável |
| `32_eda_budget_data.py` | EDA das fontes baixadas | ✅ rodado |
| `33_build_multi_rp_panel.py` | Painel multi-RP | ✅ rodado |
| `34_build_secret_budget_proxies.py` | Proxies opacas | ✅ rodado |
| `35_eda_multi_rp_cross.py` | EDA cruzado RPs + alinhamento | ✅ rodado |
| `36_followup_analyses.py` | T1-T5 originais (com bug T1) | ✅ rodado |
| `37_centrao_descriptives.py` | Descritivas pré/pós-Lira | ✅ rodado |
| `41_finish_followup.py` | T1-T4 com safety checks (gov) | ✅ rodado |
| `42_followup_centrao_outcome.py` | T1-T4 com y_centrao | ✅ rodado |
| `43_t1_corrected.py` | T1 com ctrl sem proxies | ✅ rodado |
| `44_consolidate_dual_outcome.py` | Gera tabelas LaTeX dual | ✅ rodado |
| `45_insert_dual_into_paper.py` | Insere tabelas no paper.tex | ✅ rodado |

### Resultados em `paper-emendas/results/`

- `main_results_v3.csv` — Tabela 1 do paper (âncora)
- `decomposition_v2.csv` — tercis pooled MDS-Eucl
- `mediation_polarization.csv` — mediação 5 medidas × 3 amostras
- `followup_t1_iv_corrected_gov.csv` — T1 corrigido gov
- `followup_t1_iv_corrected_centrao.csv` — T1 corrigido centrão
- `followup_t2_het_rp9_exposure.csv` — T2 het gov
- `followup_centrao_t2_het_rp9_exposure.csv` — T2 het centrão
- `followup_t3_mediation_pix.csv` — T3 Pix gov
- `followup_centrao_t3_mediation_pix.csv` — T3 Pix centrão
- `followup_t4_tercis_by_leg.csv` — T4 18 tercis gov
- `followup_centrao_t4_tercis_by_leg.csv` — T4 18 tercis centrão
- `followup_t5_centrao_alignment.csv` — T5 5 amostras
- `followup_dual_t{1,2,3,4,5}.tex` — tabelas LaTeX prontas
- `followup_master_comparison.csv` — comparação lado a lado

### Paper

- `paper-emendas/docs/paper.pdf` — 43 páginas, 5 tabelas dual inseridas
- `paper-emendas/docs/tex/paper.tex` — fonte, 0 TODOs restantes
- Inserções em vermelho via `\new{}` comando do preâmbulo

---

## 7. Próximos passos sugeridos (a decidir)

### Imediatos (resolver dúvidas antes de fechar narrativa)

1. **Re-rodar T5 leg55_full e leg56_full com config exata de 43_** para resolver discrepância (1-2 horas).
2. **Investigar outliers MDS-Eucl mid Leg 56**: olhar primeiro-estágio (F-stat).
3. **Salvar `panel_secret_budget_proxies.csv` versão limpa** (já existe, validar).

### Médio prazo (definir narrativa final)

4. **Discutir Narrativa A vs B vs E** com Daniel/Bernardo.
5. **Decidir tom**: paper foca em (i) regime change pork-as-coalition-tool, (ii) deslocamento chefe-cliente, ou (iii) validação metodológica Weak Divergence?
6. **Reescrever §1 Introdução e §7 Discussion** alinhado à narrativa escolhida.

### Plano matriz proposto (rodada de validação com `n_reps=3`)

Sob orientação do Pedro (17/06): testar matriz completa gov × centrão × polarizações × subperiodos com novos tratamentos.

**Eixo 1 — Outcomes (Y)**:
- `y_gov` (alinhamento governo) — atual
- `y_centrao` (alinhamento maioria Centrão) — já construído
- Opcionalmente: `y_pl` (alinhamento PL), `y_pp` (Lira's party)

**Eixo 2 — Tratamentos (T)**:
- `emenda_M` (RP-6 visível atual)
- `T_rp6_pix_pre60_M` (Pix isolado, 50% pos Leg 56)
- `T_rp6_pre60_M` (RP-6 finalidade definida, 88% pos Leg 56)
- `T_rp8_pre60_M` (comissão, 0.3% pos Leg 56)
- `T_rp9_imputed_pre60_M` (relator imputado, 3.2% pos Leg 56)

**Eixo 3 — Sub-amostras**:
- Leg 55 full
- Leg 56 full
- Leg 56 pre-Lira (até 2021-01)
- Leg 56 post-Lira (a partir de 2021-02)

**Eixo 4 — Tercis polarização (dentro de cada sub-amostra)**:
- MDS-Euclidean × 3 tercis
- MDS-Weak × 3 tercis
- MDS-Strong × 3 tercis

**Cálculo**:
- Versão enxuta (recomendada): 2 Y × 4 sub-amostras × 1 T main × 3 pol × 3 tercis = **72 PLIVs** + 2 Y × 2 sub-amostras × 4 T novos = **16 PLIVs**. Total: **88 PLIVs** com n_reps=3 ≈ **16-20 horas**.
- Versão completa: 4 Y × 4 sub-amostras × 5 T × 3 pol × 3 tercis = 720 PLIVs ≈ 5-7 dias.

**Aguardando aprovação do Pedro** antes de rodar.

### Possíveis extensões (se tempo)

7. **Coletar dados cargos comissionados** (Portal Transparência API). Item A.9.5 do MUSTDO_v2.
8. **Análise frentes parlamentares**: já temos `n_frentes`, fazer heterogeneidade.
9. **Sub-períodos finos da Leg 56**: 4 trimestres (pré-PSL-out, PSL-out, pré-Lira, pós-Lira). Verificar trajetória.

---

## 8. Linha do tempo (resumo)

- **Maio 2026**: defesa de qualificação. Banca pediu: tercis por leg, weak divergence, Centrão outcome, controles justificados.
- **Junho 2026 semana 1-2**: download 1,1 GB de bases adicionais (Portal Transp + SICONV + Tesouro + IFI).
- **Junho 2026 semana 3**: construção multi-RP panel + proxies + EDA.
- **Junho 2026 semana 4**: T1-T5 rodados para ambos outcomes (gov + centrão).
- **Junho 17 (hoje)**: 5 tabelas dual no paper, 43 páginas, discussão das narrativas pendente.

---

## Apêndice. Comando rápido para abrir o paper

```bash
open /Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-emendas/docs/paper.pdf
```

Para revisar fonte:
```bash
code /Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-emendas/docs/tex/paper.tex
```
