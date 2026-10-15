"""Insulin formulations: how each one is absorbed from the subcutaneous depot.

The body's pharmacokinetics come from here, never from the controller's curve: Loop's exponential
presets are a SETTING (what the controller believes), the formulation is what the body does, and the
mismatch between them is part of what a simulation must reproduce (evidence/01 §3.1).

Structure per dose (physiology.Depot):
    delay τ → a fraction ψ enters a FAST compartment that empties into plasma at rate k_fast,
              the rest the standard chain Isc1 --kd--> Isc2 --ka2--> plasma.
A formulation is: τ (min), multipliers on the person's own kd and ka2, ψ and k_fast. The person's
own kd/ka2 carry between-person variability; the formulation shifts them. Rapid analogues are the
reference (multipliers 1, ψ 0).

The ultra-rapid parameters are FITTED (fit_formulations, below) to published clamp contrasts
against their parent analogue; the fitted values are written into FORMULATIONS with the targets
beside them so a refit is reproducible:
  Lyumjev vs lispro (Clin Pharmacokinet 2020, doi:10.1007/s40262-020-00903-0; T1D, n=80):
      appearance 6 min sooner; AUC 0–15 min ×7.2; AUC beyond 3 h ×0.60 (−39 to −41%).
  Fiasp vs aspart (Heise et al., Clin Pharmacokinet 2017;56:551, doi:10.1007/s40262-017-0514-8):
      onset of appearance ~5 vs ~11 min; AUC 0–30 min ×2.0; total AUC unchanged; late AUC ~×0.8.
Regular human insulin (slower; hexamer dissociation) is included for completeness: plasma tmax
~2× the analogue's [Home 2015, doi:10.1111/dom.12501, review values, unverified].
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Formulation:
    name: str
    tau: float              # min, delivery-to-depot delay
    kd_mult: float = 1.0
    ka2_mult: float = 1.0
    psi: float = 0.0        # fraction of each dose taking the fast route
    k_fast: float = 0.1     # 1/min, fast route into plasma
    loop_preset: str = "rapidActingAdult"   # the Loop curve a user of this insulin normally selects
    note: str = ""


FORMULATIONS: dict[str, Formulation] = {
    "lispro":   Formulation("lispro", tau=8.0, note="Humalog/Admelog. Reference (ReplayBG priors)."),
    "aspart":   Formulation("aspart", tau=8.0, note="NovoLog/NovoRapid. Treated as lispro-equivalent."),
    "glulisine": Formulation("glulisine", tau=7.0, note="Apidra. Slightly faster onset [unverified]."),
    # fitted 2026-10-15 by fit_formulations(); see module docstring for targets
    # fit result: AUC0-30 x2.00, AUC>3h x0.80, onset -7 min, total x1.00, plasma tmax 55 vs 64 min
    "fiasp":    Formulation("fiasp", tau=4.0, kd_mult=1.115, ka2_mult=1.047, psi=0.022, k_fast=0.080,
                            loop_preset="fiasp", note="fitted to Heise 2017 contrasts vs aspart"),
    # fit result: AUC0-15 x7.20, AUC>3h x0.60, onset -6 min, total x1.00, plasma tmax 44 vs 64 min
    "lyumjev":  Formulation("lyumjev", tau=4.0, kd_mult=1.848, ka2_mult=1.071, psi=0.022, k_fast=0.023,
                            loop_preset="lyumjev", note="fitted to Clin Pharmacokinet 2020 contrasts vs lispro"),
    "regular":  Formulation("regular", tau=10.0, kd_mult=0.5, ka2_mult=0.6,
                            note="human regular insulin; tmax ~2x analogue [unverified]"),
}

BRAND_TO_FORMULATION = {
    "humalog": "lispro", "admelog": "lispro", "lispro": "lispro",
    "novolog": "aspart", "novorapid": "aspart", "aspart": "aspart",
    "apidra": "glulisine", "fiasp": "fiasp", "lyumjev": "lyumjev",
}


def plasma_appearance(f: Formulation, kd: float = 0.030, ka2: float = 0.0137,
                      minutes: int = 600) -> list[float]:
    """Rate of insulin appearance in plasma (fraction of dose per minute) for one unit dose."""
    i1 = i2 = fast = 0.0
    out = []
    for m in range(minutes):
        if m == int(round(f.tau)):
            fast += f.psi; i1 += 1.0 - f.psi
        a1 = kd * f.kd_mult * i1; a2 = ka2 * f.ka2_mult * i2; af = f.k_fast * fast
        i1 -= a1; i2 += a1 - a2; fast -= af
        out.append(a2 + af)
    return out


def _plasma_conc(rate, ke=0.127):
    c, out = 0.0, []
    for r in rate:
        c += r - ke * c
        out.append(c)
    return out


def contrast(f: Formulation, ref: Formulation) -> dict:
    """The clamp metrics the fit targets, as ratios of f to ref (plasma-insulin AUCs)."""
    cf = _plasma_conc(plasma_appearance(f)); cr = _plasma_conc(plasma_appearance(ref))
    auc = lambda c, a, b: sum(c[a:b])
    onset = lambda c: next(i for i, v in enumerate(c) if v > 0.05 * max(c))
    return {"auc0_15": auc(cf, 0, 15) / auc(cr, 0, 15), "auc0_30": auc(cf, 0, 30) / auc(cr, 0, 30),
            "auc_gt180": auc(cf, 180, 600) / auc(cr, 180, 600), "auc_total": auc(cf, 0, 600) / auc(cr, 0, 600),
            "onset_shift": onset(cf) - onset(cr),
            "tmax": max(range(len(cf)), key=cf.__getitem__), "tmax_ref": max(range(len(cr)), key=cr.__getitem__)}


TARGETS = {
    "lyumjev": ("lispro", {"auc0_15": 7.2, "auc_gt180": 0.60, "onset_shift": -6.0}),
    "fiasp": ("aspart", {"auc0_30": 2.0, "auc_gt180": 0.80, "onset_shift": -6.0}),
}


def fit_formulations(names=("lyumjev", "fiasp")) -> dict[str, Formulation]:
    """Least-squares fit of (tau, kd_mult, ka2_mult, psi) to TARGETS (log-ratio residuals)."""
    import math
    from scipy.optimize import least_squares
    out = {}
    for name in names:
        refname, tgt = TARGETS[name]
        ref = FORMULATIONS[refname]

        def build(x):
            return Formulation(name, tau=x[0], kd_mult=x[1], ka2_mult=x[2], psi=x[3], k_fast=x[4],
                               loop_preset=FORMULATIONS[name].loop_preset)

        def resid(x):
            c = contrast(build(x), ref)
            r = []
            for k, v in tgt.items():
                r.append((c[k] - v) / 3.0 if k == "onset_shift" else math.log(c[k] / v))
            r.append(0.5 * math.log(c["auc_total"]))          # total exposure unchanged
            return r

        x0 = [ref.tau - 4, 1.2, 1.2, 0.1, 0.1]
        sol = least_squares(resid, x0, bounds=([0.5, 0.5, 0.5, 0.0, 0.02], [12, 4, 4, 0.6, 0.5]))
        f = build(sol.x)
        out[name] = (f, contrast(f, ref))
    return out


def get(name: str) -> Formulation:
    return FORMULATIONS[BRAND_TO_FORMULATION.get(name.lower(), name.lower())]


if __name__ == "__main__":
    for name, (f, c) in fit_formulations().items():
        print(name, {k: round(v, 4) if isinstance(v, float) else v for k, v in f.__dict__.items()})
        print("   ", {k: round(v, 3) if isinstance(v, float) else v for k, v in c.items()})
