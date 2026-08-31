"""Screen the donor pool for the insulin model / formulation each person ran, by age band.

Two independent signals, deliberately kept apart:

  * **model** — Loop's own insulin-model setting (`rapidAdult` / `rapidChild`), when the
    record carries one. Authoritative when present, absent for most donors.
  * **brand** — the formulation on the pump record (`insulinFormulation.simple.brand`,
    NOT `.brand` — see the note in PRIVATE.md). Fiasp/Lyumjev are ultra-rapid, which in
    Loop implies the ultra-rapid model; NovoLog/Humalog/Apidra are compatible with either
    the adult or the child model, so a rapid brand alone resolves nothing.

`category` is the join of the two:

    rapid-adult   model says rapidAdult
    rapid-child   model says rapidChild, brand not ultra-rapid
    ultra-rapid   no model, but an ultra-rapid brand pins it
    mixed         model says rapidChild while the insulin is ultra-rapid (they disagree)
    unknown       no model, and no ultra-rapid brand to pin it

Inputs are the two CSVs a pull leaves in a run dir:

    model_vs_age.csv          uid, age, group, pediatric, detected, used_child, models
    formulation_periods.csv   uid, brand, insulin_class, replay_model, start, end, days

Usage:
    python3 -m loopeval_analysis.tidepool.formulation_screen <run-dir>              # every band
    python3 -m loopeval_analysis.tidepool.formulation_screen <run-dir> --band adult
    python3 -m loopeval_analysis.tidepool.formulation_screen <run-dir> --verify     # regression

`--verify` re-derives the 2026-08-25 pediatric cut and diffs it against the
`pediatric_model_breakdown.csv` saved beside it: the screen is only trustworthy while it
still reproduces that hand-checked result exactly.
"""
import argparse
import os
import pandas as pd

MIXED = "mixed (child model + ultra-rapid insulin)"
PEDIATRIC_GROUPS = ("Children (6–<12)", "Adolescents (12–<18)")
ADULT_GROUPS = ("Adults (18–64)", "Older Adults (≥65)")


def load(run_dir):
    """Read the two raw CSVs out of a pull's run dir."""
    ages = pd.read_csv(os.path.join(run_dir, "model_vs_age.csv"))
    periods = pd.read_csv(os.path.join(run_dir, "formulation_periods.csv"))
    return ages, periods


def categorize(ages, periods):
    """One row per donor: the age band, both signals, and the category they imply."""
    brands = periods.groupby("uid").brand.apply(lambda s: ";".join(sorted(set(s))))
    ultra = set(periods.loc[periods.insulin_class == "ultra-rapid", "uid"])

    df = ages.copy()
    df["brands"] = df.uid.map(brands).fillna("")
    df["ultra"] = df.uid.isin(ultra)
    df["models"] = df.models.fillna("")

    def cat(r):
        if "rapidChild" in r.models:
            return MIXED if r.ultra else "rapid-child"
        if "rapidAdult" in r.models:
            return "rapid-adult"
        return "ultra-rapid" if r.ultra else "unknown"

    df["category"] = df.apply(cat, axis=1)
    return df


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
    ap.add_argument("--write", action="store_true", help="write <band>_model_{summary,breakdown}.csv")
    a = ap.parse_args()

    ages, periods = load(a.run_dir)
    df = categorize(ages, periods)

    if a.verify:
        print(verify(a.run_dir, df))

    sel = band(df, a.band)
    print(f"\n=== {a.band}: {len(sel)} donors ===")
    print(summary(sel).to_string())

    known = sel[sel.category != "unknown"]
    if len(sel):
        print(f"\nresolved: {len(known)}/{len(sel)} ({100 * len(known) / len(sel):.0f}%)")
    if len(known):
        print("\namong the resolved:")
        print((100 * known.category.value_counts(normalize=True)).round(1).to_string())

    if a.write:
        cols = ["uid", "age", "group", "category", "models", "brands"]
        summary(sel).to_csv(os.path.join(a.run_dir, f"{a.band}_model_summary.csv"))
        sel[cols].sort_values(["group", "age"]).to_csv(
            os.path.join(a.run_dir, f"{a.band}_model_breakdown.csv"), index=False)
        print(f"\nwrote {a.band}_model_{{summary,breakdown}}.csv to {a.run_dir}")


if __name__ == "__main__":
    main()
