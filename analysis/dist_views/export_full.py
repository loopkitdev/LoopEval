#!/usr/bin/env python3
"""Full four-stream ETL export for the wide cohort, in parallel, alias-only.

Three things this handles that a bare loop over `export_donor` does not:

* **The ETL logs the raw `_userId`.** That is a pseudonymous access key. Every
  line is rewritten to the alias before it reaches a log file.
* **Transient connection failures are silent.** Two early attempts here died
  with no traceback and no files. Each export is therefore verified by
  inspecting its outputs, not by trusting its exit code, and retried once.
* **~5 minutes per donor.** Sequential would be five hours; a small worker pool
  brings it under one. The pool is deliberately modest — the SQL warehouse is
  shared and hammering it is how the transient failures start.

Run:  python3 export_full.py [n_workers]
      EXPORT_ROOT=handsoff EXPORT_MAP=handsoff_alias_map.json python3 export_full.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

CACHE = Path(os.path.expanduser("~/.loop-eval/trait-cohort"))
# A second cohort can be exported alongside the first by pointing these at
# another alias map and root — see pull_handsoff.py, which over-samples a cell
# the hash-ordered wide sample barely reached.
FULL = CACHE / os.environ.get("EXPORT_ROOT", "full")
LOGS = CACHE / "logs"
ALIAS_MAP = CACHE / os.environ.get("EXPORT_MAP", "alias_map.json")
WINDOW = ("2026-04-01", "2026-07-24")
# therapy.json is tiny for a person with one settings era (~1 KB), so its floor
# must be low; the earlier 5 KB floor flagged four complete exports as failed.
NEEDED = {"glucose.json": 200_000, "doses.json": 50_000,
          "therapy.json": 300, "carbs.json": 2}

WORKER = r'''
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/dev/LoopEval/analysis"))
for line in open(os.path.expanduser("~/.loop-eval/databricks.env")):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1); os.environ.setdefault(k, v.strip())
from loopeval_analysis.tidepool import etl
etl.export_donor(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
'''


def complete(d: Path) -> bool:
    """Trust the files, not the exit code."""
    for name, floor in NEEDED.items():
        f = d / name
        if not f.exists() or f.stat().st_size < floor:
            return False
    return True


def run_one(alias: str, uid: str) -> tuple[str, bool, float, str]:
    out = FULL / alias
    if complete(out):
        return alias, True, 0.0, "cached"
    t0 = time.time()
    note = ""
    for attempt in (1, 2):
        out.mkdir(parents=True, exist_ok=True)
        p = subprocess.run([sys.executable, "-u", "-c", WORKER, uid,
                            WINDOW[0], WINDOW[1], str(out)],
                           capture_output=True, text=True)
        # scrub the access key out of anything we keep
        log = (p.stdout + "\n" + p.stderr).replace(uid, alias)
        log = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                     "<uid>", log)
        LOGS.mkdir(parents=True, exist_ok=True)
        (LOGS / f"{alias}.log").write_text(log)
        if complete(out):
            return alias, True, time.time() - t0, f"ok (try {attempt})"
        note = f"incomplete after try {attempt}"
        time.sleep(5)
    return alias, False, time.time() - t0, note


def main(workers: int = 6) -> int:
    amap = json.loads(ALIAS_MAP.read_text())
    todo = sorted(amap.items())
    FULL.mkdir(parents=True, exist_ok=True)
    print(f"{len(todo)} donors, {workers} workers, ~5 min each\n")
    done = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_one, a, u): a for a, u in todo}
        for fut in as_completed(futs):
            alias, ok, secs, note = fut.result()
            done += ok
            fail += (not ok)
            print(f"  {alias:<5} {'OK ' if ok else 'FAIL'} {secs:>6.0f}s  {note}"
                  f"   [{done + fail}/{len(todo)}]", flush=True)
    print(f"\n{done} exported, {fail} failed, {(time.time()-t0)/60:.0f} min")
    if fail:
        print("re-run to retry the failures — completed donors are skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 6))
