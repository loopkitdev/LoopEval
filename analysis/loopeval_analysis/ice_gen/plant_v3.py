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
     the reported value only; readings the sensor withholds are sent as null (no reading: the engine keeps them
     out of Loop's glucose history, b09888b) and marked in the log; artifact time is left out of the scores
  7b. with --slow: background ICE += u(t), the person's persistent slow level (slow.py)
  8. actions now due -> reply {"carbs": [...], "boluses": [...]}
Warmed up on the real 24 h before the first request (real meals still absorbing carry over).

  python -m loopeval_analysis.ice_gen.plant_v3 --alias i005 --ckpt icegen_v3.pt --log out.parquet
"""
from __future__ import annotations

import argparse
import os
import zlib
import json
import sys

import numpy as np
from scipy.special import ndtr
import pandas as pd
import torch

from . import dataset_v3 as D3
from .dataset import ICE_SCALE
from .extract import MODELS, RAPID_ACTING_ADULT
from .kernel import params, rate, remaining
from .model_v3 import ICEGenV3
from .model_v3j import ICEGenV3J, ICEGenV3K
from .model_v3m import ICEGenV3M, ICEGenV3M3, ICEGenV3M4, ICEGenV3M5, ICEGenV3M6, ICEGenV3M7, ICEGenV3M8, ICEGenV3M9, ICEGenV3M10, ICEGenV3M11, ICEGenV3M12, ICEGenV3M13, ICEGenV3M14, ICEGenV3M15
from .model_v4 import ICEGenV4, ICEGenV4R
from . import dataset_v3m3 as D3M3
from . import dataset_v3m as D3M
from .noise import LevelNoise
from .plant import GAP_H
from .slow import SlowLevel
from .sensor import CompressionLayer
from .plant import ROOT, Insulin, _ts, LOW, HIGH

WARMUP = 288


def mdn_quantile(params, k, q):
    """Inverse CDF of a 1-D Gaussian mixture (logits, means, log sds) at probability q, by bisection."""
    lg, mu, ls = [t.double().numpy() for t in params.split(k, -1)]
    w = np.exp(lg - lg.max()); w /= w.sum(); sd = np.exp(np.clip(ls, -5, 3))
    lo, hi = float((mu - 8 * sd).min()), float((mu + 8 * sd).max())
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if float((w * ndtr((mid - mu) / sd)).sum()) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


class PlantV3:
    def __init__(self, alias, ckpt, seed=0, feedback="mean", noise=None, rewarm_h=0.0, slow=None, compression=None):
        # every random stream is per donor: seeded from the rollout seed AND the donor. Seeded from the rollout seed alone, every
        # donor on a seed shared one slow-level path and one stream of uniforms for its event draws, so all generated people
        # moved together (slow level +2.55 mg/dL/h averaged over 72 runs, standard error 0.26) and pooled results were not
        # independent across donors. PLANT_SHARED_SEED=1 restores the old behavior.
        if os.environ.get("PLANT_SHARED_SEED") != "1":
            seed = int(seed) * 1_000_003 + zlib.crc32(alias.encode()) % 1_000_003
        torch.manual_seed(seed); np.random.seed(seed % (2 ** 32))
        # what the generator sees as its own last background ICE: "sample" (the noisy draw) or
        # "mean" (the predictive mean). Fed its own noisy draws, the head reads them as volatility,
        # widens, and the background ICE spread runs away (i005: p5/p95 -289/340 vs real -69/177).
        self.feedback = feedback
        self.couple_meal_bolus = False
        self.alias = alias
        P = pd.read_csv(ROOT / "persons.csv").set_index("alias")
        self.isf, self.tdd = float(P.isf_tdd[alias]), float(P.tdd[alias])
        self.act_typ = self.tdd / 24.0                                  # the person's typical insulin activity, U/h
        d = ROOT / "full" / alias
        therapy = json.load(open(d / "therapy.json"))
        self.ins = Insulin(MODELS.get(therapy.get("insulinType"), RAPID_ACTING_ADULT))
        self.doses_real = json.load(open(d / "doses.json"))
        self.carbs_real = json.load(open(d / "carbs.json"))
        self.steps = pd.read_parquet(ROOT / "steps" / f"{alias}.parquet")
        self.follow_disrupted = True   # --no-follow-disrupted turns it off
        # PATIENT_INSULIN_GAIN g: insulin activity away from the person's typical rate (TDD / 24 U/h) lowers glucose at g times the
        # ISF_tdd rule. In fasting overnight hours real background ICE rises with insulin activity (slope +0.43, 163 donors;
        # confounded by Loop reacting to ICE), and the field moved 0.6-0.9x what replay predicted for real settings edits (LESSONS
        # 40): the rule likely overstates the effect of insulin the person did not get in the field. Replay is unaffected.
        self.ins_gain = float(os.environ.get("PATIENT_INSULIN_GAIN", "1"))
        self.eoff_scale = float(os.environ.get("PLANT_EOFF_SCALE", "1"))   # diagnostic: scale entry -> pulse onset delay
        # monthly-cycle dial (off by default): the person's insulin need swings on a 28-day sinusoid, amplitude MONTH_CYCLE x their
        # typical insulin action (ISF x TDD/24, mg/dL/h) added to background ICE, random phase per run
        self.mc_amp = float(os.environ.get("MONTH_CYCLE", "0"))
        self.mc_phase = float(np.random.default_rng(seed + 32452843).uniform(0, 2 * np.pi))
        # PLANT_REAL_BG=1 (diagnostic): background ICE from the field at the same time (measured ICE minus labeled pulses),
        # meals and behavior still generated; steps with no real value keep the draw
        self.real_bg = None
        if os.environ.get("PLANT_REAL_BG") == "1":
            from .dataset import to_grid
            from .kernel import reconstruct
            g_ = to_grid(self.steps); mr_ = pd.read_parquet(ROOT / "meals" / f"{alias}.parquet")
            pu_ = reconstruct(g_.index, mr_, self.isf / (500 / self.tdd)) if len(mr_) else 0.0
            self.real_bg = pd.Series(g_.ice.to_numpy() - pu_, index=g_.index)
        # bgice_rho > 0: successive background-ICE draws share an AR(1) quantile (5-min coefficient). Independent draws are
        # near white (lag-5 autocorrelation 0.26-0.31, lag-10 ~0) where real background ICE is 0.48 / 0.19 (median of 41
        # donors), and integrated they made generated glucose 1.3-2.3x rougher than real CGM at 5 min
        self.bgice_rho = float(os.environ.get("BGICE_RHO", "0")); self.bg_z = 0.0
        self.rng_z = np.random.default_rng(seed + 104729)
        self.rng_v4 = np.random.default_rng(seed + 7_368_787); self.seed_v4 = seed % 2_147_483_647
        self.xlog = [] if os.environ.get("PLANT_XLOG") else None   # PLANT_XLOG=1: write the inputs fed each step beside the log
        self.base_iob = D3.basal_iob(self.steps)
        bd = pd.read_parquet(ROOT / "bolus_decisions.parquet"); self.bd_real = bd[bd.alias == alias]
        self.meals_real = pd.read_parquet(ROOT / "meals" / f"{alias}.parquet")
        self.corr_real = pd.read_parquet(ROOT / "meals" / f"{alias}_corrections.parquet")
        ck = torch.load(ckpt, map_location="cpu", weights_only=False)
        Net = {"v3j": ICEGenV3J, "v3k": ICEGenV3K, "v3m": ICEGenV3M, "v3m3": ICEGenV3M3, "v3m4": ICEGenV3M4, "v3m5": ICEGenV3M5, "v3m6": ICEGenV3M6, "v3m7": ICEGenV3M7, "v3m8": ICEGenV3M8, "v3m9": ICEGenV3M9, "v3m10": ICEGenV3M10, "v3m11": ICEGenV3M11, "v3m12": ICEGenV3M12, "v3m13": ICEGenV3M13, "v3m14": ICEGenV3M14, "v3m15": ICEGenV3M15, "v4": ICEGenV4, "v4r": ICEGenV4R}.get(ck.get("arch"), ICEGenV3)
        self.v3m = ck.get("arch") in ("v3m", "v3m3", "v3m4", "v3m5", "v3m6", "v3m7", "v3m8", "v3m9", "v3m10", "v3m11", "v3m12", "v3m13", "v3m14", "v3m15", "v4", "v4r"); self.v3m3 = ck.get("arch") in ("v3m3", "v3m4", "v3m5", "v3m6", "v3m7", "v3m8", "v3m9", "v3m10", "v3m11", "v3m12", "v3m13", "v3m14", "v3m15", "v4", "v4r")
        self.v4 = ck.get("arch") in ("v4", "v4r")     # entries and boluses drawn as their own events (dataset_v3m)
        self.net = (Net(len(ck["features"]), len(ck["people"]), features=list(ck["features"])) if ck.get("arch") in ("v3m9", "v3m10", "v3m11", "v3m12", "v3m13", "v3m14", "v3m15", "v4", "v4r") else Net(len(ck["features"]), len(ck["people"])))
        self.net.load_state_dict(ck["state"]); self.net.eval()
        self.features = list(ck["features"]); self.F = {f: i for i, f in enumerate(self.features)}
        self.drop = list(ck.get("drop", []))
        self.pid = torch.tensor([ck["people"].index(alias)])
        # DRAW_PERSON=<seed>: a new person drawn from the population, not the host donor. The host supplies only the deployed
        # controller, insulin and warm-up context; the person's profile (and explicit trait) vector is another trained person's,
        # jittered (DRAW_MODE=gauss: a Gaussian fitted to all trained people's), and nothing personal to the host is used (no per-person calibrations, population
        # slow-state scale). For the generalization check: drawn people should match the real population's spread and co-variation.
        self.drawn = os.environ.get("DRAW_PERSON") not in (None, "")
        self.announce = float(os.environ.get("ANNOUNCE", "1")); self.rng_ann = np.random.default_rng(seed + 15485863)
        if self.drawn:
            with torch.no_grad():
                W = [self.net.profile.weight] + ([self.net.trait.weight] if hasattr(self.net, "trait") else [])
                Z = torch.cat(W, 1).double(); mu = Z.mean(0); C = torch.cov(Z.T) + 1e-6 * torch.eye(Z.shape[1], dtype=Z.dtype)
                g = torch.Generator().manual_seed(int(os.environ["DRAW_PERSON"]) * 7919 + seed)
                if os.environ.get("DRAW_MODE", "kernel") == "gauss":
                    z = mu + torch.linalg.cholesky(C) @ torch.randn(Z.shape[1], generator=g, dtype=Z.dtype)
                else:   # a trained person other than the host, jittered: keeps the population's modes (non-announcers vs announcers:
                        # the entry trait is bimodal, a Gaussian put drawn people in the gap) and how traits co-vary
                    others = [i for i in range(Z.shape[0]) if i != int(self.pid[0])]
                    j = others[int(torch.randint(len(others), (1,), generator=g))]
                    h = float(os.environ.get("DRAW_JITTER", "0.3"))
                    z = Z[j] + h * (torch.linalg.cholesky(C) @ torch.randn(Z.shape[1], generator=g, dtype=Z.dtype))
                k = self.net.profile.weight.shape[1]
                self.net.profile.weight[self.pid[0]] = z[:k].float()
                if hasattr(self.net, "trait"):
                    self.net.trait.weight[self.pid[0]] = z[k:].float()
        self.geq = ck["constants"][alias]["geq"]
        self.calib = dict(ck.get("calib", {}))      # logit offsets on event-start heads (calibrate.py)
        # bg_spread < 1: closed-loop inputs (denser generated meal activity, higher glucose) make the head predict 30-65%
        # wider background ICE than it does fed real history (i001/i005/i022, v3m4); BGICE_SPREAD or ck["calib_bg_spread"]
        self.bg_spread = float(os.environ.get("BGICE_SPREAD", ck.get("calib_bg_spread", 1.0)))
        # per-person logit offsets on the behavior heads (meal, m_ann, m_hasbol, corr), stacked on the pooled ones
        # (calibrate_closed_rates_person.py): how often a person eats, announces, boluses and corrects is their own
        for k, b in ({} if self.drawn else ck.get("calib_person", {}).get(alias, {})).items():
            self.calib[k] = self.calib.get(k, 0.0) + float(b)
        # additive background-ICE offset (mg/dL/h) in the near-low state: heading low or BG < 70 (calibrate_state.py)
        cs = ck.get("calib_state", {})              # per person, shrunk to the pooled value, where fitted
        self.near_low_bgice = float(cs.get("near_low_bgice", 0.0) if self.drawn else cs.get("near_low_bgice_person", {}).get(alias, cs.get("near_low_bgice", 0.0)))
        # meal-start logit offset per glucose band x 15-min trend cell (calibrate_meal_state.py); none unless fitted
        ms = ck.get("calib_meal_state")
        self.meal_state = (np.asarray(ms["bands"]), np.asarray(ms["trends"]), np.asarray(ms["offset"])) if ms else None
        # additive shift on the sampled log time-to-peak per glucose band at the start (calibrate_closed_peak.py); none unless fitted
        ps = ck.get("calib_peak_state")
        self.peak_state = (np.asarray(ps["bands"]), np.asarray(ps["shift"])) if ps else None
        # additive background-ICE offset (mg/dL/h) per glucose band of the input step (calibrate_closed_bg.py); none unless fitted
        bb = ck.get("calib_bg_band")
        self.bg_band = (np.asarray(bb["bands"]), np.asarray(bb["offset"])) if bb else None
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
                              float(os.environ.get("SLOW_SCALE", "1")) *   # slow-state dial
                              (float(np.median(list(slow.get("scale", {1: 1.0}).values()))) if self.drawn else slow.get("scale", {}).get(alias, 1.0)), seed) if slow else None
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
        cr = [c for c in self.carbs_real if _ts(c.get("entryDate") or c["startDate"]) <= t0]
        bdr = self.bd_real[self.bd_real.t <= t0]
        if self.v3m:
            g, X, Yh = (D3M3 if self.v3m3 else D3M).build(hist, mr, bdr, cr, self.geq, self.features, self.isf)
        else:
            g, X, _ = D3.build(hist, mr, self.corr_real[self.corr_real.t <= t0] if len(self.corr_real) else self.corr_real,
                               bdr, cr, self.geq, self.features, self.isf)
        # recent actions, for the v3m inputs (since_entry, unbolused grams, units in the last 3 h)
        w3 = t0 - pd.Timedelta(hours=3)
        self.entries = [(_ts(c.get("entryDate") or c["startDate"]), float(c["grams"])) for c in cr
                        if _ts(c.get("entryDate") or c["startDate"]) > w3 and float(c["grams"]) > 0]
        self.bols = [(r.t, float(r.requested)) for r in bdr.itertuples() if r.t > w3 and r.requested and r.requested > 0]
        ce = [_ts(c.get("entryDate") or c["startDate"]) for c in cr if float(c["grams"]) > 0]
        self.last_entry = max(ce) if ce else None
        for f in self.drop:
            X[:, self.F[f]] = 0.0
        with torch.no_grad():
            o_w, self.h = self.net(torch.from_numpy(X[-WARMUP:])[None], self.pid)
        if getattr(self, "v4", False):   # two-stream: the latent outside stream's state, filtered over the real warm-up, then drawn
            yw = torch.from_numpy(Yh[-WARMUP:, D3M3.TARGETS.index("bgice")])   # row i holds slot i+1's value, as out[i] predicts
            mpost, Ppost = self.net.filter_state(o_w, yw)
            L = torch.linalg.cholesky(Ppost + 1e-8 * torch.eye(2))
            self.fs = (mpost + L @ torch.randn(2, generator=torch.Generator().manual_seed(int(self.seed_v4)))).tolist()
        self.xbuf = [torch.from_numpy(r)[None, None] for r in X[-WARMUP:]]
        self.t = hist.t1.iloc[-1]; self.bg = float(hist.bg1.iloc[-1]) - self.e     # reported = real CGM at start
        m_, s_ = params(mr.peak_h.to_numpy() + 2.5 / 60, mr.dur_h.to_numpy()) if len(mr) else ([], [])
        for i, r in enumerate(mr.itertuples()):
            if (t0 - r.onset) < pd.Timedelta(hours=12):
                self.pulses.append((r.onset, r.size_g * self.geq, m_[i], s_[i]))
        # PLANT_REAL_MEALS=1 (diagnostic): the person's real meals (labeled pulses at their onsets), carb entries and manual boluses
        # (requested units) replayed; the generator supplies background ICE only
        self.real_meals = os.environ.get("PLANT_REAL_MEALS") == "1"
        if self.real_meals:
            mall = pd.read_parquet(ROOT / "meals" / f"{self.alias}.parquet"); ma, sa = params(mall.peak_h.to_numpy() + 2.5 / 60, mall.dur_h.to_numpy())
            for i, r in enumerate(mall.itertuples()):
                if r.onset > t0:
                    self.pulses.append((r.onset, r.size_g * self.geq, ma[i], sa[i]))
                    self.actions_log.append(dict(t=r.onset, kind="meal", size_g=r.size_g, peak_h=r.peak_h + 2.5 / 60, dur_h=r.dur_h, onset=r.onset))
            for c in self.carbs_real:
                te = _ts(c.get("entryDate") or c["startDate"])
                if te > t0 and float(c["grams"]) > 0:
                    self.due.append((te, "carb", float(c["grams"])))
            bd = pd.read_parquet(ROOT / "bolus_decisions.parquet"); bd = bd[(bd.alias == self.alias) & (bd.requested > 0)]
            bd = bd.assign(s=bd.t.dt.floor("5min")).groupby("s").requested.max()
            for tb, u in bd.items():
                if _ts(tb) > t0:
                    self.due.append((_ts(tb), "bolus", dict(units=float(u))))
        last = X[-1]; F = self.F
        self.bgice = float(last[F["bgice"]]) if "bgice" in F else 0.0
        self.own_bg = []                                          # (t, background ICE scaled) for the dataset_v3m.OWN_MEANS channels
        if "bgice_24h" in F:
            ok = X[:, F["bgice_ok"]] > 0.5
            self.own_bg = [(ti, float(v)) for ti, v, o in zip(g.index[-len(X):][-288:], X[-288:, F["bgice"]], ok[-288:]) if o]
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
        if "iob_net" in F:
            x[F["iob_net"]] = self.isf * max(self.ins.iob(t) - self.base_iob, 0.0) / 100
        x[F["pulse"]] = self._pulse_rate(t) / ICE_SCALE
        x[F["since_meal"]] = min(self.since_meal, 24) / 24; x[F["last_size"]] = self.last_size / 50; x[F["n_3h"]] = n3 / 3
        x[F["carbs"]] = self.slot_carbs / 50; x[F["bolus"]] = self.slot_bolus / 5
        x[F["since_bolus"]] = min(self.since_bolus, 24) / 24
        if "since_entry" in F:                    # dataset_v3m.action_inputs
            x[F["since_entry"]] = min((t - self.last_entry).total_seconds() / 3600, 24) / 24 if self.last_entry is not None else 1.0
            lb = max([bt for bt, _ in self.bols], default=None)
            x[F["unbolused"]] = sum(g for et, g in self.entries if t - et < pd.Timedelta(hours=3) and (lb is None or et > lb)) / 50
            x[F["bolus_3h"]] = sum(u for bt, u in self.bols if t - bt < pd.Timedelta(hours=3)) / 5
        for k, n in (("bgice_6h", 72), ("bgice_24h", 288)):     # dataset_v3m.OWN_MEANS: own background over the last 6 / 24 h
            if k in F:
                w = [v for tt, v in self.own_bg if (t - (tt.tz_convert("UTC") if getattr(tt, "tzinfo", None) else tt.tz_localize("UTC"))) <= pd.Timedelta(minutes=5 * n)]
                x[F[k]] = float(np.mean(w)) if len(w) >= n // 6 else 0.0
        if "entered_unabsorbed" in F:             # dataset_v3m.entered_since_meal: an entry the pulse has not followed yet
            lm = max(self.anchor_times, default=None)
            x[F["entered_unabsorbed"]] = sum(g for et, g in self.entries if t - et < pd.Timedelta(hours=3) and (lm is None or et >= lm)) / 50
        x[F["hour_sin"]], x[F["hour_cos"]] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
        x[F["dow_sin"]], x[F["dow_cos"]] = np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)
        return torch.from_numpy(x)[None, None], hour, dow

    def _bolus(self, s, prefix):
        if bool(s[f"{prefix}_mode"][0]):
            return dict(units=float(np.clip(np.exp(float(s[f"{prefix}_lu"][0])), 0.05, 30)))
        return dict(ratio=float(np.clip(np.exp(float(s[f"{prefix}_lr"][0])), 0.0, 5.0)))

    def _draw_m(self, s, t, x):
        """v3m: a meal pulse, a carb entry and a manual bolus, each its own draw (all due now)."""
        if self.real_meals:
            return
        if bool(s["meal"][0]):
            size = float(np.clip(np.exp(float(s["m_lsize"][0])), 5, 250))
            lpk = float(s["m_lpeak"][0])
            if self.peak_state is not None and float(x[0, -1, self.F["bg_ok"]]) > 0.5:
                lpk += float(self.peak_state[1][int(np.searchsorted(self.peak_state[0], float(x[0, -1, self.F["bg"]]) * 100, side="right"))])
            peak = float(np.clip(np.exp(lpk), 5 / 60, 4)); dur = float(np.clip(np.exp(float(s["m_ldur"][0])), 0.25, 10))
            m, sd = params(peak, dur)
            self.pulses.append((t, size * self.geq, float(m), float(sd)))
            self.anchor_times.append(t); self.since_meal = 0.0; self.last_size = size
            self.actions_log.append(dict(t=t, kind="meal", size_g=size, peak_h=peak, dur_h=dur))
        entry = bool(s["entry"][0])
        # announcement dial: a meal the person would log is logged with probability ANNOUNCE; otherwise its pulse still
        # comes, but the carb entry and the bolus that goes with it are dropped (eating unchanged, logging and dosing not)
        ann = entry and (self.announce >= 1 or self.rng_ann.random() < self.announce)
        if entry:
            if ann:
                self.due.append((t, "carb", float(np.clip(np.exp(float(s["e_lg"][0])), 1, 250))))
            # v3m3: an entry that starts a meal brings its pulse; one that joins a meal with none begun in 2 h starts one
            if self.v3m3 and (bool(s["e_new"][0]) or not any(t - a < pd.Timedelta(hours=2) for a in self.anchor_times)):
                size = float(np.clip(np.exp(float(s["e_lsize"][0])), 5, 250))
                peak = float(np.clip(np.exp(float(s["e_lpeak"][0])), 5 / 60, 4)); dur = float(np.clip(np.exp(float(s["e_ldur"][0])), 0.25, 10))
                m, sd = params(peak, dur)
                on = t + pd.Timedelta(minutes=self.eoff_scale * float(np.clip(np.expm1(float(s["e_off"][0])), 0, 120)))
                self.pulses.append((on, size * self.geq, float(m), float(sd)))
                self.anchor_times.append(t); self.since_meal = 0.0; self.last_size = size
                self.actions_log.append(dict(t=t, kind="meal", size_g=size, peak_h=peak, dur_h=dur, announced=ann, from_entry=True, onset=on))
        if bool(s["bolus"][0]) and not (entry and not ann):
            self.due.append((t, "bolus", self._bolus(s, "b")))

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
                if self.xlog is not None:
                    self.xlog.append(x[0, -1].numpy().copy())
                out, self.h = self.net(x, self.pid, self.h)
                self.xbuf.append(x); self.xbuf = self.xbuf[-WARMUP:]; self.since_rewarm += dt_h
                for k, b in self.calib.items():
                    if k in out and not (self.v3m and k in ("entry", "bolus", "b_with", "b_alone")):
                        out[k] = out[k] + b
                if self.meal_state is not None and float(x[0, -1, self.F["bg_ok"]]) > 0.5:
                    bands, trends, off = self.meal_state
                    i = int(np.searchsorted(bands, float(x[0, -1, self.F["bg"]]) * 100, side="right"))
                    j = int(np.searchsorted(trends, float(x[0, -1, self.F["bg_trend"]]) * 2, side="right"))
                    out["meal"] = out["meal"] + float(off[i, j])
                s = self.net.sample(out, {k: v for k, v in self.calib.items() if k in ("entry", "bolus", "b_with", "b_alone")}) if self.v3m else self.net.sample(out)
            self.slot_carbs = 0.0; self.slot_bolus = 0.0
            self.since_meal += dt_h; self.since_bolus += dt_h
            if self.v3m:
                self._draw_m(s, t, x)
            elif bool(s["meal"][0]):
                size = float(np.clip(np.exp(float(s["m_lsize"][0])), 5, 250))
                lpk = float(s["m_lpeak"][0])
                if self.peak_state is not None and float(x[0, -1, self.F["bg_ok"]]) > 0.5:
                    lpk += float(self.peak_state[1][int(np.searchsorted(self.peak_state[0], float(x[0, -1, self.F["bg"]]) * 100, side="right"))])
                peak = float(np.clip(np.exp(lpk), 5 / 60, 4))
                dur = float(np.clip(np.exp(float(s["m_ldur"][0])), 0.25, 10))
                m, sd = params(peak, dur)
                on = t + pd.Timedelta(minutes=float(np.clip(np.expm1(float(s["m_onset"][0])), 0, 120)))
                self.pulses.append((on, size * self.geq, float(m), float(sd)))
                self.anchor_times.append(t); self.since_meal = 0.0; self.last_size = size
                t_entry = None
                if bool(s["m_ann"][0]):
                    g = float(np.clip(np.exp(float(s["m_lg"][0])), 1, 250))
                    t_entry = t + pd.Timedelta(minutes=float(np.clip(np.expm1(float(s["m_entry"][0])), 0, 120)))
                    self.due.append((t_entry, "carb", g))
                if bool(s["m_hasbol"][0]):
                    b = self._bolus(s, "m")
                    t_bol = t + pd.Timedelta(minutes=float(np.clip(np.expm1(float(s["m_bolus"][0])), 0, 120)))
                    # the bolus calculator doses for carbs entered with it: a calculator bolus drawn
                    # before its own entry would see no carbs and deliver ~0 (29% of drawn meal boluses)
                    if self.couple_meal_bolus and t_entry is not None and "ratio" in b:
                        t_bol = max(t_bol, t_entry)
                    self.due.append((t_bol, "bolus", b))
                self.actions_log.append(dict(t=t, kind="meal", size_g=size, peak_h=peak, dur_h=dur,
                                             announced=bool(s["m_ann"][0]), meal_bolus=bool(s["m_hasbol"][0])))
            if not self.v3m and bool(s["corr"][0]):
                self.due.append((t, "bolus", self._bolus(s, "c")))
                self.actions_log.append(dict(t=t, kind="correction"))
            # actions now due
            keep = []
            for due_t, kind, pay in self.due:
                if due_t > t:
                    keep.append((due_t, kind, pay)); continue
                if kind == "carb":
                    carbs.append(dict(t=iso(t), grams=round(pay, 1), absorption_s=10800))
                    self.slot_carbs += pay; self.entries.append((t, pay)); self.last_entry = t
                    self.actions_log.append(dict(t=t, kind="carb", grams=pay))
                else:
                    boluses.append(dict(t=iso(t), **pay)); self.since_bolus = 0.0
                    self.bols.append((t, pay.get("units", 2.0)))
                    self.slot_bolus += pay.get("units", 2.0)
                    self.actions_log.append(dict(t=t, kind="bolus_units" if "units" in pay else "bolus_ratio", **pay))
            self.due = keep
            bgice = float(s["bgice"][0])
            if self.v4:   # two-stream draw: expected outside level + reaction to the observable state + latent persistence
                pf, ps, qs = [float(v) for v in self.net.phis()]
                sg = float(out["lsig"][0, -1].exp()); n5 = max(1, round(dt_h * 12))
                for _ in range(n5):
                    self.fs[0] = pf * self.fs[0] + sg * np.sqrt(1 - pf * pf) * self.rng_v4.standard_normal()
                    self.fs[1] = ps * self.fs[1] + np.sqrt(qs) * self.rng_v4.standard_normal()
                bgice = float(out["mu"][0, -1]) + float(out["react"][0, -1]) + self.fs[0] + self.fs[1]
            if self.bg_spread != 1.0:   # shrink the draw's deviation from the predicted mean (closed-loop spread calibration)
                lg_, mu_, _ = out["bgice"][0, -1].split(self.net.K_ICE)
                m_ = float((torch.softmax(lg_, -1) * mu_).sum())
                bgice = m_ + self.bg_spread * (bgice - m_)
            if self.bgice_rho > 0:   # correlated draw: the model's distribution this step, at a quantile that follows an AR(1)
                rho = self.bgice_rho ** (dt_h * 12)
                self.bg_z = rho * self.bg_z + np.sqrt(1 - rho ** 2) * self.rng_z.standard_normal()
                bgice = mdn_quantile(out["bgice"][0, -1], self.net.K_ICE, float(ndtr(self.bg_z)))
            if self.near_low_bgice and (float(x[0, -1, self.F["heading_low"]]) > 0.5 or float(x[0, -1, self.F["bg"]]) * 100 < 70):
                bgice += self.near_low_bgice / ICE_SCALE
            if self.bg_band is not None and float(x[0, -1, self.F["bg_ok"]]) > 0.5:
                bgice += float(self.bg_band[1][int(np.searchsorted(self.bg_band[0], float(x[0, -1, self.F["bg"]]) * 100, side="right"))]) / ICE_SCALE
            if self.real_bg is not None:
                k_ = self.real_bg.index.searchsorted(t.floor("5min"))
                if k_ < len(self.real_bg) and self.real_bg.index[k_] == t.floor("5min") and np.isfinite(self.real_bg.iloc[k_]):
                    bgice = float(self.real_bg.iloc[k_]) / ICE_SCALE
            if self.feedback == "mean":
                lg_, mu_, _ = out["bgice"][0, -1].split(self.net.K_ICE)
                self.bgice = float((torch.softmax(lg_, -1) * mu_).sum())
            else:
                self.bgice = bgice
            if "bgice_24h" in self.F:
                self.own_bg = [(tt, v) for tt, v in self.own_bg if (t - (tt.tz_convert("UTC") if getattr(tt, "tzinfo", None) else tt.tz_localize("UTC"))) <= pd.Timedelta(hours=24)] + [(t, self.bgice)]
            pulse = self._pulse_rate(t)
            u = self.slow.step(dt_h) if self.slow else 0.0
            ice = bgice * ICE_SCALE + u + pulse
            mc = self.mc_amp * self.isf * self.act_typ * np.sin(2 * np.pi * (t.value / 8.64e13) / 28.0 + self.mc_phase) if self.mc_amp else 0.0
            ice += mc
            act = absorbed / dt_h
            if self.ins_gain != 1.0:   # insulin above / below the person's typical rate acts at a gain (PATIENT_INSULIN_GAIN)
                act = self.act_typ + self.ins_gain * (act - self.act_typ)
            self.bg = max(self.bg + (ice - self.isf * act) * dt_h, 20.0)
            j = self.steps.t1.searchsorted(t)
            near = [k for k in (j - 1, j) if 0 <= k < len(self.steps) and abs((self.steps.t1.iloc[k] - t).total_seconds()) < 600]
            k = min(near, key=lambda k: abs((self.steps.t1.iloc[k] - t).total_seconds())) if near else None
            # a CGM gap: resume from the field reading, as the replay plant and the engine do. Inside a field disruption,
            # follow the field: the harness delivers what the pump recorded, and a long one (i061: 14 days the field record
            # fills with scheduled basal, the dose input has none) drove generated glucose into the thousands (v3k and v3m4)
            # and into the closed-loop calibrations; outcomes leave those windows out anyway
            if k is not None and np.isfinite(self.steps.bg1.iloc[k]) and (dt_h > GAP_H or (self.follow_disrupted and bool(self.steps.disrupted.iloc[k]))):
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
            self.entries = [e for e in self.entries if (t - e[0]) < pd.Timedelta(hours=3)]
            self.bols = [b for b in self.bols if (t - b[0]) < pd.Timedelta(hours=3)]
            self.log.append(dict(t1=t, dt=dt_h * 60, ice=ice, bgice=bgice * ICE_SCALE + u + mc, pulse=pulse, slow=u, cycle=mc, bg1=self.bg + self.e + self.c, e=self.e, comp=self.c, comp_missing=self.c_miss,
                                 iob=self.ins.iob(t), ins_activity_uhr=absorbed / dt_h, hour=hour, dow=dow))
            self.t = t
            if len(self.log) % 288 == 0:
                self.ins.prune(t)
            bgs.append(None if self.c_miss else min(max(self.bg + self.e + self.c, LOW), HIGH))
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
        if self.xlog:
            pd.DataFrame(np.array(self.xlog), columns=self.features).to_parquet(str(path) + ".x.parquet", index=False)
        with open(str(path) + ".doses.json", "w") as f:
            json.dump(self.doses_log, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alias", required=True); ap.add_argument("--ckpt", required=True)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--log", required=True)
    ap.add_argument("--feedback", choices=["mean", "sample"], default=os.environ.get("PLANT_FEEDBACK", "mean"))
    ap.add_argument("--noise", help="level-noise parameters (json from fit_noise)")
    ap.add_argument("--slow", help="slow-level parameters (json from fit_slow, optional per-alias 'scale')")
    ap.add_argument("--compression", help="compression layer fit json (fit_layer.py); templates parquet beside it")
    ap.add_argument("--compression-scale", type=float, default=1.0, help="dial on the compression rate (0 = off)")
    ap.add_argument("--rewarm-h", type=float, default=0.0, help="rebuild the GRU state over the last 24 h every N hours (0 = never)")
    ap.add_argument("--couple-meal-bolus", action="store_true", help="a meal's calculator bolus no earlier than its carb entry")
    ap.add_argument("--no-follow-disrupted", action="store_true", help="keep generating glucose through field disruptions")
    a = ap.parse_args()
    plant = PlantV3(a.alias, a.ckpt, a.seed, a.feedback, json.load(open(a.noise)) if a.noise else None, a.rewarm_h,
                    json.load(open(a.slow)) if a.slow else None,
                    (json.load(open(a.compression)), pd.read_parquet(a.compression.replace("_layer.json", "_templates.parquet")),
                     a.compression_scale) if a.compression else None)
    plant.couple_meal_bolus = a.couple_meal_bolus
    plant.follow_disrupted = not a.no_follow_disrupted
    for line in sys.stdin:
        if line.strip():
            sys.stdout.write(json.dumps(plant.advance(json.loads(line))) + "\n"); sys.stdout.flush()
    plant.write_log(a.log)


if __name__ == "__main__":
    main()
