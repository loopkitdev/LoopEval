#!/usr/bin/env python3
"""Fetch raw Nightscout treatments/entries/profile into <outDir> for the oref
golden-master oracle (oracle.js). Credentials come from the environment so no
site address or token is committed (these are real users' data — keep private).

  NS_URL=https://<site>  NS_TOKEN=<token> \
  python3 fetch_ns.py <outDir> <startISO> <endISO>

The window should cover the decision cycle's ~24h + DIA lookback.
"""
import json, os, sys, urllib.request, urllib.parse, datetime as dt

BASE = os.environ["NS_URL"].rstrip("/")
TOKEN = os.environ["NS_TOKEN"]
OUT, START, END = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)

def get(path, params):
    params["token"] = TOKEN
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{BASE}/api/v1/{path}?{q}", timeout=120) as r:
        return json.load(r)

T = get("treatments.json", {"find[created_at][$gte]": START, "find[created_at][$lte]": END, "count": "100000"})
E = get("entries.json", {"find[dateString][$gte]": START, "find[dateString][$lte]": END, "count": "100000"})
P = get("profile.json", {"count": "5"})
json.dump(T, open(f"{OUT}/treatments.json", "w"))
json.dump([e for e in E if e.get("sgv")], open(f"{OUT}/entries.json", "w"))
json.dump(P, open(f"{OUT}/profile.json", "w"))
print(f"treatments {len(T)}  entries(sgv) {len([e for e in E if e.get('sgv')])}  profiles {len(P)} -> {OUT}")
