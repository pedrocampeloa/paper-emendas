# -*- coding: utf-8 -*-
"""
_config.py — paper-emendas configuration
========================================
Single source of truth for paths, control sets, and modeling knobs.

Two control specifications:
  1. CONTROLS_REDUCED (~30 vars) — defensible, transparent. MAIN spec.
  2. CONTROLS_FULL (~191 vars)   — replicates legacy paper. Appendix.

Per Public Choice feedback (May 2026): main spec uses 60d pre-vote window
(panel_emendas_pre.csv); ±45d sym + 60d post-vote are robustness/placebo.
"""
from __future__ import annotations

import os
from pathlib import Path

# ============================================================================
# Paths
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "dados"
INTERIM = DATA / "interim"
PANEL = INTERIM / "panel"               # NEW data_pipeline outputs
LEGACY = INTERIM                          # OLD features_v2.csv / iv_features
RESULTS = ROOT / "paper-emendas" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Modeling knobs
# ============================================================================

TARGET = "alinhamento"
TREATMENT = "emenda_M"   # R$ MILLIONS — derived in load_modeling_panel from emenda_valor / 1e6
                          # Use this so that 1 unit = R$1M and pp_per_unit
                          # is directly interpretable as "pp change per R$1M".

# Three windows
WINDOW_FILES = {
    "pre": PANEL / "panel_emendas_pre.csv",     # MAIN
    "sym": PANEL / "panel_emendas_sym.csv",      # robustez
    "post": PANEL / "panel_emendas_post.csv",    # placebo
}
MAIN_WINDOW = "pre"

LEGISLATURAS = (55, 56)   # 57 excluded: emenda data only to 2024


# DML hyper-parameters
N_FOLDS = 3
N_REPS = 3

# IV sets
IV_SETS = {
    "fiscal":  ["iv_fiscal_q4", "iv_fiscal_pressure"],
    "backlog": ["iv_q4_no_ytd", "iv_ytd_exec_pct"],
}


# ============================================================================
# Control specifications
# ============================================================================

# Reduced (~30 vars) — main paper spec.
# Categories: party FE (one-hot via siglaPartido), UF FE (via d_reg_*),
# bill type, bill theme top-10, mesa diretora, profession bins, election years.
CONTROLS_REDUCED = [
    # Bill type
    "d_tipoVotacao_PEC", "d_tipoVotacao_MPV", "d_tipoVotacao_PLP",
    "d_tipoVotacao_PL", "d_tipoVotacao_MSC",
    # Bill themes (top-10 by frequency)
    "d_tema_AP",   # Administração Pública
    "d_tema_FPO",  # Finanças Públicas e Orçamento
    "d_tema_SAU",  # Saúde
    "d_tema_EDU",  # Educação
    "d_tema_DS",   # Defesa e Segurança
    "d_tema_TE",   # Trabalho e Emprego
    "d_tema_PAS",  # Previdência e Assistência Social
    "d_tema_ECO",  # Economia
    "d_tema_DPPP", # Direito Penal e Processual Penal
    "d_tema_DHM",  # Direitos Humanos e Minorias
    # Author origin
    "tipoAutor_Deputado(a)", "tipoAutor_Senador(a)",
    # Author state == deputy state
    "d_uf_autor",
    # Region of deputy
    "d_reg_N", "d_reg_NE", "d_reg_SE", "d_reg_S", "d_reg_CO",
    # Demographics
    "idade", "d_homem", "indice_escolaridade",
    # Political experience
    "n_legis", "n_part",
    # Party size
    "tamanho_partido",
    # Election year dummies (added at runtime)
    "d_elec_federal", "d_elec_municipal",
    # Coalition status (added at runtime from coalizao_partido_data)
    "d_oposicao",
]


# Full (~191 vars) — appendix replication of legacy paper.
# Built dynamically: take all numeric cols from panel_features that are
# not IDs / treatment / outcome / leakage / IVs.

ID_COLS = [
    "idDeputado", "dep_id", "nome", "siglaUf", "idPartido", "siglaPartido",
    "data", "y", "idLegislatura", "idProposicao", "idVotacao", "voto",
]

LEAKAGE_VARS = [
    # Same as in old model_unified.py — must NEVER be controls
    "pct_seg_ori_gov", "pct_traiu_ori_gov",
    "pct_seg_ori_part", "pct_traiu_ori_part",
    "pct_seg_ori_mai", "pct_traiu_ori_mai",
    "pct_seg_ori_min", "pct_traiu_ori_min",
    "pct_seg_ori_op", "pct_traiu_ori_op",
    "pct_seg_ori_bancada", "pct_traiu_ori_bancada",
    "pct_votSim", "pct_votNao", "pct_votSim_oriNao",
]

ALL_TREATMENT_VARS = [
    # Legacy raw names from old pipeline
    "emenda_valor", "emenda_pct", "emenda_veloc", "emenda_conc",
    # New pipeline names (b06_build_emendas_panel.py output)
    "emenda_M", "log1p_emenda", "n_empenhos",
    # Treatment-derived variables (post-treatment, must NEVER be control)
    "emenda_M_post",
]


def get_full_controls(df) -> list:
    """Return all numeric cols from df that pass the legacy filters."""
    import numpy as np
    iv_cols = [c for c in df.columns if c.startswith("iv_")]
    forbidden = set(ID_COLS + ALL_TREATMENT_VARS + [TARGET]
                      + LEAKAGE_VARS + iv_cols)
    out = []
    for c in df.columns:
        if c in forbidden:
            continue
        if df[c].dtype not in (np.float64, np.int64, float, int):
            continue
        if df[c].notna().mean() <= 0.5:
            continue
        if df[c].nunique() <= 1:
            continue
        out.append(c)
    return out


# ============================================================================
# Election years (used by build_election_dummies in scripts)
# ============================================================================

FEDERAL_ELECTIONS = {2018, 2022}
MUNICIPAL_ELECTIONS = {2016, 2020}
