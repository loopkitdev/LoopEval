"""External plant (protocol v2) driven by the v3 meal-event generator.

Run with `simulate --candidate-counterfactual --plant-behavior --external-plant ...`. Each sample t:
  1. inputs from the plant's own world (BG as a CGM reports it, background ICE, current pulse
     rate, meal history, its own actions, clock) -> the generator
  2. background ICE ~ the model
  3. a meal anchor? -> ONE draw sets the pulse (size, peak, duration, absorption onset) AND the
     person's actions for it (carb entry: when, how much logged; bolus: when, calculator ratio or
     override units). Pulse and actions are scheduled from that draw, so they cannot drift apart.
  4. a correction bolus (no meal)? -> calculator ratio or override units
  5. ICE(t) = background + sum of active pulses (kernel.py: each integrates to its size and ends)
  6. BG(t) = BG(t_prev) + (ICE - ISF_tdd * insulin absorption) * dt
  7. with --noise: the CGM reports BG + e, e the person's level noise (noise.py); the generator, Loop
     and the scores all see the reported value, and the logged ICE is the reported one
  7a. with --compression: the CGM also reports compression artifacts (sensor.CompressionLayer), an offset on
     the reported value only; readings the sensor would withhold are sent as the depressed value (the protocol
     has no missing reading) and marked in the log, and artifact time is left out of the scores
  7b. with --slow: background ICE += u(t), the person's persistent slow level (slow.py)
  8. actions now due -> reply {"carbs": [...], "boluses": [...]}
Warmed up on the real 24 h before the first request (real meals still absorbing carry over).

  python -m loopeval_analysis.ice_gen.plant_v3 --alias i005 --ckpt icegen_v3.pt --log out.parquet
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd
import torch

from . import dataset_v3 as D3
from .dataset import ICE_SCALE
from .extract import MODELS, RAPID_ACTING_ADULT
from .kernel import params, rate, remaining
from .model_v3 import ICEGenV3
from .model_v3j import ICEGenV3J, ICEGenV3K
from .noise import LevelNoise
from .plant import GAP_H
from .slow import SlowLevel
from .sensor import CompressionLayer
from .plant import ROOT, Insulin, _ts, LOW, HIGH

WARMUP = 288


class PlantV3:
    def __init__(self, alias, ckpt, seed=0, feedback="mean", noise=None, rewarm_h=0.0, slow=None, compression=None):
        torch.manual_seed(seed); np.random.seed(seed)
        # what the generator sees as its own last background ICE: "sample" (the noisy draw) or
        # "mean" (the predictive mean). Fed its own noisy draws, the head reads them as volatility,
        # widens, and the background ICE spread runs away (i005: p5/p95 -289/340 vs real -69/177).
        self.feedback = feedback
        self.alias = alias
        P = pd.read_csv(ROOT / "persons.csv").set_index("alias")
        self.isf, self.tdd = float(P.isf_tdd[alias]), float(P.tdd[alias])
        d = ROOT / "full" / alias
        therapy = json.load(open(d / "therapy.json"))
        self.ins = Insulin(MODELS.get(therapy.get("insulinType"), RAPID_ACTING_ADULT))
        self.doses_real = json.load(open(d / "doses.json"))
        self.carbs_real = json.load(open(d / "carbs.json"))
        self.steps = pd.read_parquet(ROOT / "steps" / f"{alias}.parquet")
        self.base_iob = D3.basal_iob(self.steps)
        bd = pd.read_parquet(ROOT / "bolus_decisions.parquet"); self.bd_real = bd[bd.alias == alias]
        self.meals_real = pd.read_parquet(ROOT / "meals" / f"{alias}.parquet")
        self.corr_real = pd.read_parquet(ROOT / "meals" / f"{alias}_corrections.parquet")
        ck = torch.load(ckpt, map_location="cpu", weights_only=False)
        Net = {"v3j": ICEGenV3J, "v3k": ICEGenV3K}.get(ck.get("arch"), ICEGenV3)
        self.net = Net(len(ck["features"]), len(ck["people"])); self.net.load_state_dict(ck["state"]); self.net.eval()
        self.features = list(ck["features"]); self.F = {f: i for i, f in enumerate(self.features)}
        self.drop = list(ck.get("drop", []))
        self.pid = torch.tensor([ck["people"].index(alias)])
        self.geq = ck["constants"][alias]["geq"]
        self.calib = dict(ck.get("calib", {}))      # logit offsets on event-start heads (calibrate.py)
        self.t = None; self.running = None; self.h = None
        # rewarm_h > 0: every rewarm_h hours rebuild the GRU state from zero over the last 24 h of inputs, so
        # the network always runs with 24-48 h of memory as in training (a 29-day continuous state
        # under-generates meals by ~15%: runs/2026-10-10-ice-noise/mealrate.py)
        self.rewarm_h = rewarm_h; self.xbuf = []; self.since_rewarm = 0.0
        # noise: {"a1", "a2", "var": {alias: mg/dL^2}} from fit_noise; None = no level noise
        self.noise = LevelNoise(noise["a1"], noise["a2"], noise["var"].get(alias, 0.0), seed) if noise else None
        self.e = self.noise.e1 if self.noise else 0.0
        # slow: {"fast_var", "fast_tau_h", "slow_var", "slow_tau_h", "scale": {alias: s}} from fit_slow; None = off
        self.slow = SlowLevel(slow["fast_var"], slow["fast_tau_h"], slow["slow_var"], slow["slow_tau_h"],
                              slow.get("scale", {}).get(alias, 1.0), seed) if slow else None
        # fed into the generator's own background input, the level is amplified ~6x (it reads a shifted day
        # as its own persistent state and generates more of it: daily variance 611 vs real 174); default: not fed
        self.slow_in_input = bool(slow.get("into_input", False)) if slow else False
        # compression: (fit json, templates DataFrame, scale) from fit_layer.py; None = off
        self.comp = CompressionLayer(compression[0], compression[1], alias, compression[2], seed) if compression else None
        self.c, self.c_miss = 0.0, False
        self.pulses = []           # (onset Timestamp, size mg/dL, m, s)
        self.due = []              # (due Timestamp, kind, payload)
        self.anchor_times = []
        self.log, self.actions_log, self.doses_log = [], [], []

    def _start(self, t0):
        for x in self.doses_real:
            s, e = _ts(x["startDate"]), _ts(x.get("endDate", x["startDate"]))
            if s >= t0:
                continue
            if x["deliveryType"] != "bolus" and e > t0:
                self.running = (s, e, float(x.get("volume") or 0))
            self.ins.add(s, e, float(x.get("volume") or 0))
        hist = self.steps[self.steps.t1 <= t0]
        mr = self.meals_real[self.meals_real.onset <= t0]
        g, X, _ = D3.build(hist, mr, self.corr_real[self.corr_real.t <= t0] if len(self.corr_real) else self.corr_real,
                           self.bd_real[self.bd_real.t <= t0],
                           [c for c in self.carbs_real if _ts(c.get("entryDate") or c["startDate"]) <= t0], self.geq, self.features, self.isf)
        for f in self.drop:
            X[:, self.F[f]] = 0.0
        with torch.no_grad():
            _, self.h = self.net(torch.from_numpy(X[-WARMUP:])[None], self.pid)
        self.xbuf = [torch.from_numpy(r)[None, None] for r in X[-WARMUP:]]
        self.t = hist.t1.iloc[-1]; self.bg = float(hist.bg1.iloc[-1]) - self.e     # reported = real CGM at start
        m_, s_ = params(mr.peak_h.to_numpy() + 2.5 / 60, mr.dur_h.to_numpy()) if len(mr) else ([], [])
        for i, r in enumerate(mr.itertuples()):
            if (t0 - r.onset) < pd.Timedelta(hours=12):
                self.pulses.append((r.onset, r.size_g * self.geq, m_[i], s_[i]))
        last = X[-1]; F = self.F
        self.bgice = float(last[F["bgice"]]) if "bgice" in F else 0.0
        self.ema = float(last[F["bgice_ema"]]) * ICE_SCALE if "bgice_ema" in F else np.nan
        self.since_meal = float(last[F["since_meal"]]) * 24
        self.last_size = float(last[F["last_size"]]) * 50; self.since_bolus = float(last[F["since_bolus"]]) * 24
        tail = hist[hist.t1 > hist.t1.iloc[-1] - pd.Timedelta(minutes=35)]
        self.bg_hist = list(zip(tail.t1, np.clip(tail.bg1.to_numpy(float), LOW, HIGH)))   # reported CGM, last ~30 min
        self.anchor_times = [t0 - pd.Timedelta(hours=self.since_meal)] if self.since_meal < 3 else []
        self.slot_carbs = 0.0; self.slot_bolus = 0.0

    def _pulse_rate(self, t):
        return sum(float(rate([(t - on).total_seconds() / 3600], sz, m, s)[0]) for on, sz, m, s in self.pulses)

    def _x(self, t):
        r = self.steps.t1.searchsorted(t)
        row = self.steps.iloc[min(max(r, 1), len(self.steps)) - 1]
        hour = (float(row.hour) + (t - row.t1).total_seconds() / 3600) % 24; dow = float(row.dow)
        n3 = sum(1 for a in self.anchor_times if (t - a) < pd.Timedelta(hours=3))
        F = self.F
        x = np.zeros(len(F), np.float32)
        x[F["bg"]] = min(max(self.bg + self.e + self.c, LOW), HIGH) / 100; x[F["bg_ok"]] = 1
        if "bgice" in F:
            x[F["bgice"]] = self.bgice
        if "bgice_ema" in F:
            x[F["bgice_ema"]] = self.ema / ICE_SCALE
        x[F["bgice_ok"]] = 1
        if "bg_trend" in F:                       # same definitions as dataset_v3 (15-min slope, minutes < 70 in 30)
            tl, now = self.bg_hist[-1]            # the latest reading is the one x carries as bg
            past = [b for tt, b in self.bg_hist if tl - tt >= pd.Timedelta(minutes=14)]
            x[F["bg_trend"]] = (now - past[-1]) / 15 / 2 if past else 0.0
            x[F["low30"]] = sum(1 for tt, b in self.bg_hist if tl - tt < pd.Timedelta(minutes=29) and b < 70) * 5 / 30
            if "bg_pred30" in F:
                tr = x[F["bg_trend"]] * 2
                p_, hl = D3.predicted(np.array([now]), np.array([tr]))
                x[F["bg_pred30"]] = float(p_[0]) / 100; x[F["heading_low"]] = float(hl[0])
            if "eventual" in F:
                to_come = sum(float(remaining([(t - on).total_seconds() / 3600], sz, m, s_)[0]) for on, sz, m, s_ in self.pulses)
                x[F["eventual"]] = float(D3.eventual(np.array([now]), np.array([self.ins.iob(t)]), self.isf, self.base_iob, to_come)[0]) / 100
        x[F["pulse"]] = self._pulse_rate(t) / ICE_SCALE
        x[F["since_meal"]] = min(self.since_meal, 24) / 24; x[F["last_size"]] = self.last_size / 50; x[F["n_3h"]] = n3 / 3
        x[F["carbs"]] = self.slot_carbs / 50; x[F["bolus"]] = self.slot_bolus / 5
        x[F["since_bolus"]] = min(self.since_bolus, 24) / 24
        x[F["hour_sin"]], x[F["hour_cos"]] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
        x[F["dow_sin"]], x[F["dow_cos"]] = np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)
        return torch.from_numpy(x)[None, None], hour, dow

    def _bolus(self, s, prefix):
        if bool(s[f"{prefix}_mode"][0]):
            return dict(units=float(np.clip(np.exp(float(s[f"{prefix}_lu"][0])), 0.05, 30)))
        return dict(ratio=float(np.clip(np.exp(float(s[f"{prefix}_lr"][0])), 0.0, 5.0)))

    def advance(self, req):
        t0 = _ts(req["t0"])
        if self.t is None:
            self._start(t0)
        self.doses_log.extend(req["doses"])
        for d in req["doses"]:
            s_, e_ = _ts(d["start"]), _ts(d["end"])
            if self.running is not None and d["type"] == "basal":
                rs, re_, rv = self.running
                cut = min(max(s_, rs), re_)
                if re_ > cut:
                    self.ins.add(cut, re_, -rv * (re_ - cut) / (re_ - rs))
                self.running = None
            self.ins.add(s_, e_, float(d["volume"]))
        bgs, carbs, boluses = [], [], []
        iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        for ts in req["samples"]:
            t = _ts(ts)
            dt_h = (t - self.t).total_seconds() / 3600
            if dt_h <= 0:
                bgs.append(min(max(self.bg + self.e + self.c, LOW), HIGH)); continue
            absorbed = self.ins.absorbed(self.t, t)
            x, hour, dow = self._x(t)
            with torch.no_grad():
                if self.rewarm_h and self.since_rewarm >= self.rewarm_h:
                    _, self.h = self.net(torch.cat(self.xbuf[-WARMUP:], 1), self.pid)
                    self.since_rewarm = 0.0
                out, self.h = self.net(x, self.pid, self.h)
                self.xbuf.append(x); self.xbuf = self.xbuf[-WARMUP:]; self.since_rewarm += dt_h
                for k, b in self.calib.items():
                    out[k] = out[k] + b
                s = self.net.sample(out)
            self.slot_carbs = 0.0; self.slot_bolus = 0.0
            self.since_meal += dt_h; self.since_bolus += dt_h
            if bool(s["meal"][0]):
                size = float(np.clip(np.exp(float(s["m_lsize"][0])), 5, 250))
                peak = float(np.clip(np.exp(float(s["m_lpeak"][0])), 5 / 60, 4))
                dur = float(np.clip(np.exp(float(s["m_ldur"][0])), 0.25, 10))
                m, sd = params(peak, dur)
                on = t + pd.Timedelta(minutes=float(np.clip(np.expm1(float(s["m_onset"][0])), 0, 120)))
                self.pulses.append((on, size * self.geq, float(m), float(sd)))
                self.anchor_times.append(t); self.since_meal = 0.0; self.last_size = size
                if bool(s["m_ann"][0]):
                    g = float(np.clip(np.exp(float(s["m_lg"][0])), 1, 250))
                    self.due.append((t + pd.Timedelta(minutes=float(np.clip(np.expm1(float(s["m_entry"][0])), 0, 120))), "carb", g))
                if bool(s["m_hasbol"][0]):
                    self.due.append((t + pd.Timedelta(minutes=float(np.clip(np.expm1(float(s["m_bolus"][0])), 0, 120))),
                                     "bolus", self._bolus(s, "m")))
                self.actions_log.append(dict(t=t, kind="meal", size_g=size, peak_h=peak, dur_h=dur,
                                             announced=bool(s["m_ann"][0]), meal_bolus=bool(s["m_hasbol"][0])))
            if bool(s["corr"][0]):
                self.due.append((t, "bolus", self._bolus(s, "c")))
                self.actions_log.append(dict(t=t, kind="correction"))
            # actions now due
            keep = []
            for due_t, kind, pay in self.due:
                if due_t > t:
                    keep.append((due_t, kind, pay)); continue
                if kind == "carb":
                    carbs.append(dict(t=iso(t), grams=round(pay, 1), absorption_s=10800))
                    self.slot_carbs += pay
                    self.actions_log.append(dict(t=t, kind="carb", grams=pay))
                else:
                    boluses.append(dict(t=iso(t), **pay)); self.since_bolus = 0.0
                    self.slot_bolus += pay.get("units", 2.0)
                    self.actions_log.append(dict(t=t, kind="bolus_units" if "units" in pay else "bolus_ratio", **pay))
            self.due = keep
            bgice = float(s["bgice"][0])
            if self.feedback == "mean":
                lg_, mu_, _ = out["bgice"][0, -1].split(self.net.K_ICE)
                self.bgice = float((torch.softmax(lg_, -1) * mu_).sum())
            else:
                self.bgice = bgice
            pulse = self._pulse_rate(t)
            u = self.slow.step(dt_h) if self.slow else 0.0
            ice = bgice * ICE_SCALE + u + pulse
            self.bg = max(self.bg + (ice - self.isf * absorbed / dt_h) * dt_h, 20.0)
            if dt_h > GAP_H:            # a CGM gap: resume from the field reading, as the replay plant and the engine do
                j = self.steps.t1.searchsorted(t)
                near = [k for k in (j - 1, j) if 0 <= k < len(self.steps) and abs((self.steps.t1.iloc[k] - t).total_seconds()) < 600]
                if near:
                    k = min(near, key=lambda k: abs((self.steps.t1.iloc[k] - t).total_seconds()))
                    self.bg = float(self.steps.bg1.iloc[k]) - self.e
            if self.noise:
                e0 = self.e
                for _ in range(max(1, round(dt_h * 12))):
                    self.e = self.noise.step()
                ice += (self.e - e0) / dt_h
            if self.comp:
                c0 = self.c
                self.c, self.c_miss = self.comp.step(t, dt_h, hour)
                ice += (self.c - c0) / dt_h
            # smoothed background as the CGM would show it (what dataset_v3 computes from real data)
            self.ema = D3.ema_step(self.ema, ice - pulse - (0.0 if self.slow_in_input else u))
            self.bg_hist = [(tt, b) for tt, b in self.bg_hist if t - tt < pd.Timedelta(minutes=35)] + [(t, min(max(self.bg + self.e + self.c, LOW), HIGH))]
            self.pulses = [p for p in self.pulses if (t - p[0]) < pd.Timedelta(hours=12)]
            self.anchor_times = [a for a in self.anchor_times if (t - a) < pd.Timedelta(hours=3)]
            self.log.append(dict(t1=t, dt=dt_h * 60, ice=ice, bgice=bgice * ICE_SCALE + u, pulse=pulse, slow=u, bg1=self.bg + self.e + self.c, e=self.e, comp=self.c, comp_missing=self.c_miss,
                                 iob=self.ins.iob(t), ins_activity_uhr=absorbed / dt_h, hour=hour, dow=dow))
            self.t = t
            if len(self.log) % 288 == 0:
                self.ins.prune(t)
            bgs.append(min(max(self.bg + self.e + self.c, LOW), HIGH))
        return {"bg": bgs, "carbs": carbs, "boluses": boluses}

    def write_log(self, path):
        lg = pd.DataFrame(self.log)
        if len(lg):
            off = (((lg.hour - (lg.t1.dt.hour + lg.t1.dt.minute / 60) + 36) % 24) - 12)
            lg["local_day"] = (lg.t1.astype("int64") + (off * 3.6e12).astype("int64")) // 86_400_000_000_000
            lg["clean"] = True
            lg.insert(0, "alias", self.alias)
        lg.to_parquet(path, index=False)
        pd.DataFrame(self.actions_log).to_parquet(str(path) + ".actions.parquet", index=False)
        with open(str(path) + ".doses.json", "w") as f:
            json.dump(self.doses_log, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alias", required=True); ap.add_argument("--ckpt", required=True)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--log", required=True)
    ap.add_argument("--feedback", choices=["mean", "sample"], default="mean")
    ap.add_argument("--noise", help="level-noise parameters (json from fit_noise)")
    ap.add_argument("--slow", help="slow-level parameters (json from fit_slow, optional per-alias 'scale')")
    ap.add_argument("--compression", help="compression layer fit json (fit_layer.py); templates parquet beside it")
    ap.add_argument("--compression-scale", type=float, default=1.0, help="dial on the compression rate (0 = off)")
    ap.add_argument("--rewarm-h", type=float, default=0.0, help="rebuild the GRU state over the last 24 h every N hours (0 = never)")
    a = ap.parse_args()
    plant = PlantV3(a.alias, a.ckpt, a.seed, a.feedback, json.load(open(a.noise)) if a.noise else None, a.rewarm_h,
                    json.load(open(a.slow)) if a.slow else None,
                    (json.load(open(a.compression)), pd.read_parquet(a.compression.replace("_layer.json", "_templates.parquet")),
                     a.compression_scale) if a.compression else None)
    for line in sys.stdin:
        if line.strip():
            sys.stdout.write(json.dumps(plant.advance(json.loads(line))) + "\n"); sys.stdout.flush()
    plant.write_log(a.log)


if __name__ == "__main__":
    main()
