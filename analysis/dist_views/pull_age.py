#!/usr/bin/env python3
"""Per-donor age, from Tidepool's profile tables rather than from device_data.

`device_data` carries no demographics at all; age lives in `seagull_profiles`
(birthday), `patients` (birthDate) and `consent_records` (ageGroup). Age is a
first-order covariate for insulin — a child's requirement is a fraction of an
adult's — so the insulin document needs it, and the glucose document's claim
that the records carry no age is wrong without it.

Privacy: those tables sit beside ones holding names, emails and MRNs. Select
the demographic columns ONLY, write nothing but alias + age, and keep every
published result aggregate ([[lesson 41]]).

Caveat that bounds all of it: a Tidepool profile birthday can belong to the
account holder rather than the wearer, so a child's record may carry a parent's
date or the reverse. Treat an individual age as a hint and the distribution as
approximate. `consent_records.ageGroup` is an independent check — it is what the
consenting party stated — and `grantorType` says whether a parent consented.

Writes age.csv: alias, age_years, source, age_group, grantor.

Run:  python3 pull_age.py                   (needs Databricks credentials)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import screen_cohort as SC                                   # noqa: E402
import style as S                                            # noqa: E402
from loopeval_analysis.tidepool.conn import query             # noqa: E402

# Ages are computed at the midpoint of the analysis window, not today.
MID_MS = (SC.START + SC.END) // 2


def main() -> int:
    amap = SC._ids()
    co = S.cohort()
    ids = {a: amap[a] for a in co["alias"] if a in amap}
    rev = {v: k for k, v in ids.items()}
    lst = ",".join(f"'{u}'" for u in sorted(set(ids.values())))
    mid = pd.to_datetime(MID_MS, unit="ms")
    print(f"{len(ids)} donor ids; ages at {mid.date()}")

    def go(label, q):
        print(f"  {label}…", flush=True)
        return query(q)

    prof = go("seagull_profiles", f"""
        SELECT userid AS uid, birthday FROM prod.default.seagull_profiles
        WHERE userid IN ({lst}) AND birthday IS NOT NULL""")
    pat = go("patients", f"""
        SELECT userId AS uid, min(birthDate) AS birthDate
        FROM prod.default.patients
        WHERE userId IN ({lst}) AND birthDate IS NOT NULL GROUP BY 1""")
    con = go("consent_records", f"""
        SELECT userId AS uid, max(ageGroup) AS ageGroup, max(grantorType) AS grantor
        FROM prod.default.consent_records WHERE userId IN ({lst}) GROUP BY 1""")

    def age_of(series):
        b = pd.to_datetime(series.astype(str).str[:10], errors="coerce", utc=True)
        return (mid.tz_localize("UTC") - b).dt.days / 365.25

    prof["age_prof"] = age_of(prof["birthday"])
    pat["age_pat"] = age_of(pat["birthDate"])
    d = (pd.DataFrame({"uid": sorted(set(ids.values()))})
         .merge(prof[["uid", "age_prof"]], on="uid", how="left")
         .merge(pat[["uid", "age_pat"]], on="uid", how="left")
         .merge(con, on="uid", how="left"))
    # Implausible dates are data, not people: drop rather than clamp.
    for c in ("age_prof", "age_pat"):
        d.loc[~d[c].between(1, 100), c] = np.nan

    both = d.dropna(subset=["age_prof", "age_pat"])
    if len(both):
        agree = (both["age_prof"] - both["age_pat"]).abs()
        print(f"\n  both sources present for {len(both)}: "
              f"agree within 1 year for {(agree < 1).sum()}, "
              f"median |difference| {agree.median():.2f} y")
    d["age_years"] = d["age_prof"].fillna(d["age_pat"])
    d["source"] = np.where(d["age_prof"].notna(), "profile",
                           np.where(d["age_pat"].notna(), "clinic", ""))
    d["alias"] = d["uid"].map(rev)

    out = d[["alias", "age_years", "source", "ageGroup", "grantor"]].rename(
        columns={"ageGroup": "age_group"}).sort_values("alias")
    out.to_csv(S.OUT / "age.csv", index=False)
    have = out["age_years"].notna()
    print(f"\n  age.csv — {int(have.sum())} of {len(co)} donors have an age")
    if have.any():
        a = out.loc[have, "age_years"]
        print(f"  median {a.median():.0f}  p10–p90 {a.quantile(.1):.0f}–{a.quantile(.9):.0f}"
              f"  range {a.min():.0f}–{a.max():.0f}")
        print(f"  under 18: {int((a < 18).sum())}   under 13: {int((a < 13).sum())}"
              f"   65+: {int((a >= 65).sum())}")
    print(f"  ageGroup as stated at consent: {out.age_group.value_counts(dropna=False).to_dict()}")
    print(f"  grantorType: {out.grantor.value_counts(dropna=False).to_dict()}")
    # Does the stated age group corroborate the computed age?
    chk = out[have & out["age_group"].notna()]
    if len(chk):
        band = pd.cut(chk["age_years"], [0, 13, 18, 200],
                      labels=["<13", "13-17", "18+"], right=False)
        print("\n  computed band x stated ageGroup:")
        print(pd.crosstab(band, chk["age_group"]).to_string().replace("\n", "\n    "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
