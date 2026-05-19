# -*- coding: utf-8 -*-
"""
_sanity.py
==========
Reusable assertion / sanity-check primitives for the paper-emendas pipeline.

Design principle: fail loud. Never paper over a discrepancy. Every script in
the pipeline calls these checks at its boundary and dumps a structured report
to results/sanity_report_<step>.md so the human reader can audit each stage.

The functions are deliberately conservative:
  - asserts use TIGHT tolerances; if you want a relaxed check, pass `tol=`
  - every check returns the data it inspected so the caller can keep using it
  - check_panel_*() emit a one-line summary to stdout for log readability

Reference values (frozen 2026-05-03; update only if raw data changes):

    Raw votacoes_votos_raw.csv (source of truth, all vote types):
        Leg 55: 308,714 deputy×vote rows
        Leg 56: 800,095 deputy×vote rows

    Forecasting paper (Sim/Não only, plenary, ≥2 voters):
        Leg 55: 283,692
        Leg 56: 771,263

    Polarization paper (no extra filters, all leg 51-57):
        Total: 1,676,162

    Filtered emendas panel (gov-oriented, MPV/PLP/PEC/PL-urgent):
        Must satisfy N(panel) ≤ N(forecasting) per legislature.
"""

from __future__ import annotations

import os
import hashlib
from typing import Iterable

import numpy as np
import pandas as pd


# ============================================================================
# Reference values from cross-paper audit
# ============================================================================

REF_RAW_VOTOS = {55: 308_714, 56: 800_095}
REF_FORECASTING_SIM_NAO = {55: 283_692, 56: 771_263}
REF_POLARIZATION_TOTAL = 1_676_162   # leg 51-57 unfiltered (features_v2 row count)


# ============================================================================
# Core assertions
# ============================================================================

def assert_unique_pair(
    df: pd.DataFrame,
    cols: Iterable[str],
    label: str = "panel",
) -> pd.DataFrame:
    """Assert (cols) is a unique key. Fails loud, prints sample of dupes."""
    cols = list(cols)
    n_dups = df.duplicated(subset=cols).sum()
    if n_dups > 0:
        sample = (df[df.duplicated(subset=cols, keep=False)]
                    .sort_values(cols).head(10))
        print(f"\n*** DUPLICATE KEY *** {label}: {n_dups:,} duplicates on {cols}")
        print(sample.to_string())
        raise AssertionError(
            f"{label}: {n_dups:,} duplicate rows on key {cols}"
        )
    return df


def assert_n_within(
    actual: int,
    expected_min: int,
    expected_max: int,
    label: str,
) -> None:
    """Assert actual N is within an expected band."""
    if not (expected_min <= actual <= expected_max):
        raise AssertionError(
            f"{label}: N={actual:,} outside expected range "
            f"[{expected_min:,}, {expected_max:,}]"
        )


def assert_no_negative(df: pd.DataFrame, col: str) -> None:
    if (df[col] < 0).any():
        n = (df[col] < 0).sum()
        raise AssertionError(f"{col}: {n:,} negative values")


def assert_subset(actual_set, expected_set, label: str) -> None:
    """Assert `actual_set` ⊆ `expected_set`. (e.g. legislaturas ⊆ {51..57})"""
    extra = set(actual_set) - set(expected_set)
    if extra:
        raise AssertionError(f"{label}: unexpected values {sorted(extra)}")


# ============================================================================
# Panel-level checks
# ============================================================================

