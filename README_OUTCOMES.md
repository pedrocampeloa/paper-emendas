# README — Construção dos três outcomes do paper

> Arquivo de referência para auditar como cada $y$ é construído no código.
> Última revisão: 2026-06-24.

O paper trabalha com **três outcomes binários** por (deputado, votação):

| Outcome | Significado | Onde é construído |
|---|---|---|
| `alinhamento` (= **y_gov**) | Voto bate com orientação formal do **governo federal** | `data_pipeline/builders/b04_build_panel_base.py` |
| `y_pres_camara_orient` (= **y_pres**) | Voto bate com orientação formal do **partido do presidente da Câmara** | `paper-emendas/source/54_build_y_pres_camara_orient.py` |
| `y_centrao_orient` (= **y_centrao**) | Voto bate com a **maioria das orientações** dos 9 partidos do Centrão | `paper-emendas/source/51_build_y_centrao_orient.py` |

Todas as três variáveis dependem da **orientação formal** publicada pelo partido/bloco **antes da votação**. Nenhuma usa o voto realizado (ex-post), o que evita o problema de endogeneidade que existiria se medíssemos "alinhamento com a maioria do bloco" usando a maioria *votada* (o próprio voto $i$ contribui para a maioria).

---

## Dados-fonte comuns a todos os três outcomes

Todos partem de duas tabelas brutas da API da Câmara dos Deputados:

1. **`votos_individuais.csv`** — uma linha por (deputado × votação) com o voto registrado (`Sim`, `Não`, `Obstrução`, `Abstenção`, `Artigo 17`).
2. **`orientacoes.csv`** — uma linha por (votação × bloco) com a orientação que o bloco anunciou antes da votação. Bancadas incluem: **`Governo`**, partidos individuais (`PP`, `PT`, `PL`, ...), e blocos compostos.

A orientação assume cinco valores: `Sim`, `Não`, `Obstrução`, `Abstenção`, `Liberado`. Quando o valor é `Liberado` (voto livre) ou ausente, a observação é **descartada** porque não há referência contra a qual medir alinhamento.

---

## 1. y_gov — alinhamento com o Executivo (`alinhamento`)

**Arquivo:** [`data_pipeline/builders/b04_build_panel_base.py`](data_pipeline/builders/b04_build_panel_base.py), função `compute_alignment` (linha 62).

**Lógica:**

```python
# Para cada votação, pegar a orientação do bloco "Governo" do orientacoes.csv
is_gov = orient["siglaBancada"].astype(str).str.upper().str.startswith("GOV")
gov_ori_df = (orient[is_gov]
                .drop_duplicates("idVotacao", keep="first")
                [["idVotacao", "orientacao"]])
gov_ori = gov_ori_df.set_index("idVotacao")["orientacao"]

# Marcar 1 quando o voto bate exatamente com a orientação
sim_match = (df["ori_gov"] == "Sim")        & (df["voto"] == "Sim")
nao_match = (df["ori_gov"] == "Não")        & (df["voto"] == "Não")
obs_match = (df["ori_gov"] == "Obstrução")  & (df["voto"].isin(["Obstrução", "Artigo 17"]))
abs_match = (df["ori_gov"] == "Abstenção")  & (df["voto"] == "Abstenção")

df["alinhamento"] = 0
df.loc[sim_match | nao_match | obs_match | abs_match, "alinhamento"] = 1
```

**Filtros aplicados:**

| Filtro | Efeito |
|---|---|
| `voto ∈ {Sim, Não, Obstrução, Abstenção, Artigo 17}` | Descarta `Branco`, `Liberado`, abstenções não-canônicas |
| `ori_gov ∈ {Sim, Não, Obstrução, Abstenção}` | Descarta votações com `Liberado` ou sem orientação do governo |
| `idLegislatura ∈ {55, 56}` (no carregamento do painel) | Restringe ao escopo do paper |

**Regra de pareamento:** voto e orientação têm que casar **exatamente**, com uma exceção:

- Quando o governo orienta `Obstrução`, o deputado é considerado alinhado tanto votando `Obstrução` quanto votando `Artigo 17` (que é a "obstrução discreta" — registrar presença sem votar). Essa equivalência é convencional na literatura institucional brasileira.

**Output salvo:**
`dados/interim/panel/panel_features.csv`, coluna `alinhamento` (0 ou 1).

**Validação no painel final** (após filtros para Leg 55 + 56):
- $N = 869{,}902$ observações
- $\bar{y}_{\mathrm{gov}} = 0{,}74$

---

## 2. y_pres — alinhamento com o partido do presidente da Câmara

**Arquivo:** [`paper-emendas/source/54_build_y_pres_camara_orient.py`](paper-emendas/source/54_build_y_pres_camara_orient.py).

**Mapeamento temporal do presidente da Câmara → partido:**

```python
def get_partido_presidente(data: pd.Timestamp) -> str:
    if data < pd.Timestamp("2016-07-14"):
        return "PMDB"   # Cunha (fev/2015 a jul/2016)
    if data < pd.Timestamp("2021-02-01"):
        return "DEM"    # Maia (jul/2016 a jan/2021)
    return "PP"         # Lira (fev/2021 em diante)
```

