#!/usr/bin/env python3
"""i05 — the distribution of ICE per person (absolute insulin, scheduled ISF).

Every five-minute step and the 30-minute centred mean, non-disrupted steps only.
Writes ice/ice_dist.csv (per-person quantiles and shape) and figs/i05_dist.png.
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa

H = 12
GRID = np.linspace(-400, 900, 521)
QS = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]


def person(alias):
    p = S.load(alias)
    ok = p["v"].notna().to_numpy() & ~p["disrupted"].astype(bool).to_numpy()
    raw = (p["ice_abs"] * H).where(ok)
    sm = raw.rolling(6, center=True, min_periods=6).mean()
    quiet = _quiet_mask(p)
    out = {"alias": alias}
    for name, x in (("raw", raw.to_numpy()), ("sm", sm.to_numpy())):
        x = x[np.isfinite(x)]
        q = np.quantile(x, QS)
        out.update({f"{name}_q{int(k*100):02d}": v for k, v in zip(QS, q)})
        out[f"{name}_mean"] = x.mean(); out[f"{name}_sd"] = x.std()
        out[f"{name}_neg"] = (x < 0).mean()
        z = (x - x.mean()) / x.std()
        out[f"{name}_skew"] = (z ** 3).mean(); out[f"{name}_kurt"] = (z ** 4).mean() - 3
    s = sm.to_numpy()
    out["sm_fast_med"] = np.nanmedian(s[quiet]); out["sm_fed_med"] = np.nanmedian(s[~quiet & ok])
    dens = {k: S.kde(x[np.isfinite(x)], GRID, bw=8.0)
            for k, x in (("raw", raw.to_numpy()), ("sm", s))}
    return out, dens


def main():
    co = S.cohort()
    with Pool(8) as pool:
        res = pool.map(person, list(co.alias))
    d = pd.DataFrame([r[0] for r in res])
    d.to_csv(S.OUT / "ice" / "ice_dist.csv", index=False)
    dens = {a: r[1] for a, r in zip(co.alias, res)}

    fig = S.plt.figure(figsize=(13, 10.5))
    fig.patch.set_facecolor(S.SURFACE)
    gs = fig.add_gridspec(2, 2, hspace=0.38, wspace=0.2, height_ratios=[1, 1.15])
    ax = [S.axes(fig.add_subplot(gs[0, i])) for i in range(2)]
    for a in co.alias:
        st = S.line_style(co, a, lw=1.3)
        ax[0].plot(GRID, dens[a]["sm"], **st)
        ax[1].plot(GRID, dens[a]["sm"], **st)
    for a_, key, ttl, log in ((ax[0], "sm", "30-minute mean", False),
                              (ax[1], "sm", "The same, log scale: the tails", True)):
        med = np.median(np.vstack([dens[a][key] for a in co.alias]), axis=0)
        a_.plot(GRID, med, color=S.INK, lw=2.2, zorder=6)
        a_.axvline(0, color=S.INK2, lw=0.8)
        a_.set_xlim(-250, 600)
        if log:
            a_.set_yscale("log"); a_.set_ylim(1e-6, 3e-2)
        else:
            a_.set_ylim(0, None)
        a_.set_yticks([]); a_.minorticks_off()
        a_.set_xlabel("ICE, mg/dL per hour", fontsize=8.5, color=S.INK2)
        a_.set_title(ttl if log else ttl + f" · median {d[key+'_q50'].median():.0f}, "
                     f"below zero {d[key+'_neg'].median():.0%} of the time",
                     loc="left", fontsize=10.5, color=S.INK)
    # per-person quantile rows, sorted by median
    a_ = S.axes(fig.add_subplot(gs[1, :]))
    o = d.sort_values("sm_q50").reset_index(drop=True)
    y = np.arange(len(o))
    cols = [S.color_for(co, a) for a in o.alias]
    a_.hlines(y, o.sm_q01, o.sm_q99, color=S.MUTED, lw=0.6, alpha=0.6)
    a_.hlines(y, o.sm_q10, o.sm_q90, color=cols, lw=1.6, alpha=0.55)
    a_.hlines(y, o.sm_q25, o.sm_q75, color=cols, lw=3.2, alpha=0.95)
    a_.scatter(o.sm_q50, y, s=9, color=S.INK, zorder=5)
    a_.scatter(o.sm_fast_med, y, s=9, marker="|", color=S.ACCENT, zorder=6)
    a_.axvline(0, color=S.INK2, lw=0.8)
    a_.set_yticks([]); a_.set_xlim(-200, 700); a_.set_ylim(-1, len(o))
    a_.set_xlabel("ICE, 30-minute mean, mg/dL per hour", fontsize=8.5, color=S.INK2)
    a_.set_title("One row per person, sorted by median · thin p1–p99, mid p10–p90, thick p25–p75, "
                 "black dot median, orange tick fasting median", loc="left", fontsize=10.5, color=S.INK)
    S.title(fig, "The distribution of ICE, person by person",
            f"{len(d)} people, absolute insulin at the scheduled ISF, non-disrupted steps. "
            "Faint grey lines are people, coloured lines the representative sample, black the median density.")
    S.save(fig, "i05_dist", tight=dict(left=0.03, right=0.98, top=0.88, bottom=0.06))
    print(d[["raw_q50", "raw_sd", "raw_neg", "raw_skew", "raw_kurt", "sm_q01", "sm_q10", "sm_q50",
             "sm_q90", "sm_q99", "sm_sd", "sm_neg", "sm_skew", "sm_kurt", "sm_fast_med", "sm_fed_med"]]
          .describe(percentiles=[.1, .5, .9]).T[["10%", "50%", "90%"]].round(2).to_string())


if __name__ == "__main__":
    main()
