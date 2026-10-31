"""The ICE generator (plant_v3, pilot ice_v32 pool) in closed loop: each donor's held-out last 28 days after one warm-up
day, the generator plant against the donor's deployed controller config, on the Mac or gamepc.
  S=0 RUN_DIR=<run dir> ARMS=gr,stock [ARMS_FILE=<run dir>/arms.py] [BIN=<engine path or ~/frozen commit>] [DONORS=a,b]
  [SEEDS=1] [PAR=6] ~/.venv/bin/python3 scripts/gen/gen.py run|score
Use the torch venv (gamepc ~/venv): the plant inherits this interpreter. One RUN_DIR per experiment: scores go to scores_<TAG>.csv.
Built-in arms: stock, and gr (guard + runway at the frozen constants). Any other arm is the experiment's own, in ARMS_FILE:
  arm(a, name, gr) -> None (built-in) | False (skip this donor) | [flags] | {"flags": [...], "env": {...}, "bin": ...}
  gr(a) is a fresh copy of the gr flag list. env overrides that arm's simulator and plant env (REGIME, ANNOUNCE, SG,
  ICE_TREE = the plant tree, ...); bin is an engine path or a commit frozen at ~/frozen/<commit>. Keep the hook pure.
Host layout, the same on both: GEN_DATA (default ~/frozen/gen-v32) = checkpoints icegen_<TAG>.pt, config.csv,
controller_curves.json, donor_extra_flags.json, eoff_map_oc.json, size_person_oc.json; plant tree ~/frozen/ice-cobt;
data ~/.loop-eval/ice_v32. A frozen engine: git worktree add --detach ~/frozen/<c> <c>, submodule update, swift build."""
import json, os, subprocess, sys, warnings
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
H = os.path.expanduser
GEN = H(os.environ.get("GEN_DATA", "~/frozen/gen-v32")); RUNS = H("~/.loop-eval/runs")
S = os.environ["S"]; HERE = os.path.abspath(H(os.environ["RUN_DIR"])); ROOT = H("~/.loop-eval/ice_v32")
TAG = f"v32oc{S}TcB2FGUCGLBGGSKaLK"; CKPT = f"{GEN}/icegen_{TAG}.pt"; OUT = f"{HERE}/runs_{TAG}"
# plant_v3 settings, read by the plant from its env
PLANT_ENV = dict(ICE_ROOT=ROOT, ICE_TREE=H("~/frozen/ice-cobt/analysis"), PYTHONWARNINGS="ignore", IOBNET_COB="1", PUMPLESS="1",
                 BOLUSMASK="1", ARCH="m21", FEATS="m2i", LOWW="5", TRAIT_SD="3", PLANT_FEEDBACK="sample", PLANT_BGBAND_AFTER="1",
                 PLANT_FOLLOW_MIN="60", PLANT_EOFF_MAP=f"{GEN}/eoff_map_oc.json", PLANT_SIZE_PERSON=f"{GEN}/size_person_oc.json")
