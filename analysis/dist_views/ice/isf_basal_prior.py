#!/usr/bin/env python3
"""Option 3 with a BASAL-based prior instead of the TDD rule.

Daily insulin carries meal insulin, so the TDD rule predicts a stronger ISF for
a bigger eater with the same sensitivity (isf_departure / variants showed the
fit's departure from it tracking announced carbs, and the schedules' too).

  fb        measured fasting basal: median insulin absorbed per hour over base
            fasting steps (ice_first._quiet_mask). No ISF enters.
  basal rule  ISF = K / fb^b, fitted once across people (log scheduled ISF on
            log fb, whole record), applied to each half's fb.
  E_basal   the fasting regression C (base fasting, as before) shrunk toward
            the basal rule, levelled to the scheduled median — the
            isf_fasting_variants.shrink procedure with B replaced.
E_tdd (the TDD-rule prior) is recomputed alongside for comparison.

Similar people are scored two ways: nearest neighbour on (log TDD, age) and on
(log fasting basal, age).

Quiet steps also exclude every bin the ICE bad-data screen flags (ice_raw.EXCLUDE:
disruptions, unrecorded insulin, clamps, jumps, compression, site/pod changes,
failing sites, occlusions, fast glucose). Set ISF_NO_SCREEN=1 for the unscreened fit.

Output: ice/isf_basal_prior.csv, ice/isf_basal_prior_score.csv
"""
from __future__ import annotations
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
np.seterr(all="ignore")
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa
from ice_first import _quiet_mask  # noqa
from isf_shrink import fit  # noqa
from isf_fasting_variants import shrink, icc  # noqa
from ice_raw import excluded_on_grid  # noqa
import os
EXCL = os.environ.get("ISF_NO_SCREEN") != "1"   # screen on by default

H = 12


