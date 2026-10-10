#!/usr/bin/env python3
"""Every number on the "ISF, Rule of X and Outcomes" page, regenerated.

Reads isf_rules.csv (settings_rules.py + settings_explore/) and
cap_changes_loose.csv (settings_explore/cap_changers.py). Prints each claim and
writes settings_claims.json, which doc_settings.py transcribes — prose is never
typed from memory (lesson 23).

Partial correlations are Spearman: every variable ranked, the covariates
regressed out of both ranks, the residuals correlated (t-test, n-k-2 df).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as S  # noqa

RULE_EDGES = [0, 1400, 1700, 2000, 2400, 1e9]
RULE_LABELS = ["< 1400", "1400–1700", "1700–2000", "2000–2400", "≥ 2400"]
BOL_EDGES = [0, 3, 5, 8, 1e9]
BOL_LABELS = ["< 3", "3–5", "5–8", "≥ 8"]


def pcorr(d, x, y, covs):
    m = d[[x, y] + covs].dropna()
    r = m.rank()
    X = np.column_stack([np.ones(len(r))] + [r[c] for c in covs])
    res = lambda v: v - X @ np.linalg.lstsq(X, v, rcond=None)[0]
    rx, ry = res(r[x].to_numpy()), res(r[y].to_numpy())
    rho = float(np.corrcoef(rx, ry)[0, 1])
    df = len(m) - len(covs) - 2
    t = rho * np.sqrt(df / max(1 - rho ** 2, 1e-12))
    return rho, float(2 * stats.t.sf(abs(t), df)), int(len(m))


def mw(a, b):
    return float(stats.mannwhitneyu(a.dropna(), b.dropna()).pvalue)


def main():
    d = pd.read_csv(S.OUT / "isf_rules.csv")
    d["log_tdd"] = np.log(d.tdd_use); d["log_isf"] = np.log(d.isf)
    d["rule"] = d.k1800
    d["rule_bin"] = pd.cut(d.rule, RULE_EDGES, labels=RULE_LABELS, right=False)
    d["temp"] = (d.strategy == "temp").astype(float)
    C = {"n": len(d)}

    # 1 — the rule of X
    C["rule_median"] = d.rule.median(); C["rule_p10"] = d.rule.quantile(.1); C["rule_p90"] = d.rule.quantile(.9)
    b, a = np.polyfit(d.log_tdd, d.log_isf, 1)
    C["fit_K"], C["fit_b"] = float(np.exp(a)), float(-b)
    C["fit_b_by_pump"] = {p: float(-np.polyfit(g.log_tdd, g.log_isf, 1)[0]) for p, g in d.groupby("pump") if len(g) >= 20}
    q = pd.qcut(d.tdd_use, 4, labels=["Q1", "Q2", "Q3", "Q4"])
    C["rule_by_tdd_quartile"] = d.groupby(q, observed=True).rule.median().round(0).to_dict()
    C["tdd_quartile_edges"] = d.tdd_use.quantile([.25, .5, .75]).round(1).tolist()

    # 2 — rule of X against outcomes
    for y in ("tir", "t70", "t54"):
        C[f"rule_{y}_raw"] = pcorr(d, "rule", y, [])
        C[f"rule_{y}_tdd_age"] = pcorr(d, "rule", y, ["log_tdd", "age_years"])
        C[f"rule_{y}_tdd_age_bol"] = pcorr(d, "rule", y, ["log_tdd", "age_years", "manual_bolus_day"])
    t = d.groupby("rule_bin", observed=True).agg(n=("alias", "size"), tir=("tir", "median"),
                                                 t70=("t70", "median"), t54=("t54", "median"))
    C["rule_bins"] = t.round(2).to_dict("index")
    ts = d.groupby(["strategy", "rule_bin"], observed=True).agg(n=("alias", "size"), tir=("tir", "median"),
                                                                 t54=("t54", "median"))
    C["rule_bins_by_strategy"] = {f"{s}|{b}": v for (s, b), v in ts.round(2).to_dict("index").items()}

    # 3 — the people at TIR >= 80 and time below 54 <= 1
    top = (d.tir >= 80) & (d.t54 <= 1)
    C["top_n"] = int(top.sum())
    C["top_rule"] = d.rule[top].median(); C["rest_rule"] = d.rule[~top].median()
    C["top_rule_p"] = mw(d.rule[top], d.rule[~top])
    res = d.log_isf - np.polyval(np.polyfit(d.log_tdd, d.log_isf, 1), d.log_tdd)
    C["top_isf_vs_peers_pct"] = float(100 * (np.exp(res[top].median() - res[~top].median()) - 1))
    C["top_isf_vs_peers_p"] = mw(res[top], res[~top])
    tq = pd.qcut(d.tdd_use, 3, labels=["low", "mid", "high"])
    C["top_isf_vs_peers_by_tdd_third"] = {
        str(k): float(100 * (np.exp(res[top & (tq == k)].median() - res[~top & (tq == k)].median()) - 1))
        for k in ["low", "mid", "high"] if (top & (tq == k)).sum() >= 3}
    C["top_by_tdd_third_n"] = {str(k): int((top & (tq == k)).sum()) for k in ["low", "mid", "high"]}

    # 4 — strategy
    C["strategy_n"] = d.strategy.value_counts().to_dict()
    C["strategy_pump"] = pd.crosstab(d.strategy, d.pump).to_dict("index")
    C["strategy_sensor"] = pd.crosstab(d.strategy, d.sensor).to_dict("index")
    for y in ("tir", "t70", "t54", "rule"):
        C[f"{y}_by_strategy"] = d.groupby("strategy")[y].median().round(2).to_dict()
        C[f"{y}_strategy_p"] = mw(d[d.strategy == "bolus"][y], d[d.strategy == "temp"][y])
    C["t54_strategy_partial"] = pcorr(d, "temp", "t54", ["log_tdd", "age_years", "target"])
    young = d.age_years < 26
    C["t54_by_strategy_under26"] = d[young].groupby("strategy").t54.median().round(2).to_dict()
    C["t54_by_strategy_26plus"] = d[~young].groupby("strategy").t54.median().round(2).to_dict()

    # 5 — the cap (temp-basal users)
    tb = d[d.strategy == "temp"].copy()
    tb["log_head"] = np.log(tb.headroom)
    covs = ["log_tdd", "age_years", "target"]
    C["temp_n"] = len(tb)
    C["temp_rule_tir"] = pcorr(tb, "rule", "tir", covs + ["log_head"])
    C["temp_rule_t70"] = pcorr(tb, "rule", "t70", covs + ["log_head"])
    C["temp_rule_t54"] = pcorr(tb, "rule", "t54", covs + ["log_head"])
    C["temp_head_tir"] = pcorr(tb, "log_head", "tir", covs + ["rule"])
    C["temp_head_t70"] = pcorr(tb, "log_head", "t70", covs + ["rule"])
    C["temp_head_t54"] = pcorr(tb, "log_head", "t54", covs + ["rule"])
    C["temp_rule_head_rho"] = float(stats.spearmanr(tb.rule, tb.headroom)[0])
    r = tb[["rule", "headroom", "tir", "t70", "t54", "log_tdd", "age_years", "target"]].dropna().rank()
    r["inter"] = (r.rule - r.rule.mean()) * (r.headroom - r.headroom.mean())
    ps = {}
    for y in ("tir", "t70", "t54"):
        X = np.column_stack([np.ones(len(r)), r.rule, r.headroom, r.inter, r.log_tdd, r.age_years, r.target])
        beta, *_ = np.linalg.lstsq(X, r[y], rcond=None)
        e = r[y] - X @ beta
        s2 = e @ e / (len(r) - X.shape[1])
        se = np.sqrt(s2 * np.linalg.inv(X.T @ X)[3, 3])
        ps[y] = float(2 * stats.t.sf(abs(beta[3] / se), len(r) - X.shape[1]))
    C["temp_interaction_p"] = ps
    strong = tb.rule < tb.rule.median()
    low_cap = tb.headroom < tb.headroom.median()
    g = tb.groupby([strong.map({True: "strong", False: "weak"}), low_cap.map({True: "low cap", False: "high cap"})])
    C["temp_2x2"] = {f"{a}|{b}": v for (a, b), v in g.agg(n=("alias", "size"), tir=("tir", "median"),
                                                            t70=("t70", "median")).round(2).to_dict("index").items()}
    C["temp_rule_median"] = float(tb.rule.median()); C["temp_head_median"] = float(tb.headroom.median())
    ag = tb[strong]; ot = tb[~strong]
    C["strong_max_basal"] = [float(ag.max_basal.median()), float(ot.max_basal.median()), mw(ag.max_basal, ot.max_basal)]
    C["strong_pinned"] = [float(ag.at_max_when_high.median()), float(ot.at_max_when_high.median()),
                          mw(ag.at_max_when_high, ot.at_max_when_high)]
    good = (ag.tir >= ag.tir.median())
    C["strong_pinned_by_tir"] = [float(ag[good].at_max_when_high.median()), float(ag[~good].at_max_when_high.median()),
                                 mw(ag[good].at_max_when_high, ag[~good].at_max_when_high)]

    # 6 — within-person cap changes
    cc = pd.read_csv(S.OUT / "cap_changes_loose.csv")
    C["cap_changes_n"] = len(cc); C["cap_changes_people"] = int(cc.alias.nunique())
    clean = cc[cc.clean]
    C["cap_clean"] = clean.dir.value_counts().to_dict()
    up = clean[clean.dir == "raised"]
    C["cap_up_pct"] = float(up.pct.median())
    for y in ("tir", "t70", "t54", "mean", "tdd", "pin"):
        dd = up[f"post_{y}"] - up[f"pre_{y}"]
        C[f"cap_up_{y}"] = [float(dd.median()), float(stats.wilcoxon(up[f"post_{y}"], up[f"pre_{y}"]).pvalue)]
    C["cap_pre_days_min"] = int(cc.pre_days.min()); C["cap_post_days_min"] = int(cc.post_days.min())

    # 7 — bolus frequency and TDD
    C["bol_tir"] = pcorr(d, "manual_bolus_day", "tir", ["log_tdd", "rule", "age_years", "target", "temp"])
    C["bol_t70"] = pcorr(d, "manual_bolus_day", "t70", ["log_tdd", "rule", "age_years", "target", "temp"])
    C["bol_t54"] = pcorr(d, "manual_bolus_day", "t54", ["log_tdd", "rule", "age_years", "target", "temp"])
    bb = pd.cut(d.manual_bolus_day, BOL_EDGES, labels=BOL_LABELS, right=False)
    C["tir_by_boluses"] = d.groupby(bb, observed=True).agg(n=("alias", "size"), tir=("tir", "median"),
                                                          t70=("t70", "median")).round(2).to_dict("index")
    C["tdd_tir_raw"] = pcorr(d, "log_tdd", "tir", [])
    C["tdd_tir_adj"] = pcorr(d, "log_tdd", "tir", ["manual_bolus_day", "rule", "age_years"])
    C["age_tir_adj"] = pcorr(d, "age_years", "tir", ["manual_bolus_day", "rule", "log_tdd"])

    def clean_json(o):
        if isinstance(o, dict):
            return {str(k): clean_json(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean_json(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else round(float(o), 4)
        if isinstance(o, (np.integer,)):
            return int(o)
        return o
    C = clean_json(C)
    (S.OUT / "settings_claims.json").write_text(json.dumps(C, indent=1))
    for k, v in C.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()


# ── The 2026-09-24 thread: who meets the target, and the rule of X they run ──
TIER_LABELS = ["TIR ≥ 80, t<54 ≤ 1", "TIR ≥ 80, t<54 > 1", "TIR 70–80", "TIR 60–70", "TIR < 60"]
BIN200_EDGES = [0, 1200, 1400, 1600, 1800, 2000, 2200, 2500, 1e9]
BIN200_LABELS = ["< 1200", "1200s", "1400s", "1600s", "1800s", "2000s", "2200–2500", "2500+"]
BIN4_EDGES = [0, 1400, 1800, 2200, 1e9]
BIN4_LABELS = ["< 1400", "1400–1800", "1800–2200", "2200+"]


def tier(r):
    if r.tir >= 80 and r.t54 <= 1.0:
        return TIER_LABELS[0]
    if r.tir >= 80:
        return TIER_LABELS[1]
    if r.tir >= 70:
        return TIER_LABELS[2]
    if r.tir >= 60:
        return TIER_LABELS[3]
    return TIER_LABELS[4]


def thread_claims():
    from scipy.stats import kruskal
    d = pd.read_csv(S.OUT / "isf_rules.csv")
    d = d[d[["isf", "tdd_use", "tir", "t54"]].notna().all(axis=1)].copy()
    d["well"] = (d.tir >= 80) & (d.t54 <= 1)
    d["tier"] = d.apply(tier, axis=1)
    a, b0 = np.polyfit(np.log(d.tdd_use), np.log(d.isf), 1)
    K = float(np.exp(b0))
    d["ratio"] = d.isf / (K * d.tdd_use ** a)
    W, R = d[d.well], d[~d.well]
    T = {"n": len(d), "well_n": int(len(W)), "fit_K": K, "fit_b": float(-a)}
    T["tiers"] = (d.groupby("tier")[["tdd_use", "isf", "k1800", "tir", "t54", "t70"]].median().round(1)
                  .join(d.groupby("tier").size().rename("n")).reindex(TIER_LABELS).to_dict("index"))
    for c in ("isf", "tdd_use", "k1800", "ratio"):
        T[f"well_{c}"] = [float(W[c].median()), float(R[c].median()), mw(W[c], R[c])]
    tb = pd.qcut(d.tdd_use, 3, labels=["low", "mid", "high"])
    T["tdd_third_edges"] = d.tdd_use.quantile([1 / 3, 2 / 3]).round(1).tolist()
    T["thirds"] = {}
    for k in ("low", "mid", "high"):
        g = d[tb == k]
        w_, r_ = g[g.well], g[~g.well]
        T["thirds"][k] = {"n": int(len(g)), "well": int(len(w_)),
                          "ratio_well": float(w_.ratio.median()) if len(w_) else None,
                          "ratio_rest": float(r_.ratio.median()),
                          "p": mw(w_.ratio, r_.ratio) if len(w_) >= 3 else None}
    r_w = float(W.ratio.median())
    T["well_curve_K"] = K * r_w
    T["implied_x"] = {int(t): {"r1800": 1800 / t, "cohort": K * t ** a, "well": K * r_w * t ** a,
                               "x": K * r_w * t ** a * t,
                               "inside": bool(W.tdd_use.min() <= t <= W.tdd_use.max())}
                      for t in (15, 20, 30, 40, 50, 60, 80)}
    T["well_tdd_range"] = [float(W.tdd_use.min()), float(W.tdd_use.max()), int((W.tdd_use > 50).sum())]
    # fifths of ISF relative to peers at the same TDD
    d["fifth"] = pd.qcut(d.ratio, 5, labels=["strongest", "2", "3", "4", "weakest"])
    d["x40"] = d.ratio * K * 40 ** a * 40
    T["fifths"] = d.groupby("fifth", observed=True).agg(
        n=("tir", "size"), x40=("x40", "median"), tir=("tir", "median"), t70=("t70", "median"),
        t54=("t54", "median"), over1=("t54", lambda s: 100 * (s > 1).mean()),
        well=("well", lambda s: 100 * s.mean())).round(2).to_dict("index")
    for y in ("tir", "t70", "t54"):
        T[f"fifths_p_{y}"] = float(kruskal(*[g[y] for _, g in d.groupby("fifth", observed=True)]).pvalue)
    T["well_by_strategy"] = {s: {"n": int(len(g)), "x": float(g.k1800.median()), "ratio": float(g.ratio.median())}
                             for s, g in W.groupby("strategy")}
    # bins in steps of 200
    d["b200"] = pd.cut(d.k1800, BIN200_EDGES, labels=BIN200_LABELS, right=False)
    T["bins200"] = d.groupby("b200", observed=True).agg(
        n=("tir", "size"), tir=("tir", "median"), tir25=("tir", lambda s: s.quantile(.25)),
        tir75=("tir", lambda s: s.quantile(.75)), t54=("t54", "median"), t70=("t70", "median"),
        tdd=("tdd_use", "median"), well=("well", lambda s: 100 * s.mean())).round(2).to_dict("index")
    T["bins200_p_tir"] = float(kruskal(*[g.tir for _, g in d.groupby("b200", observed=True)]).pvalue)
    T["bins200_p_t54"] = float(kruskal(*[g.t54 for _, g in d.groupby("b200", observed=True)]).pvalue)
    lo = d[d.k1800 < 1200]
    T["sub1200"] = {"n": int(len(lo)), "well": int(lo.well.sum()), "temp": int((lo.strategy == "temp").sum()),
                    "twiist": int((lo.pump == "twiist").sum()), "t70": float(lo.t70.median()),
                    "t70_rest": float(d[d.k1800 >= 1200].t70.median()), "tdd": float(lo.tdd_use.median())}
    # by strategy, four bands
    d["b4"] = pd.cut(d.k1800, BIN4_EDGES, labels=BIN4_LABELS, right=False)
    T["strategy_bins"] = {}
    for s, g in d.groupby("strategy"):
        t = g.groupby("b4", observed=True).agg(n=("tir", "size"), tir=("tir", "median"), t54=("t54", "median"),
                                               t70=("t70", "median"), well=("well", lambda v: 100 * v.mean()),
                                               pinned=("at_max_when_high", "median"))
        T["strategy_bins"][s] = t.round(2).to_dict("index")
        T[f"strategy_rho_{s}"] = float(stats.spearmanr(g.k1800, g.tir)[0])
    tt = d[d.strategy == "temp"].copy()
    tt["hb"] = pd.qcut(tt.headroom, 3, labels=["low", "mid", "high"])
    T["temp_headroom_thirds"] = tt.groupby("hb", observed=True).agg(
        headroom=("headroom", "median"), t70=("t70", "median"), t54=("t54", "median"),
        tir=("tir", "median")).round(2).to_dict("index")
    T["temp_max_basal"] = float(tt.max_basal.median()); T["temp_headroom"] = float(tt.headroom.median())
    lo_t, hi_t = tt[tt.k1800 < 1400], tt[tt.k1800 >= 1400]
    T["temp_low_x_pinned"] = [float(lo_t.at_max_when_high.median()), float(hi_t.at_max_when_high.median()),
                              mw(lo_t.at_max_when_high, hi_t.at_max_when_high)]
    T["temp_low_x_maxbasal"] = [float(lo_t.max_basal.median()), float(hi_t.max_basal.median())]
    # autobolus against temp basal
    B, Tm = d[d.strategy == "bolus"], d[d.strategy == "temp"]
    T["ab_vs_temp"] = {c: [float(B[c].median()), float(Tm[c].median()), mw(B[c], Tm[c])]
                       for c in ("tir", "t70", "t54", "k1800", "age_years")}
    T["ab_vs_temp_over1"] = [float(100 * (B.t54 > 1).mean()), float(100 * (Tm.t54 > 1).mean())]
    T["ab_vs_temp_well"] = [float(100 * B.well.mean()), float(100 * Tm.well.mean())]
    for lab, m in (("26plus", d.age_years >= 26), ("under26", d.age_years < 26)):
        b, t = d[m & (d.strategy == "bolus")], d[m & (d.strategy == "temp")]
        T[f"ab_vs_temp_{lab}"] = {"n": [int(len(b)), int(len(t))], "t54": [float(b.t54.median()), float(t.t54.median()),
                                  mw(b.t54, t.t54)], "tir": [float(b.tir.median()), float(t.tir.median())]}
    om = d[d.pump == "Omnipod"]
    T["omnipod_by_strategy"] = om.groupby("strategy").agg(n=("tir", "size"), tir=("tir", "median"),
                                                          t54=("t54", "median")).round(2).to_dict("index")
    return T


if __name__ == "__main__":
    import json as _j
    T = thread_claims()
    C = _j.loads((S.OUT / "settings_claims.json").read_text())

    def cj(o):
        if isinstance(o, dict):
            return {str(k): cj(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [cj(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else round(float(o), 4)
        if isinstance(o, np.integer):
            return int(o)
        return o
    C["thread"] = cj(T)
    (S.OUT / "settings_claims.json").write_text(_j.dumps(C, indent=1))
    for k, v in C["thread"].items():
        print(f"T.{k}: {v}")
