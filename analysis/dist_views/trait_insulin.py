#!/usr/bin/env python3
"""View 23 — trait or state, on the insulin side.

The glucose-only pass could only ask about glucose. With the four-stream export
the same question extends to how a person's insulin actually behaves, and to how
they operate the system. Those are separable, and the split is the interesting
part: someone can be metabolically steady while changing their settings weekly,
or run a fixed regimen with unstable physiology.

Settings columns are included on purpose. Their between-person ICC says nothing
about biology — a schedule is whatever the person last typed — but their
WITHIN-person variance measures settings churn, which is a real behaviour and one
that bounds how stable anything downstream of the settings can be.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt                              # noqa: E402
import style as S                                            # noqa: E402
from loopeval_analysis import traits as T                    # noqa: E402

OUT = S.OUT
GROUPS = {
    "physiology": ["ia_abs_mean", "ice_abs_mean", "ia_sched_share",
                   "iob_net_mean", "corr_v_ia"],
    "operation": ["tdd", "basal_frac", "auto_frac_u", "carb_g_day",
                  "manual_bolus_day"],
    "settings": ["isf_mean", "cr_mean", "basal_sched_mean", "target_lo_mean"],
}
NICE = {
    "ia_abs_mean": "insulin action (mg/dL/h)", "ice_abs_mean": "non-insulin appearance",
    "ia_sched_share": "scheduled-basal share of action", "iob_net_mean": "mean IOB (net)",
    "corr_v_ia": "corr(velocity, insulin action)",
    "tdd": "total daily dose", "basal_frac": "basal share of TDD",
    "auto_frac_u": "automated share of boluses", "carb_g_day": "carbs announced /day",
    "manual_bolus_day": "manual boluses /day",
    "isf_mean": "ISF setting", "cr_mean": "carb-ratio setting",
    "basal_sched_mean": "scheduled basal", "target_lo_mean": "target low",
}
COL = {"physiology": S.COOL, "operation": S.ACCENT, "settings": S.WARM}


def build() -> pd.DataFrame:
    co = S.cohort()
    frames = []
    for alias in co["alias"]:
        try:
            panel = S.load(alias)
        except Exception:                                     # noqa: BLE001
            continue
        b = T.panel_block_features(panel, block="7D")
        if len(b) >= 4:
            b["alias"] = alias
            b["source"] = panel.attrs.get("source", "?")
            frames.append(b)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> int:
    F = build()
    if F.empty:
        print("no panels with insulin streams")
        return 1
    F.to_pickle(OUT / "trait_blocks_insulin.pkl")
    print(f"{F.alias.nunique()} people, {len(F)} person-weeks")
    print(F.groupby("source").agg(people=("alias", "nunique"),
                                  weeks=("alias", "size")).to_string())

    feats = [f for g in GROUPS.values() for f in g if f in F.columns]
    I = T.icc_table(F, feats)
    I.to_csv(OUT / "trait_icc_insulin.csv", index=False)
    grp = {f: g for g, fs in GROUPS.items() for f in fs}
    I["group"] = I["feature"].map(grp)

    print("\n" + "=" * 76)
    print("TRAIT OR STATE — insulin side, weekly blocks")
    print("=" * 76)
    print(f"{'feature':<32}{'group':<12}{'ICC':>7}{'90% CI':>15}{'within CV':>11}")
    for r in I.itertuples():
        if not np.isfinite(r.icc):
            continue
        d = F[["alias", r.feature]].dropna()
        w = d.groupby("alias")[r.feature].std().mean()
        lvl = abs(d[r.feature].mean())
        print(f"{NICE.get(r.feature, r.feature):<32}{r.group:<12}{r.icc:>7.3f}"
              f"{f'[{r.lo:.2f},{r.hi:.2f}]':>15}{100*w/max(lvl,1e-9):>10.0f}%")

    # ── figure ──
    I2 = I[np.isfinite(I["icc"])].sort_values("icc")
    fig, ax = S.figure(1, 2, figsize=(14.2, 6.6),
                       gridspec_kw={"width_ratios": [1.3, 1]})
    y = np.arange(len(I2))
    for i, r in enumerate(I2.itertuples()):
        c = COL.get(r.group, S.MUTED)
        ax[0].plot([r.lo, r.hi], [i, i], color=c, lw=2.4, alpha=0.9,
                   solid_capstyle="round")
        ax[0].plot([r.icc], [i], "o", color=c, ms=6.5, mec=S.SURFACE, mew=1.3,
                   zorder=3)
    ax[0].set_yticks(y)
    ax[0].set_yticklabels([NICE.get(f, f) for f in I2["feature"]], fontsize=9,
                          color=S.INK2)
    for v in (0.3, 0.5, 0.6):
        ax[0].axvline(v, color=S.MUTED, lw=1.0, ls=(0, (3, 3)))
    ax[0].set_xlim(0, 1)
    ax[0].set_xlabel("intraclass correlation", fontsize=9.5, color=S.INK2)
    for g, c in COL.items():
        ax[0].plot([], [], color=c, lw=3, label=g)
    ax[0].legend(frameon=False, fontsize=8.5, labelcolor=S.INK2, loc="lower left")
    ax[0].set_title("How much of each is the person?", fontsize=11, color=S.INK,
                    loc="left", pad=8, weight="bold")

    # within-person churn: how much a person's own value moves week to week
    rows = []
    for f in I2["feature"]:
        d = F[["alias", f]].dropna()
        if d.alias.nunique() < 3:
            continue
        w = d.groupby("alias")[f].std() / d.groupby("alias")[f].mean().abs()
        rows.append((f, float(np.nanmedian(w)), grp.get(f, "")))
    C = pd.DataFrame(rows, columns=["feature", "churn", "group"]).sort_values("churn")
    yy = np.arange(len(C))
    ax[1].barh(yy, C["churn"] * 100, color=[COL.get(g, S.MUTED) for g in C["group"]],
               alpha=0.9, height=0.7)
    ax[1].set_yticks(yy)
    ax[1].set_yticklabels([NICE.get(f, f) for f in C["feature"]], fontsize=8.5,
                          color=S.INK2)
    ax[1].set_xlabel("median within-person week-to-week variation (% of own level)",
                     fontsize=9.5, color=S.INK2)
    ax[1].set_title("How much it moves for one person", fontsize=11, color=S.INK,
                    loc="left", pad=8, weight="bold")

    S.title(fig, "23 · Trait or state, on the insulin side",
            "Same weekly-block intraclass correlation as view 19, on quantities that need the dose, carb and therapy streams. "
            "Blue is the person's metabolic operating\npoint, orange is how they run the system, gold is what their settings say. "
            "The right panel is the companion question ICC cannot answer: how far a person's own\nvalue moves from week to week, "
            "as a share of their own level.")
    S.save(fig, "23_trait_insulin",
           dict(left=0.215, right=0.985, top=0.815, bottom=0.10, wspace=0.55))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
