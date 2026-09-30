import sys; sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis/dist_views'); sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis')
import numpy as np, pandas as pd, style as S
from loopeval_analysis import dists as D
d = pd.read_csv(S.OUT/"isf_rules.csv").set_index("alias")
edges=np.arange(60,310,10); ctr=(edges[:-1]+edges[1:])/2
curves={k:{} for k in ("now","2h","4h","net2h")}; rows=[]
for a in d.index:
    tdd=d.loc[a,"tdd_use"]
    if not np.isfinite(tdd): continue
    try: c=D.clean(S.load(a))
    except Exception: continue
    if len(c)<5000: continue
    unit=tdd/24.0
    iob=c.iob_abs/unit; net=c.iob_net/unit
    xs={"now":c.bg, "2h":c.bg.rolling("2h",min_periods=18).mean(),
        "4h":c.bg.rolling("4h",min_periods=36).mean()}
    xs["net2h"]=xs["2h"]
    r=dict(alias=a, iob_mean=float(iob.mean()))
    for k,x in xs.items():
        y = net if k=="net2h" else iob
        i=np.digitize(x.to_numpy(),edges)-1; ok=(i>=0)&(i<len(ctr))&np.isfinite(y.to_numpy())
        g=pd.DataFrame({"i":i[ok],"y":y.to_numpy()[ok]}).groupby("i"); n=g.size(); m=g.y.mean()[n>=30]
        xx=ctr[m.index]; curves[k][a]=pd.Series(m.to_numpy(),index=xx)
        sel=(xx>=120)&(xx<=250)
        if sel.sum()>=8:
            r[f"slope_{k}"]=np.polyfit(xx[sel],m.to_numpy()[sel],1,w=np.sqrt(n[m.index].to_numpy()[sel]))[0]*100
        for lo,hi,nm in ((100,120,"at110"),(190,210,"at200"),(70,90,"at80")):
            mm=(xx>=lo)&(xx<hi); r[f"{nm}_{k}"]=float(m.to_numpy()[mm].mean()) if mm.any() else np.nan
    rows.append(r)
g=pd.DataFrame(rows).set_index("alias")
d=d.drop(columns=[c for c in g.columns if c in d.columns]).join(g)
d.to_csv(S.OUT/"isf_rules.csv")
pd.to_pickle(curves, S.OUT/"iob_vs_bg.pkl")
q=lambda s: f"p10 {s.quantile(.1):5.2f}  p50 {s.median():5.2f}  p90 {s.quantile(.9):5.2f}"
print("IOB in hours of the person's average delivery")
print(f"  overall mean IOB           {q(d.iob_mean)}")
for k in ("now","2h","4h"):
    print(f"  vs {k:3s} glucose: at 80 {d[f'at80_{k}'].median():.2f}  at 110 {d[f'at110_{k}'].median():.2f}  "
          f"at 200 {d[f'at200_{k}'].median():.2f}   slope/100 mg/dL {q(d[f'slope_{k}'])}")
print(f"  net-of-schedule vs 2h: at 110 {d.at110_net2h.median():.2f}  at 200 {d.at200_net2h.median():.2f}  slope {q(d.slope_net2h)}")
print("\nby strategy (median):")
print(d.groupby("strategy")[["iob_mean","at110_2h","at200_2h","slope_2h","slope_now","slope_net2h"]].median().round(2).to_string())
