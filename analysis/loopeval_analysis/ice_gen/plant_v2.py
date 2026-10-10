"""External plant (protocol v2) driven by the v2 generator: ICE AND the person's actions.

Run with `simulate --candidate-counterfactual --plant-behavior --external-plant ...`. Each sample:
  inputs   the plant's own world only — generated ICE history, plant BG as a CGM reports it
           (40-400), running ICE budget, the carb entries / boluses this plant's person made,
           clock, profile. Nothing from the real record after the warm-up.
  draws    next ICE; P(carb entry) -> grams, absorption; P(manual bolus) -> override (units) or
           calculator mode (ratio x recommendation)
  BG       BG(t) = BG(t_prev) + (ICE - ISF_tdd * insulin absorption) * dt   (as plant.py)
  reply    {"bg": [...], "carbs": [...], "boluses": [...]}
The generator is warmed up on the real 24 h before the first request, real actions included.

  python -m loopeval_analysis.ice_gen.plant_v2 --alias i005 --ckpt icegen_v2.pt --log out.parquet
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd
import torch

from . import dataset_v2 as D2
from .dataset import ICE_SCALE
from .extract import MODELS, RAPID_ACTING_ADULT
from .model_v2 import ICEGenV2
from .plant import ROOT, Insulin, _ts, LOW, HIGH

WARMUP = 288


class PlantV2:
    def __init__(self, alias, ckpt, seed=0):
        torch.manual_seed(seed); np.random.seed(seed)
        self.alias = alias
        P = pd.read_csv(ROOT / "persons.csv").set_index("alias")
        self.isf, self.tdd = float(P.isf_tdd[alias]), float(P.tdd[alias])
        d = ROOT / "full" / alias
        therapy = json.load(open(d / "therapy.json"))
        self.ins = Insulin(MODELS.get(therapy.get("insulinType"), RAPID_ACTING_ADULT))
        self.doses_real = json.load(open(d / "doses.json"))
        self.carbs_real = json.load(open(d / "carbs.json"))
        self.steps = pd.read_parquet(ROOT / "steps" / f"{alias}.parquet")
        bd = pd.read_parquet(ROOT / "bolus_decisions.parquet")
        self.bd_real = bd[bd.alias == alias]
        ck = torch.load(ckpt, map_location="cpu", weights_only=False)   # our own checkpoint (holds per-person constants)
        self.net = ICEGenV2(len(ck["features"]), len(ck["people"])); self.net.load_state_dict(ck["state"]); self.net.eval()
        self.pid = torch.tensor([ck["people"].index(alias)])
        self.k = ck["constants"][alias]
        self.drop = [ck["features"].index(f) for f in ck.get("drop", [])]   # inputs the model never saw
        self.t = None; self.running = None; self.h = None
        self.log, self.actions_log, self.doses_log = [], [], []

    # ---- warm-up on the real record up to t0 (inputs exactly as in training)
    def _start(self, t0):
        for x in self.doses_real:
            s, e = _ts(x["startDate"]), _ts(x.get("endDate", x["startDate"]))
            if s >= t0:
                continue
            if x["deliveryType"] != "bolus" and e > t0:
                self.running = (s, e, float(x.get("volume") or 0))
            self.ins.add(s, e, float(x.get("volume") or 0))
        hist = self.steps[self.steps.t1 <= t0]
        g, X, _, _ = D2.build(hist, [c for c in self.carbs_real if _ts(c.get("dosingVisibleDate") or c["startDate"]) <= t0],
                              self.bd_real[self.bd_real.t <= t0], self.tdd, self.isf)
        X[:, self.drop] = 0.0
        with torch.no_grad():
            _, self.h = self.net(torch.from_numpy(X[-WARMUP:])[None], self.pid)
        self.t = hist.t1.iloc[-1]; self.bg = float(hist.bg1.iloc[-1])
        ice = g.ice.to_numpy()[-WARMUP:]
        self.ice_hist = list(np.nan_to_num(ice, nan=self.k["base"]))
        self.last_ice = self.ice_hist[-1] / ICE_SCALE
        cg, bu = X[-WARMUP:, D2.FEATURES.index("carbs")], X[-WARMUP:, D2.FEATURES.index("bolus_man")]
        self.since_carb = float(X[-1, D2.FEATURES.index("since_carb")]) * 24
        self.since_bolus = float(X[-1, D2.FEATURES.index("since_bolus")]) * 24
        self.pending_carb_g = 0.0; self.pending_bolus_u = 0.0

    def _x(self, t):
        hour = None
        r = self.steps.t1.searchsorted(t)                       # local clock from the record's own tz
        if 0 < r <= len(self.steps):
            row = self.steps.iloc[min(r, len(self.steps) - 1)]
            hour = (float(row.hour) + (t - row.t1).total_seconds() / 3600) % 24; dow = float(row.dow)
        if hour is None:
            hour, dow = t.hour + t.minute / 60, t.dayofweek
        B = D2.budget(np.array(self.ice_hist[-288:]), self.k["base"], self.k["geq"])[-1]
        x = np.array([self.last_ice, 1.0, min(max(self.bg, LOW), HIGH) / 100, 1.0,
                      self.pending_carb_g / 50, self.pending_bolus_u / 5,
                      np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24),
                      np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7),
                      *(B / 50), min(self.since_carb, 24) / 24, min(self.since_bolus, 24) / 24], np.float32)
        x[self.drop] = 0.0
        return torch.from_numpy(x)[None, None], hour, dow

    def advance(self, req):
        t0 = _ts(req["t0"])
        if self.t is None:
            self._start(t0)
        rec = float(req.get("state", {}).get("rec_bolus") or 0.0)
        self.doses_log.extend(req["doses"])
        for d in req["doses"]:
            s, e = _ts(d["start"]), _ts(d["end"])
            if self.running is not None and d["type"] == "basal":
                rs, re_, rv = self.running
                cut = min(max(s, rs), re_)
                if re_ > cut:
                    self.ins.add(cut, re_, -rv * (re_ - cut) / (re_ - rs))
                self.running = None
            self.ins.add(s, e, float(d["volume"]))
        bgs, carbs, boluses = [], [], []
        for ts in req["samples"]:
            t = _ts(ts)
            dt_h = (t - self.t).total_seconds() / 3600
            if dt_h <= 0:
                bgs.append(min(max(self.bg, LOW), HIGH)); continue
            absorbed = self.ins.absorbed(self.t, t)
            x, hour, dow = self._x(t)
            with torch.no_grad():
                out, self.h = self.net(x, self.pid, self.h)
                s = self.net.sample(out)
            ice = float(s["ice"][0]) * ICE_SCALE
            self.bg = max(self.bg + (ice - self.isf * absorbed / dt_h) * dt_h, 20.0)
            self.ice_hist.append(ice); self.last_ice = ice / ICE_SCALE
            self.since_carb += dt_h; self.since_bolus += dt_h
            self.pending_carb_g = 0.0; self.pending_bolus_u = 0.0
            iso = t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            if bool(s["carb"][0]):
                g = float(s["carb_g"][0]); a = float(s["carb_abs_h"][0])
                carbs.append(dict(t=iso, grams=round(g, 1), absorption_s=round(a * 3600)))
                self.pending_carb_g = g; self.since_carb = 0.0
                self.actions_log.append(dict(t=t, kind="carb", grams=g, abs_h=a))
            if bool(s["bolus"][0]):
                # the model's mode choice stands: a calculator-mode bolus returns a RATIO and the
                # simulator computes the recommendation at the next decision, with this step's carb
                # entry visible. (Falling back to units whenever the pre-entry recommendation was ~0
                # turned nearly every meal bolus into a small override and ran the loop away.)
                if bool(s["override"][0]):
                    u = float(s["units"][0]); boluses.append(dict(t=iso, units=round(u, 2)))
                    self.actions_log.append(dict(t=t, kind="bolus_units", units=u, rec=rec))
                else:
                    r = float(s["ratio"][0]); u = r * rec; boluses.append(dict(t=iso, ratio=round(r, 3)))
                    self.actions_log.append(dict(t=t, kind="bolus_ratio", ratio=r, rec=rec, units=u))
                self.pending_bolus_u = u; self.since_bolus = 0.0
            self.log.append(dict(t1=t, dt=dt_h * 60, ice=ice, bg1=self.bg, iob=self.ins.iob(t),
                                 ins_activity_uhr=absorbed / dt_h, hour=hour, dow=dow))
            self.t = t
            if len(self.log) % 288 == 0:
                self.ins.prune(t)
            bgs.append(min(max(self.bg, LOW), HIGH))
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
    a = ap.parse_args()
    plant = PlantV2(a.alias, a.ckpt, a.seed)
    for line in sys.stdin:
        if line.strip():
            sys.stdout.write(json.dumps(plant.advance(json.loads(line))) + "\n"); sys.stdout.flush()
    plant.write_log(a.log)


if __name__ == "__main__":
    main()
