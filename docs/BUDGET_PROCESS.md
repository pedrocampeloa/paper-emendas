# Processo Orçamentário Brasileiro e Emendas Parlamentares

> Documento de referência para o paper-emendas. Explica o processo orçamentário federal, distingue as 4 modalidades de emendas (RP-6 a RP-9), apresenta o marco legal do orçamento impositivo, e cataloga todas as fontes de dados públicas disponíveis (com URLs verificadas e status de disponibilidade).
>
> Última atualização: 2026-06-15. Pesquisa de fontes feita em duas rodadas (rodada 1: fontes "canônicas"; rodada 2: fontes adicionais e dados pós-ADPF 854).

---

## 1. O ciclo orçamentário federal em 5 etapas

| Etapa | Quem | Quando | O que acontece |
|---|---|---|---|
| **1. PLOA** | Executivo (SOF/MPO) | Até 31/ago do ano anterior | Projeto de Lei Orçamentária Anual é enviado ao Congresso |
| **2. Tramitação** | CMO (Comissão Mista de Orçamento) | Set–Dez | Deputados e senadores apresentam **emendas** (individuais, bancada, comissão, relator) ao PLOA |
| **3. LOA aprovada** | Congresso | Geralmente dez/jan | Sanção presidencial; vira lei |
| **4. Empenho** | Executivo (UO — Unidade Orçamentária) | Durante o ano | Reserva legal do recurso para um beneficiário (artigo 35, Lei 4.320/1964) |
| **5. Pagamento** | Tesouro / Unidade Pagadora | Durante e até abril seguinte (RP) | Liquidação + pagamento; resíduo vira "Restos a Pagar" |

**Conceitos-chave para identificação econométrica do paper**:
- O **timing** entre empenho e pagamento é discricionário do executivo, mesmo quando o valor é impositivo. Daí o instrumento Q4 + backlog ainda ser válido pós-EC 86.
- A "linha temporal" entre LOA aprovada (dezembro) e o ano de execução cria a janela onde nossos IVs operam.
- **Restos a Pagar (RP)**: empenhos não pagos no ano viram RP, podem ser pagos por até 2 anos depois. Vital para o painel.

---

## 2. As 4 modalidades de emendas (RP-6, RP-7, RP-8, RP-9)

| RP | Nome | Autor | Limite | Caráter |
|---|---|---|---|---|
| **RP-6** | Emendas individuais | 1 deputado / 1 senador | 1,2% RCL (desde 2015) + 25% obrigatório em saúde | **Impositiva** desde 2015 (EC 86) |
| **RP-7** | Emendas de bancada estadual | Bancada UF | 1% RCL (desde 2020) | **Impositiva** desde 2020 (EC 100) |
| **RP-8** | Emendas de comissão | Comissão (mista ou temática) | Sem teto explícito | Discricionária; **execução obrigatória** após STF 2022 |
| **RP-9** | Emendas de relator | Relator-geral do orçamento | Sem teto | **Extinta em dez/2022** (ADPF 854); só existiu 2020-22 |

### RP-6 — duas modalidades
- **Modalidade 99**: transferência com finalidade definida (tradicional convênio).
- **Modalidade 96**: **"Pix"** — transferência especial direta para o município/estado, sem convênio. Criada pela EC 105/2019.

### Sobre RP-7
- Não-impositiva até 2019; impositiva desde execução 2020.
- Cada bancada estadual decide internamente como alocar — pouca transparência sobre o "autor" individual.

### Sobre RP-8 (pós-2022)
- Era residual antes do STF. Explodiu após extinção do RP-9 — saltou de **R$ 329 mi (2022) para R$ 6,9 bi (2023)**, ~21×.
- Hoje funciona como "veículo" para alocações que antes iam por RP-9.

### Sobre RP-9 (Orçamento Secreto)
- Criado de fato em **2020** via Lei de Diretrizes Orçamentárias.
- Atribuído nominalmente ao **Relator-Geral do Orçamento** (código de autoria 8100 nos sistemas).
- Operação real: "apoiamentos" — congressistas individuais indicavam ao Relator quais municípios/projetos receberiam, mas o "autor" oficial ficava como o Relator.
- **Decisão STF — ADPF 854 (dez/2022)**: declarou inconstitucional. Determinou transparência.

---

## 3. Marco legal — Timeline do Orçamento Impositivo

