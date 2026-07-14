# MUSTDO_v2 — Paper Emendas (pós-qualificação)

> Consolidação dos feedbacks da banca de qualificação (02/06/2026): Daniel Cajueiro, Bernardo Mueller, Rafael Terra.
> Alvo: **Public Choice** — draft revisado submissível em 4 semanas (deadline interno: **2026-07-15**).
> Versão de partida: `main_results_v3.csv` (PLIV-DML + Deputy-FE + party-FE + cluster-SE).
>
> **Status pré-existente**: 31 scripts, MUSTDO.md (172 linhas) e METHODOLOGY_LOG.md (950 linhas) cobrem Bloco 0–3 da rodada anterior.
> **Este documento NÃO duplica o anterior** — foca exclusivamente em itens novos da banca.

---

## STATUS FINAL DOS TODOs (21/06/2026)

Cross-check item-a-item contra `docs/tex/paper.tex` (versão atual com Narrativa F + Legislative Capture):

| Item | Descrição | Status | Onde no paper |
|---|---|---|---|
| **A.1** | Tercis polarização por leg | ✅ Feito | §6.3 (`subsec:terciles_by_leg`), Tabela 10 |
| **A.2** | Quebra Lira (fev/2021) | ✅ Feito (refinado) | §6.4 (Legislative capture), Tabela 11, Fig 5 |
| **A.3** | `d_centrao` + heterogeneidade | ✅ Feito | §6.5 (`subsec:centrao_outcome`), Tabela 12 |
| **A.4** | Outcome alinhamento Centrão | ✅ Feito | §6.5, Tabela 12 |
| **A.5** | T quadrático (T+T²) | ✅ Feito (robustez) | App F (`app:quadratic`), Tabela 14; IV-2SLS com QR rank-validation; T*≈3M R$, U-shape em todas as legs |
| **A.6** | PECs 2 turnos | ✅ Feito (robustez) | App G (`app:twopecs`), Tabela 15; 9 PECs, 3,383 obs; β=+0.37 sem FE, =0 com PEC FE |
| **A.7** | Stylized facts | ✅ Feito | §2.4 (`subsec:stylized_facts`), Tabela 1+2, Figs 1-2 |
| **A.8** | Tabela testes consolidada | ✅ Feito | Tabela 3 (`tab:iv_validation`) |
| **A.9** | Weak vs Strong como mediador | ✅ Feito | App H (`app:dualmed`), Tabela 16; Strong absorve 31% Leg55, 10% Leg56; Weak ~0% em ambas |
| **A.9.5** | Cargos legislativos como controle/het | ✅ Feito | §6.6 (`subsec:cargos_het`), Tabela 13; Tier-2 attenua backfire ($-0.38$ n.s. vs $-1.03^{***}$ sem cargo) |
| **B.1** | Convenções literatura | ⚠️ A revisar | Reescrita ampla feita; verificar página 10 com Bernardo |
| **B.2** | Texto → tabelas/gráficos | ✅ Feito | Tabelas 1-13 + 5 figuras |
| **B.3** | Justificar controles | ✅ Feito | §4 parágrafo de ablação explícita inserido (142 controles, 5 famílias) |
| **B.4** | Reescrever backfire (credibility cost) | ✅ Feito | §7 (Discussion), 5 ocorrências do termo |
| **C.1** | Orçamento federal total | ✅ Feito | §2.4, Tabela 1 |
| **C.2** | EC 86/100/105 | ✅ Feito | §2.1 (`subsec:legal_architecture`) |
| **C.3** | RP-9 nível deputado | ✅ Feito | §6.1 (controles d_rp9, Tabela 9) + Proxy P4 imputada |
| **C.4** | RP-8 + Pix pós-STF | ✅ Feito | §2.2, §7 (TransparenciaBrasil2025 citado) |
| **D.1** | Causalidade reversa | ✅ Feito | §7 (parágrafo refinado) |
| **D.2** | STF event study | ✅ Feito (Apêndice) | App A (`app:event`), Fig 6 |
| **D.3** | Excluir leg 57 | ✅ Feito | §2.2 (justificativa explícita) |
| **D.4** | Tipologia A/B | ✅ Feito | §1 (programmatic vs identity-driven) |

### Achados pós-defesa adicionais (não-MUSTDO)

