"""Compression-low (pressure-artifact) detector on one donor's step table (`extract`).

Signature: a sudden break from the prior level / trend, then a return to that level and trend. Three branches,
because the sensor shows the artifact three ways:

  gap    the reading slides below a near-flat prior trend, the sensor then WITHHOLDS readings (its own
         algorithm flags the data), and readings resume back on the trend. The commonest form.
  floor  the reading pins at the sensor's LOW limit (<= 40), entered by a sudden fall from a near-flat trend
         and left by a jump back to the old level. ICE is meaningless while pinned, so judged on glucose.
  ice    no gap, no floor: a fall that insulin does not explain (ICE well below its background), then a sharp
         return onto the old level and trend with no overshoot.

Every window is grown to the whole artifact: back over the slide in, forward over the release (the readings
leading into the floor or the gap are part of the drop). Thresholds were tuned on the ICE pilot against a mirror
control (sudden RISES that return, which physiology rarely makes): gap-branch precision about 0.75 at a 40 mg/dL
slide; the strict ICE branch about 0.5 overall, higher overnight. Deliberately on the strict side: some real
compression is missed. Review sheets: runs/2026-10-11-ice-compression/.

`artifacts(df)` returns one row per window: start, end, branch, depth (mg/dL), hour. `flag(df)` marks steps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FLOOR = 40.5
# ice branch
A, DMIN, F, TMAX, B, BASE_MIN, POST_MIN, SEG_GAP = 60.0, 20.0, 0.3, 180.0, 60.0, 60.0, 30.0, 15.0
SOFT, CAP = 40.0, 60.0
# gap branch
GAP_DROP, GAP_RET, GAP_MAX = 40.0, 25.0, 90.0


def _break_ok(pre_slope, slide, release, bg_start, width_min):
    """The trend-break rules shared by the floor and ice branches (mg/dL/min)."""
    return (slide - pre_slope <= -1.5 and slide <= -3 and release >= 2
            and (pre_slope >= -1.0 or bg_start >= 100) and width_min <= 45)


def _grow(t, ice, bg, i0, i1):
    """Grow the core [i0, i1] back over the slide in and forward over the release; returns (ws, we, slopes)."""
    ref = ice[(t >= t[i0] - 90) & (t < t[i0] - 30)]
    base = np.nanmedian(ref) if np.isfinite(ref).sum() >= 4 else np.nan
    ws, we = i0, i1
    if np.isfinite(base):
        k = i0 - 1
        while k > 0 and t[i0] - t[k] <= CAP and t[k + 1] - t[k] <= SEG_GAP and np.isfinite(ice[k]) and ice[k] - base <= -SOFT:
            ws = k; k -= 1
        if i1 + 1 < len(t) and t[i1 + 1] - t[i1] <= CAP:       # the release step itself, even across a gap
            we = i1 + 1
        k = we + 1
        while k < len(t) and t[k] - t[i1] <= CAP and t[k] - t[k - 1] <= SEG_GAP and np.isfinite(ice[k]) and ice[k] - base >= SOFT:
            we = k; k += 1
    k0 = max(ws - 1, 0)
    pre = (t >= t[k0] - 40) & (t <= t[k0])
    pre_slope = np.polyfit(t[pre], bg[pre], 1)[0] if pre.sum() >= 4 else np.nan
    kmin = k0 + int(np.argmin(bg[k0:i1 + 1]))
    slide = (bg[kmin] - bg[k0]) / max(t[kmin] - t[k0], 5)
    release = (bg[we] - bg[kmin]) / max(t[we] - t[kmin], 5)
    return k0, we, pre_slope, slide, release, bg[k0], bg[kmin]


def _ice_cores(t, ice, dt, ok):
    """Sudden unexplained falls that return to the background ICE (the ice branch's cores)."""
    seg = np.concatenate([[0], np.cumsum(np.diff(t) > SEG_GAP)])
    n_base = max(int(round(BASE_MIN / np.median(dt))), 6)
    base = pd.Series(np.where(ok, ice, np.nan)).rolling(n_base, min_periods=6).median().shift(1).to_numpy()
    cores, i, n = [], 1, len(t)
    while i < n - 2:
        b = base[i]
        if not (ok[i] and ok[i - 1] and np.isfinite(b)) or not (ice[i] - b <= -A and ice[i - 1] - b > -A / 2):
            i += 1; continue
        C, peak, kpk, j, ret = 0.0, 0.0, i, i, None
        while j < n and seg[j] == seg[i] and t[j] - t[i] <= TMAX and ok[j]:
            C += (ice[j] - b) * dt[j] / 60.0
            if -C > peak:
                peak, kpk = -C, j
            elif peak >= DMIN and -C <= F * peak:
                ret = j; break
            j += 1
        if ret is None:
            i += 1; continue
        C2, over, k = C, 0.0, ret + 1                            # no overshoot for an hour after the return
        while k < n and seg[k] == seg[ret] and t[k] - t[ret] <= 60 and ok[k]:
            C2 += (ice[k] - b) * dt[k] / 60.0; over = max(over, C2); k += 1
        post = ice[(t > t[ret]) & (t <= t[ret] + POST_MIN) & (seg == seg[ret]) & ok]
        ret_rate = float(np.max(ice[kpk:ret + 1] - b)) if ret > kpk else 0.0
        if len(post) >= 3 and abs(np.median(post) - b) <= B and ret_rate >= 150 and over / peak <= 0.3 and ret - i >= 2:
            cores.append((i, ret, peak))
        i = ret + 1
    return cores


def artifacts(df: pd.DataFrame) -> pd.DataFrame:
    s = df.sort_values("t1").reset_index(drop=True)
    t = s.t1.astype("int64").to_numpy() / 6e10
    bg = s.bg1.to_numpy(float); ice = s.ice.to_numpy(float); dt = s.dt.to_numpy(float)
    carbs = s.carbs_g.to_numpy(float); hour = s.hour.to_numpy(float)
    junk = (s.alternating | s.change).to_numpy()
    cad = float(np.median(np.diff(t))) if len(t) > 1 else 5.0
    out = []

    def add(branch, ws, we, depth):
        if carbs[max(ws - 3, 0): we + 3].sum() > 0 or junk[max(ws - 8, 0): we + 2].any():
            return
        out.append(dict(start=s.t1[ws], end=s.t1[we], branch=branch, depth=float(depth), hour=hour[ws]))

    # gap branch
    for i in np.flatnonzero((np.diff(t) > 1.8 * cad) & (np.diff(t) <= GAP_MAX)):
        g0, g1 = t[i], t[i + 1]
        pre = (t >= g0 - 55) & (t <= g0 - 15)
        if pre.sum() < 5:
            continue
        b, c = np.polyfit(t[pre] - g0, bg[pre], 1)
        near = np.flatnonzero((t > g0 - 20) & (t <= g0))
        dev = bg[near] - (c + b * (t[near] - g0))
        if abs(b) > 1.0 or dev.min() > -GAP_DROP or abs(bg[i + 1] - (c + b * (g1 - g0))) > GAP_RET:
            continue
        first = near[np.flatnonzero(dev < -10)[0]] if (dev < -10).any() else near[-1]
        add("gap", max(first - 1, 0), i + 1, -dev.min())
    # floor branch
    fl = bg <= FLOOR
    i = 0
    while i < len(t):
        if not fl[i]:
            i += 1; continue
        j = i
        while j + 1 < len(t) and fl[j + 1] and t[j + 1] - t[j] <= 15:
            j += 1
        pre = (t >= t[i] - 45) & (t < t[i] - 10) & ~fl
        post = (t > t[j] + 10) & (t <= t[j] + 40) & ~fl
        nxt = np.flatnonzero((t > t[j]) & (t <= t[j] + 30) & ~fl)
        if pre.sum() >= 3 and post.sum() >= 3 and len(nxt):
            lp, lq = np.median(bg[pre]), np.median(bg[post])
            rise = (bg[nxt[0]] - FLOOR) / max(t[nxt[0]] - t[j], 1) * 60
            if lp >= 80 and rise >= 120 and 0.6 <= (lq - 40) / (lp - 40) <= 1.5:
                ws, we, ps, sl, rl, b0, _ = _grow(t, ice, bg, i, j)
                if _break_ok(ps, sl, rl, b0, t[we] - t[ws]):
                    add("floor", ws, we, lp - 40)
        i = j + 1
    # ice branch
    ok = s.on_cadence.to_numpy() & np.isfinite(ice) & ~(s.clamp | s.jump | s.post_gap).to_numpy() & (bg < 380)
    for i0, i1, peak in _ice_cores(t, ice, dt, ok):
        ws, we, ps, sl, rl, b0, _ = _grow(t, ice, bg, i0, i1)
        if _break_ok(ps, sl, rl, b0, t[we] - t[ws]):
            add("ice", ws, we, peak)
    a = pd.DataFrame(out, columns=["start", "end", "branch", "depth", "hour"]).sort_values("start")
    # one artifact can trip two branches (a slide into the floor that ends in a gap): keep the first, merged
    if len(a):
        a = a.reset_index(drop=True); keep = [0]
        for k in range(1, len(a)):
            if a.start[k] <= a.end[keep[-1]]:
                a.loc[keep[-1], "end"] = max(a.end[keep[-1]], a.end[k])
            else:
                keep.append(k)
        a = a.loc[keep].reset_index(drop=True)
    return a


def flag(df: pd.DataFrame, arts: pd.DataFrame | None = None) -> np.ndarray:
    """Boolean per row of df (in df's order): the step overlaps a detected artifact window."""
    arts = artifacts(df) if arts is None else arts
    t0 = df.t0.astype("int64").to_numpy(); t1 = df.t1.astype("int64").to_numpy()
    m = np.zeros(len(df), bool)
    for s_, e_ in zip(arts.start.astype("int64"), arts.end.astype("int64")):
        m |= (t1 >= s_) & (t0 <= e_)
    return m
