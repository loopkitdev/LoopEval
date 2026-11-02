"""Does the ICE labeller recover the TRUE appearance shape? Only this role can ask: for a twin we know `truth.ra`,
the true rate of glucose appearance, so the labeller's `peak_h` / `dur_h` can be checked against it.

This matters for the open question of L 617-622 — why matching the donors' measured appearance dispersion costs TIR.
The labeller infers appearance from ICE, which is glucose change minus a MODELLED insulin effect, so a labelled
"appearance" difference can be an insulin-model difference. If the labeller distorts the twins' pulse shape in a
known direction, then the donors' labels are distorted the same way and a labelled-to-labelled comparison is still
fair - but a labelled target must not be used to calibrate the BODY's appearance.

For each non-rescue labelled pulse, inside [onset, onset + 4 h]:
  true peak    = argmax of true `ra` (minutes from onset, as the labeller's peak_h is onset-relative; L 595)
  true dur     = minutes until the cumulative true appearance in the window reaches 90% (fit_shapes' dur_h
                 convention is the lognormal's 90th percentile)
Both sides are then medians per person, then across people, as the scorer does.

    python label_vs_truth.py <run> [...] [--n N]
"""
import sys, pickle, numpy as np, pandas as pd
from pathlib import Path

EPOCH = pd.Timestamp("2026-01-05", tz="UTC")
W = 240          # minutes of window
args = [a for a in sys.argv[1:] if not a.startswith("--")]
NMAX = 10 ** 9
ISO = "--all" not in sys.argv
if "--n" in sys.argv:
    NMAX = int(sys.argv[sys.argv.index("--n") + 1])

print(f"{'ISOLATED pulses only' if ISO else 'ALL pulses (overlap-confounded)'}")
print(f"{'arm':>10} {'people':>7} {'pulses':>7} "
      f"{'peak_h lab':>11} {'peak_h TRUE':>12} {'dur_h lab':>10} {'dur_h TRUE':>11}")
for run in args:
    rows = []
    for d in sorted(Path(run).glob("v*"))[:NMAX]:
        f = d / "meals_labeled.csv"
        if not f.exists():
            continue
        try:
            ml = pd.read_csv(f)
            tr = pickle.load(open(d / "truth.pkl", "rb"))
        except Exception:
            continue
        if "rescue" in ml.columns:
            ml = ml[~ml.rescue.astype(bool)]
        if ml.empty:
            continue
        T = tr["truth"]
        tm = T.m.to_numpy(float); ra = T.ra.to_numpy(float)
        on = ((pd.to_datetime(ml.onset, utc=True) - EPOCH).dt.total_seconds() / 60).to_numpy()
        pk_l, pk_t, du_l, du_t = [], [], [], []
        ons = np.sort(on)
        for o, phl, dhl in zip(on, ml.peak_h.to_numpy(float), ml.dur_h.to_numpy(float)):
            if ISO:
                # ISOLATED pulses only: a later pulse inside the window can own the true-ra argmax and the
                # cumulative 90%, which would fake an instrument bias entirely
                j = np.searchsorted(ons, o, "right")
                if j < len(ons) and ons[j] - o < W:
                    continue
                k = np.searchsorted(ons, o - W, "left")
                if k < np.searchsorted(ons, o, "left"):
                    continue
            i0 = int(np.searchsorted(tm, o)); i1 = int(np.searchsorted(tm, o + W))
            if i1 - i0 < 60:
                continue
            seg = ra[i0:i1]
            if not np.isfinite(seg).all() or seg.max() <= 0:
                continue
            c = np.cumsum(seg)
            pk_l.append(phl * 60); pk_t.append(float(np.argmax(seg)))
            du_l.append(dhl * 60); du_t.append(float(np.searchsorted(c, 0.9 * c[-1])))
        if len(pk_l) < 3:
            continue
        rows.append((np.median(pk_l), np.median(pk_t), np.median(du_l), np.median(du_t), len(pk_l)))
    if not rows:
        print(f"{Path(run).name:>10}   nothing measurable")
        continue
    R = np.array(rows)
    print(f"{Path(run).name:>10} {len(R):>7} {int(R[:,4].sum()):>7} "
          f"{np.median(R[:,0]):>9.1f}m {np.median(R[:,1]):>11.1f}m "
          f"{np.median(R[:,2]):>9.1f}m {np.median(R[:,3]):>10.1f}m")
print("\nThe donors' labels are the LABELLED column's analogue; their truth is unobservable. A systematic")
print("labelled-vs-true offset here is the instrument, and it applies to the donor side too.")
