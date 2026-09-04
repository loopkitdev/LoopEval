#!/usr/bin/env python3
"""Rebalance the cohort's pumps, and stop defining engagement in device-specific terms.

Two problems this fixes.

FIRST, the hands-off screen used manual boluses as a SHARE of all boluses. twiist
automates through basal and records essentially no automated boluses (4.1M
automated basal rows against 2 donors with an automated bolus), while Loop on an
Omnipod auto-boluses ~62 times a day. So every twiist user has a manual share of
1.0 and the screen excluded them categorically: the resulting stratum is 18
Omnipod and 1 Medtronic, zero twiist, in a pool whose low-bolus stratum is 80%
twiist. Engagement must be measured as a RATE (boluses per day), which is
comparable across both, never as a share.

SECOND, the cohort over-weights twiist relative to the reference population the
modelling targets — Omnipod 5 and Control-IQ, where twiist has no share at all.
This selects Omnipod donors into the cells where we are twiist-heavy, while
keeping at least a few twiist users in every cell so that device is not perfectly
confounded with engagement.

Writes device_alias_map.json (aliases d01…); export with:
    EXPORT_ROOT=device EXPORT_MAP=device_alias_map.json python3 export_full.py 6
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

CACHE = Path(os.path.expanduser("~/.loop-eval/trait-cohort"))
GRID = Path("/private/tmp/claude-501/-Users-pete-dev-loopeval-eda/"
            "bfa63131-1394-4401-ba0d-468c73f27a9b/scratchpad/eligible_grid.csv")
OUT_MAP = CACHE / "device_alias_map.json"
TARGET_OMNIPOD = 0.65          # share of the cohort on an Omnipod-class pump
MIN_TWIIST_PER_CELL = 3


def main() -> int:
    g = pd.read_csv(GRID)
    held = set()
    for f in ("alias_map.json", "handsoff_alias_map.json", "grid_alias_map.json"):
        p = CACHE / f
        if p.exists():
            held |= set(json.loads(p.read_text()).values())
    g["hash"] = [hashlib.md5(str(u).encode()).hexdigest() for u in g["_userId"]]
    ours = g[g["_userId"].isin(held)]
    n_now, n_omni = len(ours), (ours["pump"] == "Omnipod (Insulet)").sum()
    picked: list[str] = []

    # Omnipod top-up, placed where we are most twiist-heavy.
    short = {}
    for cell, sub in ours.groupby("dosing", observed=True):
        omni_share = (sub["pump"] == "Omnipod (Insulet)").mean()
        short[cell] = max(round((TARGET_OMNIPOD - omni_share) * len(sub)), 0)
    for cell, need in sorted(short.items(), key=lambda kv: -kv[1]):
        if not need:
            continue
        avail = g[(g["dosing"] == cell) & (g["pump"] == "Omnipod (Insulet)")
                  & ~g["_userId"].isin(held | set(picked))].sort_values("hash")
        take = avail["_userId"].head(need).tolist()
        picked += take
        print(f"  {cell:>4} boluses/day: +{len(take)} Omnipod")

    # Keep twiist present in every cell, so device is not a proxy for engagement.
    for cell, sub in ours.groupby("dosing", observed=True):
        have = (sub["pump"] == "twiist (Sequel)").sum()
        need = max(MIN_TWIIST_PER_CELL - have, 0)
        if not need:
            continue
        avail = g[(g["dosing"] == cell) & (g["pump"] == "twiist (Sequel)")
                  & ~g["_userId"].isin(held | set(picked))].sort_values("hash")
        take = avail["_userId"].head(need).tolist()
        picked += take
        print(f"  {cell:>4} boluses/day: +{len(take)} twiist (cell floor)")

    amap = {f"d{i + 1:02d}": u for i, u in enumerate(picked)}
    OUT_MAP.write_text(json.dumps(amap, indent=2))
    proj = (n_omni + sum(1 for u in picked
                         if g.loc[g["_userId"] == u, "pump"].iloc[0] == "Omnipod (Insulet)"))
    print(f"\nnow: {n_omni}/{n_now} Omnipod ({n_omni / n_now:.0%})")
    print(f"after: {proj}/{n_now + len(picked)} ({proj / (n_now + len(picked)):.0%})")
    print(f"{len(amap)} donors -> {OUT_MAP} (git-ignored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