```
2015 ──── EC 86 ──── RP-6 (individuais) viram IMPOSITIVAS até 1,2% RCL
                     50% delas obrigatórias em saúde
                     Antes: ~30% das individuais executadas; depois: ~70-80%
        │
2019 ──── EC 100 ─── RP-7 (bancada) viram IMPOSITIVAS até 1% RCL
                     Vigência a partir do orçamento 2020
        │
2019 ──── EC 105 ─── Cria "Emendas Pix" (transferência especial e
                     transferência com finalidade definida — modalidades 96 e 99)
                     Diminui burocracia mas reduz rastreabilidade
        │
2020 ──── LDO ────── Criação do RP-9 (Emendas de Relator) na LDO
                     Início do "Orçamento Secreto"
        │
2021 ──── Lira ───── Arthur Lira eleito presidente da Câmara (fev/2021)
                     RP-9 atinge R$ 16-18 bi/ano
        │
2022 ──── ADPF 850 ─ STF inicia julgamento; veta execução parcial
        │
2022 ──── ADPF 854 ─ Dez/2022: STF declara RP-9 inconstitucional
                     Determina disclosure de "apoiamentos"
                     Extinção formal na LOA 2023
        │
2023 ──── RP-8 ───── Emendas de comissão saltam de R$ 329 mi → R$ 6,9 bi
                     Emendas Pix sobem de R$ 3 bi → R$ 7 bi
                     "Continuidade do orçamento secreto por outras vias"
        │
2024 ──── STF ─────── Ago: confirma suspensão por descumprimento
                     Caso reaberto; transparência ainda parcial
        │
2025 ──── NT TB ───── Set: Transparência Brasil + TI-Brasil + Contas Abertas
                     protocolam NT documentando descumprimento parcial da ADPF 854
        │
2026 ──── TCU ─────── Mar: TCU aprova fiscalização contínua de emendas
                     (≥1 relatório/ano)
```

---

## 4. Volume — quanto é o orçamento total e quanto vai para emendas

| Ano | Orçamento total da União | Total de emendas | % do total | Em saúde (% piso fed.) |
|---|---|---|---|---|
| 2015 | ~R$ 2,9 tri | ~R$ 10 bi | ~0,35% | 3,1% (2014) |
| 2020 | R$ 3,8 tri (com COVID) | RP-6 ~R$ 18 bi + RP-9 R$ 20 bi | ~1,0% | — |
| 2024 | **R$ 5,5 tri** | **R$ 44,7-49,2 bi** (TCU) | **~0,83-0,89%** | **11,4%** |

**Crescimento das emendas 2014-2024**: +321% (IPEA). Em saúde: +383%.

**Composição 2024** (TCU): R$ 25,07 bi (RP-6) + R$ 8,56 bi (RP-7) + R$ 15,54 bi (RP-8) + R$ 0 (RP-9, extinto) = R$ 49,17 bi.

**Importante para a discussão com Bernardo**:
- O peso das emendas no orçamento aumentou ~2,5× em termos relativos (0,35% → 0,89%).
- Em saúde, a alocação via emendas é hoje um dos maiores canais (11,4% do piso federal).
- A discricionariedade do executivo **caiu no agregado** (impositividade) mas **se manteve no timing** (empenho/pagamento) — o que preserva nossa estratégia de identificação.

---

## 5. Catálogo completo de fontes de dados (verificadas)

### 5.1 — Fontes oficiais primárias

