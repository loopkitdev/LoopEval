"""Explore the Tidepool BDDP device-data in Databricks: discover the table,
its columns, the `type` distribution, and how Loop/AID users are identifiable.

Run after setting the DATABRICKS_* env vars (see conn.py):
    python3 -m loopeval_analysis.tidepool.explore                 # discovery
    python3 -m loopeval_analysis.tidepool.explore <full.table>    # inspect a known table
"""
import sys
from loopeval_analysis.tidepool.conn import query

def discover():
    print("=== catalogs ===")
    try: print(query("SHOW CATALOGS").to_string());
    except Exception as e: print("SHOW CATALOGS failed:", e)
    print("\n=== schemas (per catalog) — set TIDEPOOL_CATALOG to narrow ===")
    import os
    cat = os.environ.get("TIDEPOOL_CATALOG")
    if cat:
        print(query(f"SHOW SCHEMAS IN {cat}").to_string())
        sch = os.environ.get("TIDEPOOL_SCHEMA")
        if sch:
            print(f"\n=== tables in {cat}.{sch} ===")
            print(query(f"SHOW TABLES IN {cat}.{sch}").to_string())
    else:
        print("(set TIDEPOOL_CATALOG, then TIDEPOOL_SCHEMA, to drill in)")

def inspect(table):
    print(f"=== columns of {table} ===")
    print(query(f"DESCRIBE {table}").to_string())
    print(f"\n=== row count ===")
    print(query(f"SELECT count(*) AS n FROM {table}").to_string())
    print(f"\n=== distinct `type` ===")
    try: print(query(f"SELECT type, count(*) AS n FROM {table} GROUP BY type ORDER BY n DESC").to_string())
    except Exception as e: print("type breakdown failed (no `type` col?):", e)
    print(f"\n=== sample row (first non-null per a few cols) ===")
    print(query(f"SELECT * FROM {table} LIMIT 3").T.to_string())
    # Loop/AID identification probes — try common Tidepool fields
    for col in ["origin", "deviceManufacturers", "deviceId", "uploadId"]:
        try:
            print(f"\n=== top {col} values (Loop/AID markers?) ===")
            print(query(f"SELECT {col}, count(*) AS n FROM {table} GROUP BY {col} ORDER BY n DESC LIMIT 15").to_string())
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect(sys.argv[1])
    else:
        discover()
