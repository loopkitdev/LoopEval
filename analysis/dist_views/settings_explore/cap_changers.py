import sys; sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis/dist_views'); sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis')
import numpy as np, pandas as pd, style as S
from loopeval_analysis import dists as D
from scipy.stats import wilcoxon
H = pd.read_pickle(S.OUT/"pumpsettings_history.pkl")
R = pd.read_csv(S.OUT/"isf_rules.csv").set_index("alias")
WIN, MIN_DAYS, GUARD, CO = 28, 10, 1, 3
events=[]
for a,g in H.dropna(subset=["max_basal"]).groupby("alias"):
    g = g.set_index("t").sort_index()
    daily = g.resample("1D").last().ffill()
    mb = daily.max_basal
    ch = mb.ne(mb.shift()) & mb.shift().notna()
    days = list(mb.index[ch])
    for i,day in enumerate(days):
        prev_change = days[i-1] if i>0 else mb.index[0]
        next_change = days[i+1] if i+1<len(days) else mb.index[-1]+pd.Timedelta(days=1)
        pre_lo = max(prev_change, day-pd.Timedelta(days=WIN+GUARD)); pre_hi = day-pd.Timedelta(days=GUARD)
        post_lo = day+pd.Timedelta(days=GUARD); post_hi = min(next_change, day+pd.Timedelta(days=WIN+GUARD))
        co = {}
        for h in ("h_isf","h_basal","h_target","h_cr"):
            s = daily[h]; near = s[(s.index>=day-pd.Timedelta(days=CO))&(s.index<=day+pd.Timedelta(days=CO))]
            co[h] = near.nunique()>1
        events.append(dict(alias=a, day=day, old=mb.shift()[day], new=mb[day],
                           pre=(pre_lo,pre_hi), post=(post_lo,post_hi), **co))
E = pd.DataFrame(events)
print(f"{len(E)} max-basal changes across {E.alias.nunique()} donors")
rows=[]
for _,e in E.iterrows():
    try: c = D.clean(S.load(e.alias))
    except Exception: continue
    out = dict(alias=e.alias, day=e.day.date(), old=e.old, new=e.new,
               co_isf=e.h_isf, co_basal=e.h_basal, co_target=e.h_target, co_cr=e.h_cr)
    ok=True
    for side,(lo,hi),cap in (("pre",e.pre,e.old),("post",e.post,e.new)):
        w = c[(c.index>=lo)&(c.index<hi)]
        nd = w.index.normalize().nunique()
        if nd < MIN_DAYS: ok=False; break
        bg = w.bg; hi_ = bg>180
        dl = w.basal_eff/12 + w.bolus_u.fillna(0)
        out.update({f"{side}_days":nd, f"{side}_tir":100*bg.between(70,180).mean(),
                    f"{side}_t70":100*(bg<70).mean(), f"{side}_t54":100*(bg<54).mean(),
                    f"{side}_mean":bg.mean(), f"{side}_tdd":dl.sum()/nd,
                    f"{side}_pin":100*(w.basal_eff[hi_]>=cap*0.99).mean() if hi_.sum()>50 else np.nan})
    if ok: rows.append(out)
P = pd.DataFrame(rows)
P["dir"] = np.where(P.new<P.old,"lowered","raised")
P["clean"] = ~(P.co_isf|P.co_basal|P.co_target|P.co_cr)
P["pct"] = 100*(P.new/P.old-1)
P = P.join(R[["strategy","k1800"]], on="alias")
P.to_csv(S.OUT/"cap_changes.csv", index=False)
print(f"{len(P)} changes with >= {MIN_DAYS} usable days each side ({P.alias.nunique()} donors); "
      f"{int(P.clean.sum())} with no other settings change within {CO} days")
print(P.groupby(["strategy","dir"]).size().unstack(fill_value=0).to_string())
for sub,lab in ((P,"all"),(P[P.clean],"clean only")):
    for dr in ("lowered","raised"):
        s = sub[sub.dir.eq(dr)]
        if len(s) < 4: print(f"\n[{lab}] {dr}: n={len(s)} — too few"); continue
        print(f"\n[{lab}] cap {dr}: n={len(s)} (median change {s.pct.median():+.0f}%)")
        for m in ("tir","t70","t54","mean","tdd","pin"):
            x = (s[f"post_{m}"]-s[f"pre_{m}"]).dropna()
            p = wilcoxon(x).pvalue if len(x)>=5 and (x!=0).any() else np.nan
            print(f"   {m:5s} before {s[f'pre_{m}'].median():7.2f}  after {s[f'post_{m}'].median():7.2f}   "
                  f"median change {x.median():+6.2f}   p={p:.3f}")
