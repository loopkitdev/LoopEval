import sys; sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis/dist_views'); sys.path.insert(0,'/Users/pete/dev/loopeval-eda/analysis')
import numpy as np, pandas as pd, style as S
from loopeval_analysis import dists as D
d = pd.read_csv(S.OUT/"isf_rules.csv").set_index("alias")
edges=np.arange(50,330,10); ctr=(edges[:-1]+edges[1:])/2
curves={"all":{}, "rise":{}, "flat":{}, "fall":{}}
for a in d.index:
    try: c=D.clean(S.load(a))
    except Exception: continue
    if len(c)<5000: continue
    auto=c.basal_eff.to_numpy()+12*c.auto_bolus_u.fillna(0).to_numpy(); sch=c.basal_sched.to_numpy()
    bg=c.bg.to_numpy(); v30=c.v30.to_numpy()
    for k,m in (("all",np.isfinite(v30)),("rise",v30>=15),("flat",np.abs(v30)<=10),("fall",v30<=-15)):
        i=np.digitize(bg[m],edges)-1; ok=(i>=0)&(i<len(ctr))
        g=pd.DataFrame({"i":i[ok],"a":auto[m][ok],"s":sch[m][ok]}).groupby("i"); n=g.size()
        r=(g.a.mean()/g.s.mean())[n>=30]
        curves[k][a]=pd.Series(r.to_numpy(), index=ctr[r.index])
fig,ax=S.figure(1,2,figsize=(13.6,5.0))
COL={"bolus":S.ACCENT,"temp":S.COOL}; NAME={"bolus":"automatic bolus","temp":"temp basal"}
C=pd.DataFrame(curves["all"])
for a in C.columns: ax[0].plot(C.index,C[a],color=S.MUTED,lw=.6,alpha=.25,zorder=1)
for st in ("bolus","temp"):
    cols=[a for a in C.columns if d.loc[a,"strategy"]==st]
    ax[0].plot(C.index,C[cols].median(axis=1),color=COL[st],lw=2.6,zorder=4,label=f"{NAME[st]} (median of {len(cols)})")
ax[0].axhline(1,color=S.INK,lw=1,ls=(0,(3,3)))
ax[0].set_yscale("log"); ax[0].set_ylim(.05,8)
ax[0].set_xlabel("glucose (mg/dL)",fontsize=9.5,color=S.INK2)
ax[0].set_ylabel("automated delivery ÷ scheduled basal (log)",fontsize=9.5,color=S.INK2)
ax[0].legend(frameon=False,fontsize=8.5,labelcolor=S.INK2,loc="upper left")
ax[0].set_title("The dose–response curve, by strategy",fontsize=10.5,color=S.INK,loc="left",pad=6,weight="bold")
for k,col,lab in (("rise",S.ACCENT,"rising ≥15 mg/dL in 30 min"),("flat",S.INK,"flat (within ±10)"),("fall",S.COOL,"falling ≥15")):
    X=pd.DataFrame(curves[k]); med=X.median(axis=1); cnt=X.notna().sum(axis=1)
    med=med[cnt>=40]
    ax[1].plot(med.index,med,color=col,lw=2.6,zorder=4,label=lab)
    ax[1].fill_between(med.index,X.quantile(.25,axis=1)[med.index],X.quantile(.75,axis=1)[med.index],
                       color=col,alpha=.12,lw=0,zorder=2)
ax[1].axhline(1,color=S.INK,lw=1,ls=(0,(3,3)))
ax[1].set_yscale("log"); ax[1].set_ylim(.05,8)
ax[1].set_xlabel("glucose (mg/dL)",fontsize=9.5,color=S.INK2)
ax[1].set_ylabel("automated delivery ÷ scheduled basal (log)",fontsize=9.5,color=S.INK2)
ax[1].legend(frameon=False,fontsize=8.5,labelcolor=S.INK2,loc="upper left")
ax[1].set_title("…and by where glucose is heading",fontsize=10.5,color=S.INK,loc="left",pad=6,weight="bold")
S.title(fig,"How much insulin the automation delivers, at each glucose level",
        f"{len(C.columns)} Loop donors. Delivery is effective basal plus automatic boluses, divided by the person's own scheduled basal, so 1 =\n"
        "'delivering the schedule'. Faint lines are people; bands are the middle half. At the same glucose, the direction of travel\nchanges delivery by roughly an order of magnitude — the controller responds to trend far more than to level.")
S.save(fig,"dose_response",dict(left=0.06,right=0.99,top=0.78,bottom=0.12,wspace=0.2))