**Como a orientação do partido entra:**

O `panel_features.csv` já carrega, para cada (deputado, votação), 5 dummies que codificam a orientação do **partido do próprio deputado** (uma linha por deputado × votação):

```
d_ori_part_sim, d_ori_part_nao, d_ori_part_obstrucao,
d_ori_part_liberado, d_ori_part_abstencao
```

O construtor recupera a orientação do **partido do presidente** restringindo o painel aos deputados desse partido (que carregam exatamente essa orientação no `d_ori_part_*`), pega o primeiro registro por (votação, partido_presidente), e depois propaga para todos os deputados:

```python
# Restringir ao subconjunto de deputados do partido do presidente da Câmara
presidentes = pf[pf["partido_norm"] == pf["partido_presidente"]].copy()

# Decodificar para string ("Sim", "Não", ...)
def get_ori_str(row):
    if row["d_ori_part_sim"] == 1: return "Sim"
    if row["d_ori_part_nao"] == 1: return "Não"
    if row["d_ori_part_obstrucao"] == 1: return "Obstrução"
    if row["d_ori_part_liberado"] == 1: return "Liberado"
    if row["d_ori_part_abstencao"] == 1: return "Abstenção"
    return None

# Mapa (votação, partido_pres) → orientação
ori_map = (presidentes
           .groupby(["idVotacao", "partido_presidente"])["ori_partido_str"]
           .first().reset_index())

# Voto bate com orientação?
out["y_pres_camara_orient"] = (out["voto"] == out["ori_pres_camara"]).astype(int)

# Descarta Liberado / Abstenção / NaN
invalid = (out["ori_pres_camara"].isin(["Liberado", "Abstenção"])
           | out["ori_pres_camara"].isna())
out.loc[invalid, "y_pres_camara_orient"] = np.nan
```

**Observações importantes:**

1. A orientação é **ex-ante**: vem do registro formal do partido na própria sessão da votação, antes de cada deputado votar individualmente. Não depende do voto realizado.
2. **PMDB-Cunha não entra no estudo**: a orientação formal de PMDB para o subset 2015–jul/2016 cobre poucas roll-calls. O paper apresenta apenas Maia (DEM) e Lira (PP).
3. Quando o partido do presidente da Câmara orientou `Liberado` ou `Abstenção`, a observação é descartada (`y_pres = NaN`).

**Cobertura no painel final**:
- DEM (Maia): cobertura ~95% das votações sob a sua presidência
- PP (Lira): cobertura ~66% das votações sob a sua presidência

**Output salvo:**
`dados/interim/panel/panel_y_pres_camara_orient.csv`, colunas:
- `idDeputado`, `idVotacao`
- `partido_presidente` (PMDB / DEM / PP)
- `ori_pres_camara` (a orientação anunciada por aquele partido)
- `y_pres_camara_orient` (0, 1, ou NaN)

---

## 3. y_centrao — alinhamento com a maioria das orientações do Centrão

**Arquivo:** [`paper-emendas/source/51_build_y_centrao_orient.py`](paper-emendas/source/51_build_y_centrao_orient.py).

> ⚠️ **Importante:** existe uma versão antiga, ex-post (voto majoritário do bloco), que é incorreta por endogeneidade — o próprio voto do deputado contribui para a maioria votada, e o pork pode afetar tanto o voto individual quanto a posição do bloco. A versão correta usada no paper é **ex-ante**, baseada nas orientações registradas pelos 9 partidos individualmente.

**Lista do Centrão:**

```python
CENTRAO_PARTIES = {
    "PP", "PL", "REPUBLICANOS", "SOLIDARIEDADE", "UNIAO",
    "PTB", "AVANTE", "PSD", "MDB"
}
```

