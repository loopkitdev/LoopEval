#!/usr/bin/env python3
"""Local-network doc preview for LoopEval.

Renders the Markdown docs the way GitHub does — GitHub alerts (> [!NOTE] ...),
Mermaid diagrams, tables, and relative images — and serves the whole repo over HTTP
so teammates on your LAN can read the docs with no build step and no push to GitHub.

    python3 scripts/docserve.py                 # 0.0.0.0:8080
    python3 scripts/docserve.py 9000            # custom port
    python3 scripts/docserve.py 8080 127.0.0.1  # localhost only

Then open the LAN URL it prints (e.g. http://192.168.1.20:8080/docs/).

Markdown is rendered client-side with marked + mermaid loaded from a CDN, so the
*viewing* machine needs internet — it's a dev preview, not a hosted site. Everything
else (PNGs, etc.) is served as static files, so relative image links resolve normally.
"""
import base64
import http.server
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # repo root

# ---------------------------------------------------------------- allowlist
# This server binds to 0.0.0.0 by default, so everything reachable is on the LAN.
# The repo holds a real person's medical data (runs/) and live credentials
# (PRIVATE.md) — so paths are ALLOWLISTED, not denylisted: a request is served
# only if it resolves inside an explicitly allowed root. Nothing else exists as
# far as this server is concerned, including the rest of the filesystem.
#
#   docs/  is always allowed (the guides + their images).
#   --allow <dir>  opts an extra repo-relative dir in, e.g. `--allow runs`
#                  to share case-study plots. Never on by default.
ALWAYS_ALLOW = ["docs"]

# Extra (opted-in) roots serve only these suffixes — plots and tabular data,
# never source, config, or credential files that may sit alongside them.
DATA_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp",
                 ".csv", ".json", ".md", ".txt"}

# Belt-and-braces: never serve these, even if they land inside an allowed root.
DENY_NAMES = {"private.md", ".env", "site.json", ".netrc", "databricks.env",
              "credentials", "secrets.json", "id_rsa", ".git-credentials"}
DENY_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".sqlite", ".db"}


def _parse_args(argv):
    port, host, extra = 8080, "0.0.0.0", []
    pos = []
    i = 0
    while i < len(argv):
        if argv[i] == "--allow" and i + 1 < len(argv):
            extra.append(argv[i + 1].strip("/"))
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    if pos:
        port = int(pos[0])
    if len(pos) > 1:
        host = pos[1]
    return port, host, extra


PORT, HOST, EXTRA_ALLOW = _parse_args(sys.argv[1:])

ALLOW_ROOTS = []
for rel in ALWAYS_ALLOW + EXTRA_ALLOW:
    p = (ROOT / rel).resolve()
    if p.is_dir():
        ALLOW_ROOTS.append(p)
    else:
        print(f"  ! --allow {rel}: not a directory under {ROOT} — ignored")


def permitted(fp: Path):
    """True if fp resolves inside an allowed root and isn't denied.

    Resolves symlinks first, so a link pointing out of an allowed root (or out
    of the repo) is rejected rather than followed.
    """
    try:
        real = fp.resolve()
    except (OSError, RuntimeError):
        return False
    if real.name.lower() in DENY_NAMES or real.suffix.lower() in DENY_SUFFIXES:
        return False
    if any(part.startswith(".") and part not in (".", "..") for part in real.parts):
        return False  # dotfiles / .git / .ssh …
    for root in ALLOW_ROOTS:
        if real == root or root in real.parents:
            # Opted-in extra roots are restricted to plot/data suffixes.
            if root.name not in ALWAYS_ALLOW and real.is_file() \
                    and real.suffix.lower() not in DATA_SUFFIXES:
                return False
            return True
    return False