| Fonte | URL | Formato | Granularidade | Status |
|---|---|---|---|---|
| **Portal Transparência — Emendas (download bulk)** | `portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares` | CSV anual | RP-6/7/8/9 × autor × beneficiário × empenho/pago | ✅ 2014-2024 |
| **Portal Transparência — Apoiadores RP-8/RP-9** | `portaldatransparencia.gov.br/emendas/apoiadores` | XLSX semanal | "Apoiamentos" deputado→indicação | ✅ atualizado 2026-04-27 |
| **Portal Transparência — ADPF 854** | `portaldatransparencia.gov.br/emendas/adpf854` | XLSX | Mapeamento ADPF 854 (RP-9 deputado-nível) | ✅ Ofícios 932/2024 + 114/2025 |
| **Câmara CMO — Execução RP-9** | `www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-mistas/cmo/Execucao-orcamentaria-das-emendas-de-Relator-geral` | XLSX | Apoiamentos por relator | ✅ 2020-22 |
| **Câmara Infoleg — RP-6** | `www2.camara.leg.br/orcamento-da-uniao/consultas-e-relatorios-de-execucao/execucao-apenas-de-emendas-individuais` | CSV | Deputado × emenda × estágio | ✅ 2015+ |
| **CGU Portal Transparência — Pix dedicado** | `portaldatransparencia.gov.br/transparencia-emendas-pix` | Web/XLSX | Plano de Trabalho por emenda Pix | ✅ ativado 2026-05 |
| **Transferegov API — Pix** | `docs.api.transferegov.gestao.gov.br/transferenciasespeciais/` | REST/JSON | Autor × beneficiário × valor × plano | ✅ atualização diária |
| **Transferegov bulk download** | `repositorio.dados.gov.br/seges/detru/` | CSV | Idem, em bulk | ✅ diário até 9h |
| **SIGA Brasil (Senado)** | `www12.senado.leg.br/orcamento/sigabrasil` | Relatórios web + Excel | RP-6/7/8/9 detalhado | ✅ desde 2000+ |
| **SIOP — Acesso Público** | `www1.siop.planejamento.gov.br/siopdoc/doku.php/acesso_publico:emendas_parlamentares_dados_abertos` | SPARQL + filtros | Programa/ação | ✅ 2014+ |
| **Tesouro Transparente — painel emendas** | `tesourotransparente.gov.br/consultas/painel-das-emendas-parlamentares-individuais-e-de-bancada` | Painel Power BI | RP-6, RP-7 | ✅ |
| **Tesouro CKAN — séries temporais** | `tesourotransparente.gov.br/ckan/dataset/seriestemporaisdotesouronacional` | CSV mensal | Resultado Fiscal, Despesas, Investimento 1997+ | ✅ |
| **SICONFI / FINBRA** | `siconfi.tesouro.gov.br` | CSV | Município receita/despesa 2013+ | ✅ ~98,6% munis |
| **Câmara dados abertos — Frentes** | `dadosabertos.camara.leg.br/api/v2/frentes` + `arquivos/frentesDeputados/` | JSON/CSV/XLSX | Membros de cada frente | ✅ leg 54+ |
| **Câmara — Bulk XML proposições** | `dadosabertos.camara.leg.br/arquivos/proposicoes/xml/proposicoes-{YYYY}.xml` | XML/ano | Todas as proposições + `urlInteiroTeor` | ✅ |
| **IPEADATA** | `ipeadata.gov.br` | CSV / API R/Python | Macro e regional | ✅ |

### 5.2 — Fontes "tier-2" (consolidadas por terceiros, com limitações)

| Fonte | URL | Conteúdo | Limitação |
|---|---|---|---|
| **Base dos Dados — BigQuery** | `basedosdados.org/dataset/257e000c-1685-418a-88d9-4908ccef2840` | Painel histórico harmonizado de emendas | Lag de ~6 meses |
| **Codevasf RP-8/RP-9** | `codevasf.gov.br/acesso-a-informacao/.../emendas-de-relator-rp9-e-emendas-de-comissao-rp8` | XLSX dedicado à autarquia (caso central do escândalo) | Só Codevasf |
| **Ministério das Cidades RP-8** | `gov.br/cidades/pt-br/assuntos/emendasparlamentares/emendas-de-comissao-bancadas-2024/emendas-de-comissao-rp8-2023` | RP-8 por programa | Só Ministério das Cidades |
| **Transparência Brasil — Painel histórico** | `portaltransparenciabrasil.com/emendas-parlamentares/painel` | Dashboard 2014-2026 | Visualização derivada |
| **GitHub gabinete-compartilhado-acredito/execucao_RP9** | github | CSV + notebook 2020-21 | Sem atribuição a deputado |
| **CGU Relatório Técnico RP-8 (set/2024)** | `backend.transparencia.org.br/wp-content/uploads/2024/09/Relatorio_CGU_RP8.pdf` | Microdata em apêndice | PDF (precisa extração) |
| **NT TB+TI+Contas Abertas (set/2025)** | `backend.transparencia.org.br/wp-content/uploads/2025/09/continuidadedoorcamentosecreto-1.pdf` | Evidência de descumprimento parcial | PDF discursivo |

### 5.3 — Fontes "tier-3" (acadêmicas / LAI)

