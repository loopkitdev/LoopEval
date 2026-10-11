"""An `--external-plant` for `loop-eval simulate`: BG driven by generated (or replayed) ICE.

Per requested CGM sample at time t (previous sample t_prev, dt in hours):
    BG(t) = BG(t_prev) + (ICE(t) - ISF_tdd * insulin_absorption_rate(t_prev, t)) * dt
where insulin absorption comes from the donor's real doses before the first request and the
simulator's (candidate) doses after it, through the donor's insulin model -- the same quantity
and ISF that `extract` used to define ICE, so the two are interchangeable.

ICE source (--mode):
  replay  the person's measured ICE at that interval (NaN gaps: carried from the last value). Inside a
          disruption (the export's disruptions.csv: suspends, Loop offline, pump errors) the replay follows
          the field CGM instead, as the simulator's own counterfactual does (it stops advancing during an
          outage and resumes from the real CGM): integrating measured ICE through a multi-day outage pinned
          at the 401 ceiling ran one replay to the 20 mg/dL floor for 60 h.
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

ROOT = Path(os.path.expanduser(os.environ.get("ICE_ROOT", "~/.loop-eval/ice")))   # ICE_ROOT: another extracted bed
WARMUP_H = 24
LOW, HIGH = 40.0, 400.0


def _ts(x):
    return pd.Timestamp(x).tz_convert("UTC") if pd.Timestamp(x).tzinfo else pd.Timestamp(x, tz="UTC")


GAP_H = 2.0          # hours without a CGM sample after which the plant re-anchors to the field (shorter gaps
                     # integrate the gap's averaged ICE, which is exact when the insulin matches the field's)


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
    def __init__(self, alias, mode, ckpt=None, seed=0, actions="none", isf=None):
        self.alias, self.mode, self.actions = alias, mode, actions
        P = pd.read_csv(ROOT / "persons.csv").set_index("alias")
        self.isf, self.tdd = float(P.isf_tdd[alias]), float(P.tdd[alias])
        # isf: run the replay at another plant ISF; ICE is rebuilt at it (ice = v + ISF x absorbed), so the replay
        # stays exact when the insulin matches the field and only the loop's response to a dose difference changes
        self.ice_scale_isf = (float(isf) / self.isf) if isf else 1.0
        if isf:
            self.isf = float(isf)
        d = ROOT / "full" / alias
        therapy = json.load(open(d / "therapy.json"))
        self.ins = Insulin(MODELS.get(therapy.get("insulinType"), RAPID_ACTING_ADULT))
        self.doses_real = json.load(open(d / "doses.json"))
        # protocol v2 test actions: the person's REAL carb entries (at the moment Loop could see
        # them) and REAL manual boluses, returned in the step they fall in
        self.real_carbs = sorted((_ts(c.get("dosingVisibleDate") or c["startDate"]), float(c["grams"]),
                                  c.get("absorptionTime")) for c in json.load(open(d / "carbs.json")))
        self.real_manual = sorted((_ts(x["startDate"]), float(x["volume"])) for x in self.doses_real
                                  if x["deliveryType"] == "bolus" and not x.get("automatic"))
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
        self.t = None; self.bg = None; self.h = None; self.running = None; self.doses_log = []; self.last_ice = 0.0; self.last_ice_ok = 0.0
        self.log = []
        dpath = ROOT / "full" / alias / "disruptions.csv"
        dis = pd.read_csv(dpath) if dpath.exists() else pd.DataFrame(columns=["start", "end"])
        self.outages = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in zip(dis.start, dis.end)]

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
        if i < len(s) and abs((s.t1.iloc[i] - t).total_seconds()) < 60:
            r = s.iloc[i]
            # extraction leaves ICE (and v) NaN on off-cadence / flagged steps; the replay must still move glucose
            # as the field did there, so rebuild it from the field's own change (exact by construction)
            v = r.v if np.isfinite(r.v) else ((r.bg1 - r.bg0) / r.dt * 60 if np.isfinite(r.bg0) and np.isfinite(r.bg1) and r.dt > 0 else np.nan)
            if np.isfinite(v) and np.isfinite(r.ia):
                self.last_ice = float(v + r.ia * self.ice_scale_isf) / DS.ICE_SCALE
        return self.last_ice * DS.ICE_SCALE

    def _model_ice(self, t, hour, dow, carbs, man, auto, act_uhr):
        torch = self.torch
        # the generator sees BG as a CGM reports it (40-400): training data never exceeds the sensor
        # range, and an unclamped BG above 400 sent it out of distribution into runaway (i012, i033)
        x = np.array([[self.last_ice, self.last_ice_ok, min(max(self.bg, LOW), HIGH) / 100.0, 1.0, self.ins.iob(t) / 5.0,
                       act_uhr / 2.0, carbs / 50.0, man / 5.0, auto,
                       np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
                       np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)]], np.float32)
        x[:, self.drop] = 0.0
        with torch.no_grad():
            logit, mu, ls, self.h = self.net(torch.from_numpy(x)[None], self.pid, self.h)
            y = float(self.net.sample(logit, mu, ls)[0, -1])
        self.last_ice, self.last_ice_ok = y, 1.0
        return y * DS.ICE_SCALE

    def _actions(self, t0, t1):
        """Replay the person's real actions in (t0, t1] through protocol v2 (identity tests)."""
        if self.actions == "none":
            return {}
        iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        carbs = [dict(t=iso(t), grams=g, **({"absorption_s": a} if a else {}))
                 for t, g, a in self.real_carbs if t0 < t <= t1]
        if self.actions == "replay-units":
            bol = [dict(t=iso(t), units=u) for t, u in self.real_manual if t0 < t <= t1]
        else:                                                    # replay-ratio: the calculator's own advice
            bol = [dict(t=iso(t), ratio=1.0) for t, u in self.real_manual if t0 < t <= t1]
        return {"carbs": carbs, "boluses": bol}

    def advance(self, req):
        t0 = _ts(req["t0"])
        if self.t is None:
            self._start(t0)
        auto_u = 0.0
        self.doses_log.extend(req["doses"])
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
            # a CGM gap longer than GAP_H (sensor off, nothing uploaded) is followed like an outage: integrating
            # ICE across it in one step pinned one replay at 2,300 mg/dL after a 77 h gap
            outage = self.mode == "replay" and (dt_h > GAP_H or any(a <= t <= b for a, b in self.outages))
            if self.mode == "replay":
                ice = self._real_ice(t)
            else:
                ice = self._model_ice(t, hour, dow, carbs, man, auto_u, absorbed / dt_h)
            self.bg = max(self.bg + (ice - self.isf * absorbed / dt_h) * dt_h, 20.0)
            if outage:                                       # follow the field through the outage
                i = self.steps.t1.searchsorted(t)
                j = min(max(i, 1), len(self.steps)) - 1
                if abs((self.steps.t1.iloc[j] - t).total_seconds()) < 600:
                    self.bg = float(self.steps.bg1.iloc[j])
            self.log.append(dict(t1=t, dt=dt_h * 60, ice=ice, bg1=self.bg, iob=self.ins.iob(t),
                                 ins_activity_uhr=absorbed / dt_h, hour=hour, dow=dow, outage=outage))
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
        with open(str(path) + ".doses.json", "w") as f:          # what the simulator delivered
            json.dump(self.doses_log, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alias", required=True)
    ap.add_argument("--mode", choices=["replay", "model"], default="model")
    ap.add_argument("--ckpt")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--log", required=True)
    ap.add_argument("--isf", type=float, help="replay at this plant ISF (mg/dL/U) instead of ISF_tdd")
    ap.add_argument("--actions", choices=["none", "replay-ratio", "replay-units"], default="none",
                    help="protocol v2: return the person's real carb entries / manual boluses (tests)")
    a = ap.parse_args()
    plant = Plant(a.alias, a.mode, a.ckpt, a.seed, a.actions, a.isf)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        bg = plant.advance(req)
        reply = {"bg": bg, **plant._actions(_ts(req["t0"]), _ts(req["t1"]))}
        sys.stdout.write(json.dumps(reply) + "\n"); sys.stdout.flush()
    plant.write_log(a.log)


if __name__ == "__main__":
    main()
