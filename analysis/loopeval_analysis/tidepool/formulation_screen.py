"""Screen the donor pool for the insulin model / formulation each person ran, by age band.

Two independent signals, deliberately kept apart:

  * **model** — Loop's own insulin-model setting (`rapidAdult` / `rapidChild`), when the
    record carries one. Authoritative when present, absent for most donors.
  * **brand** — the formulation on the pump record (`insulinFormulation.simple.brand`,
    NOT `.brand` — see the note in PRIVATE.md). Fiasp/Lyumjev are ultra-rapid, which in
    Loop implies the ultra-rapid model; NovoLog/Humalog/Apidra are compatible with either
    the adult or the child model, so a rapid brand alone resolves nothing.

**The adult/child setting applies only to rapid-acting insulin.** Ultra-rapid has its own
model with no adult/child variant, so on an ultra-rapid brand the setting is simply not in
play — a record carrying `rapidChild` next to Fiasp is a stale or since-changed setting, not
a contradiction. Brand therefore decides first, and the setting is consulted only when the
brand is rapid:

    ultra-rapid   ultra-rapid brand — the model follows the brand; adult/child does not apply
    rapid-adult   rapid brand, adult setting
    rapid-child   rapid brand, child setting
    unknown       rapid brand but no setting to disambiguate, or no signal at all

The 2026-08-25 cut predates this and scored `rapidChild` + ultra-rapid as its own `mixed`
category; `categorize(legacy=True)` reproduces that older labelling for the regression check
in `--verify`, and nothing else should use it.

Inputs are the two CSVs a pull leaves in a run dir:

    model_vs_age.csv          uid, age, group, pediatric, detected, used_child, models
    formulation_periods.csv   uid, brand, insulin_class, replay_model, start, end, days

Usage:
    python3 -m loopeval_analysis.tidepool.formulation_screen <run-dir>              # every band
    python3 -m loopeval_analysis.tidepool.formulation_screen <run-dir> --band adult
    python3 -m loopeval_analysis.tidepool.formulation_screen <run-dir> --verify     # regression
    python3 -m loopeval_analysis.tidepool.formulation_screen <run-dir> --brands     # exact brand

`--brands` resolves past the rapid/ultra-rapid class to the brand itself. For the donors who
changed insulin mid-record there is no single right label: they get a dominant brand (by
days) plus a `switcher` flag, and `--write` emits their full period timeline.

`--windows transition_users.csv` is the precise form, and the one to prefer: each donor has
their own 27-day transition window, so resolve the brand *in that window* rather than the
brand they used most across a multi-year record. It reports coverage honestly — a donor
whose formulation record does not reach their window is `record-out-of-window`, not a guess.

`--verify` re-derives the 2026-08-25 pediatric cut and diffs it against the
`pediatric_model_breakdown.csv` saved beside it: the screen is only trustworthy while it
still reproduces that hand-checked result exactly.
"""
import argparse
import os
import pandas as pd

# The pull's own artefacts, plus the hand-checked cut `--verify` measures against. Outputs
# are written under a `screen_` prefix so a re-run can never land on one of these; a bare
# `--write` once overwrote the reference and it had to be rebuilt from the raw inputs.
PROTECTED = frozenset({
    "model_vs_age.csv", "formulation_periods.csv", "no_formulation_data.txt",
    "transition_users.csv", "pediatric_model_summary.csv", "pediatric_model_breakdown.csv",
})

MIXED = "mixed (child model + ultra-rapid insulin)"
PEDIATRIC_GROUPS = ("Children (6–<12)", "Adolescents (12–<18)")
ADULT_GROUPS = ("Adults (18–64)", "Older Adults (≥65)")


def _out(run_dir, name):
    """Resolve an output path, refusing to write over a source or reference file."""
    name = f"screen_{name}"
    if name in PROTECTED:
        raise ValueError(f"refusing to overwrite {name}")
    return os.path.join(run_dir, name)


def load(run_dir):
    """Read the two raw CSVs out of a pull's run dir."""
    ages = pd.read_csv(os.path.join(run_dir, "model_vs_age.csv"))
    periods = pd.read_csv(os.path.join(run_dir, "formulation_periods.csv"))
    return ages, periods


