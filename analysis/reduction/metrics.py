"""Outcome metrics for one compacted step table (runs/2026-10-23-frontier-dosing/dr/compact.py: t, bg, fbg, cob, iob,
auto, manual, excl). Disruption intervals are excluded from glucose metrics; insulin counts every step."""
import numpy as np, pandas as pd

def risk(bg):
    """Kovatchev LBGI / HBGI (mg/dL)."""
    f = 1.509 * (np.log(np.clip(bg, 20, 600)) ** 1.084 - 5.381)
    r = 10 * f ** 2
    return float(np.mean(np.where(f < 0, r, 0))), float(np.mean(np.where(f > 0, r, 0)))

def iob_at_cross(bg, iob, thr=54):
    b = bg.values; i = iob.values
    k = np.where((b[1:] < thr) & (b[:-1] >= thr))[0] + 1
    return (float(np.nanmean(i[k])) if len(k) else np.nan), len(k)

def stats(s):
    k = s[~s.excl & s.bg.notna()]; bg = k.bg
    days = (s.t.iloc[-1] - s.t.iloc[0]) / pd.Timedelta(days=1)
    lb, hb = risk(bg.values)
    ins = s.auto + s.manual
    ic, nc = iob_at_cross(k.bg, k.iob)
    a = s.auto.values
    return dict(tir=bg.between(70, 180).mean() * 100, t70=(bg < 70).mean() * 100, t54=(bg < 54).mean() * 100,
                t180=(bg > 180).mean() * 100, t250=(bg > 250).mean() * 100, mean=bg.mean(), cv=bg.std() / bg.mean() * 100,
                lbgi=lb, hbgi=hb, ins=ins.sum() / days, auto=s.auto.sum() / days, manual=s.manual.sum() / days,
                big1=(a > 1.0).sum() / days, big2=(a > 2.0).sum() / days, p99_auto=float(np.percentile(a, 99)),
                tv=float(np.abs(np.diff(a)).mean()), iob54=ic, n54=nc / days,
                ftir=k.fbg.between(70, 180).mean() * 100, ft70=(k.fbg < 70).mean() * 100, ft54=(k.fbg < 54).mean() * 100)
