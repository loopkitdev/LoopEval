"""Schedule swaps in the pilot (ice_v32 exports): do whole-profile changes reduce to one insulin-needs factor?

usage: python profiles.py [out.csv]
Per donor and local day, from therapy.json raw schedules (overrides excluded): the day's basal total, and the
time-weighted means of 1/ISF and 1/CR, each relative to the donor's median day. A day's profile counts as
different when any of the three moves more than 3%. For each donor with such days: the share of days that differ,
how well the three ratios agree (one factor f = their geometric mean; residual = largest |log ratio - log f|), and
whether the difference follows the day of the week (share of variance in log f explained by weekday)."""
import json, os, sys
import numpy as np, pandas as pd
ROOT = os.path.expanduser("~/.loop-eval/ice_v32")

def daily(alias):
    t = json.load(open(f"{ROOT}/full/{alias}/therapy.json"))
    tz = pd.read_csv(f"{ROOT}/tz_daily.csv"); tz = tz[tz.alias == alias].tz.mode()
    tz = tz.iloc[0] if len(tz) else "UTC"
    def grid(key, f):
        rows = t.get("raw" + key[0].upper() + key[1:]) or t[key]
        s = []
        for r in rows:
            a, b = pd.Timestamp(r["startDate"]), pd.Timestamp(r["endDate"])
            v = f(r)
            s.append((a, b, v))
        idx = pd.date_range(s[0][0].ceil("30min"), s[-1][1], freq="30min", inclusive="left")
        out = pd.Series(np.nan, idx)
        for a, b, v in s: out[(idx >= a) & (idx < b)] = v
        return out
    b = grid("basal", lambda r: r["value"]); i = grid("sensitivity", lambda r: 1 / r["value"]); c = grid("carbRatio", lambda r: 1 / r["value"])
    d = pd.DataFrame(dict(basal=b, iisf=i, icr=c)).dropna()
    d.index = d.index.tz_convert(tz)
    g = d.groupby(d.index.date)
    D = pd.DataFrame(dict(basal=g.basal.sum() / 2, iisf=g.iisf.mean(), icr=g.icr.mean(), n=g.size()))
    D = D[D.n == 48]; D.index = pd.to_datetime(D.index)
    return D

def summarize(alias):
    D = daily(alias)
    if len(D) < 28: return None
    L = np.log(D[["basal", "iisf", "icr"]] / D[["basal", "iisf", "icr"]].median())
    diff = (L.abs() > np.log(1.03)).any(axis=1)
    if diff.sum() < 3: return dict(alias=alias, days=len(D), diff_days=int(diff.sum()))
    f = L.mean(axis=1)
    resid = (L.sub(f, axis=0)).abs().max(axis=1)[diff]
    wd = D.index.dayofweek
    r2 = 1 - (f - f.groupby(wd).transform("mean")).var() / f.var() if f.var() > 0 else np.nan
    wk = f.groupby(wd >= 5).mean()
    return dict(alias=alias, days=len(D), diff_days=int(diff.sum()), share=diff.mean(),
                f_lo=float(np.exp(f[diff].min())), f_hi=float(np.exp(f[diff].max())),
                one_factor_resid_med=float(np.exp(resid.median()) - 1), one_factor_resid_p90=float(np.exp(resid.quantile(0.9)) - 1),
                weekday_r2=float(r2), weekend_vs_week=float(np.exp(wk.get(True, 0) - wk.get(False, 0))),
                n_profiles=int(L.round(2).drop_duplicates().shape[0]))

if __name__ == "__main__":
    al = sorted(a for a in os.listdir(f"{ROOT}/full") if a.startswith("i"))
    rows = []
    for a in al:
        try:
            r = summarize(a)
            if r: rows.append(r)
        except Exception as ex: print(a, "skip", ex, file=sys.stderr)
    T = pd.DataFrame(rows)
    if len(sys.argv) > 1: T.to_csv(sys.argv[1], index=False)
    sw = T[T.diff_days >= 3]
    print(f"donors {len(T)}; with >=3 days on a different profile {len(sw)}")
    pd.set_option("display.width", 200)
    print(sw.sort_values("share", ascending=False).round(3).to_string(index=False))
