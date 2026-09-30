import sys; sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis/dist_views')
sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis')
import numpy as np, pandas as pd, style as S
from loopeval_analysis import dists as D
d = pd.read_csv(S.OUT/"isf_rules.csv").set_index("alias")
edges = np.arange(40, 410, 10); ctr = (edges[:-1]+edges[1:])/2
rows, curves = [], {}
for a in d.index:
    try: c = D.clean(S.load(a))
    except Exception: continue
    tdd = d.loc[a,"tdd_use"]
    if not np.isfinite(tdd) or len(c) < 5000: continue
    auto = c.basal_eff.to_numpy()/12 + c.auto_bolus_u.fillna(0).to_numpy()
    tot  = auto + c.manual_bolus_u.fillna(0).to_numpy()
    unit = tdd/288.0                      # the person's average insulin per 5-min bin
    i = np.digitize(c.bg.to_numpy(), edges)-1; ok = (i>=0)&(i<len(ctr))
    g = pd.DataFrame({"i":i[ok],"a":auto[ok]/unit,"t":tot[ok]/unit}).groupby("i")
    n = g.size(); ma = g.a.mean()[n>=30]; mt = g.t.mean()[n>=30]
    x = ctr[ma.index]
    curves[a] = pd.Series(ma.to_numpy(), index=x)
    sel = (x>=120)&(x<=250)
    if sel.sum() < 8: continue
    w = n[ma.index].to_numpy()[sel]
    gain  = np.polyfit(x[sel], ma.to_numpy()[sel], 1, w=np.sqrt(w))[0]*100
    gainT = np.polyfit(x[sel], mt.to_numpy()[sel], 1, w=np.sqrt(w))[0]*100
    def at(lo,hi,s=ma):
        m = (x>=lo)&(x<hi); return float(np.average(s.to_numpy()[m], weights=n[s.index].to_numpy()[m])) if m.any() else np.nan
    rows.append(dict(alias=a, gain=gain, gain_total=gainT, floor=at(70,90),
                     at110=at(100,120), at200=at(190,210), at250=at(240,260)))
g = pd.DataFrame(rows).set_index("alias")
d = d.drop(columns=[c for c in g.columns if c in d.columns]).join(g)
d["settings_gain"] = 100/d.k1800            # fraction of TDD per 100 mg/dL the settings imply
d.to_csv(S.OUT/"isf_rules.csv")
pd.DataFrame(curves).to_pickle(S.OUT/"delivery_vs_bg.pkl")
q=lambda s,f="{:.2f}": f"p10 {f.format(s.quantile(.1))}  p50 {f.format(s.median())}  p90 {f.format(s.quantile(.9))}"
print(f"{len(g)} people")
print(f"  gain (automated, x average rate per +100 mg/dL): {q(d.gain)}")
print(f"  gain including manual boluses:                    {q(d.gain_total)}")
print(f"  delivery at 70-90  (x average): {q(d.floor)}")
print(f"  delivery at 100-120:            {q(d.at110)}")
print(f"  delivery at 190-210:            {q(d.at200)}")
print(f"  delivery at 240-260:            {q(d.at250)}")
print("\nby strategy (median):")
print(d.groupby("strategy")[["gain","gain_total","floor","at110","at200","at250","k1800"]].median().round(2).to_string())
