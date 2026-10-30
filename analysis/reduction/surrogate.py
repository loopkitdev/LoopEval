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
           manual_tau > 0: the meal-bolus discount fades linearly to zero over manual_tau minutes from each bolus
           prop_temp: temp = b * clip((G_ev - temp_floor_bg) / (T - temp_floor_bg), 0, 1), G_ev = G_h - (net - carb) * ISF_T
           adaptive scale (ad_sp > 0): TDD above is TDD0 * m(t), log m integrating glucose error against the set
           point ad_sp (ad_k per mg/dL per day), ad_klo times faster below ad_lo, clipped to [ad_min, ad_max];
           basal_uh > 0: b = basal_uh (the person's pre-window background rate, tdd.basal_hat) instead of basal_frac TDD/24
           rc_k > 0: retrospective correction, D = ΔG_30 + ISF_T * (U absorbed in 30 min - b/2), G_h += clamp(rc_k D, ±rc_cap)
           iob_cap_h > 0: a bolus never lifts net IOB above iob_cap_h * TDD/24 (hours of average delivery)
           the correction ISF follows m ** ad_isf; the basal follows m ** ad_basal (0 = basal stays at its TDD0 value, only ISF adapts).
           User inputs (the only settings a surrogate may take; Pete 2026-10-30):
           use_target: T = midpoint of the request's "user_target" (the person's own target) instead of `target`;
           use_override: an active override's needs factor f scales the dose (b x f, ISF / f, carb ratio / f, as Loop's
           insulin-needs factor does) and its target replaces T. Either target is floored at target_min. t_bolus and
           ad_sp move with T (T - `target`); t_low does not. The adaptive scale does not learn while an override is on.
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

def features(m, curve, manual_tau=0.0):
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
    def absorbed(t0, t1):
        """U absorbed in (t0, t1] from every dose in the window."""
        tot = 0.0
        for s0, s1, u, kind, _a in m["doses"]:
            a0, a1 = ts(s0), ts(s1)
            if kind == "bolus" or a1 - a0 < 1: pts, w = np.array([a0]), u
            else:
                n = max(1, int(round((a1 - a0) / 300))); pts = a0 + (np.arange(n) + 0.5) * (a1 - a0) / n; w = u / n
            pts = pts[pts < t1]
            if len(pts): tot += w * float((curve.remaining((t0 - pts) / 60.0) - curve.remaining((t1 - pts) / 60.0)).sum())
        return tot
    k30 = gt >= gt[-1] - 30 * 60 - 30
    dG30 = float(gv[-1] - gv[k30][0]) if k30.sum() >= 2 else 0.0
    span30 = float((gt[-1] - gt[k30][0]) / 60.0) if k30.sum() >= 2 else 0.0
    ab30 = absorbed(gt[-1] - span30 * 60, gt[-1]) if span30 > 0 else 0.0
    iob = iob_manual = 0.0
    for s0, s1, u, kind, auto in m["doses"]:
        a0, a1 = ts(s0), ts(s1)
        if kind == "bolus" or a1 - a0 < 1:
            r = u * float(curve.remaining((t - a0) / 60.0))
            iob += r
            if not auto: iob_manual += r * (max(0.0, 1 - (t - a0) / 60.0 / manual_tau) if manual_tau > 0 else 1.0)
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
    return dict(G=G, s15=slope(15), s30=slope(30), iob=iob, iob_manual=iob_manual, cob=cob, age=(t - gt[-1]) / 60.0,
                dG30=dG30, span30=span30, ab30=ab30)

def floor_to(x, inc):
    return math.floor(x / inc + 1e-9) * inc if inc and inc > 0 else x