def check_panel_counts_vs_raw(
    df: pd.DataFrame,
    legis_col: str = "idLegislatura",
    label: str = "panel",
) -> dict:
    """
    For a deputy×vote panel, verify per-legislature counts do not exceed the
    raw data. Returns a dict {leg: count}.

    The forecasting paper is the strictest upper bound (Sim/Não, plenary,
    ≥2 voters). A panel with additional filters (gov-oriented, etc.) must
    fall at or below those bounds.
    """
    counts = df[legis_col].value_counts().sort_index().to_dict()
    print(f"\n[sanity] {label}: counts by {legis_col}")
    for leg, n in counts.items():
        ref_raw = REF_RAW_VOTOS.get(int(leg))
        ref_fc  = REF_FORECASTING_SIM_NAO.get(int(leg))
        flag = ""
        if ref_raw is not None and n > ref_raw:
            flag = f"  *** EXCEEDS RAW {ref_raw:,} ***"
        elif ref_fc is not None and n > ref_fc:
            flag = f"  (above forecasting paper {ref_fc:,} — check filters)"
        print(f"  Leg {int(leg)}: {n:>10,}{flag}")
        if ref_raw is not None and n > ref_raw:
            raise AssertionError(
                f"{label}: leg {int(leg)} N={n:,} > raw N={ref_raw:,}. "
                f"Likely panel inflation (merge bug)."
            )
    return counts


def check_one_date_per_vote(
    df: pd.DataFrame,
    vote_col: str = "idVotacao",
    date_col: str = "data",
    label: str = "panel",
) -> int:
    """
    Each idVotacao must have exactly ONE canonical date.
    Votes that span midnight (vote opened before midnight, closed after)
    must have been collapsed upstream — this check catches the common bug
    where date is derived from individual vote timestamps.

    Returns the number of multi-date votes found (should be 0).
    """
    s = df.drop_duplicates([vote_col, date_col]).groupby(vote_col)[date_col].nunique()
    n_multi = int((s > 1).sum())
    if n_multi > 0:
        offenders = s[s > 1].head(20)
        print(f"\n*** MULTI-DATE VOTES *** {label}: {n_multi} idVotacao with >1 date")
        for v, k in offenders.items():
            dates = df[df[vote_col] == v][date_col].drop_duplicates().tolist()
            print(f"  {v}: {dates}")
        raise AssertionError(
            f"{label}: {n_multi} idVotacao map to multiple dates. "
            f"Use canonical date (first vote or votacoes_file_.csv)."
        )
    print(f"[sanity] {label}: 1 date per idVotacao ✓")
    return 0


def check_no_leakage_columns(
    df: pd.DataFrame,
    forbidden_substrings: Iterable[str] = (
        "pct_seg_ori", "pct_traiu_ori", "pct_votSim", "pct_votNao",
    ),
    label: str = "panel",
) -> None:
    """Assert no leakage columns survived to a panel that will be modeled."""
    found = [c for c in df.columns
             if any(sub in c for sub in forbidden_substrings)]
    if found:
        raise AssertionError(
            f"{label}: leakage columns present {found[:5]}{'…' if len(found)>5 else ''}"
        )
    print(f"[sanity] {label}: no leakage columns ✓")


def check_outcome_distribution(
    df: pd.DataFrame,
    outcome_col: str = "alinhamento",
    label: str = "panel",
) -> dict:
    """Outcome must be in {0,1} (no -1 placeholders) and reasonably balanced."""
    if df[outcome_col].isna().any():
        raise AssertionError(f"{label}: {outcome_col} has NaN")
    vals = set(df[outcome_col].unique())
    if not vals.issubset({0, 1}):
        raise AssertionError(
            f"{label}: {outcome_col} has values outside {{0,1}}: {vals}"
        )
    mean = df[outcome_col].mean()
    print(f"[sanity] {label}: {outcome_col} mean={mean:.4f} (expect ≈0.74)")
    if not (0.60 <= mean <= 0.85):
        print(f"  *** WARNING: outcome mean outside expected band [0.60, 0.85]")
    return {"mean": float(mean), "n_0": int((df[outcome_col] == 0).sum()),
            "n_1": int((df[outcome_col] == 1).sum())}


