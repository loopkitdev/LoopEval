#!/usr/bin/env python3
"""Does volatility LEAD a low, or FOLLOW it?

The case studies suggest the mechanism's premise is inverted: sigma is an EWMA of
recent absolute increments, and the largest increments occur DURING a steep fall
and its rebound — so by the time sigma is high, the excursion has already
happened. A controller acting on it then suppresses dosing into the recovery,
which costs TIR and prevents nothing.

This tests that directly by averaging the sigma profile around every downward
crossing of 70 mg/dL. If sigma peaks at or after the crossing, the signal is
diagnostic rather than predictive and no amount of gain tuning will fix it.

Run on the STOCK counterfactual's crossings, with sigma taken from the candidate
arm, so the events are not contaminated by the mechanism's own dosing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                              # noqa: E402
import style as S                                            # noqa: E402
import vsb_episodes as EP                                    # noqa: E402

LEADS = np.arange(-36, 37)          # +/- 3 h in 5-min steps


def crossings(bg: pd.Series, thresh: float = 70.0) -> pd.DatetimeIndex:
    below = bg < thresh
    onset = below & ~below.shift(1, fill_value=False)
    return bg.index[onset.fillna(False)]


def profile(donor: str, needs: str, k: str = "1.0"):
    st, cd = EP.load(donor, "0", needs), EP.load(donor, k, needs)
    if st is None or cd is None:
        return None
    fs, bgs = EP.frame(st)
    fc, _ = EP.frame(cd)
    sig = fc["sigma"].where(fc["sigma"] > 0).dropna()
    if sig.empty:
        return None
    grid = pd.date_range(sig.index.min(), sig.index.max(), freq="5min")
    sg = sig.reindex(grid, method="nearest", tolerance=pd.Timedelta("3min"))
    bgg = bgs.reindex(grid, method="nearest", tolerance=pd.Timedelta("3min"))
    z = (sg - sg.mean()) / sg.std()

    ev = crossings(bgg.dropna())
    pos = grid.get_indexer(ev, method="nearest")
    S_, B_ = [], []
    for p in pos:
        lo, hi = p + LEADS[0], p + LEADS[-1] + 1
        if lo < 0 or hi > len(grid):
            continue
        S_.append(z.to_numpy()[lo:hi])
        B_.append(bgg.to_numpy()[lo:hi])
    if len(S_) < 20:
        return None
    return dict(donor=donor, needs=needs, n=len(S_),
                sigma=np.nanmean(np.array(S_), axis=0),
                bg=np.nanmean(np.array(B_), axis=0))


def main() -> int:
    runs = []
    for donor in ("bddp11", "bddp10"):
        for needs in ("1.00", "1.05", "1.10"):
            r = profile(donor, needs)
            if r:
                runs.append(r)
    if not runs:
        print("no traces")
        return 1

    fig, ax = S.figure(1, 2, figsize=(13.4, 5.4))
    x = LEADS * 5
    print(f"{'bed':<9}{'needs':>6}{'events':>8}{'σ peak at':>12}{'σ at −60m':>11}"
          f"{'σ at 0':>9}{'σ at +30m':>11}")
    for r in runs:
        col = "#3b6ea5" if r["donor"] == "bddp11" else S.ACCENT
        ax[0].plot(x, r["sigma"], color=col, lw=1.6, alpha=0.85,
                   label=f"{r['donor']} ×{r['needs']} (n={r['n']})")
        ax[1].plot(x, r["bg"], color=col, lw=1.6, alpha=0.85)
        peak = x[int(np.nanargmax(r["sigma"]))]
        at = lambda m: r["sigma"][int(np.where(x == m)[0][0])]
        print(f"{r['donor']:<9}{r['needs']:>6}{r['n']:>8}{peak:>+11.0f}m"
              f"{at(-60):>11.2f}{at(0):>9.2f}{at(30):>11.2f}")

    for A, ylab, ttl in (
            (ax[0], "σ, standardised (SD units)",
             "Volatility around a downward crossing of 70"),
            (ax[1], "glucose (mg/dL)", "The crossings themselves")):
        A.axvline(0, color=S.INK, lw=1.4, ls=(0, (4, 2)))
        A.set_xlabel("minutes relative to crossing 70 mg/dL", fontsize=9.5, color=S.INK2)
        A.set_ylabel(ylab, fontsize=9.5, color=S.INK2)
        A.set_title(ttl, fontsize=11, color=S.INK, loc="left", pad=7, weight="bold")
    ax[0].axhline(0, color=S.MUTED, lw=1.0)
    ax[0].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="upper left")
    ax[1].axhline(70, color=S.GREEN, lw=1.1, ls=(0, (3, 3)))

    S.title(fig, "Volatility is a lagging indicator of a low, not a leading one",
            "Mean σ profile around every downward crossing of 70 mg/dL on the stock counterfactual. If σ peaked BEFORE the crossing it could be "
            "acted on; it peaks at or after it,\nbecause σ measures the size of moves that have already happened — the steep fall and its rebound. "
            "A controller keyed on it withholds insulin during the recovery.")
    S.save(fig, "16_leadlag")
    import shutil
    shutil.copy(S.FIG / "16_leadlag.png", EP.RUN / "leadlag.png")
    print(f"\nwrote {EP.RUN}/leadlag.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
