# -*- coding: utf-8 -*-
"""
27_hierarchical_breakdown.py — Quebra hierárquica recursiva por blocos
=========================================================================
Pergunta: dado que o pooled e cada leg dão sinais diferentes, **onde
exatamente** o sinal é positivo, negativo, nulo? Mapear hierarquicamente.

Estrutura de árvore:

  ROOT (pooled)
    ├── leg 55
    │   ├── oposição
    │   │   ├── não-eleição
    │   │   │   ├── PEC
    │   │   │   ├── MPV
    │   │   │   └── PL
    │   │   └── eleição
    │   ├── coalizão
    │   │   └── ...
    │   └── independente
    └── leg 56
        └── ...

Para cada nó, roda PLIV-bl + FE + cluster. Identifica nós-folha
onde o efeito é homogêneo. Output:
  results/hierarchical_breakdown.csv

Output formatado tipo árvore + tabela para o paper.
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as C
import _utils_v2 as U2


# Hierarquia: cada nível é uma dimensão de split
HIERARCHY = [
    # (label, filter_fn, key)
    ("leg", "idLegislatura"),       # 55, 56
    ("status", "_status"),           # opos, coal, indep
    ("election", "d_elec_federal"),  # 0, 1
    ("tipo", "_tipo"),                # PEC, MPV, PLP, PL
]


def build_split_keys(df):
    """Adiciona colunas auxiliares para split."""
    df = df.copy()
    # _status
    df["_status"] = "indep"
    df.loc[df["d_oposicao"] == 1, "_status"] = "opos"
    df.loc[df["d_coalizao"] == 1, "_status"] = "coal"
    # _tipo (categórica baseada em d_tipoVotacao_*)
    df["_tipo"] = "outros"
    for t in ("PEC", "MPV", "PLP", "PL", "MSC"):
        col = f"d_tipoVotacao_{t}"
        if col in df.columns:
            df.loc[df[col] == 1, "_tipo"] = t
    return df


def run_node(df, ctrl, label, log, n_reps=1, min_n=4000, min_clusters=30):
    """Roda um nó da árvore; retorna dict ou None."""
    if len(df) < min_n:
        return {"group": label, "model": "skip_small_n",
                  "n_obs": len(df), "n_clusters": df["idDeputado"].nunique()}
    if df["idDeputado"].nunique() < min_clusters:
        return {"group": label, "model": "skip_few_clusters",
                  "n_obs": len(df), "n_clusters": df["idDeputado"].nunique()}
    try:
        t0 = time.time()
        r = U2.run_pliv_main(df, controls=ctrl, n_reps=n_reps)
        if r:
            r["group"] = label
            log.info("  %s (%ds): pp=%+.3f%s n=%d c=%d",
                     label, int(time.time()-t0), r["pp_per_unit"],
                     r["stars"], r["n_obs"], r["n_clusters"])
        return r
    except Exception as e:
        log.error("  %s failed: %s", label, e)
        return None


def recurse(df, ctrl, depth, max_depth, path, log, rows):
    """Recursão pela hierarquia."""
    label = "_".join(path) if path else "root"
    r = run_node(df, ctrl, label, log)
    if r: rows.append(r)
    if depth >= max_depth: return

    # Próximo nível
    next_dim_label, next_col = HIERARCHY[depth]
    if next_col not in df.columns: return

    values = df[next_col].dropna().unique()
    # Filter only meaningful values
    if next_dim_label == "leg":
        values = sorted([v for v in values if int(v) in (55, 56)])
    elif next_dim_label == "election":
        values = [0, 1]
    elif next_dim_label == "status":
        values = ["opos", "coal", "indep"]
    elif next_dim_label == "tipo":
        values = ["PEC", "MPV", "PLP", "PL"]
    else:
        values = sorted(values)

    for v in values:
        if next_dim_label == "leg":
            sub = df[df[next_col] == int(v)]
            new_path = path + [f"leg{v}"]
        elif next_dim_label == "election":
            sub = df[df[next_col] == v]
            new_path = path + ("eleicao" if v == 1 else "naoeleicao",)
        else:
            sub = df[df[next_col] == v]
            new_path = path + [f"{next_dim_label}_{v}"]
        recurse(sub, ctrl, depth + 1, max_depth, list(new_path), log, rows)


def main():
    logging.basicConfig(level=logging.INFO,
                          format="%(asctime)s [%(levelname)s] %(message)s")
    log = logging.getLogger("27_hier")

    df = U2.load_modeling_panel(window="pre", legis=C.LEGISLATURAS, log=log)
    df = build_split_keys(df)
    df["idLegislatura"] = df["idLegislatura"].astype(int)
    ctrl = U2.get_clean_full_controls(df)
    log.info("Panel: %d | full_clean: %d", len(df), len(ctrl))

    rows = []
    recurse(df, ctrl, 0, max_depth=4, path=[], log=log, rows=rows)

    df_out = pd.DataFrame(rows)
    out = C.RESULTS / "hierarchical_breakdown.csv"
    df_out.to_csv(out, sep=";", index=False)
    log.info("\n✓ saved %s (%d nodes)", out, len(df_out))

    # Print as tree
    log.info("\n=== TREE VIEW ===")
    for _, r in df_out.iterrows():
        depth = r["group"].count("_") if r["group"] != "root" else 0
        indent = "  " * depth
        pp = r.get("pp_per_unit", None)
        stars = r.get("stars", "")
        n_obs = int(r.get("n_obs", 0))
        n_cl = int(r.get("n_clusters", 0))
        if pd.notna(pp):
            log.info("%s%s: pp=%+.3f%s n=%d c=%d",
                     indent, r["group"], pp, stars, n_obs, n_cl)
        else:
            log.info("%s%s: SKIP n=%d c=%d",
                     indent, r["group"], n_obs, n_cl)


if __name__ == "__main__":
    main()
