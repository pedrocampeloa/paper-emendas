import sys
from pathlib import Path
sys.path.insert(0, "/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-emendas/source")
import _config as C
import pandas as pd
import numpy as np

base = Path("/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/dados/interim/panel")

print("Loading panel_features.csv...", flush=True)
needed = ["idDeputado","siglaPartido","data","idLegislatura","alinhamento","voto"]
df = pd.read_csv(base/"panel_features.csv", sep=";",
                   usecols=lambda c: c in needed, low_memory=False)
df["data"] = pd.to_datetime(df["data"], errors="coerce")
df = df.dropna(subset=["data","idDeputado","alinhamento"])
print(f"Loaded {len(df)} rows | {df['data'].min()} → {df['data'].max()}", flush=True)

print("Loading coalizao_partido_data.csv...", flush=True)
coal = pd.read_csv(base/"coalizao_partido_data.csv", sep=";")
coal["data"] = pd.to_datetime(coal["data"], errors="coerce")

# Build map (siglaPartido, mes) → status
df["mes"] = df["data"].dt.to_period("M").dt.to_timestamp()
coal["mes"] = coal["data"].dt.to_period("M").dt.to_timestamp()

# Each (partido, data) has a status — convert to monthly modal status
coal_m = coal.groupby(["siglaPartido","mes"]).agg(
    d_oposicao=("d_oposicao","max"),
    d_coalizao=("d_coalizao","max"),
    d_independente=("d_independente","max"),
    coalizao_status=("coalizao_status","first"),
).reset_index()
print(f"coal_m: {len(coal_m)} (partido, mes) combos", flush=True)

df = df.merge(coal_m, on=["siglaPartido","mes"], how="left")
print(f"After merge: {len(df)}, d_coalizao non-null: {df['d_coalizao'].notna().mean():.3f}", flush=True)

# Status
df["__status"] = "missing"
df.loc[df["d_oposicao"]==1, "__status"] = "opos"
df.loc[df["d_coalizao"]==1, "__status"] = "coal"
df.loc[df["d_independente"]==1, "__status"] = "indep"
print(f"Status: {df['__status'].value_counts().to_dict()}", flush=True)

# Drop missing
df = df[df["__status"] != "missing"].copy()
print(f"After dropping missing status: {len(df)}", flush=True)

# Restrict to relevant window: full leg 56 + leg 57
df = df[df["data"] >= "2020-01-01"].copy()
print(f"After 2020+ filter: {len(df)} | legs: {df['idLegislatura'].value_counts().sort_index().to_dict()}", flush=True)

# Monthly aggregation
monthly = df.groupby(["mes","__status"]).agg(
    align_mean=("alinhamento", "mean"),
    n=("alinhamento", "size"),
).reset_index()

out_dir = "/Users/pedrocampelo/Library/CloudStorage/Dropbox/UnB/Doc/projects/api_camara/paper-emendas/results"
monthly.to_csv(f"{out_dir}/event_study_monthly_full.csv", sep=";", index=False)
print(f"\n✓ saved event_study_monthly_full.csv ({len(monthly)} rows)", flush=True)

EVENTS = {
    "stf_cautelar":  pd.Timestamp("2021-11-05"),
    "stf_final":     pd.Timestamp("2022-12-19"),
    "lula_assume":   pd.Timestamp("2023-01-01"),
}

def wmean(d, col="align_mean"):
    if len(d)==0 or d["n"].sum()==0: return np.nan
    return (d[col]*d["n"]).sum() / d["n"].sum()

# ─── EVENT 1: STF CAUTELAR (within Bolsonaro gov) ────────────────────────────
EVENT = EVENTS["stf_cautelar"]
print(f"\n{'='*75}\nEVENT 1: STF cautelar {EVENT.date()} (WITHIN Bolsonaro government)\n{'='*75}")
pre = monthly[(monthly["mes"] >= EVENT - pd.DateOffset(months=18)) & (monthly["mes"] < EVENT)]
pos = monthly[(monthly["mes"] >= EVENT) & (monthly["mes"] < EVENTS["lula_assume"])]
print(f"Pre: {pre['mes'].min()} → {pre['mes'].max()} ({pre['mes'].nunique()} months)")
print(f"Pos: {pos['mes'].min()} → {pos['mes'].max()} ({pos['mes'].nunique()} months)")
print(f"{'status':10} {'pre_align':>12} {'pos_align':>12} {'diff_pp':>10} {'pre_n':>12} {'pos_n':>12}")
for s in ["coal","opos","indep"]:
    pre_s = pre[pre["__status"]==s]; pos_s = pos[pos["__status"]==s]
    pm = wmean(pre_s); pp = wmean(pos_s)
    diff = (pp-pm)*100 if not (np.isnan(pm) or np.isnan(pp)) else np.nan
    print(f"{s:10} {pm:>12.4f} {pp:>12.4f} {diff:>+10.2f} {int(pre_s['n'].sum()):>12} {int(pos_s['n'].sum()):>12}")
