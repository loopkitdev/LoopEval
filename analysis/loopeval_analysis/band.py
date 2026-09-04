"""Operating-band scoring (docs/FRONTIERS.md → Scoring; docs/GOALS.md).

A candidate is an improvement iff, with the insulin-needs dial free to move inside the
donor's OPERATING BAND (validated multiplier ± 0.1), it reaches a point that strictly
dominates the reference sweep (more TIR AND less lows). This module scores traces in
weekly BLOCKS so every headline number carries a paired block-bootstrap CI.

Typical use::

    ref  = {m: block_scores(f"std_m{m}.json", outages_csv=...) for m in MULTS}
    cand = {"uam90": {m: block_scores(f"uam90_m{m}.json", ...) for m in MULTS}, ...}
    table, points = band_report(ref, cand, op_mult=1.00)

Lows axis: ``t54`` unless the reference's in-band t54 is ≈0 (< ``t54_floor``), then
``t70`` (the geometry degenerates when the curve runs flat at zero).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple, Sequence

import numpy as np
import pandas as pd

from .scoring import magni_risk

from .frontier import lift as _lift, _ref_polyline
from .scoring import exclusion_mask

BLOCK_COLS = ["n", "in_range", "lt54", "lt70", "gt180", "gt250", "sum_bg", "sum_magni"]


# --------------------------------------------------------------------------- #
#  Per-trace block scoring                                                    #
# --------------------------------------------------------------------------- #

def counter_series(trace_path: str | Path, burnin_hours: float = 6.0,
                   outages_csv: Optional[str] = None, post_hours: float = 0.0,
                   tz="UTC") -> pd.Series:
    """The scored counterfactual BG series: burn-in skipped, disruption intervals
    excluded (interval only — ``post_hours=0`` is the project policy)."""
    t = json.loads(Path(trace_path).read_text())
    c = pd.DataFrame(t["counter"])
    c["t"] = pd.to_datetime(c["t"], utc=True)
    bg = c.set_index("t")["bg"].dropna().sort_index()
    cf = pd.to_datetime(t["intervalStart"], utc=True) + pd.Timedelta(hours=burnin_hours)
    bg = bg.loc[bg.index >= cf]
    if outages_csv:
        from .outage import read_outages_csv
        outs = read_outages_csv(outages_csv)
        if outs:
            excl = exclusion_mask(bg.index, outs, [], post_hours=post_hours)
            bg = bg[~excl.reindex(bg.index).fillna(False).to_numpy()]
    return bg


def block_scores(trace_path: str | Path, block_days: float = 7.0,
                 block_origin: Optional[pd.Timestamp] = None, **kw) -> pd.DataFrame:
    """Score a trace in fixed calendar blocks. Returns one row per block with raw
    sample counts (so blocks can be pooled/resampled exactly). ``block_origin``
    fixes the block grid across traces (default: the trace's intervalStart)."""
    bg = counter_series(trace_path, **kw)
    if block_origin is None:
        t = json.loads(Path(trace_path).read_text())
        block_origin = pd.to_datetime(t["intervalStart"], utc=True)
    blk = np.floor((bg.index - block_origin) / pd.Timedelta(days=block_days)).astype(int)
    df = pd.DataFrame({
        "block": blk, "n": 1,
        "in_range": ((bg >= 70) & (bg <= 180)).astype(int).to_numpy(),
        "lt54": (bg < 54).astype(int).to_numpy(),
        "lt70": (bg < 70).astype(int).to_numpy(),
        "gt180": (bg > 180).astype(int).to_numpy(),
        "gt250": (bg > 250).astype(int).to_numpy(),
        "sum_bg": bg.to_numpy(),
        # Magni risk is a per-sample quantity, so it sums in blocks and divides by n
        # exactly like the others — which is what lets it survive the block bootstrap.
        "sum_magni": magni_risk(bg.to_numpy()),
    })
    return df.groupby("block")[BLOCK_COLS].sum()


def pooled(blocks: pd.DataFrame, idx=None) -> dict:
    """Pool block rows (optionally a resampled index list) into outcome %s."""
    b = blocks if idx is None else blocks.reindex(idx)
    s = b[BLOCK_COLS].sum()
    n = float(s["n"]) or 1.0
    return {"TIR": 100 * s["in_range"] / n, "t54": 100 * s["lt54"] / n,
            "t70": 100 * s["lt70"] / n, "t180": 100 * s["gt180"] / n,
            "t250": 100 * s["gt250"] / n, "mean": s["sum_bg"] / n,
            "magni": s["sum_magni"] / n, "n": n}


# --------------------------------------------------------------------------- #
#  Geometry                                                                   #
# --------------------------------------------------------------------------- #

def _frame(sweep: Mapping[float, pd.DataFrame], idx=None, lows="t54") -> pd.DataFrame:
    rows = []
    for m, b in sorted(sweep.items()):
        p = pooled(b, idx)
        rows.append({"multiplier": float(m), "TIR": p["TIR"], "t54": p["t54"],
                     "t70": p["t70"], "mean": p["mean"], "magni": p["magni"], "lows": p[lows]})
    return pd.DataFrame(rows)


def _ref_for_lift(ref: pd.DataFrame) -> pd.DataFrame:
    # frontier.lift reads columns TIR and t54; feed it the chosen lows axis as "t54".
    return ref[["multiplier", "TIR", "lows"]].rename(columns={"lows": "t54"})


def dominates(ref: pd.DataFrame, tir: float, lows: float, samples: int = 200) -> bool:
    """Strict dominance: no point on the reference polyline has TIR >= and lows <=
    the candidate point (the candidate is below-and-right of the whole curve)."""
    P, _ = _ref_polyline(_ref_for_lift(ref))
    if P is None:
        return False
    for a, b in zip(P[:-1], P[1:]):
        s = np.linspace(0, 1, samples)[:, None]
        pts = a + s * (b - a)
        if np.any((pts[:, 0] >= tir - 1e-9) & (pts[:, 1] <= lows + 1e-9)):
            return False
    return True


def _interp_at(frame: pd.DataFrame, mult: float) -> Optional[pd.Series]:
    f = frame.sort_values("multiplier")
    m = f["multiplier"].to_numpy()
    if mult < m.min() - 1e-9 or mult > m.max() + 1e-9:
        return None
    out = {}
    for col in ("TIR", "t54", "t70", "mean", "magni", "lows"):
        out[col] = float(np.interp(mult, m, f[col].to_numpy()))
    return pd.Series(out)


# --------------------------------------------------------------------------- #
#  Report                                                                     #
# --------------------------------------------------------------------------- #

def band_report(ref: Mapping[float, pd.DataFrame],
                cands: Mapping[str, Mapping[float, pd.DataFrame]],
                op_mult: float, half_width: float = 0.1,
                lows_axis: str = "auto", t54_floor: float = 0.05,
                n_boot: int = 500, seed: int = 0,
                ci: Tuple[float, float] = (5, 95),
                ref_extra: float = 0.1) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Per-mechanism operating-band verdict with paired block-bootstrap CIs.

    The comparison stays IN THE OPERATING BAND on both sides: candidate points at
    op ± half_width are judged against the reference polyline restricted to
    op ± (half_width + ref_extra) — i.e. "better than any re-tune of the dial within
    ±0.2". A candidate point is never called dominant if its lows exceed the worst
    lows the in-band reference produces (it escaped the band upward, into a region
    the reference is not asked to cover). Without these two rules a hot candidate
    "dominates" the reference at ×1.5–2.0, where nobody operates (bddp03 UAM case).

    Returns ``(table, points)``. ``table`` has one row per mechanism:
      lows_axis, n_band (candidate points in band), band_lift (mean in-band lift),
      band_lift_lo/hi (bootstrap CI), frac_dominant (share of in-band points that
      strictly dominate the reference polyline), dominant_ci_lo (bootstrap lower
      bound of that share), dTIR_op / dt54_op / dt70_op (candidate − reference at the
      operating multiplier, interpolated) with CIs, and verdict:
        IMPROVES   — band_lift CI excludes 0 from above AND some in-band point dominates
        NEUTRAL    — CI straddles 0
        WORSE      — CI below 0
        UNDER-COVERED  — fewer than 3 candidate points in the band, or a NaN delta at op: the lift is
                         not computable from this sweep. Extend the multiplier grid to cover
                         op ± half_width. NEVER average this row into a cohort mean.
        DEGENERATE-REF — the in-band reference does not span both axes (TIR span < 1 pt, lows span
                         < 0.05, or lows-at-op < 0.10 on the t54 axis), so the axis-normalized lift is
                         meaningless. Read dTIR_op / dt54_op instead.
    ``points`` has every candidate sweep point with its lift and dominance flag.
    """
    rng = np.random.default_rng(seed)
    ref_full = _frame(ref, lows="t54")
    band = lambda f: f[(f["multiplier"] >= op_mult - half_width - 1e-9) &
                       (f["multiplier"] <= op_mult + half_width + 1e-9)]
    rw = half_width + ref_extra
    ref_band = lambda f: f[(f["multiplier"] >= op_mult - rw - 1e-9) &
                           (f["multiplier"] <= op_mult + rw + 1e-9)]
    if lows_axis == "auto":
        lows_axis = "t54" if band(ref_full)["t54"].max() >= t54_floor else "t70"
    ref_f = ref_band(_frame(ref, lows=lows_axis))
    if len(ref_f) < 2:
        raise ValueError("fewer than 2 reference points in the operating band")
    blocks = sorted(set.intersection(*[set(b.index) for b in ref.values()] +
                                     [set(b.index) for c in cands.values() for b in c.values()]))
    if not blocks:
        raise ValueError("no common blocks across traces")
    B = len(blocks)
    boots = [list(rng.choice(blocks, size=B, replace=True)) for _ in range(n_boot)]

    def stats(ref_frame, cand_frame):
        cb = band(cand_frame)
        lifts = [_lift(_ref_for_lift(ref_frame), r.TIR, r.lows) for r in cb.itertuples()]
        # strict dominance also requires being on the better side of the curve AND
        # inside the band's lows range — a point beyond the reference's extent is
        # not "dominant" just because the reference stops short of it.
        lows_cap = float(ref_frame["lows"].max()) + 1e-9
        dom = [l > 0 and r.lows <= lows_cap and dominates(ref_frame, r.TIR, r.lows)
               for r, l in zip(cb.itertuples(), lifts)]
        rop, cop = _interp_at(ref_frame, op_mult), _interp_at(cand_frame, op_mult)
        d = {k: (cop[k] - rop[k]) if (rop is not None and cop is not None) else np.nan
             for k in ("TIR", "t54", "t70", "mean", "magni")}
        return (float(np.mean(lifts)) if lifts else np.nan,
                float(np.mean(dom)) if dom else np.nan, d, lifts, dom, cb)

    rows, pts = [], []
    for name, sweep in cands.items():
        cf = _frame(sweep, lows=lows_axis)
        bl, fd, d, lifts, dom, cb = stats(ref_f, cf)
        for r, l, dm in zip(cb.itertuples(), lifts, dom):
            pts.append({"mechanism": name, "multiplier": r.multiplier, "TIR": r.TIR,
                        "t54": r.t54, "t70": r.t70, "mean": r.mean, "lift": l, "dominates": dm})
        bs_l, bs_d, bs_dT, bs_d54, bs_d70, bs_dM = [], [], [], [], [], []
        for idx in boots:
            rb, cbf = ref_band(_frame(ref, idx, lows=lows_axis)), _frame(sweep, idx, lows=lows_axis)
            l2, d2, dd, *_ = stats(rb, cbf)
            bs_l.append(l2); bs_d.append(d2)
            bs_dT.append(dd["TIR"]); bs_d54.append(dd["t54"]); bs_d70.append(dd["t70"])
            bs_dM.append(dd["magni"])
        pc = lambda a: (float(np.nanpercentile(a, ci[0])), float(np.nanpercentile(a, ci[1])))
        lo, hi = pc(bs_l)
        verdict = ("IMPROVES" if (lo > 0 and fd > 0) else "WORSE" if hi < 0 else "NEUTRAL")
        # --- VALIDITY GUARDS (2026-08-28). Both of these produced readable-but-wrong numbers that were
        # nearly published, so they blank the verdict rather than trusting the caller to notice.
        #
        # UNDER-COVERED: a candidate whose sweep barely reaches into op ± half_width yields a lift from
        # 1–2 points and a NaN operating-point delta. Averaged into a cohort mean it poisons it — this
        # happened twice (bddp06 at op ×1.20 against a default 0.85–1.15 grid read −0.042 on 2 points
        # against +0.009 on 5, and made a gated stack look worse than an ungated one).
        #
        # DEGENERATE-REF: lift is the AXIS-NORMALIZED distance to the reference polyline, so it means
        # nothing where the reference does not span both axes in the band. A 90 %-TIR donor whose dial
        # buys 0.53 TIR points turns any small move into lift −0.293 [−0.645,+0.222]; and a donor with
        # essentially no severe lows at op still selects the t54 axis when its band MAX clears
        # `t54_floor`, so a Δt54 of +0.01 normalizes into −0.080 — the same behaviour scored NEUTRAL on
        # the t70 axis in a shorter window, i.e. the verdict flipped because the AXIS flipped.
        under_covered = (len(cb) < 3) or not np.isfinite(d.get("TIR", np.nan))
        tir_span = float(ref_f["TIR"].max() - ref_f["TIR"].min())
        lows_span = float(ref_f["lows"].max() - ref_f["lows"].min())
        lows_at_op = float(np.interp(op_mult, ref_f["multiplier"], ref_f["lows"]))
        degenerate = (tir_span < 1.0) or (lows_span < 0.05) or (lows_axis == "t54" and lows_at_op < 0.10)
        if under_covered:
            verdict = "UNDER-COVERED"
        elif degenerate:
            verdict = "DEGENERATE-REF"
        rows.append({"mechanism": name, "lows_axis": lows_axis, "n_band": len(cb),
                     "under_covered": under_covered, "degenerate_ref": degenerate,
                     "ref_tir_span": tir_span, "ref_lows_span": lows_span, "ref_lows_at_op": lows_at_op,
                     "band_lift": bl, "band_lift_lo": lo, "band_lift_hi": hi,
                     "frac_dominant": fd, "dominant_ci_lo": pc(bs_d)[0],
                     "dTIR_op": d["TIR"], "dTIR_lo": pc(bs_dT)[0], "dTIR_hi": pc(bs_dT)[1],
                     "dt54_op": d["t54"], "dt54_lo": pc(bs_d54)[0], "dt54_hi": pc(bs_d54)[1],
                     "dt70_op": d["t70"], "dt70_lo": pc(bs_d70)[0], "dt70_hi": pc(bs_d70)[1],
                     "dmagni_op": d["magni"], "dmagni_lo": pc(bs_dM)[0], "dmagni_hi": pc(bs_dM)[1],
                     "dmean_op": d["mean"], "verdict": verdict, "n_blocks": B})
    table = pd.DataFrame(rows).sort_values("band_lift", ascending=False).reset_index(drop=True)
    return table, pd.DataFrame(pts)


def cohort_mean_ci(table: pd.DataFrame, drop_beds: Sequence[str] = (),
                   n_boot: int = 20000, ci: Tuple[float, float] = (5, 95),
                   seed: int = 0) -> pd.DataFrame:
    """A PROPER confidence interval on the MULTI-DONOR MEAN band lift.

    Averaging per-bed ``band_lift`` and reporting ``band_lift_lo.mean()`` alongside it is a trap: that
    second number is the MEAN OF THE PER-BED LOWER BOUNDS, not an interval on the mean, and it is far
    too conservative — averaging n roughly independent estimates shrinks the standard error by about
    sqrt(n), so the mean's own interval is much tighter than the average of the individual ones.
    Reading ``lift_lo_mean > 0`` as "the multi-donor mean clears zero" understates every multi-donor
    result; it flipped four mechanisms from "does not clear" to "clears" when computed correctly.

    Two-level bootstrap: resample BEDS with replacement (between-donor variability, which is what
    "works across a wide range of patients" actually asks about) and, within each drawn bed, draw its
    lift from ``N(band_lift, sd)`` with ``sd`` implied by that bed's own interval.

    Rows whose verdict is ``UNDER-COVERED`` or ``DEGENERATE-REF`` are dropped — their lift is not a
    number this should average. Beds are the unit of inference, so a donor appearing twice (e.g. a
    90-day window and a 2-month window of the same person) must be de-duplicated via ``drop_beds``.

    Note the model: when between-donor variance is ~0 this is CONSERVATIVE, because resampling beds
    already carries the within-bed noise and the second stage adds it again.
    """
    T = table[~table["bed"].isin(list(drop_beds))] if "bed" in table.columns else table
    for col in ("verdict",):
        if col in T.columns:
            T = T[~T[col].isin(["UNDER-COVERED", "DEGENERATE-REF"])]
    z = 1.6448536269514722 if tuple(ci) == (5, 95) else 1.959963984540054
    rng = np.random.default_rng(seed)
    out = []
    for mech, g in T.groupby("mechanism"):
        lift = g["band_lift"].to_numpy(float)
        sd = (g["band_lift_hi"].to_numpy(float) - g["band_lift_lo"].to_numpy(float)) / (2 * z)
        ok = np.isfinite(lift) & np.isfinite(sd)
        lift, sd = lift[ok], np.where(sd[ok] > 0, sd[ok], 1e-12)
        n = len(lift)
        if n < 2:
            continue
        idx = rng.integers(0, n, size=(n_boot, n))
        draws = (lift[idx] + rng.normal(0, 1, size=(n_boot, n)) * sd[idx]).mean(axis=1)
        lo, hi = np.percentile(draws, list(ci))
        out.append({"mechanism": mech, "n_beds": n, "mean": float(lift.mean()),
                    "ci_lo": float(lo), "ci_hi": float(hi), "p_gt0": float((draws > 0).mean()),
                    "n_improves": int((g["verdict"] == "IMPROVES").sum()) if "verdict" in g else -1,
                    "n_worse": int((g["verdict"] == "WORSE").sum()) if "verdict" in g else -1})
    return pd.DataFrame(out).sort_values("mean", ascending=False).reset_index(drop=True)


def format_table(table: pd.DataFrame) -> str:
    """Compact human-readable rendering of :func:`band_report`'s table."""
    lines = []
    for r in table.itertuples():
        lines.append(
            f"{r.mechanism:<22} {r.verdict:<8} lift {r.band_lift:+.3f} [{r.band_lift_lo:+.3f},{r.band_lift_hi:+.3f}]"
            f"  dom {r.frac_dominant:.2f}(lo {r.dominant_ci_lo:.2f})"
            f"  @op ΔTIR {r.dTIR_op:+.1f} [{r.dTIR_lo:+.1f},{r.dTIR_hi:+.1f}]"
            f"  Δt54 {r.dt54_op:+.2f} [{r.dt54_lo:+.2f},{r.dt54_hi:+.2f}]"
            f"  ΔMagni {r.dmagni_op:+.2f} [{r.dmagni_lo:+.2f},{r.dmagni_hi:+.2f}]"
            f"  Δt70 {r.dt70_op:+.2f}  ({r.lows_axis}, {r.n_band} pts, {r.n_blocks} blk)")
    return "\n".join(lines)
