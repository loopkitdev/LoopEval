#!/usr/bin/env python3
"""Per-donor insulin formulation from source, as a BRAND and a category.

The ETL reads `insulinFormulation.simple.brand` correctly but maps it straight
onto an EvalCore model preset, so the exported `insulinType` cannot tell
"recorded as Humalog" from "no brand recorded" — both arrive as
`rapidActingAdult`. The brand string is in the source and worth keeping: it is
what decides whether a donor is on a rapid or an ULTRA-rapid analogue, which
changes the timing of every activity estimate and is a plausible source of
difference in how delivery behaves.

Writes formulation.csv: alias, brand, category, share of records carrying the
brand, and whether the donor's records disagree with each other.

  rapid        Novolog / NovoRapid, Humalog, Admelog, Apidra
  ultra-rapid  Fiasp, Lyumjev
  inhaled      Afrezza

Run:  python3 pull_formulation.py            (needs Databricks credentials)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import screen_cohort as SC                                   # noqa: E402
import style as S                                            # noqa: E402
from loopeval_analysis.tidepool.conn import query             # noqa: E402

CATEGORY = {
    "novolog": "rapid", "novorapid": "rapid", "humalog": "rapid",
    "admelog": "rapid", "apidra": "rapid", "insulin lispro": "rapid",
    "fiasp": "ultra-rapid", "lyumjev": "ultra-rapid",
    "afrezza": "inhaled",
}


def main() -> int:
    amap = SC._ids()
    co = S.cohort()
    ids = {a: amap[a] for a in co["alias"] if a in amap}
    missing = [a for a in co["alias"] if a not in amap]
    print(f"{len(ids)} of {len(co)} aliases resolve to a donor id"
          + (f"; no id for {missing}" if missing else ""))
    lst = ",".join(f"'{u}'" for u in sorted(set(ids.values())))
    W = f"{SC.T} BETWEEN {SC.START} AND {SC.END}"

    print("  formulation…", flush=True)
    d = query(f"""
        SELECT _userId,
               lower(trim(get_json_object(insulinFormulation,'$.simple.brand'))) AS brand,
               lower(trim(get_json_object(insulinFormulation,'$.simple.actingType'))) AS acting,
               count(*) AS n
        FROM {SC.TBL}
        WHERE type IN ('bolus','basal','pumpSettings') AND {W}
          AND _userId IN ({lst}) AND insulinFormulation IS NOT NULL
        GROUP BY 1,2,3""")
    d["n"] = pd.to_numeric(d["n"], errors="coerce").fillna(0).astype(int)

    rev = {v: k for k, v in ids.items()}
    d["alias"] = d["_userId"].map(rev)
    named = d[d["brand"].notna() & (d["brand"] != "")]
    print(f"  rows with a brand: {named['n'].sum():,} across {named.alias.nunique()} donors")
    print("\n  brands in the cohort:")
    print(named.groupby("brand")[["n"]].sum().join(
        named.groupby("brand")["alias"].nunique().rename("donors"))
        .sort_values("donors", ascending=False).to_string().replace("\n", "\n    "))
    print("\n  actingType as recorded:",
          named.groupby("acting")["alias"].nunique().to_dict())

    rows = []
    for a, g in named.groupby("alias"):
        tot = g["n"].sum()
        top = g.sort_values("n", ascending=False).iloc[0]
        brands = sorted(set(g["brand"]))
        rows.append(dict(alias=a, brand=top["brand"],
                         category=CATEGORY.get(top["brand"], "other"),
                         records=int(tot), purity=round(top["n"] / tot, 4),
                         n_brands=len(brands),
                         brands="|".join(brands) if len(brands) > 1 else top["brand"]))
    t = pd.DataFrame(rows).sort_values("alias")
    t.to_csv(S.OUT / "formulation.csv", index=False)
    print(f"\n  formulation.csv — {len(t)} donors with a brand, "
          f"{len(co) - len(t)} without")
    print("  by category:", t.category.value_counts().to_dict())
    mixed = t[t.n_brands > 1]
    if len(mixed):
        print(f"  {len(mixed)} donors record more than one brand:")
        print(mixed[["alias", "brands", "purity"]].to_string(index=False)
              .replace("\n", "\n    "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
