#!/usr/bin/env python3
"""Do observable temporal modalities explain the increment's excess kurtosis?

The increment is fat-tailed (excess kurtosis ~3-4, view 09) and a causal
volatility estimator removes about 40% of that (view 14). The open question is
what the volatility is MADE of: if it is mostly the person alternating between
known modalities — eating, sleeping — then the tail is a mixture artefact of
pooling states we can name in advance, and the state is observable rather than
latent.

Two ways of asking, both per person, both on the cached raw increments (the
same test-split set view 14 scores, so the numbers are comparable):

1. CONDITION. Divide each increment by the SD of its own state cell (time of
   day x carb state) and see how much excess kurtosis survives. This is
   generous to the modality story: cell SDs are fitted in sample, so it is an
   upper bound on what a schedule could remove.
2. LOOK INSIDE ONE MODALITY. Take the calmest, most homogeneous state there
   is — asleep, no carbs on board, no recent meal — and measure the excess
   kurtosis inside it. No pooling across modalities happens there at all.

State comes from the 5-minute panel (COB, local time of day) joined to the raw
increment's own timestamp. The INCREMENTS are raw, never the panel's
interpolated ones (lesson 1); the panel supplies state only.

Writes modality_kurtosis.csv.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import style as S                                          # noqa: E402
import vol_cache as VC                                     # noqa: E402

warnings.filterwarnings("ignore")

MIN_CELL = 200          # an SD or a kurtosis needs this many increments
NIGHT = (0, 360)        # local 00:00-06:00, the sleep proxy
QUIET_H = 240           # minutes since the last carb entry to count as fasted


def excess_kurtosis(x) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(pd.Series(x).kurtosis()) if len(x) >= MIN_CELL else np.nan


def standardise_by_cell(eps, cell) -> np.ndarray:
    """Divide each increment by the SD of its own cell. Cells too small to
    estimate an SD from are dropped rather than pooled into a default."""
    out = np.full(len(eps), np.nan)
    for c in np.unique(cell):
        m = cell == c
        if m.sum() < MIN_CELL:
            continue
        sd = eps[m].std()
        if sd > 0:
            out[m] = eps[m] / sd
    return out[np.isfinite(out)]


def state_frame(alias: str) -> pd.DataFrame | None:
    """Raw increments with the modality state that was current when each landed."""
    d = VC.load(alias)
    if not d:
        return None
    t = pd.to_datetime(np.asarray(d["t"])).tz_localize("UTC")
    eps = np.asarray(d["eps"], dtype=float)

    panel = S.load(alias)
    if panel is None or not len(panel):
        return None
    # State is whatever was already true at the increment's own time: take the
    # panel row at or before it, never after.
    cols = [c for c in ("cob", "tod_min", "disrupted", "bg", "ia_abs")
            if c in panel.columns]
    st = panel[cols].reindex(t, method="ffill", tolerance=pd.Timedelta("10min"))

    f = pd.DataFrame({"eps": eps, "t": t})
    for c in cols:
        f[c] = st[c].to_numpy()
    if "cob" not in f:
        return None
    f = f[np.isfinite(f["eps"]) & f["cob"].notna() & f["tod_min"].notna()]
    if "disrupted" in f:
        f = f[~f["disrupted"].fillna(False).astype(bool)]

    # Minutes since the last carb entry, from the panel's COB stream: COB
    # rising means an entry landed on that step.
    cob = panel["cob"].fillna(0.0)
    entry = cob.index[(cob.diff() > 0.5).to_numpy()]
    if len(entry):
        # tz-aware Series.to_numpy() is object dtype and will not subtract.
        tv = f["t"].dt.tz_localize(None).to_numpy()
        ev = entry.tz_localize(None).to_numpy()
        idx = np.searchsorted(ev, tv, side="right") - 1
        since = np.where(idx >= 0,
                         (tv - ev[np.clip(idx, 0, None)]) / np.timedelta64(1, "m"),
                         np.inf)
    else:
        since = np.full(len(f), np.inf)
    f["since_carb"] = since
    f["night"] = ((f["tod_min"] >= NIGHT[0]) & (f["tod_min"] < NIGHT[1])).astype(int)
    f["fed"] = (f["cob"] > 0).astype(int)
    f["tod8"] = (f["tod_min"] // 180).astype(int)
    # Insulin action is a modality too, and an observable one: tertiles of
    # absorbed insulin activity at the time of the increment.
    if "ia_abs" in f:
        ia = f["ia_abs"].astype(float)
        q = ia.quantile([1 / 3, 2 / 3]).to_numpy()
        f["ia3"] = np.digitize(ia.to_numpy(), q)
    else:
        f["ia3"] = 0
    return f


def person_row(alias: str) -> dict | None:
    f = state_frame(alias)
    if f is None or len(f) < 2000:
        return None
    eps = f["eps"].to_numpy()
    k_raw = excess_kurtosis(eps)
    if not np.isfinite(k_raw) or k_raw >= 20:      # sensor-spike records
        return None

    cells = {
        "k_night": f["night"].to_numpy(),
        "k_fed": f["fed"].to_numpy(),
        "k_night_fed": (f["night"] * 2 + f["fed"]).to_numpy(),
        "k_tod8": f["tod8"].to_numpy(),
        "k_tod8_fed": (f["tod8"] * 2 + f["fed"]).to_numpy(),
        "k_all3": (f["tod8"] * 6 + f["fed"] * 3 + f["ia3"]).to_numpy(),
    }
    row = {"alias": alias, "n": len(f), "k_raw": k_raw}
    for name, c in cells.items():
        row[name] = excess_kurtosis(standardise_by_cell(eps, c))

    # The latent benchmark: the causal volatility estimator on the same set.
    d = VC.load(alias)
    sig = np.asarray(d["ewma"], dtype=float)
    e_all = np.asarray(d["eps"], dtype=float)
    ok = np.isfinite(sig) & (sig > 0) & np.isfinite(e_all)
    row["k_ewma"] = excess_kurtosis(e_all[ok] / sig[ok])

    # Inside one modality, no pooling at all.
    fasted = (f["fed"] == 0) & (f["since_carb"] > QUIET_H)
    quiet = (f["night"] == 1) & fasted
    row["k_quiet"] = excess_kurtosis(eps[quiet.to_numpy()])
    row["n_quiet"] = int(quiet.sum())
    row["k_day_fasted"] = excess_kurtosis(eps[((f["night"] == 0) & fasted).to_numpy()])
    row["k_day_fed"] = excess_kurtosis(eps[((f["night"] == 0) & (f["fed"] == 1)).to_numpy()])
    # Nights carry an artefact days do not: lying on the sensor produces
    # compression lows, whose recovery is a burst the person never had. Redo
    # the quiet state away from the low range to see whether it survives.
    if "bg" in f:
        hi = quiet & (f["bg"] >= 80)
        row["k_quiet_hi"] = excess_kurtosis(eps[hi.to_numpy()])
        row["n_quiet_hi"] = int(hi.sum())
        row["frac_night_low"] = float((f.loc[quiet, "bg"] < 70).mean()) if quiet.any() else np.nan

    # How much of the increment's SCALE the modality explains: R² of eps² on
    # the cell mean of eps² (the same target view 14's estimators are scored on).
    s2 = eps ** 2
    for name, c in (("r2_night_fed", cells["k_night_fed"]),
                    ("r2_tod8_fed", cells["k_tod8_fed"]),
                    ("r2_all3", cells["k_all3"])):
        pred = pd.Series(s2).groupby(c).transform("mean").to_numpy()
        row[name] = float(1 - np.mean((s2 - pred) ** 2) / np.mean((s2 - s2.mean()) ** 2))
    # The same R² for the causal estimator, so the two are comparable: predict
    # the squared increment from sigma² known before it. (Scored on the same
    # increments; vol_scores' r2_logvar is a different target and cannot be
    # read against this one.)
    ok2 = np.isfinite(sig) & (sig > 0) & np.isfinite(e_all)
    se, ss = e_all[ok2] ** 2, sig[ok2] ** 2
    row["r2_ewma"] = float(1 - np.mean((se - ss) ** 2) / np.mean((se - se.mean()) ** 2))
    row["sd_night"] = float(eps[(f["night"] == 1).to_numpy()].std())
    row["sd_day"] = float(eps[(f["night"] == 0).to_numpy()].std())
    row["sd_fed"] = float(eps[(f["fed"] == 1).to_numpy()].std())
    row["sd_fasted"] = float(eps[(f["fed"] == 0).to_numpy()].std())
    row["frac_fed"] = float((f["fed"] == 1).mean())
    return row


def main() -> None:
    rows = []
    for alias in S.cohort()["alias"]:
        try:
            r = person_row(alias)
        except Exception as e:                    # noqa: BLE001
            print(f"  ! {alias}: {type(e).__name__} {e}")
            continue
        if r:
            rows.append(r)
            print(f"  {alias:8s} n={r['n']:6d} raw={r['k_raw']:5.2f} "
                  f"tod8xfed={r['k_tod8_fed']:5.2f} ewma={r['k_ewma']:5.2f} "
                  f"quiet={r['k_quiet']:5.2f} (n={r['n_quiet']})")
    df = pd.DataFrame(rows)
    co = S.cohort().set_index("alias")
    df["group"] = [S.group_of(co.loc[a]) if a in co.index else "" for a in df["alias"]]
    df.to_csv(S.OUT / "modality_kurtosis.csv", index=False)

    def med(c):
        v = df[c].dropna()
        return f"{v.median():5.2f}  [{v.quantile(.1):5.2f}, {v.quantile(.9):5.2f}]  n={len(v)}"

    print(f"\n{len(df)} people. Excess kurtosis, median [p10, p90]:")
    for c, lab in (("k_raw", "raw increment"),
                   ("k_night", "/ SD(night vs day)"),
                   ("k_fed", "/ SD(carbs on board vs not)"),
                   ("k_night_fed", "/ SD(night x carbs)"),
                   ("k_tod8", "/ SD(8 x 3h of day)"),
                   ("k_tod8_fed", "/ SD(8 x 3h x carbs)"),
                   ("k_all3", "/ SD(8 x 3h x carbs x insulin)"),
                   ("k_ewma", "/ causal EWMA sigma")):
        print(f"  {lab:32s} {med(c)}")
    print("\nWithin one modality, unstandardised:")
    for c, lab in (("k_quiet", "night, fasted >4h, COB=0"),
                   ("k_quiet_hi", "  same, only BG >= 80"),
                   ("k_day_fasted", "daytime, fasted >4h, COB=0"),
                   ("k_day_fed", "daytime, carbs on board")):
        print(f"  {lab:32s} {med(c)}")
    print(f"  share of quiet-state samples below 70: "
          f"{df['frac_night_low'].median():.1%} median")

    print("\nBy behaviour group (COB is only meaningful where carbs are announced):")
    for g, sub in df.groupby("group"):
        if len(sub) < 3:
            continue
        share = (1 - sub["k_tod8_fed"] / sub["k_raw"]).median()
        ew = (1 - sub["k_ewma"] / sub["k_raw"]).median()
        print(f"  {g or 'unknown':20s} n={len(sub):3d}  carbs announced on "
              f"{sub['frac_fed'].median():4.0%} of samples  "
              f"modality removes {share:+.0%}  EWMA {ew:+.0%}")
    print("\nShare of the increment's squared scale explained by the modality:")
    for c, lab in (("r2_night_fed", "night x carbs"), ("r2_tod8_fed", "8 x 3h x carbs"),
                   ("r2_all3", "8 x 3h x carbs x insulin"), ("r2_ewma", "causal EWMA sigma²")):
        print(f"  {lab:32s} {med(c)}")
    print("\nSD ratios (median):",
          f"night/day {(df['sd_night'] / df['sd_day']).median():.2f},",
          f"fed/fasted {(df['sd_fed'] / df['sd_fasted']).median():.2f}")
    figure(df)
    print("\nremoved by conditioning, as a share of raw excess kurtosis:")
    for c, lab in (("k_night_fed", "night x carbs"), ("k_tod8_fed", "8 x 3h x carbs"),
                   ("k_all3", "8 x 3h x carbs x insulin"), ("k_ewma", "causal EWMA")):
        share = 1 - df[c] / df["k_raw"]
        print(f"  {lab:32s} {share.median():.0%}  [{share.quantile(.1):.0%}, {share.quantile(.9):.0%}]")


# ────────────────────────────────────────────────────────────────────────────
# 24 — the figure: does a named state explain the tail?
# ────────────────────────────────────────────────────────────────────────────
def _paired(ax, df, cols, labels, ylabel, colors):
    """One faint line per person across the conditions, medians marked. Shows
    the per-person CHANGE, which grouped bars cannot (lesson 17)."""
    import matplotlib.pyplot as plt                          # noqa: F401
    rng = np.random.default_rng(5)
    X = np.arange(len(cols))
    V = df[list(cols)].to_numpy(dtype=float)
    jit = rng.uniform(-0.05, 0.05, len(V))
    for i, row in enumerate(V):
        m = np.isfinite(row)
        ax.plot(X[m] + jit[i], row[m], color=S.MUTED, lw=0.6, alpha=0.30, zorder=1)
    for j, (x, c) in enumerate(zip(X, colors)):
        v = V[:, j][np.isfinite(V[:, j])]
        ax.scatter(np.full(len(v), x) + jit[:len(v)], v, s=15, color=c, alpha=0.6,
                   lw=0, zorder=2)
        lo, med, hi = np.percentile(v, [10, 50, 90])
        ax.plot([x - 0.24, x + 0.24], [med, med], color=S.INK, lw=2.6, zorder=4)
        ax.plot([x, x], [lo, hi], color=S.INK, lw=2.0, alpha=0.22, zorder=3)
        ax.text(x + 0.28, med, f"{med:.2f}", fontsize=9, color=S.INK, weight="bold",
                va="center", ha="left", zorder=5)
    ax.set_xticks(X)
    ax.set_xticklabels(labels, fontsize=8.5, color=S.INK2)
    ax.set_xlim(-0.5, len(cols) - 0.3)
    ax.set_ylabel(ylabel, fontsize=9.5, color=S.INK2)


def figure(df: pd.DataFrame) -> None:
    co = S.cohort()
    fig, ax = S.figure(1, 3, figsize=(14.4, 5.4))

    _paired(ax[0], df, ("k_raw", "k_all3", "k_ewma"),
            ["raw\nincrement", "÷ SD of its\nnamed state", "÷ causal\nvolatility σ"],
            "excess kurtosis", [S.INK2, S.GREEN, S.COOL])
    ax[0].axhline(0, color=S.MUTED, lw=1.3, ls=(0, (4, 2)))
    ax[0].text(0.995, 0, "Gaussian ", fontsize=7.5, color=S.MUTED, va="bottom",
               ha="right", transform=ax[0].get_yaxis_transform())
    ax[0].set_ylim(-0.5, 12)
    ax[0].set_title("A named state removes none of the tail",
                    fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    _paired(ax[1], df, ("k_day_fed", "k_day_fasted", "k_quiet"),
            ["daytime,\ncarbs on board", "daytime, fasted\n>4 h", "night, fasted\n>4 h"],
            "excess kurtosis inside the state", [S.ACCENT, S.WARM, S.COOL])
    ax[1].axhline(0, color=S.MUTED, lw=1.3, ls=(0, (4, 2)))
    ax[1].set_ylim(-0.5, 14)
    ax[1].set_title("The calmest state has the fattest tail",
                    fontsize=10.5, color=S.INK, loc="left", pad=6, weight="bold")

    _paired(ax[2], df, ("r2_all3", "r2_ewma"),
            ["named state\n(clock × carbs × insulin)", "causal volatility σ²"],
            "share of the squared increment explained", [S.GREEN, S.COOL])
    ax[2].set_ylim(-0.02, 0.45)
    ax[2].set_title("And little of the scale", fontsize=10.5, color=S.INK,
                    loc="left", pad=6, weight="bold")

    n = len(df)
    S.title(fig, "24 · The tail is not a mixture of meals and nights",
            "Every increment carries the state it happened in — local time of day, whether carbs were on board, how much insulin was acting. If the fat tail "
            f"came from pooling those states,\ndividing each increment by the spread of its OWN state would remove it. Across {n} people it removes nothing "
            "(median excess kurtosis 2.71 raw, 2.88 conditioned), while the same increments\nconditioned on recent volatility — a latent quantity, not a "
            "named one — lose about a quarter of it. Read the middle panel for why: the fat tail is not where the eating is.")
    S.save(fig, "24_modality", dict(left=0.055, right=0.985, top=0.70, bottom=0.135, wspace=0.30))


if __name__ == "__main__":
    main()
