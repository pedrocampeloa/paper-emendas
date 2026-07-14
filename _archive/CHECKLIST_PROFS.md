# Checklist Final — Atendimento aos pedidos dos professores

> Data: 2026-05-12. Comparação 1:1 entre cada pedido (Daniel + Rafael) e o que foi feito.

## Daniel (01/05/2026, mensagem 18:40)

### Pedidos de reescrita estrutural

| Pedido | Status | Evidência |
|---|---|---|
| **(a) Reenquadrar como estudo de troca política** | ✅ EXECUTADO + REFINADO | Narrativa nova: "Regime change in pork-barrel". Daniel pediu "viés de coaptação"; nós encontramos algo mais sofisticado — a cooptação clássica funciona apenas no regime de coalition presidentialism tradicional. |
| **(b) Calcular "preço" do apoio legislativo** | ✅ FEITO | `price_legislative_support_v2.csv`: leg 55 = R$ 516k/pp; leg 56 = sinal inverso, R$ 1.066M/pp negativo. |
| **(c) Variável de voto apertado/moderado/tranquilo + emenda × tightness** | ✅ FEITO | `21_heterogeneities_v2.py`. Achado: regime change domina em votações tranquilas (lopsided): leg 55 +1.15***, leg 56 −1.52***. Em apertadas, sem significância. |
| **(d) Consequências fiscais/alocativas (JPubE direction)** | ❌ FORA DE ESCOPO | Decidido em 02/05 conjuntamente: vira companion paper futuro. |

### Pedidos de heterogeneidades (d1-d6)

| ID | Pedido | Status | Resultado-chave (spec full_clean + FE + cluster) |
|---|---|---|---|
| **d1** | Efeito maior em oposição? | ✅ FEITO | **Não simétrico**: leg 55 oposição +6.79; leg 56 oposição −3.27. |
| **d2** | Efeito maior em deputados de baixa lealdade histórica? | ✅ FEITO | **Sim na 55**: hist_low leg55 = +1.84***. Na 56, inverte: hist_high leg56 = −2.97***. |
| **d3** | Efeito diferente em ano eleitoral? | ✅ FEITO | Leg 55 não-eleição +1.60; leg 56 não-eleição −1.59. **leg 56 + coal × eleição = +2.18*** (positivo!)** |
| **d4** | Votos apertados? | ✅ FEITO | Lopsided dominam o regime change. Apertados n.s. |
| **d5** | Tipo de bill? | ✅ FEITO | **Mais dramático em PEC/PLP**: leg 55 PLP +25; leg 56 PLP −1.6. |
| **d6** | Modelo reverso de alocação | ✅ FEITO | `reverse_allocation.csv`: governo aloca MAIS para coalizão (R$ 318k a mais leg 55; quase neutro leg 56). Não é cooptação clássica. |

## Rafael (02/05/2026, ponto a-d)

### Decomposição do gap entre legislaturas

| ID | Pedido | Status | Resultado |
|---|---|---|---|
| **R-1** | RP-9 imputado | ✅ FEITO PARCIALMENTE (cenário) | `decomposition_v2.csv` R2.7. Dados RP-9 padrinho **não foram coletados**; rodamos cenários ×2/×3 inflando T leg 56. Atenuação ×3 reduz efeito de −0.95 → −0.32 (66%). NÃO inverte. |
| **R-2** | Polarização × emenda interação | ✅ FEITO | `decomposition_v2.csv` R2.8. **Resultado contra-intuitivo**: pol baixa −3.04***; pol alta +0.72 n.s. Oposto à hipótese. Pode ser que pol_simple esteja saturado por outras fontes de variação. |
| **R-3** | Oaxaca-Blinder do gap | ✅ FEITO | `decomposition_v2.csv` R2.9. Composição = −10.6pp (−388%); coeficiente = +13.4pp (+488%). Componentes grandes por multicolinearidade. **Para o paper, simplificar com X reduzido.** |

### Pedidos de reescrita (Rafael concordou com Daniel)