def categorize(ages, periods, legacy=False):
    """One row per donor: the age band, both signals, and the category they imply.

    `legacy=True` restores the 2026-08-25 labelling, which treated a child setting alongside
    ultra-rapid insulin as a `mixed` contradiction. It is kept only so `--verify` can prove
    the screen still reproduces that hand-checked cut; see the module docstring.
    """
    brands = periods.groupby("uid").brand.apply(lambda s: ";".join(sorted(set(s))))
    ultra = set(periods.loc[periods.insulin_class == "ultra-rapid", "uid"])

    df = ages.copy()
    df["brands"] = df.uid.map(brands).fillna("")
    df["ultra"] = df.uid.isin(ultra)
    df["models"] = df.models.fillna("")

    def legacy_cat(r):
        if "rapidChild" in r.models:
            return MIXED if r.ultra else "rapid-child"
        if "rapidAdult" in r.models:
            return "rapid-adult"
        return "ultra-rapid" if r.ultra else "unknown"

    def cat(r):
        # Brand decides first: on ultra-rapid there is no adult/child variant to choose.
        if r.ultra:
            return "ultra-rapid"
        if "rapidChild" in r.models:
            return "rapid-child"
        if "rapidAdult" in r.models:
            return "rapid-adult"
        return "unknown"

    df["category"] = df.apply(legacy_cat if legacy else cat, axis=1)
    # True where the adult/child setting is actually in play — i.e. the insulin is rapid.
    df["setting_applies"] = ~df.ultra
    return df


def precise(ages, periods):
    """One row per donor with formulation data: the exact brand, not just its class.

    A donor who switched insulin has no single brand. `dominant` is whichever brand covers
    the most days, `switcher` marks that the label hides a change, and `brands` keeps the
    full set — for replay, use the period timeline rather than any one of these.
    """
    per = periods.copy()
    per["start"] = pd.to_datetime(per.start)
    per["end"] = pd.to_datetime(per.end)

    days = per.groupby(["uid", "brand"]).days.sum()
    dom = days.groupby(level=0).idxmax().apply(lambda t: t[1])
    g = per.groupby("uid")

    out = pd.DataFrame({
        "brands": g.brand.apply(lambda s: ";".join(sorted(set(s)))),
        "n_brands": g.brand.nunique(),
        "n_periods": g.size(),
        "dominant": dom,
        "dominant_days": days.groupby(level=0).max(),
        "total_days": g.days.sum(),
        "first": g.start.min().dt.date,
        "last": g.end.max().dt.date,
        "replay_models": g.replay_model.apply(lambda s: ";".join(sorted(set(s)))),
    })
    out["switcher"] = out.n_brands > 1
    out["dominant_frac"] = (out.dominant_days / out.total_days).round(3)

    meta = ages.set_index("uid")[["age", "group"]]
    return out.join(meta, how="left").reset_index().rename(columns={"index": "uid"})


def at_window(periods, windows):
    """Resolve each donor's brand *during their own transition window*.

    The blunt alternative — whichever brand covers the most days of the whole record — can
    name an insulin the person had stopped using a year before the window that matters. Here
    a brand counts only for the days it overlaps the window, and donors the record does not
    reach are reported as uncovered rather than guessed at.

    `coverage` is one of:
        covered               a formulation period overlaps the window
        record-out-of-window  the donor has formulation data, but none of it reaches the window
        no-record             no formulation data at all
    """
    w = windows.rename(columns={"_userId": "uid"}).copy()
    w["win_start"] = pd.to_datetime(w.transition_window_start)
    w["win_end"] = pd.to_datetime(w.transition_window_end)

    per = periods.copy()
    per["start"] = pd.to_datetime(per.start)
    per["end"] = pd.to_datetime(per.end)

    m = per.merge(w[["uid", "win_start", "win_end"]], on="uid")
    overlap = (m[["end", "win_end"]].min(axis=1) - m[["start", "win_start"]].max(axis=1)).dt.days + 1
    m["overlap_days"] = overlap.clip(lower=0)
    hit = m[m.overlap_days > 0]

    days = hit.groupby(["uid", "brand"]).overlap_days.sum()
    g = hit.groupby("uid")
    res = pd.DataFrame({
        "brand": days.groupby(level=0).idxmax().apply(lambda t: t[1]),
        "overlap_days": days.groupby(level=0).max(),
        "in_window_brands": g.brand.apply(lambda s: ";".join(sorted(set(s)))),
        "n_brands_in_window": g.brand.nunique(),
        "replay_model": g.replay_model.apply(lambda s: ";".join(sorted(set(s)))),
    })
    res["changed_in_window"] = res.n_brands_in_window > 1

    out = w.set_index("uid").join(res, how="left")
    has_record = set(periods.uid)
    out["coverage"] = [
        "covered" if isinstance(b, str) else ("record-out-of-window" if u in has_record else "no-record")
        for u, b in zip(out.index, out.brand)
    ]
    return out.reset_index()


def brand_summary(df):
    """Exact brand × age-group counts, counting a switcher under its dominant brand."""
    t = pd.crosstab(df.dominant, df.group)
    t["Total"] = t.sum(axis=1)
    t.loc["Total"] = t.sum()
    return t


def summary(df):
    """category × age-group counts, with a Total row and column."""
    t = pd.crosstab(df.category, df.group)
    t["Total"] = t.sum(axis=1)
    t.loc["Total"] = t.sum()
    return t


def band(df, which):
    if which == "pediatric":
        return df[df.group.isin(PEDIATRIC_GROUPS)]
    if which == "adult":
        return df[df.group.isin(ADULT_GROUPS)]
    return df