| Achado | Onde |
|---|---|
| **Narrativa F (Legislative Capture)** — pork muda de principal | §6.4, Abstract, §1, §7, §8 |
| **6 proxies extras** | `panel_proxies_extra.csv` (P1-P6), STATE_OF_PLAY §1.5.bis.STATUS |
| **n_reps=3 rodada definitiva** | `results/n3_*` (gov + y_pres) |
| **y_pres_camara_orient** (outcome alternativo) | §6.4, Tabela 11 |

### Pendências para submissão Public Choice

**Críticas (P1)**:
- B.1 — revisão da página 10 com Bernardo (item subjetivo)

**Nice-to-have (P3)**:
- Atualizar `METHODOLOGY_LOG.md`
- `response_to_committee.tex`

Status global (21/06/2026, 16h15): **~98% completo** (22 de 22 itens substantivos entregues; apenas B.1 subjetivo + housekeeping P3 abertos).

---

## Princípios de organização

Cada item da banca está etiquetado:
- **[B-XX]** vem da banca diretamente (exam transcript).
- **[N-XX]** vem de "nossas" próprias notas pós-defesa.
- **[Q-XX]** é questão da banca que demanda resposta no paper (não nova análise).

Cada item tem: **Prioridade** (P1 crítico / P2 importante / P3 nice-to-have) + **Tipo** (análise / escrita / dado externo / resposta) + **Status atual** + **Como atacar**.

---

## BLOCO A — Mudanças empíricas (novas análises)

### A.1 — Tercis de polarização SEPARADOS por legislatura
- **Origem**: [B-01] Bernardo (e Q-3 da banca) — "tercis na análise pooled não permitem distinguir 'polarização causa backfire' de 'era Bolsonaro é o fenômeno'."
- **Prioridade**: **P1** (crítico).
- **Status**: parcialmente pronto. `heterogeneities_v2.csv` já tem tercis de `align_hist` e `margem` POR LEG. **`decomposition_v2.csv` tem tercis de polarização SÓ POOLED**.
- **Como atacar**: estender `22_decomposition_v2.py` (ou criar `22b_pol_tercis_by_leg.py`). Spec idêntica à pooled, mas split por `idLegislatura ∈ {55, 56}` antes do tercil split. **Cuidado**: tercis precisam ser definidos DENTRO de cada legislatura (não usar cortes pooled).
- **Resultado esperado se Bernardo estiver certo**: leg 55 mostra coeficiente positivo nos 3 tercis (cooptação clássica não-modulada por polarização); leg 56 mostra gradiente negativo apenas no tercil alto.
- **Output**: nova Tabela em `paper.tex` (Seção 6 ou Apêndice C).

### A.2 — Quebra estrutural em fevereiro/2021 (eleição de Lira)
- **Origem**: [N-01] discussão durante defesa — "no governo Bolsonaro há um aumento enorme do orçamento secreto + Arthur Lira é eleito presidente da Câmara, isso muda tudo".
- **Prioridade**: **P1**.
- **Status**: NÃO existe. `07_subperiods_leg56.py` quebra leg 56 em mai/2020 (saída PSL), não em fev/2021.
- **Como atacar**: criar `07b_subperiods_lira.py` com 3 sub-períodos:
  - **PSL era**: 2019-01 → 2020-04 (até saída do PSL)
  - **Pré-Lira (RP-9 nascendo)**: 2020-05 → 2021-01
  - **Pós-Lira (Centrão consolidado + RP-9 maduro)**: 2021-02 → 2022-12
  - Rodar PLIV-DML em cada sub-período. Salvar em `results/subperiods_lira.csv`.
- **Resultado esperado**: coeficiente negativo se concentra em pós-Lira; pré-Lira deve estar próximo de zero ou levemente positivo.

### A.3 — Variável `d_centrao` + heterogeneidade Centrão vs identity-party
- **Origem**: [B-02] Bernardo, [N-02] — "talvez o efeito que você atribui à polarização seja na verdade do Centrão fagocitar as emendas".
- **Prioridade**: **P1**.
- **Status**: NÃO existe variável binária.
- **Como atacar**:
  1. Definir lista de partidos do Centrão por período (literatura: Limongi, Power, Melo, Pereira). Sugestão: **PP, PL, Republicanos, Solidariedade, União Brasil (após fusão out/2021), PTB, Avante, PSD, MDB (condicional ao período)**. Documentar fonte.
  2. Criar `d_centrao_t` (varia no tempo, observando filiações na data do voto).
  3. Rodar heterogeneidade `T × d_centrao` em leg 55 e leg 56 separadamente.
  4. Rodar análise paralela com `d_pt` e `d_pl` (identity-parties) como categoria contrastante.
