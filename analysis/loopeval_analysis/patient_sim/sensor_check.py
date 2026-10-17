"""The sensor model as a whole against the FDA iCGM accuracy tables (evidence/08 §1.4).

Pairs each simulated CGM reading with true glucose at the same minute, on a 15-min grid during daytime
(clinic sessions), and reports bias and MARD/MAD by range, binned by the comparator (true) and by the CGM
value, per sensor family. The FDA G7 adult arm (K213919, YSI comparator) is the reference.

    python -m loopeval_analysis.patient_sim.sensor_check <cohort-root> [...]
"""
from __future__ import annotations

import glob
import pickle
import sys

import numpy as np
import pandas as pd

EDGES = [0, 54, 70, 181, 251, 1000]
LABELS = ["<54", "54-69", "70-180", "181-250", ">250"]
FDA_G7 = {  # comparator-binned: bias, MARD (%) ; CGM-binned <54: bias -9.3, MARD 16.0; 54-69: -2.3, 9.1
    "true": {"<54": (4.0, 14.0), "54-69": (1.1, 10.7), "70-180": (1.1, 8.6), "181-250": (-1.9, 7.4), ">250": (-6.6, 6.4)},
    "cgm": {"<54": (-9.3, 16.0), "54-69": (-2.3, 9.1)},
}


def pairs(root: str) -> pd.DataFrame:
    out = []
    for d in sorted(glob.glob(root + "/v0*")):
        tr = pickle.load(open(d + "/truth.pkl", "rb"))
        fam = pickle.load(open(d + "/person.pkl", "rb")).sensor
        T = tr["truth"]; bg = pd.Series(T.bg.to_numpy(), index=T.m.to_numpy())
        c = tr["cgm"].dropna()
        c = c[(c.index >= 1800) & ((c.index % 1440) >= 8 * 60) & ((c.index % 1440) < 20 * 60)]
        c = c[(c.index.astype(int) % 15) < 5]                    # ~15-min reference spacing
        out.append(pd.DataFrame(dict(cgm=c.to_numpy(), true=bg.reindex(c.index).to_numpy(), sensor=fam)))
    return pd.concat(out).dropna()


def table(p: pd.DataFrame, by: str) -> pd.DataFrame:
    p = p[(p.cgm > 39) & (p.cgm < 401)]
    p = p.assign(bin=pd.cut(p[by], EDGES, labels=LABELS, right=False), err=p.cgm - p.true)
    g = p.groupby("bin", observed=True)
    return pd.DataFrame(dict(n=g.size(), bias=g.err.mean(), mard=100 * g.apply(lambda x: (x.err.abs() / x.true).mean()),
                             mad=g.err.apply(lambda e: e.abs().mean()),
                             p15=100 * g.apply(lambda x: np.mean(np.where(x.true < 100, x.err.abs() <= 15, x.err.abs() <= 0.15 * x.true)))))


def main():
    p = pd.concat([pairs(r) for r in sys.argv[1:]])
    pd.set_option("display.width", 200)
    for fam, q in p.groupby("sensor"):
        for by in ("true", "cgm"):
            t = table(q, by)
            ref = FDA_G7.get(by, {})
            t["fda_g7_bias"] = [ref.get(b, (np.nan, np.nan))[0] for b in t.index]
            t["fda_g7_mard"] = [ref.get(b, (np.nan, np.nan))[1] for b in t.index]
            print(f"\n{fam} — binned by {by}"); print(t.round(2).to_string())
        mid = {"<54": 45, "54-69": 62, "70-180": 125, "181-250": 215, ">250": 310}
        t = table(q, "true"); t = t[t.index.isin(["54-69", "70-180", "181-250", ">250"])]
        el = np.polyfit(np.log([mid[b] for b in t.index]), np.log(t.mad), 1)[0]
        print(f"{fam}: MAD elasticity {el:.2f} (FDA G7 0.69)")


if __name__ == "__main__":
    main()
