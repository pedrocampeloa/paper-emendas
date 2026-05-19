# MUSTDO — Paper Emendas (Public Choice)

> Consolidação dos feedbacks de Daniel Cajueiro e Rafael Terra (1–2 maio 2026), mais correções de bugs identificadas em 3-6 maio 2026.
> Alvo de publicação: **Public Choice** (decidido em 02/05/2026 com Daniel + Rafael).
> Janela pré-voto (60d antes) passa a ser **especificação principal**; ±45d vira robustez.
>
> **🔴 ATUALIZAÇÃO 06/05/2026**: após auditoria detalhada e correção de bug crítico
> (`emenda_M` aparecia como controle E tratamento), a narrativa central do paper
> precisa ser reorientada de "cooptação universal" para **"regime change in
> pork-barrel"**. Ver METHODOLOGY_LOG.md para evidências completas.

---

## Princípios da reescrita

1. **Reenquadrar como troca política** (substantivo > metodologia). DML/PLIV continua sendo o método, mas não é a contribuição central.
2. **Contribuição central**: identificar causalmente o "preço político" das emendas e o **viés de coaptação** (governo concentra emendas em deputados menos alinhados, gerando viés OLS para baixo).
3. **Reduzir ML no título / abstract / intro**. O paper é de economia política, não de ML aplicado.
4. **Janela pré-voto = principal**; ±45d e pós-voto = robustez.

---

## BLOCO 0 — Correções de bugs (PRÉ-REQUISITO)

Antes de qualquer extensão, corrigir:

- **B0.1** — Duplicação no `iv_features.csv` (542k linhas duplicadas). Causa raiz: party-switching dentro da legislatura + votações cruzando meia-noite + `df_deps.drop_duplicates` agregando em `(siglaPartido, idLegislatura)` sem garantir unicidade. **Fix**: dedup explícito por `(idDeputado, idVotacao)` antes de qualquer merge.
- **B0.2** — Painel inflado de 761k → 1.288k via merge naive. Confirmado contra raw (`votacoes_votos_raw.csv` leg 56 = 800.095 < 1.021.640 reportado). **Fix**: dedup garantido + asserts de N por legislatura batendo com forecasting + polarization papers.
- **B0.3** — Votações atravessando meia-noite (11 casos) ganham datas diferentes em `features_v2.csv` porque `data` é derivada de `dataHoraVoto` individual. **Fix**: usar `data` canônica de `votacoes_file_.csv` ou `min(dataHoraVoto)` por idVotacao.
- **B0.4** — Erro de unidades: paper reporta "+0.52 pp por R\$1M", mas `theta` no CSV (= 0.523) é prob por R\$1M = +52.3 pp. Cross-check: counterfactual 2.47 pp / T̄ 0.045 R\$M ≈ 55 pp/R\$M, consistente com 52, **NÃO** com 0.52. **Fix**: redefinir reporting nas tabelas + recomputar todas as magnitudes citadas no abstract/intro/conclusion.
- **B0.5** — Sargan-Hansen rejeita p≈0 em todos os specs sobreidentificados; paper omite (Tabela 4 mostra "—"). **Fix**: reportar honestamente; discutir que com N grande Sargan é hipersensível e oferecer testes alternativos (Hausman, sensitivity Cinelli–Hazlett).
- **B0.6** — "130× smaller" no abstract vs "36×" na tabela; real é 38×. **Fix**: número único, consistente.
- **B0.7** — Tabela 1 (descritiva): emenda mean=0.843 não bate com nenhum painel. **Fix**: regerar a partir do painel correto.
- **B0.8** — Tabela 3 (correlações IV): sinais invertidos para 4 dos 4 IVs. **Fix**: regerar.

**Sanity tests obrigatórios** (vão para `tests/`):
- N(painel ±45d, leg 55) ≤ N(forecasting Sim/Não, leg 55) = 283.692
- N(painel ±45d, leg 56) ≤ N(forecasting Sim/Não, leg 56) = 771.263
- duplicates(idDeputado, idVotacao) == 0 em **todos** os artefatos
- min(dataHoraVoto) ≤ data ≤ max(dataHoraVoto) por idVotacao
- counterfactual(theta_std × T̄_std) ≈ Y_obs − Y_cf, dentro de 0.5 pp de tolerância

---

## BLOCO 1 — Reescrita estrutural (Daniel a, b, c — todas)

- **R1.1** — **Reenquadrar título e abstract** como economia política. Tirar "Machine Learning" do título. Sugestão de título: *"Buying Votes with Public Money: Causal Evidence from Brazil's Coalition Presidentialism"* (ou similar). Abstract foca em (i) viés de coaptação, (ii) preço político por voto.
- **R1.2** — **Janela pré-voto (60d antes) = especificação principal**. Mover Tabela `tab:left` (atual robustez) para a posição principal. ±45d simétrico vai para robustez.
- **R1.3** — **Reduzir ênfase em ML/DML**: não tirar, mas mover para subseção metodológica curta. Não usar acrônimos no abstract.
- **R1.4** — **Seção dedicada "Price of Legislative Support"**: calcular R\$ por pp de alinhamento. Daniel cita "R\$1.9M / pp na 55ª e R\$10M / pp na 56ª" como números a alcançar (a partir dos coeficientes).