- **Output**: nova Tabela. **Crítico para a narrativa**.

### A.4 — Outcome alternativo: alinhamento com bloco do Centrão
- **Origem**: [N-03] — "talvez no leg 56 o que está acontecendo é que deputados se alinham mais com Lira do que com Bolsonaro".
- **Prioridade**: **P2**.
- **Status**: NÃO existe.
- **Como atacar**: redefinir Y como `alinhamento_com_centrao` (deputado vota igual à maioria dos deputados do Centrão na mesma votação). Rerodar PLIV-DML em leg 56. **Hipótese**: coeficiente positivo significativo — emendas compram alinhamento com o Centrão, não com o governo.
- **Output**: parágrafo + tabela em Seção 6 (mecanismos).

### A.5 — Tratamento quadrático (T + T²)
- **Origem**: [B-03] banca — "será que o efeito é monotônico em R$?".
- **Prioridade**: **P2**.
- **Status**: NÃO existe.
- **Como atacar**: rodar PLIV-DML com `T` e `T²` simultaneamente como tratamentos (DML multivariado). Reportar curva resposta e ponto de inflexão.
- **Cuidado**: identificação fica mais frágil (2 IVs precisam discriminar T e T²). Talvez exigir IVs adicionais ou aceitar identificação parcial.
- **Output**: figura curva resposta + tabela coeficientes.

### A.6 — Análise de votações em 2 turnos (PECs)
- **Origem**: [B-04] Bernardo — referência ao próprio trabalho anterior dele.
- **Prioridade**: **P2**.
- **Status**: NÃO existe detecção.
- **Como atacar**:
  1. Identificar pares (1º turno, 2º turno) de PECs por `descricao`/`siglaProposicao` em `votacoes_file_.csv`.
  2. Hipótese: emenda chega ENTRE turnos → identificar efeito within-PEC.
  3. Modelo: `Y_v2 − Y_v1 = θ × ΔEmenda + ε`, com IV similar.
- **Output**: subseção dedicada (talvez Apêndice D); pode ser narrativamente forte se sinal aparecer.

### A.7 — Análise descritiva: distribuição histórica das emendas
- **Origem**: [B-05] banca + [N-04] — "vocês têm que mostrar a foto: base vs Centrão, quem ganha mais em proporção".
- **Prioridade**: **P1** (relativamente fácil).
- **Status**: parcial. Há tabelas descritivas básicas; faltam recortes pedidos.
- **Como atacar**: criar `32_descriptive_stats.py`:
  - Tabela: emendas (mediana, p25, p75) × {coalizão, oposição, centrão} × ano
  - Tabela: emendas por deputado / total da União / total impositivo (ver dado externo C.1)
  - Figura: série temporal % do orçamento que vai para emendas (2015-2024)
  - Tabela: emendas pagas vs autorizadas (gap fiscal); destacar Q4
  - Correlação entre emenda e cada controle (apontar quais correlacionam forte → discutir multicolinearidade controlada).
- **Output**: nova Seção 3.2 ("Stylized Facts").

### A.8 — Estatísticas de teste em formato de tabela
- **Origem**: [B-06] banca — "vocês citam Sargan, AR, RV no texto, coloca em uma tabela compacta".
- **Prioridade**: **P1** (apenas formatação).
- **Status**: valores existem em `tier1_*.csv`, `iv_validation.csv`; falta a tabela única.
- **Como atacar**: criar `33_test_table.py` que consolida em uma tabela:
  - Linhas: PLR, PLIV-bl, PLIV-fiscal × {pooled, 55, 56}
  - Colunas: θ, SE, Sargan p, AR 95% CI, Cinelli-Hazlett RV, Kleibergen-Paap (se aplicável)
- **Output**: Tabela única em §5 (validação dos instrumentos).