class TddPD:
    defaults = dict(tdd=40.0, isf_k=688.0, isf_e=0.74, basal_frac=0.45, target=110.0, t_low=80.0, t_bolus=120.0,
                    h=30.0, slope_cap=3.0, rise_cap=80.0, af=0.4, fall_gate=-1.0, withhold_u=0.3, peak=75.0,
                    manual_w=0.0, cr_k=0.0,
                    manual_tau=0.0, prop_temp=0, temp_floor_bg=80.0,
                    basal_uh=0.0, ad_basal=1.0, ad_isf=1.0, iob_cap_h=0.0, rc_k=0.0, rc_cap=150.0,
                    ad_sp=0.0, ad_k=0.0139, ad_lo=80.0, ad_klo=3.0, ad_min=0.33, ad_max=3.0,
                    use_target=0, use_override=0, target_min=87.0)
    def __init__(self, **p):
        self.p = {**self.defaults, **p}
        self.curve = ExpCurve(peak=self.p["peak"])
        self.ieq = self.curve.iob_eq()
        self.logm, self.last_t = 0.0, None
    def adapt(self, t, G, sp_shift=0.0, frozen=False):
        """Outcome-keyed scale: log m integrates glucose above the set point (+ad_k per mg/dL·day) and below ad_lo
        (ad_klo times faster, downward). Reads glucose only, never delivered insulin."""
        p = self.p
        if p["ad_sp"] <= 0: return 1.0
        if self.last_t is not None and not frozen:
            sp = p["ad_sp"] + sp_shift
            dt = min(max(t - self.last_t, 0), 1800) / 86400.0
            self.logm += dt * p["ad_k"] * ((G - sp) if G >= p["ad_lo"] else -p["ad_klo"] * (p["ad_lo"] - G) + (p["ad_lo"] - sp))
            self.logm = min(max(self.logm, math.log(p["ad_min"])), math.log(p["ad_max"]))
        self.last_t = t
        return math.exp(self.logm)
    def target_and_factor(self, m):
        """Correction target and the active override's needs factor (None = no override): the person's target when
        use_target, else `target`; an override's target and factor when use_override. Targets floored at target_min."""
        p = self.p; T = p["target"]; fac = None
        ut = m.get("user_target")
        if p["use_target"] and ut: T = (ut[0] + ut[1]) / 2
        ov = m.get("override") if p["use_override"] else None
        if ov:
            if ov.get("target_lo") is not None and ov.get("target_hi") is not None: T = (ov["target_lo"] + ov["target_hi"]) / 2
            fac = ov["factor"] if ov.get("factor") else 1.0
        return max(T, p["target_min"]), fac
    def __call__(self, m):
        p = self.p; f = features(m, self.curve, p["manual_tau"]); st = m["settings"]
        T, fac = self.target_and_factor(m)
        dT = T - p["target"]
        tdd = p["tdd"] * self.adapt(ts(m["t"]), f["G"], dT, frozen=fac is not None)
        fac = fac or 1.0
        f["scale"] = tdd / p["tdd"]; f["T"] = T; f["factor"] = fac
        isf = p["isf_k"] / (p["tdd"] * f["scale"] ** p["ad_isf"]) ** p["isf_e"] / fac
        b0 = p["basal_uh"] if p["basal_uh"] > 0 else p["basal_frac"] * p["tdd"] / 24.0
        b = b0 * f["scale"] ** p["ad_basal"] * fac
        s = max(-p["slope_cap"], min(p["slope_cap"], f["s15"]))
        Gh = f["G"] + s * p["h"]
        net = f["iob"] - p["manual_w"] * f["iob_manual"] - b * self.ieq
        # retrospective correction: 30-min glucose change the insulin model did not explain (insulin absorbed above
        # the basal need b lowers glucose by ISF_T per U), carried into the forecast like Loop's RC (effect ≈ rc_k x D)
        rc = 0.0
        if p["rc_k"] > 0 and f["span30"] >= 20:
            D = f["dG30"] + isf * (f["ab30"] - b * f["span30"] / 60.0)
            rc = max(-p["rc_cap"], min(p["rc_cap"], p["rc_k"] * D))
        f["rc"] = rc
        Gh = Gh + rc
        carb_u = f["cob"] / (p["cr_k"] / (tdd * fac)) if p["cr_k"] > 0 else 0.0
        need = (min(Gh, f["G"] + p["rise_cap"]) - T) / isf - net + carb_u
        bolus = 0.0
        if need > 0 and f["G"] >= p["t_bolus"] + dT and s > p["fall_gate"]:
            bolus = min(p["af"] * need, st.get("max_bolus") or 1e9)
            if p["iob_cap_h"] > 0:   # net insulin on board never above iob_cap_h hours of average delivery
                bolus = max(0.0, min(bolus, p["iob_cap_h"] * tdd / 24.0 - net))
        if p["prop_temp"]:
            # basal in proportion to where the IOB-aware forecast lands between temp_floor_bg and target
            Gev = min(Gh, f["G"] + p["rise_cap"]) - (net - carb_u) * isf
            temp = b * min(1.0, max(0.0, (Gev - p["temp_floor_bg"]) / max(T - p["temp_floor_bg"], 5.0)))
            if f["G"] < p["t_low"] or Gh < p["t_low"]: temp = 0.0
        else:
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
