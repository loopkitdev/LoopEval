"""A pool's settings edits as change-test events (LESSONS 525): the pooled screen's edits (2026-10-23-ice-edit-pool/
edits_pool.parquet) that map to the pool's aliases, held >= 14 days on both sides and inside the export; field outcomes with the
tool comparison's scorer (score_tools.py: clean time, pre = day-13..day, post = day+1..day+14, d_ice = clean ICE mean
post - pre). Run from the pool's run dir (templates_<pool>_base.csv); writes change_<pool>/events.csv and
change_<pool>/field_and_tools.csv in the 2026-10-21 format.
    python make_events.py x|e        (ICE root ~/.loop-eval/ice_<pool>32, or ICE_ROOT)"""
import os, sys, json
import numpy as np, pandas as pd
from pathlib import Path
POOL = sys.argv[1]
os.environ.setdefault("ICE_ROOT", os.path.expanduser(f"~/.loop-eval/ice_{POOL}32")); os.environ.setdefault("CFG", "0")
class R:     # clean time as scripts/gen/gen.py clean_mask (ice LESSONS 16); gen.py is a driver, not importable
    ROOT = os.environ["ICE_ROOT"]
    @staticmethod
    def outcomes(bg):
        bg = np.asarray(bg, float); bg = bg[np.isfinite(bg)]
        return dict(tir=100 * ((bg >= 70) & (bg <= 180)).mean(), t70=100 * (bg < 70).mean(), t54=100 * (bg < 54).mean(), mean=bg.mean())
    @staticmethod
    def clean_mask(st, cut):
        te = st[st.t1 > cut - pd.Timedelta(hours=5)].assign(slot=lambda x: x.t1.dt.floor("30min"))
        un = (te.dt * ~te.clean).groupby(te.slot).sum() / te.dt.groupby(te.slot).sum()
        bad = un[un >= 0.5].index.to_numpy()
        def keep(times):
            t = times.to_numpy(); c = np.zeros(len(t), bool)
            for b in bad: c |= (t >= b) & (t <= b + np.timedelta64(270, "m"))
            return ~c
        return keep
OUT = Path.cwd() / f"change_{POOL}"; OUT.mkdir(exist_ok=True)
M = ["tir", "t70", "t54", "mean"]
E = pd.read_parquet(Path.home() / ".loop-eval/runs/2026-10-23-ice-edit-pool/edits_pool.parquet")
inv = {v: k for k, v in json.load(open(Path.home() / f".loop-eval/ice/alias_map_{POOL}.json")).items()}
E["alias"] = E._userId.map(inv); E = E.dropna(subset=["alias"]).drop(columns="_userId")
E["t_edit"] = pd.to_datetime(E.t_edit, utc=True).dt.floor("D")
E = E[(E.clear_before >= 14) & (E.clear_after >= 14)]
tpl = set(pd.read_csv(Path.cwd() / f"templates_{POOL}_base.csv").alias)
E = E[E.alias.isin(tpl)].copy()
E["kind"] = "edit"; E["eid"] = E.alias + "_" + E.t_edit.dt.strftime("%m%d"); E["before"] = "before"; E["after"] = "after"
E = E.drop_duplicates("eid")
wins = lambda day: {"pre": (day - pd.Timedelta(days=13), day), "post": (day + pd.Timedelta(days=1), day + pd.Timedelta(days=14))}
rows, keep = [], []
for _, e in E.iterrows():
    try: st = pd.read_parquet(f"{R.ROOT}/steps/{e.alias}.parquet")
    except Exception: continue
    W = wins(e.t_edit)
    if st.t1.min() > W["pre"][0] or st.t1.max() < W["post"][1]: continue
    def field(w0, w1):
        k = R.clean_mask(st, w0); te = st[(st.t1 > w0) & (st.t1 <= w1)]
        return R.outcomes(te.bg1.to_numpy()[k(te.t1)])
    fp, fq = field(*W["pre"]), field(*W["post"])
    r = dict(eid=e.eid, alias=e.alias, kind="edit", **{f"field_{k}": fq[k] - fp[k] for k in M}, **{f"fieldpre_{k}": fp[k] for k in M})
    r["d_ice"] = (st[(st.t1 > W["post"][0]) & (st.t1 <= W["post"][1]) & st.clean].ice.mean()
                  - st[(st.t1 > W["pre"][0]) & (st.t1 <= W["pre"][1]) & st.clean].ice.mean())
    rows.append(r); keep.append(e.eid)
E = E[E.eid.isin(keep)]
E.to_csv(OUT / "events.csv", index=False); pd.DataFrame(rows).to_csv(OUT / "field_and_tools.csv", index=False)
print(f"{len(E)} {POOL}-pool edits on {E.alias.nunique()} donors -> {OUT}")
