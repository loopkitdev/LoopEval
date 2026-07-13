"""One-time OAuth U2M (browser) login for the Tidepool Databricks SQL warehouse.

Run this ONCE, interactively (a browser window opens to authenticate):

    cd LoopEval/analysis
    python3 -m loopeval_analysis.tidepool.login

It caches the OAuth token (refresh-token-backed, in ~/.databricks/token-cache.json),
so subsequent non-interactive queries reuse and silently refresh it — no PAT needed.
Reads DATABRICKS_HOST from ~/.loop-eval/databricks.env (auto-loaded by conn.py).
"""
import os
import loopeval_analysis.tidepool.conn  # noqa: F401 — triggers env-file load
from databricks.sdk.core import Config

def main():
    host = os.environ.get("DATABRICKS_HOST", "").replace("https://", "").strip("/")
    if not host:
        raise SystemExit("DATABRICKS_HOST not set — add it to ~/.loop-eval/databricks.env first.")
    print(f"Authenticating to https://{host} via browser (OAuth U2M)…")
    cfg = Config(host=f"https://{host}", auth_type="external-browser")
    headers = cfg.authenticate()  # opens browser on first run; caches token
    ok = bool(headers.get("Authorization"))
    print("OAuth login OK — token cached." if ok else "Login returned no auth header (check host).")
    print("You can now run: python3 -m loopeval_analysis.tidepool.explore")

if __name__ == "__main__":
    main()
