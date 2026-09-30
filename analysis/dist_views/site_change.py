#!/usr/bin/env python3
"""Insulin and glucose over the life of an infusion site (twiist).

twiist uploads a `prime` deviceEvent (target=cannula) at every site change and a
`reservoirChange` with 91% of them, so site age is known to the minute. Omnipod via
Loop uploads neither, which is why this is twiist-only.

Site age = hours since the last cannula prime (primes within 3 h merged). Every
5-minute sample gets an age; statistics are then taken by age.

Changes cluster in the evening (17:00-22:00), so site age and time of day are
confounded, and insulin and glucose both have strong daily rhythms. Every quantity
is therefore adjusted for the person's own time-of-day profile: the value at an
age is compared with that person's usual value AT THAT LOCAL HOUR. 1.0 (or 0 for
differences) means "typical for this person at this time of day".

Writes site_age.csv (per person x age bin) and figure 29.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S
from loopeval_analysis import dists as D

MERGE_H, MAX_AGE = 3.0, 96.0

def site_changes() -> pd.DataFrame:
    d = pd.read_pickle(S.OUT/"twiist_changes.pkl")
    p = d[d.subType.eq("prime")].copy()
    p["gap"] = p.groupby("alias").t.diff().dt.total_seconds()/3600
    return p[p.gap.isna() | (p.gap > MERGE_H)][["alias","t","volume"]]

def person(alias, ch):
    c = S.load(alias)                               # unclean: keeps the change-time gap visible
    if c is None or len(c) < 5000: return None
    tot = (c.basal_eff/12 + c.bolus_u.fillna(0)).rename("dl")
    auto = (c.basal_eff/12 + c.auto_bolus_u.fillna(0)).rename("auto")
    f = pd.DataFrame({"bg": c.bg, "dl": tot, "auto": auto, "hour": (c.tod_min//60).astype(int)})
    # work in hours since epoch: tz-aware timestamps turn into object arrays otherwise
    th = f.index.tz_convert("UTC").asi8 / 3.6e12
    ts = np.sort(ch.t.dt.tz_convert("UTC").astype("int64").to_numpy() / 3.6e12)
    i = np.searchsorted(ts, th, side="right") - 1
    f["age"] = np.where(i >= 0, th - ts[np.clip(i, 0, None)], np.nan)
    f["to_next"] = np.where(i + 1 < len(ts), ts[np.clip(i + 1, 0, len(ts) - 1)] - th, np.nan)
    # time-of-day adjustment, per person
    for col in ("dl","auto","bg"):
        hm = f.groupby("hour")[col].transform("mean"); m = f[col].mean()
        f[col+"_adj"] = f[col] - hm + m
    f["dl_rel"]   = f.dl_adj / f.dl.mean()            # 1 = this person's usual rate at this hour
    f["auto_rel"] = f.auto_adj / f.auto.mean()
    f["bg_dev"]   = f.bg_adj - f.bg.mean()            # mg/dL above this person's usual at this hour
    f["inr"] = f.bg.between(70,180).astype(float)
    f["inr_adj"] = f.inr - f.groupby("hour").inr.transform("mean") + f.inr.mean()
    f["alias"] = alias
    return f

def main():
    ch = site_changes(); co = S.cohort()
    frames = []
    for a in co[co.pump.eq("twiist")].alias:
        c_ = ch[ch.alias.eq(a)]
        if len(c_) < 5: continue
        f = person(a, c_)
        if f is not None: frames.append(f)
    F = pd.concat(frames)
    F.to_pickle(S.OUT/"site_age_samples.pkl")
    print(f"{F.alias.nunique()} twiist people, {len(ch)} site changes")
    # day-of-site summary, per person then across people
    X = F[F.age.between(0, MAX_AGE)].copy()
    X["day"] = pd.cut(X.age, [0,24,48,72,96], labels=["day 1","day 2","day 3","day 4"], right=False)
    per = X.groupby(["alias","day"], observed=True).agg(n=("bg","size"), dl_rel=("dl_rel","mean"),
          auto_rel=("auto_rel","mean"), bg_dev=("bg_dev","mean"), tir=("inr_adj","mean"))
    per["tir"] *= 100; per = per[per.n >= 200].reset_index()
    per.to_csv(S.OUT/"site_age.csv", index=False)
    print("\nby day of site (median across people; time-of-day adjusted):")
    print(per.groupby("day", observed=True)[["dl_rel","auto_rel","bg_dev","tir"]].median().round(3).to_string())
    print("people per day:", per.groupby("day", observed=True).alias.nunique().to_dict())
    from scipy.stats import wilcoxon
    W = per.pivot(index="alias", columns="day", values=["dl_rel","bg_dev","tir"])
    for m_ in ("dl_rel","bg_dev","tir"):
        for d2 in ("day 3","day 4"):
            s = W[m_][["day 1", d2]].dropna()
            if len(s) >= 8:
                x = s[d2] - s["day 1"]
                print(f"  {m_:7s} {d2} - day 1: median {x.median():+.3f}  n={len(s)}  p={wilcoxon(x).pvalue:.4f}")
    return F

if __name__ == "__main__" and "--fig" not in sys.argv:
    main()


def f29():
    """Figure 29: what a site change does, and whether a site wears out."""
    F = pd.read_pickle(S.OUT/"site_age_samples.pkl")
    ch = site_changes().sort_values(["alias","t"])
    ch["prev_age"] = ch.groupby("alias").t.diff().dt.total_seconds()/3600
    ch["kind"] = np.where(ch.prev_age < 48, "early", "routine")
    rows = []
    for al, g in ch.dropna(subset=["prev_age"]).groupby("alias"):
        f = F[F.alias.eq(al)]
        if not len(f): continue
        th = f.index.tz_convert("UTC").asi8/3.6e12
        for _, e in g.iterrows():
            t0 = e.t.value/3.6e12; m = (th >= t0-12) & (th < t0+30)
            if m.sum() < 200: continue
            rows.append(f.loc[m, ["bg_dev","dl_rel"]].assign(rel=np.floor((th[m]-t0)*2)/2, alias=al, kind=e.kind))
    R = pd.concat(rows).groupby(["kind","alias","rel"]).mean().reset_index()
    fig, ax = S.figure(1, 3, figsize=(15.4, 5.0))
    COL = {"routine": S.COOL, "early": S.ACCENT}
    LAB = {"routine": f"routine change (old site ≥ 48 h), n={int((ch.kind=='routine').sum())}",
           "early": f"early change (old site < 48 h), n={int((ch.kind=='early').sum())}"}
    for k in ("routine","early"):
        g = R[R.kind.eq(k)].groupby("rel")
        for A, col in ((ax[0], "bg_dev"), (ax[1], "dl_rel")):
            med, lo, hi = g[col].median(), g[col].quantile(.25), g[col].quantile(.75)
            A.plot(med.index, med, color=COL[k], lw=2.3, label=LAB[k], zorder=4)
            A.fill_between(med.index, lo, hi, color=COL[k], alpha=.13, lw=0, zorder=2)
    for A in ax[:2]:
        A.axvline(0, color=S.INK, lw=1.2, ls=(0,(4,2))); A.set_xlim(-12, 30)
        A.set_xlabel("hours from the site change", fontsize=9.5, color=S.INK2); S.axes(A)
    ax[0].axhline(0, color=S.MUTED, lw=1)
    ax[0].set_ylabel("glucose vs this person's usual at that hour (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[0].set_title("Glucose around a site change", fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    ax[0].legend(frameon=False, fontsize=8, labelcolor=S.INK2, loc="upper right")
    ax[1].axhline(1, color=S.MUTED, lw=1)
    ax[1].set_ylabel("insulin delivered ÷ usual at that hour", fontsize=9.5, color=S.INK2)
    ax[1].set_title("Insulin around a site change", fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    # life course, routine sites, first 6 h excluded
    X = F[F.age.between(6, 96) & ((F.age + F.to_next) >= 48)].copy()
    X["b"] = (X.age // 6) * 6 + 3
    P = X.groupby(["alias","b"]).agg(n=("bg","size"), bg=("bg_dev","mean")).reset_index()
    P = P[P.n >= 36]
    g = P.groupby("b").bg
    ax[2].plot(g.median().index, g.median(), color=S.INK, lw=2.3, marker="o", ms=4, zorder=4)
    ax[2].fill_between(g.median().index, g.quantile(.25), g.quantile(.75), color=S.MUTED, alpha=.18, lw=0)
    ax[2].axhline(0, color=S.MUTED, lw=1)
    for x in (24, 48, 72): ax[2].axvline(x, color=S.MUTED, lw=.8, ls=(0,(2,3)))
    ax[2].set_xlabel("site age (hours), routine sites, first 6 h left out", fontsize=9.5, color=S.INK2)
    ax[2].set_ylabel("glucose vs usual at that hour (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[2].set_title("Does a site wear out?", fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")
    S.axes(ax[2])
    S.title(fig, "29 · Infusion-site changes (twiist)",
            f"{F.alias.nunique()} twiist users, {len(ch)} site changes, each recorded by the pump. Everything is compared with the same person at the same hour of day. "
            "A routine change costs\nabout six hours of higher glucose (peak roughly +28 mg/dL) as the set is disconnected and re-primed. A quarter of changes "
            "come early, after glucose has been\nclimbing for hours without insulin delivery rising — the signature of a failing site. Between changes, glucose "
            "shows no drift from day 1 to day 4.")
    S.save(fig, "29_site_change", dict(left=0.05, right=0.99, top=0.745, bottom=0.12, wspace=0.27))

if __name__ == "__main__" and "--fig" in sys.argv:
    f29()
