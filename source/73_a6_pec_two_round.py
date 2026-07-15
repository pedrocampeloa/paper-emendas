"""
73_a6_pec_two_round.py
-----------------------
A.6 (Bernardo): votacoes em 2 turnos (PECs).
Identifica pares (1o turno, 2o turno) por mesma proposicao e estima within-PEC:
  Delta_y_{i,2-1} = theta * Delta_T_{i,2-1} + epsilon_i

Hipotese: emenda chegando entre turnos move o alinhamento dentro da mesma PEC,
controlando por todos efeitos fixos (deputado, ideologia, contexto).

Output: results/n3_a6_pec_two_round.csv
"""

import sys, re, logging, warnings
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import _config as _CFG
import _utils as U

warnings.filterwarnings("ignore")

PANEL = Path(_CFG.PANEL)
RESULTS = Path(_CFG.RESULTS)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("a6")


def detect_turn(desc):
    """Detecta turno a partir de descricao: '1o turno', '2o turno', etc."""
    if not isinstance(desc, str): return None
    s = desc.lower()
    if re.search(r"1[oº\.]?\s*turno|primeiro turno", s): return 1
    if re.search(r"2[oº\.]?\s*turno|segundo turno", s): return 2
    return None


def main():
    log.info("A.6: PECs em 2 turnos")
    log.info("[1] Loading votacoes_file_ para idProposicao + descricao")
    vf = pd.read_csv(
        "/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/dados/raw/votacoes/arquivos/votacoes_file_.csv",
        sep=";", low_memory=False, dtype=str,
        usecols=["id", "data", "descricao",
                 "ultimaApresentacaoProposicao_idProposicao"])
    vf = vf.rename(columns={"id": "idVotacao",
                              "ultimaApresentacaoProposicao_idProposicao": "idProposicao"})
    vf["turno"] = vf["descricao"].apply(detect_turn)
    vf["data"] = pd.to_datetime(vf["data"], errors="coerce")
    vf = vf.dropna(subset=["turno", "idProposicao", "data"])
    log.info(f"  {len(vf):,} votacoes com turno detectado")
    log.info(f"  turno dist: {vf['turno'].value_counts().to_dict()}")

    log.info("[2] Identificando pares (1o turno, 2o turno) por idProposicao")
    pairs = (vf.pivot_table(index="idProposicao", columns="turno",
                              values=["idVotacao", "data"], aggfunc="first")
              .dropna())
    pairs.columns = [f"{a}_{int(b)}" for a, b in pairs.columns]
    log.info(f"  {len(pairs)} pares (1o/2o turno) encontrados")
    print(pairs.head())

    if len(pairs) < 5:
        log.error("  Poucas PECs com 2 turnos. Abortando.")
        return

    log.info("[3] Loading painel principal")
    df = U.load_modeling_panel(window="pre", log=log, include_coalizao=True)
    df["idDeputado"] = df["idDeputado"].astype(str)
    df["idVotacao"] = df["idVotacao"].astype(str)

    pairs = pairs.reset_index()
    pairs["idVotacao_1"] = pairs["idVotacao_1"].astype(str)
    pairs["idVotacao_2"] = pairs["idVotacao_2"].astype(str)

    log.info("[4] Construindo painel within-PEC (deputado x PEC)")
    rows = []
    for _, p in pairs.iterrows():
        v1 = df[df["idVotacao"] == p["idVotacao_1"]][["idDeputado", "alinhamento", "emenda_M"]]
        v2 = df[df["idVotacao"] == p["idVotacao_2"]][["idDeputado", "alinhamento", "emenda_M"]]
        if len(v1) == 0 or len(v2) == 0: continue
        m = v1.merge(v2, on="idDeputado", suffixes=("_1", "_2"))
        m["d_align"] = m["alinhamento_2"] - m["alinhamento_1"]
        m["d_T"] = m["emenda_M_2"] - m["emenda_M_1"]
        m["idProposicao"] = p["idProposicao"]
        rows.append(m)

    if not rows:
        log.error("  No merges produziram dados.")
        return

    out = pd.concat(rows, ignore_index=True).dropna(subset=["d_align", "d_T"])
    log.info(f"  {len(out):,} (deputado, PEC) pares no painel within-PEC")
    log.info(f"  d_align mean={out['d_align'].mean():.4f}")
    log.info(f"  d_T mean={out['d_T'].mean():.4f}")
    log.info(f"  d_T std={out['d_T'].std():.4f}")

    log.info("[5] OLS within-PEC: Delta_align ~ Delta_T")
    import statsmodels.formula.api as smf
    model = smf.ols("d_align ~ d_T", data=out).fit(cov_type="cluster",
                                                     cov_kwds={"groups": out["idDeputado"]})
    log.info(f"  beta(d_T) = {model.params['d_T']:+.4f}")
    log.info(f"  se = {model.bse['d_T']:.4f}")
    log.info(f"  p = {model.pvalues['d_T']:.4f}")
    log.info(f"  n = {int(model.nobs)}")
    log.info(f"  R2 = {model.rsquared:.4f}")

    # also: PEC fixed effects
    log.info("[6] OLS within-PEC + PEC fixed effects")
    model_fe = smf.ols("d_align ~ d_T + C(idProposicao)", data=out).fit(
        cov_type="cluster", cov_kwds={"groups": out["idDeputado"]})
    log.info(f"  beta(d_T) FE = {model_fe.params['d_T']:+.4f} se={model_fe.bse['d_T']:.4f} p={model_fe.pvalues['d_T']:.4f}")

    result = pd.DataFrame([
        {
            "model": "OLS no FE",
            "beta_dT": round(float(model.params['d_T']), 6),
            "se": round(float(model.bse['d_T']), 6),
            "ci_lo": round(float(model.conf_int().loc['d_T', 0]), 6),
            "ci_hi": round(float(model.conf_int().loc['d_T', 1]), 6),
            "pval": round(float(model.pvalues['d_T']), 6),
            "n_obs": int(model.nobs),
            "n_pecs": out["idProposicao"].nunique(),
            "r2": round(float(model.rsquared), 4),
        },
        {
            "model": "OLS + PEC FE",
            "beta_dT": round(float(model_fe.params['d_T']), 6),
            "se": round(float(model_fe.bse['d_T']), 6),
            "ci_lo": round(float(model_fe.conf_int().loc['d_T', 0]), 6),
            "ci_hi": round(float(model_fe.conf_int().loc['d_T', 1]), 6),
            "pval": round(float(model_fe.pvalues['d_T']), 6),
            "n_obs": int(model_fe.nobs),
            "n_pecs": out["idProposicao"].nunique(),
            "r2": round(float(model_fe.rsquared), 4),
        },
    ])
    result.to_csv(RESULTS / "n3_a6_pec_two_round.csv", sep=";", index=False)
    log.info(f"  saved {RESULTS / 'n3_a6_pec_two_round.csv'}")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
