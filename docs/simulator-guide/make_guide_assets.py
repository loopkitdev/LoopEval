"""Generate explanatory graphs for the simulator guide (real user1 data)."""
import sys, json
import os
from pathlib import Path
_REPO = Path(__file__).resolve().parents[2]  # LoopEval repo root
sys.path.insert(0, str(_REPO / 'analysis'))
import numpy as np, pandas as pd, pytz
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from loopeval_analysis.iob import RAPID_ACTING_ADULT, percent_effect_remaining
G=str(Path(__file__).resolve().parent)
# A: directory of simulate traces used as illustration inputs (any run dir works)
A=os.environ.get('GUIDE_ASSETS_RUN', str(_REPO / 'runs/guide-assets'))
tz=pytz.timezone('America/Chicago')
plt.rcParams.update({'figure.dpi':120,'font.size':10,'axes.grid':True,'grid.alpha':0.3})

# ---------- 1. Insulin PD curve (the pharmacodynamic model) ----------
mins=np.arange(0,371,1.0)
rem=percent_effect_remaining(mins, RAPID_ACTING_ADULT)        # IOB fraction remaining
act=np.gradient(1-rem, mins)                                  # activity = d(effect delivered)/dt
fig,ax=plt.subplots(figsize=(8,4))
ax.plot(mins/60, rem,'-',color='#1565c0',lw=2,label='IOB (fraction of dose remaining)')
ax2=ax.twinx(); ax2.plot(mins/60, act*1000,'-',color='#c62828',lw=2,label='activity (effect rate)')
ax.axvline(75/60,color='#888',ls=':'); ax.annotate('peak activity ~75 min',(75/60,0.5),fontsize=8,color='#555')
ax.set_xlabel('hours since dose'); ax.set_ylabel('IOB fraction',color='#1565c0'); ax2.set_ylabel('activity (×10⁻³ /min)',color='#c62828')
ax.set_title('Insulin pharmacodynamics — RAPID_ACTING_ADULT (DIA 6h, peak 75 min, 10 min delay)')
ax.set_xlim(0,6.2); fig.tight_layout(); fig.savefig(G+'/pd_curve.png',bbox_inches='tight'); plt.close()

# ---------- load user1 substrate (smoothed) + a raw trace ----------
d=pd.read_csv(A+'/nie_mmax2.csv', parse_dates=['t']); d['t']=d.t.dt.tz_convert(tz)
tr=json.load(open(A+'/nbnc_af040.json')); ac=pd.DataFrame(tr['actual']); ac['t']=pd.to_datetime(ac['t']).dt.tz_convert(tz); ac=ac.dropna(subset=['bg'])

# ---------- 2. Substrate: raw CGM vs RTS-smoothed 5-min grid ----------
w0=pd.Timestamp('2025-09-04',tz=tz); w1=w0+pd.Timedelta(days=1)
dr=ac[(ac.t>=w0)&(ac.t<w1)]; ds=d[(d.t>=w0)&(d.t<w1)]
fig,ax=plt.subplots(figsize=(9,3.6))
ax.plot(dr.t, dr.bg,'.',color='#bbb',ms=4,label='raw CGM (irregular)')
ax.plot(ds.t, ds.bg,'-',color='#1565c0',lw=1.6,label='RTS-smoothed substrate (5-min grid)')
ax.axhline(70,color='#c62828',lw=0.6,ls='--'); ax.axhline(180,color='#ef6c00',lw=0.6,ls='--')
ax.set_ylabel('BG (mg/dL)'); ax.set_title('SUBSTRATE — actual CGM is RTS-Kalman-smoothed onto a 5-min grid (the trace the whole sim runs on)')
ax.legend(loc='upper right',fontsize=8); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(G+'/substrate.png',bbox_inches='tight'); plt.close()

# ---------- 3. Counterfactual decomposition: NIE baseline + insulin ----------
# "no insulin" = bg_start + cumsum(NIE). Over a long window this runs away (carbs+EGP
# with nothing opposing → BG to the moon), so the decomposition is only legible over a
# SHORT horizon. Auto-pick a ~5h window where the no-insulin line peaks on-chart (~280-360)
# so you can actually SEE the insulin-effect gap open up.
HRS=5.0
cand=d.reset_index(drop=True)
best=None
for i in range(0, len(cand)-1, 6):                       # step ~30 min
    seg=cand.iloc[i:i+int(HRS*12)]                        # 12 five-min steps/hr
    if len(seg)<int(HRS*12): break
    b0=seg.bg.iloc[0]; noins=b0+np.cumsum(seg.nie.values)
    pk=noins.max()
    if 90<=b0<=140 and 280<=pk<=360 and seg.bg.min()>55:  # clean single excursion, on-chart
        best=(i,seg.reset_index(drop=True),noins); break