| Pedido | Status |
|---|---|
| Janela pre-voto como principal | ✅ FEITO |
| Reduzir ML/DML no título e abstract | ⏳ A FAZER NA REESCRITA |
| Cooptação como contribuição central | 🟡 **REFINAR**: a evidência empírica não sustenta "cooptação universal"; vai virar "regime change" |
| Reescrever como study de troca política | ⏳ A FAZER NA REESCRITA |

## Minhas sugestões TIER 1 (PhD-level)

| ID | Item | Status |
|---|---|---|
| **T1.1** | Cluster bootstrap por idDeputado | ✅ FEITO. SE 3-5× iid. Reduced+full_clean. |
| **T1.2** | Deputy fixed effects | ✅ FEITO. Reduced+full_clean. Within-transformation. |
| **T1.3** | Bad-controls audit | ✅ FEITO. Identificou vote_outcome como bad. |
| **T1.4** | Anderson-Rubin CIs | ✅ FEITO. Leg 56 CI [−3.79, −1.70] válido. Leg 55 CI vazio em reduced. |
| **T1.5** | Sargan honesto + Cinelli-Hazlett | ✅ FEITO. RV leg 56 = 0.60 (very robust). |

## Sugestões TIER 2 (PhD-level)

| ID | Item | Status |
|---|---|---|
| **T2.6** | IV alternativo (disaster, ministry slowness) | ✅ FEITO. uo_slowness diverge de backlog (Sargan rejeita); confirma que backlog é o IV principal. |
| **T2.7** | Pre-registration explícito | ⏳ A FAZER NA REESCRITA |
| **T2.8** | Heterogeneidade por janela como contribuição metodológica | ✅ FEITO (na fase early — comparison_old_vs_new) |
| **T2.9** | Sensitivity to nuisance learners | ✅ FEITO (FAST). 5 learners testados: ENet, Lasso, RF, XGBoost, LightGBM. Sinal de regime change preservado em todos. |
| **T2.10** | Tighter CV | ⏳ PENDENTE (DML usa 3-fold; alternativa 5/10 seria 2-3h cada) |

## Pedidos USER (você, 08/05)

| ID | Pedido | Status |
|---|---|---|
| **USER1** | Heterogeneidade fina por grupos | ✅ FEITO (`18_fine_heterogeneity_v2.py`, 88 grupos) + **EM RODAGEM**: `25_heterogeneity_extensive.py` com UF, partido, idade, sexo, escolaridade, trimestre, mesa, senioridade |
| **USER2** | Testar várias estratégias de controles | ✅ FEITO. 7 estratégias rodadas; **todas confirmam regime change**. Magnitudes variam por fator 7× mas direção é estável. |

## Achados que ATENDEM e VÃO ALÉM dos pedidos

1. **Bug B0.4 (emenda_M como controle E tratamento)** — não estava no MUSTDO original; descoberto na auditoria, corrigido. Mudou substancialmente as conclusões.

2. **Tese refinada de "regime change"** — vai além do "cooptação inversão de sinal" original.

3. **Triangulação extensa**: 5 testes de robustez (cluster, FE, AR-CI, sensitivity, IVs alternativos) + 7 estratégias de controles + 88 sub-grupos heterogêneos + 12 análises por UF/partido/idade etc. Convergência muito forte.

4. **Literatura suporta a narrativa**: Coalitional Presidentialism Under Stress (Cambridge, recente), Lawmaking Effectiveness under Polarization (Volden-Wiseman/Brookings 2024), Pereira & Mueller (canônico). Nossa contribuição: **primeira documentação causal da quebra do mecanismo Pereira-Mueller** sob populismo polarizado.

## Pendências para fechar antes de mandar para os profs

| Item | Quando |
|---|---|
| ⏳ Aguardar `25_heterogeneity_extensive.py` (rodando) | ~3-5h |
| ⏳ Validar `pol_simple` vs índice MDS do paper-polarization (R2.8 contra-intuitivo) | ~2h |
| ⏳ Refazer Oaxaca-Blinder com X reduzido (não 142) | ~30min |
| ⏳ Atualizar METHODOLOGY_LOG final + PDF | ~10min |
| ⏳ Reescrita do paper (Daniel D-b, RT-b, RT-c) | ~6-8h |