---

## BLOCO 2 — Heterogeneidades (Daniel d1–d6 + Rafael 1–3)

Cada item gera UMA estimação adicional + UM painel novo na seção de resultados.

### Heterogeneidade por posição partidária (Daniel d1)
- **R2.1** — Interagir `emenda × dummy_oposicao`. Hipótese: efeito maior na oposição (consistente com narrativa de coaptação).
- Definir oposição: deputado cujo partido NÃO está na coalizão do governo na data do voto. Coalizão pode ser inferida a partir de `d_ori_gov_*` consistente ou tabela manual por governo (Temer: PMDB+; Bolsonaro: PSL+Centrão pós-2020).

### Heterogeneidade por alinhamento histórico (Daniel d2)
- **R2.2** — Construir `align_hist_pre = % de votos com governo nos 6 meses anteriores`, **rigorosamente excluindo o voto atual**. Dividir em terços (baixo / médio / alto). Interagir com emenda. Hipótese: efeito maior em baixo/médio.
- Cuidado: precisa garantir que `align_hist_pre` não vaze o outcome → rolling window estritamente anterior.

### Heterogeneidade por ano eleitoral (Daniel d3)
- **R2.3** — Interações `emenda × d_elec_federal` e `emenda × d_elec_municipal`. Já temos as dummies; só faltam as interações.

### Quando o governo precisa de votos (Daniel d4)
- **R2.4** — Margem da votação: `margem = |votosSim − votosNao| / total`. Classificar em apertado / moderado / tranquilo. Interagir.
- Disponível em `votacoes_file_.csv` (colunas `votosSim`, `votosNao`, `votosOutros`).

### Importância da votação (Daniel d5)
- **R2.5** — Interagir com tipo de proposta: `d_PEC`, `d_MPV`, `d_PLP` × emenda. Hipótese: efeito maior em matérias mais importantes (PEC).

### Direção da alocação (Daniel d6)
- **R2.6** — **Modelo reverso**: regredir `emenda` em `align_hist_pre`, dummy_oposicao, dummy_pivô. Não é o resultado principal, mas evidência da história de coaptação.

### Decomposição do gap entre legislaturas (Rafael 1, 2, 3 — IMPORTANTE)

Atualmente §7.2 atribui o gap inteiro (52 pp 55ª vs 10 pp 56ª) ao Orçamento Secreto. Rafael pede abrir em 3 hipóteses:

- **R2.7** (Rafael 1) — **RP-9 imputado**. STF liberou dados pós-2022 das emendas de relator. Imputar RP-9 ao deputado padrinho (via dados liberados) e re-estimar `Y = θ × (emenda + RP9_padrinho) + g(X)`. Predição: θ da 56ª sobe, gap encolhe.
  - **Verificar disponibilidade dos dados de RP-9** (STF 2022). Provavelmente em `dados/raw/emendas/` mas precisa confirmar.
- **R2.8** (Rafael 2) — **Polarização da votação**. Construir índice de polarização por votação: `pol_v = |votos_coalizao_sim − votos_oposicao_sim|` ou `1 − jaccard(coalizao_pattern, oposicao_pattern)`, **excluindo o voto do próprio deputado i**. Estimar interação `emenda × pol_v`. Predição: θ_int < 0 (emenda compra menos quando polarização alta).
- **R2.9** (Rafael 3) — **Decomposição Oaxaca-Blinder do gap**. Variáveis X: ideologia (NOMINATE 1D ou rótulo de coalizão), profissão, base eleitoral (UF), dependência histórica de emendas. Decompor `θ̄_56 − θ̄_55` em "efeito composição" + "efeito coeficiente". Predição: composição explica fração relevante.
  - Cuidado: ideologia precisa de fonte (Cajueiro tem alguma medida? `Zucco2024ideology`?). Senão usar dummy de coalizão como proxy.

---

## BLOCO 3 — Sugestões minhas (PhD-level, não obrigatórias mas valiosas)

