"""Do the donors withhold a correction when Loop SHOWS them insulin on board? The behaviour model's correction limb
fires on CGM level and trend alone, while a real user sees IOB and a forecast. If the hazard of a manual correction
falls with displayed IOB at the same glucose, controller-presented state belongs in that decision.

Confound: IOB is ENDOGENOUS to the glucose history. At the same glucose, high IOB means Loop has been dosing hard,
which means the glucose has been stubbornly high — and a person corrects a glucose that will not come down. Raw, the
donors look 4-5x MORE likely to correct at high IOB. So the comparison is made inside a cell of (donor, glucose band,
2-h mean glucose tercile, trend sign) and >= 60 min after the last manual bolus, which holds the trajectory as well
as the level.
    python corr_vs_iob.py"""
import sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.quiet import local_offset, to_local
BANDS = [(150, 180), (180, 220), (220, 300)]
rows = []
for a in sorted({p.stem for p in (L.ICE_ROOT / "steps").glob("*.parquet")}):
    try:
        s = pd.read_parquet(L.ICE_ROOT / "steps" / f"{a}.parquet",
                            columns=["t1", "bg1", "iob", "carbs_g", "bolus_manual_u", "clean"])
    except Exception:
        continue
    s = s.sort_values("t1").reset_index(drop=True)
    try:
        hr = to_local(s.t1, local_offset(a, L.ICE_ROOT)).hour
    except Exception:
        continue
    awake = (np.asarray(hr) >= 8) & (np.asarray(hr) < 22)
    man = (s.bolus_manual_u.fillna(0) > 0.05).to_numpy()
    carb = (s.carbs_g.fillna(0) > 0).to_numpy()
    n = len(s)
    # minutes since the last manual bolus, and whether a carb entry sits within +-30 min (meal bolus, not a correction)
    since = np.full(n, 1e9); last = -1e9
    for i in range(n):
        since[i] = (i - last) * 5.0
        if man[i]: last = i
    w = 6
    near_carb = pd.Series(carb).rolling(2 * w + 1, center=True, min_periods=1).max().to_numpy() > 0
    ok = (since >= 180) & awake & (~near_carb) & s.clean.fillna(False).to_numpy() & np.isfinite(s.iob.to_numpy())
    bg = s.bg1.to_numpy(float)
    hist = pd.Series(bg).rolling(24, min_periods=12).mean().to_numpy()      # 2-h mean glucose
    tr = pd.Series(bg).diff(6).to_numpy()                                   # 30-min change
    for lo, hi in BANDS:
        m = ok & (bg >= lo) & (bg < hi) & np.isfinite(hist) & np.isfinite(tr)
        if m.sum() < 400: continue
        iob = s.iob.to_numpy()[m]; hit = man[m]; h = hist[m]; d = tr[m]
        hq = np.quantile(h, [1 / 3, 2 / 3])
        cell = np.digitize(h, hq) * 2 + (d > 0).astype(int)                 # history tercile x trend sign
        lo_hit, hi_hit, lo_n, hi_n, il, ih = 0.0, 0.0, 0, 0, [], []
        for c in np.unique(cell):                                           # IOB terciles INSIDE each cell
            k = cell == c
            if k.sum() < 150: continue
            q = np.quantile(iob[k], [1 / 3, 2 / 3])
            g = np.digitize(iob[k], q)
            if (g == 0).sum() < 50 or (g == 2).sum() < 50: continue
            lo_hit += hit[k][g == 0].sum(); lo_n += int((g == 0).sum()); il.append(np.median(iob[k][g == 0]))
            hi_hit += hit[k][g == 2].sum(); hi_n += int((g == 2).sum()); ih.append(np.median(iob[k][g == 2]))
        if lo_n < 200 or hi_n < 200: continue
        rows.append(dict(alias=a, band=f"{lo}-{hi}", n=int(m.sum()), iob_lo=float(np.mean(il)), iob_hi=float(np.mean(ih)),
                         p0=lo_hit / lo_n * 288, p2=hi_hit / hi_n * 288))
R = pd.DataFrame(rows).dropna(subset=["p0", "p2"])
print(f"{R.alias.nunique()} donors, {len(R)} donor-bands; >= 60 min after the last manual bolus, no carb entry within 30 min,")
print("IOB terciles compared INSIDE each (2-h mean glucose tercile x trend sign) cell")
print(f"{'band':>9} {'donors':>7} {'IOB low':>9} {'IOB high':>9} {'corr/day at low IOB':>21} {'at high IOB':>13} {'ratio':>7}")
for b, g in R.groupby("band"):
    rat = (g.p2 / g.p0.replace(0, np.nan)).median()
    print(f"{b:>9} {len(g):>7} {g.iob_lo.median():>9.2f} {g.iob_hi.median():>9.2f} {g.p0.median():>21.2f} {g.p2.median():>13.2f} {rat:>7.2f}")
pair = R.dropna(subset=["p0", "p2"])
from scipy.stats import wilcoxon
try:
    st, p = wilcoxon(pair.p0, pair.p2)
    print(f"\npaired within donor-band, low vs high IOB: n {len(pair)}, Wilcoxon p {p:.2g}; "
          f"median drop {(pair.p0 - pair.p2).median():+.2f} corrections/day")
except Exception as e:
    print("wilcoxon:", e)