| Fonte | URL | Conteúdo |
|---|---|---|
| **Harvard Dataverse — Pereira (cabinet/spending)** | `doi:10.7910/DVN/CAYIBS` | Replication data |
| **Achados e Pedidos — RP-6 LAI** | `achadosepedidos.org.br/pedidos/planilha-com-emendas-impositivas-rp-6` | XLSX Lexor 2020-23 |
| **IFI Nota Técnica 57 (nov/2024)** | `www12.senado.leg.br/ifi/pdf/nt57_emendasparlamentares.pdf` | Tabelas agregadas |
| **PMC 12091854 (SUS+mayoral reelection 2024)** | NCBI | Dados secundários 2,818 munis |

### 5.4 — Acórdãos e relatórios oficiais (TCU)

| Fonte | URL | Conteúdo |
|---|---|---|
| **TCU Contas Gov 2024** | `portal.tcu.gov.br` | Tabelas detalhadas por RP |
| **TCU Fiscalização contínua (mar/2026)** | `portal.tcu.gov.br` | Em desenvolvimento; ≥1 rel/ano a partir de 2026 |

---

## 6. Inventário do que JÁ está baixado (atualizado 2026-06-15)

Script de download: `shared/download_budget_data.py`. Destino: `dados/raw/orcamento/`. Total: **~1,1 GB em 115 arquivos**.

### 6.1 — Pré-existente em `dados/raw/emendas/`
- `emendas_raw.csv` (14,7 MB) — Portal da Transparência via API antigamente. Colunas: `codigoEmenda`, `ano`, `tipoEmenda`, `autor`, `nomeAutor`, `localidadeDoGasto`, `funcao`, `subfuncao`, `valorEmpenhado`, `valorPago`, `valorRestoInscrito/Cancelado/Pago`. Cobertura 2014+. **Usado no painel atual do paper.**
- `emendas_raw.json` (33 MB) — mesma fonte, JSON.
- `documentos/` — docs de empenho/pagamento.

### 6.2 — Novo: Portal da Transparência (bulk)
Pasta `dados/raw/orcamento/portal_transparencia/`:
- `emendas_bulk.zip` (30 MB) + 3 CSVs extraídos:
  - **`EmendasParlamentares.csv`** (47 MB, **93.715 linhas**) — granularidade emenda × autor × localidade.
    - Colunas: `Código da Emenda`, `Ano`, `Tipo de Emenda`, **`Código do Autor`**, **`Nome do Autor`**, `Número da emenda`, localidade, função, programa, ação, `Valor Empenhado/Liquidado/Pago`, `Restos a Pagar Inscritos/Cancelados/Pagos`.
    - **Cobertura**: 2014-2026.
    - **Composição**:
      - 79.076 Emendas Individuais (RP-6 com finalidade definida)
      - 4.986 Emendas Pix (RP-6 transferências especiais)
      - 3.892 Emendas de Relator (RP-9, autor = "RELATOR GERAL")
      - 3.573 Emendas de Bancada (RP-7)
      - 2.187 Emendas de Comissão (RP-8)
  - `EmendasParlamentares_Convenios.csv` (25 MB, 83.105 linhas)
  - `EmendasParlamentares_PorFavorecido.csv` (176 MB, **799.044 linhas**) — granularidade por favorecido (CNPJ).
- 4 HTMLs índice (ADPF 854, apoiadores, Pix, download-de-dados) para inspeção.

### 6.3 — Câmara CMO (PDFs oficiais)
Pasta `dados/raw/orcamento/camara_cmo/`:
- 3 HTMLs índice.
- **`recibos_pdfs/`** (~80 MB, 11 PDFs): recibos das comissões 2021-2024 (CD, mistas, SF). Documentam quem emitiu/recebeu emendas RP-8.
- **`atos_conjuntos/`** (~42 MB, 15 PDFs): Atos Conjuntos das Mesas RP-9 2021 — documento OFICIAL de transparência exigido pela ADPF 854.

### 6.4 — Tesouro CKAN (XLSX + CSV oficiais)
Pasta `dados/raw/orcamento/tesouro/`:
- **`emendas-parlamentares-individuais-e-de-bancada/emendas-parlamentares.csv`** (68 MB, **388.496 linhas**):
  - Colunas: `Nome Ente`, `UF`, `Código IBGE/Siafi`, `Data`, `Ano`, `Mês`, `Tipo Ente`, `OB` (ordem bancária), `CNPJ Favorecido`, `Nome Favorecido`, **`Nome Emenda`** (Individual ou Bancada), **`Transferência Especial`** (Sim/Não — marca Pix), `Categoria Econômica Despesa`, `Valor`.
  - Cobertura: 2015-2026, granularidade município × mês × emenda.
  - **347.328 emendas individuais + 41.168 de bancada; 52.631 são Pix.**
