#!/usr/bin/env python3
"""Downsample runs/.../figs into runs/.../web for the artifact.

`make_artifact.py` inlines every figure as a base64 data URI, and base64 costs
a third again on top of the file, so the whole page has to stay well under the
16 MB artifact limit. Full-resolution 150-dpi figures blow through it; these
1650-px 192-colour copies land around 4-5 MB for the set.

Run this after ANY figure change, before make_artifact.py — a rebuilt figure
that never reaches web/ is published as its stale predecessor with no error.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as _S

WIDTH = 1650
COLORS = 192

FIGS = _S.OUT / "figs"
WEB = _S.OUT / "web"


def main() -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    total = 0
    for src in sorted(FIGS.glob("*.png")):
        im = Image.open(src).convert("RGB")
        if im.width > WIDTH:
            im = im.resize((WIDTH, round(im.height * WIDTH / im.width)),
                           Image.LANCZOS)
        q = im.quantize(colors=COLORS, method=Image.MEDIANCUT,
                        dither=Image.FLOYDSTEINBERG)
        dst = WEB / src.name
        q.save(dst, optimize=True)
        kb = dst.stat().st_size / 1024
        total += kb
        print(f"  {src.name:32s} {kb:7.0f} KB")
    print(f"  total {total / 1024:.1f} MB  (~{total / 1024 * 4 / 3:.1f} MB base64)")


if __name__ == "__main__":
    main()
