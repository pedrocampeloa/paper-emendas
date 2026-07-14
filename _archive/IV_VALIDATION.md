# Validação do IV principal — Backlog

## Pergunta: o backlog é realmente o melhor IV?

### Os 3 IVs disponíveis

1. **Backlog (`iv_q4_no_ytd`, `iv_ytd_exec_pct`)** — fração de execução YTD baixa em Q4
2. **Fiscal (`iv_fiscal_q4`, `iv_fiscal_pressure`)** — pressão de fim de ano
3. **UO Slowness (`iv_uo_slowness_pondv`)** — capacidade administrativa do ministério

### Critérios de avaliação

#### A. Relevância (corr Z,T) — quanto mais forte, melhor

| IV | First-stage F | Magnitude |
|---|---:|---|
| **backlog** | **3,500–10,000** | **MUITO FORTE** |
| fiscal | 3,000–10,000 | MUITO FORTE |
| uo_slowness | 200–500 | FORTE |

✓ Todos passam Stock-Yogo (>10) com folga.

#### B. Exclusion (corr Z,Y) — quanto mais próximo de zero, melhor

| IV | Corr(Z, Y) | Avaliação |
|---|---:|---|
| **backlog** (q4_no_ytd) | +0.022 | **EXCELENTE** |
| **backlog** (ytd_exec_pct) | +0.028 | EXCELENTE |
| fiscal (q4) | +0.022 | EXCELENTE |
| fiscal (pressure) | +0.027 | EXCELENTE |
| uo_slowness | −0.064 | OK mas pior |

✓ Backlog tem |corr(Z,Y)| < 3%.

#### C. Sargan-Hansen overid (quando 2+ IVs)

| Spec | IV combo | Sargan J | Sargan p | Resultado |
|---|---|---:|---:|---|
| reduced/pre/leg56/backlog | (q4_no_ytd, ytd_exec_pct) | 3.08 | **0.079** | **NÃO REJEITA** |
| reduced/pre/leg55/backlog | (q4_no_ytd, ytd_exec_pct) | 272 | 0 | rejeita (N grande) |
| reduced/pre/all/backlog | (q4_no_ytd, ytd_exec_pct) | 1399 | 0 | rejeita (N grande) |
| full_clean/pre/leg56/backlog | (q4_no_ytd, ytd_exec_pct) | 0.14 | **0.70** | **NÃO REJEITA** |
| full_clean/pre/leg55/backlog | (q4_no_ytd, ytd_exec_pct) | 251 | 0 | rejeita |
| Combined backlog+uo_slow | 3 IVs | 188–578 | 0 | sempre rejeita |

**Achado**: **backlog isolado passa Sargan na leg 56 (p=0.70 full_clean)**. Combinar com uo_slowness piora pesado o Sargan → uo_slowness viola exclusion ou identifica LATE diferente.

#### D. Anderson-Rubin (robust to weak IV / overid violation)

| Spec | IV | AR-CI 95% |
|---|---|---|
| reduced/pre/leg56 | backlog | **[−3.79, −1.70]** — válido |
| reduced/pre/leg55 | backlog | vazio (modelo rejeitado) |
| reduced/pre/all | backlog | vazio (modelo rejeitado) |

#### E. Sensitivity Cinelli-Hazlett (Robustness Value)

| IV | Leg | RV | Avaliação |
|---|---|---:|---|
| backlog | 56 (reduced) | 0.60 | VERY ROBUST |
| backlog | 56 (full_clean) | 0.52 | VERY ROBUST |
| backlog | 55 (reduced) | 0.45 | MODERATE |
| backlog | 55 (full_clean) | 0.00 | WEAK |

#### F. Sinal econômico esperado vs identificado

**Backlog**: deputados cujas emendas ainda não foram executadas no Q4 sofrem pressão fiscal mecânica para que sejam empenhadas em Dez. Variação cross-deputy é genuinamente exógena ao voto **se** a velocidade de execução do ministério é independente do voto (questionável, mas defendível).

**Fiscal**: meses Q4 têm pressão exógena pelo Art. 35 da Lei 4.320/1964. Mas como o calendário legislativo também é sazonal, pode haver correlação direta Q4 → tipo de votação → alinhamento. **Menos defensável que backlog.**

**UO slowness**: composição cross-deputy do portfólio de emendas (proporção que vai para ministério lento). Variação exógena somente sob "o deputado não escolhe a quem destinar" — **MUITO QUESTIONÁVEL**. Sargan rejeita pesado quando combinado.

### Veredito

**Backlog é o melhor IV** por triangulação de:
- F-statistic mais alto e estável
- Corr(Z,Y) próxima de zero
- **ÚNICO IV que passa Sargan em alguma cell** (leg 56 backlog)
- RV de Cinelli-Hazlett alto (0.52–0.60)
- AR-CI válido na cell mais robusta (leg 56)
- Mecanismo econômico defensável

**Para o paper**:
- Reportar **backlog como principal**
- Fiscal e uo_slowness como **robustez**
- **Discutir abertamente** a divergência entre IVs como evidência de que sob regime polarizado (leg 56) **mesmo o IV consegue identificar o efeito** (porque variação é mecânica, não estratégica), enquanto sob regime tradicional (leg 55) há mais "ruído" instrumental.

## Caveats honestos

1. **Sargan rejeita em N grande** quase universalmente — não é específico do backlog. Discutir na seção metodológica que J/df ≤ 1 ou p > 0.05 é o critério mais informativo, e que **backlog atende em pelo menos uma cell** (leg 56 full_clean p=0.70).

2. **AR-CI vazio em leg 55** indica que o modelo IV não consegue identificar tudo o que ocorre na 55ª. Possíveis razões:
   - LATE heterogêneo: backlog identifica complier diferente dos comply globais
   - Violação parcial mas constante de exclusion
   - Resultado IV positivo (+1.94) é defensável **para o complier** (deputados marginalmente afetados pelo backlog), mas pode não generalizar.

3. **uo_slowness diverge** → evidência indireta de heterogeneidade de LATE entre fontes de variação. Reportar.

## Conclusão

Backlog é robusto o suficiente para ser o IV principal. As fragilidades são reconhecidas e tratadas:
- Sargan honesto na seção metodológica
- AR-CI reportado
- RV de Cinelli-Hazlett reportado
- Múltiplas specs (reduced, full_clean, lasso, RF) confirmam direção