if best is None:                                          # fallback: fixed window
    w0=pd.Timestamp('2025-09-10',tz=tz); w1=w0+pd.Timedelta(hours=HRS)
    seg=cand[(cand.t>=w0)&(cand.t<w1)].reset_index(drop=True); noins=seg.bg.iloc[0]+np.cumsum(seg.nie.values)
else:
    seg=best[1]; noins=best[2]
fig,ax=plt.subplots(figsize=(9,4))
ax.fill_between(seg.t, seg.bg, noins, color='#c62828',alpha=0.16,label='insulin effect (the gap insulin closes)')
ax.plot(seg.t, noins,'--',color='#2e7d32',lw=1.8,label='if NO insulin (cumulative NIE = carbs + EGP)')
ax.plot(seg.t, seg.bg,'-',color='#1565c0',lw=2.2,label='actual / counter BG')
ax.axhline(70,color='#c62828',lw=0.6,ls=':'); ax.axhline(180,color='#ef6c00',lw=0.6,ls=':')
ax.set_ylabel('BG (mg/dL)'); ax.set_ylim(40, noins.max()*1.08)
ax.set_title('COUNTERFACTUAL DECOMPOSITION  —  BG = (non-insulin NIE trajectory) + (insulin effect)\n'
             'A ~5 h meal window: insulin holds BG in range against a rise that would otherwise run off the top')
ax.legend(loc='upper left',fontsize=8); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(G+'/decomposition.png',bbox_inches='tight'); plt.close()

# ---------- 4. Sensitivity inference m(t): residual -> m ----------
# find a window with a m>1 cluster
mwin=d[(d.m>1.2)]
if len(mwin):
    c=mwin.t.iloc[len(mwin)//2]; w0=c-pd.Timedelta(hours=3); w1=c+pd.Timedelta(hours=3)
else:
    w0=pd.Timestamp('2025-09-04',tz=tz); w1=w0+pd.Timedelta(hours=6)
seg=d[(d.t>=w0)&(d.t<w1)].reset_index(drop=True)
fig,(ax,axm)=plt.subplots(2,1,figsize=(9,5),sharex=True,gridspec_kw={'height_ratios':[2,1]})
ax.plot(seg.t, seg.bg,'-',color='#1565c0',lw=2,label='BG (smoothed)')
ax.axhline(70,color='#c62828',lw=0.6,ls='--'); ax.set_ylabel('BG (mg/dL)')
ax.set_title('SENSITIVITY INFERENCE — when BG drops faster than scheduled insulin explains, infer higher sensitivity m(t)')
ax.legend(fontsize=8,loc='upper right')
axm.fill_between(seg.t, 1.0, seg.m, where=seg.m>1.0, color='#7b1fa2',alpha=0.4)
axm.plot(seg.t, seg.m,'-',color='#7b1fa2',lw=1.8)
axm.axhline(1.0,color='#888',lw=0.8); axm.axhline(2.0,color='#888',lw=0.6,ls=':')
axm.set_ylabel('m(t)  (ISF×)'); axm.set_ylim(0.9,2.15); axm.annotate('cap 2.0',(seg.t.iloc[1],2.02),fontsize=7,color='#555')
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(G+'/sensitivity.png',bbox_inches='tight'); plt.close()

# ---------- 5. Closed-loop counterfactual example: actual vs candidate counters ----------
def counter(path):
    t=json.load(open(path)); a=pd.DataFrame(t['counter']); a['t']=pd.to_datetime(a['t']).dt.tz_convert(tz); return a.dropna(subset=['bg'])
san=counter(A+'/nbnc_af040.json')          # hands-off sanity (ISF x1.0)
agg=counter(A+'/nbnc_isf_m070.json')        # aggressive ISF x0.70
w0=pd.Timestamp('2025-09-10',tz=tz); w1=w0+pd.Timedelta(days=2)
def cut(x): return x[(x.t>=w0)&(x.t<w1)]
fig,ax=plt.subplots(figsize=(10,4))
ax.plot(cut(ac).t, cut(ac).bg,'.',color='#ccc',ms=3,label='real CGM')
ax.plot(cut(san).t, cut(san).bg,'-',color='#1565c0',lw=1.6,label='counter: hands-off sanity (ISF×1.0)')
ax.plot(cut(agg).t, cut(agg).bg,'-',color='#c62828',lw=1.6,label='counter: aggressive ISF×0.70')
ax.axhline(70,color='#c62828',lw=0.5,ls='--'); ax.axhline(180,color='#ef6c00',lw=0.5,ls='--')
ax.set_ylabel('BG (mg/dL)'); ax.set_title('CLOSED-LOOP COUNTERFACTUAL — each candidate is a fully independent BG trajectory (same NIE substrate, different insulin decisions)')
ax.legend(loc='upper right',fontsize=8); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(G+'/counterfactual.png',bbox_inches='tight'); plt.close()
print('wrote: pd_curve, substrate, decomposition, sensitivity, counterfactual')
