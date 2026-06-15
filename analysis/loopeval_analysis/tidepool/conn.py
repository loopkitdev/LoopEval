"""Databricks SQL-warehouse connection for the Tidepool BDDP data.

Reads connection details from env vars (set these in your shell, e.g. a
`~/.loop-eval/databricks.env` you `source`):

    DATABRICKS_HOST        e.g.  dbc-xxxx.cloud.databricks.com   (no https://)
    DATABRICKS_HTTP_PATH   e.g.  /sql/1.0/warehouses/abc123
    DATABRICKS_TOKEN       e.g.  dapi....

Optionally:
    TIDEPOOL_CATALOG / TIDEPOOL_SCHEMA / TIDEPOOL_TABLE   (the device-data table)

Usage:
    from loopeval_analysis.tidepool.conn import query
    df = query("SELECT * FROM <table> LIMIT 5")
"""
import os
import pandas as pd
from databricks import sql

# Auto-load credentials from ~/.loop-eval/databricks.env (KEY=VALUE lines) if the
# env vars aren't already set in the process — so connection details persist across
# tool calls without echoing the token into the shell.
_ENVFILE = os.path.expanduser("~/.loop-eval/databricks.env")
if os.path.exists(_ENVFILE):
    for _line in open(_ENVFILE):
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _k = _k.strip().replace("export ", "").strip()
        os.environ.setdefault(_k, _v.strip().strip('"').strip("'"))

def _cfg():
    host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").strip("/")
    http_path = os.environ.get("DATABRICKS_HTTP_PATH", "")
    if not host or not http_path:
        miss = [k for k, v in [("DATABRICKS_HOST", host), ("DATABRICKS_HTTP_PATH", http_path)] if not v]
        raise RuntimeError("Missing Databricks env vars: " + ", ".join(miss) +
                           "\nAdd them to ~/.loop-eval/databricks.env then retry.")
    return host, http_path

def connection():
    """Connect to the SQL warehouse. Auth method auto-selected:
      • DATABRICKS_TOKEN set                  → PAT
      • DATABRICKS_CLIENT_ID + _CLIENT_SECRET → OAuth M2M (service principal)
      • else                                  → OAuth U2M (browser; uses the token
        cached by `databricks auth login` / a prior browser login, refreshing
        silently — no PAT needed). PATs-disabled workspaces use this path.
    """
    host, http_path = _cfg()
    token = os.environ.get("DATABRICKS_TOKEN")
    if token:
        return sql.connect(server_hostname=host, http_path=http_path, access_token=token)

    from databricks.sdk.core import Config, oauth_service_principal
    cid = os.environ.get("DATABRICKS_CLIENT_ID")
    csec = os.environ.get("DATABRICKS_CLIENT_SECRET")
    if cid and csec:  # M2M
        cfg = Config(host=f"https://{host}", client_id=cid, client_secret=csec)
        return sql.connect(server_hostname=host, http_path=http_path,
                           credentials_provider=lambda: oauth_service_principal(cfg))
    # U2M (external browser; reuses cached OAuth token, refreshes automatically)
    cfg = Config(host=f"https://{host}", auth_type="external-browser")
    return sql.connect(server_hostname=host, http_path=http_path,
                       credentials_provider=lambda: cfg.authenticate)

def query(q, params=None):
    """Run a SQL query, return a pandas DataFrame."""
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, params or {})
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

TABLE = lambda: os.environ.get("TIDEPOOL_TABLE") or ".".join(
    x for x in [os.environ.get("TIDEPOOL_CATALOG"), os.environ.get("TIDEPOOL_SCHEMA"),
                os.environ.get("TIDEPOOL_TABLE_NAME")] if x)