def person(alias):
    p = S.load(alias)
    p = p[p["bg"].notna() | p["v"].notna()]
    q = _quiet_mask(p)
    if EXCL:                                   # the ICE bad-data screen (ice_raw.EXCLUDE)
        q &= ~excluded_on_grid(alias, p.index)
    u = p["ia_abs"].to_numpy() / p["isf"].to_numpy() * H        # U/hr absorbed
    week = ((p.index - p.index[0]).days // 7).to_numpy()
    r = {"alias": alias}
    for name, sel in (("all", np.ones(len(p), bool)), ("h1", week % 2 == 0), ("h2", week % 2 == 1)):
        r[f"C_{name}"], r[f"se_{name}"], r[f"nblk_{name}"] = fit(p, q, sel)
        m = q & sel & np.isfinite(u)
        r[f"fb_{name}"] = np.median(u[m]) if m.sum() > 500 else np.nan
    return r


def nn_score(d, col, keys):
    q = d[keys + [col]].dropna(); q = q[q[col] > 0]
    z = np.column_stack([np.log(q[keys[0]]), q[keys[1]]]); z = (z - z.mean(0)) / z.std(0)
    D = ((z[:, None] - z[None]) ** 2).sum(-1); np.fill_diagonal(D, np.inf)
    lv = np.log(q[col].to_numpy())
    return 100 * (np.exp(np.median(np.abs(lv - lv[D.argmin(1)]))) - 1)


def score(d, e, prior):
    h = d[[f"{e}_h1", f"{e}_h2"]].dropna(); h = h[(h > 0).all(1)]
    lr = np.log(h.iloc[:, 1] / h.iloc[:, 0])
    lv = np.log(d[f"{e}_all"].dropna())
    rnd = np.abs(lv.to_numpy()[:, None] - lv.to_numpy()[None])
    dd = d[(d[f"{e}_all"] > 0) & d[f"{prior}_all"].notna()]
    dep = np.log(dd[f"{e}_all"] / dd[f"{prior}_all"])
    ra = stats.spearmanr(np.log1p(dd.carb_g_day), dep)
    rs = stats.spearmanr(np.log(dd.A_all / dd[f"{prior}_all"]), dep)
    return {"people": len(h), "ICC": icc(np.log(h.iloc[:, 0]), np.log(h.iloc[:, 1])),
            "halves gap %": 100 * (np.exp(np.median(np.abs(lr))) - 1),
            ">25% apart": (np.abs(lr) > np.log(1.25)).mean(),
            "similar TDD+age %": nn_score(d, f"{e}_all", ["tdd_all", "age_years"]),
            "similar basal+age %": nn_score(d, f"{e}_all", ["fb_all", "age_years"]),
            "random %": 100 * (np.exp(np.median(rnd[~np.eye(len(lv), dtype=bool)])) - 1),
            "dep~announcing rho": ra[0], "p ann": ra[1],
            "dep~schedule rho": rs[0], "p sched": rs[1],
            "median": d[f"{e}_all"].median()}


if __name__ == "__main__":
    co = S.cohort()
    with Pool(8) as pool:
        d = pd.DataFrame(pool.map(person, list(co.alias)))
    sp = pd.read_csv(S.OUT / "ice" / "isf_split.csv")[["alias", "A_all", "B_all", "B_h1", "B_h2", "tdd_all"]]
    d = d.merge(sp, on="alias").merge(co[["alias", "carb_g_day"]], on="alias")
    d = d.merge(pd.read_csv(S.OUT / "age.csv")[["alias", "age_years"]], on="alias", how="left")

    ok = d.fb_all > 0
    b, a = np.polyfit(np.log(d.fb_all[ok]), np.log(d.A_all[ok]), 1)
    K, BEXP = np.exp(a), b
    rule_r = stats.spearmanr(d.fb_all[ok], d.A_all[ok])[0]
    tdd_r = stats.spearmanr(d.tdd_all, d.A_all, nan_policy="omit")[0]
    for n in ("all", "h1", "h2"):
        d[f"Bb_{n}"] = K * d[f"fb_{n}"] ** BEXP

    et, hp_t = shrink(d)                                       # TDD prior (B)
    eb, hp_b = shrink(d.assign(**{f"B_{n}": d[f"Bb_{n}"] for n in ("all", "h1", "h2")}))
    d["E_tdd_all"], d["E_tdd_h1"], d["E_tdd_h2"] = et.E_all, et.E_h1, et.E_h2
    for n in ("all", "h1", "h2"):
        d[f"E_basal_{n}"] = eb[f"E_{n}"]
    d["w_basal"] = eb.w_all
    d.to_csv(S.OUT / "ice" / "isf_basal_prior.csv", index=False)
    # the fitted cohort parameters every ICE analysis reads (ice/isf_yardstick.py)
    import json
    pfile = S.OUT / "ice" / "isf_yardstick_params.json"
    prm = json.loads(pfile.read_text()) if pfile.exists() else {}
    prm.update({"basal_rule_K": float(K), "basal_rule_b": float(BEXP),
                "slope_offset_log": float(np.log(hp_b["level_C_over_B"])), "tau_log": float(hp_b["tau"]),
                "se_calibration": float(hp_b["se_calib"]), "level_factor": float(hp_b["level_factor"]),
                "min_blocks": 100, "fitted_on": int(len(d))})
    pfile.write_text(json.dumps(prm, indent=1))

    print(f"basal rule: ISF = {K:.0f} / fb^{-BEXP:.2f}  (fb = fasting U/hr absorbed, median "
          f"{d.fb_all.median():.2f});  schedule rank-corr with fb {rule_r:.2f}, with TDD {tdd_r:.2f}")
    print("TDD prior hyper:", {k: round(v, 3) for k, v in hp_t.items()})
    print("basal prior hyper:", {k: round(v, 3) for k, v in hp_b.items()},
          " weight on own median", round(eb.w_all.median(), 2))
    rows = [{"estimator": "B  TDD rule", **score(d, "B", "B")},
            {"estimator": "Bb basal rule", **score(d, "Bb", "Bb")},
            {"estimator": "E  shrunk to TDD rule", **score(d.rename(columns={"E_tdd_all": "Et_all", "E_tdd_h1": "Et_h1", "E_tdd_h2": "Et_h2"}), "Et", "B")},
            {"estimator": "Eb shrunk to basal rule", **score(d.rename(columns={"E_basal_all": "Eb_all", "E_basal_h1": "Eb_h1", "E_basal_h2": "Eb_h2"}), "Eb", "Bb")}]
    r = pd.DataFrame(rows)
    r.to_csv(S.OUT / "ice" / "isf_basal_prior_score.csv", index=False)
    pd.set_option("display.width", 260)
    print(r.round(3).to_string(index=False))