PLANT_ARGS = f"--rewarm-h 24 --compression {RUNS}/2026-10-11-ice-compression/compression_layer.json --compression-scale 1"
BIN = H(os.environ.get("BIN", os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.build/release/loop-eval")))

CONFIG = pd.read_csv(f"{GEN}/config.csv").set_index("alias")   # recovered deployed config (24 held-out donors)
CURVES = {k: v for k, v in json.load(open(f"{GEN}/controller_curves.json")).items() if not k.startswith("_")}
EXTRA_DONOR = {k: v for k, v in json.load(open(f"{GEN}/donor_extra_flags.json")).items() if not k.startswith("_")}   # GBAF, increments
# RC mode per donor and era, recovered by simulator from forecast match (docs/handoffs/2026-10-15-frontier-rc-switches.md)
RCM = pd.read_csv(f"{RUNS}/2026-10-15-replay-change/rc/rc_mode.csv").set_index("alias")
# per-donor sigma5 median (gr band k) and frontier's R2 donor list
SIG = json.load(open(f"{RUNS}/2026-10-25-ice-r2/sigma5_p50.json"))
M = pd.read_csv(f"{RUNS}/2026-10-25-ice-r2/r2_multipliers.csv").set_index("donor")
FLAGS = ["--candidate-counterfactual", "--no-mid-absorption-isf", "--no-gradual-transitions-gate", "--legacy-rc-decay",
         "--no-candidate-manual-bolus-from-recommendation", "--no-candidate-iob-adjust-manual-boluses", "--cgm-stale-guard-min", "5"]


def window(a):
    end = pd.read_parquet(f"{ROOT}/steps/{a}.parquet", columns=["t1"]).t1.max().floor("D")
    return end - pd.Timedelta(days=28), end


def rc_window(a, w0, w1):
    """the recovered RC mode ('std' / 'ircc') covering most of [w0, w1); None when no std/ircc era overlaps it"""
    if a not in RCM.index or not isinstance(RCM.eras[a], str):
        return None
    cover = {}
    for era in RCM.eras[a].split(";"):
        mode, span = era.strip().split(" ")
        if mode not in ("std", "ircc"):
            continue
        d0, d1 = (pd.Timestamp(f"{w0.year}-{x}", tz="UTC") for x in span.split(".."))
        ov = (min(w1, d1 + pd.Timedelta(days=1)) - max(w0, d0)).total_seconds()
        if ov > 0:
            cover[mode] = cover.get(mode, 0) + ov
    return max(cover, key=cover.get) if cover else None


def donor_flags(a, w0, w1):
    """the deployed controller: insulin curve, strategy (the window's majority mode), RC mode, GBAF / increments, disruptions"""
    c = CONFIG.loc[a] if a in CONFIG.index else pd.Series(dict(strategy="bolus", rc="std")); f = []; cv = CURVES.get(a)
    rc = rc_window(a, w0, w1) or c.rc
    if cv and "from" not in cv:
        f += ["--controller-insulin-model", "custom", "--custom-insulin-duration-min", str(cv["duration_min"]), "--custom-insulin-peak-min", str(cv["peak_min"])]
    if cv and "from" in cv:
        f += ["--controller-insulin-switch", f"{cv['from']}={cv['duration_min']}/{cv['peak_min']}"]
    d = pd.read_csv(f"{ROOT}/full/{a}/decision_times.csv", usecols=["t", "mode"]); t = pd.to_datetime(d.t, utc=True, format="mixed")
    m = d["mode"][(t >= w0) & (t < w1)].value_counts()
    if (m.idxmax() if len(m) else c.strategy) == "temp":
        f.append("--temp-basal-strategy")
    if rc in ("irc", "ircc"):
        f.append("--integral-rc")
    if rc == "ircc":
        f.append("--integral-rc-clamp")
    f += EXTRA_DONOR.get(a, [])
    if os.path.exists(f"{ROOT}/full/{a}/disruptions.csv"):
        f += ["--outages-csv", f"{ROOT}/full/{a}/disruptions.csv"]
    return f


GBAF_VAL = ("--candidate-gbaf-low-anchor", "--candidate-gbaf-high-anchor", "--candidate-gbaf-factor-low", "--candidate-gbaf-factor-high")


def regime(f, env):
    """REGIME=ab: automatic bolus at application factor 0.4 for every donor (temp-basal strategy and GBAF dropped)"""
    if env.get("REGIME") != "ab": return f
    o, i = [], 0
    while i < len(f):
        if f[i] in ("--temp-basal-strategy", "--candidate-gbaf"): i += 1; continue
        if f[i] in GBAF_VAL: i += 2; continue
        o.append(f[i]); i += 1
    return o + ["--application-factor", "0.4"]


def gr(a):
    return ["--candidate-sigma-band-k", f"{min(1.0, 6.7 / SIG[a]) if SIG.get(a, 0) > 0 else 1.0:.3f}", "--candidate-sigma-band-cob-gate",
            "--candidate-postlow-rc-rise-scale", "0.3", "--candidate-postlow-window", "720", "--candidate-runway-fraction", "0.7",
            "--candidate-runway-cob-gate", "--candidate-runway-bg-min", "150"]


HOOK = None
if os.environ.get("ARMS_FILE"):
    import importlib.util
    _sp = importlib.util.spec_from_file_location("arms", H(os.environ["ARMS_FILE"]))
    HOOK = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(HOOK)


def spec(a, arm):
    """the arm for this donor: {"flags", "env", "bin"}, or None when it skips the donor"""
    s = HOOK.arm(a, arm, gr) if HOOK else None
    if s is None:
        if arm not in ("stock", "gr"): raise KeyError(f"unknown arm {arm!r}: add it in ARMS_FILE")
        s = gr(a) if arm == "gr" else []
    if s is False: return None
    s = {"flags": s} if isinstance(s, list) else dict(s)
    b = s.get("bin")
    s["bin"] = BIN if not b else H(b if os.sep in b else f"~/frozen/{b}/.build/release/loop-eval")
    s["env"] = env = {**os.environ, **PLANT_ENV, **{k: str(v) for k, v in s.get("env", {}).items()}}
    env["ICE_TREE"] = env["PYTHONPATH"] = H(env["ICE_TREE"])
    return s


def run(a, arm, seed):
    cut, end = window(a)
    log = f"{OUT}/{a}_{arm}_{seed}.parquet"
    if os.path.exists(log): return log
    s = spec(a, arm)
    if s is None: return None
    os.makedirs(OUT, exist_ok=True); env = s["env"]
    plant = (f"cd {env['ICE_TREE']} && OMP_NUM_THREADS=1 {sys.executable} -m loopeval_analysis.ice_gen.plant_v3 --alias {a} "
             f"--ckpt {CKPT} --seed {seed} --log {log} {PLANT_ARGS}")
    p = subprocess.run([s["bin"], "simulate", "--data-dir", f"{ROOT}/full/{a}", "--start", (cut - pd.Timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "--end", end.strftime("%Y-%m-%dT%H:%M:%SZ"), "--trace-out", f"{log}.trace.json",
                        *FLAGS, *regime(donor_flags(a, cut, end), env), *s["flags"], "--plant-behavior", "--external-plant", plant],
                       capture_output=True, text=True, env=env)
    if os.path.exists(f"{log}.trace.json"): os.remove(f"{log}.trace.json")
    if not os.path.exists(log): raise RuntimeError(f"{a} {arm}: {p.stderr[-400:]}")
    return log


def clean_mask(st, cut):
    """Clean time: drop every 30-min window with >= 50% excluded ICE and the 4.5 h after it (ice LESSONS 16)"""
    te = st[st.t1 > cut - pd.Timedelta(hours=5)].assign(slot=lambda x: x.t1.dt.floor("30min"))
    un = (te.dt * ~te.clean).groupby(te.slot).sum() / te.dt.groupby(te.slot).sum()
    bad = un[un >= 0.5].index.to_numpy()
    def keep(times):
        t = times.to_numpy(); c = np.zeros(len(t), bool)
        for b in bad:
            c |= (t >= b) & (t <= b + np.timedelta64(270, "m"))
        return ~c
    return keep


def outc(bg, keep):
    bg = np.asarray(bg, float); ok = np.isfinite(bg)
    o = {}
    for lab, k in (("", ok), ("_c", ok & keep)):
        b = bg[k]; o.update({f"tir{lab}": 100 * ((b >= 70) & (b <= 180)).mean(), f"t70{lab}": 100 * (b < 70).mean(),
                             f"t54{lab}": 100 * (b < 54).mean(), f"mean{lab}": b.mean()})
    return o


def score(a, arm, seed):
    log = f"{OUT}/{a}_{arm}_{seed}.parquet"
    if not os.path.exists(log): return None
    cut, end = window(a); lg = pd.read_parquet(log); lg = lg[lg.t1 > cut]
    keep = clean_mask(pd.read_parquet(f"{ROOT}/steps/{a}.parquet"), cut)(lg.t1)
    art = ((lg.comp != 0) | lg.comp_missing).to_numpy()
    r = dict(alias=a, arm=arm, seed=seed)
    r.update({f"cgm_{k}": v for k, v in outc(lg.bg1, keep & ~art).items()})
    r.update({f"true_{k}": v for k, v in outc(lg.bg1 - lg.e - lg.comp, keep).items()})
    b = lg.bg1.to_numpy(); x = np.flatnonzero((b[1:] < 54) & (b[:-1] >= 54)) + 1   # downward 54 crossings on CGM, plant IOB there
    r["n_x54"] = len(x); r["iob_x54"] = float(lg.iob.to_numpy()[x].mean()) if len(x) and "iob" in lg else np.nan
    r["insulin_u"] = pd.DataFrame(json.load(open(f"{log}.doses.json"))).volume.sum() / ((lg.t1.max() - lg.t1.min()).total_seconds() / 86400)
    return r


if __name__ == "__main__":
    import torch
    people = torch.load(CKPT, map_location="cpu", weights_only=False)["people"]
    donors = [a for a in M.index if a in people and os.path.isdir(f"{ROOT}/full/{a}") and os.path.exists(f"{ROOT}/steps/{a}.parquet")]
    if os.environ.get("DONORS"): donors = [a for a in donors if a in os.environ["DONORS"].split(",")]
    arms = os.environ["ARMS"].split(","); seeds = range(int(os.environ.get("SEEDS", 1)))
    try: os.nice(10)   # sims and plants inherit it
    except PermissionError: pass   # already niced (Mac jobq runs at 20; macOS refuses a further increment)
    if sys.argv[1] == "run":
        jobs = [(a, arm, s) for s in seeds for arm in arms for a in donors if spec(a, arm) is not None]
        print(f"{TAG}: {len(donors)} donors, {len(jobs)} runs", flush=True)
        def go(j):
            try: run(*j)
            except Exception as ex: print("FAILED", j, str(ex)[-300:], flush=True)
        with ThreadPoolExecutor(int(os.environ.get("PAR", 6))) as ex: list(ex.map(go, jobs))
        print("runs done", flush=True)
    else:
        with ThreadPoolExecutor(8) as ex:
            rows = [r for r in ex.map(lambda j: score(*j), [(a, arm, s) for s in seeds for arm in arms for a in donors]) if r]
        pd.DataFrame(rows).to_csv(f"{HERE}/scores_{TAG}.csv", index=False); print(len(rows), "scored")
