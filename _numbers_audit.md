# Audit of numbers in paper.tex against ground-truth CSVs (22/06/2026)

**Source of truth**: `paper-emendas/results/n3_*.csv` (n_reps=3 final run).

---

## 1. Main coefficient (Executive alignment) -- CORRECT in paper

| Sample | θ (pp/R$M) | 95% CI | p | N |
|---|---|---|---|---|
| Pooled | −2.82*** | [−3.74, −1.90] | <0.001 | 869,902 |
| Leg 55 | **+1.73** ** | [+0.26, +3.20] | 0.021 | 226,308 |
| Leg 56 | **−0.94** *** | [−1.37, −0.51] | <0.001 | 643,594 |

Status: ✅ Paper Table 4 matches.

---

## 2. Chamber-president alignment (Lira/Maia) -- CORRECT in paper

| Sample | θ (pp/R$M) | 95% CI | p | N |
|---|---|---|---|---|
| Leg 55 Maia (DEM) | **−2.76** *** | [−4.81, −0.71] | 0.008 | 119,389 |
| Leg 56 Maia (DEM) | +0.04 | [−0.33, +0.40] | 0.85 | 219,765 |
| **Leg 56 Lira (PP)** | **+0.33** ** | [+0.01, +0.65] | 0.043 | 396,066 |
| Lira excl PP | +0.32 * | [−0.03, +0.68] | 0.076 | 363,271 |
| Lira excl Centrão | −0.06 | [−0.58, +0.46] | 0.81 | 181,278 |

Status: ✅ Paper Table 11 matches.

---

## 3. Centrão alignment (alignment with Centrão bloc) -- CORRECT in paper

| Sample | θ (pp/R$M) | 95% CI | p | y_centrao_mean |
|---|---|---|---|---|
| Leg 55 full | +0.06 | [−1.47, +1.60] | 0.94 | 0.737 |
| Leg 56 full | **−0.67** ** | [−1.30, −0.04] | 0.036 | 0.766 |
| Leg 56 pre-Lira | **+0.87** *** | [+0.31, +1.44] | 0.003 | 0.771 |
| Leg 56 post-Lira | **+0.40** ** | [+0.07, +0.73] | 0.018 | 0.763 |
| Post-Lira excl Centrão | +0.24 | [−0.28, +0.76] | 0.36 | 0.633 |

⚠️ Paper Table 12 has `+1.37 **` for Leg 55 (CI [+0.14, +2.59]) -- this is from
an OLDER run (before n_reps=3). Should be **+0.06 n.s.** in revised paper.

Status: ⚠️ Paper Table 12 has wrong Leg 55 number (+1.37 from n_reps=1 instead of +0.06 n_reps=3).

---

## 4. Polarization terciles BY LEGISLATURE -- WRONG in paper

⚠️ Paper currently cites:
- "+4.21 pp in low tercile, -2.27 pp middle, ~0 high" (pooled)

These numbers are from an **older n_reps=1 run** (decomposition_v2.csv). The
n_reps=3 values are completely different:

### Gov outcome

| Measure | Leg | Low | Mid | High |
|---|---|---|---|---|
| MDS-Euclidean | 55 | −4.37 n.s. | +0.11 n.s. | +0.30 n.s. |
| MDS-Euclidean | 56 | **−1.38** *** | +18.80 (outlier, n.s.) | −0.32 * |
| MDS-Strong | 55 | −0.81 n.s. | **+3.11** *** | −1.86 n.s. |
| MDS-Strong | 56 | +8.99 (outlier, n.s.) | **−1.87** *** | −0.08 n.s. |
| **MDS-Weak** | 55 | −1.13 n.s. | **+6.91** *** | **+5.13** ** |
| **MDS-Weak** | 56 | +14.85 (outlier, n.s.) | **−1.10** *** | **+1.96** *** |

**The MDS-Weak Leg 56 pattern is the central polarization finding** (negative in
middle, positive in high tercile). Pattern is consistent with Strong but with
opposite mid-leg direction.

### Centrão outcome

Same pattern: MDS-Weak Leg 55 mid is **+4.18*** ***, high **+3.36*** ***.
For Leg 56, NaN for some rows (sample too small after cuts).

Status: ⚠️ Paper text needs full rewrite of polarization section with these numbers.

---

## 5. Causal mediation (single mediator) -- WRONG in paper

⚠️ Paper claims "63.8 percent of the Temer-era effect to legislative polarization;
in the Bolsonaro era the mediated share drops to zero".

But the ground truth (n3_t3_mediation_pix_gov.csv) shows:

| Sample | β_T total | β_T direct | indirect (Pix) | prop_med |
|---|---|---|---|---|
| Pooled | +0.0009 | +0.0007 | +0.0002 | **26.9%** |
| Leg 55 | +0.0111 | +0.0111 | +0.0000 | **0.0%** |
| Leg 56 | −0.0030 | −0.0031 | +0.0001 | **−3.4%** |

