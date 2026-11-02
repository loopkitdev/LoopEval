"""Is the donors' within-block TDD persistence physiological, or is it their SETTINGS? A basal/ISF edit persists by
construction — every day after it shares the new level — and an override lasting days does the same. The twins hold
one settings era for 14 days, so if the donors' persistence lives on edit and override days, the twins are RIGHT to
sit at the independent-day null and `ac1` is not a body target at all.

Measures lag-1 over block-demeaned adjacent day pairs (drift out), then over the pairs where neither day carries a
settings change or an override.
    python tdd_clean_ac.py"""
import json, sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.quiet import local_offset, to_local
DAY, B, FULL = 1440.0, 13, Path.home() / ".loop-eval/ice_v32/full"

def _days(iso_series, off):
    """ISO stamps → local day index on the same epoch the steps use."""
    lt = to_local(pd.to_datetime(iso_series, utc=True, format="mixed"), off)
    return (L._mins(lt) // DAY).astype(int)

def settings_days(th, off):
    """Days whose scheduled basal total or mean ISF differs from the day before, and days with >30 min of override."""
    chg, ovr = set(), set()
    for key, agg in (("basal", "sum"), ("sensitivity", "mean")):
        seg = th.get(key) or []
        if len(seg) < 2: continue
        s = pd.DataFrame(seg)
        t = pd.to_datetime(s.startDate, utc=True, format="mixed")
        e = pd.to_datetime(s.endDate, utc=True, format="mixed")
        hrs = (e - t).dt.total_seconds() / 3600.0
        d = pd.Series(_days(s.startDate, off))
        v = s.value.astype(float) * (hrs.to_numpy() if key == "basal" else 1.0)
        g = pd.DataFrame(dict(d=d, v=v)).groupby("d").agg(v=("v", agg)).sort_index()
        if len(g) < 2: continue
        diff = g.v.diff().abs() / g.v.abs().clip(lower=1e-6)
        chg |= set(g.index[(diff > 0.01).fillna(False)].tolist())
    for w in (th.get("overrideWindows") or []):
        try:
            a = pd.to_datetime(w["start"], utc=True, format="mixed")
            b = pd.to_datetime(w["end"], utc=True, format="mixed")
            if (b - a).total_seconds() < 1800: continue
            d0, d1 = (int(x) for x in _days(pd.Series([w["start"], w["end"]]), off))
        except Exception:
            continue
        ovr |= set(range(d0, min(d1, d0 + 30) + 1))
    return chg, ovr

def pooled(pairs):
    if len(pairs) < 50: return np.nan, 0
    a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
    return (np.corrcoef(a, b)[0, 1] if a.std() > 0 and b.std() > 0 else np.nan), len(pairs)

all_p, clean_p, dirty_p = {k: [] for k in ("bas", "bol", "tot")}, {k: [] for k in ("bas", "bol", "tot")}, {k: [] for k in ("bas", "bol", "tot")}
nd = ndonor = 0
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    th_p = FULL / a / "therapy.json"
    if not th_p.exists(): continue
    try:
        off = local_offset(a, L.ICE_ROOT)
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet",
                            columns=["t1", "basal_u", "bolus_auto_u", "bolus_manual_u"])
        th = json.load(open(th_p))
    except Exception:
        continue
    t = L._mins(to_local(s.t1, off))
    g = pd.DataFrame(dict(d=(t // DAY).astype(int), bas=s.basal_u.fillna(0).to_numpy(float),
                          bol=(s.bolus_auto_u.fillna(0) + s.bolus_manual_u.fillna(0)).to_numpy(float))).groupby("d").sum()
    g = g[(g.bas + g.bol) > 5].sort_index()
    if len(g) < 2 * B: continue
    g["tot"] = g.bas + g.bol
    g["blk"] = np.arange(len(g)) // B
    chg, ovr = settings_days(th, off)
    bad = chg | ovr
    ndonor += 1; nd += len(g)
    for _, blk in g.groupby("blk"):
        if len(blk) < B: continue
        idx = blk.index.to_numpy()
        for k in ("bas", "bol", "tot"):
            v = blk[k].to_numpy(float); v = v - v.mean()          # demean the block: drift out
            for i in range(len(v) - 1):
                if idx[i + 1] != idx[i] + 1: continue             # adjacent calendar days only
                pr = (v[i], v[i + 1])
                all_p[k].append(pr)
                (clean_p if (idx[i] not in bad and idx[i + 1] not in bad) else dirty_p)[k].append(pr)

print(f"{ndonor} donors with therapy.json, {nd} donor-days, {B}-day blocks demeaned")
print(f"{'limb':>6} {'all pairs':>16} {'clean pairs':>18} {'edit/override pairs':>22}")
for k, lab in (("bas", "basal"), ("bol", "bolus"), ("tot", "TOTAL")):
    ra, na = pooled(all_p[k]); rc, nc = pooled(clean_p[k]); rd, ndp = pooled(dirty_p[k])
    print(f"{lab:>6} {ra:>+10.3f} (n{na:>5}) {rc:>+11.3f} (n{nc:>5}) {rd:>+14.3f} (n{ndp:>5})")
print("\nThe twins hold one era and run no overrides, so the CLEAN column is what they should be compared with.")
