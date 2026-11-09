"""Parity fixtures for the Swift port: closed-loop synthetic streams run through the Python reference
(analysis/reduction/adaptive.py, family tdd_pd), recorded as events + the reference's answer every cycle.

Each fixture is one JSON file: params, profile, the event streams (glucose samples, doses with the cycle that issued
them, carb entries with the cycle that entered them, override intervals, user target, delivery limits) and per-cycle
expected outputs. The Swift test rebuilds every request exactly as this script built it:
  glucose  = the last 40 samples at or before the cycle's sample time
  doses    = doses issued on earlier cycles whose start is later than (sample time - 7 h)
  carbs    = entries made on this cycle or earlier
  now      = sample time + 5 s
Body: unannounced/announced meals at 07:30 and 18:30 UTC (±20 min), 3.5 mg/dL per g over 2 h, its own ISF from
TDD 40, baseline need 0.8 U/h, sensor noise 1.5 mg/dL. Announced meals get a carb entry and a manual bolus of the
reference's own calculator answer. Run: ~/.venv/bin/python3 analysis/reduction/swift_fixtures.py (writes LoopAlgorithm/Tests/LoopAdaptiveTests/Fixtures)"""
import importlib.util, json, os, sys
from datetime import datetime, timezone
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location("adaptive", os.path.join(HERE, "adaptive.py"))
A = importlib.util.module_from_spec(sp); sp.loader.exec_module(A)
iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
PROFILE = dict(tdd=36.0, basal_uh=0.72, ad_sp=130.0)
CAND = dict(cr_k=500.0, prop_temp=1, rc_k=1.0, own_manual=1, ad_basal=1.0, ad_isf=0.0, ad_min=0.5, ad_max=2.0, ad_brake_h=12.0)

def run(name, extra, days, announce, overrides, user_target, suspend, seed):
    rng = np.random.default_rng(seed)
    t0 = 1_760_000_000 - 1_760_000_000 % 86400
    P = {**CAND, **PROFILE, **extra}
    c = A.TddPD(**P); curve = A.ExpCurve(); isf_body = 688 / 40 ** 0.74
    meals = [(t0 + d * 86400 + hh * 3600 + float(rng.normal(0, 1200)), float(rng.uniform(30, 70)), bool(rng.random() < announce))
             for d in range(days) for hh in (7.5, 18.5)]
    ov = [(t0 + d * 86400 + 14 * 3600, t0 + d * 86400 + 16 * 3600) for d in range(days)] if overrides else []
    limits = dict(max_bolus=6.0, bolus_inc=0.05, **({"suspend": suspend} if suspend else {}))
    G = 125.0; glu, doses, carbs, outs, entered = [], [], [], [], set()
    all_glu, all_doses, all_carbs = [], [], []
    for i in range(days * 288):
        t = t0 + i * 300
        act = sum(u * float(curve.remaining((t - 300 - A.ts(s0)) / 60) - curve.remaining((t - A.ts(s0)) / 60))
                  for s0, s1, u, k, au in doses)
        carb = sum(g * 3.5 * 300 / 7200 for mt, g, _ in meals if 0 <= t - mt < 7200)
        G = max(40.0, G + carb - isf_body * (act - 0.8 * 300 / 3600) + float(rng.normal(0, 1.5)))
        sample = [iso(t), round(G, 1)]; glu.append(sample); glu = glu[-40:]; all_glu.append(sample)
        doses = [x for x in doses if A.ts(x[0]) > t - 7 * 3600]
        new_entry = False
        for j, (mt, g, ann) in enumerate(meals):
            if ann and j not in entered and mt <= t:
                e = [iso(mt), round(g, 1), 10800]; carbs.append(e); all_carbs.append(dict(entry=e, cycle=i)); entered.add(j); new_entry = True
        m = dict(t=iso(t + 5), glucose=glu, doses=doses, carbs=carbs, settings=limits, loop=dict(bolus=0, temp_rate=0, iob=0))
        if user_target: m["user_target"] = user_target
        if any(a <= t < b for a, b in ov): m["override"] = dict(target_lo=140.0, target_hi=150.0, factor=0.8)
        r = c(m); f = r["_f"]
        outs.append(dict(bolus=r["bolus"], temp_rate=r["temp_rate"], manual_rec=r.get("manual_rec"), need=r["_need"],
                         scale=f["scale"], rc=f["rc"], hab=f.get("hab", 0.0), gsl_hold=f.get("gsl_hold", False)))
        issued = []
        if r["bolus"] > 0: issued.append([iso(t + 5), iso(t + 5), r["bolus"], "bolus", True])
        if new_entry and r.get("manual_rec", 0) > 0:
            issued.append([iso(t + 5), iso(t + 5), A.floor_to(r["manual_rec"], limits["bolus_inc"]), "bolus", False])
        issued.append([iso(t + 5), iso(t + 305), r["temp_rate"] / 12, "basal", True])
        for d_ in issued: doses.append(d_); all_doses.append(dict(dose=d_, cycle=i))
    fx = dict(name=name, params=P, start=t0, cycles=days * 288, limits=limits, user_target=user_target,
              overrides=[dict(start=a, end=b, target_lo=140.0, target_hi=150.0, factor=0.8) for a, b in ov],
              glucose=all_glu, doses=all_doses, carbs=all_carbs, expected=outs)
    path = os.path.join(HERE, "../../LoopAlgorithm/Tests/LoopAdaptiveTests/Fixtures", f"{name}.json")
    json.dump(fx, open(path, "w"))
    b = sum(o["bolus"] for o in outs); n_hold = sum(o["gsl_hold"] for o in outs)
    print(f"{name}: {len(outs)} cycles, auto bolus {b:.1f} U, manual entries {len(all_carbs)}, gsl holds {n_hold}, "
          f"scale {outs[-1]['scale']:.3f}, max |hab| {max(abs(o['hab']) for o in outs):.1f}, {os.path.getsize(path) / 1e6:.2f} MB")

run("candidate", {}, 4, 0.5, False, None, None, 1)
run("target_override", dict(use_target=1, use_override=1), 4, 0.5, True, [100.0, 110.0], None, 2)
run("gsl", dict(gsl=80.0, gsl_settings=1), 4, 0.5, False, None, 75.0, 3)
run("habit", dict(hab_k=0.4, hab_ref=0.3), 9, 0.0, False, None, None, 4)
run("habit_gsl_override", dict(hab_k=0.2, hab_ref=0.3, gsl=80.0, use_target=1, use_override=1), 8, 0.3, True, [105.0, 115.0], None, 5)
