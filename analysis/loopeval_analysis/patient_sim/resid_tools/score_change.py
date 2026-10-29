"""Change-prediction score of additive variants on the 108 real events (runs/2026-10-21-tool-change): per event the
variant's predicted change (after - before, paired seeds averaged) against the field's change. Headline = the structural
response: OLS of each outcome's change on the insulin index x = log(basal ratio) - log(ISF ratio), with log(CR ratio) and
the target change as covariates (and, for the field, the need shift d_ice and the pre level); the field / variant ratio
(1 = right size) with a 90% bootstrap CI. Also Spearman rho of predicted vs field change per kind.
Usage: score_change.py ARM [ARM ...]   (ARM = a run dir under change/, e.g. additive_base)"""
import pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
HERE = Path(__file__).resolve().parent
BURN = 2880.0
M = ["tir", "t70", "t54", "mean"]
F = pd.read_csv(HERE / "field_and_tools.csv")
E = pd.read_csv(HERE / "events.csv")


def outc(run):
    tr = pickle.load(open(run / "truth.pkl", "rb")); c = tr["cgm"].dropna(); c = c[c.index >= BURN].to_numpy()
    return dict(tir=100 * np.mean((c >= 70) & (c <= 180)), t54=100 * np.mean(c < 54), t70=100 * np.mean(c < 70), mean=float(c.mean()))


def preds(arm):
    rows = []
    for e in E.itertuples():
        d, own = [], []
        for sd in sorted((HERE / arm / f"{e.eid}_after").glob("v0*")):
            b = HERE / arm / f"{e.eid}_before" / sd.name
            if (sd / "truth.pkl").exists() and (b / "truth.pkl").exists():
                oa, ob = outc(sd), outc(b); d.append({k: oa[k] - ob[k] for k in M}); own.append(ob)
        if d:
            rows.append(dict(eid=e.eid, **{f"p_{k}": np.mean([x[k] for x in d]) for k in M},
                             **{f"own_{k}": np.mean([x[k] for x in own]) for k in M}))
    return pd.DataFrame(rows)


def fit(df, y, cols):
    X = np.column_stack([np.ones(len(df))] + [df[c].fillna(0).to_numpy() for c in cols]); yy = df[y].to_numpy()
    ok = np.isfinite(yy) & np.isfinite(X).all(1)
    return np.linalg.lstsq(X[ok], yy[ok], rcond=None)[0][1]


def main(arms):
    ed = F.merge(E[["eid", "basal_before", "basal_after", "isf_before", "isf_after", "cr_before", "cr_after", "target_before", "target_after"]], on="eid")
    ed["x"] = np.log(ed.basal_after / ed.basal_before) - np.log(ed.isf_after / ed.isf_before)
    # the need shift net of the ICE extractor's own response to the edit, which the twins share (LESSONS 541–542):
    # the field is adjusted only for need that moved, not for the settings ISF the edit changed (twins +3–4 per log unit)
    import os as _os
    ed["d_ice"] = ed["d_ice"] - float(_os.environ.get("NEED_MECH", "3.5")) * ed["x"]
    ed["l_cr"] = np.log(ed.cr_after / ed.cr_before); ed["dtgt"] = ed.target_after - ed.target_before
    P = {a: preds(a) for a in arms}
    common = set.intersection(*(set(p.eid) for p in P.values()))
    rng = np.random.default_rng(1)
    for a, p in P.items():
        m = ed.merge(p, on="eid"); m = m[m.eid.isin(common)]
        lv = (m.own_mean - m.fieldpre_mean).median() if "fieldpre_mean" in m else np.nan
        print(f"== {a}: {len(m)} events; own-settings level vs field pre, mean BG median {lv:+.1f}")
        d = m[(m.kind == "edit") & m[[f"field_{k}" for k in M]].notna().all(1)].reset_index(drop=True)
        for k in ["mean", "tir", "t70", "t54"]:
            fc = ["x", "l_cr", "dtgt", "d_ice", "fieldpre_mean"] if "fieldpre_mean" in d else ["x", "l_cr", "dtgt", "d_ice"]
            bf, bp = fit(d, f"field_{k}", fc), fit(d, f"p_{k}", ["x", "l_cr", "dtgt"])
            r = []
            for _ in range(800):
                s = d.iloc[rng.integers(0, len(d), len(d))]
                r.append(fit(s, f"field_{k}", fc) / fit(s, f"p_{k}", ["x", "l_cr", "dtgt"]))
            rho = spearmanr(d[f"p_{k}"], d[f"field_{k}"]).correlation
            print(f"  edit {k:4s} n {len(d)} response per log-unit insulin: field {bf:+6.2f} variant {bp:+6.2f}  "
                  f"field/variant {np.median(r):.2f} [{np.percentile(r, 5):.2f}, {np.percentile(r, 95):.2f}]  rho {rho:+.2f}")
        for kind in ["strategy", "rc"]:
            s = m[(m.kind == kind)]
            print(f"  {kind:8s} n {len(s)}  " + "  ".join(
                f"{k} rho {spearmanr(s[f'p_{k}'], s[f'field_{k}'], nan_policy='omit').correlation:+.2f} sd(pred) {s[f'p_{k}'].std():.2f}" for k in ["tir", "mean", "t70"]))


if __name__ == "__main__":
    main(sys.argv[1:])
