"""Extract the deployed algorithm's per-cycle MANUAL-BOLUS RECOMMENDATION from Nightscout
devicestatus, as an overlay for the sim's **user-scaled** manual-bolus mode.

Motivation: the default manual-bolus mode replaces each real user manual bolus with the
CANDIDATE's full recommendation. But a user who habitually under-doses a big meal (delivering
a fraction of what their own app recommended and letting SMB/auto-bolus finish) then gets
over-dosed in the counterfactual. The user-scaled mode instead delivers
``candidate_rec * (user_bolus / field_recommendedBolus)`` — i.e. it carries the user's own
scaling of their algorithm's recommendation over onto the candidate's recommendation. When the
field recommendation is 0/absent (e.g. a pre-bolus the algorithm never called for) there is
nothing to scale against, so the sim FALLS BACK to the candidate's full recommendation.

**Two deployed algorithms store the recommendation in different places — hence two parsers:**
  - **Loop**  → ``devicestatus.loop.recommendedBolus``   (number, or {amount: n})
  - **oref/Trio** → ``devicestatus.openaps.recommendedBolus`` (number)

Both emit the SAME overlay: every cycle's recommendation (INCLUDING zeros — the sim needs the
current value to know when to fall back), as ``[{"t": ISO, "recommendedBolus": float}, ...]``.

CLI:
    python -m loopeval_analysis.recommended_bolus from-nightscout \
        --host https://HOST --algo oref --start 2026-06-13 --end 2026-06-17 \
        --tz Europe/Berlin --token TOKEN --out recommended_bolus.json
"""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from .reconstruct_carb_history import _fetch, _ISO_MS


def _as_number(v) -> float | None:
    """Recommendation may be a bare number or a dict ({amount: n}); return float or None."""
    if v is None:
        return None
    if isinstance(v, dict):
        v = v.get("amount", v.get("units", v.get("value")))
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _oref_stream(devicestatus: list[dict]) -> list[tuple[pd.Timestamp, float]]:
    """(time, recommendedBolus) per cycle from oref/Trio devicestatus."""
    out = []
    for ds in devicestatus:
        oa = ds.get("openaps") or {}
        rb = _as_number(oa.get("recommendedBolus"))
        if rb is None:
            continue
        src = oa.get("enacted") or oa.get("suggested") or {}
        t = src.get("timestamp") or ds.get("created_at")
        if t is not None:
            out.append((pd.to_datetime(t, utc=True), rb))
    return out


def _loop_stream(devicestatus: list[dict]) -> list[tuple[pd.Timestamp, float]]:
    """(time, recommendedBolus) per cycle from Loop devicestatus."""
    out = []
    for ds in devicestatus:
        lp = ds.get("loop") or {}
        rb = _as_number(lp.get("recommendedBolus"))
        if rb is None:
            continue
        t = lp.get("timestamp") or ds.get("created_at")
        if t is not None:
            out.append((pd.to_datetime(t, utc=True), rb))
    return out


_PARSERS = {"oref": _oref_stream, "loop": _loop_stream}


def extract(devicestatus: list[dict], algo: str) -> list[dict]:
    """Sorted, de-duplicated overlay points for the given algorithm."""
    if algo not in _PARSERS:
        raise ValueError(f"algo must be one of {sorted(_PARSERS)}, got {algo!r}")
    pts = _PARSERS[algo](devicestatus)
    # de-dup by timestamp (keep last), sort chronologically
    by_t: dict[pd.Timestamp, float] = {}
    for t, rb in pts:
        by_t[t] = rb
    # floor to seconds: _ISO_MS mangles sub-second timestamps (oref carries ms) into a
    # double-fraction (...50.460000.000Z); second precision is ample for a 5-min stream.
    return [{"t": _ISO_MS(t.floor("s")), "recommendedBolus": rb}
            for t, rb in sorted(by_t.items())]


def _cmd_from_nightscout(args) -> None:
    tz = args.tz
    start = pd.Timestamp(args.start, tz=tz).tz_convert("UTC")
    end = pd.Timestamp(args.end, tz=tz).tz_convert("UTC")
    extra = {"token": args.token} if args.token else None
    ds = _fetch(args.host, "devicestatus", start, end, extra=extra)
    points = extract(ds, args.algo)
    with open(args.out, "w") as f:
        json.dump({"algo": args.algo, "points": points}, f)
    nz = sum(1 for p in points if p["recommendedBolus"] > 0.05)
    print(f"[recommended_bolus] {args.algo}: {len(points)} cycles "
          f"({nz} with rec>0.05) -> {args.out}", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    fn = sub.add_parser("from-nightscout", help="fetch devicestatus + write rec-bolus overlay")
    fn.add_argument("--host", required=True)
    fn.add_argument("--algo", required=True, choices=sorted(_PARSERS),
                    help="deployed algorithm: 'loop' (loop.recommendedBolus) or "
                         "'oref' (openaps.recommendedBolus)")
    fn.add_argument("--start", required=True, help="ISO date/time (in --tz)")
    fn.add_argument("--end", required=True, help="ISO date/time (in --tz)")
    fn.add_argument("--tz", default="UTC")
    fn.add_argument("--token", default=None, help="Nightscout token (if the host needs one)")
    fn.add_argument("--out", required=True)
    fn.set_defaults(func=_cmd_from_nightscout)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
