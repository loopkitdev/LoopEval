"""Do insulin needs follow the day of the week? Per pilot donor, clean local days (>=90 % of 5-min steps, no
unrecorded delivery) from ice steps: daily insulin (TDD) and mean CGM by weekday. Weekend/weekday TDD ratio and
mean-glucose difference; one-way ANOVA of log TDD on weekday (share of donors with p < 0.05, ~5 % expected by
chance). Run: ~/.venv/bin/python3 weekday.py"""
import os, glob
import numpy as np, pandas as pd
from scipy import stats
rows = []
for p in sorted(glob.glob(os.path.expanduser("~/.loop-eval/ice/steps/i*.parquet"))):
    s = pd.read_parquet(p, columns=["alias", "dt", "bg1", "basal_u", "bolus_auto_u", "bolus_manual_u", "carbs_g", "dow", "local_day", "unrecorded"])
    s = s.assign(u=s.basal_u + s.bolus_auto_u + s.bolus_manual_u)
    g = s.groupby("local_day").agg(u=("u", "sum"), mins=("dt", "sum"), bad=("unrecorded", "any"), bg=("bg1", "mean"), dow=("dow", "first"), carbs=("carbs_g", "sum"))
    g = g[(g.mins >= 0.9 * 1440) & ~g.bad & (g.u > 0)]
    if len(g) < 42: continue
    we = g.dow >= 5
    groups = [np.log(g.u[g.dow == d]) for d in range(7) if (g.dow == d).sum() >= 3]
    rows.append(dict(alias=s.alias.iloc[0], days=len(g), tdd=g.u.mean(), we_ratio=g.u[we].mean() / g.u[~we].mean(),
                     dbg=g.bg[we].mean() - g.bg[~we].mean(), carb_ratio=(g.carbs[we].mean() / g.carbs[~we].mean()) if g.carbs[~we].mean() > 0 else np.nan,
                     p=stats.f_oneway(*groups).pvalue if len(groups) == 7 else np.nan,
                     dow_spread=np.exp(np.ptp([x.mean() for x in groups]))))
T = pd.DataFrame(rows); T.to_csv("weekday.csv", index=False)
print(f"donors {len(T)}, median clean days {T.days.median():.0f}; dow convention check: {sorted(s.dow.unique())}")
print("weekend/weekday TDD ratio: median %.3f, IQR %.3f-%.3f; share outside +/-10%%: %.0f%%" % (T.we_ratio.median(), *T.we_ratio.quantile([.25, .75]), 100 * ((T.we_ratio < 0.9) | (T.we_ratio > 1.1)).mean()))
print("weekend - weekday mean CGM: median %+.1f mg/dL, IQR %+.1f..%+.1f" % (T.dbg.median(), *T.dbg.quantile([.25, .75])))
print("weekday ANOVA on log TDD: p<0.05 in %.0f%% of donors (5%% by chance); p<0.01 in %.0f%%" % (100 * (T.p < 0.05).mean(), 100 * (T.p < 0.01).mean()))
print("largest - smallest weekday mean TDD (ratio): median %.2f" % T.dow_spread.median())
print(T[T.p < 0.01].sort_values("p")[["alias", "days", "tdd", "we_ratio", "dbg", "carb_ratio", "p", "dow_spread"]].round(3).to_string(index=False))
