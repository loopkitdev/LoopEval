"""Additive arm of the tool comparison: each event donor's twin, run 14 days under the event's BEFORE and AFTER
controller, paired (same template row, same seeds, so the same person, meals and life events).

  settings edit:   after arm = the twin's settings x (after / before) for day-average basal, ISF, CR; target + (after - before)
  strategy switch: both arms with the strategy forced (temp / autobolus)
  RC switch:       both arms with rc_own off; integral RC (+ clamp for ircc) passed only to the arm that ran it

The body is never touched: template settings columns also feed the body (isf_true, CSF), so settings are changed on the
sampled Person, after sampling. Cohort defaults + --enable rc_own (additive's canonical twin, 2026-10-21) and
--disable edits (no random settings edits of the person's own). Code and binary frozen in the run dir (the change dir's parent); ARM_NAME / ARM_ENABLE (JSON) name the variant.
Usage: additive_arm.py <events.csv> <seeds> <par>"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import pandas as pd

HERE = Path.cwd()                  # the change dir; the run dir above it holds the binary
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # this tree's analysis/ (live or frozen)
import json as _json
EXTRA = _json.loads(os.environ.get("ARM_ENABLE", "{}"))   # the variant's enable additions
TEMPLATES = Path(os.environ.get("ARM_TEMPLATES", str(Path.home() / ".loop-eval/runs/2026-10-15-additive-templates/templates_pilot_logs.csv")))
BIN = str(next(HERE.parent.glob("loop-eval-*")))
OUT = HERE / os.environ.get("ARM_NAME", "additive")
EVM = dict(pd.read_csv(os.environ["ARM_EVM"]).values) if os.environ.get("ARM_EVM") else None   # eid -> resid_m
IRC = {"std": [], "irc": ["--candidate-integral-rc"], "ircc": ["--candidate-integral-rc", "--candidate-integral-rc-clamp"]}


def job(ev: dict, arm: str, seed: int):
    import loopeval_analysis.patient_sim.person as PM
    from loopeval_analysis.patient_sim import cohort
    orig = PM.sample_person
    root = OUT / f"{ev['eid']}_{arm}"
    tmpl = root / "template.csv"
    root.mkdir(parents=True, exist_ok=True)
    T = pd.read_csv(TEMPLATES)
    T[T.alias == ev["alias"]].to_csv(tmpl, index=False)
    enable = {"rc_own": True, "edits": False, **EXTRA}
    flags = {}
    if ev["kind"] == "rc":
        enable["rc_own"] = False
        flags = {"*": IRC[ev[arm]]}

    def patched(*a, **k):
        P = orig(*a, **k)
        st = P.settings
        if ev["kind"] == "edit" and arm == "after":
            for key, col in (("basal_uh", "basal"), ("isf", "isf"), ("cr", "cr")):
                st[key] *= ev[f"{col}_after"] / ev[f"{col}_before"]
            st["max_basal"] = max(st["max_basal"], st["basal_uh"] * max(st.get("basal_profile") or [1.0]))
            st["target"] += ev["target_after"] - ev["target_before"]
        if ev["kind"] == "strategy":
            P.strategy = "temp" if ev[arm] == "temp" else "autobolus"
        if EVM is not None and ev["eid"] in EVM:      # per-event residual level (LESSONS 527): the donor's own pre-edit mean
            P.traits.setdefault("resid", {})["resid_m"] = float(EVM[ev["eid"]])
        return P
    PM.sample_person = patched
    try:
        if os.environ.get("ARM_EVSEED"):     # a seed per event (shared by its two arms): one seed for every event gave every
            import hashlib                     # twin the same person jitter, a common level bias (LESSONS 531)
            seed = seed + (int(hashlib.md5(ev["eid"].encode()).hexdigest(), 16) % 800) * 10
        return cohort._one((seed, 14, str(root), str(tmpl), BIN, enable, "loop-main", flags))
    finally:
        PM.sample_person = orig


def main():
    E = pd.read_csv(sys.argv[1])
    seeds = [int(s) for s in sys.argv[2].split(",")]
    par = int(sys.argv[3])
    T = pd.read_csv(TEMPLATES)
    E = E[E.alias.isin(T.alias)]
    jobs = [(e._asdict() if hasattr(e, "_asdict") else e.to_dict(), arm, s)
            for _, e in E.iterrows() for arm in ("before", "after") for s in seeds]
    print(f"{len(E)} events, {len(jobs)} runs", flush=True)
    done = 0
    with ProcessPoolExecutor(par) as ex:
        for f in as_completed([ex.submit(job, *j) for j in jobs]):
            done += 1
            s, st = f.result()
            if done % 20 == 0 or not str(st).startswith(("ok", "cached")):
                print(f"{done}/{len(jobs)} v{s:05d} {st}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
