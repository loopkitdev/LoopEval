"""Reduced-input surrogate dosing functions, run as a --candidate-external-controller process.

usage: python surrogate.py <family> '<json params>'
The process reads one decision request per line (protocol: Sources/EvalCore/Engine/ExternalControllerAdapter.swift)
and answers {"bolus": U, "temp_rate": U/h}. A surrogate never reads the request's "loop" block or the person's
schedules (basal / ISF / CR / target); it may read the safety limits (max bolus, max basal) and the pump increments.
Everything person-specific comes from `tdd` (U/day, measured on days BEFORE the scored window) and the params.

Families
  tdd_pd   predictive correction on an insulin-only forecast, every scale from TDD:
           ISF_T = isf_k / TDD^isf_e   (eda population fit 688 / TDD^0.74 by default)
           b     = basal_frac * TDD / 24                       U/h, the 'need' the temp falls back to
           G_h   = G + clamp(slope, ±slope_cap) * h            momentum over the next h minutes
           net   = IOB_abs - manual_w * IOB_manual - b * IOB_eq  insulin on board above steady basal; manual_w > 0
                                                          treats that share of a user bolus as already spent on food
           carb  = COB / (cr_k / TDD)  if cr_k > 0             optional: entered carbs not yet absorbed (linear),
                                                          at a TDD carb ratio (500-rule form)
           need  = (min(G_h, G + rise_cap) - T) / ISF_T - net + carb   U still owed to bring G_h to T
           bolus = af * need       when need > 0 and G >= T_bolus and slope > fall_gate
           temp  = 0               when G_h < T_low or need < -withhold_u ; else b
"""
import json, math, sys
from datetime import datetime, timezone
import numpy as np

def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()

class ExpCurve:
    """Loop's exponential insulin model: remaining fraction after t minutes (delay included)."""
    def __init__(self, peak=75.0, dur=360.0, delay=10.0):
        self.tp, self.td, self.delay = peak, dur, delay
        self.tau = peak * (1 - peak / dur) / (1 - 2 * peak / dur)
        self.a = 2 * self.tau / dur
        self.S = 1 / (1 - self.a + (1 + self.a) * math.exp(-dur / self.tau))
    def remaining(self, t):
        t = np.clip(np.asarray(t, float) - self.delay, 0, None)
        tau, td, a, S = self.tau, self.td, self.a, self.S
        r = 1 - S * (1 - a) * ((t ** 2 / (tau * td * (1 - a)) - t / tau - 1) * np.exp(-t / tau) + 1)
        return np.where(t >= td, 0.0, np.clip(r, 0, 1))
    def iob_eq(self):
        """IOB (in hours of rate) of a constant infusion that has run forever: ∫ remaining dt / 60."""
        t = np.arange(0, self.td + self.delay + 5, 1.0)
        return float(self.remaining(t).sum() / 60.0)

def features(m, curve):
    t = ts(m["t"])
    g = m["glucose"]
    gt = np.array([ts(x[0]) for x in g]); gv = np.array([x[1] for x in g], float)
    G = gv[-1]
    def slope(minutes):
        k = gt >= gt[-1] - minutes * 60 - 30
        if k.sum() < 2: return 0.0
        x = (gt[k] - gt[-1]) / 60.0; y = gv[k]
        return float(np.polyfit(x, y, 1)[0]) if np.ptp(x) > 0 else 0.0   # mg/dL per min
    # absolute insulin on board: boluses at their time, basal segments spread in 5-min pieces
    iob = iob_manual = 0.0
    for s0, s1, u, kind, auto in m["doses"]:
        a0, a1 = ts(s0), ts(s1)
        if kind == "bolus" or a1 - a0 < 1:
            r = u * float(curve.remaining((t - a0) / 60.0))
            iob += r
            if not auto: iob_manual += r
        else:
            n = max(1, int(round((a1 - a0) / 300)))
            mids = a0 + (np.arange(n) + 0.5) * (a1 - a0) / n
            mids = mids[mids < t]
            if len(mids): iob += u / n * float(curve.remaining((t - mids) / 60.0).sum())
    # carbs entered and not yet absorbed: linear absorption over each entry's time (default 3 h)
    cob = 0.0
    for c0, g_, ab in m["carbs"]:
        el = (t - ts(c0)) / 60.0; dur = (ab or 10800) / 60.0
        if 0 <= el < dur: cob += g_ * (1 - el / dur)
        elif el < 0: cob += g_
    return dict(G=G, s15=slope(15), s30=slope(30), iob=iob, iob_manual=iob_manual, cob=cob, age=(t - gt[-1]) / 60.0)

def floor_to(x, inc):
    return math.floor(x / inc + 1e-9) * inc if inc and inc > 0 else x

class TddPD:
    defaults = dict(tdd=40.0, isf_k=688.0, isf_e=0.74, basal_frac=0.45, target=110.0, t_low=80.0, t_bolus=120.0,
                    h=30.0, slope_cap=3.0, rise_cap=80.0, af=0.4, fall_gate=-1.0, withhold_u=0.3, peak=75.0,
                    manual_w=0.0, cr_k=0.0)
    def __init__(self, **p):
        self.p = {**self.defaults, **p}
        self.curve = ExpCurve(peak=self.p["peak"])
        self.ieq = self.curve.iob_eq()
    def __call__(self, m):
        p = self.p; f = features(m, self.curve); st = m["settings"]
        isf = p["isf_k"] / p["tdd"] ** p["isf_e"]
        b = p["basal_frac"] * p["tdd"] / 24.0
        s = max(-p["slope_cap"], min(p["slope_cap"], f["s15"]))
        Gh = f["G"] + s * p["h"]
        net = f["iob"] - p["manual_w"] * f["iob_manual"] - b * self.ieq
        carb_u = f["cob"] / (p["cr_k"] / p["tdd"]) if p["cr_k"] > 0 else 0.0
        need = (min(Gh, f["G"] + p["rise_cap"]) - p["target"]) / isf - net + carb_u
        bolus = 0.0
        if need > 0 and f["G"] >= p["t_bolus"] and s > p["fall_gate"]:
            bolus = min(p["af"] * need, st.get("max_bolus") or 1e9)
        temp = 0.0 if (Gh < p["t_low"] or need < -p["withhold_u"] or f["G"] < p["t_low"]) else b
        return dict(bolus=floor_to(bolus, st.get("bolus_inc")), temp_rate=temp,
                    _f=f, _need=need)

FAMILIES = {"tdd_pd": TddPD}

def main():
    fam = FAMILIES[sys.argv[1]](**(json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))
    log = open(sys.argv[3], "w") if len(sys.argv) > 3 else None
    for line in sys.stdin:
        m = json.loads(line)
        r = fam(m)
        if log: log.write(json.dumps({"t": m["t"], **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r["_f"].items()},
                                      "need": round(r["_need"], 4), "bolus": r["bolus"], "temp": r["temp_rate"],
                                      "loop_bolus": m["loop"]["bolus"], "loop_temp": m["loop"]["temp_rate"], "loop_iob": m["loop"]["iob"]}) + "\n")
        sys.stdout.write(json.dumps({"bolus": r["bolus"], "temp_rate": r["temp_rate"]}) + "\n"); sys.stdout.flush()

if __name__ == "__main__":
    main()