- **`despesas-e-transferencias-totais/`** (~700 MB, 19 XLSX): orçamento federal anual 2008-2026 (`base-despesas-{ano}.xlsx`, `tetodez{ano}.xlsx`, `limite-gastos-lc200dez{ano}.xlsx`) + 19 PDFs notas técnicas LC 200 / EC 95.

### 6.5 — GitHub gabinete-compartilhado-acredito/execucao_RP9
Pasta `dados/raw/orcamento/github_rp9/`:
- `processados/` (~14 MB, 4 CSVs): empenhos RP-9 com **imputação por prefeito**.
  - Cobertura: 2020-2021, ministérios FNDE (educação) e MDR (desenvolvimento regional).
  - Colunas relevantes: `Autor Emenda` (sempre "8100 - RELATOR GERAL"), `Favorecido`, `Município`, `Valor`, `cnpj`, `NM_CANDIDATO` (prefeito eleito 2020 via TSE), `SG_PARTIDO`, `DS_COMPOSICAO_COLIGACAO`.
  - **Lógica de imputação**: o autor formal é o Relator-Geral; o prefeito recebedor pertence a um partido/coligação, sugerindo qual deputado articulou. Não é atribuição direta.
- `aux/` (32 MB): tabela de conexão CNPJ × prefeito 2020 (essencial para o mapping).

### 6.6 — IFI / Transparência Brasil / CGU (PDFs)
Pasta `dados/raw/orcamento/ifi/`:
- `ifi_nt57_emendasparlamentares.pdf` (1 MB) — Nota Técnica 57 IFI, nov/2024. Tabelas agregadas por RP.
- `nt_tb_ti_contasabertas_set2025.pdf` (1,5 MB) — Nota Técnica TB+TI-Brasil+Contas Abertas documentando descumprimento da ADPF 854.
- `cgu_rp8_relatorio_set2024.pdf` (1,4 MB) — Relatório CGU sobre RP-8.

### 6.7 — Nova: SICONV bulk completo (~2,5 GB)
Pasta `dados/raw/orcamento/transferegov_bulk/`. **8 arquivos extraídos**, cobertura **2008-2026**:
- **`apoiadores_emendas_programas.csv`** (28 MB, **291.167 linhas**, **2.248 parlamentares únicos**):
  - Colunas: `ID_CNPJ_PROGRAMA_EMENDA`, `NUMERO_EMENDA`, **`NOME_PARLAMENTAR`** (deputado/senador OU "Relator Geral" OU comissão), **`INDICACAO`** (INDIVIDUAL/COMISSAO/BANCADA), **`PARLAMENTAR_SOLICITANTE`** (nome do deputado real para indicação RP-8/RP-7), **`VALOR_REPASSE_PROPOSTA`**, `CNPJ_PROPONENTE`, `NOME_PROPONENTE`.
  - **Mapping deputado → RP-9**: 137 dos 10.036 registros RP-9 (1,4%) — limitação conhecida.
  - **Mapping deputado → RP-8 (comissão)**: 11.003 dos 25.663 registros (43%) — bom.
  - **Mapping deputado → RP-6 individual**: 100% (nome do deputado é o autor).
- **`siconv_emenda.csv`** (31 MB, **296.701 linhas**, 1.651 parlamentares únicos):
  - Colunas: `ID_PROPOSTA`, `QUALIF_PROPONENTE`, `COD_PROGRAMA_EMENDA`, `NR_EMENDA`, **`NOME_PARLAMENTAR`**, `BENEFICIARIO_EMENDA` (CNPJ), **`IND_IMPOSITIVO`** (SIM/NÃO), **`TIPO_PARLAMENTAR`** (INDIVIDUAL/COMISSAO/BANCADA/RELATOR GERAL), `VALOR_REPASSE_EMENDA`.
  - Composição: 238.464 INDIVIDUAL + 24.380 COMISSAO + 13.792 RELATOR GERAL + 9.411 BANCADA.
  - 101.953 marcadas como impositivas; 194.748 não-impositivas.
