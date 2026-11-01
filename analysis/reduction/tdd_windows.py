"""How variable is TDD over longer averaging windows? Pilot ice_v32 donors, clean local days from ice steps
(>= 90 % of 5-min steps, no unrecorded delivery), on the calendar (missing days stay missing).
For each window w days:
  spread  within each person, the CV of the w-day average over non-overlapping w-day blocks (a block counts when
          >= 80 % of its days are clean); median and IQR across people. Reference: the daily CV / sqrt(w), what
          the spread would be if days were independent around a fixed level (the gap above it is slow drift).
  predict |next 14-day mean / previous w-day mean - 1| at every cut point with both windows >= 80 % clean;
          median per person, then median and IQR across people. This is Loop Adaptive's use (w = 14 now).
usage: ~/.venv/bin/python3 tdd_windows.py <out dir>"""
import glob, os, sys
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
W = [1, 2, 3, 5, 7, 10, 14, 21, 28, 42, 56]

def days(p):
    s = pd.read_parquet(p, columns=["dt", "basal_u", "bolus_auto_u", "bolus_manual_u", "local_day", "unrecorded"])
    g = s.assign(u=s.basal_u + s.bolus_auto_u + s.bolus_manual_u).groupby("local_day").agg(u=("u", "sum"), m=("dt", "sum"), bad=("unrecorded", "any"))
    g.index = pd.to_datetime(g.index, unit="D"); g = g.asfreq("D")   # local_day = days since 1970-01-01
    return g.u.where((g.m >= 0.9 * 1440) & ~g.bad.astype("boolean").fillna(True).astype(bool) & (g.u > 0))

rows = []
for p in sorted(glob.glob(os.path.expanduser("~/.loop-eval/ice/steps/i*.parquet"))):
    u = days(p)
    if u.notna().sum() < 84: continue
    a = os.path.basename(p)[:-8]; cv1 = u.std() / u.mean()
    for w in W:
        n = len(u) // w; b = u.iloc[:n * w].to_numpy().reshape(n, w)
        ok = np.isfinite(b).sum(1) >= 0.8 * w
        bm = np.nanmean(b[ok], 1) if ok.sum() else np.array([])
        spread = bm.std(ddof=1) / bm.mean() if len(bm) >= 3 else np.nan
        past = u.rolling(w, min_periods=int(np.ceil(0.8 * w))).mean()
        fut = u[::-1].rolling(14, min_periods=12).mean()[::-1].shift(-1)
        e = (fut / past - 1).abs().dropna()
        rows.append(dict(alias=a, w=w, spread=spread, ref=cv1 / np.sqrt(w), pred=e.median() if len(e) >= 10 else np.nan))
T = pd.DataFrame(rows); out = sys.argv[1]; T.to_csv(f"{out}/tdd_windows.csv", index=False)
S = T.groupby("w").agg(sp50=("spread", "median"), sp25=("spread", lambda x: x.quantile(.25)), sp75=("spread", lambda x: x.quantile(.75)),
                       ref=("ref", "median"), pr50=("pred", "median"), pr25=("pred", lambda x: x.quantile(.25)), pr75=("pred", lambda x: x.quantile(.75)),
                       n_sp=("spread", "count"), n_pr=("pred", "count")) * 1
for c in ("sp50", "sp25", "sp75", "ref", "pr50", "pr25", "pr75"): S[c] *= 100
print(f"donors {T.alias.nunique()}"); print(S.round(1).to_string())

BLUE, INK, INK2, GRID, SURF = "#2a78d6", "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4), facecolor=SURF)
for a_, (m, lo, hi, title, sub) in zip(ax, [("sp50", "sp25", "sp75", "How much the average itself moves",
                                              "within-person CV of the w-day average TDD"),
                                             ("pr50", "pr25", "pr75", "How well it predicts the next 14 days",
                                              "|next 14-day TDD / previous w-day TDD − 1|")]):
    a_.set_facecolor(SURF)
    a_.fill_between(S.index, S[lo], S[hi], color=BLUE, alpha=0.15, lw=0)
    a_.plot(S.index, S[m], color=BLUE, lw=2, marker="o", ms=5, mec=SURF, mew=1.5, label="median person (band: middle half)")
    if m == "sp50":
        a_.plot(S.index, S.ref, color=INK2, lw=1.5, ls="--", label="if days varied independently around a fixed level")
    a_.set_xscale("log"); a_.set_xticks(W); a_.set_xticklabels(W)
    a_.set_xlabel("averaging window w (days)", color=INK2); a_.set_ylabel("%", color=INK2)
    a_.set_ylim(0, None); a_.grid(True, color=GRID, lw=0.8); a_.set_axisbelow(True)
    for s in ("top", "right"): a_.spines[s].set_visible(False)
    for s in ("left", "bottom"): a_.spines[s].set_color(GRID)
    a_.tick_params(colors=INK2)
    a_.set_title(title, loc="left", color=INK, fontsize=12, fontweight="bold", pad=18)
    a_.text(0, 1.02, sub, transform=a_.transAxes, color=INK2, fontsize=9)
    a_.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper right")
    k = 14; a_.annotate(f"{S.loc[k, m]:.0f}% at 14 d", (k, S.loc[k, m]), xytext=(6, 8), textcoords="offset points", color=INK, fontsize=9)
fig.text(0.01, 0.005, f"{T.alias.nunique()} pilot donors, ~125 clean days each, total daily insulin delivered under Loop (basal + automatic + manual).",
         color=INK2, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f"{out}/tdd_windows.png", dpi=160, facecolor=SURF)
