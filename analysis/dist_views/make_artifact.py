#!/usr/bin/env python3
"""Build every document in the distribution study.

The study is four pages: glucose, insulin, glucose given insulin, and
counteraction. Shared chrome lives in page.py; each document owns its own body
in doc_<name>.py. Run this after web_figs.py — the pages inline the downsampled
copies under runs/.../web, so a figure rebuilt without re-running web_figs.py
republishes its stale predecessor with no error (lesson 26).

    python3 analysis/dist_views/web_figs.py
    python3 analysis/dist_views/make_artifact.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import doc_conditioning
import doc_counteraction
import doc_glucose
import doc_insulin

DOCS = (doc_glucose, doc_insulin, doc_conditioning, doc_counteraction)


def main() -> int:
    for m in DOCS:
        m.build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