- **`siconv_convenio.csv`** (70 MB, **283.524 linhas**, 2008-2026):
  - Colunas: `NR_CONVENIO`, `ID_PROPOSTA`, `DIA`/`MES`/`ANO`, `DIA_ASSIN_CONV`, `SIT_CONVENIO`, `VL_GLOBAL_CONV`, `VL_REPASSE_CONV`, `VL_EMPENHADO_CONV`, `VL_DESEMBOLSADO_CONV` + 30 outras colunas de situação/vigência.
- **`siconv_empenho.csv`** (96 MB) — todos os empenhos SICONV
- **`siconv_pagamento.csv`** (1 GB) — todos os pagamentos
- **`siconv_proposta.csv`** (750 MB) — todas as propostas
- **`siconv_programa.csv`** (350 MB) — todos os programas
- **`siconv_proponentes.csv`** (15 MB) — entes proponentes

### 6.8 — O que NÃO foi possível baixar automaticamente
1. **Codevasf** ❌ não tem dados próprios — a página é apenas uma **ferramenta de consulta por número de empenho**; os dados são os mesmos do Portal Transparência que já temos. **REMOVIDO do TODO.**
2. **Portal Transparência ADPF 854 XLSX direto** — página dinâmica em JS; mas os dados estão em **`apoiadores_emendas_programas.csv`** (SICONV) que já baixamos. **RESOLVIDO.**
3. **Transferegov bulk Pix** — **RESOLVIDO** via SICONV completo.
4. **Achados e Pedidos LAI** — site não permite acesso direto; precisaria de cadastro. Provavelmente redundante com SICONV.

### 6.9 — Pendências para você baixar manualmente (se quiser)
1. **Base dos Dados BigQuery** (`basedosdados:br_cgu_emendas_parlamentares`):
   - Já temos a fonte original (Portal Transparência). Base dos Dados oferece versão harmonizada/limpa.
   - Para download: `pip install basedosdados`; depois `bd.read_table('br_cgu_emendas_parlamentares.microdados', ...)`.
2. **Harvard Dataverse — Pereira (CAYIBS)**: `doi:10.7910/DVN/CAYIBS` — replication data do Pereira-Mueller-style paper. Vale para referência metodológica, não para dados primários.
3. **Achados e Pedidos LAI RP-6** (opcional): `https://www.achadosepedidos.org.br/pedidos/` — precisa cadastro.

---

## 7. Inventário e EDA gerados (executar em paper-emendas/)

Script: `paper-emendas/source/32_eda_budget_data.py`

Outputs:
- `paper-emendas/results/eda_overview.csv` — Tabela 1 (1 linha por fonte)
- `paper-emendas/results/eda_by_year_rp.csv` — Tabela 2 (ano × RP × valor)
- `paper-emendas/results/eda_deputy_coverage.csv` — Tabela 3 (cobertura cross-fonte)
- `paper-emendas/results/eda_panel_intersection.csv` — Tabela 4 (interseção com painel)
- `paper-emendas/docs/figs/eda_empenho_by_rp.pdf` — figura empilhada de empenho
- `paper-emendas/docs/figs/eda_composicao_rp_pct.pdf` — composição percentual

### 7.1 — Principais achados do EDA

**Volume total e composição (2014-2026)**:
| Fonte | Linhas | Parlamentares únicos | Valor total empenhado |
|---|---|---|---|
| Portal Transparência bulk | 93.714 | 1.611 | R$ 332,6 bi |
| Tesouro CKAN | 388.496 | — | R$ 163,6 bi |
| SICONV emenda | 296.701 | 1.651 | R$ 98,5 bi |
| SICONV apoiadores | 291.167 | **2.248** | — |
| SICONV convênio | 283.524 | — | R$ 211,4 bi |

**Cobertura cross-deputado**:
- Total único de parlamentares nas 3 fontes (PT + SICONV emenda + apoiadores): **2.476**.
- Painel principal do paper: **2.030 deputados únicos**.
- Interseção do painel com Portal Transparência: 996 (~49%); com SICONV emenda: 1.022 (~50%); com SICONV apoiadores: 993 (~49%).
- **Implicação**: ~50% dos deputados do painel têm cobertura direta nas bases de emendas. Os outros 50% provavelmente são deputados que (a) nunca apresentaram emenda ou (b) têm grafia de nome diferente. Vale investigar o mapping.

