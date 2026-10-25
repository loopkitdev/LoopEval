"""Batched warehouse reads for multi-donor ETL exports.

Every query against the device-data view costs a near-fixed scan, whatever it selects:
pumpSettings for one donor took 14.3 s, for all 207 pilot donors 17.4 s. `export_donor` runs ~19
per-donor queries, so a donor costs ~2 min of scans that return a few thousand rows.

Inside `with batch(users):`, a per-donor query whose only donor-specific part is
`_userId='<uid>'` (uid in the block) is rewritten to `_userId IN (<block>)`, run ONCE for the
block, and each donor's call is served its own rows from the cached result. Order is preserved
(the block result keeps the query's ORDER BY, and a donor's rows are a stable subset of it).
A single-SELECT aggregate (COUNT, GROUP BY, LIMIT k) is batched too: the donor joins the GROUP BY, LIMIT k becomes
the first k rows per donor (the ORDER BY is kept), and a donor with no rows in a pure aggregate gets its zero row.
They are not cheap: each still scans ~85 GB (13 s on the Small warehouse), two per donor. Other queries that
can't be split run per donor as before. The ETL's logic is untouched: `export_donor` inside a block writes the same files it writes
outside one.

Donors in a block must share the export window: time bounds are part of every query's text, so a
donor with a different window simply misses the cache and runs its own queries.

    from loopeval_analysis.tidepool.batch import export_block
    export_block(users, "2026-06-01", "2026-10-07", outdirs)
"""
from __future__ import annotations

import re
import threading
from contextlib import contextmanager

import pandas as pd

from .conn import query as _direct_query

_UID = re.compile(r"_userId\s*=\s*'([0-9a-fA-F-]+)'")
_UNSPLITTABLE = re.compile(r"\bGROUP\s+BY\b|\bLIMIT\b|\bCOUNT\s*\(", re.IGNORECASE)
_state = threading.local()


class _Block:
    def __init__(self, users):
        self.users = list(dict.fromkeys(users))
        self.cache: dict[str, dict] = {}
        self.columns: dict[str, list] = {}
        self.served: dict[str, set] = {}
        self.lock = threading.Lock()
        self.hits = self.misses = self.direct = 0


@contextmanager
def batch(users):
    """Serve per-donor ETL queries for `users` from block-wide queries (see module doc)."""
    prev = getattr(_state, "block", None)
    _state.block = _Block(users)
    try:
        yield _state.block
    finally:
        _state.block = prev


