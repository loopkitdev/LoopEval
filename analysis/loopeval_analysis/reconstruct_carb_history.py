"""Reconstruct the as-seen carb-entry history from Nightscout.

Nightscout stores only the FINAL state of a carb entry, stamped at the ORIGINAL
entry time. A user who logs 15 g at 11:26 then edits it to 45 g at 12:01 leaves
ONE document: 45 g @ 11:26. Naive replay applies the full 45 g from 11:26 and
carries ~30 g of phantom carbs-on-board until the edit, over-forecasting and
over-dosing (see runs/2026-06-18-user2-casestudy).

This module recovers what the *deployed* Loop actually saw at each moment and
writes an OVERLAY JSON of the EDITED entries with their time-ordered revision
sequences. The Swift CLI (`--carb-revisions-json`) splices these into the cached
carbs so decision-time replay / counterfactual sim matches the deployed Loop.

Detection signal: `userLastModifiedAt > userEnteredAt`.
Pre-edit grams: inferred from the deployed Loop's own per-cycle devicestatus COB
— the INCREMENT in total COB at the entry's appearance (robust to overlapping
entries, since it differences against the COB level just before the entry).

CLI:
    python -m loopeval_analysis.reconstruct_carb_history from-nightscout \
        --host https://HOST --start 2026-06-08 --end 2026-06-15 \
        --tz America/Chicago --out carb_revisions.json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

import pandas as pd

_ISO_MS = lambda ts: ts.tz_convert("UTC").isoformat().replace("+00:00", ".000Z")


# ───────────────────────────── Nightscout fetch ──────────────────────────────

def _fetch(host: str, collection: str, start: pd.Timestamp, end: pd.Timestamp,
           *, page_days: float = 3.0, count: int = 20000, timeout: float = 60.0,
           extra: dict | None = None) -> list[dict]:
    """Fetch a Nightscout collection over [start, end), paging by created_at."""
    if not host.startswith("http"):
        host = "https://" + host
    host = host.rstrip("/")
    rows: list[dict] = []
    cur = start
    step = pd.Timedelta(days=page_days)
    while cur < end:
        nxt = min(cur + step, end)
        params = {
            "find[created_at][$gte]": _ISO_MS(cur),
            "find[created_at][$lt]": _ISO_MS(nxt),
            "count": count,
        }
        if extra:
            params.update(extra)
        url = f"{host}/api/v1/{collection}.json?" + urllib.parse.urlencode(params)
        try:
            rows += json.loads(urllib.request.urlopen(url, timeout=timeout).read())
        except Exception as exc:  # noqa: BLE001
            print(f"  [reconstruct] fetch {collection} {cur.date()}..{nxt.date()} "
                  f"failed: {exc}", file=sys.stderr)
        cur = nxt
    return rows


def _cob_series(devicestatus: list[dict]) -> pd.Series:
    """Per-cycle total COB (g) reported by the deployed Loop, indexed by time."""
    recs = []
    for ds in devicestatus:
        lp = ds.get("loop") or {}
        cob = lp.get("cob")
        if isinstance(cob, dict):
            cob = cob.get("cob")
        t = ds.get("created_at")
        if cob is not None and t is not None:
            recs.append((t, float(cob)))
    if not recs:
        return pd.Series(dtype=float)
    s = pd.Series({pd.to_datetime(t).tz_convert("UTC"): c for t, c in recs})
    return s.sort_index()


# ─────────────────────────────── reconstruction ──────────────────────────────

@dataclass
class ReconResult:
    edited: list[dict] = field(default_factory=list)
    n_carbs: int = 0
    n_edited_meta: int = 0       # userLastModifiedAt != userEnteredAt
    n_reconstructed: int = 0     # produced a real pre-edit revision
    n_fallback_hide: int = 0     # no COB inference -> hide until edit
    n_skipped_noinc: int = 0     # edit didn't raise grams -> leave as-is


def _incremental_revisions(
    cob: pd.Series,
    te: pd.Timestamp,
    tm: pd.Timestamp,
    final_g: float,
    other_appear: list[pd.Timestamp],
    *,
    appear_before_min: float,
    appear_after_min: float,
    min_jump_g: float,
) -> list[tuple[pd.Timestamp, float]] | None:
    """Reconstruct the time-ordered grams trajectory of one entry from the
    deployed Loop's total-COB series.

    A meal logged incrementally (or edited up several times) leaves ONE
    Nightscout document (final grams @ original time, lastModified at the final
    edit) but produces SEVERAL upward jumps in the per-cycle total COB. Each
    upward jump in `[te, tm]` that is NOT coincident with another entry's
    appearance is an addition to THIS entry. Returns cumulative-grams revisions
    `[(t, grams), ...]`; None if there's no COB to anchor on.
    """
    if cob.empty:
        return None
    before = cob[(cob.index < te) &
                 (cob.index >= te - pd.Timedelta(minutes=appear_before_min))]
    # Scan from just before the entry through the final edit.
    win = cob[(cob.index >= te - pd.Timedelta(minutes=appear_before_min)) &
              (cob.index <= tm + pd.Timedelta(minutes=appear_after_min))]
    if win.empty:
        return None

    cumulative = 0.0
    revs: list[tuple[pd.Timestamp, float]] = []
    prev = float(before.iloc[-1]) if len(before) else None
    for ts, c in win.items():
        c = float(c)
        if prev is None:
            prev = c
            continue
        delta = c - prev
        prev = c
        if delta <= min_jump_g:
            continue
        # Skip jumps that belong to a DIFFERENT entry appearing around now.
        if any(abs((ts - oa).total_seconds()) <= appear_after_min * 60
               for oa in other_appear):
            continue
        cumulative = min(cumulative + delta, final_g)
        # Stamp the FIRST addition at the entry time (te) — Loop saw it from when
        # the user logged it; the COB registers a cycle later. Later increments
        # are stamped at their detected jump time.
        stamp = te if not revs else ts
        revs.append((stamp, round(cumulative, 2)))

    if not revs:
        return None
    # The lastModified edit finalizes the count (often post-hoc, after COB has
    # decayed); make sure the trajectory ends at the cached final grams.
    if final_g - revs[-1][1] >= 0.01 and tm > revs[-1][0]:
        revs.append((tm, final_g))
    return revs


def reconstruct(
    treatments: list[dict],
    devicestatus: list[dict],
    *,
    appear_before_min: float = 12.0,
    appear_after_min: float = 7.0,
    edit_tol_sec: float = 30.0,
    min_grams_increase: float = 2.0,
    min_jump_g: float = 12.0,
    incremental: bool = False,
) -> ReconResult:
    """Build the edited-entry overlay from treatments + devicestatus COB.

    For each carb entry whose `userLastModifiedAt` is meaningfully later than
    `userEnteredAt`, reconstruct the grams trajectory the deployed Loop actually
    saw. Default is the 2-step `[(entered, pre), (modified, final)]`.

    `incremental=True` tries to recover the full ramp from upward jumps in total
    COB. NOTE (validated 2026-06-19, runs/2026-06-19-divergence): this is NET
    WORSE on aggregate dose fidelity (user2 2wk: 2-step ratio 1.118 vs
    incremental 1.18–1.41) because Loop's DYNAMIC carb absorption ticks COB up
    when it re-estimates absorption, and those upticks are indistinguishable from
    real carb additions — so the ramp over-attributes. It fixes genuinely-
    incremental meals (e.g. 06-08 04:27) but over-counts absorption upticks
    elsewhere (06-04: COB 28→70 vs field 42). Kept as an opt-in experiment; the
    robust fix is COB-trajectory matching against field's published per-cycle COB,
    not jump attribution. `min_jump_g` (default 12) is the best-tested threshold.
    """
    cob = _cob_series(devicestatus)
    res = ReconResult()

    carbs = [t for t in treatments if t.get("carbs")]
    res.n_carbs = len(carbs)

    # Appearance times of ALL carb entries — used to avoid mis-attributing one
    # entry's COB jump to an overlapping entry.
    all_appear: list[pd.Timestamp] = []
    for t in carbs:
        e = t.get("userEnteredAt") or t.get("created_at") or t.get("timestamp")
        if e is not None:
            all_appear.append(pd.to_datetime(e).tz_convert("UTC"))

    for t in carbs:
        final_g = float(t["carbs"])
        entered = t.get("userEnteredAt") or t.get("created_at") or t.get("timestamp")
        modified = t.get("userLastModifiedAt")
        meal = t.get("timestamp") or t.get("created_at")     # meal time == cache startDate
        sync = t.get("syncIdentifier") or t.get("_id")
        if entered is None or meal is None or sync is None:
            continue
        te = pd.to_datetime(entered).tz_convert("UTC")
        tmeal = pd.to_datetime(meal).tz_convert("UTC")
        if modified is None:
            continue
        tm = pd.to_datetime(modified).tz_convert("UTC")
        if (tm - te).total_seconds() <= edit_tol_sec:
            continue   # not edited (or trivially so)
        res.n_edited_meta += 1

        # Other entries' appearance times (exclude this entry's own).
        other_appear = [a for a in all_appear
                        if abs((a - te).total_seconds()) > edit_tol_sec]

        revs = None
        if incremental:
            revs = _incremental_revisions(
                cob, te, tm, final_g, other_appear,
                appear_before_min=appear_before_min,
                appear_after_min=appear_after_min,
                min_jump_g=min_jump_g)
        else:
            # Default 2-step: pre-edit grams = COB INCREMENT at appearance. The
            # carb often registers a cycle AFTER userEnteredAt, so take the MAX COB
            # over the appearance window minus the baseline just before the entry.
            if not cob.empty:
                before = cob[(cob.index < te) &
                             (cob.index >= te - pd.Timedelta(minutes=appear_before_min))]
                after = cob[(cob.index >= te) &
                            (cob.index <= te + pd.Timedelta(minutes=appear_after_min))]
                if len(after):
                    cob_before = float(before.iloc[-1]) if len(before) else 0.0
                    pre_g = min(max(float(after.max()) - cob_before, 0.0), final_g)
                    revs = [(te, round(pre_g, 2)), (tm, final_g)]

        if revs is not None:
            if len(revs) == 1 and final_g - revs[0][1] < min_grams_increase:
                res.n_skipped_noinc += 1
                continue
            if len(revs) == 2 and final_g - revs[0][1] < min_grams_increase:
                # Edit didn't raise grams (absorption/foodType edit or reduction) —
                # the cached final is already what Loop saw early.
                res.n_skipped_noinc += 1
                continue
            revisions = [{"visibleFrom": _ISO_MS(ts), "grams": g} for ts, g in revs]
            res.n_reconstructed += 1
        else:
            # No COB anchor — conservatively hide the entry until the edit.
            revisions = [{"visibleFrom": _ISO_MS(tm), "grams": final_g}]
            res.n_fallback_hide += 1

        res.edited.append({
            "matchStartDate": _ISO_MS(tmeal),
            "revisionKey": str(sync),
            "foodType": t.get("foodType"),
            "revisions": revisions,
        })

    return res


# ───────────────────────────────── CLI ───────────────────────────────────────

def _cmd_from_nightscout(args: argparse.Namespace) -> None:
    tz = args.tz
    start = pd.Timestamp(args.start, tz=tz)
    end = pd.Timestamp(args.end, tz=tz)
    print(f"[reconstruct] {args.host}  {start} .. {end}", file=sys.stderr)

    treatments = _fetch(args.host, "treatments", start, end)
    devicestatus = _fetch(args.host, "devicestatus", start, end)
    print(f"[reconstruct] fetched {len(treatments)} treatments, "
          f"{len(devicestatus)} devicestatus", file=sys.stderr)

    res = reconstruct(treatments, devicestatus, incremental=args.incremental,
                      min_jump_g=args.min_jump_g)
    out = {"version": 1, "edited": res.edited}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"[reconstruct] carbs={res.n_carbs}  edited(meta)={res.n_edited_meta}  "
          f"reconstructed={res.n_reconstructed}  hide-fallback={res.n_fallback_hide}  "
          f"skipped(no-increase)={res.n_skipped_noinc}", file=sys.stderr)
    print(f"[reconstruct] wrote {len(res.edited)} edited entries -> {args.out}",
          file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    fn = sub.add_parser("from-nightscout", help="fetch + reconstruct + write overlay")
    fn.add_argument("--host", required=True)
    fn.add_argument("--start", required=True, help="ISO date/time (in --tz)")
    fn.add_argument("--end", required=True, help="ISO date/time (in --tz)")
    fn.add_argument("--tz", default="UTC")
    fn.add_argument("--out", required=True)
    fn.add_argument("--incremental", action="store_true",
                    help="EXPERIMENTAL (net-worse, see reconstruct() docstring): "
                         "recover the full grams ramp from upward COB jumps "
                         "instead of the default 2-step revision")
    fn.add_argument("--min-jump-g", type=float, default=12.0,
                    help="min upward COB jump (g) counted as a carb addition "
                         "when --incremental (default 12)")
    fn.set_defaults(func=_cmd_from_nightscout)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