### A.9.5 — Cargos no Executivo / Comissões como canais paralelos de pork (robustez)
- **Origem**: discussão pós-defesa — pork pode operar via cargos comissionados, comissões legislativas, frentes parlamentares, indicações em estatais (não monetário). Atualmente o painel só mede RP-6/Pix/RP-8/RP-9.
- **Prioridade**: P3 (robustez para versão final).
- **Status**: nenhum dado integrado ainda.
- **Como atacar**:
  1. **Cargos legislativos** (já temos via API Câmara): construir `d_dep_lideranca_t` (presidente comissão, líder partido/bloco, mesa diretora) por deputado×data via `/orgaos/{id}/membros` e `/lideres`. Já tem em `panel_features.csv` colunas `d_mesa_*`, `d_lider_*` — usar como controle adicional ou interação.
  2. **Cargos no Executivo** (precisa coleta nova): Portal da Transparência `/cargos-comissionados`. Matching deputado→cargo é difícil (raramente direto; vai via parentes). Limitação: scope reduzido.
  3. **Frentes parlamentares** (`/frentes/{id}/membros`): já no painel via `n_frentes`, `pct_frentes`. Pode incluir como interação `T × n_frentes`.
- **Output**: spec robustez com controles adicionais; heterogeneidade por liderança.
- **Limitação**: cargos comissionados raramente vão direto ao deputado (vão para parentes/indicados). Matching nominal/familial caro.

### A.9 — Weak vs Strong divergence como mediador
- **Origem**: [N-05] (já discutido pré-defesa) — Paper 2 mostra Strong > Weak na era Bolsonaro; Paper 3 ainda não usa.
- **Prioridade**: **P3** (linkage entre papers; opcional para Public Choice).
- **Status**: NÃO existe. Variáveis `pol_paper_forte_mds` e `pol_paper_fraca_mds` já estão no painel (usadas em `26_*` e `29_*` como medidas separadas, nunca em interação dual ou mediação dupla).
- **Como atacar**: estender `29_mediation_polarization.py` para mediação Acharya-Blackwell-Sen com mediadores duplos.
- **Output**: subseção ou apenas figura comparativa.

---

## BLOCO B — Mudanças de escrita (sem nova análise)

### B.1 — Seguir convenções da literatura (página 10)
- **Origem**: [Q-1] banca — "página 10 do paper, vocês têm que seguir mais o template da literatura".
- **Prioridade**: **P1**.
- **Status**: precisa checar `paper.tex` página ~10 para entender o que estava lá. **TODO ao começar**: localizar a referência exata.
- **Como atacar**: revisitar `paper.tex` (provavelmente seção 4 — método), comparar com 2-3 papers do Public Choice + EJPE recentes, ajustar notação/ordem.

### B.2 — Mover texto-conteudo para tabelas/gráficos onde aplicável
- **Origem**: [B-07] banca — "vocês descrevem demais no texto, ponha em tabela".
- **Prioridade**: **P2**.
- **Status**: revisão geral do `paper.tex`.
- **Como atacar**: passar uma vez por todas as seções identificando descrições verbais de números → mover para tabela/figura compacta + frase de leitura.

### B.3 — Justificar melhor a seleção de controles
- **Origem**: [B-08] Bernardo — "não me convenceu que 245 controles é a escolha certa, justifiquem com mais clareza".
- **Prioridade**: **P1**.
- **Status**: discussão existe em §4 mas é técnica.
- **Como atacar**: criar parágrafo em §4 explicando (i) por que o conjunto largo é necessário em DML (sparsity-after-selection), (ii) por que `full_clean` foi escolhido vs `reduced`, (iii) ablação em `socio_ablation.csv` (year-FE excluído, party-FE incluído).

### B.4 — Reescrever interpretação backfire com cuidado causal
- **Origem**: [N-06] — durante defesa, tive que reformular ao vivo a interpretação do sinal negativo da leg 56.
- **Prioridade**: **P1**.
- **Status**: paper atual tem versão escrita pré-defesa; precisa incorporar interpretação refinada.
- **Como atacar**: subseção §7 "Interpretation". Argumentar:
  1. IV controla causalidade reversa ("deputado em apuros recebe emenda extra") — não é isso.
  2. Mecanismo plausível: deputado recebe emenda → sinaliza captura → eleitorado pune ou peer-deputies punem → deputado se alinha menos com governo para preservar credibilidade.
  3. Alternativa: deputado recebe emenda do governo MAS alinhamento real é com Centrão (ver A.4).
  4. Discutir limitações dessa interpretação (não pode ser definitivamente provada com IV apenas).