cd = wmean(pos[pos["__status"]=="coal"]) - wmean(pre[pre["__status"]=="coal"])
od = wmean(pos[pos["__status"]=="opos"]) - wmean(pre[pre["__status"]=="opos"])
id_ = wmean(pos[pos["__status"]=="indep"]) - wmean(pre[pre["__status"]=="indep"])
print(f"\nDelta_coal = {cd*100:+.2f} pp")
print(f"Delta_opos = {od*100:+.2f} pp")
print(f"Delta_indep = {id_*100:+.2f} pp")
print(f"DiD coal-opos = {(cd-od)*100:+.2f} pp")
print(f"DiD coal-indep = {(cd-id_)*100:+.2f} pp")

# Parallel trends
print(f"\nPre-period 12m trends:")
pre12 = monthly[(monthly["mes"] >= EVENT - pd.DateOffset(months=12)) & (monthly["mes"] < EVENT)]
for s in ["coal","opos","indep"]:
    sub = pre12[pre12["__status"]==s].sort_values("mes")
    if len(sub) < 3: continue
    x = np.arange(len(sub))
    y = sub["align_mean"].values
    slope = np.polyfit(x, y, 1)[0] if not np.any(np.isnan(y)) else np.nan
    print(f"  {s}: slope = {slope*100:+.3f} pp/month")

# ─── EVENT 2: STF FINAL (CONFOUNDED) ─────────────────────────────────────────
EVENT = EVENTS["stf_final"]
print(f"\n{'='*75}\nEVENT 2: STF final {EVENT.date()} — CONFOUNDED with Lula change\n{'='*75}")
pre = monthly[(monthly["mes"] >= EVENT - pd.DateOffset(months=12)) & (monthly["mes"] < EVENT)]
pos = monthly[(monthly["mes"] >= EVENT) & (monthly["mes"] < EVENT + pd.DateOffset(months=12))]
print(f"Pre: {pre['mes'].min()} → {pre['mes'].max()}")
print(f"Pos: {pos['mes'].min()} → {pos['mes'].max()}")
print(f"{'status':10} {'pre_align':>12} {'pos_align':>12} {'diff_pp':>10}")
for s in ["coal","opos","indep"]:
    pre_s = pre[pre["__status"]==s]; pos_s = pos[pos["__status"]==s]
    pm = wmean(pre_s); pp = wmean(pos_s)
    diff = (pp-pm)*100 if not (np.isnan(pm) or np.isnan(pp)) else np.nan
    print(f"{s:10} {pm:>12.4f} {pp:>12.4f} {diff:>+10.2f}")

# ─── EVENT 2-alt: PRE-STF-cautelar (placebo) ─────────────────────────────────
# Placebo: pick a date 18 months BEFORE STF cautelar where nothing happened (e.g., 2020-05-05)
EVENT = pd.Timestamp("2020-05-05")
print(f"\n{'='*75}\nPLACEBO: 2020-05-05 (random pre-event date)\n{'='*75}")
pre = monthly[(monthly["mes"] >= EVENT - pd.DateOffset(months=4)) & (monthly["mes"] < EVENT)]
pos = monthly[(monthly["mes"] >= EVENT) & (monthly["mes"] < pd.Timestamp("2021-05-01"))]
print(f"Pre: {pre['mes'].min()} → {pre['mes'].max()}")
print(f"Pos: {pos['mes'].min()} → {pos['mes'].max()}")
print(f"{'status':10} {'pre_align':>12} {'pos_align':>12} {'diff_pp':>10}")
for s in ["coal","opos","indep"]:
    pre_s = pre[pre["__status"]==s]; pos_s = pos[pos["__status"]==s]
    pm = wmean(pre_s); pp = wmean(pos_s)
    diff = (pp-pm)*100 if not (np.isnan(pm) or np.isnan(pp)) else np.nan
    print(f"{s:10} {pm:>12.4f} {pp:>12.4f} {diff:>+10.2f}")

print(f"\n=== Monthly evolution (2020-01 → 2024-12, align by status) ===")
piv = monthly.pivot(index="mes", columns="__status", values="align_mean").round(4)
print(piv.to_string())