def verify(run_dir, df):
    """Reproduce the hand-checked 2026-08-25 pediatric breakdown, or say how it differs."""
    ref_path = os.path.join(run_dir, "pediatric_model_breakdown.csv")
    if not os.path.exists(ref_path):
        return f"no reference at {ref_path} — nothing to verify against"
    ref = pd.read_csv(ref_path).set_index("_userId").category
    mine = band(df, "pediatric").set_index("uid").category
    if set(ref.index) != set(mine.index):
        only_ref = len(set(ref.index) - set(mine.index))
        only_mine = len(set(mine.index) - set(ref.index))
        return f"VERIFY FAILED: donor sets differ (reference-only {only_ref}, screen-only {only_mine})"
    diff = mine.reindex(ref.index) != ref
    if diff.any():
        return f"VERIFY FAILED: {int(diff.sum())} of {len(ref)} donors categorized differently"
    return f"verified: {len(ref)}/{len(ref)} donors reproduce the 2026-08-25 pediatric cut"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="dir holding model_vs_age.csv + formulation_periods.csv")
    ap.add_argument("--band", choices=["all", "pediatric", "adult"], default="all")
    ap.add_argument("--verify", action="store_true", help="check against the saved pediatric cut")
    ap.add_argument("--brands", action="store_true", help="resolve the exact brand, not just its class")
    ap.add_argument("--windows", metavar="CSV", help="transition_users.csv: resolve the brand in "
                                                     "each donor's own window (the precise form)")
    ap.add_argument("--write", action="store_true", help="write the screen_<band>_* CSVs")
    a = ap.parse_args()

    ages, periods = load(a.run_dir)
    df = categorize(ages, periods)

    if a.verify:
        print(verify(a.run_dir, categorize(ages, periods, legacy=True)))

    sel = band(df, a.band)
    print(f"\n=== {a.band}: {len(sel)} donors ===")
    print(summary(sel).to_string())

    known = sel[sel.category != "unknown"]
    if len(sel):
        print(f"\nresolved: {len(known)}/{len(sel)} ({100 * len(known) / len(sel):.0f}%)")
    if len(known):
        print("\namong the resolved:")
        print((100 * known.category.value_counts(normalize=True)).round(1).to_string())

    if a.windows:
        w = pd.read_csv(a.windows)
        aw = at_window(periods, w)
        aw = aw[aw.uid.isin(sel.uid)]
        print(f"\n=== {a.band}: brand during the donor's own transition window ===")
        print(pd.crosstab(aw.coverage, aw.age_group, margins=True).to_string())
        cov = aw[aw.coverage == "covered"]
        print(f"\nresolved in-window: {len(cov)}/{len(aw)} ({100 * len(cov) / len(aw):.0f}%)")
        if len(cov):
            t = pd.crosstab(cov.brand, cov.age_group)
            t["Total"] = t.sum(axis=1)
            t.loc["Total"] = t.sum()
            print(t.to_string())
            ch = cov[cov.changed_in_window]
            print(f"\nchanged insulin inside the window: {len(ch)}")
            if len(ch):
                print(ch[["age_years", "age_group", "in_window_brands",
                          "win_start", "win_end"]].to_string(index=False))
        if a.write:
            aw.to_csv(_out(a.run_dir, f"{a.band}_formulation_at_window.csv"), index=False)
            print(f"\nwrote screen_{a.band}_formulation_at_window.csv to {a.run_dir}")

    if a.brands:
        pre = precise(ages, periods)
        pre = pre[pre.uid.isin(sel.uid)]
        print(f"\n=== {a.band}: exact formulation, {len(pre)} of {len(sel)} donors with a record ===")
        print(brand_summary(pre).to_string())
        sw = pre[pre.switcher].sort_values("age")
        print(f"\nswitched insulin mid-record: {len(sw)} donors "
              f"({100 * len(sw) / len(pre):.0f}% of those with a record)")
        if len(sw):
            print(sw[["age", "group", "brands", "n_periods", "dominant",
                      "dominant_frac", "first", "last"]].to_string(index=False))

    if a.write:
        cols = ["uid", "age", "group", "category", "models", "brands"]
        summary(sel).to_csv(_out(a.run_dir, f"{a.band}_model_summary.csv"))
        sel[cols].sort_values(["group", "age"]).to_csv(
            _out(a.run_dir, f"{a.band}_model_breakdown.csv"), index=False)
        pre = precise(ages, periods)
        pre = pre[pre.uid.isin(sel.uid)]
        pre.sort_values(["group", "age"]).to_csv(
            _out(a.run_dir, f"{a.band}_formulation.csv"), index=False)
        periods[periods.uid.isin(sel.uid)].to_csv(
            _out(a.run_dir, f"{a.band}_formulation_periods.csv"), index=False)
        print(f"\nwrote the screen_{a.band}_* CSVs to {a.run_dir}")


if __name__ == "__main__":
    main()