def _rewrite(q: str, uid: str, users) -> str:
    in_list = ", ".join(f"'{u}'" for u in users)
    q = _UID.sub(lambda m: f"_userId IN ({in_list})" if m.group(1) == uid else m.group(0), q)
    # Thread the donor id through every SELECT: a SELECT reading a subquery ("FROM (")
    # passes the column on; one reading the table adds it.
    out, pos = [], 0
    for m in re.finditer(r"\bSELECT\s+(DISTINCT\s+)?", q, re.IGNORECASE):
        out.append(q[pos:m.end()])
        depth, j = 0, m.end()
        while j < len(q):                     # find this SELECT's own FROM (same paren depth)
            c = q[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif depth == 0 and re.match(r"FROM\b", q[j:j + 5], re.IGNORECASE):
                break
            j += 1
        from_sub = re.match(r"FROM\s*\(", q[j:], re.IGNORECASE) is not None
        out.append("__uid, " if from_sub else "_userId AS __uid, ")
        pos = m.end()
    out.append(q[pos:])
    return "".join(out)


_LIMIT = re.compile(r"\s+LIMIT\s+(\d+)\s*$", re.IGNORECASE)
_GROUP = re.compile(r"\bGROUP\s+BY\s+", re.IGNORECASE)
_ORDER = re.compile(r"\s+ORDER\s+BY\b", re.IGNORECASE)


def _agg_rewrite(q: str, uid: str, users):
    """Block form of a single-SELECT aggregate for one donor -> (query, per-donor limit or None, pure aggregate),
    or None when the query has a subquery or a LIMIT that is not the last clause."""
    if len(re.findall(r"\bSELECT\b", q, re.IGNORECASE)) != 1 or re.search(r"FROM\s*\(", q, re.IGNORECASE):
        return None
    if re.search(r"\bLIMIT\b", q, re.IGNORECASE) and not _LIMIT.search(q):
        return None
    limit = None
    lm = _LIMIT.search(q)
    if lm:
        limit = int(lm.group(1)); q = q[:lm.start()]
    in_list = ", ".join(f"'{u}'" for u in users)
    q = _UID.sub(lambda m: f"_userId IN ({in_list})", q)
    q = re.sub(r"\bSELECT\s+", "SELECT _userId AS __uid, ", q, count=1, flags=re.IGNORECASE)
    pure = not _GROUP.search(q)
    if pure:
        om = _ORDER.search(q)
        q = (q[:om.start()] + " GROUP BY _userId" + q[om.start():]) if om else q + " GROUP BY _userId"
    else:
        q = _GROUP.sub("GROUP BY _userId, ", q, count=1)
    return q, limit, pure


def _canonical(df):
    """Deterministic row order. SQL leaves rows tied on the ORDER BY key in any order, and the ETL
    keeps the FIRST row per key in several places (glucose by timestamp, boluses by second and
    units, basal by start and duration, decisions by instant). Duplicate CGM uploads at one
    timestamp carry different values (129.73 vs 130.02), so two exports of the same donor could
    differ. Order by t_ms, then every other column, so ties always resolve the same way."""
    if df.empty or "t_ms" not in df.columns or len(df.columns) < 2:
        return df
    keys = pd.DataFrame({"__t": pd.to_numeric(df["t_ms"], errors="coerce")})
    for i, c in enumerate(df.columns):
        if c != "t_ms":
            keys[f"__k{i}"] = df[c].astype(str)
    order = keys.sort_values(list(keys.columns), kind="mergesort").index
    return df.loc[order].reset_index(drop=True)


def query(q, params=None):
    """Drop-in for conn.query: block-served when inside `batch(...)`, direct otherwise. Results
    carrying `t_ms` come back in a canonical order (see `_canonical`)."""
    return _canonical(_query(q, params))


def _query(q, params=None):
    blk = getattr(_state, "block", None)
    if blk is None or params:
        return _direct_query(q, params)
    m = _UID.search(q)
    if not m or m.group(1) not in blk.users or len(set(_UID.findall(q))) != 1 \
            or (_UNSPLITTABLE.search(q) and _agg_rewrite(q, m.group(1), blk.users) is None):
        blk.direct += 1
        return _direct_query(q)
    uid = m.group(1)
    agg = bool(_UNSPLITTABLE.search(q))
    key = q.replace(uid, "\x00")
    with blk.lock:
        if key not in blk.cache:
            blk.misses += 1
            if agg:
                bq, limit, pure = _agg_rewrite(q, uid, blk.users)
                df = _direct_query(bq)
            else:
                df = _direct_query(_rewrite(q, uid, blk.users)); limit, pure = None, False
            cols = [c for c in df.columns if c != "__uid"]
            blk.columns[key] = cols
            parts = {u: g.drop(columns="__uid").reset_index(drop=True) for u, g in df.groupby("__uid", sort=False)}
            if limit is not None:
                parts = {u: g.head(limit) for u, g in parts.items()}
            if pure:                                      # COUNT(*) with no group: every donor has one row
                zero = pd.DataFrame([{c: 0 for c in cols}])
                parts = {u: parts.get(u, zero.copy()) for u in blk.users}
            blk.cache[key] = parts
        else:
            blk.hits += 1
        freed = blk.cache[key] is None
        if not freed:
            part = blk.cache[key].get(uid)
            cols = blk.columns[key]
            blk.served.setdefault(key, set()).add(uid)
            if len(blk.served[key]) == len(blk.users):    # every donor served: free the block result
                blk.cache[key] = None
    if freed:                                             # a repeat after freeing: ask directly
        blk.direct += 1
        return _direct_query(q)
    return part.copy() if part is not None else pd.DataFrame(columns=cols)


def export_block(users, start, end, outdirs, insulin_types=None):
    """Export `users` (one shared window) with block-batched reads. `outdirs` parallels `users`.
    Returns per-donor results or the exception each raised."""
    from . import etl
    results = []
    with batch(users) as blk:
        for i, (u, od) in enumerate(zip(users, outdirs)):
            try:
                it = insulin_types[i] if insulin_types else None
                results.append(etl.export_donor(u, start, end, od, insulin_type=it))
            except Exception as e:          # one bad donor must not sink the block
                results.append(e)
        stats = dict(block_queries=blk.misses, served_from_block=blk.hits, direct=blk.direct)
    return results, stats
