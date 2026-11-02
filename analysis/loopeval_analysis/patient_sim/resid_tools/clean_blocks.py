"""Which scored statistics are contaminated by the donors' SETTINGS? A twin holds one therapy era for its whole
window and runs no overrides; a donor's 13-day block often straddles a basal/ISF edit or a multi-day override. For
`ac1` that accounts for half the target (L 585). This screens every statistic the same way: it replays `real_stats`'
block walk to date each accepted block, flags blocks carrying an edit or >30 min of override, and reports the donor
median on clean versus contaminated blocks.
    python clean_blocks.py REAL_PILOT_BLOCKS.csv"""
import json, sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path.home() / "dev/loopeval-additive/analysis"))
from loopeval_analysis.patient_sim import lifestats as L
from loopeval_analysis.patient_sim.quiet import local_offset, to_local
from loopeval_analysis.patient_sim.resid_tools.tdd_clean_ac import settings_days, _days
FULL, DAY, B = Path.home() / ".loop-eval/ice_v32/full", 1440.0, 13

def block_spans(alias):
    """The accepted blocks' local day ranges, in real_stats' own order (index = position among ACCEPTED blocks)."""
    g = json.load(open(FULL / alias / "glucose.json"))
    idx = pd.to_datetime([x["startDate"] for x in g], utc=True).sort_values()
    try:
        off = local_offset(alias, L.ICE_ROOT)
        idx = to_local(idx, off)
    except Exception:
        off = None
    cnt = pd.Series(1, index=idx)
    t0, t1 = idx[0].floor("D") + pd.Timedelta(days=1), idx[-1].floor("D")
    out, s = [], t0
    while s + pd.Timedelta(days=B) <= t1:
        e = s + pd.Timedelta(days=B)
        if int(cnt[(cnt.index >= s) & (cnt.index < e)].sum()) > 0.7 * B * 288:
            out.append((s, e))
        s = e
    return out, off

R = pd.read_csv(sys.argv[1] if len(sys.argv) > 1 else
                str(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/real_pilot_blocks.csv"))
flags, miss = {}, 0
for a in sorted(R.alias.unique()):
    th_p = FULL / a / "therapy.json"
    if not th_p.exists(): miss += 1; continue
    try:
        spans, off = block_spans(a)
        chg, ovr = settings_days(json.load(open(th_p)), off)
    except Exception:
        miss += 1; continue
    ovh = {}
    for w in (json.load(open(th_p)).get("overrideWindows") or []):
        try:
            t_ = pd.to_datetime(w["start"], utc=True, format="mixed"); e_ = pd.to_datetime(w["end"], utc=True, format="mixed")
            h = (e_ - t_).total_seconds() / 3600.0
            if h < 0.5: continue
            d_ = int(_days(pd.Series([w["start"]]), off).iloc[0] if hasattr(_days(pd.Series([w["start"]]), off), "iloc")
                     else _days(pd.Series([w["start"]]), off)[0])
        except Exception:
            continue
        ovh[d_] = ovh.get(d_, 0.0) + min(h, 24.0)
    for i, (s, e) in enumerate(spans):
        d0 = int((s - pd.Timestamp("1970-01-01")).total_seconds() // 86400)
        days = range(d0, d0 + B)
        flags[(a, i)] = (sum(1 for k in days if k in chg), sum(ovh.get(k, 0.0) for k in days))
R["n_edit"] = [flags.get((a, b), (np.nan, np.nan))[0] for a, b in zip(R.alias, R.block)]
R["ovr_h"] = [flags.get((a, b), (np.nan, np.nan))[1] for a, b in zip(R.alias, R.block)]
K = R.dropna(subset=["n_edit"])
stats = [c for c in R.columns if c not in ("alias", "block", "n_edit", "ovr_h")]
print(f"{len(K)} blocks dated of {len(R)}; per block: edit days p50 {K.n_edit.median():.0f}, "
      f"override hours p50 {K.ovr_h.median():.1f}; {miss} donors skipped")
print("Within-donor Spearman of each block statistic against the block's edit days and override hours")
print(f"{'statistic':>18} {'r(edits)':>10} {'r(override h)':>14}")
def wd(df, col, flag):
    g = df.groupby("alias")
    x = df[col].astype(float) - g[col].transform("median")
    y = df[flag].astype(float) - g[flag].transform("median")
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 200 or x[m].std() == 0 or y[m].std() == 0: return np.nan
    return float(pd.Series(x[m]).corr(pd.Series(y[m]), method="spearman"))
rows = []
for c in stats:
    re_, ro_ = wd(K, c, "n_edit"), wd(K, c, "ovr_h")
    rows.append((max(abs(re_ or 0), abs(ro_ or 0)), c, re_, ro_))
for mx, c, re_, ro_ in sorted(rows, reverse=True):
    mark = "  <--" if mx > 0.08 else ""
    print(f"{c:>18} {re_:>+10.3f} {ro_:>+14.3f}{mark}")