---

## BLOCO C — Dados externos a coletar

> Pesquisa concluída em 15/06/2026. Resumo: viável para C.1 e C.2; viável parcial para C.3.

### C.1 — Orçamento federal total e composição por RP (2015-2024)
- **Origem**: [Q-2] banca — "vocês têm que mostrar quanto é o volume de emendas em % do orçamento total".
- **Prioridade**: **P1**.
- **Fontes disponíveis** (verificadas):
  - **Portal da Transparência** — `portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares` (CSV anual, 2014-2024, com campo `Resultado Primário` que separa RP-6/7/8/9).
  - **IFI Nota Técnica 57** (nov/2024) — tabelas já agregadas com obrigatórias vs discricionárias.
  - **Tesouro Transparente** — painel emendas individuais e bancada.
- **Como atacar**: criar `shared/download_orcamento_federal.py` puxando CSVs anuais → consolidar em `dados/interim/orcamento_federal_2015_2024.csv` com colunas: ano, total_uniao, total_obrigatorias, total_discricionarias, RP6_aut, RP6_pago, RP7_aut, RP7_pago, RP8_aut, RP8_pago, RP9_aut, RP9_pago.
- **Output**: alimenta A.7 (descritivas) e B.2 (tabelas em vez de texto).

### C.2 — Marco legal do Orçamento Impositivo
- **Origem**: [Q-3] banca — "discutam o impositivo: EC 86, EC 100, EC 105".
- **Prioridade**: **P1** (apenas escrita).
- **Status**: não está discutido no paper atual.
- **Como atacar**: adicionar parágrafo em §2 (institutional background):
  - **EC 86/2015**: torna RP-6 impositiva até 1,2% RCL; metade em saúde.
  - **EC 100/2019**: torna RP-7 (bancada) impositiva até 1% RCL.
  - **EC 105/2019**: cria "emendas Pix" (transferências especiais e com finalidade definida).
  - Discutir implicação para identificação: o caráter impositivo significa que o tratamento NÃO depende mais de discricionariedade do executivo no agregado, MAS o timing de empenho (instrumento) ainda é discricionário.

### C.3 — Dados RP-9 (Orçamento Secreto) nível deputado
- **Origem**: [Q-4] banca — "vocês têm que tentar pegar os dados liberados pelo STF".
- **Prioridade**: **P2** (já existe imputação em `decomposition_v2.csv` x2/x3; dados reais são bônus).
- **Status pesquisa**: parcialmente viável.
  - **Disponível**: `portaldatransparencia.gov.br/emendas/adpf854` (XLSX com indicações por parlamentar — "apoiamentos" Ofícios 932/2024 e 114/2025 do Congresso ao STF).
  - **Disponível**: `www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-mistas/cmo/Execucao-orcamentaria-das-emendas-de-Relator-geral` (XLSX).
  - **Limitação crítica**: planilhas chamam "apoiamento", não "autoria"; vínculo deputado→valor é incompleto (Nota Técnica TB/TI-Brasil/Contas Abertas set/2025).
- **Como atacar**:
  1. Criar `shared/download_rp9.py` para os 2 XLSX.
  2. Padronizar IDs (`cpf` ou `nome normalizado`) e match com `dep_info.csv`.
  3. Construir `rp9_by_dep_year.csv` (deputado × ano × valor indicado).
  4. **Substituir** as imputações x2/x3 de `22_decomposition_v2.py` pelos dados reais.
- **Output**: nova versão de R2.7 (`decomposition_v3.csv`). **Limitação assumida**: dados oficiais com cobertura parcial.

### C.4 — Dados pós-STF (RP-8 inflado + emendas Pix)
- **Origem**: [N-07] — narrativa de continuidade do orçamento secreto via outras vias.
- **Prioridade**: **P3**.
- **Como atacar**: usar dados de C.1 para mostrar salto de RP-8 (R$329mi → R$6,9bi de 2022 para 2023) e crescimento Pix (R$3bi → R$7bi). Referenciar Nota Técnica TB/TI-Brasil set/2025.
- **Output**: 1-2 parágrafos em §7 (interpretation) sobre continuidade do regime.

---

## BLOCO D — Respostas diretas (sem nova análise)

> Itens onde a banca pediu esclarecimento que pode ser atendido com parágrafo + cita ao já existente.

