"""Model-ready sequences: each donor's step table on a regular 5-min grid.

Every slot carries what the generator may condition on at that moment, and the ICE it must
predict for the next slot. ICE is NaN (and masked out of the loss) where the interval wasn't
clean; context columns are carried through gaps with a validity flag rather than invented.

Feature scaling is fixed (not fitted), so a generated series can be fed back in unchanged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ICE_SCALE = 100.0          # mg/dL/h
FEATURES = ["ice", "ice_ok", "bg", "bg_ok", "iob", "act", "carbs", "bolus_man", "bolus_auto",
            "hour_sin", "hour_cos", "dow_sin", "dow_cos"]


def to_grid(df: pd.DataFrame) -> pd.DataFrame:
    """Step table -> 5-min grid with raw (unscaled) columns."""
    d = df.copy()
    d["slot"] = d.t1.dt.floor("5min")
    clean_ice = d.ice.where(d.clean)
    g = pd.DataFrame({
        "ice": clean_ice.groupby(d.slot).mean(),
        "bg": d.bg1.groupby(d.slot).last(),
        "iob": d.iob.groupby(d.slot).last(),
        "act": d.ins_activity_uhr.groupby(d.slot).mean(),
        "carbs": d.carbs_g.groupby(d.slot).sum(),
        "bolus_man": d.bolus_manual_u.groupby(d.slot).sum(),
        "bolus_auto": d.bolus_auto_u.groupby(d.slot).sum(),
        "hour": d.hour.groupby(d.slot).last(),
        "dow": d.dow.groupby(d.slot).last(),
    })
    idx = pd.date_range(g.index.min(), g.index.max(), freq="5min")
    g = g.reindex(idx)
    utc_h = idx.hour + idx.minute / 60
    off = (((g.hour - utc_h + 36) % 24) - 12).ffill().bfill()
    g["hour"] = (utc_h + off) % 24
    g["dow"] = g.dow.ffill().bfill()
    for c in ("carbs", "bolus_man", "bolus_auto"):
        g[c] = g[c].fillna(0.0)
    return g


def features(g: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(X [T, F] float32, y [T] float32 = scaled ICE of the NEXT slot, NaN when not a target)."""
    ice = g.ice.to_numpy() / ICE_SCALE
    bg_ok = g.bg.notna().to_numpy()
    X = np.stack([
        np.nan_to_num(ice), np.isfinite(ice).astype(float),
        g.bg.ffill().bfill().to_numpy() / 100.0, bg_ok.astype(float),
        g.iob.ffill().bfill().to_numpy() / 5.0,
        g.act.ffill().bfill().to_numpy() / 2.0,
        g.carbs.to_numpy() / 50.0, g.bolus_man.to_numpy() / 5.0, g.bolus_auto.to_numpy(),
        np.sin(2 * np.pi * g.hour / 24), np.cos(2 * np.pi * g.hour / 24),
        np.sin(2 * np.pi * g.dow / 7), np.cos(2 * np.pi * g.dow / 7),
    ], axis=1).astype(np.float32)
    y = np.r_[ice[1:], np.nan].astype(np.float32)
    return X, y
