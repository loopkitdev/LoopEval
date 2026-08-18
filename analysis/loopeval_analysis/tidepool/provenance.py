"""Export provenance — so a STALE export can never masquerade as a fresh one.

An exported donor dir (`data_causal/`) is effectively a **cache** of a Databricks pull
shaped by the ETL code. When the ETL changes in a way that alters the data, every export
made before that change is silently wrong — and nothing in the files says so.

That is not hypothetical: on 2026-08-13 the basal-dedup fix (92fafda, 21:17) landed 3.5 h
*after* most of the cohort was exported. The stale dirs carried 21-88 h of phantom basal,
which read as a systematic insulin-curve bias and inverted an insulin-model conclusion
before anyone noticed the files were old. See [[stale-preFix-cohort-exports]].

**The staleness gate is `etl.DATA_VERSION`, bumped by hand when a change alters output.**
That is deliberate: hashing the ETL source would flag every comment and refactor too, and a
checker that cries wolf gets ignored — or worse, gets `--purge`d past. The source hash IS
recorded alongside, but only as a forensic hint ("source drifted since this export"), never
as a staleness verdict.

    python3 -m loopeval_analysis.tidepool.provenance runs/           # report
    python3 -m loopeval_analysis.tidepool.provenance runs/ --purge --yes
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time

MANIFEST = "_export_manifest.json"
_SHAPING_SOURCES = ("etl.py",)


def _current_data_version() -> int:
    from . import etl
    return int(getattr(etl, "DATA_VERSION", 0))


def etl_source_hash() -> str:
    """SHA-256 (first 12) over ETL sources — forensic hint only, NOT the gate."""
    h = hashlib.sha256()
    here = os.path.dirname(os.path.abspath(__file__))
    for name in sorted(_SHAPING_SOURCES):
        with open(os.path.join(here, name), "rb") as fh:
            h.update(name.encode())
            h.update(fh.read())
    return h.hexdigest()[:12]


def _uid_fingerprint(user: str) -> str:
    """Never store the raw `_userId` — it is a pseudonymous access key. A hash still lets
    an export be matched to a donor without carrying the key around."""
    return hashlib.sha256(str(user).encode()).hexdigest()[:12]


def write_manifest(outdir, user, start, end, counts=None):
    m = {
        "data_version": _current_data_version(),
        "etl_source_hash": etl_source_hash(),
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "window": {"start": str(start), "end": str(end)},
        "uid_fingerprint": _uid_fingerprint(user),
        "counts": counts or {},
    }
    with open(os.path.join(outdir, MANIFEST), "w") as fh:
        json.dump(m, fh, indent=2)
    return m


def scan(root="runs"):
    """[(dir, status, detail)] — status 'ok' | 'STALE' | 'UNKNOWN'.

    STALE  = manifest says an older DATA_VERSION → data is known-wrong, re-export.
    UNKNOWN = no manifest (predates provenance) → provenance can't be established;
              treat with suspicion but don't assume it's wrong.
    """
    cur = _current_data_version()
    cur_hash = etl_source_hash()
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        if "doses.json" not in filenames:
            continue
        dirnames[:] = []
        mp = os.path.join(dirpath, MANIFEST)
        if not os.path.exists(mp):
            out.append((dirpath, "UNKNOWN", "no manifest (predates provenance)"))
            continue
        try:
            m = json.load(open(mp))
        except Exception as e:
            out.append((dirpath, "UNKNOWN", f"unreadable manifest: {e}"))
            continue
        v = int(m.get("data_version", -1))
        when = m.get("exported_at", "?")
        if v < cur:
            out.append((dirpath, "STALE", f"data_version {v} < current {cur} · exported {when}"))
        else:
            drift = "" if m.get("etl_source_hash") == cur_hash else "  (etl source drifted — cosmetic unless DATA_VERSION bumped)"
            out.append((dirpath, "ok", f"data_version {v} · exported {when}{drift}"))
    return sorted(out)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    root = args[0] if args else "runs"
    purge = "--purge" in argv
    yes = "--yes" in argv
    include_unknown = "--include-unknown" in argv

    rows = scan(root)
    if not rows:
        print(f"no export dirs found under {root}/")
        return 0
    stale = [r for r in rows if r[1] == "STALE"]
    unknown = [r for r in rows if r[1] == "UNKNOWN"]
    ok = [r for r in rows if r[1] == "ok"]

    print(f"current DATA_VERSION={_current_data_version()}  etl_source_hash={etl_source_hash()}\n")
    for d, status, detail in rows:
        if status == "ok" and not ("-v" in argv or "--verbose" in argv):
            continue
        print(f"[{status:^8}] {d}\n           {detail}")
    print(f"\n{len(rows)} export(s): {len(ok)} ok, {len(stale)} STALE, {len(unknown)} UNKNOWN")

    targets = list(stale) + (list(unknown) if include_unknown else [])
    if not purge:
        if targets:
            print("\nStale exports produce results that look physiological but aren't.")
            print(f"Re-export, or delete: python3 -m loopeval_analysis.tidepool.provenance {root} "
                  f"--purge --yes{' --include-unknown' if unknown and not stale else ''}")
        return 1 if stale else 0

    if not targets:
        print("\nnothing to purge")
        return 0
    print(f"\nwould delete {len(targets)} dir(s):")
    for d, _s, _ in targets:
        print(f"  {d}")
    if not yes:
        print("\nre-run with --yes to actually delete (nothing deleted)")
        return 1
    for d, _s, _ in targets:
        shutil.rmtree(d)
        print(f"deleted {d}")
    print(f"\npurged {len(targets)} export(s) — re-export before analysing")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