def check_treatment_scale(
    df: pd.DataFrame,
    treatment_col: str = "emenda_valor",
    expected_unit: str = "BRL",
    label: str = "panel",
) -> dict:
    """
    Verify treatment is in the expected unit. BRL means raw reais; values
    should be in millions. If you ever rescale to R$M, set expected_unit='BRLm'.
    """
    s = df[treatment_col]
    summary = {
        "min": float(s.min()), "max": float(s.max()),
        "mean": float(s.mean()), "median": float(s.median()),
        "std": float(s.std()), "p90": float(s.quantile(0.90)),
    }
    print(f"[sanity] {label}: {treatment_col} (unit={expected_unit})")
    print(f"  min={summary['min']:.3g}  median={summary['median']:.3g}  "
          f"mean={summary['mean']:.3g}  p90={summary['p90']:.3g}")

    if expected_unit == "BRL":
        # Expect raw reais: mean is millions of BRL
        if summary["mean"] < 1e3 or summary["mean"] > 1e9:
            print(f"  *** WARNING: mean {summary['mean']:.3g} unusual for BRL")
    elif expected_unit == "BRLm":
        # Expect R$M (already divided by 1e6)
        if summary["mean"] < 1e-3 or summary["mean"] > 1e3:
            print(f"  *** WARNING: mean {summary['mean']:.3g} unusual for R$M")
    return summary


def check_iv_correlations(
    df: pd.DataFrame,
    iv_cols: Iterable[str],
    treatment_col: str,
    outcome_col: str,
    label: str = "iv",
) -> pd.DataFrame:
    """
    For exclusion restriction + relevance:
      - corr(Z, T) should be meaningful (relevance)
      - corr(Z, Y) should be near zero (exclusion restriction)
      - ratio |corr(Z,Y) / corr(Z,T)| should be < 1
    """
    rows = []
    for z in iv_cols:
        rT = df[[z, treatment_col]].corr().iloc[0, 1]
        rY = df[[z, outcome_col]].corr().iloc[0, 1]
        ratio = abs(rY / rT) if rT != 0 else np.nan
        rows.append({
            "iv": z,
            "corr_ZT": round(rT, 4),
            "corr_ZY": round(rY, 4),
            "ratio_abs": round(ratio, 3) if not np.isnan(ratio) else None,
        })
    out = pd.DataFrame(rows)
    print(f"\n[sanity] {label}: IV correlations")
    print(out.to_string(index=False))
    # Soft warnings — IVs failing these are not necessarily bad, but flag them
    for row in rows:
        if abs(row["corr_ZT"]) < 0.001:
            print(f"  *** {row['iv']}: |corr(Z,T)|<0.001 (very weak)")
        if abs(row["corr_ZY"]) > 0.05:
            print(f"  *** {row['iv']}: |corr(Z,Y)|>0.05 (exclusion concern)")
    return out


# ============================================================================
# Reproducibility helpers
# ============================================================================

def file_hash(path: str, algo: str = "md5") -> str:
    """Hash a file (for input-data fingerprinting in audit logs)."""
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def write_sanity_report(
    step: str,
    payload: dict,
    out_dir: str,
) -> str:
    """
    Write a markdown sanity report for an audit trail.

    payload is a dict of section_name -> any (str, dict, or DataFrame).
    """
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"sanity_{step}.md")
    lines = [f"# Sanity report — {step}", ""]
    for section, content in payload.items():
        lines.append(f"## {section}")
        lines.append("")
        if isinstance(content, pd.DataFrame):
            lines.append("```")
            lines.append(content.to_string(index=False))
            lines.append("```")
        elif isinstance(content, dict):
            for k, v in content.items():
                lines.append(f"- **{k}**: {v}")
        else:
            lines.append(str(content))
        lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"\n[sanity] report → {path}")
    return path


# ============================================================================
# Smoke test
# ============================================================================

if __name__ == "__main__":
    # Quick smoke test if run directly
    df = pd.DataFrame({
        "idDeputado": [1, 1, 2, 2],
        "idVotacao":  ["a", "b", "a", "b"],
        "data":       pd.to_datetime(["2020-01-01"] * 4),
        "alinhamento": [0, 1, 1, 1],
        "idLegislatura": [55, 55, 55, 55],
    })
    assert_unique_pair(df, ["idDeputado", "idVotacao"], "smoke")
    check_one_date_per_vote(df, label="smoke")
    check_outcome_distribution(df, label="smoke")
    print("\n✓ _sanity.py self-test passed")