PAGE = r"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>__TITLE__ · LoopEval docs</title>
<style>
  :root{color-scheme:light dark}
  body{margin:0;background:#fff;color:#1f2328;font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  .md{max-width:900px;margin:0 auto;padding:32px 24px 120px}
  .md img{max-width:100%;border:1px solid #d0d7de;border-radius:6px}
  .md h1,.md h2{border-bottom:1px solid #d1d9e0;padding-bottom:.3em}
  .md h1{font-size:2em}.md h2{font-size:1.5em;margin-top:1.6em}
  .md code{background:#eff1f3;padding:.2em .4em;border-radius:6px;font:85% ui-monospace,SFMono-Regular,Menlo,monospace}
  .md pre{background:#f6f8fa;padding:14px 16px;border-radius:8px;overflow:auto}
  .md pre code{background:none;padding:0;font-size:90%}
  .md pre.mermaid{background:none;text-align:center}
  .md table{border-collapse:collapse;display:block;overflow:auto;max-width:100%}
  .md th,.md td{border:1px solid #d1d9e0;padding:6px 13px}.md tr:nth-child(2n){background:#f6f8fa}
  .md blockquote{margin:0;color:#59636e;border-left:.25em solid #d1d9e0;padding:0 1em}
  .md a{color:#0969da;text-decoration:none}.md a:hover{text-decoration:underline}
  .gh-alert{border-left-width:.25em;border-left-style:solid;padding:8px 16px;margin:16px 0;color:inherit}
  .gh-alert-title{display:flex;font-weight:600;margin:0 0 4px}
  .gh-note{border-left-color:#0969da}.gh-note .gh-alert-title{color:#0969da}
  .gh-tip{border-left-color:#1a7f37}.gh-tip .gh-alert-title{color:#1a7f37}
  .gh-important{border-left-color:#8250df}.gh-important .gh-alert-title{color:#8250df}
  .gh-warning{border-left-color:#9a6700}.gh-warning .gh-alert-title{color:#9a6700}
  .gh-caution{border-left-color:#cf222e}.gh-caution .gh-alert-title{color:#cf222e}
  @media (prefers-color-scheme:dark){
    body{background:#0d1117;color:#e6edf3}
    .md code{background:#6e768166}.md pre{background:#161b22}.md th,.md td{border-color:#3d444d}
    .md tr:nth-child(2n){background:#161b22}.md blockquote{border-left-color:#3d444d;color:#9198a1}
    .md h1,.md h2{border-color:#21262d}.md img{border-color:#30363d}.md a{color:#4493f8}}
</style></head><body><article class=md id=doc>Rendering…</article>
<script type=module>
import {marked} from 'https://cdn.jsdelivr.net/npm/marked@12/lib/marked.esm.js';
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
const md = new TextDecoder().decode(Uint8Array.from(atob("__B64__"), c=>c.charCodeAt(0)));
const el = document.getElementById('doc');
el.innerHTML = marked.parse(md, {gfm:true});
// ```mermaid fences -> <pre class=mermaid>
el.querySelectorAll('pre code.language-mermaid').forEach(c=>{
  const p=document.createElement('pre');p.className='mermaid';p.textContent=c.textContent;
  c.closest('pre').replaceWith(p);});
// GitHub alerts: > [!NOTE] ...
const names={NOTE:'Note',TIP:'Tip',IMPORTANT:'Important',WARNING:'Warning',CAUTION:'Caution'};
el.querySelectorAll('blockquote').forEach(bq=>{
  const m=bq.textContent.trim().match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/i);
  if(!m)return;const t=m[1].toUpperCase();
  bq.classList.add('gh-alert','gh-'+t.toLowerCase());
  const fp=bq.querySelector('p');
  if(fp)fp.innerHTML=fp.innerHTML.replace(/^\s*\[![^\]]*\]\s*(<br\s*\/?>)?\s*/i,'');
  const h=document.createElement('p');h.className='gh-alert-title';h.textContent=names[t];
  bq.insertBefore(h,bq.firstChild);});
mermaid.initialize({startOnLoad:false, theme: matchMedia('(prefers-color-scheme:dark)').matches?'dark':'neutral'});
await mermaid.run();
document.title = (el.querySelector('h1')?.textContent || '__TITLE__') + ' · LoopEval docs';
</script></body></html>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def do_GET(self):
        fp = Path(self.translate_path(self.path))
        clean = self.path.split("?")[0]

        # Root: a small index of what's shared — never a repo-root listing.
        if clean in ("/", "/index.html"):
            return self._index()

        # Everything else must be inside an allowed root (see permitted()).
        if not permitted(fp):
            self.send_error(404, "Not Found")
            return

        if fp.is_dir():
            if not self.path.split("?")[0].endswith("/"):
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return
            readme = fp / "README.md"
            if readme.exists():
                return self._render(readme)
        elif fp.suffix.lower() == ".md" and fp.exists():
            return self._render(fp)
        return super().do_GET()

    def _index(self):
        links = "".join(
            f'<li><a href="/{r.relative_to(ROOT).as_posix()}/">'
            f'{r.relative_to(ROOT).as_posix()}/</a></li>'
            for r in ALLOW_ROOTS
        )
        html = (
            "<!doctype html><meta charset=utf-8><title>LoopEval docs</title>"
            "<style>body{font:16px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;"
            "max-width:640px;margin:64px auto;padding:0 24px}"
            "a{color:#0969da}@media(prefers-color-scheme:dark){"
            "body{background:#0d1117;color:#e6edf3}a{color:#4493f8}}</style>"
            "<h1>LoopEval docs</h1><p>Shared on this LAN:</p><ul>" + links + "</ul>"
            "<p><a href='/docs/simulator-guide/'>→ Simulator guide</a></p>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def _render(self, mdpath: Path):
        b64 = base64.b64encode(mdpath.read_text(encoding="utf-8").encode("utf-8")).decode("ascii")
        html = PAGE.replace("__TITLE__", mdpath.stem).replace("__B64__", b64)
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quieter
        pass


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    ip = lan_ip()
    print(f"LoopEval docs — repo {ROOT}")
    print("  sharing (allowlist):")
    for r in ALLOW_ROOTS:
        print(f"    {r.relative_to(ROOT).as_posix()}/")
    print("  blocked: PRIVATE.md, credentials, dotfiles, and everything not listed above")
    print(f"  local : http://localhost:{PORT}/docs/simulator-guide/")
    if HOST == "0.0.0.0":
        print(f"  LAN   : http://{ip}:{PORT}/docs/simulator-guide/   ← share this")
    print("  Ctrl-C to stop")
    http.server.ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
