"""An `--external-plant` for `loop-eval simulate`: BG driven by generated (or replayed) ICE.

Per requested CGM sample at time t (previous sample t_prev, dt in hours):
    BG(t) = BG(t_prev) + (ICE(t) - ISF_tdd * insulin_absorption_rate(t_prev, t)) * dt
where insulin absorption comes from the donor's real doses before the first request and the
simulator's (candidate) doses after it, through the donor's insulin model -- the same quantity
and ISF that `extract` used to define ICE, so the two are interchangeable.

ICE source (--mode):
  replay  the person's measured ICE at that interval (NaN gaps: carried from the last value).
          With `simulate --cf-identity` this must reproduce the field CGM -- the plant's check.
  model   sampled from the trained generator, conditioned on the plant's OWN BG / IOB / ICE
          history (never the field's: real BG would leak the real ICE), local clock, the
          person's carb entries and boluses, and their profile vector. Warmed up on the real
          24 h before the first request.

Protocol (ExternalPlant.swift): one JSON request per stdin line, one {"bg": [...]} reply per line.
On EOF it writes the rollout (t1, dt, ice, bg1, iob, hour, local_day, clean...) to --log.

  python -m loopeval_analysis.ice_gen.plant --alias i004 --mode model --ckpt icegen_v1.pt --log out.parquet
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import dataset as DS
from .extract import MODELS, RAPID_ACTING_ADULT
from ..iob import percent_effect_remaining

ROOT = Path(os.path.expanduser("~/.loop-eval/ice"))
WARMUP_H = 24
LOW, HIGH = 40.0, 400.0


def _ts(x):
    return pd.Timestamp(x).tz_convert("UTC") if pd.Timestamp(x).tzinfo else pd.Timestamp(x, tz="UTC")


class Insulin:
    """Point-mass insulin events (basal split into <= 1-min chunks); absorbed fraction via the
    model's percent-effect-remaining curve."""

    def __init__(self, model):
        self.model = model
        self.t = np.zeros(0, "int64"); self.u = np.zeros(0)

    def add(self, start, end, units):
        if units == 0:
            return
        s, e = start.value, max(end.value, start.value)
        n = max(1, int(np.ceil((e - s) / 60e9)))           # 1-min chunks, as extract.py
        mids = s + (np.arange(n) + 0.5) * (e - s) / n if e > s else np.array([s])
        self.t = np.r_[self.t, mids.astype("int64")]; self.u = np.r_[self.u, np.full(n, units / n)]

    def prune(self, now):
        """Drop events fully absorbed before `now` (they contribute nothing from here on)."""
        keep = (now.value - self.t) / 6e10 < self.model.effect_duration_min + 5
        self.t, self.u = self.t[keep], self.u[keep]

    def _remaining(self, at_ns):
        el = (at_ns - self.t) / 6e10
        live = (el >= 0) & (el < self.model.effect_duration_min + 1)
        rem = np.where(el < 0, 1.0, 0.0)
        rem[live] = percent_effect_remaining(el[live], self.model)
        return rem

    def iob(self, at):
        el = (at.value - self.t) / 6e10
        m = (el >= 0) & (el < self.model.effect_duration_min + 1)
        return float(np.sum(self.u[m] * percent_effect_remaining(el[m], self.model)))

    def absorbed(self, a, b):
        """Units absorbed in (a, b] from events delivered up to b."""
        m = self.t <= b.value
        ra = np.where(self.t[m] <= a.value, self._remaining(a.value)[m], 1.0)
        rb = self._remaining(b.value)[m]
        return float(np.sum(self.u[m] * (ra - rb)))


