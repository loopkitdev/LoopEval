#!/usr/bin/env python3
"""Case studies: what the volatility band actually did, episode by episode.

Four situations, picked automatically and plotted as representatives:

  HELPED    sigma spiked, the stock arm went low, the candidate did not
  FALSE     sigma spiked, no low was coming, the candidate withheld anyway
  MISSED    the stock arm went low with no sigma spike — the mechanism was blind
  FIRED-ANYWAY  sigma spiked, the candidate withheld, and it went low regardless

Both arms are counterfactuals of the same donor at the same dial setting, so the
only difference between the lines is the mechanism. The field trace is shown for
orientation only — it is a different dosing history and is NOT the comparison.

Dose panel convention (AGENTS.md): bars are DELIVERED insulin from each arm's
`delivery[]` stream, never recommendations, and the two streams are never mixed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                              # noqa: E402
import matplotlib.dates as mdates                            # noqa: E402
import style as S                                            # noqa: E402
import vsb_episodes as EP                                    # noqa: E402

RUN = EP.RUN
LOW, SEVERE = EP.LOW, EP.SEVERE
WIN_BEFORE = pd.Timedelta("2h")
WIN_AFTER = pd.Timedelta("4h")


def delivered(trace: dict, source: str) -> pd.Series:
    d = [x for x in trace["delivery"] if x.get("source") == source]
    if not d:
        return pd.Series(dtype=float)
    t = pd.to_datetime([x["t"] for x in d], utc=True, format="ISO8601")
    return pd.Series([float(x["amountU"]) for x in d], index=t).sort_index()


def counter_bg(trace: dict) -> pd.Series:
    c = pd.DataFrame(trace["counter"])
    c["t"] = pd.to_datetime(c["t"], utc=True, format="ISO8601")
    return c.set_index("t")["bg"].dropna()


def field_bg(trace: dict) -> pd.Series:
    a = pd.DataFrame(trace["actual"])
    a["t"] = pd.to_datetime(a["t"], utc=True, format="ISO8601")
    key = "bg" if "bg" in a.columns else a.columns[-1]
    return a.set_index("t")[key].dropna()


def pick_episodes(donor: str, needs: str, k: str = "1.0"):
    st, cd = EP.load(donor, "0", needs), EP.load(donor, k, needs)
    if st is None or cd is None:
        return None
    fs, bgs = EP.frame(st)
    fc, bgc = EP.frame(cd)
    sig = fc["sigma"].where(fc["sigma"] > 0)
    thresh = sig.quantile(EP.SPIKE_Q)

    fmin_s = EP.forward_min(bgs, EP.LOOKAHEAD_MIN).reindex(
        fc.index, method="nearest", tolerance=pd.Timedelta("3min"))
    fmin_c = EP.forward_min(bgc, EP.LOOKAHEAD_MIN).reindex(
        fc.index, method="nearest", tolerance=pd.Timedelta("3min"))
    ok = sig.notna() & fmin_s.notna() & fmin_c.notna()

    # A spike ONSET: sigma crosses the threshold having been below it, so the
    # episode starts where the mechanism first has something to say.
    above = (sig >= thresh) & ok
    onset = above & ~above.shift(1, fill_value=False)

    lowS = (fmin_s < LOW) & ok
    lowC = (fmin_c < LOW) & ok
    cats = {
        "HELPED": onset & lowS & ~lowC,
        "FALSE": onset & ~lowS & ~lowC,
        "FIRED-ANYWAY": onset & lowS & lowC,
        # blind: a low arrives with sigma in its BOTTOM half and no recent onset
        "MISSED": lowS & ~lowC.isna() & (sig <= sig.quantile(0.5)) & ok
                  & ~lowS.shift(1, fill_value=False),
    }
    out = {}
    for name, mask in cats.items():
        idx = list(fc.index[mask.fillna(False)])
        if not idx:
            continue
        # rank by how deep the stock arm went, so the representative is a real
        # event rather than a marginal one
        depth = fmin_s.reindex(idx)
        order = depth.sort_values().index if name != "FALSE" else \
            pd.Index(idx)[np.argsort(-sig.reindex(idx).to_numpy())]
        out[name] = list(order)[:4]
    return dict(fs=fs, fc=fc, bgs=bgs, bgc=bgc, st=st, cd=cd,
                sig=sig, thresh=float(thresh), cats=out)


def plot_case(D, t0: pd.Timestamp, name: str, donor: str, needs: str, out: Path):
    lo, hi = t0 - WIN_BEFORE, t0 + WIN_AFTER
    sl = lambda s: s.loc[(s.index >= lo) & (s.index <= hi)]

    fig, ax = S.figure(4, 1, figsize=(11.6, 10.2), sharex=True,
                       gridspec_kw={"height_ratios": [3.0, 1.5, 1.5, 1.4]})

    # ── glucose ──
    A = ax[0]
    A.axhspan(70, 180, color=S.GREEN, alpha=0.07, lw=0)
    A.axhline(LOW, color=S.GREEN, lw=1.0, ls=(0, (3, 3)))
    A.axhline(SEVERE, color=S.ACCENT, lw=1.1, ls=(0, (2, 2)))
    A.plot(sl(field_bg(D["cd"])).index, sl(field_bg(D["cd"])).to_numpy(),
           color=S.MUTED, lw=1.2, alpha=0.55, label="field (different dosing — context only)")
    A.plot(sl(D["bgs"]).index, sl(D["bgs"]).to_numpy(), color="#3b6ea5", lw=2.2,
           label="stock counterfactual (k=0)")
    A.plot(sl(D["bgc"]).index, sl(D["bgc"]).to_numpy(), color=S.ACCENT, lw=2.2,
           label="volatility band (k=1)")
    A.axvline(t0, color=S.INK, lw=1.3, ls=(0, (4, 2)))
    A.set_ylabel("glucose (mg/dL)", fontsize=9.5, color=S.INK2)
    A.legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="upper right", ncol=2)
    A.set_title(f"{name} · {donor} · needs ×{needs} · spike onset {t0:%Y-%m-%d %H:%M} UTC",
                fontsize=11.5, color=S.INK, loc="left", pad=8, weight="bold")

    # ── sigma ──
    B = ax[1]
    s = sl(D["sig"])
    B.plot(s.index, s.to_numpy(), color="#7c4fe0", lw=1.8)
    B.axhline(D["thresh"], color=S.INK, lw=1.2, ls=(0, (4, 2)),
              label=f"spike threshold (p{int(EP.SPIKE_Q*100)}) = {D['thresh']:.1f}")
    B.axvline(t0, color=S.INK, lw=1.3, ls=(0, (4, 2)))
    B.set_ylabel("σ  (mg/dL / 5 min)", fontsize=9.5, color=S.INK2)
    B.legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="upper right")

    # ── band offset ──
    C = ax[2]
    bb = sl(D["fc"]["band"].where(D["fc"]["band"] > -0.5))
    C.fill_between(bb.index, 0, bb.to_numpy(), color=S.ACCENT, alpha=0.35, lw=0)
    C.plot(bb.index, bb.to_numpy(), color=S.ACCENT, lw=1.5)
    C.axhline(0, color=S.INK, lw=1.0)
    C.axvline(t0, color=S.INK, lw=1.3, ls=(0, (4, 2)))
    C.set_ylabel("forecast bent\ndown (mg/dL)", fontsize=9.5, color=S.INK2)

    # ── delivered insulin, per arm, never mixed ──
    E = ax[3]
    for src, trace, col, lbl in (("candidate", D["st"], "#3b6ea5", "stock arm delivered"),
                                 ("candidate", D["cd"], S.ACCENT, "band arm delivered")):
        dl = sl(delivered(trace, src))
        if dl.empty:
            continue
        cum = dl.cumsum()
        E.step(cum.index, cum.to_numpy(), where="post", color=col, lw=1.9, label=lbl)
    E.axvline(t0, color=S.INK, lw=1.3, ls=(0, (4, 2)))
    E.set_ylabel("cumulative U\nDELIVERED", fontsize=9.5, color=S.INK2)
    E.legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="upper left")
    E.set_xlabel("time (UTC)", fontsize=9.5, color=S.INK2)
    E.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    E.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    fig.subplots_adjust(left=0.085, right=0.985, top=0.945, bottom=0.065, hspace=0.16)
    fig.savefig(out, dpi=150, facecolor=S.SURFACE)
    plt.close(fig)
    print(f"  wrote {out.name}")


def main() -> int:
    outdir = RUN / "cases"
    outdir.mkdir(parents=True, exist_ok=True)
    donor, needs = "bddp11", "1.05"
    D = pick_episodes(donor, needs)
    if D is None:
        print("traces missing")
        return 1
    print(f"{donor} needs ×{needs}, spike threshold σ = {D['thresh']:.2f}")
    for name, times in D["cats"].items():
        print(f"  {name}: {len(times)} candidates")
        for i, t0 in enumerate(times[:2]):
            plot_case(D, t0, name, donor, needs,
                      outdir / f"{donor}_{needs}_{name.lower().replace('-','_')}_{i+1}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
