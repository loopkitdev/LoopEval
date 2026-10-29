"""Reference-trace regression suite for `loop-eval simulate`: one short run per simulation mode in use,
compared field by field against traces recorded from a trusted build.

    python scripts/golden.py record [--bin B] [--only NAME ...]   # (re)record references with build B
    python scripts/golden.py check  [--bin B] [--only NAME ...]   # run build B, compare with the references
    python scripts/golden.py list

An engine change that should not move any number (a refactor, a fix in another mode) must pass `check`
with every case identical. A change that moves numbers on purpose is checked, explained in its commit,
and then re-recorded with `record --only` for the cases it moves.

References live outside the repo, in $LOOPEVAL_GOLDEN (default ~/.loop-eval/golden): traces, the
manifest (build, commit, case flags), and the inputs a case needs that are not a donor export (a
swapped schedule file, an additive person). Donor exports come from $LOOPEVAL_DATA (default
~/.loop-eval/ice_v32/full).

External-plant cases replay a recorded protocol transcript (`plant` subcommand, below), so they do not
depend on the plant's code after recording. The replay plant checks every request against the
recorded one and stops the run at the first difference: the doses the engine sends the plant are part
of what is checked. Recording one needs the live plant (the additive simulator) and its person dir.
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLDEN = Path(os.environ.get("LOOPEVAL_GOLDEN", Path.home() / ".loop-eval/golden"))
DATA = Path(os.environ.get("LOOPEVAL_DATA", Path.home() / ".loop-eval/ice_v32/full"))
PY = sys.executable

CLASS1 = ["--no-mid-absorption-isf", "--no-gradual-transitions-gate", "--legacy-rc-decay"]
# The frontier harness's counterfactual flags (runs/2026-10-15-replay-change/run.py COMMON, variant A).
FRONTIER = ["--candidate-counterfactual", "--candidate-infer-sensitivity", "--counter-reg-onset", "54",
            "--counter-reg-gain", "0.4", "--counter-reg-max", "8.0", "--cgm-stale-guard-min", "5"] + CLASS1
VERBATIM_BOLUS = ["--no-candidate-manual-bolus-from-recommendation", "--no-candidate-iob-adjust-manual-boluses"]
DTR = ["--decision-time-replay", "--no-clip-in-progress-temp-basal"] + CLASS1
IRCC = ["--integral-rc", "--integral-rc-clamp"]
# Guard + runway (C20 + C29 + C40), the frozen arm of runs/2026-10-23-frontier-dosing/dr/run.py arm_flags("gr"),
# band depth k = min(1, 6.7 / σ5 median) pinned at i008's value so the case does not depend on that file.
GR = ["--candidate-sigma-band-k", "0.964", "--candidate-sigma-band-cob-gate", "--candidate-postlow-rc-rise-scale", "0.3",
      "--candidate-postlow-window", "720", "--candidate-runway-fraction", "0.7", "--candidate-runway-cob-gate",
      "--candidate-runway-bg-min", "150"]
W = ("2026-09-04T02:00:00Z", "2026-09-08T00:00:00Z")      # 22 h lead + 3 days, as the frontier harness

# Each case: donor export (alias, or "@input" for a dir under GOLDEN/inputs), window, flags. "{in}" in a
# flag is replaced by GOLDEN/inputs, "{data}" by the donor's export dir.
CASES = {
    # Frontier counterfactual: ICE replay, candidate settings differ from the field.
    "frontier_a":        dict(alias="i008", flags=FRONTIER + ["--candidate-insulin-needs", "0.85"]),
    "frontier_b":        dict(alias="i008", flags=FRONTIER + VERBATIM_BOLUS + ["--candidate-insulin-needs", "0.85"]),
    "frontier_iob_adjust": dict(alias="i008", flags=FRONTIER + ["--no-candidate-manual-bolus-from-recommendation",
                                                                "--candidate-insulin-needs", "0.85"]),
    "frontier_ircc_gbaf": dict(alias="i003", flags=FRONTIER + IRCC + [
        "--candidate-gbaf", "--candidate-gbaf-low-anchor", "98", "--candidate-gbaf-high-anchor", "200",
        "--candidate-gbaf-factor-low", "0.2", "--candidate-gbaf-factor-high", "0.8", "--candidate-insulin-needs", "1.15"]),
    "frontier_timeaf":   dict(alias="i001", flags=FRONTIER + [
        "--candidate-bolus-increment", "0.025", "--candidate-temp-basal-increment", "0.025",
        "--basal-pulse-quantum", "0.025", "--time-based-af", "--candidate-insulin-needs", "0.9"]),
    "frontier_temp":     dict(alias="i040", flags=FRONTIER + ["--temp-basal-strategy", "--candidate-insulin-needs", "1.1"]),
    "frontier_curve":    dict(alias="i009", flags=FRONTIER + [
        "--controller-insulin-model", "custom", "--custom-insulin-duration-min", "180",
        "--custom-insulin-peak-min", "80", "--candidate-insulin-needs", "0.9"]),
    "frontier_gr":       dict(alias="i008", flags=FRONTIER + GR),
    # Settings edit replayed: the candidate runs the other window's schedules (Experiment 1).
    "candidate_schedules": dict(alias="i005", window=("2026-06-09T02:00:00Z", "2026-06-13T00:00:00Z"),
                                flags=FRONTIER + ["--candidate-schedules-json", "{in}/i005_0619_pre.json"]),
    # Patient decoupled from the controller.
    "patient_isf":       dict(alias="i008", flags=FRONTIER + ["--patient-isf", "45", "--candidate-insulin-needs", "0.9"]),
    # Legacy fixed 5-min grid.
    "grid":              dict(alias="i008", flags=FRONTIER + ["--no-decisions-from-cgm", "--candidate-insulin-needs", "0.9"]),
    # Identity: the candidate delivers exactly the field's doses / runs the baseline's config.
    "cf_identity":       dict(alias="i008", flags=FRONTIER + ["--cf-identity"]),
    "same_config":       dict(alias="i008", flags=CLASS1),
    # No counterfactual, different settings: the candidate decides open loop on the field's inputs.
    "open_loop":         dict(alias="i008", flags=CLASS1 + ["--candidate-insulin-needs", "0.9"]),
    # Decision-time replay (open loop on the field's inputs), both RC modes.
    "dtr":               dict(alias="i008", flags=DTR),
    "dtr_ircc":          dict(alias="i014", flags=DTR + IRCC),
    "dtr_gr":            dict(alias="i008", flags=DTR + GR),
    # Other controllers for the candidate.
    "openaps":           dict(alias="i008", flags=FRONTIER + ["--candidate-openaps"]),
    "loop_mimic":        dict(alias="i008", flags=FRONTIER + ["--candidate-loop-mimic-oaps"]),
    # External plant (additive person v01009, 4 days, recorded transcript), with and without the
    # plant's person acting (carbs, boluses, plant-sent overrides).
    "plant_behavior":    dict(alias="@plant_v01009/data", window=("2026-01-05T00:00:00Z", "2026-01-09T00:00:00Z"),
                              plant="plant_behavior", flags=["--candidate-counterfactual", "--plant-behavior",
                                                            "--cf-gap-reanchor-min", "0"] + CLASS1),
    "plant_v1":          dict(alias="@plant_v01009/data", window=("2026-01-05T00:00:00Z", "2026-01-09T00:00:00Z"),
                              plant="plant_v1", flags=["--candidate-counterfactual", "--cf-gap-reanchor-min", "0"] + CLASS1),
}
# Live plant used only when recording a plant case: the additive simulator serving the person dir, with
# the person's later Temporary Overrides sent by the plant (held.json) rather than exported.
LIVE_PLANT = "cd {repo}/analysis && {py} -m loopeval_analysis.patient_sim.loopeval_io serve {person}"


def data_dir(c) -> Path:
    a = c["alias"]
    return GOLDEN / "inputs" / a[1:] if a.startswith("@") else DATA / a


def command(name, c, bin_path, trace, plant_cmd=None) -> list[str]:
    d = data_dir(c)
    w = c.get("window", W)
    fl = [f.replace("{in}", str(GOLDEN / "inputs")).replace("{data}", str(d)) for f in c["flags"]]
    if (d / "disruptions.csv").exists() and not c["alias"].startswith("@"):
        fl += ["--outages-csv", str(d / "disruptions.csv")]
    if plant_cmd:
        fl += ["--external-plant", plant_cmd]
    return [bin_path, "simulate", "--data-dir", str(d), "--start", w[0], "--end", w[1],
            "--trace-out", str(trace), *fl, "--candidate-label", name]


def plant_cmd(name, c, mode) -> str | None:
    if "plant" not in c: return None
    tr = GOLDEN / "plant" / f"{c['plant']}.jsonl"
    me = Path(__file__).resolve()
    if mode == "record":
        person = GOLDEN / "inputs" / c["alias"][1:].split("/")[0]
        live = LIVE_PLANT.format(repo=REPO, py=PY, person=person)
        inject = person / "held.json"
        return f"{PY} {me} plant record {tr} {inject} '{live}'"
    return f"{PY} {me} plant replay {tr}"


def run_case(name, bin_path, mode, outdir: Path):
    c = CASES[name]
    trace = outdir / f"{name}.json"
    cmd = command(name, c, bin_path, trace, plant_cmd(name, c, mode))
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    (outdir / f"{name}.log").write_text(" ".join(cmd) + "\n\n" + p.stderr[-20000:])
    if p.returncode != 0 or not trace.exists():
        lines = p.stderr.strip().splitlines()
        why = next((l for l in lines if l.startswith("golden plant:")), lines[-1] if lines else "")
        return name, None, f"exit {p.returncode}: {why[:400]}", time.time() - t
    return name, trace, None, time.time() - t


def diff(a, b, path="", out=None, limit=8):
    """First `limit` differing leaves of two JSON values, and the largest numeric difference."""
    if out is None: out = dict(paths=[], n=0, maxabs=0.0, where="")
    if type(a) != type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        out["n"] += 1
        if len(out["paths"]) < limit: out["paths"].append(f"{path}: {str(a)[:60]} -> {str(b)[:60]}")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out["n"] += 1
                if len(out["paths"]) < limit: out["paths"].append(f"{path}/{k}: {'missing in new' if k not in b else 'new key'}")
            else: diff(a[k], b[k], f"{path}/{k}", out, limit)
    elif isinstance(a, list):
        if len(a) != len(b):
            out["n"] += 1
            if len(out["paths"]) < limit: out["paths"].append(f"{path}: length {len(a)} -> {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)): diff(x, y, f"{path}[{i}]", out, limit)
    elif a != b:
        out["n"] += 1
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) > out["maxabs"]:
            out["maxabs"], out["where"] = abs(a - b), path
        if len(out["paths"]) < limit: out["paths"].append(f"{path}: {a} -> {b}")
    return out


def git_commit():
    r = subprocess.run(["git", "-C", str(REPO), "describe", "--always", "--dirty"], capture_output=True, text=True)
    return r.stdout.strip()


def main_suite(a):
    names = a.only or list(CASES)
    bad = [n for n in names if n not in CASES]
    if bad: sys.exit(f"unknown case(s): {bad}")
    bin_path = str(Path(a.bin).resolve())
    if a.cmd == "record":
        (GOLDEN / "traces").mkdir(parents=True, exist_ok=True); (GOLDEN / "plant").mkdir(exist_ok=True)
        outdir = GOLDEN / "traces"
    else:
        outdir = Path(tempfile.mkdtemp(prefix="golden-check-"))
    with ThreadPoolExecutor(a.par) as ex:
        res = list(ex.map(lambda n: run_case(n, bin_path, a.cmd, outdir), names))
    failed = 0
    if a.cmd == "record":
        man_p = GOLDEN / "manifest.json"
        man = json.load(open(man_p)) if man_p.exists() else {}
        for n, tr, err, sec in res:
            if err: print(f"  {n:22s} FAILED  {err}"); failed += 1; continue
            man[n] = dict(commit=git_commit(), bin=bin_path, recorded=time.strftime("%Y-%m-%dT%H:%M:%S"),
                          flags=CASES[n]["flags"], alias=CASES[n]["alias"], seconds=round(sec, 1))
            print(f"  {n:22s} recorded  {sec:5.0f} s")
        json.dump(man, open(man_p, "w"), indent=1)
    else:
        for n, tr, err, sec in res:
            ref = GOLDEN / "traces" / f"{n}.json"
            if err: print(f"  {n:22s} FAILED   {err}"); failed += 1; continue
            if not ref.exists(): print(f"  {n:22s} NO REFERENCE"); failed += 1; continue
            d = diff(json.load(open(ref)), json.load(open(tr)))
            if d["n"] == 0:
                print(f"  {n:22s} identical  {sec:5.0f} s")
            else:
                failed += 1
                print(f"  {n:22s} DIFFERS    {d['n']} leaves, max |Δ| {d['maxabs']:.3g} at {d['where']}")
                for p in d["paths"]: print(f"      {p}")
        print(f"traces and logs: {outdir}")
    print(f"{len(res) - failed}/{len(res)} {'recorded' if a.cmd == 'record' else 'identical'}")
    sys.exit(1 if failed else 0)


# ── Recording / replaying plant ─────────────────────────────────────────────────────────────────────
def plant_main(argv):
    mode, tr = argv[0], Path(argv[1])
    if mode == "record":
        inject = json.load(open(argv[2])) if Path(argv[2]).exists() else []
        p = subprocess.Popen(argv[3], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        from datetime import datetime
        P = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
        with open(tr, "w") as log:
            for line in sys.stdin:
                req = json.loads(line); p.stdin.write(line); p.stdin.flush()
                rep = json.loads(p.stdout.readline())
                t0, t1 = P(req["t0"]), P(req["t1"])
                ov = [dict(t=w["start"], end=w["end"], **{k: w[k] for k in ("factor", "targetLo", "targetHi") if k in w})
                      for w in inject if t0 < P(w["start"]) <= t1]
                if ov: rep["overrides"] = rep.get("overrides", []) + ov
                log.write(json.dumps(dict(req=req, rep=rep)) + "\n"); log.flush()
                sys.stdout.write(json.dumps(rep) + "\n"); sys.stdout.flush()
        p.stdin.close(); p.wait()
    else:
        rows = [json.loads(l) for l in open(tr)]
        for i, line in enumerate(sys.stdin):
            req = json.loads(line)
            if i >= len(rows):
                sys.stderr.write(f"golden plant: request {i} beyond the {len(rows)} recorded\n"); sys.exit(2)
            if req != rows[i]["req"]:
                d = diff(rows[i]["req"], req)
                sys.stderr.write(f"golden plant: request {i} ({req.get('t0')}) differs from the recording: {d['paths']}\n")
                sys.exit(2)
            sys.stdout.write(json.dumps(rows[i]["rep"]) + "\n"); sys.stdout.flush()
        if i + 1 != len(rows):
            sys.stderr.write(f"golden plant: {i + 1} requests, {len(rows)} recorded\n"); sys.exit(2)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "plant":
        plant_main(sys.argv[2:]); sys.exit(0)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["record", "check", "list"])
    ap.add_argument("--bin", default=str(REPO / ".build/release/loop-eval"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--par", type=int, default=int(os.environ.get("PAR", 8)))
    a = ap.parse_args()
    if a.cmd == "list":
        for n, c in CASES.items(): print(f"{n:22s} {c['alias']:20s} {' '.join(c['flags'])}")
        sys.exit(0)
    main_suite(a)