Esta é a categorização padrão da literatura comparativa brasileira ([Power 2010](https://doi.org/10.1080/13510347.2010.501678) e atualizações).

**Lógica:**

```python
# Para cada (partido_centrao, votacao), pegar a orientação registrada
cen = pf[pf["d_centrao"] == 1].copy()
ori_centrao = (cen.groupby(["idVotacao", "partido_norm"])
                  .agg({"d_ori_part_sim": "first",
                        "d_ori_part_nao": "first",
                        "d_ori_part_obstrucao": "first",
                        "d_ori_part_liberado": "first",
                        "d_ori_part_abstencao": "first"})
                  .reset_index())

# Contar quantos dos 9 partidos orientaram cada direção em cada votação
votacao_summary = (ori_centrao.groupby("idVotacao")
                     .agg(n_partidos=("partido_norm", "count"),
                          n_sim=("d_ori_part_sim", "sum"),
                          n_nao=("d_ori_part_nao", "sum"),
                          n_obstrucao=("d_ori_part_obstrucao", "sum"),
                          ...)
                     .reset_index())

# Pegar a orientação majoritária; empate → NaN
def consolida(row):
    sim, nao, obs = row["n_sim"], row["n_nao"], row["n_obstrucao"]
    max_count = max(sim, nao, obs)
    if max_count == 0:
        return np.nan
    equals = (sim == max_count) + (nao == max_count) + (obs == max_count)
    if equals > 1:
        return np.nan          # empate, descartar
    if sim == max_count: return "Sim"
    if nao == max_count: return "Não"
    return "Obstrução"

# y = 1 se voto do deputado bate com a orientação majoritária do bloco
out["y_centrao_orient"] = (out["voto"] == out["orientacao_centrao"]).astype(int)
out.loc[out["orientacao_centrao"].isna(), "y_centrao_orient"] = np.nan
```

**Pontos-chave:**

1. Cada um dos 9 partidos do Centrão emite uma orientação por votação. A orientação do bloco é a **maioria simples** entre {`Sim`, `Não`, `Obstrução`}.
2. **`Liberado` e `Abstenção` não entram na contagem** (são tratados como ausência de orientação substantiva).
3. Quando há empate entre `Sim` / `Não` / `Obstrução` (ex: 3-3-2), a votação é descartada (`y_centrao = NaN`).

**Output salvo:**
`dados/interim/panel/panel_y_centrao_orient.csv`, colunas:
- `idDeputado`, `idVotacao`
- `orientacao_centrao` (a maioria consolidada)
- `y_centrao_orient` (0, 1, ou NaN)

---

## ⚠️ Inconsistência conhecida: o Causal Forest IV (Apêndice A.9)

O script [`paper-emendas/source/90_causal_forest_iv.py`](paper-emendas/source/90_causal_forest_iv.py) constrói **internamente** uma versão simplificada do `y_centrao` para a robustez não-paramétrica, e essa versão **NÃO é a mesma usada nas tabelas principais**.

```python
# 90_causal_forest_iv.py (versão ex-post, usada APENAS no apêndice de robustez)
df["voto_num"] = df["voto"].map({"Sim": 1, "Não": -1}).fillna(0)
centrao_vote = (df[df["is_centrao"] == 1]
                .groupby("idVotacao")["voto_num"]
                .apply(lambda s: 1 if s.mean() > 0 else (-1 if s.mean() < 0 else 0)))
df["y_centrao"] = (df["voto_num"] == df["centrao_major_vote"]).astype(int)
```

Essa é a versão **ex-post (voto majoritário)**, que tem o problema de endogeneidade discutido acima. Como o forest no apêndice é apenas uma checagem secundária (e os resultados que reportamos são apenas para o outcome `gov`, não `centrao`), a inconsistência não afeta nenhum número que apareça no paper. Mas vale corrigir antes de uma submissão final: substituir a função `attach_centrao` no script 90 por uma leitura direta de `panel_y_centrao_orient.csv`.

---

## Como auditar os números do paper

Para cada $y$, o painel final é montado em `paper-emendas/source/_utils.py::load_modeling_panel`, que faz inner-join entre:

1. `panel_features.csv` (carrega `alinhamento` = y_gov)
2. `panel_emendas_pre.csv` (carrega `emenda_valor`)
3. `iv_features.csv` (carrega instrumentos)

Para os outcomes adicionais, o painel é então merged com:
- `panel_y_pres_camara_orient.csv` → adiciona `y_pres_camara_orient`
- `panel_y_centrao_orient.csv` → adiciona `y_centrao_orient`

**Validação cruzada rápida (Python):**

```python
import pandas as pd
PANEL = "dados/interim/panel/"

# 1. y_gov direto do painel base
pf = pd.read_csv(PANEL + "panel_features.csv", sep=";", usecols=["idDeputado", "idVotacao", "alinhamento"])
print("y_gov mean:", pf["alinhamento"].mean())

# 2. y_pres
yp = pd.read_csv(PANEL + "panel_y_pres_camara_orient.csv", sep=";")
print("y_pres distribution by sub-period:")
print(yp.groupby("partido_presidente")["y_pres_camara_orient"]
      .agg(["count", "mean"]))

# 3. y_centrao (versão ex-ante correta)
yc = pd.read_csv(PANEL + "panel_y_centrao_orient.csv", sep=";")
print("y_centrao mean:", yc["y_centrao_orient"].mean())
print("y_centrao coverage:", yc["y_centrao_orient"].notna().mean())
```

**Cross-tabela entre y_gov e y_centrao_orient:**
Construída no fim do script `51_build_y_centrao_orient.py` — uma sanity check útil para verificar quantas votações têm orientação de governo *e* de centrão diferentes (que é o que dá identificação ao Centrão como outcome alternativo).

---

## Resumo em uma frase cada

- **y_gov:** voto do deputado $=$ orientação do bloco "Governo" na mesma votação.
- **y_pres:** voto do deputado $=$ orientação formal do partido do presidente da Câmara na mesma votação (PMDB→DEM→PP por calendário).
- **y_centrao:** voto do deputado $=$ orientação majoritária (sim/não/obstrução) entre os 9 partidos do Centrão na mesma votação.

Todos são **ex-ante**: dependem apenas das orientações anunciadas pelos blocos/partidos antes da votação, não dos votos realizados.
