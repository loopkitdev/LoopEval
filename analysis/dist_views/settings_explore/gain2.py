import sys; sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis/dist_views')
sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis')
import numpy as np, pandas as pd, style as S
from loopeval_analysis import dists as D
from scipy.stats import spearmanr, rankdata, t as tdist
d = pd.read_csv(S.OUT/"isf_rules.csv").set_index("alias")
bands = {"b70":(70,90),"b110":(100,120),"b150":(140,160),"b200":(190,210),"b250":(240,260)}
rows=[]; curves={}
edges=np.arange(40,410,10); ctr=(edges[:-1]+edges[1:])/2
for a in d.index:
    try: c = D.clean(S.load(a))
    except Exception: continue
    if len(c)<5000: continue
    auto = c.basal_eff.to_numpy() + 12*c.auto_bolus_u.fillna(0).to_numpy()   # U/hr, automated
    sch  = c.basal_sched.to_numpy()
    bg = c.bg.to_numpy()
    r = dict(alias=a)
    for k,(lo,hi) in bands.items():
        m=(bg>=lo)&(bg<hi)
        r[k] = auto[m].mean()/sch[m].mean() if m.sum()>=50 else np.nan   # x scheduled basal
    rows.append(r)
    i=np.digitize(bg,edges)-1; ok=(i>=0)&(i<len(ctr))
    g=pd.DataFrame({"i":i[ok],"v":auto[ok]/sch[ok]}).groupby("i"); n=g.size()
    curves[a]=pd.Series(g.v.mean()[n>=30].to_numpy(), index=ctr[g.v.mean()[n>=30].index])
g=pd.DataFrame(rows).set_index("alias")
d=d.drop(columns=[c for c in g.columns if c in d.columns]).join(g)
d["push"]    = d.b200/d.b110          # how much harder when 90 mg/dL higher (scale-free)
d["backoff"] = d.b70/d.b110           # how much it backs off near 80 (scale-free)
d.to_csv(S.OUT/"isf_rules.csv"); pd.DataFrame(curves).to_pickle(S.OUT/"delivery_vs_bg_sched.pkl")
q=lambda s: f"p10 {s.quantile(.1):.2f}  p50 {s.median():.2f}  p90 {s.quantile(.9):.2f}"
print("automated delivery as a multiple of scheduled basal:")
for k in bands: print(f"  {k:5s} {q(d[k])}")
print(f"  push   (x200/x110) {q(d.push)}")
print(f"  backoff (x80/x110) {q(d.backoff)}")
print("\nby strategy (median):"); print(d.groupby("strategy")[list(bands)+["push","backoff"]].median().round(2).to_string())

def partial(x,y,ctrl,g=d):
    s=g[[x,y]+ctrl].dropna()
    R=np.column_stack([np.ones(len(s))]+[rankdata(s[c]) for c in ctrl])
    res=lambda v: rankdata(v)-R@np.linalg.lstsq(R,rankdata(v),rcond=None)[0]
    rr=np.corrcoef(res(s[x]),res(s[y]))[0,1]; n=len(s); k=len(ctrl)
    return rr, 2*tdist.sf(abs(rr*np.sqrt((n-k-2)/(1-rr*rr))),n-k-2)
C=["tdd_use","age_years","target"]
print("\n=== outcomes: partial Spearman holding TDD, age, target")
for sub,gg in (("all",d),("autobolus",d[d.strategy.eq("bolus")]),("temp",d[d.strategy.eq("temp")])):
    print(f"  -- {sub} (n={len(gg)})")
    for x in ("b110","b150","push","backoff","settings_gain"):
        out=[f"    {x:13s}"]
        for y in ("tir","t70","t54"):
            rr,p=partial(x,y,C,gg); out.append(f"{y} {rr:+.2f} (p={p:.3f})")
        print("  ".join(out))
print("\n=== what sets the delivery shape?")
for x in ("settings_gain","headroom","k1800","target"):
    for y in ("b110","push","backoff"):
        s=d[[x,y]].dropna(); rr=spearmanr(s[x],s[y]); print(f"  {x:13s} vs {y:7s} rho {rr[0]:+.2f} p={rr[1]:.3g}")