class Plant:
    def __init__(self, alias, mode, ckpt=None, seed=0):
        self.alias, self.mode = alias, mode
        P = pd.read_csv(ROOT / "persons.csv").set_index("alias")
        self.isf, self.tdd = float(P.isf_tdd[alias]), float(P.tdd[alias])
        d = ROOT / "full" / alias
        therapy = json.load(open(d / "therapy.json"))
        self.ins = Insulin(MODELS.get(therapy.get("insulinType"), RAPID_ACTING_ADULT))
        self.doses_real = json.load(open(d / "doses.json"))
        self.steps = pd.read_parquet(ROOT / "steps" / f"{alias}.parquet")
        self.grid = DS.to_grid(self.steps)                      # real history (warm-up, carbs, clock)
        self.rng = np.random.default_rng(seed)
        self.net = None
        if mode == "model":
            import torch
            self.torch = torch
            torch.manual_seed(seed)
            ck = torch.load(ckpt, map_location="cpu")
            from .model import ICEGen
            self.net = ICEGen(len(ck["features"]), len(ck["people"]))
            self.net.load_state_dict(ck["state"]); self.net.eval()
            self.pid = torch.tensor([ck["people"].index(alias)])
            self.drop = [ck["features"].index(f) for f in ck.get("drop", [])]   # inputs the model never saw
        self.t = None; self.bg = None; self.h = None; self.running = None; self.last_ice = 0.0; self.last_ice_ok = 0.0
        self.log = []

    # ---- initialisation at the first request: real insulin before t0, warm the generator up
    def _start(self, t0):
        for x in self.doses_real:
            s, e = _ts(x["startDate"]), _ts(x.get("endDate", x["startDate"]))
            if s >= t0:
                continue
            v = float(x.get("volume") or 0)
            if x["deliveryType"] != "bolus" and e > t0:
                # basal running at t0: the simulator only sends doses that START after t0, so this
                # one runs on until the first basal the simulator sends replaces it
                self.running = (s, e, v)
            self.ins.add(s, e, v)
        hist = self.grid.loc[:t0]
        prior = self.steps[self.steps.t1 <= t0]                  # the last real reading at/before t0
        self.t = prior.t1.iloc[-1] if len(prior) else t0
        self.bg = float(prior.bg1.iloc[-1]) if len(prior) else 120.0
        if self.net is not None:
            w = hist.iloc[-WARMUP_H * 12:]
            X, _ = DS.features(w)
            X[:, self.drop] = 0.0
            with self.torch.no_grad():
                _, _, _, self.h = self.net(self.torch.from_numpy(X)[None], self.pid)
            ice = w.ice.dropna()
            self.last_ice = float(ice.iloc[-1]) / DS.ICE_SCALE if len(ice) else 0.0
            self.last_ice_ok = 1.0 if len(ice) else 0.0

    def _context(self, t):
        """Clock and recorded behaviour (carb entries, manual boluses) for slot t, from the record."""
        slot = t.floor("5min")
        g = self.grid
        row = g.loc[slot] if slot in g.index else None
        hour = float(row.hour) if row is not None else (t.hour + t.minute / 60)
        dow = float(row.dow) if row is not None else t.dayofweek
        carbs = float(row.carbs) if row is not None else 0.0
        man = float(row.bolus_man) if row is not None else 0.0
        return hour, dow, carbs, man

    def _real_ice(self, t):
        s = self.steps
        i = s.t1.searchsorted(t)
        if i < len(s) and abs((s.t1.iloc[i] - t).total_seconds()) < 60 and np.isfinite(s.ice.iloc[i]):
            self.last_ice = float(s.ice.iloc[i]) / DS.ICE_SCALE
        return self.last_ice * DS.ICE_SCALE

    def _model_ice(self, t, hour, dow, carbs, man, auto, act_uhr):
        torch = self.torch
        x = np.array([[self.last_ice, self.last_ice_ok, self.bg / 100.0, 1.0, self.ins.iob(t) / 5.0,
                       act_uhr / 2.0, carbs / 50.0, man / 5.0, auto,
                       np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
                       np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)]], np.float32)
        x[:, self.drop] = 0.0
        with torch.no_grad():
            logit, mu, ls, self.h = self.net(torch.from_numpy(x)[None], self.pid, self.h)
            y = float(self.net.sample(logit, mu, ls)[0, -1])
        self.last_ice, self.last_ice_ok = y, 1.0
        return y * DS.ICE_SCALE

    def advance(self, req):
        t0 = _ts(req["t0"])
        if self.t is None:
            self._start(t0)
        auto_u = 0.0
        for d in req["doses"]:
            s, e = _ts(d["start"]), _ts(d["end"])
            if self.running is not None and d["type"] == "basal":
                rs, re_, rv = self.running                 # superseded at this basal's start:
                cut = min(max(s, rs), re_)                 # remove the part it never delivered
                if re_ > cut:
                    self.ins.add(cut, re_, -rv * (re_ - cut) / (re_ - rs))
                self.running = None
            self.ins.add(s, e, float(d["volume"]))
            if d["type"] == "bolus":
                auto_u += float(d["volume"])
        out = []
        for ts in req["samples"]:
            t = _ts(ts)
            dt_h = (t - self.t).total_seconds() / 3600
            if dt_h <= 0:
                out.append(min(max(self.bg, LOW), HIGH)); continue
            absorbed = self.ins.absorbed(self.t, t)
            hour, dow, carbs, man = self._context(t)
            if self.mode == "replay":
                ice = self._real_ice(t)
            else:
                ice = self._model_ice(t, hour, dow, carbs, man, auto_u, absorbed / dt_h)
            self.bg = max(self.bg + (ice - self.isf * absorbed / dt_h) * dt_h, 20.0)
            self.log.append(dict(t1=t, dt=dt_h * 60, ice=ice, bg1=self.bg, iob=self.ins.iob(t),
                                 ins_activity_uhr=absorbed / dt_h, hour=hour, dow=dow))
            self.t = t; auto_u = 0.0
            if len(self.log) % 288 == 0:
                self.ins.prune(t)
            out.append(min(max(self.bg, LOW), HIGH))
        return out

    def write_log(self, path):
        lg = pd.DataFrame(self.log)
        if len(lg):
            off = (((lg.hour - (lg.t1.dt.hour + lg.t1.dt.minute / 60) + 36) % 24) - 12)
            lg["local_day"] = (lg.t1.astype("int64") + (off * 3.6e12).astype("int64")) // 86_400_000_000_000
            lg["clean"] = True
            lg.insert(0, "alias", self.alias)
        lg.to_parquet(path, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alias", required=True)
    ap.add_argument("--mode", choices=["replay", "model"], default="model")
    ap.add_argument("--ckpt")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--log", required=True)
    a = ap.parse_args()
    plant = Plant(a.alias, a.mode, a.ckpt, a.seed)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        bg = plant.advance(json.loads(line))
        sys.stdout.write(json.dumps({"bg": bg}) + "\n"); sys.stdout.flush()
    plant.write_log(a.log)


if __name__ == "__main__":
    main()