So Pix is NOT the mediator. The "63.8%" came from an older single-mediator
run using MDS-Euclidean. Need to recompute or remove the specific number.

Status: ⚠️ Paper "63.8%" claim is unverifiable from current CSVs.

---

## 6. Dual mediation (Strong + Weak) -- CORRECT in paper

| Sample | β_T total | Strong indirect (%) | Weak indirect (%) |
|---|---|---|---|
| Leg 55 | +0.0111 | +0.0035 (**31.4%**) | −0.0002 (−2.2%) |
| Leg 56 | −0.0030 | −0.0003 (9.6%) | ~0 (~0%) |

Status: ✅ Paper Appendix H matches.

---

## 7. RP-9 exposure heterogeneity (Leg 56) -- CORRECT

| Subgroup | θ (pp/R$M) | p | N |
|---|---|---|---|
| RP-9 exposed | −0.31 n.s. | 0.55 | 20,755 |
| RP-9 not exposed | **−0.99** *** | <0.001 | 622,839 |

---

## 8. Cargos het (Leg 56) -- CORRECT

| Subgroup | θ (pp/R$M) | p | N |
|---|---|---|---|
| No Mesa | −0.92 *** | <0.001 | 641,139 |
| Tier-2 (leadership/committee) | **−0.38 n.s.** | 0.35 | 217,061 |
| No Tier-2 | −1.03 *** | <0.001 | 426,533 |

---

## 9. T1 IV with proxies -- CORRECT

| Spec | Leg | θ (pp/R$M) |
|---|---|---|
| base_pure | 55 (y_pres) | −2.92 *** |
| base_plus_proxies | 55 | −3.04 *** |
| base_pure | 56 (y_pres) | −1.30 *** |
| base_plus_proxies | 56 | −1.32 *** |

(These are with y_pres outcome, not gov. Robustness story stable.)

---

## 10. Quadratic IV-2SLS -- CORRECT

| Sample | θ_T | θ_T² | T* (inflection) |
|---|---|---|---|
| Pooled | −0.071 *** | +0.012 *** | 2.88 R$M |
| Leg 55 | −0.251 *** | +0.042 *** | 2.99 R$M |
| Leg 56 | −0.020 *** | +0.004 ** | 2.70 R$M |

Status: ✅ Paper Appendix F matches.

---

## 11. Two-round PEC -- CORRECT

| Spec | β | p | N |
|---|---|---|---|
| OLS no FE | +0.37** | 0.015 | 3,383 |
| OLS + PEC FE | −0.21 | 0.26 | 3,383 |

Status: ✅ Paper Appendix G matches.

---

## Other claims in paper that need verification

| Claim | Where | Status |
|---|---|---|
| "1M raises alignment by 2.06pp" | §5.3 (Price subsection) | ❌ **WRONG**. Coefficient is 1.73, not 2.06. (The "2.06" was a false algebraic inversion attempt.) |
| "implicit price R$486k per pp" | §5.3 | Inversion of 1.73 ≈ R$578k, not R$486k. **WRONG by 19%.** |
| "implicit price R$1,066,000 per pp" Leg 56 | §5.3 | ❌ Mathematically OK (1/0.94 in R$M = R$1.064M) but interpretively nonsensical for negative coefficient |
| "63.8 percent of Temer-era effect to polarization" | Intro + Results | ❌ Source not in current CSVs (older run) |
| "+4.21 pp low tercile / −2.27 mid" | Results polarization | ❌ Old n_reps=1 numbers |
| "0.85% of federal budget" | Stylized facts | ⚠️ Was wrong denominator; should be 3.25% of RCL or 26.9% of discretionary |
| "Sargan-Hansen J=1399.6 p=0.000" | Diagnostic table | Need to verify against IV validation CSV |

---

## Recommendations for rewrite

1. **Remove the "Price of legislative support" subsection (Table 6)** entirely.
   The 2.06pp and R$486k numbers are wrong; the R$1.066M per pp is conceptually
   incoherent for the negative Leg 56 coefficient. Cleaner to drop.

2. **Centrão alignment table needs replacement**: use n3_t5_centrao numbers, not
   the OLD "+1.37**" for Leg 55.

3. **Polarization tercile narrative needs full rewrite** with correct n_reps=3
   numbers. MDS-Weak is the discriminating measure (matches our companion paper).

4. **Pix mediation claim ("63.8%") must be removed or recomputed**. Current Pix
   mediation gives 0% / -3% / 27% (pooled/55/56) -- the original 63.8% likely
   referenced MDS-Euclidean mediation, which we no longer have in CSVs.

5. **Budget share should be 3.25% of RCL** (or 26.9% of discretionary), not 0.85%.

6. **Pre-Lira / Post-Lira split of Leg 56**: this is a result that should be in
   the main results (Centrão outcome already has it; n_reps=3 values:
   - Leg 56 full: −0.67 ** (gov), Centrão alignment shifts pre-Lira to +0.87 ***
     and post-Lira to +0.40 **).
