#!/usr/bin/env python3
"""Shared chrome for the distribution study's documents.

The study is four pages now, not one: glucose, insulin, glucose given insulin,
and counteraction. They share a visual identity and a figure-inlining
convention, so those live here and each document owns only its own body. A
document is a `build(body, filename, title)` call; `{{FIG:name}}` in the body
is replaced by the downsampled copy under runs/.../web.

Figures are inlined from `web/`, NOT `figs/` — run web_figs.py after any
figure change or a page republishes its stale predecessor (lesson 26).
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as _S

OUT = _S.OUT
WEB = OUT / "web"

CSS = """<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
  :root { color-scheme: light;
    --ground:#fbfaf7; --panel:#f3f1ea; --panel-2:#ebe8df; --plot:#fcfcfb;
    --ink:#14181d; --ink-2:#4a5661; --muted:#8a949e; --rule:#e0ddd4;
    --accent:#c94a26; --blue:#3b6ea5; --green:#158f64; --violet:#7c4fe0; }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground:#0f1216; --panel:#171b21; --panel-2:#1f242b; --plot:#f3f2ee;
    --ink:#e9e6df; --ink-2:#a7b0ba; --muted:#6d7681; --rule:#282e35;
    --accent:#f0764a; --blue:#78a6d8; --green:#3ecf9a; --violet:#a98bf0; } }
  :root[data-theme="dark"] { color-scheme: dark;
    --ground:#0f1216; --panel:#171b21; --panel-2:#1f242b; --plot:#f3f2ee;
    --ink:#e9e6df; --ink-2:#a7b0ba; --muted:#6d7681; --rule:#282e35;
    --accent:#f0764a; --blue:#78a6d8; --green:#3ecf9a; --violet:#a98bf0; }

  body { background:var(--ground); color:var(--ink); margin:0;
    padding:0 22px 110px;
    font-family:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
    font-size:16.5px; line-height:1.62; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1460px; margin:0 auto; }
  .col { max-width:68ch; }
  p, li { color:var(--ink-2); }
  strong { color:var(--ink); font-weight:600; }
  em { font-style:italic; }
  a { color:var(--accent); }

  h1 { font-family:Spectral,Georgia,serif; font-weight:600;
       font-size:clamp(34px,5vw,58px); line-height:1.06; letter-spacing:-.02em;
       margin:76px 0 0; max-width:15ch; text-wrap:balance; color:var(--ink); }
  .lede { font-family:Spectral,Georgia,serif; font-size:clamp(18px,2.1vw,22px);
       line-height:1.5; color:var(--ink-2); max-width:56ch; margin:20px 0 0; }
  h2 { font-family:Spectral,Georgia,serif; font-weight:600;
       font-size:clamp(23px,2.7vw,31px); line-height:1.18; letter-spacing:-.012em;
       margin:0 0 6px; color:var(--ink); max-width:26ch; text-wrap:balance; }
  h3 { font-family:"IBM Plex Sans",sans-serif; font-weight:600; font-size:17px;
       margin:34px 0 6px; color:var(--ink); }

  .eyebrow { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:11.5px;
       letter-spacing:.13em; text-transform:uppercase; color:var(--accent);
       margin:0 0 10px; display:flex; align-items:center; gap:10px; }
  .eyebrow::after { content:""; flex:1; height:1px; background:var(--rule); }

  section { margin:74px 0 0; }
  section > p, section > ul, section > ol, section > h3 { max-width:68ch; }

  figure { margin:30px 0 0; }
  figure img { width:100%; height:auto; display:block; border:1px solid var(--rule);
       border-radius:3px; background:var(--plot); }
  figcaption { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12px;
       line-height:1.55; color:var(--muted); margin:10px 0 0; max-width:100ch; }
  figcaption b { color:var(--ink-2); font-weight:500; }

  .read { border-left:2px solid var(--accent); padding:2px 0 2px 18px;
       margin:26px 0 0; max-width:66ch; }
  .read p { margin:0; color:var(--ink); }

  .scroll { overflow-x:auto; margin:26px 0 0;
       border:1px solid var(--rule); border-radius:3px; background:var(--panel); }
  table { border-collapse:collapse; width:100%;
       font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12.5px;
       font-variant-numeric:tabular-nums; }
  th, td { padding:7px 13px; text-align:right; white-space:nowrap;
       border-bottom:1px solid var(--rule); }
  th { color:var(--muted); font-weight:500; font-size:11px; letter-spacing:.06em;
       text-transform:uppercase; text-align:right; position:sticky; top:0;
       background:var(--panel-2); }
  td:first-child, th:first-child { text-align:left; color:var(--ink); }
  tbody tr:last-child td { border-bottom:none; }
  tbody tr:hover td { background:var(--panel-2); }

  .ledger { display:grid; gap:1px; background:var(--rule); border:1px solid var(--rule);
       border-radius:3px; margin:30px 0 0;
       grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); }
  .cell { background:var(--panel); padding:17px 18px; }
  .cell .k { font-family:"IBM Plex Mono",monospace; font-size:10.5px;
       letter-spacing:.1em; text-transform:uppercase; color:var(--muted); }
  .cell .v { font-family:Spectral,Georgia,serif; font-size:29px; line-height:1.1;
       color:var(--ink); margin:7px 0 3px; font-variant-numeric:tabular-nums; }
  .cell .n { font-size:13px; line-height:1.45; color:var(--ink-2); }

  .swatch { display:inline-block; width:9px; height:9px; border-radius:2px;
       margin-right:5px; vertical-align:baseline; }
  code { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:13.5px;
       background:var(--panel-2); padding:1px 5px; border-radius:3px; color:var(--ink); }
  hr { border:0; border-top:1px solid var(--rule); margin:74px 0 0; }
  ul { padding-left:19px; }
  li { margin:7px 0; }
  li::marker { color:var(--muted); }
  .foot { color:var(--muted); font-size:14px; max-width:68ch; }
  :focus-visible { outline:2px solid var(--accent); outline-offset:3px; }
  @media (prefers-reduced-motion: reduce) { * { transition:none !important; } }

  /* companion-document strip */
  .sib { display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 16px;
    margin:40px 0 0; padding:14px 0 0; border-top:1px solid var(--rule);
    font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12px; }
  .sib-l { color:var(--muted); letter-spacing:.06em; text-transform:uppercase; }
  .sib a { color:var(--accent); text-decoration:none;
    border-bottom:1px solid color-mix(in srgb, var(--accent) 35%, transparent); }
  .sib a:hover { border-bottom-color:var(--accent); }
  .sib-here { color:var(--ink); font-weight:600; }
  .sib-soon { color:var(--muted); }
  .sib-soon::after { content:" · in preparation"; color:var(--rule); }
</style>
\"\"\"
"""


def chrome(title: str) -> str:
    return f"<title>{title}</title>\n" + CSS


def img(name: str) -> str:
    b = (WEB / f"{name}.png").read_bytes()
    return "data:image/png;base64," + base64.b64encode(b).decode()


def build(body: str, filename: str, title: str) -> Path:
    """Render one document to runs/.../<filename> and return the path."""
    html = chrome(title) + body
    html = re.sub(r"\{\{FIG:([0-9a-z_]+)\}\}", lambda m: img(m.group(1)), html)
    dst = OUT / filename
    dst.write_text(html)
    print(f"wrote {dst}  ({dst.stat().st_size/1e6:.1f} MB)")
    return dst


# Every document carries the same short index of its companions, so a reader
# who lands on one can find the rest. URLs are filled in as each is published.
SIBLINGS = {
    "glucose": ("The Shape of Glucose",
                "https://claude.ai/code/artifact/6b061d95-1172-41a8-b048-1a567e2c533c"),
    "insulin": ("The Shape of Insulin", None),
    "conditioning": ("Glucose Given Insulin", None),
    "counteraction": ("Counteraction", None),
}


def nav(current: str) -> str:
    """The companion-document strip, with `current` marked and unlinked."""
    out = ['<nav class="sib"><span class="sib-l">This is one of four:</span>']
    for key, (name, url) in SIBLINGS.items():
        if key == current:
            out.append(f'<span class="sib-here">{name}</span>')
        elif url:
            out.append(f'<a href="{url}">{name}</a>')
        else:
            out.append(f'<span class="sib-soon">{name}</span>')
    out.append("</nav>")
    return "".join(out)