- **R3.1** — **Cluster bootstrap por deputado**. Mesmo com painel correto, observações dentro de mesmo deputado são correlacionadas. SE robustos a cluster.
- **R3.2** — **Sensitivity analysis Cinelli-Hazlett** ([sensemakr](https://carloscinelli.com/sensemakr/)) para violação parcial da exclusão restriction. Reviewer cético vai apreciar.
- **R3.3** — **Placebo "voto livre"**: votos onde o governo NÃO orientou. Efeito de emenda deve ser zero. Já temos `d_ori_gov_liberado`.
- **R3.4** — **Reportar IC em pp/R\$M explicitamente** nas tabelas, não em coef padronizado. Magnitude tangível.
- **R3.5** — Após implementar tudo isso, pode valer **escrever paper companion** no JPubE com a parte alocativa (função do gasto, UF, distorção). Ver Rafael final: "daria outro paper".

---

## BLOCO 4 — Coisas para descartar / movido para "fora do escopo"

- **JPubE** (alocação geográfica, distorção) → companion paper futuro. Não implementar agora.
- **Apêndice CMO** (`iv_appendix.tex` mencionado no SPEC mas nunca existiu como arquivo) → manter excluído, mencionar uma linha no apêndice principal. Não vale resgatar.
- **`features_emenda_right` (placebo pós-voto)** → manter como falsificação, mas não inflar com mais análise.

---

## Ordem de execução proposta

```
1. BLOCO 0 (correções) ─ pré-requisito, sem isso nada vale
2. BLOCO 1 (reescrita estrutural) ─ depois de termos os números corrigidos
3. BLOCO 2 R2.1–R2.5 (heterogeneidades simples) ─ usam mesma base
4. BLOCO 2 R2.7–R2.9 (decomposição gap) ─ Rafael, mais elaboradas
5. BLOCO 2 R2.6 (alocação reversa) ─ dispersão pequena, pode ficar para o fim
6. BLOCO 3 (sugestões) ─ se houver tempo
```

Estimativa de horas-DML rodando: ~4h por especificação completa (PLR+PLIV em todas as legs/janelas/IVs). Total: 8–12h de cluster.

---

## O que muda nas conclusões / o que avisar para os professores

### Achados preliminares (20% sample, 1 rep — full run em curso 03/05/2026)

| | Leg 55 | Leg 56 | Pooled |
|---|---|---|---|
| PLR (paper antigo, coef_std×100) | -0.22 pp | +0.52 pp | +0.36 pp |
| **PLR (novo)** | **+0.58 pp*** | **−0.22 pp*** | +0.07 pp |
| PLIV-backlog (paper antigo) | +52.3 pp* | +10.0 pp* | +14.5 pp* |
| **PLIV-backlog (novo)** | **+3.52 pp*** | **−2.96 pp*** | +1.61 pp |

*Valores antigos com asterisco têm interpretação ambígua; provavelmente o paper antigo reportou em pp/100 ou misturou unidades. O novo está em **pp/R\$1M** explícito.

### Mudanças substantivas vs paper antigo

1. **Leg 55**: cooptação ainda confirmada. Sinal qualitativo preserva (PLIV > PLR > 0).
2. **Leg 56**: **inversão de sinal**. Onde paper antigo via +0.10 pp, novo vê **−2.96 pp**. Possíveis explicações:
   - Bug de duplicação no IV antigo inflava sinal positivo
   - RP-9 (Orçamento Secreto) realmente domina e visível emenda agora indica oposição
   - Coalition shift: emenda concentrada em Centrão pós-2020 ocorre paralelamente a outras formas de barganha
   Decomposição R2.7 (RP-9 scenarios x2/x3) **não fecha o gap** completamente: leg 56 permanece negativa mesmo com RP-9 imputado x3.
3. **Magnitudes em pp/R\$M são agora explícitas e interpretáveis**, sem ambiguidade do paper antigo.
4. **Sargan rejeita** em quase todos os specs (consistente com N grande). Vai virar parágrafo de discussão honesto.

### Direção da reescrita

- **História da leg 55 sobrevive** → cooptação positiva, magnitudes maiores.
- **História da leg 56 muda** → narrativa não pode mais ser "efeito atenuado pelo RP-9", precisa ser "efeito invertido sob hipóteses alternativas, com discussão de mecanismos".
- **R2.8 (polarização)** confirmou hipótese de Rafael: efeito da emenda menor quando polarização alta. Vai virar achado central.
- **R2.9 (Oaxaca)**: gap entre legs é dirigido por mudança de coeficientes (perfil estrutural diferente), não composição.
- **Preço político (Public Choice central)**: leg 55 R\$ 486k/pp; leg 56 inverso; pooled R\$ 509k/pp.

### Achado que INVERTE narrativa de cooptação (full sample, 03/05/2026)

R2.1 e R2.2 produziram resultados que **redirecionam a história**:

- **Coalizão**: emenda → **+5.60 pp/R\$M** (positivo forte)
- **Oposição**: emenda → **−2.15 pp/R\$M** (negativo)
- **Deputados com histórico de baixa lealdade**: emenda → **−1.75 pp/R\$M**
- **Deputados loyalists**: emenda → **n.s. (zero)**

A narrativa antiga era: "governo aloca emendas para deputados oposicionistas marginais → IV resgata sinal positivo → naive OLS é negativo por seleção adversa". **Mas o IV positivo, dirigido pela coalizão, sugere que o mecanismo real é REFORÇO DE LEALDADE, não cooptação.**

Implicações:
1. O **viés OLS não é tão grande** quanto o paper antigo sugeriu — porque a maioria do efeito ocorre na coalizão (onde alinhamento já é alto).
2. A narrativa de "preço político" pode ser refinada como "preço de manutenção de lealdade", não "preço de conversão de oposição".
3. **R2.6 (alocação reversa)** vira ainda mais importante: confirmar se governo realmente envia emendas mais para oposição (e o efeito IV é de quem reverte) OU se a alocação é principalmente para coalizão.

**AÇÃO:** Avisar Daniel e Rafael **antes** da reescrita do paper. A narrativa da leg 56 muda completamente, E a narrativa central de cooptação também precisa ser refinada.
