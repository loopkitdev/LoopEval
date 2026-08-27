#!/usr/bin/env python3
"""View 13 — is the shape of the glucose distribution a within-day fact?

Pooling two months of readings mixes days with very different mean levels.
A mixture of narrow, well-behaved distributions with drifting centres looks
fat-tailed and skewed when you pool it. That would be a completely different
explanation for the shape in view 01 than "glucose is intrinsically lognormal",
and it has different consequences, so it is worth separating.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                      # noqa: E402
import style as S                                    # noqa: E402
import fundamentals as F                             # noqa: E402
from loopeval_analysis import dists as D             # noqa: E402


def daily(panel: pd.DataFrame) -> pd.DataFrame:
    c = D.clean(panel)
    day = c.index.tz_convert("UTC").floor("D")
    g = c.groupby(day)["bg"]
    out = pd.DataFrame({"n": g.size(), "mean": g.mean(), "sd": g.std(),
                        "skew": g.skew(),
                        "tir": g.apply(lambda s: 100 * s.between(70, 180).mean())})
    return out[out["n"] >= 200]              # ≥ ~70% of a day


def f13_mixture(panels, co):
    order = S.order_by(co, "tir")
    fig, ax = S.figure(2, 3, figsize=(14.4, 9.0))

    # 1 — variance decomposition: between-day vs within-day.
    rows = []
    for a in order:
        d = daily(panels[a])
        if len(d) < 10:
            continue
        c = D.clean(panels[a])
        tot = c["bg"].var()
        between = np.average((d["mean"] - c["bg"].mean()) ** 2, weights=d["n"])
        rows.append({"alias": a, "between": between / tot,
                     "n_days": len(d), "sd_of_daily_mean": d["mean"].std(),
                     "mean_daily_sd": d["sd"].mean()})
    R = pd.DataFrame(rows).sort_values("between")
    y = np.arange(len(R))
    ax[0][0].barh(y, R["between"], color=[S.color_for(co, a) for a in R["alias"]],
                  alpha=0.88, height=0.72)
    if len(R) > 30:
        ax[0][0].set_yticks([])
        ax[0][0].set_ylabel(f"{len(R)} people, sorted", fontsize=9, color=S.INK2)
    else:
        ax[0][0].set_yticks(y)
        ax[0][0].set_yticklabels(R["alias"], fontsize=8, color=S.INK2)
        for yi, b in zip(y, R["between"]):
            ax[0][0].text(b + 0.005, yi, f"{b*100:.0f}%", va="center", fontsize=7.8,
                          color=S.INK2)
    ax[0][0].set_xlim(0, max(0.35, R["between"].max() * 1.25))
    med = float(R["between"].median())
    ax[0][0].axvline(med, color=S.INK, lw=1.4, ls=(0, (4, 2)))
    ax[0][0].text(med + 0.005, 1, f"median {med*100:.0f}%", fontsize=8.5, color=S.INK)
    ax[0][0].set_xlabel("share of total glucose variance that is between-day",
                        fontsize=9.5, color=S.INK2)
    ax[0][0].set_title("Most variance is within the day, not between days",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 2 — pooled vs within-day-centred: does the skew survive?
    for a in order:
        c = D.clean(panels[a])
        day = c.index.tz_convert("UTC").floor("D")
        bg = c["bg"]
        centred = bg - bg.groupby(day).transform("mean")
        col = S.color_for(co, a)
        for A, x in ((ax[0][1], bg), (ax[0][2], centred)):
            th, xs = F.qq_points(x.to_numpy(), "normal")
            z = (xs - xs.mean()) / xs.std()
            A.plot(th, z, **S.line_style(co, a))
    for A, ttl in ((ax[0][1], "Pooled over the whole window"),
                   (ax[0][2], "After removing each day's own mean")):
        A.plot([-4, 4], [-4, 4], color=S.INK, lw=1.5, ls=(0, (4, 2)))
        A.set_xlim(-4, 4)
        A.set_ylim(-4, 6)
        A.set_xlabel("normal quantile", fontsize=9.5, color=S.INK2)
        A.set_ylabel("standardised sample quantile", fontsize=9.5, color=S.INK2)
        A.set_title(ttl, fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 3 — every day, from everyone: mean against spread.
    for a in order:
        d = daily(panels[a])
        ax[1][0].scatter(d["mean"], d["sd"], s=11, color=S.color_for(co, a),
                         alpha=0.5, lw=0)
    alld = pd.concat([daily(panels[a]) for a in order])
    m, s_ = alld["mean"].to_numpy(), alld["sd"].to_numpy()
    ok = np.isfinite(m) & np.isfinite(s_)
    fit = np.polyfit(m[ok], s_[ok], 1)
    xs = np.linspace(m[ok].min(), m[ok].max(), 50)
    ax[1][0].plot(xs, np.polyval(fit, xs), color=S.INK, lw=2.0, ls=(0, (4, 2)),
                  label=f"slope {fit[0]:.2f}  (r={np.corrcoef(m[ok], s_[ok])[0,1]:.2f})")
    ax[1][0].set_xlabel("that day's mean glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1][0].set_ylabel("that day's SD (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1][0].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="upper left")
    ax[1][0].set_title(f"{ok.sum()} person-days: higher days are also wider days",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 4 — the coefficient of variation is the stable quantity.
    ax[1][1].scatter(m[ok], 100 * s_[ok] / m[ok], s=11, color=S.MUTED, alpha=0.4, lw=0)
    for a in order:
        d = daily(panels[a])
        ax[1][1].scatter(d["mean"].mean(), 100 * (d["sd"] / d["mean"]).mean(),
                         s=70, color=S.color_for(co, a), edgecolor=S.SURFACE,
                         lw=1.3, zorder=4)
    cv = 100 * s_[ok] / m[ok]
    ax[1][1].axhline(np.median(cv), color=S.INK, lw=1.8, ls=(0, (4, 2)),
                     label=f"median CV {np.median(cv):.0f}%")
    ax[1][1].axhline(36, color=S.ACCENT, lw=1.5, ls=(0, (2, 2)),
                     label="36% — the usual stability threshold")
    ax[1][1].set_xlabel("that day's mean glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    ax[1][1].set_ylabel("that day's CV (%)", fontsize=9.5, color=S.INK2)
    ax[1][1].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="upper right")
    ax[1][1].set_title("Large dots are people; CV is flat in the level",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    # 5 — day-to-day memory of the daily mean.
    for a in order:
        d = daily(panels[a]).sort_index()
        x = d["mean"].to_numpy()
        if len(x) < 20:
            continue
        x = x - x.mean()
        nl = min(14, len(x) // 3)
        ac = [float((x[k:] * x[:-k]).mean() / x.var()) if k else 1.0
              for k in range(nl + 1)]
        ax[1][2].plot(np.arange(nl + 1), ac, **S.line_style(co, a))
    ax[1][2].axhline(0, color=S.INK, lw=1.2)
    ax[1][2].set_xlabel("lag (days)", fontsize=9.5, color=S.INK2)
    ax[1][2].set_ylabel("autocorrelation of daily mean glucose", fontsize=9.5,
                        color=S.INK2)
    ax[1][2].set_title("A bad day predicts the next day, weakly",
                       fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    S.title(fig, "13 · Is the shape a within-day fact, or an artefact of pooling days?",
            "It is mostly a within-day fact. Only about a fifth of glucose variance is between-day, and removing each day's own mean barely "
            "straightens the Q-Q plot — the right\ntail is there inside single days. What days do differ in is level, and higher days are "
            "proportionally wider, which is why the coefficient of variation is the stable summary.")
    S.save(fig, "13_mixture",
           dict(left=0.06, right=0.985, top=0.885, bottom=0.075, hspace=0.42, wspace=0.28))
    return R


def main():
    co = S.cohort()
    panels = S.load_all()
    f13_mixture(panels, co)


if __name__ == "__main__":
    main()