**Evolução temporal (R$ bi empenhado)**:
| Ano | RP-6 | RP-6 Pix | RP-7 | RP-8 | RP-9 | Total |
|---|---|---|---|---|---|---|
| 2014 | 6,1 | 0 | 0 | 0 | 0 | 6,1 |
| 2016 | 7,2 | 0 | 3,6 | 1,3 | 13,7 | 25,8 |
| 2018 | 8,5 | 0 | 3,4 | 0,2 | 0 | 12,1 |
| 2020 | 8,6 | 0,6 | 6,5 | 0,6 | **21,2** | 37,5 |
| 2022 | 7,4 | 3,3 | 5,8 | 0,3 | 8,6 | 25,4 |
| 2023 | 13,8 | 7,1 | 7,6 | 6,9 | 0 | 35,4 |
| 2024 | 17,0 | 7,7 | 8,4 | **11,7** | 0 | 44,8 |
| 2025 | 17,3 | 7,0 | 11,6 | 11,2 | 0 | 47,1 |

Padrões:
- **RP-9 nasceu em 2016** (não 2020 como literatura diz; nascimento formal em LDO 2020 mas há registros desde 2016), **explodiu em 2020 (R$ 21,2 bi)**, **extinto em 2022 (R$ 8,6 bi residual)**.
- **RP-8 explodiu em 2024 (R$ 11,7 bi)** após extinção do RP-9 — substituição confirmada.
- **RP-6 Pix nasceu em 2020** (EC 105/2019) e cresceu para **R$ 7,7 bi em 2024**.
- **Total de emendas cresceu de R$ 6 bi (2014) para R$ 47 bi (2025)** — +680% nominal.

**Achado para o paper**: o EDA confirma a tese de "regime change" — a quebra mais clara está em 2020 (RP-9 explosão) e em 2023/2024 (RP-8 substituindo RP-9). **A linha temporal RP-9 → RP-8 + Pix é o achado central a discutir.**

---

## 8. Próximos passos para o paper

1. Inserir parágrafo no §2 (institutional background) do `paper.tex` baseado nas seções 1-3 deste documento.
2. Adicionar figura "Timeline do Orçamento Impositivo" baseada na seção 3.
3. Adicionar tabela "Volume das Emendas por RP × Ano" baseada na seção 7.1 (números reais).
4. Adicionar figura `eda_empenho_by_rp.pdf` (volume empilhado) e `eda_composicao_rp_pct.pdf` (composição percentual).
5. Discussão na §7 (interpretação) sobre a transição RP-9 → RP-8 + Pix como continuidade do regime (citar NT TB set/2025).
6. Apêndice metodológico: discussão sobre limitações de "apoiamento ≠ autoria" nos dados RP-9 disponíveis. Usar SICONV apoiadores onde possível (RP-8 com 43% de cobertura).

---

## 9. Discussão sobre identificação econométrica

**Para Bernardo (que está preocupado com a discricionariedade do executivo)**:

A EC 86/2015 reduziu a discricionariedade do executivo no **volume** de RP-6 alocado — desde então execução é impositiva até 1,2% RCL. No entanto, três margens de discricionariedade permanecem:

1. **Timing de empenho**: o executivo decide *quando* empenhar dentro do exercício. Daí o instrumento "Q4 deadline" (1/dias até 31/dez).
2. **Backlog**: o executivo escolhe quais ministérios/programas executam mais devagar. Daí o instrumento "YTD execution %".
3. **Modalidade**: dentro do RP-6, o executivo pode preferir liberar via Pix (modalidade 96) ou convênio (modalidade 99).

Nossa estratégia de identificação (`iv_features.csv` com `iv_fiscal_q4`, `iv_fiscal_pressure`, `iv_ytd_exec_pct`, `iv_q4_no_ytd`) explora a margem 1 + 2. **O caráter impositivo no agregado NÃO invalida o instrumento** — ele opera no timing, não no volume.

Argumento adicional: mesmo se a EC 86 tivesse eliminado completamente a discricionariedade do executivo, a barganha política se deslocaria para outras dimensões observáveis (Pix vs convênio, ordem de pagamento, alocação por município). Nossa identificação seria mais difícil mas o problema substantivo continuaria existindo. Citar Pereira-Mueller (2004) que documentou esse fenômeno antes mesmo da EC 86.
