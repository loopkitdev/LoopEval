"""Fit a donor's body sensitivities with the additive body itself (not Loop's insulin curve).

For each fasting window of a pilot donor (no carb entry and no manual bolus from 4 h before to the window's end, ice
screen `clean`, CGM 80–250 at the start), the donor's own body (sample_person on their template, no jitter) is driven by
the insulin the donor actually received (doses.json: basal segments and boluses) from 6 h before the window: during
those 6 h glucose is held on the CGM (an observer, so insulin action, counter-regulation and HAAF states follow the real
trace), then it runs free for 3 h on insulin alone. Two scales are fitted per donor by a grid search on a robust (Huber)
error against the CGM at 30–180 min: `k` on both insulin arms (Body.step si_mult: disposal si_d and EGP suppression se)
and `e` on basal EGP (egp_mult, on top of the donor's hourly need shape). Points after the CGM reaches 75 are dropped
(rescue and counter-regulation confounds). The fitted body = the template body with its sensitivities × k.

Closed-loop attenuation: Loop sets the insulin in answer to the glucose trend's own unobserved drivers, so the observed
change follows the body's prediction at a slope ~0.4–0.55 (i001 / i002 / i005, r 0.43–0.69) and k comes out low for
every donor — the same attenuation the ICE yardstick corrects with its cohort level factor (2.0). As there, the
per-person k carries the ranking and one cohort factor sets the level (LESSONS 262).

    python -m loopeval_analysis.patient_sim.fit_body OUT.csv [--aliases i001,i002] [--par 12] [--regression]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ICE = Path.home() / ".loop-eval/ice_v32"
TPL = Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot_logs.csv"
KS = np.exp(np.linspace(math.log(0.1), math.log(3.0), 18))
ES = np.array([0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35])
HIST, PRED, EVAL = 360, 180, (30, 60, 90, 120, 150, 180)
SEGMENTS = False      # --segments: the regression also per clock segment (N 0–6, B 6–11, L 11–17, D 17–24 local)


def _ts(s):
    return pd.Timestamp(s).value / 6e10


def windows(alias: str, max_n: int = 400):
    s = pd.read_parquet(ICE / "steps" / f"{alias}.parquet").sort_values("t1")
    tm = (s.t1.astype("int64") / 6e10).to_numpy(); g = s.bg1.to_numpy(float)
    off = float(np.median(((s.hour.to_numpy() * 60 - (tm % 1440)) + 720) % 1440 - 720))
    ev = np.sort(tm[(s.carbs_g.fillna(0) > 0).to_numpy() | (s.bolus_manual_u.fillna(0) > 0).to_numpy()])
    bad = tm[~s.clean.fillna(False).to_numpy(bool) | s.disrupted.fillna(False).to_numpy(bool)]
    out, last = [], -1e18
    for t0 in np.arange(tm[0] + HIST + 240, tm[-1] - PRED, 30.0):
        if t0 - last < PRED: continue
        if np.any((ev >= t0 - 240) & (ev <= t0 + PRED)) or np.any((bad >= t0) & (bad <= t0 + PRED)): continue
        w = (tm >= t0 - HIST) & (tm <= t0 + PRED)
        if w.sum() < (HIST + PRED) / 5 * 0.85: continue
        g0 = np.interp(t0, tm, g)
        if not (80 <= g0 <= 250): continue
        out.append(t0); last = t0
    rng = np.random.default_rng(0)
    if len(out) > max_n: out = sorted(rng.choice(out, max_n, replace=False))
    return np.array(out), tm, g, off


_STEPS: dict = {}


def insulin_minutes(alias: str, t_lo: float, t_hi: float):
    """Per-minute basal units and (minute, units) boluses over [t_lo, t_hi), from the ice steps (basal_u, with the
    export's gaps already filled by the scheduled basal, spread over each step; automatic and manual boluses at the
    step start). doses.json leaves those gaps empty, which reads as no insulin."""
    if alias not in _STEPS:
        s = pd.read_parquet(ICE / "steps" / f"{alias}.parquet").sort_values("t1")
        _STEPS[alias] = ((s.t0.astype("int64") / 6e10).to_numpy(), s.dt.to_numpy(float), s.basal_u.fillna(0).to_numpy(float),
                         (s.bolus_auto_u.fillna(0) + s.bolus_manual_u.fillna(0)).to_numpy(float))
    t0s, dts, bu, bo = _STEPS[alias]
    n = int(t_hi - t_lo); basal = np.zeros(n); bol = []
    sel = np.where((t0s + dts > t_lo) & (t0s < t_hi))[0]
    for i in sel:
        st = t0s[i] - t_lo; en = st + dts[i]
        i0, i1 = int(max(math.floor(st), 0)), int(min(math.ceil(en), n))
        if bu[i] > 0 and i1 > i0: basal[i0:i1] += bu[i] / (i1 - i0)
        if bo[i] > 0 and 0 <= st < n: bol.append((int(st), float(bo[i])))
    return basal, bol


def person_body(alias: str):
    from .person import sample_person
    T = pd.read_csv(TPL)
    P = sample_person(T, 0, alias=alias, jitter=0.0, egp_sat=True, prof_deliv=True, night_own=True)
    return P


def predict(P, prof, t0, tm, g, off, basal, bol, k, es):
    """Observer over HIST minutes, then free runs for each e in `es`; returns array (len(es), len(EVAL))."""
    from .physiology import Body
    b = Body(P.body, P.formulation); b.prime(b.basal_rate_u_per_h())
    bmap = {}
    for (mm, u) in bol: bmap.setdefault(mm, []).append(u)
    t_lo = t0 - HIST
    def hour_egp(m): return prof[int(((t_lo + m + off) % 1440) // 60)]
    for m in range(HIST):
        if basal[m] > 0: b.infuse(basal[m], b.minute)
        for u in bmap.get(m, ()): b.infuse(u, b.minute, omega=1.0, dose=u)
        b.g = float(np.interp(t_lo + m, tm, g))
        b.step(1.0, si_mult=k, egp_mult=hour_egp(m))
    b.g = float(np.interp(t0, tm, g))
    res = []
    for e in es:
        c = copy.deepcopy(b); row = []
        for m in range(HIST, HIST + PRED):
            if basal[m] > 0: c.infuse(basal[m], c.minute)
            for u in bmap.get(m, ()): c.infuse(u, c.minute, omega=1.0, dose=u)
            c.step(1.0, si_mult=k, egp_mult=e * hour_egp(m))
            if (m - HIST + 1) in EVAL: row.append(c.g)
        res.append(row)
    return np.array(res)


def huber(r, d=20.0):
    a = np.abs(r); return np.where(a <= d, 0.5 * r * r, d * (a - 0.5 * d))


def fit_alias(alias: str, halves: bool = False):
    try:
        P = person_body(alias)
        W, tm, g, off = windows(alias)
        if len(W) < 20: return dict(alias=alias, n=len(W))
        prof = np.asarray(P.truth["basal_profile"], float)
        obs = np.array([[np.interp(t0 + h, tm, g) for h in EVAL] for t0 in W])
        mask = np.ones_like(obs, bool)
        for i in range(len(W)):
            lo = np.where(obs[i] < 75)[0]
            if len(lo): mask[i, lo[0] + 1:] = False
        L = np.zeros((len(KS), len(ES), len(W)))
        for wi, t0 in enumerate(W):
            basal, bol = insulin_minutes(alias, t0 - HIST, t0 + PRED + 1)
            for ki, k in enumerate(KS):
                pr = predict(P, prof, t0, tm, g, off, basal, bol, k, ES)
                L[ki, :, wi] = (huber(pr - obs[wi]) * mask[wi]).sum(1)
        week = ((W - W[0]) // (7 * 1440)).astype(int)
        out = dict(alias=alias, n=len(W), isf_template=float(P.truth["isf"]), formulation=P.formulation)
        for name, sel in (("all", np.ones(len(W), bool)), ("h1", week % 2 == 0), ("h2", week % 2 == 1)):
            if sel.sum() < 10: continue
            tot = L[:, :, sel].sum(2); ki, ei = np.unravel_index(np.argmin(tot), tot.shape)
            out[f"k_{name}"] = float(KS[ki]); out[f"e_{name}"] = float(ES[ei])
        base = L[np.argmin(np.abs(KS - 1.0)), np.argmin(np.abs(ES - 1.0))].sum()
        out["loss_fit"] = float(L.reshape(len(KS) * len(ES), -1).sum(1).min()); out["loss_template"] = float(base)
        return out
    except Exception as ex:                                       # noqa: BLE001
        return dict(alias=alias, error=repr(ex)[:200])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--aliases", default=""); ap.add_argument("--par", type=int, default=8)
    a = ap.parse_args()
    al = [x for x in a.aliases.split(",") if x] or list(pd.read_csv(TPL).alias)
    with Pool(a.par) as pool:
        rows = pool.map(fit_alias, al)
    pd.DataFrame(rows).to_csv(a.out, index=False)
    print(pd.DataFrame(rows).describe().round(3).to_string())




# ---------------------------------------------------------------- regression form (LESSONS 262)
def body_effect_series(alias: str, P=None):
    """Run the donor's body over the whole record with glucose held on the CGM (observer), driven by the insulin the donor
    received (ice steps). Per minute, the insulin-driven glucose rate in the body's own terms at sensitivity 1:
    −(X_D·M(G)·risk − SI_D·Ib·Gb) + (EGP_ins − EGP_b)/VG, mg/dL/min (tissue uptake and EGP suppression relative to basal).
    Returns minute grid (absolute minutes) and the effect series."""
    from .physiology import Body
    P = P or person_body(alias)
    s = pd.read_parquet(ICE / "steps" / f"{alias}.parquet").sort_values("t1")
    tm = (s.t1.astype("int64") / 6e10).to_numpy(); g = s.bg1.to_numpy(float); k = np.isfinite(g); tg, gg = tm[k], g[k]
    off = float(np.median(((s.hour.to_numpy() * 60 - (tm % 1440)) + 720) % 1440 - 720))
    t_lo, t_hi = float(np.floor(tm[0])), float(np.floor(tm[-1]))
    basal, bol = insulin_minutes(alias, t_lo, t_hi)
    bmap = {}
    for (mm_, u) in bol: bmap.setdefault(mm_, []).append(u)
    prof = np.asarray(P.truth["basal_profile"], float)
    b = Body(P.body, P.formulation); b.prime(b.basal_rate_u_per_h()); p = b.p
    n = len(basal); eff = np.zeros(n)
    gi = np.interp(t_lo + np.arange(n), tg, gg)
    for m in range(n):
        if basal[m] > 0: b.infuse(basal[m], b.minute)
        for u in bmap.get(m, ()): b.infuse(u, b.minute, omega=1.0, dose=u)
        b.g = float(gi[m])
        b.step(1.0, egp_mult=prof[int(((t_lo + m + off) % 1440) // 60)])
        G = b.g; mmv = p.gb + p.kappa * (G - p.gb) if (G >= p.gb or not p.low_prop) else G
        egp_ins = p.egp_b * min(max(1.0 - p.se * b.xe, 0.0), 1.0 + p.se)
        eff[m] = -(b.xd * mmv * b.risk(G) - p.si_d * p.ib * p.gb) + (egp_ins - p.egp_b) / p.vg
    return t_lo + np.arange(n), eff, s, tm


def fit_alias_regression(alias: str):
    """OLS over fasting hourly blocks (the yardstick's mask): glucose change = a + b × the body's insulin-driven change.
    b = 1 when the donor's glucose follows the template body's insulin action exactly; b's spread across donors is the
    per-person information (closed-loop attenuation lowers every b alike). Also halves by alternate weeks."""
    try:
        P = person_body(alias)
        mins, eff, s, tm = body_effect_series(alias, P)
        ev_c = tm[(s.carbs_g.fillna(0) > 0).to_numpy()]; ev_b = tm[(s.bolus_manual_u.fillna(0) > 0).to_numpy()]
        def recent(ev):
            if not len(ev): return np.zeros(len(tm), bool)
            i = np.searchsorted(ev, tm, side="right") - 1
            return (i >= 0) & (tm - ev[np.maximum(i, 0)] < 240)
        v = s.v.to_numpy(float)
        q = (~recent(ev_c) & ~recent(ev_b) & ~s.disrupted.fillna(False).to_numpy(bool) & np.isfinite(v) & (np.abs(v) < 600)
             & s.clean.fillna(False).to_numpy(bool))
        dg = v * s.dt.to_numpy(float) / 60.0
        t0s = (s.t0.astype("int64") / 6e10).to_numpy(); dts = s.dt.to_numpy(float)
        ce = np.r_[0.0, np.cumsum(eff)]
        e_step = np.array([ce[int(min(max(a_ + d_ - mins[0], 0), len(eff)))] - ce[int(min(max(a_ - mins[0], 0), len(eff)))]
                           for a_, d_ in zip(t0s, dts)])
        n = len(s) // 12 * 12; mblk = q[:n].reshape(-1, 12).all(1)
        dv = np.nan_to_num(dg[:n]).reshape(-1, 12).sum(1); de = np.nan_to_num(e_step[:n]).reshape(-1, 12).sum(1)
        week = (((t0s[:n:12]) - t0s[0]) // (7 * 1440)).astype(int)
        out = dict(alias=alias, isf_template=float(P.truth["isf"]), formulation=P.formulation)
        hr = s.hour.to_numpy()[:n:12] % 24
        seg = np.select([hr < 6, hr < 11, hr < 17], ["N", "B", "L"], "D")     # Visentin's B / L / D segments plus night
        sels = [("all", np.ones(len(dv), bool)), ("h1", week % 2 == 0), ("h2", week % 2 == 1)]
        if SEGMENTS:     # per clock segment, and per segment by alternate-week halves (split-half reliability, LESSONS 335)
            sels += [(f"{g}{h}", (seg == g) & hs) for g in "NBLD" for h, hs in (("", np.ones(len(dv), bool)), ("_h1", week % 2 == 0), ("_h2", week % 2 == 1))]
        for name, sel in sels:
            mm_ = mblk & sel
            if mm_.sum() < (30 if len(name) <= 4 and name[0] in "NBLD" else 100) or np.std(de[mm_]) == 0: continue
            X = np.column_stack([np.ones(mm_.sum()), de[mm_]]); beta = np.linalg.lstsq(X, dv[mm_], rcond=None)[0]
            r = dv[mm_] - X @ beta; s2 = r @ r / (mm_.sum() - 2); se = np.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1])
            out[f"b_{name}"] = float(beta[1]); out[f"se_{name}"] = float(se); out[f"nblk_{name}"] = int(mm_.sum())
        return out
    except Exception as ex:                                       # noqa: BLE001
        return dict(alias=alias, error=repr(ex)[:200])


def main_regression():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--aliases", default=""); ap.add_argument("--par", type=int, default=8)
    a = ap.parse_args()
    al = [x for x in a.aliases.split(",") if x] or list(pd.read_csv(TPL).alias)
    with Pool(a.par) as pool:
        rows = pool.map(fit_alias_regression, al)
    pd.DataFrame(rows).to_csv(a.out, index=False)
    print(pd.DataFrame(rows).describe().round(3).to_string())


if __name__ == "__main__":
    import sys as _s
    if "--segments" in _s.argv:
        _s.argv.remove("--segments"); SEGMENTS = True
    if "--regression" in _s.argv:
        _s.argv.remove("--regression"); main_regression()
    else:
        main()
