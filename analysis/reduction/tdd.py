"""Pre-window TDD: mean daily delivered insulin (basal + automatic + manual boluses, absolute) over the `days` local
days before `w0`, from ice's gap-checked step table (~/.loop-eval/ice/steps, ice_gen/extract.py). Days with < 90 %
of 5-min intervals present, or with any interval whose delivery can't be told, are left out.
The raw doses.json can't be summed directly: scheduled basal that ran is implicit in it (AGENTS.md trap)."""
import os
import pandas as pd
STEPS = os.path.expanduser("~/.loop-eval/ice/steps")

def tdd(alias, w0, days=14):
    s = pd.read_parquet(f"{STEPS}/{alias}.parquet", columns=["t0", "dt", "basal_u", "bolus_auto_u", "bolus_manual_u", "local_day", "unrecorded"])
    w0 = pd.Timestamp(w0); w0 = w0.tz_localize("UTC") if w0.tzinfo is None else w0
    s = s[(s.t0 < w0) & (s.t0 >= w0 - pd.Timedelta(days=days + 1))]
    s = s.assign(u=s.basal_u + s.bolus_auto_u + s.bolus_manual_u)
    g = s.groupby("local_day").agg(u=("u", "sum"), mins=("dt", "sum"), bad=("unrecorded", "any"))
    g = g[(g.mins >= 0.9 * 1440) & ~g.bad].tail(days)
    return float(g.u.mean()) if len(g) else float("nan"), len(g)

def basal_hat(alias, w0, days=14, q=0.5):
    """Pre-window background rate (U/h): the q-quantile over clean clock hours of automatic delivery (basal + automatic
    boluses; manual boluses left out), same 14 days and day filter as tdd()."""
    s = pd.read_parquet(f"{STEPS}/{alias}.parquet", columns=["t0", "dt", "basal_u", "bolus_auto_u", "local_day", "unrecorded"])
    w0 = pd.Timestamp(w0); w0 = w0.tz_localize("UTC") if w0.tzinfo is None else w0
    s = s[(s.t0 < w0) & (s.t0 >= w0 - pd.Timedelta(days=days + 1))]
    s = s.assign(u=s.basal_u + s.bolus_auto_u, hr=s.t0.dt.floor("h"))
    g = s.groupby("hr").agg(u=("u", "sum"), mins=("dt", "sum"), bad=("unrecorded", "any"))
    g = g[(g.mins >= 54) & ~g.bad]
    return float(g.u.quantile(q)) if len(g) else float("nan")