- **D.1** — *"Vocês podem testar causalidade reversa?"* → **resposta**: IV-DML controla isso por construção (a residual T̃ é T menos m(X)); referência a `01_*` (placebo voto livre = nulo) e à exclusão restriction.
- **D.2** — *"O experimento natural do STF (ADPF 850) — vocês exploram?"* → **resposta**: sim, event study mensal está em `31_event_study_stf.py` + `event_study_stf_monthly.csv`. Está no Apêndice A. **Considerar**: mover para corpo principal? Decisão narrativa.
- **D.3** — *"Por que excluir leg 57?"* → **resposta**: emendas têm lag estrutural no Portal da Transparência (último ano completo = 2024). Citação ao CLAUDE.md `data_cutoffs.md`.
- **D.4** — *"Os achados servem como uma 'tipologia' de regimes pork-barrel?"* → **resposta**: sim, dedicar parágrafo na introdução nomeando: **Regime A (clássico cooptativo, Temer 2016-2018)** vs **Regime B (negociado-fragmentado, Bolsonaro-Lira 2021-2022)**.

---

## Pipeline cronológico de 4 semanas (15/06 → 15/07)

### Semana 1 (15-21/06) — Análises empíricas críticas
- **D1-D2**: BLOCO A.1 (tercis polarização por leg) + A.2 (quebra Fev/2021)
- **D3-D4**: BLOCO A.3 (variável `d_centrao` + heterogeneidade)
- **D5-D7**: BLOCO C.1 (download orçamento federal) + BLOCO C.3 (download RP-9 XLSX)

### Semana 2 (22-28/06) — Análises empíricas secundárias + descritivas
- **D8-D9**: BLOCO A.4 (alinhamento com Centrão) + A.5 (tratamento quadrático)
- **D10-D11**: BLOCO A.7 (descritivas com C.1) + A.8 (tabela de testes)
- **D12-D13**: BLOCO A.6 (dois turnos PECs)
- **D14**: BLOCO A.9 (weak vs strong como mediador) — apenas se sobrar tempo

### Semana 3 (29/06-05/07) — Reescrita
- **D15-D16**: BLOCO B.1 (página 10 + literatura) + B.3 (justificar controles)
- **D17-D19**: BLOCO B.4 (interpretação backfire) + B.2 (mover texto→tabelas)
- **D20-D21**: BLOCO C.2 (parágrafo Orçamento Impositivo) + D.1-D.4 (respostas)

### Semana 4 (06-15/07) — Polish e submissão
- **D22-D23**: Atualizar abstract, introdução, conclusão com novos achados
- **D24-D25**: Atualizar `METHODOLOGY_LOG.md` + criar `response_to_committee.tex`
- **D26-D27**: Recompilar paper.pdf; cross-check de números entre tabelas/texto
- **D28-D29**: Atualizar qualify.pdf (Essay 3); revisão final
- **D30**: Submissão Public Choice

---

## Checklist de qualidade pré-submissão

- [ ] Todos os números no abstract batem com Tabela 1.
- [ ] Todas as tabelas têm interpretação em pp + R$M.
- [ ] Sargan, AR, RV, KP em uma tabela única consolidada.
- [ ] Tercis de polarização por legislatura (decisão Bernardo).
- [ ] Quebra Lira documentada com 3 sub-períodos.
- [ ] Variável `d_centrao` com fonte/lista de partidos no apêndice.
- [ ] Marco legal Orçamento Impositivo discutido em §2.
- [ ] Descritivas de % orçamento federal em §3.2.
- [ ] Interpretação backfire reformulada (não "deputado em apuros").
- [ ] Limitações claras: RP-9 imputação vs dados oficiais parciais.
- [ ] Response document para Daniel + Bernardo + Rafael antes de submeter.

---

## Notas sobre alocação de tempo

Items P1 = ~60% do tempo. P2 = ~30%. P3 = ~10%.

Risco maior: **A.3 (`d_centrao`)** — depende de definição defensável da lista de partidos. Caso falhe, A.4 (outcome alternativo) cai junto. Mitigation: usar 2 definições (estrita: PP+PL+Republicanos+União; ampla: +PSD+MDB+Solidariedade) e reportar ambas.

Risco menor: **C.3 (RP-9 XLSX)** — dados existem mas mapping incompleto. Fallback: manter cenários x2/x3 imputados e citar limitação.
